# API Contract: `/videos/list` — Issue #23
**By:** Ripley  
**Date:** 2026-05-07  
**Branch:** `squad/23-local-video-upload-gemini-caching-library-ui`  
**For:** Hudson (Frontend) — build your UI badges/buttons against this exact shape

---

## `GET /videos/list`

Returns all locally stored videos with Gemini file-cache status.

### Response
```json
{
  "videos": [
    {
      "filename": "demo.mp4",
      "filepath": "/app/uploads/demo.mp4",
      "size": 104857600,
      "modified": 1746633000.0,
      "duration": 120.5,
      "fps": 30.0,
      "gemini_uri": "files/abc123",
      "gemini_cache_status": "fresh",
      "expires_in_hours": 41
    },
    {
      "filename": "old.mp4",
      "filepath": "/app/uploads/old.mp4",
      "size": 52428800,
      "modified": 1746546600.0,
      "duration": 60.0,
      "fps": 25.0,
      "gemini_uri": "files/xyz789",
      "gemini_cache_status": "expired"
    },
    {
      "filename": "local.mp4",
      "filepath": "/app/uploads/local.mp4",
      "size": 20971520,
      "modified": 1746546600.0,
      "duration": 45.0,
      "fps": 24.0,
      "gemini_uri": null,
      "gemini_cache_status": "not_uploaded"
    }
  ]
}
```

### Field Reference

| Field | Type | Notes |
|-------|------|-------|
| `filename` | string | Safe filename (werkzeug `secure_filename`) |
| `filepath` | string | Absolute path inside container |
| `size` | int | Bytes |
| `modified` | float | Unix timestamp |
| `duration` | float | Seconds |
| `fps` | float | Frames per second |
| `gemini_uri` | string \| null | Gemini Files API URI (e.g. `"files/abc123"`) or `null` |
| `gemini_cache_status` | string | `"fresh"` \| `"expired"` \| `"not_uploaded"` |
| `expires_in_hours` | int | **Only present when `gemini_cache_status == "fresh"`** — hours until cache expires |

### Cache Status Rules
- **`fresh`** — has a URI and uploaded within the last 48 hours → show green badge + `expires_in_hours`
- **`expired`** — has a URI but older than 48 hours → show amber badge + "Re-upload" button
- **`not_uploaded`** — no URI in DB (or GEMINI_API_KEY not configured) → show grey badge + "Upload to Gemini" button

---

## `POST /upload` — New Gemini Fields

Existing upload endpoint; now returns Gemini status alongside file info.

```json
{
  "success": true,
  "filename": "demo.mp4",
  "filepath": "/app/uploads/demo.mp4",
  "duration": 120.5,
  "fps": 30.0,
  "total_frames": 3615,
  "width": 1920,
  "height": 1080,
  "gemini_uri": "files/abc123",
  "gemini_cache_status": "fresh"
}
```

- `gemini_uri` is `null` and `gemini_cache_status` is `"not_uploaded"` when Gemini key is absent or upload fails
- `gemini_upload_error` key (string) added **only** when a Gemini upload failure occurred — non-fatal, file is still saved locally

---

## `POST /videos/upload-to-gemini` — Re-upload Endpoint

Trigger a Gemini upload for a video that is `not_uploaded` or `expired`.

### Request
```json
{ "filename": "demo.mp4" }
```

### Success (200)
```json
{ "status": "ok", "uri": "files/abc123", "gemini_cache_status": "fresh" }
```

### Error responses
| Status | Body | Condition |
|--------|------|-----------|
| 400 | `{"error": "filename is required"}` | Missing body field |
| 404 | `{"error": "File not found"}` | File not in uploads dir |
| 503 | `{"error": "GEMINI_API_KEY is not configured"}` | Key absent |
| 500 | `{"error": "<message>"}` | Gemini API error |

---

## Removed Routes (Hudson: remove any JS calls to these)

- ~~`POST /videos/download`~~ — Reka CDN download, gone
- ~~`POST /reka/refresh-status/<video_id>`~~ — Reka status refresh, gone
