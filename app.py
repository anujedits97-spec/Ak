"""Standalone xHamster-only resolver API."""
import logging
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

import config
import xhamster_resolver
import terabox_resolver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("xhamster_api")

app = FastAPI(
    title="xHamster Resolver API",
    description="Standalone xHamster-only video resolver API.",
    version="1.0.0",
)

_hits: dict[str, deque] = defaultdict(deque)
EXAMPLE_URL = "https://xhamster.com/videos/example-video-name-1234567"


def _check_rate_limit(client_ip: str):
    now = time.time()
    window = _hits[client_ip]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= config.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again in a bit.")
    window.append(now)


@app.get("/", include_in_schema=False)
def root():
    return {
        "status": True,
        "creator": "Ak API",
        "message": "Ak Resolver API is online",
        "version": "2.0.0",
        "endpoints": {
            "xhamster": "/api/xhamster?url=<XHAMSTER_VIDEO_URL>",
            "terabox": "/api/terabox?url=<TERABOX_SHARE_URL>",
            "unified": "/api?url=<URL>",
            "health": "/health",
        },
    }


@app.get("/health")
def health():
    return {"status": True, "service": "ak-resolver-api", "providers": ["xHamster", "TeraBox"]}


@app.get("/api/terabox")
async def terabox(url: str = Query(..., description="TeraBox public share link"), cookie: str | None = Query(None, description="Optional upstream cookie; not required")):
    if not terabox_resolver.is_terabox_link(url):
        return JSONResponse(status_code=400, content={"status": False, "error": "Only TeraBox share links are supported here."})
    try:
        data = await run_in_threadpool(terabox_resolver.resolve_terabox, url, cookie)
    except terabox_resolver.TeraBoxUpstreamError as e:
        logger.warning("TeraBox upstream failed: %s", e)
        return JSONResponse(status_code=502, content={
            "status": False,
            "error": str(e),
            "errno": next((a.get("errno") for a in e.attempts if a.get("errno") not in (None, 0, "0")), -1),
            "attempts": e.attempts,
        })
    except Exception as e:
        logger.warning("TeraBox resolve failed for %s: %s", url, e)
        return JSONResponse(status_code=502, content={"status": False, "error": str(e)})
    return {"status": True, "creator": "Ak", "data": data}


@app.get("/api")
async def unified(url: str = Query(..., description="xHamster or TeraBox URL"), cookie: str | None = Query(None, description="Optional TeraBox cookie")):
    if xhamster_resolver.is_xhamster_link(url):
        return await xhamster(url)
    if terabox_resolver.is_terabox_link(url):
        return await terabox(url, cookie)
    return JSONResponse(status_code=400, content={"status": False, "error": "Unsupported URL. Use xHamster or TeraBox."})


@app.get("/api/xhamster")
async def xhamster(url: str = Query(..., description="xHamster video link")):
    if not xhamster_resolver.is_xhamster_link(url):
        return JSONResponse(
            status_code=400,
            content={"status": False, "error": "Only xHamster links are supported here."},
        )
    try:
        data = await run_in_threadpool(xhamster_resolver.resolve_xhamster, url)
    except Exception as e:
        logger.warning("xHamster resolve failed for %s: %s", url, e)
        return JSONResponse(status_code=502, content={"status": False, "error": str(e)})
    return {"status": True, "data": data, "credit": "Ak"}


@app.middleware("http")
async def rate_limit_mw(request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    try:
        _check_rate_limit(client_ip)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"status": False, "error": e.detail})
    return await call_next(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=config.PORT, reload=False)
