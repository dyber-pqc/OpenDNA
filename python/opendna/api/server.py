"""FastAPI server for OpenDNA v0.2."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, is_dataclass
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

app = FastAPI(
    title="OpenDNA API",
    description="The People's Protein Engineering Platform",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=4)
jobs: dict[str, dict] = {}
result_cache: dict[str, dict] = {}  # hash -> result


def _to_dict(obj):
    """Recursively convert dataclasses to dicts."""
    if is_dataclass(obj):
        return {k: _to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_dict(v) for v in obj]
    return obj


# =====================================================
# Request models
# =====================================================

class FoldRequest(BaseModel):
    sequence: str
    method: str = "auto"
    device: Optional[str] = None


class DesignRequest(BaseModel):
    pdb_string: str
    num_candidates: int = Field(10, ge=1, le=100)
    temperature: float = Field(0.1, ge=0.01, le=2.0)
    device: Optional[str] = None


class IterativeRequest(BaseModel):
    sequence: str
    n_rounds: int = Field(5, ge=1, le=20)
    candidates_per_round: int = Field(5, ge=1, le=20)
    temperature: float = 0.2


class EvaluateRequest(BaseModel):
    sequence: str


class MutateRequest(BaseModel):
    sequence: str
    mutation: str


class ChatRequest(BaseModel):
    message: str


class AnalyzeRequest(BaseModel):
    sequence: str
    pdb_string: Optional[str] = None


class ExplainRequest(BaseModel):
    sequence: str
    pdb_string: Optional[str] = None


class FetchUniProtRequest(BaseModel):
    accession: str


class FetchPdbRequest(BaseModel):
    pdb_id: str


class CompareRequest(BaseModel):
    pdb_a: str
    pdb_b: str


class DockRequest(BaseModel):
    pdb_string: str
    ligand_smiles: str


class ScreenRequest(BaseModel):
    pdb_string: str
    ligands: list[str]


class MdRequest(BaseModel):
    pdb_string: str
    duration_ps: float = 100


class CostRequest(BaseModel):
    sequence: str


class ProjectSaveRequest(BaseModel):
    name: str
    data: dict


class ProjectLoadRequest(BaseModel):
    name: str


class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: float = 0.0
    result: Optional[dict] = None
    error: Optional[str] = None


# =====================================================
# Health & meta
# =====================================================

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0", "engines": [
        "fold", "design", "iterative_design", "evaluate", "analyze", "explain",
        "mutate", "compare", "dock", "screen", "md", "disorder",
    ]}


@app.get("/v1/hardware")
async def get_hardware():
    from opendna.hardware.detect import detect_hardware
    hw = detect_hardware()
    return {
        "cpu": hw.cpu_name,
        "cores": hw.cpu_cores,
        "ram_gb": round(hw.total_ram_gb, 1),
        "gpu": (
            {"name": hw.gpu.name, "vram_gb": hw.gpu.vram_gb, "backend": hw.gpu.backend.value}
            if hw.gpu else None
        ),
        "recommended_tier": hw.recommended_tier.value,
        "recommended_backend": hw.recommended_backend.value,
        "recommended_precision": hw.recommended_precision.value,
    }


# =====================================================
# Folding & design
# =====================================================

@app.post("/v1/fold", response_model=JobResponse)
async def submit_fold(request: FoldRequest):
    cache_key = f"fold:{request.sequence}:{request.method}"
    if cache_key in result_cache:
        job_id = str(uuid.uuid4())[:8]
        jobs[job_id] = {
            "status": "completed",
            "progress": 1.0,
            "result": result_cache[cache_key],
            "error": None,
            "type": "fold",
            "started_at": time.time(),
        }
        return JobResponse(job_id=job_id, status="completed", progress=1.0, result=result_cache[cache_key])

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "running", "progress": 0.0, "result": None, "error": None,
        "type": "fold", "started_at": time.time(),
    }
    asyncio.get_event_loop().run_in_executor(
        executor, _run_fold, job_id, request.sequence, request.method, request.device, cache_key
    )
    return JobResponse(job_id=job_id, status="running")


@app.post("/v1/design", response_model=JobResponse)
async def submit_design(request: DesignRequest):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "running", "progress": 0.0, "result": None, "error": None,
        "type": "design", "started_at": time.time(),
    }
    asyncio.get_event_loop().run_in_executor(
        executor, _run_design, job_id, request.pdb_string, request.num_candidates,
        request.temperature, request.device,
    )
    return JobResponse(job_id=job_id, status="running")


@app.post("/v1/iterative_design", response_model=JobResponse)
async def submit_iterative_design(request: IterativeRequest):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "running", "progress": 0.0, "result": None, "error": None,
        "type": "iterative_design", "started_at": time.time(),
    }
    asyncio.get_event_loop().run_in_executor(
        executor, _run_iterative, job_id, request.sequence, request.n_rounds,
        request.candidates_per_round, request.temperature,
    )
    return JobResponse(job_id=job_id, status="running")


# =====================================================
# Analysis (instant - no background job needed)
# =====================================================

@app.post("/v1/analyze")
async def analyze(request: AnalyzeRequest):
    """Run the full Schrödinger-equivalent analysis suite."""
    from opendna.engines.analysis import (
        compute_properties, hydropathy_profile, lipinski_rule_of_five,
        secondary_structure, secondary_structure_summary, radius_of_gyration,
        compute_dihedrals, sasa_estimate, detect_pockets,
    )
    from opendna.engines.disorder import predict_disorder
    from opendna.engines.predictors import (
        predict_transmembrane, predict_signal_peptide, predict_aggregation,
        predict_phosphorylation, predict_glycosylation,
    )
    from opendna.engines.bonds import detect_bonds
    from opendna.models.protein import Structure

    seq = request.sequence.upper().strip()
    properties = _to_dict(compute_properties(seq))
    lipinski = _to_dict(lipinski_rule_of_five(seq))
    hydro = hydropathy_profile(seq)
    disorder = predict_disorder(seq)
    transmembrane = predict_transmembrane(seq)
    signal_peptide = predict_signal_peptide(seq)
    aggregation = predict_aggregation(seq)
    phospho = predict_phosphorylation(seq)
    glyco = predict_glycosylation(seq)

    structure_analysis = None
    if request.pdb_string:
        try:
            structure = Structure.from_pdb_string(request.pdb_string)
            ss = secondary_structure(structure)
            ss_summary = secondary_structure_summary(ss)
            angles = compute_dihedrals(structure)
            rg = radius_of_gyration(structure)
            sasa = sasa_estimate(structure)
            pockets = detect_pockets(structure)
            bonds = detect_bonds(structure)
            structure_analysis = {
                "secondary_structure": ss,
                **ss_summary,
                "ramachandran": [
                    {"phi": a[0], "psi": a[1]} for a in angles
                ],
                "radius_of_gyration": rg,
                "sasa_estimate": sasa,
                "pockets": pockets,
                "num_atoms": structure.num_atoms,
                "bonds": bonds,
            }
        except Exception as e:
            structure_analysis = {"error": str(e)}

    return {
        "properties": properties,
        "lipinski": lipinski,
        "hydropathy_profile": hydro,
        "disorder": disorder,
        "transmembrane": transmembrane,
        "signal_peptide": signal_peptide,
        "aggregation": aggregation,
        "phosphorylation": phospho,
        "glycosylation": glyco,
        "structure": structure_analysis,
    }


class AlignRequest(BaseModel):
    seq1: str
    seq2: str


@app.post("/v1/align")
async def align(request: AlignRequest):
    from opendna.engines.alignment import needleman_wunsch
    return needleman_wunsch(request.seq1.upper().strip(), request.seq2.upper().strip())


class DdgRequest(BaseModel):
    sequence: str
    mutation: str


@app.post("/v1/predict_ddg")
async def predict_ddg_endpoint(request: DdgRequest):
    from opendna.engines.predictors import predict_ddg
    return predict_ddg(request.sequence, request.mutation)


@app.post("/v1/evaluate")
async def evaluate_protein(request: EvaluateRequest):
    from opendna.engines.scoring import evaluate
    result = evaluate(request.sequence)
    return {
        "overall": result.overall,
        "confidence": result.confidence,
        "breakdown": _to_dict(result.breakdown),
        "summary": result.summary,
        "recommendations": result.recommendations,
    }


@app.post("/v1/explain")
async def explain(request: ExplainRequest):
    from opendna.engines.analysis import compute_properties, secondary_structure, secondary_structure_summary
    from opendna.engines.scoring import evaluate
    from opendna.engines.explain import explain_protein
    from opendna.models.protein import Structure

    properties = _to_dict(compute_properties(request.sequence))
    score_obj = evaluate(request.sequence)
    score = {
        "overall": score_obj.overall,
        "summary": score_obj.summary,
    }

    structure_info = None
    if request.pdb_string:
        try:
            structure = Structure.from_pdb_string(request.pdb_string)
            ss = secondary_structure(structure)
            structure_info = {
                "mean_confidence": structure.mean_confidence,
                **secondary_structure_summary(ss),
            }
        except Exception:
            pass

    text = explain_protein(request.sequence, properties, score, structure_info)
    return {"explanation": text}


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


# =====================================================
# Comparison
# =====================================================

@app.post("/v1/compare")
async def compare_structures_endpoint(request: CompareRequest):
    from opendna.engines.analysis import compare_structures
    from opendna.models.protein import Structure
    s1 = Structure.from_pdb_string(request.pdb_a)
    s2 = Structure.from_pdb_string(request.pdb_b)
    return compare_structures(s1, s2)


# =====================================================
# Docking
# =====================================================

@app.post("/v1/dock")
async def dock_endpoint(request: DockRequest):
    from opendna.engines.docking import dock_ligand
    result = dock_ligand(request.pdb_string, request.ligand_smiles)
    return _to_dict(result)


@app.post("/v1/screen")
async def screen_endpoint(request: ScreenRequest):
    from opendna.engines.docking import virtual_screen
    return {"results": virtual_screen(request.pdb_string, request.ligands)}


# =====================================================
# Molecular dynamics
# =====================================================

@app.post("/v1/md", response_model=JobResponse)
async def md_endpoint(request: MdRequest):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "running", "progress": 0.0, "result": None, "error": None,
        "type": "md", "started_at": time.time(),
    }
    asyncio.get_event_loop().run_in_executor(
        executor, _run_md, job_id, request.pdb_string, request.duration_ps
    )
    return JobResponse(job_id=job_id, status="running")


# =====================================================
# Data sources
# =====================================================

@app.post("/v1/fetch_uniprot")
async def fetch_uniprot_endpoint(request: FetchUniProtRequest):
    """Fetch UniProt entry AND try AlphaFold DB structure in one call.

    Returns the sequence info plus a `pdb_string` and `structure_source` if
    a high-quality AlphaFold prediction exists for this UniProt entry.
    """
    from opendna.data.sources import fetch_uniprot, fetch_alphafold, FAMOUS_PROTEINS
    accession = request.accession.strip()
    # Allow famous-name shortcuts
    if accession.lower() in FAMOUS_PROTEINS:
        accession = FAMOUS_PROTEINS[accession.lower()]
    entry = fetch_uniprot(accession)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"UniProt entry not found: {accession}")

    # Try to fetch AlphaFold DB structure for this entry
    pdb_string = fetch_alphafold(accession)
    structure_source = "alphafold" if pdb_string else None

    result = _to_dict(entry)
    result["pdb_string"] = pdb_string
    result["structure_source"] = structure_source
    return result


@app.post("/v1/fetch_pdb")
async def fetch_pdb_endpoint(request: FetchPdbRequest):
    from opendna.data.sources import fetch_pdb
    pdb = fetch_pdb(request.pdb_id)
    if pdb is None:
        raise HTTPException(status_code=404, detail=f"PDB entry not found: {request.pdb_id}")
    return {"pdb_id": request.pdb_id.upper(), "pdb_string": pdb}


@app.get("/v1/famous_proteins")
async def famous_proteins():
    from opendna.data.sources import FAMOUS_PROTEINS
    return FAMOUS_PROTEINS


# =====================================================
# Cost & carbon
# =====================================================

@app.post("/v1/cost")
async def cost_endpoint(request: CostRequest):
    from opendna.data.synthesis import estimate_synthesis_cost, estimate_carbon, estimate_compute_time
    cost = estimate_synthesis_cost(request.sequence)
    duration = estimate_compute_time(len(request.sequence), "fold", "cpu")
    carbon_cpu = estimate_carbon("fold", duration, "cpu")
    carbon_gpu = estimate_carbon("fold", estimate_compute_time(len(request.sequence), "fold", "cuda"), "cuda")
    return {
        "synthesis": _to_dict(cost),
        "compute_carbon_cpu": _to_dict(carbon_cpu),
        "compute_carbon_gpu": _to_dict(carbon_gpu),
    }


# =====================================================
# Project workspace
# =====================================================

@app.post("/v1/projects/save")
async def project_save(request: ProjectSaveRequest):
    from opendna.storage.projects import save_project
    path = save_project(request.name, request.data)
    return {"name": request.name, "path": path}


@app.post("/v1/projects/load")
async def project_load(request: ProjectLoadRequest):
    from opendna.storage.projects import load_project
    data = load_project(request.name)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {request.name}")
    return data


@app.get("/v1/projects")
async def projects_list():
    from opendna.storage.projects import list_projects
    return {"projects": list_projects()}


@app.delete("/v1/projects/{name}")
async def project_delete(name: str):
    from opendna.storage.projects import delete_project
    if not delete_project(name):
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": name}


# =====================================================
# Job status
# =====================================================

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


@app.get("/v1/jobs")
async def list_jobs():
    return {
        "jobs": [
            {
                "id": k,
                "type": v.get("type"),
                "status": v["status"],
                "progress": v["progress"],
                "started_at": v.get("started_at"),
            }
            for k, v in sorted(jobs.items(), key=lambda x: -x[1].get("started_at", 0))
        ][:50]
    }


# =====================================================
# Background runners
# =====================================================

def _run_fold(job_id: str, sequence: str, method: str, device: Optional[str], cache_key: str):
    try:
        from opendna.engines.folding import fold
        def on_progress(stage: str, frac: float):
            jobs[job_id]["progress"] = frac
        result = fold(sequence, method=method, device=device, on_progress=on_progress)
        out = {
            "pdb": result.pdb_string,
            "mean_confidence": result.mean_confidence,
            "method": result.method,
            "explanation": result.explanation,
        }
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["result"] = out
        result_cache[cache_key] = out
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


def _run_design(job_id, pdb_string, n, temp, device):
    try:
        from opendna.engines.design import DesignConstraints, design
        def on_progress(stage: str, frac: float):
            jobs[job_id]["progress"] = frac
        constraints = DesignConstraints(num_candidates=n, temperature=temp)
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


def _run_iterative(job_id, sequence, n_rounds, n_per_round, temp):
    try:
        from opendna.engines.iterative import iterative_design
        def on_progress(stage: str, frac: float):
            jobs[job_id]["progress"] = frac
        result = iterative_design(
            sequence, n_rounds=n_rounds, candidates_per_round=n_per_round,
            temperature=temp, on_progress=on_progress,
        )
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["result"] = {
            "initial_sequence": result.initial_sequence,
            "final_sequence": result.final_sequence,
            "initial_score": result.initial_score,
            "final_score": result.final_score,
            "improvement": result.improvement,
            "history": result.history,
            "rounds": [
                {
                    "round": r.round,
                    "sequence": r.sequence,
                    "score": r.score,
                    "confidence": r.confidence,
                    "pdb": r.pdb,
                }
                for r in result.rounds
            ],
        }
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


def _run_md(job_id, pdb_string, duration_ps):
    try:
        from opendna.engines.dynamics import quick_md
        def on_progress(stage: str, frac: float):
            jobs[job_id]["progress"] = frac
        result = quick_md(pdb_string, duration_ps=duration_ps, on_progress=on_progress)
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["result"] = _to_dict(result)
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


def start_server(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()
