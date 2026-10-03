# ClaimShield API Interfaces

FastAPI server for running ClaimShield detectors on GPU/CPU, accessed remotely or locally.

## Base URL
- Local: `http://localhost:8000`
- HPC (via SSH tunnel): `http://localhost:8000` (tunneled to GPU node)

## Authentication
None (internal use only; HPC compute nodes have no internet access).

---

## Endpoints

### `GET /`
Root endpoint, returns welcome message and links.

**Response:**
```json
{
  "message": "ClaimShield API",
  "docs": "/docs",
  "health": "/api/health"
}
```

---

### `GET /api/health`
Model and system status check. Returns problems list (empty if all OK).

**Response:**
```json
{
  "status": "ok" | "degraded",
  "problems": ["list", "of", "issues"],
  "device": "cpu" | "cuda",
  "models_loaded": true | false
}
```

**Example:**
```bash
curl http://localhost:8000/api/health
```

---

### `POST /api/score/image`
Score a single image. Returns immediately with `job_id`; stream `/api/jobs/{job_id}/events` for cards.

**Request:**
- **Form data:** multipart/form-data
- **Fields:**
  - `file`: Image file (JPEG/PNG/HEIC/WebP), required

**Response:**
```json
{
  "job_id": "job_a1b2c3d4e5f6",
  "status": "pending"
}
```

**Example:**
```bash
curl -X POST -F "file=@photo.jpg" http://localhost:8000/api/score/image
# Returns: {"job_id": "job_...", "status": "pending"}
```

---

### `POST /api/score/document`
Score a document (PDF or scanned image). Returns `job_id`.

**Request:**
- **Form data:** multipart/form-data
- **Fields:**
  - `file`: Document file (PDF or image), required

**Response:**
```json
{
  "job_id": "job_...",
  "status": "pending"
}
```

---

### `POST /api/arena`
Attack an image and re-score (arena mode). Returns `job_id`.

**Request:**
- **Form data:** multipart/form-data
- **Fields:**
  - `seed`: (string, required) Seed filename in `data/seeds/` or `"upload"`
  - `method`: (string, optional) Attack method: `"inpaint"` (default) or `"recompress"`
  - `file`: (file, required if `seed="upload"`) Image file to attack

**Response:**
```json
{
  "job_id": "job_...",
  "status": "pending"
}
```

**Examples:**
```bash
# Attack existing seed
curl -X POST -d "seed=car_0001.jpg" -d "method=recompress" http://localhost:8000/api/arena

# Upload custom image
curl -X POST -F "seed=upload" -F "method=inpaint" -F "file=@my_photo.jpg" http://localhost:8000/api/arena
```

---

### `GET /api/jobs/{job_id}`
Get job status and result (polls, does not stream).

**Response:**
```json
{
  "job_id": "job_...",
  "status": "pending" | "running" | "completed" | "failed",
  "kind": "image" | "document" | "case" | "arena",
  "result": { ... } | null,
  "error": "error message" | null,
  "created_at": 1234567890.123,
  "completed_at": 1234567890.456 | null
}
```

When `status="completed"`, `result` contains the full scoring result (see **Result Schema** below).

**Example:**
```bash
curl http://localhost:8000/api/jobs/job_a1b2c3d4e5f6
```

---

### `GET /api/jobs/{job_id}/events`
Server-Sent Events (SSE) stream of job progress. Emits `card` events as signals complete, then a `final` event with the complete result.

**Event types:**
- `event: card` — A signal card completed
  ```json
  {"name": "exif", "score": 0.23, "confidence": 0.85, "reason": "...", ...}
  ```
- `event: final` — Job completed
  ```json
  {"overall": 0.42, "band": "MEDIUM", "signals": [...], ...}
  ```
- `event: error` — Job failed
  ```json
  {"error": "error message"}
  ```

**Example:**
```bash
curl -N http://localhost:8000/api/jobs/job_a1b2c3d4e5f6/events
# Streams:
# event: card
# data: {"name": "c2pa", ...}
#
# event: card
# data: {"name": "exif", ...}
# ...
# event: final
# data: {"overall": 0.42, ...}
```

---

## Result Schema

### ScoreResponse
Returned by `/api/jobs/{job_id}` when `status="completed"` for image/document scoring.

```json
{
  "overall": 0.42,
  "band": "LOW" | "MEDIUM" | "HIGH" | "UNCERTAIN",
  "image_score": 0.38 | null,
  "document_score": 0.51 | null,
  "identity_score": null,
  "waterfall": [
    ["signal_name", 0.15],
    ["another_signal", -0.08],
    ...
  ],
  "regions": [
    {
      "box": [100, 200, 300, 400],
      "area_frac": 0.12,
      "signals": {"localizer": 0.91, "ae_reconstruction": 0.73},
      "reason": "Region A (12%): localizer anomaly 0.91, ...",
      "stage": 1
    }
  ],
  "signals": [
    {
      "name": "c2pa",
      "score": null,
      "confidence": 0.0,
      "reason": "No Content Credentials found",
      "evidence": {},
      "abstained": false,
      "applicable": true,
      "tier": "fast"
    },
    {
      "name": "clip_probe",
      "score": 0.68,
      "confidence": 0.82,
      "reason": "CLIP features suggest diffusion-generated image",
      "evidence": {...},
      "abstained": false,
      "applicable": true,
      "tier": "fast"
    },
    ...
  ],
  "pending_deep": false,
  "sha256": "abc123...",
  "quality_flag": false,
  "t_first": 1.23,
  "t_fast": 6.78,
  "t_deep": 28.45
}
```

**Fields:**
- `overall`: Final score 0.0 (authentic) to 1.0 (manipulated)
- `band`: Risk band (`LOW < 0.35 ≤ MEDIUM < 0.65 ≤ HIGH`; `UNCERTAIN` if quality gate fired)
- `*_score`: Per-lane scores (image/document/identity); null if not applicable
- `waterfall`: Contribution breakdown (sorted by |value|)
- `regions`: Suspicious regions with bounding boxes
- `signals`: All detector outputs
- `pending_deep`: True if deep tier (AE reconstruction) is still running
- `sha256`: File hash
- `quality_flag`: True if quality gate fired (low resolution, blur, heavy compression)
- `t_first`, `t_fast`, `t_deep`: Timing (seconds)

### ArenaResponse
Returned by `/api/jobs/{job_id}` when `status="completed"` for arena attacks.

```json
{
  "seed_sha256": "original_hash",
  "attack_sha256": "attacked_hash",
  "attack_kind": "inpaint" | "recompress_q70",
  "attack_method": "nova" | "local_sd15" | "recompress",
  "attack_note": "Honest sentence about the attack",
  "attack_seconds": 12.34,
  "before": { ... ScoreResponse ... },
  "after": { ... ScoreResponse ... }
}
```

---

## Workflow Example

### 1. Start scoring an image
```bash
JOB=$(curl -s -X POST -F "file=@photo.jpg" http://localhost:8000/api/score/image | jq -r .job_id)
echo "Job ID: $JOB"
```

### 2. Stream events (SSE)
```bash
curl -N http://localhost:8000/api/jobs/$JOB/events
# Prints cards as they complete, then final result
```

### 3. Or poll for completion
```bash
while true; do
  STATUS=$(curl -s http://localhost:8000/api/jobs/$JOB | jq -r .status)
  echo "Status: $STATUS"
  [ "$STATUS" = "completed" ] && break
  sleep 1
done

curl -s http://localhost:8000/api/jobs/$JOB | jq .result
```

---

## Running the API

### Local (CPU or GPU)
```bash
# Activate venv
source .venv/bin/activate  # Linux/Mac
.\.venv\Scripts\Activate.ps1  # Windows

# Set environment
export CLAIMSHIELD_DEVICE=cuda  # or cpu
export HF_HUB_OFFLINE=1
export CLAIMSHIELD_LLM_PRIMARY=template  # no LLM for narrative

# Start server
uvicorn claimshield.api:app --host 0.0.0.0 --port 8000

# Open http://localhost:8000/docs for Swagger UI
```

### HPC GPU (via SSH tunnel)
See the main deployment guide in the user's prompt. Summary:
1. On HPC GPU node: `uvicorn claimshield.api:app --host 0.0.0.0 --port 8000`
2. On laptop (must be on campus network):
   ```bash
   ssh -N -L 8000:rachel-gpu:8000 btech10279.24@172.16.220.100
   ```
3. Access from laptop: `http://localhost:8000`

---

## Notes

- **Deep tier:** Image scoring returns immediately with `pending_deep=True`. The deep tier (AE reconstruction) runs async. Poll `/api/jobs/{job_id}` or stream `/events` to get the final result when it lands (typically 20-30s on CPU, <5s on GPU).
- **Card streaming:** The `/events` endpoint is designed for real-time UI updates. Each card event contains one detector's output; the final event has the complete scored result.
- **Temporary files:** Uploads are saved to temp files that are deleted after scoring completes. Attacked images (arena mode) are also deleted after re-scoring.
- **Concurrency:** The API runs up to 4 concurrent scoring jobs. Additional requests queue.
- **Error handling:** If a job fails, `status="failed"` and `error` contains the exception message.

---

## Status Codes

- `200 OK` — Success
- `404 Not Found` — Job ID not found, or seed file not found (arena)
- `400 Bad Request` — Missing required fields
- `500 Internal Server Error` — Unexpected server error

---

## Swagger UI

Interactive API documentation with request/response examples:
**http://localhost:8000/docs**
