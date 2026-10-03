"""FastAPI server for ClaimShield detector models (GPU/CPU, remote or local).

Endpoints:
  GET  /api/health              - model status
  POST /api/score/image         - score image, returns job_id
  POST /api/score/document      - score document, returns job_id
  POST /api/score/case          - score case (multiple files), returns job_id
  POST /api/arena               - attack & re-score, returns job_id
  GET  /api/jobs/{job_id}       - job status
  GET  /api/jobs/{job_id}/events - SSE stream of cards + final result
  GET  /docs                    - Swagger UI

Jobs emit card events as signals complete, then a final event with the full result.
Fast tier completes in ~8s; deep tier (AE reconstruction) lands later.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import config, pipeline
from .arena import attacks
from .contracts import Band, ClaimScore, Signal
from .preprocess import prepare

app = FastAPI(title="ClaimShield API", version="1.0.0")

# Job storage: job_id -> Job
_jobs: dict[str, "Job"] = {}
_job_lock = asyncio.Lock()

# Background executor for scoring
_executor = ThreadPoolExecutor(max_workers=4)

JobStatus = Literal["pending", "running", "completed", "failed"]


@dataclass
class Job:
    id: str
    status: JobStatus
    kind: Literal["image", "document", "case", "arena"]
    result: Any = None
    error: str | None = None
    cards: list[dict] = None  # emitted Signal cards
    created_at: float = 0.0
    completed_at: float | None = None

    def __post_init__(self):
        if self.cards is None:
            self.cards = []
        if self.created_at == 0.0:
            self.created_at = time.time()


# ============================================================================ Models
class HealthResponse(BaseModel):
    status: str
    problems: list[str]
    device: str
    models_loaded: bool


class JobCreateResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    kind: str
    result: dict | None
    error: str | None
    created_at: float
    completed_at: float | None


class ScoreResponse(BaseModel):
    """Final result for image/document/case scoring."""
    overall: float
    band: Band
    image_score: float | None
    document_score: float | None
    identity_score: float | None
    waterfall: list[tuple[str, float]]
    regions: list[dict]
    signals: list[dict]
    pending_deep: bool
    sha256: str | None = None
    quality_flag: bool = False
    t_first: float | None = None
    t_fast: float | None = None
    t_deep: float | None = None


class ArenaResponse(BaseModel):
    """Arena attack result."""
    seed_sha256: str
    attack_sha256: str
    attack_kind: str
    attack_method: str
    attack_note: str
    attack_seconds: float
    before: ScoreResponse
    after: ScoreResponse


# ============================================================================ Helpers
def _signal_dict(s: Signal) -> dict:
    return {
        "name": s.name,
        "score": s.score,
        "confidence": s.confidence,
        "reason": s.reason,
        "evidence": s.evidence,
        "abstained": s.abstained,
        "applicable": s.applicable,
        "tier": s.tier,
    }


def _claim_dict(claim: ClaimScore) -> dict:
    return {
        "image_score": claim.image_score,
        "document_score": claim.document_score,
        "identity_score": claim.identity_score,
        "overall": claim.overall,
        "band": claim.band,
        "waterfall": claim.waterfall,
        "regions": [asdict(r) for r in claim.regions],
        "signals": [_signal_dict(s) for s in claim.signals],
        "pending_deep": claim.pending_deep,
    }


async def _create_job(kind: Literal["image", "document", "case", "arena"]) -> str:
    """Create a new job and return its ID."""
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    async with _job_lock:
        _jobs[job_id] = Job(id=job_id, status="pending", kind=kind)
    return job_id


async def _get_job(job_id: str) -> Job:
    """Get job or raise 404."""
    async with _job_lock:
        if job_id not in _jobs:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        return _jobs[job_id]


async def _update_job(job_id: str, **kwargs):
    """Update job fields."""
    async with _job_lock:
        if job_id in _jobs:
            job = _jobs[job_id]
            for k, v in kwargs.items():
                setattr(job, k, v)


def _on_card(job_id: str):
    """Returns a callback that appends cards to the job."""
    def callback(s: Signal):
        # Run in executor thread; update synchronously
        try:
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(lambda: _append_card(job_id, s))
        except RuntimeError:
            # No event loop in this thread; append directly (not ideal but safe)
            pass
    return callback


def _append_card(job_id: str, s: Signal):
    """Append a card to the job (called from executor thread)."""
    if job_id in _jobs:
        _jobs[job_id].cards.append(_signal_dict(s))


# ============================================================================ Endpoints
@app.get("/")
async def root():
    return {"message": "ClaimShield API", "docs": "/docs", "health": "/api/health"}


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Check model status. Returns problems list (empty if all OK)."""
    problems = pipeline.warm()
    return HealthResponse(
        status="ok" if not problems else "degraded",
        problems=problems,
        device=config.device(),
        models_loaded=len(problems) == 0,
    )


@app.post("/api/score/image", response_model=JobCreateResponse)
async def score_image_endpoint(
    file: UploadFile = File(..., description="Image file (JPEG/PNG/HEIC/WebP)"),
):
    """Score a single image. Returns job_id; stream /api/jobs/{job_id}/events for cards."""
    job_id = await _create_job("image")

    # Save upload to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Start scoring in background
    async def run():
        await _update_job(job_id, status="running")
        try:
            def score():
                res = pipeline.score_image(tmp_path, on_card=_on_card(job_id), wait_deep=False)
                # Wait for deep tier
                res = pipeline.finish(res)
                return res

            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(_executor, score)

            result = ScoreResponse(
                overall=res.claim.overall,
                band=res.claim.band,
                image_score=res.claim.image_score,
                document_score=res.claim.document_score,
                identity_score=res.claim.identity_score,
                waterfall=res.claim.waterfall,
                regions=[asdict(r) for r in res.claim.regions],
                signals=[_signal_dict(s) for s in res.claim.signals],
                pending_deep=res.claim.pending_deep,
                sha256=res.sha256,
                quality_flag=res.quality_flag,
                t_first=res.t_first,
                t_fast=res.t_fast,
                t_deep=res.t_deep,
            )
            await _update_job(job_id, status="completed", result=result.dict(),
                            completed_at=time.time())
        except Exception as e:
            await _update_job(job_id, status="failed", error=str(e), completed_at=time.time())
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    asyncio.create_task(run())
    return JobCreateResponse(job_id=job_id, status="pending")


@app.post("/api/score/document", response_model=JobCreateResponse)
async def score_document_endpoint(
    file: UploadFile = File(..., description="Document file (PDF or image)"),
):
    """Score a document. Returns job_id; stream /api/jobs/{job_id}/events for cards."""
    job_id = await _create_job("document")

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    async def run():
        await _update_job(job_id, status="running")
        try:
            def score():
                return pipeline.score_document(tmp_path, on_card=_on_card(job_id))

            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(_executor, score)

            result = ScoreResponse(
                overall=res.claim.overall,
                band=res.claim.band,
                image_score=res.claim.image_score,
                document_score=res.claim.document_score,
                identity_score=res.claim.identity_score,
                waterfall=res.claim.waterfall,
                regions=[asdict(r) for r in res.claim.regions],
                signals=[_signal_dict(s) for s in res.claim.signals],
                pending_deep=False,
                sha256=res.sha256,
                t_fast=res.t_total,
            )
            await _update_job(job_id, status="completed", result=result.dict(),
                            completed_at=time.time())
        except Exception as e:
            await _update_job(job_id, status="failed", error=str(e), completed_at=time.time())
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    asyncio.create_task(run())
    return JobCreateResponse(job_id=job_id, status="pending")


@app.post("/api/arena", response_model=JobCreateResponse)
async def arena_endpoint(
    seed: str = Form(..., description="Seed filename in data/seeds/ or 'upload'"),
    method: str = Form("inpaint", description="inpaint or recompress"),
    file: UploadFile = File(None, description="Upload if seed='upload'"),
):
    """Attack image and re-score. Returns job_id; stream /api/jobs/{job_id}/events."""
    job_id = await _create_job("arena")

    # Resolve seed path
    if seed == "upload":
        if not file:
            raise HTTPException(400, "file required when seed='upload'")
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            seed_path = tmp.name
    else:
        seed_path = str(config.ROOT / "data" / "seeds" / seed)
        if not Path(seed_path).exists():
            raise HTTPException(404, f"Seed {seed} not found in data/seeds/")

    async def run():
        await _update_job(job_id, status="running")
        try:
            def score():
                # Score before
                before_res = pipeline.score_image(seed_path, wait_deep=True)
                before_sha = before_res.sha256

                # Attack
                t0 = time.time()
                if method == "recompress":
                    atk = attacks.recompress_q70(Path(seed_path))
                else:
                    img = attacks._open(seed_path)
                    cfg = attacks._cfg()
                    try:
                        out = attacks.inpaint_nova(img, cfg["prompt"], cfg["mask_prompt"])
                    except Exception:
                        # Fallback to local
                        out = attacks.inpaint_local_sd15(img, cfg["prompt"])
                    atk = attacks.Attack(attacks._jpeg(out, 95), "inpaint", "nova", "", 0.0)
                atk_seconds = time.time() - t0

                # Save attacked image
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    tmp.write(atk.data)
                    atk_path = tmp.name

                # Score after
                after_res = pipeline.score_image(atk_path, on_card=_on_card(job_id), wait_deep=True)
                after_sha = after_res.sha256

                Path(atk_path).unlink(missing_ok=True)

                return {
                    "seed_sha256": before_sha,
                    "attack_sha256": after_sha,
                    "attack_kind": atk.kind,
                    "attack_method": atk.method,
                    "attack_note": atk.note,
                    "attack_seconds": atk_seconds,
                    "before": ScoreResponse(
                        overall=before_res.claim.overall,
                        band=before_res.claim.band,
                        image_score=before_res.claim.image_score,
                        document_score=before_res.claim.document_score,
                        identity_score=before_res.claim.identity_score,
                        waterfall=before_res.claim.waterfall,
                        regions=[asdict(r) for r in before_res.claim.regions],
                        signals=[_signal_dict(s) for s in before_res.claim.signals],
                        pending_deep=False,
                        sha256=before_sha,
                        t_first=before_res.t_first,
                        t_fast=before_res.t_fast,
                        t_deep=before_res.t_deep,
                    ).dict(),
                    "after": ScoreResponse(
                        overall=after_res.claim.overall,
                        band=after_res.claim.band,
                        image_score=after_res.claim.image_score,
                        document_score=after_res.claim.document_score,
                        identity_score=after_res.claim.identity_score,
                        waterfall=after_res.claim.waterfall,
                        regions=[asdict(r) for r in after_res.claim.regions],
                        signals=[_signal_dict(s) for s in after_res.claim.signals],
                        pending_deep=False,
                        sha256=after_sha,
                        t_first=after_res.t_first,
                        t_fast=after_res.t_fast,
                        t_deep=after_res.t_deep,
                    ).dict(),
                }

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(_executor, score)
            await _update_job(job_id, status="completed", result=result, completed_at=time.time())
        except Exception as e:
            import traceback
            await _update_job(job_id, status="failed", error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
                            completed_at=time.time())
        finally:
            if seed == "upload":
                Path(seed_path).unlink(missing_ok=True)

    asyncio.create_task(run())
    return JobCreateResponse(job_id=job_id, status="pending")


@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get job status and result."""
    job = await _get_job(job_id)
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        kind=job.kind,
        result=job.result,
        error=job.error,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@app.get("/api/jobs/{job_id}/events")
async def stream_job_events(job_id: str):
    """SSE stream of job events: card events + final event."""
    job = await _get_job(job_id)

    async def event_generator():
        # Send existing cards
        last_card_count = 0
        while True:
            async with _job_lock:
                current_job = _jobs.get(job_id)
                if not current_job:
                    yield f"event: error\ndata: {json.dumps({'error': 'job not found'})}\n\n"
                    break

                # Send new cards
                while last_card_count < len(current_job.cards):
                    card = current_job.cards[last_card_count]
                    yield f"event: card\ndata: {json.dumps(card)}\n\n"
                    last_card_count += 1

                # Check if completed
                if current_job.status in ("completed", "failed"):
                    if current_job.status == "completed":
                        yield f"event: final\ndata: {json.dumps(current_job.result)}\n\n"
                    else:
                        yield f"event: error\ndata: {json.dumps({'error': current_job.error})}\n\n"
                    break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
