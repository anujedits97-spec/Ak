# 🚀 Ak xHamster + TeraBox Resolver API

Standalone FastAPI resolver for **xHamster and public TeraBox share links**.

## TeraBox: cookie-free first

The TeraBox resolver does **not require a saved cookie file or hard-coded ndus token**. It opens the public share page, extracts the share ID and page-generated request context, then tries the public share-list endpoints.

A cookie query parameter is available only as an optional fallback:

```text
/api/terabox?url=<TERABOX_URL>&cookie=<COOKIE>
```

Do not put long-lived secrets in URLs in production; use a reverse proxy/header or environment secret if you intentionally need authenticated fallback.

## Endpoints

### TeraBox

```http
GET /api/terabox?url=https://terabox.com/s/XXXXXXXX
```

Also:

```http
GET /api?url=https://terabox.com/s/XXXXXXXX
```

### xHamster

```http
GET /api/xhamster?url=<XHAMSTER_VIDEO_URL>
```

### Health

```http
GET /health
```

### Docs

```text
/docs
```

## TeraBox response

```json
{
  "status": true,
  "creator": "Ak",
  "data": {
    "title": "video.mp4",
    "thumbnail": "https://...",
    "size": "131.02 MB",
    "size_bytes": 137388129,
    "extension": "mp4",
    "category": "Video",
    "download_url": "https://...",
    "dlink": "https://...",
    "fs_id": "...",
    "files": []
  }
}
```

## errno 105

TeraBox documents error **105** as an external-link error. If the public share endpoint rejects a request, the API now tries multiple current frontend hosts and both the full and simplified share/list parameter sets. It returns the upstream error instead of fabricating a direct URL.

## Important limitation

No resolver can guarantee a cookie-free direct download URL for every TeraBox share. Password-protected, expired, verification-gated, region-restricted, or otherwise authenticated shares can require additional TeraBox authorization. The API reports that condition cleanly.

## Run

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Docker

```bash
docker build -t ak-resolver-api .
docker run --rm -p 8000:8000 ak-resolver-api
```

## Render

Deploy the repository using the included Dockerfile. Render's `PORT` is respected.
