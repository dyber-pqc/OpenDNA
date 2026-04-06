"""FastAPI server for OpenDNA."""

from __future__ import annotations

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

app = FastAPI(
    title="OpenDNA API",
    description="The People's Protein Engineering Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool for compute-heavy tasks
executor = ThreadPoolExecutor(max_workers=2)

# In-memory job store (replace with DB in production)
jobs: dict[str, dict] = {}


# --- Request/Response Models ---

class FoldRequest(BaseModel):
    sequence: str = Field(..., description="Amino acid sequence")
    method: str = Field("auto", description="Folding method")
    device: Optional[str] = Field(None, description="Compute device")


class DesignRequest(BaseModel):
    pdb_string: str = Field(..., description="Input PDB structure")
    num_candidates: int = Field(10, ge=1, le=100)
    temperature: float = Field(0.1, ge=0.01, le=2.0)
    device: Optional[str] = None


class EvaluateRequest(BaseModel):
    sequence: str = Field(..., description="Amino acid sequence")


class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: float = 0.0
    result: Optional[dict] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str


# --- Endpoints ---

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", version="0.1.0")


@app.get("/v1/hardware")
async def get_hardware():
    from opendna.hardware.detect import detect_hardware
    hw = detect_hardware()
    return {
        "cpu": hw.cpu_name,
        "cores": hw.cpu_cores,
        "ram_gb": hw.total_ram_gb,
        "gpu": {"name": hw.gpu.name, "vram_gb": hw.gpu.vram_gb, "backend": hw.gpu.backend.value} if hw.gpu else None,
        "recommended_tier": hw.recommended_tier.value,
        "recommended_backend": hw.recommended_backend.value,
        "recommended_precision": hw.recommended_precision.value,
    }


@app.post("/v1/fold", response_model=JobResponse)
async def submit_fold(request: FoldRequest):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "running", "progress": 0.0, "result": None, "error": None}

    asyncio.get_event_loop().run_in_executor(
        executor, _run_fold, job_id, request.sequence, request.method, request.device
    )

    return JobResponse(job_id=job_id, status="running")


@app.post("/v1/design", response_model=JobResponse)
async def submit_design(request: DesignRequest):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "running", "progress": 0.0, "result": None, "error": None}

    asyncio.get_event_loop().run_in_executor(
        executor, _run_design, job_id, request.pdb_string, request.num_candidates, request.temperature, request.device
    )

    return JobResponse(job_id=job_id, status="running")


class MutateRequest(BaseModel):
    sequence: str
    mutation: str  # e.g. "G45D"


class ChatRequest(BaseModel):
    message: str


@app.post("/v1/mutate")
async def mutate_protein(request: MutateRequest):
    from opendna.engines.design import apply_mutation
    try:
        new_seq = apply_mutation(request.sequence, request.mutation)
        return {
            "original": request.sequence,
            "mutated": new_seq,
            "mutation": request.mutation.upper(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/chat")
async def chat(request: ChatRequest):
    from opendna.engines.nlu import parse_intent
    intent = parse_intent(request.message)
    return {
        "action": intent.action,
        "sequence": intent.sequence,
        "mutation": intent.mutation,
        "response": intent.response,
    }


@app.post("/v1/evaluate")
async def evaluate_protein(request: EvaluateRequest):
    from opendna.engines.scoring import evaluate

    result = evaluate(request.sequence)
    return {
        "overall": result.overall,
        "confidence": result.confidence,
        "breakdown": {
            "stability": result.breakdown.stability,
            "solubility": result.breakdown.solubility,
            "immunogenicity": result.breakdown.immunogenicity,
            "developability": result.breakdown.developability,
            "novelty": result.breakdown.novelty,
        },
        "summary": result.summary,
        "recommendations": result.recommendations,
    }


@app.get("/v1/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    return JobResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        result=job["result"],
        error=job["error"],
    )


@app.get("/v1/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        import json
        while True:
            job = jobs.get(job_id)
            if job is None:
                break
            yield {
                "event": "progress",
                "data": json.dumps({
                    "status": job["status"],
                    "progress": job["progress"],
                }),
            }
            if job["status"] in ("completed", "failed"):
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "status": job["status"],
                        "result": job["result"],
                        "error": job["error"],
                    }),
                }
                break
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())


# --- Background job runners ---

def _run_fold(job_id: str, sequence: str, method: str, device: Optional[str]):
    try:
        from opendna.engines.folding import fold

        def on_progress(stage: str, frac: float):
            jobs[job_id]["progress"] = frac

        result = fold(sequence, method=method, device=device, on_progress=on_progress)
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["result"] = {
            "pdb": result.pdb_string,
            "mean_confidence": result.mean_confidence,
            "method": result.method,
            "explanation": result.explanation,
        }
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


def _run_design(job_id: str, pdb_string: str, num_candidates: int, temperature: float, device: Optional[str]):
    try:
        from opendna.engines.design import DesignConstraints, design

        def on_progress(stage: str, frac: float):
            jobs[job_id]["progress"] = frac

        constraints = DesignConstraints(num_candidates=num_candidates, temperature=temperature)
        result = design(pdb_string, constraints=constraints, device=device, on_progress=on_progress)
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["result"] = {
            "candidates": [
                {"rank": c.rank, "sequence": str(c.sequence), "score": c.score, "recovery": c.recovery}
                for c in result.candidates
            ],
            "method": result.method,
            "explanation": result.explanation,
        }
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


def start_server(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()
