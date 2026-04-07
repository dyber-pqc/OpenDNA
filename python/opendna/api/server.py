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


# Friendly error handling: catch all exceptions and return user-readable JSON.
from fastapi import Request
from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
async def opendna_exception_handler(request: Request, exc: Exception):
    from opendna.exceptions import to_friendly
    # Don't override HTTPException - let FastAPI handle it
    if isinstance(exc, HTTPException):
        raise exc
    payload = to_friendly(exc)
    return JSONResponse(status_code=500, content=payload)

executor = ThreadPoolExecutor(max_workers=4)


class HybridJobStore:
    """Wraps SQLite JobStore with an in-memory cache for fast UI polling.

    On startup, marks any "running" jobs as failed (server restart killed them).
    All API code uses this with a dict-like interface for backwards compat.
    """

    def __init__(self):
        from opendna.storage.jobs import get_job_store
        self._mem: dict[str, dict] = {}
        self._db = get_job_store()
        # Mark stale running jobs as failed
        for j in self._db.list_recent(limit=200):
            if j["status"] == "running":
                self._db.update(j["id"], status="failed", error="Server restarted while job was running")

    def __contains__(self, job_id: str) -> bool:
        return job_id in self._mem or self._db.get(job_id) is not None

    def __getitem__(self, job_id: str) -> dict:
        if job_id in self._mem:
            return self._mem[job_id]
        j = self._db.get(job_id)
        if j is None:
            raise KeyError(job_id)
        self._mem[job_id] = j
        return j

    def __setitem__(self, job_id: str, data: dict) -> None:
        self._mem[job_id] = data
        if self._db.get(job_id) is None:
            self._db.create(job_id, data.get("type", "unknown"))
        self._db.update(
            job_id,
            status=data.get("status"),
            progress=data.get("progress"),
            result=data.get("result") if data.get("status") in ("completed", "failed") else None,
            error=data.get("error"),
        )

    def items(self):
        # Combine memory and DB recent items
        seen = set()
        for k, v in self._mem.items():
            seen.add(k)
            yield k, v
        for j in self._db.list_recent(limit=200):
            if j["id"] not in seen:
                yield j["id"], j

    def list_recent(self, limit: int = 50) -> list[dict]:
        return self._db.list_recent(limit)

    def cancel(self, job_id: str) -> bool:
        if job_id in self._mem:
            self._mem[job_id]["status"] = "cancelled"
        existing = self._db.get(job_id)
        if existing and existing["status"] == "running":
            self._db.update(job_id, status="cancelled", error="Cancelled by user")
            return True
        return False


jobs = HybridJobStore()
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


# =====================================================
# v0.3 - 9 NEW ANALYSES
# =====================================================

class ConservationRequest(BaseModel):
    sequence: str


@app.post("/v1/conservation")
async def conservation_endpoint(request: ConservationRequest):
    from opendna.engines.conservation import analyze_conservation
    return _to_dict(analyze_conservation(request.sequence))


class ConstrainedDesignRequest(BaseModel):
    pdb_string: str
    fixed_positions: list[int]
    num_candidates: int = 10
    temperature: float = 0.1


@app.post("/v1/constrained_design", response_model=JobResponse)
async def constrained_design_endpoint(request: ConstrainedDesignRequest):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "running", "progress": 0.0, "result": None, "error": None,
        "type": "constrained_design", "started_at": time.time(),
    }
    asyncio.get_event_loop().run_in_executor(
        executor, _run_constrained_design, job_id, request.pdb_string,
        request.fixed_positions, request.num_candidates, request.temperature,
    )
    return JobResponse(job_id=job_id, status="running")


class MultiObjectiveRequest(BaseModel):
    sequence: str
    objectives: list[str]
    num_candidates: int = 20


@app.post("/v1/multi_objective_design", response_model=JobResponse)
async def multi_objective_endpoint(request: MultiObjectiveRequest):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "running", "progress": 0.0, "result": None, "error": None,
        "type": "multi_objective", "started_at": time.time(),
    }
    asyncio.get_event_loop().run_in_executor(
        executor, _run_multi_objective, job_id, request.sequence,
        request.objectives, request.num_candidates,
    )
    return JobResponse(job_id=job_id, status="running")


class PharmacophoreRequest(BaseModel):
    pdb_string: str
    pocket_residues: Optional[list[int]] = None


@app.post("/v1/pharmacophore")
async def pharmacophore_endpoint(request: PharmacophoreRequest):
    from opendna.engines.pharmacophore import extract_pharmacophore
    from opendna.models.protein import Structure
    structure = Structure.from_pdb_string(request.pdb_string)
    result = extract_pharmacophore(structure, request.pocket_residues)
    return _to_dict(result)


class AntibodyRequest(BaseModel):
    sequence: str
    scheme: str = "kabat"


@app.post("/v1/antibody_numbering")
async def antibody_endpoint(request: AntibodyRequest):
    from opendna.engines.antibody import find_cdrs
    return find_cdrs(request.sequence, request.scheme)


class PdbStringRequest(BaseModel):
    pdb_string: str


@app.post("/v1/predict_pka")
async def pka_endpoint(request: PdbStringRequest):
    from opendna.engines.pka import predict_pka
    from opendna.models.protein import Structure
    structure = Structure.from_pdb_string(request.pdb_string)
    return predict_pka(structure)


@app.post("/v1/validate_structure")
async def validate_endpoint(request: PdbStringRequest):
    from opendna.engines.validation import validate_structure
    from opendna.models.protein import Structure
    structure = Structure.from_pdb_string(request.pdb_string)
    return validate_structure(structure)


class MmgbsaRequest(BaseModel):
    pdb_string: str
    ligand_smiles: str
    pocket_residue: Optional[int] = None


@app.post("/v1/mmgbsa")
async def mmgbsa_endpoint(request: MmgbsaRequest):
    from opendna.engines.mmgbsa import estimate_binding_energy
    from opendna.models.protein import Structure
    structure = Structure.from_pdb_string(request.pdb_string)
    result = estimate_binding_energy(structure, request.ligand_smiles, request.pocket_residue)
    return _to_dict(result)


class QsarRequest(BaseModel):
    sequence: str


@app.post("/v1/qsar")
async def qsar_endpoint(request: QsarRequest):
    from opendna.engines.qsar import compute_qsar_descriptors
    return compute_qsar_descriptors(request.sequence)


# =====================================================
# v0.3 - LLM AGENT
# =====================================================

class AgentGoalRequest(BaseModel):
    goal: str
    max_steps: int = 8


@app.post("/v1/agent")
async def agent_endpoint(request: AgentGoalRequest):
    from opendna.llm.agent import run_agent
    result = run_agent(request.goal, max_steps=request.max_steps)
    return {
        "goal": result.goal,
        "steps": [
            {
                "step": s.step_number,
                "thought": s.thought,
                "tool": s.tool_called,
                "arguments": s.tool_arguments,
                "result": s.tool_result,
            }
            for s in result.steps
        ],
        "final_answer": result.final_answer,
        "success": result.success,
        "provider": result.provider,
    }


class SmartChatRequest(BaseModel):
    message: str
    history: Optional[list[dict]] = None


@app.post("/v1/smart_chat")
async def smart_chat_endpoint(request: SmartChatRequest):
    """Real LLM chat with tool calling. Uses Ollama / Anthropic / OpenAI / fallback."""
    from opendna.llm.agent import simple_chat
    return simple_chat(request.message, request.history)


# =====================================================
# v0.4 - Multimer, benchmark, MD with explicit solvent
# =====================================================

class MultimerRequest(BaseModel):
    sequences: list[str]
    chain_ids: Optional[list[str]] = None


@app.post("/v1/multimer", response_model=JobResponse)
async def multimer_endpoint(request: MultimerRequest):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "running", "progress": 0.0, "result": None, "error": None,
        "type": "multimer", "started_at": time.time(),
    }
    asyncio.get_event_loop().run_in_executor(
        executor, _run_multimer, job_id, request.sequences, request.chain_ids
    )
    return JobResponse(job_id=job_id, status="running")


def _run_multimer(job_id, sequences, chain_ids):
    try:
        from opendna.engines.multimer import fold_multimer
        def on_progress(stage, frac):
            jobs[job_id]["progress"] = frac
        result = fold_multimer(sequences, chain_ids, on_progress=on_progress)
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["result"] = {
            "pdb": result.pdb_string,
            "chains": result.chains,
            "mean_confidence": result.mean_confidence,
            "interface_residues": result.interface_residues,
            "method": result.method,
            "notes": result.notes,
        }
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


class MdSolventRequest(BaseModel):
    pdb_string: str
    duration_ps: float = 100
    explicit_solvent: bool = True


@app.post("/v1/md_full", response_model=JobResponse)
async def md_full_endpoint(request: MdSolventRequest):
    """Full MD with explicit solvent (real OpenMM if installed)."""
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "running", "progress": 0.0, "result": None, "error": None,
        "type": "md_full", "started_at": time.time(),
    }
    asyncio.get_event_loop().run_in_executor(
        executor, _run_md_full, job_id, request.pdb_string, request.duration_ps, request.explicit_solvent
    )
    return JobResponse(job_id=job_id, status="running")


def _run_md_full(job_id, pdb_string, duration_ps, explicit_solvent):
    try:
        from opendna.engines.dynamics import quick_md
        def on_progress(stage, frac):
            jobs[job_id]["progress"] = frac
        result = quick_md(pdb_string, duration_ps, explicit_solvent, on_progress=on_progress)
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["result"] = _to_dict(result)
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@app.post("/v1/benchmark", response_model=JobResponse)
async def benchmark_endpoint():
    """Run the OpenDNA self-benchmark suite."""
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "running", "progress": 0.0, "result": None, "error": None,
        "type": "benchmark", "started_at": time.time(),
    }
    asyncio.get_event_loop().run_in_executor(executor, _run_benchmark, job_id)
    return JobResponse(job_id=job_id, status="running")


def _run_benchmark(job_id):
    try:
        from opendna.benchmarks import run_benchmark_suite
        suite = run_benchmark_suite()
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["result"] = suite.to_dict()
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


# =====================================================
# v0.4 - Workflows, project export, first-run wizard
# =====================================================

class WorkflowRunRequest(BaseModel):
    yaml_content: str


@app.post("/v1/workflow/run")
async def workflow_run(request: WorkflowRunRequest):
    """Run a YAML workflow inline."""
    import tempfile
    from opendna.workflows import run_workflow
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(request.yaml_content)
        path = f.name
    try:
        result = run_workflow(path)
    finally:
        try:
            Path(path).unlink()
        except OSError:
            pass
    return {
        "name": result.name,
        "success": result.success,
        "error": result.error,
        "outputs": result.outputs,
        "n_steps": len(result.steps),
        "steps": [
            {"name": s.name, "action": s.action} for s in result.steps
        ],
    }


class ProjectExportRequest(BaseModel):
    project_data: dict
    name: str


@app.post("/v1/projects/export")
async def project_export(request: ProjectExportRequest):
    """Export a project as a .opendna zip file. Returns the path."""
    from opendna.storage.export import export_project
    from opendna.storage.projects import projects_dir
    out = projects_dir() / f"{request.name}.opendna"
    path = export_project(request.project_data, out)
    return {"path": path, "name": request.name}


class FirstRunRequest(BaseModel):
    pass


@app.get("/v1/first_run/check")
async def first_run_check():
    """Check if this is a first-run setup. Returns hardware, missing deps, recommendations."""
    from opendna.hardware.detect import detect_hardware
    from opendna.llm.providers import detect_providers

    hw = detect_hardware()
    providers = detect_providers()

    recommendations = []
    needs_setup = False

    # Check ML model availability (rough check via cache dir)
    import os
    hf_cache = Path(os.path.expanduser("~/.cache/huggingface/hub"))
    has_esmfold = any("esmfold" in p.name for p in hf_cache.glob("**/*")) if hf_cache.exists() else False

    if not has_esmfold:
        recommendations.append({
            "level": "info",
            "title": "ESMFold not yet downloaded",
            "message": "ESMFold (~8 GB) will download on first protein fold. Make sure you have stable internet.",
        })
        needs_setup = True

    if hw.gpu is None:
        recommendations.append({
            "level": "warning",
            "title": "No GPU detected",
            "message": "OpenDNA will run on CPU only. Folding will be slow (5-10 min for small proteins). For faster results, use a system with NVIDIA GPU or Apple Silicon.",
        })

    if hw.total_ram_gb < 16:
        recommendations.append({
            "level": "warning",
            "title": "Limited RAM",
            "message": f"You have {hw.total_ram_gb:.0f} GB RAM. ESMFold needs ~8 GB just for inference. Stick to small proteins (<150 residues).",
        })

    has_real_llm = any(p.name != "heuristic" for p in providers)
    if not has_real_llm:
        recommendations.append({
            "level": "info",
            "title": "No LLM provider detected",
            "message": "For natural language and AI features, install Ollama from https://ollama.com and run 'ollama pull llama3.2:3b'.",
        })

    return {
        "needs_setup": needs_setup,
        "hardware": {
            "cpu": hw.cpu_name,
            "cores": hw.cpu_cores,
            "ram_gb": round(hw.total_ram_gb, 1),
            "gpu": {"name": hw.gpu.name, "vram_gb": hw.gpu.vram_gb} if hw.gpu else None,
            "tier": hw.recommended_tier.value,
        },
        "llm_providers": [{"name": p.name, "model": p.model} for p in providers],
        "recommendations": recommendations,
    }


@app.get("/v1/llm/providers")
async def llm_providers():
    from opendna.llm.providers import detect_providers
    providers = detect_providers()
    return {
        "providers": [
            {
                "name": p.name,
                "available": p.available,
                "model": p.model,
                "supports_tools": p.supports_tools,
            }
            for p in providers
        ]
    }


# =====================================================
# Background runners for new jobs
# =====================================================

def _run_constrained_design(job_id, pdb_string, fixed_positions, n, temp):
    try:
        from opendna.engines.constrained_design import constrained_design
        result = constrained_design(pdb_string, fixed_positions, n, temp)
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["result"] = _to_dict(result)
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


def _run_multi_objective(job_id, sequence, objectives, n):
    try:
        from opendna.engines.multi_objective import design_multi_objective
        result = design_multi_objective(sequence, objectives, n)
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["result"] = result
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


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
    return {"jobs": jobs.list_recent(50)}


@app.post("/v1/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    if not jobs.cancel(job_id):
        raise HTTPException(status_code=404, detail="Job not found or not cancellable")
    return {"cancelled": job_id}


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


def start_server(host: str = "127.0.0.1", port: int = 8765):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import os
    import sys

    # Allow port override via env var (used by Tauri sidecar) or CLI arg
    port = int(os.environ.get("OPENDNA_PORT", "8765"))
    host = os.environ.get("OPENDNA_HOST", "127.0.0.1")

    # Simple CLI: python -m opendna.api.server [--port N] [--host H]
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        elif args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        else:
            i += 1

    print(f"Starting OpenDNA API server on http://{host}:{port}")
    start_server(host=host, port=port)
