"""FastAPI server for OpenDNA v0.2."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, is_dataclass
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Depends, WebSocket, WebSocketDisconnect
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
        # Phase 3: try real Boltz-1 → ColabFold → then heuristic
        from opendna.engines.real_models import (
            boltz_multimer, colabfold_multimer, NotInstalledError,
        )
        for fn, name in ((boltz_multimer, "boltz"), (colabfold_multimer, "colabfold")):
            try:
                jobs[job_id]["progress"] = 0.1
                r = fn(sequences)
                jobs[job_id]["status"] = "completed"
                jobs[job_id]["progress"] = 1.0
                jobs[job_id]["result"] = {
                    "pdb": r.get("pdb", ""),
                    "chains": chain_ids or [chr(65 + i) for i in range(len(sequences))],
                    "mean_confidence": r.get("plddt_mean", 0.0),
                    "interface_residues": [],
                    "method": name,
                    "notes": f"Real {name} prediction",
                    "ptm": r.get("ptm"),
                    "iptm": r.get("iptm"),
                }
                return
            except NotInstalledError:
                continue
            except Exception:
                continue
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
    # Phase 3: try real DiffDock first, then fall back to heuristic docking
    try:
        from opendna.engines.real_models import diffdock_dock, NotInstalledError
        try:
            return diffdock_dock(request.pdb_string, request.ligand_smiles)
        except NotInstalledError:
            pass
    except Exception:
        pass
    from opendna.engines.docking import dock_ligand
    result = dock_ligand(request.pdb_string, request.ligand_smiles)
    return _to_dict(result)


@app.get("/v1/backends")
def backends_endpoint():
    """Report which real heavy-model backends are currently importable."""
    from opendna.engines.real_models import available_backends
    return {"backends": available_backends()}


@app.post("/v1/qm/single_point")
def qm_single_point_endpoint(body: dict):
    """Phase 3: xTB or ANI-2x single-point energy. Tries xTB first, ANI second."""
    pdb_string = body.get("pdb_string", "")
    prefer = body.get("engine", "xtb")
    from opendna.engines.real_models import xtb_single_point, ani_energy, NotInstalledError
    order = [xtb_single_point, ani_energy] if prefer == "xtb" else [ani_energy, xtb_single_point]
    errs = []
    for fn in order:
        try:
            return fn(pdb_string)
        except NotInstalledError as e:
            errs.append(str(e))
    return JSONResponse(
        {"error": "no QM backend available", "details": errs},
        status_code=503,
    )


@app.post("/v1/design_denovo")
def design_denovo_endpoint(body: dict):
    """Phase 3: RFdiffusion de novo backbone generation."""
    from opendna.engines.real_models import rfdiffusion_design, NotInstalledError
    try:
        return rfdiffusion_design(
            length=int(body.get("length", 100)),
            contigs=body.get("contigs"),
            num_designs=int(body.get("num_designs", 1)),
        )
    except NotInstalledError as e:
        return JSONResponse({"error": str(e)}, status_code=503)


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


# =============================================================================
# Component Manager endpoints (Phase 2)
# =============================================================================

_component_jobs: dict[str, dict] = {}


@app.get("/v1/components")
def list_components_endpoint():
    """List all registered components with their current install status."""
    from opendna.components import list_components, get_status
    out = []
    for c in list_components():
        d = c.to_dict()
        d["status"] = get_status(c.name)
        out.append(d)
    return {"components": out}


@app.get("/v1/components/{name}")
def get_component_endpoint(name: str):
    from opendna.components import get_component, get_status
    c = get_component(name)
    if c is None:
        return JSONResponse({"error": f"unknown component {name}"}, status_code=404)
    d = c.to_dict()
    d["status"] = get_status(name)
    return d


@app.post("/v1/components/{name}/install")
def install_component_endpoint(name: str):
    """Start an install job. Returns a job_id you can poll / stream."""
    from opendna.components import install_component, get_component
    import threading, uuid
    if get_component(name) is None:
        return JSONResponse({"error": f"unknown component {name}"}, status_code=404)
    job_id = f"comp-{uuid.uuid4().hex[:12]}"
    _component_jobs[job_id] = {
        "component": name,
        "status": "running",
        "progress": 0.0,
        "messages": [],
    }

    def _work():
        def on_progress(n: str, pct: float, msg: str):
            _component_jobs[job_id]["progress"] = pct / 100.0
            _component_jobs[job_id]["messages"].append(msg)
            if len(_component_jobs[job_id]["messages"]) > 500:
                _component_jobs[job_id]["messages"] = _component_jobs[job_id]["messages"][-500:]
        try:
            result = install_component(name, on_progress=on_progress)
            _component_jobs[job_id]["status"] = "completed" if result.get("status") in ("installed", "already_installed") else "failed"
            _component_jobs[job_id]["result"] = result
            _component_jobs[job_id]["progress"] = 1.0
        except Exception as e:
            _component_jobs[job_id]["status"] = "failed"
            _component_jobs[job_id]["error"] = str(e)

    threading.Thread(target=_work, daemon=True).start()
    return {"job_id": job_id, "component": name}


@app.post("/v1/components/{name}/uninstall")
def uninstall_component_endpoint(name: str):
    from opendna.components import uninstall_component, get_component
    if get_component(name) is None:
        return JSONResponse({"error": f"unknown component {name}"}, status_code=404)
    return uninstall_component(name)


@app.get("/v1/components/jobs/{job_id}")
def component_job_status(job_id: str):
    job = _component_jobs.get(job_id)
    if job is None:
        return JSONResponse({"error": "unknown job"}, status_code=404)
    return job


# =============================================================================
# PQC Auth (Phase 4)
# =============================================================================
import os as _os

_AUTH_REQUIRED = _os.environ.get("OPENDNA_AUTH_REQUIRED", "0") == "1"


def _resolve_identity(user_id: str):
    from opendna.auth import get_user_store
    return get_user_store().get_identity(user_id)


async def require_auth(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
):
    """FastAPI dependency. Returns AuthContext or None when auth is not required."""
    from opendna.auth import validate_token, get_user_store, get_audit_log
    if not _AUTH_REQUIRED:
        return None  # open mode (backward compatible)
    store = get_user_store()
    audit = get_audit_log()
    ip = request.client.host if request.client else None
    # API key path
    if x_api_key:
        uid = store.verify_api_key(x_api_key)
        if uid:
            audit.append("auth.api_key", actor=uid, ip=ip)
            from opendna.auth.tokens import AuthContext
            return AuthContext(user_id=uid, scopes=store.get_user_scopes(uid),
                               algorithm="api-key", token_exp=0.0, is_pqc=False)
    # Bearer token path
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        ctx = validate_token(token, _resolve_identity)
        if ctx:
            audit.append("auth.token", actor=ctx.user_id, ip=ip,
                         details={"alg": ctx.algorithm, "pqc": ctx.is_pqc})
            return ctx
    audit.append("auth.denied", ip=ip)
    raise HTTPException(status_code=401, detail="authentication required")


class _RegisterBody(BaseModel):
    user_id: str
    password: Optional[str] = None
    scopes: Optional[list] = None


@app.post("/v1/auth/register")
def auth_register(body: _RegisterBody, request: Request):
    from opendna.auth import get_user_store, get_audit_log, issue_token, PQC_AVAILABLE
    store = get_user_store()
    if store.get_identity(body.user_id) is not None:
        raise HTTPException(status_code=409, detail="user already exists")
    identity = store.create_user(body.user_id, body.password, body.scopes)
    token = issue_token(identity, scopes=body.scopes or ["user"])
    get_audit_log().append(
        "user.register",
        actor=body.user_id,
        ip=request.client.host if request.client else None,
        details={"pqc": PQC_AVAILABLE, "algorithm": identity.algorithm},
    )
    return {
        "user_id": body.user_id,
        "token": token,
        "algorithm": identity.algorithm,
        "pqc_available": PQC_AVAILABLE,
    }


class _LoginBody(BaseModel):
    user_id: str
    password: str


@app.post("/v1/auth/login")
def auth_login(body: _LoginBody, request: Request):
    from opendna.auth import get_user_store, get_audit_log, issue_token, PQC_AVAILABLE
    store = get_user_store()
    ip = request.client.host if request.client else None
    if not store.verify_password(body.user_id, body.password):
        get_audit_log().append("user.login_failed", actor=body.user_id, ip=ip)
        raise HTTPException(status_code=401, detail="invalid credentials")
    identity = store.get_identity(body.user_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="user has no identity")
    token = issue_token(identity, scopes=store.get_user_scopes(body.user_id))
    get_audit_log().append("user.login", actor=body.user_id, ip=ip,
                            details={"pqc": PQC_AVAILABLE})
    return {"user_id": body.user_id, "token": token, "pqc": PQC_AVAILABLE}


@app.get("/v1/auth/me")
def auth_me(ctx = Depends(require_auth)):
    if ctx is None:
        return {"auth_required": False, "mode": "open"}
    return {
        "user_id": ctx.user_id,
        "scopes": ctx.scopes,
        "algorithm": ctx.algorithm,
        "is_pqc": ctx.is_pqc,
        "token_exp": ctx.token_exp,
    }


@app.post("/v1/auth/api_keys")
def auth_create_api_key(body: dict, ctx = Depends(require_auth)):
    from opendna.auth import get_user_store, get_audit_log
    user_id = (ctx.user_id if ctx else body.get("user_id")) or "anonymous"
    store = get_user_store()
    raw = store.create_api_key(user_id, name=body.get("name", ""))
    get_audit_log().append("api_key.create", actor=user_id,
                            details={"name": body.get("name", "")})
    return {"api_key": raw, "user_id": user_id}


@app.get("/v1/auth/status")
def auth_status():
    from opendna.auth import PQC_AVAILABLE
    from opendna.auth.pqc import ALG_SIG, ALG_KEM
    return {
        "pqc_available": PQC_AVAILABLE,
        "auth_required": _AUTH_REQUIRED,
        "sig_algorithm": ALG_SIG if PQC_AVAILABLE else "HMAC-SHA256-fallback",
        "kem_algorithm": ALG_KEM if PQC_AVAILABLE else "hash-fallback",
    }


@app.get("/v1/auth/audit")
def auth_audit_tail(limit: int = 100, ctx = Depends(require_auth)):
    if ctx and not ctx.has_scope("admin") and _AUTH_REQUIRED:
        raise HTTPException(status_code=403, detail="admin scope required")
    from opendna.auth import get_audit_log
    log = get_audit_log()
    return {
        "chain": log.verify_chain(),
        "entries": log.tail(limit),
    }


# =============================================================================
# Phase 5: per-user workspaces + encryption-at-rest
# =============================================================================

class _WorkspaceOpenBody(BaseModel):
    user_id: str
    password: Optional[str] = None
    name: str = "default"


@app.post("/v1/workspaces/open")
def workspace_open(body: _WorkspaceOpenBody):
    from opendna.workspaces import get_workspace, ENCRYPTION_AVAILABLE
    try:
        ws = get_workspace(body.user_id, body.password, body.name)
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return {
        "user_id": ws.meta.user_id,
        "name": ws.meta.name,
        "encrypted": ws.meta.encrypted,
        "encryption_available": ENCRYPTION_AVAILABLE,
        "projects": ws.list_projects(),
    }


@app.get("/v1/workspaces/{user_id}")
def workspace_list(user_id: str):
    from opendna.workspaces import list_user_workspaces
    return {"workspaces": list_user_workspaces(user_id)}


class _WorkspaceSaveBody(BaseModel):
    user_id: str
    password: Optional[str] = None
    name: str = "default"
    project_name: str
    payload: dict


@app.post("/v1/workspaces/save_project")
def workspace_save_project(body: _WorkspaceSaveBody):
    from opendna.workspaces import get_workspace
    try:
        ws = get_workspace(body.user_id, body.password, body.name)
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    path = ws.save_project(body.project_name, body.payload)
    from opendna.auth import get_audit_log
    get_audit_log().append(
        "project.save", actor=body.user_id, resource=body.project_name,
        details={"encrypted": ws.meta.encrypted},
    )
    return {"path": str(path), "encrypted": ws.meta.encrypted}


class _WorkspaceLoadBody(BaseModel):
    user_id: str
    password: Optional[str] = None
    name: str = "default"
    project_name: str


@app.post("/v1/workspaces/load_project")
def workspace_load_project(body: _WorkspaceLoadBody):
    from opendna.workspaces import get_workspace
    try:
        ws = get_workspace(body.user_id, body.password, body.name)
        data = ws.load_project(body.project_name)
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="project not found")
    return {"project": data}


# =============================================================================
# Phase 6: Priority job queue + WebSocket streaming + GPU pool
# =============================================================================

@app.on_event("startup")
async def _startup_queue():
    from opendna.runtime import get_queue
    await get_queue().start()


@app.get("/v1/queue/stats")
def queue_stats():
    from opendna.runtime import get_queue, get_gpu_pool
    return {
        "queue": get_queue().stats(),
        "gpu": get_gpu_pool().info(),
    }


@app.get("/v1/queue/jobs")
def queue_list(user_id: Optional[str] = None):
    from opendna.runtime import get_queue
    return {"jobs": get_queue().list(user_id=user_id)}


@app.get("/v1/queue/jobs/{job_id}")
def queue_get(job_id: str):
    from opendna.runtime import get_queue
    job = get_queue().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job")
    return job


class _EnqueueBody(BaseModel):
    kind: str              # "fold" | "design" | "md" | "dock" | "multimer"
    params: dict
    priority: int = 1      # 0=interactive, 1=normal, 2=batch
    user_id: Optional[str] = None


def _runner_for(kind: str):
    """Return a callable fn(on_progress=..., **params) -> result for a job kind."""
    def _fold(on_progress, sequence: str, **_):
        from opendna.engines.folding import fold_sequence
        pdb = fold_sequence(sequence, on_progress=lambda s, f: on_progress(s, f))
        return {"pdb": pdb.pdb_string if hasattr(pdb, "pdb_string") else str(pdb)}

    def _design(on_progress, pdb_string: str, num_candidates: int = 10, **_):
        from opendna.engines.design import design_sequences
        res = design_sequences(pdb_string, num_candidates=num_candidates)
        return {"candidates": res}

    def _md(on_progress, pdb_string: str, duration_ps: float = 100, **_):
        from opendna.engines.dynamics import quick_md
        r = quick_md(pdb_string, duration_ps=duration_ps,
                     on_progress=lambda s, f: on_progress(s, f))
        return {"result": str(r)}

    def _dock(on_progress, pdb_string: str, ligand_smiles: str, **_):
        from opendna.engines.real_models import diffdock_dock, NotInstalledError
        try:
            return diffdock_dock(pdb_string, ligand_smiles)
        except NotInstalledError:
            from opendna.engines.docking import dock_ligand
            return _to_dict(dock_ligand(pdb_string, ligand_smiles))

    def _multimer(on_progress, sequences: list, chain_ids: Optional[list] = None, **_):
        from opendna.engines.multimer import fold_multimer
        r = fold_multimer(sequences, chain_ids,
                          on_progress=lambda s, f: on_progress(s, f))
        return {"pdb": r.pdb_string, "method": r.method}

    return {"fold": _fold, "design": _design, "md": _md,
            "dock": _dock, "multimer": _multimer}.get(kind)


@app.post("/v1/queue/enqueue")
async def queue_enqueue(body: _EnqueueBody):
    from opendna.runtime import get_queue
    fn = _runner_for(body.kind)
    if fn is None:
        raise HTTPException(status_code=400, detail=f"unknown job kind: {body.kind}")
    q = get_queue()
    await q.start()
    job_id = await q.submit(
        fn, priority=body.priority, job_type=body.kind,
        kwargs=body.params, user_id=body.user_id,
    )
    return {"job_id": job_id, "priority": body.priority}


@app.websocket("/v1/ws/jobs/{job_id}")
async def ws_job(websocket: WebSocket, job_id: str):
    from opendna.runtime import get_queue
    await websocket.accept()
    q = get_queue()
    job = q.get(job_id)
    if job is None:
        await websocket.send_json({"event": "error", "reason": "unknown job"})
        await websocket.close()
        return
    # Send current state immediately so clients joining mid-run catch up.
    await websocket.send_json({"event": "snapshot", "job": job})
    sub = q.subscribe(job_id)
    try:
        while True:
            if job["status"] in ("completed", "failed"):
                await websocket.send_json({"event": "final", "job": job})
                break
            try:
                evt = await asyncio.wait_for(sub.get(), timeout=30.0)
                await websocket.send_json(evt)
                if evt.get("event") == "finished":
                    break
            except asyncio.TimeoutError:
                await websocket.send_json({"event": "heartbeat", "ts": time.time()})
    except WebSocketDisconnect:
        pass
    finally:
        q.unsubscribe(job_id, sub)


@app.get("/v1/gpu/info")
def gpu_info():
    from opendna.runtime import get_gpu_pool
    return get_gpu_pool().info()


@app.post("/v1/gpu/evict_warm")
def gpu_evict_warm(older_than_s: int = 300):
    from opendna.runtime import get_gpu_pool
    n = get_gpu_pool().evict_older_than(older_than_s)
    return {"evicted": n}


# =============================================================================
# Phase 7: crash reporting + self-healing
# =============================================================================

@app.on_event("startup")
async def _startup_reliability():
    from opendna.reliability import install_excepthook, get_healer
    install_excepthook()
    get_healer().start(interval_s=60.0)


@app.get("/v1/health")
def health_endpoint():
    from opendna.reliability import get_healer
    return get_healer().run_once()


@app.get("/v1/crashes")
def crashes_list(limit: int = 50):
    from opendna.reliability import get_crash_reporter
    return {"crashes": get_crash_reporter().list_crashes(limit=limit)}


@app.delete("/v1/crashes")
def crashes_clear():
    from opendna.reliability import get_crash_reporter
    return {"deleted": get_crash_reporter().clear()}


# =============================================================================
# Phase 8: provenance graph + time machine + diff/blame/bisect
# =============================================================================

class _ProvAddBody(BaseModel):
    project_id: str
    kind: str
    inputs: dict
    outputs: dict
    score: Optional[float] = None
    parent_ids: Optional[list] = None
    actor: Optional[str] = None


@app.post("/v1/provenance/record")
def prov_record(body: _ProvAddBody):
    from opendna.provenance import record_step
    n = record_step(
        project_id=body.project_id, kind=body.kind,
        inputs=body.inputs, outputs=body.outputs,
        score=body.score, parent_ids=body.parent_ids, actor=body.actor,
    )
    return n.to_dict()


@app.get("/v1/provenance/{project_id}")
def prov_get_project(project_id: str):
    from opendna.provenance import get_provenance_store
    store = get_provenance_store()
    return {
        "nodes": [n.to_dict() for n in store.project_nodes(project_id)],
        "edges": [{"parent": e.parent, "child": e.child} for e in store.project_edges(project_id)],
        "stats": store.stats(project_id),
    }


@app.get("/v1/provenance/node/{node_id}")
def prov_node(node_id: str):
    from opendna.provenance import get_provenance_store
    n = get_provenance_store().get(node_id)
    if n is None:
        raise HTTPException(status_code=404, detail="node not found")
    return n.to_dict()


@app.get("/v1/provenance/lineage/{node_id}")
def prov_lineage(node_id: str):
    from opendna.provenance import get_provenance_store
    return {"lineage": [n.to_dict() for n in get_provenance_store().lineage(node_id)]}


@app.get("/v1/provenance/diff")
def prov_diff(a: str, b: str):
    from opendna.provenance import diff_steps
    return diff_steps(a, b)


@app.get("/v1/provenance/blame")
def prov_blame(project_id: str, residue: int):
    from opendna.provenance import blame_residue
    return {"blame": blame_residue(project_id, residue)}


@app.get("/v1/provenance/bisect")
def prov_bisect(project_id: str, threshold: float = 0.0):
    from opendna.provenance import bisect_regression
    return {"result": bisect_regression(project_id, threshold=threshold)}


# =============================================================================
# Phase 9: Visual workflow editor backend
# =============================================================================

@app.get("/v1/workflow/node_types")
def workflow_node_types():
    from opendna.workflows.graph_runner import list_node_types
    return {"node_types": list_node_types()}


class _GraphRunBody(BaseModel):
    workflow: dict
    project_id: Optional[str] = None
    actor: Optional[str] = None


@app.post("/v1/workflow/run_graph")
async def workflow_run_graph(body: _GraphRunBody):
    from opendna.workflows.graph_runner import run_workflow
    from opendna.runtime import get_queue
    q = get_queue()
    await q.start()

    def _runner(on_progress, **_):
        return run_workflow(
            body.workflow,
            project_id=body.project_id,
            actor=body.actor,
            on_progress=on_progress,
        )

    job_id = await q.submit(_runner, priority=1, job_type="workflow",
                            user_id=body.actor)
    return {"job_id": job_id}


# =============================================================================
# Phase 10: External APIs (NCBI, PubMed, vendors, notifications, webhooks)
# =============================================================================

@app.get("/v1/ncbi/search")
def ncbi_search_endpoint(db: str, term: str, retmax: int = 20):
    from opendna.external import ncbi_search
    return ncbi_search(db, term, retmax)


@app.get("/v1/uniprot/search")
def uniprot_search_endpoint(query: str, size: int = 25, reviewed_only: bool = True, organism: Optional[str] = None):
    from opendna.external import uniprot_search
    return uniprot_search(query, size=size, reviewed_only=reviewed_only, organism=organism)


@app.get("/v1/uniprot/{accession}")
def uniprot_fetch_endpoint(accession: str):
    from opendna.external import uniprot_fetch_sequence
    return uniprot_fetch_sequence(accession)


@app.get("/v1/alphafold/{uniprot_id}")
def alphafold_db_fetch_endpoint(uniprot_id: str, with_meta: bool = False):
    from opendna.external import fetch_alphafold, fetch_alphafold_meta
    try:
        if with_meta:
            return fetch_alphafold_meta(uniprot_id)
        return fetch_alphafold(uniprot_id)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"AlphaFold DB fetch failed: {e}")


@app.post("/v1/export/trajectory_gif")
def export_trajectory_gif_endpoint(payload: dict):
    from opendna.notebook import trajectory_to_gif
    from pathlib import Path
    import tempfile, base64
    frames = payload.get("pdb_frames") or []
    fps = int(payload.get("fps", 10))
    if not isinstance(frames, list) or not frames:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="pdb_frames must be a non-empty list")
    out_path = tempfile.NamedTemporaryFile(suffix=".gif", delete=False).name
    path = trajectory_to_gif(frames, out_path, fps=fps)
    try:
        data = Path(path).read_bytes()
        b64 = base64.b64encode(data).decode()
    except Exception:
        b64 = ""
    return {"path": path, "frames": len(frames), "fps": fps, "gif_b64": b64}


@app.get("/v1/ncbi/fetch")
def ncbi_fetch_endpoint(db: str, id: str, rettype: str = "fasta"):
    from opendna.external import ncbi_fetch
    return ncbi_fetch(db, id, rettype)


@app.get("/v1/pubmed/search")
def pubmed_search_endpoint(query: str, retmax: int = 20):
    from opendna.external import pubmed_search
    return pubmed_search(query, retmax)


@app.get("/v1/pubmed/summarize")
def pubmed_summarize_endpoint(pmid: str):
    from opendna.external import pubmed_summarize
    return pubmed_summarize(pmid)


@app.get("/v1/vendors")
def vendors_list():
    from opendna.external import list_vendors
    return {"vendors": list_vendors()}


class _QuoteBody(BaseModel):
    sequence: str
    kind: str = "dna_gene"
    vendor: Optional[str] = None


@app.post("/v1/vendors/quote")
def vendors_quote(body: _QuoteBody):
    from opendna.external import quote_synthesis
    return quote_synthesis(body.sequence, body.kind, body.vendor)


class _OrderBody(BaseModel):
    sequence: str
    vendor: str
    product: str
    customer_email: str = ""
    notes: str = ""


@app.post("/v1/vendors/order")
def vendors_order(body: _OrderBody):
    from opendna.external import place_order, fire_webhooks
    from opendna.auth import get_audit_log
    record = place_order(body.sequence, body.vendor, body.product, body.customer_email, body.notes)
    get_audit_log().append("vendor.order", actor=body.customer_email or None,
                            resource=record.get("order_id"),
                            details={"vendor": body.vendor, "status": record.get("status")})
    fire_webhooks("vendor.order", record)
    return record


class _NotifyBody(BaseModel):
    text: str
    channel: str  # "slack" | "teams" | "discord"
    webhook_url: Optional[str] = None


@app.post("/v1/notify")
def notify_endpoint(body: _NotifyBody):
    from opendna.external import notify_slack, notify_teams, notify_discord
    fn = {"slack": notify_slack, "teams": notify_teams, "discord": notify_discord}.get(body.channel)
    if fn is None:
        raise HTTPException(status_code=400, detail="unknown channel")
    return {"sent": fn(body.text, body.webhook_url)}


class _WebhookBody(BaseModel):
    url: str
    event: str = "*"
    secret: Optional[str] = None


@app.post("/v1/webhooks")
def webhook_register(body: _WebhookBody):
    from opendna.external import register_webhook
    return {"id": register_webhook(body.url, body.event, body.secret)}


@app.get("/v1/webhooks")
def webhook_list():
    from opendna.external import list_webhooks
    return {"webhooks": list_webhooks()}


@app.delete("/v1/webhooks/{wid}")
def webhook_delete(wid: str):
    from opendna.external import delete_webhook
    return {"deleted": delete_webhook(wid)}


# =============================================================================
# Phase 12: Lab notebook + DOI/Zenodo + figure/GLTF/OBJ export
# =============================================================================

class _NotebookEntryBody(BaseModel):
    project_id: str
    title: str
    body_md: str
    tags: Optional[list] = None
    prov_node_ids: Optional[list] = None
    author: Optional[str] = None


@app.post("/v1/notebook/entries")
def notebook_add_entry(body: _NotebookEntryBody):
    from opendna.notebook import get_notebook
    nb = get_notebook(body.project_id)
    e = nb.add_entry(body.title, body.body_md, body.tags, body.prov_node_ids, body.author)
    return e.to_dict()


@app.get("/v1/notebook/{project_id}/entries")
def notebook_list_entries(project_id: str):
    from opendna.notebook import get_notebook
    return {"entries": get_notebook(project_id).list_entries()}


@app.get("/v1/notebook/{project_id}/entries/{entry_id}")
def notebook_get_entry(project_id: str, entry_id: str):
    from opendna.notebook import get_notebook
    e = get_notebook(project_id).get_entry(entry_id)
    if e is None:
        raise HTTPException(status_code=404, detail="entry not found")
    return e


@app.get("/v1/notebook/{project_id}/attachments")
def notebook_list_attachments(project_id: str):
    """List files in the project's notebook attachment directory."""
    from opendna.notebook import get_notebook
    nb = get_notebook(project_id)
    items = []
    try:
        attach_dir = getattr(nb, "attach_dir", None)
        if attach_dir is not None and attach_dir.exists():
            for p in sorted(attach_dir.iterdir()):
                if p.is_file():
                    try:
                        items.append({"name": p.name, "size": p.stat().st_size})
                    except OSError:
                        items.append({"name": p.name, "size": 0})
    except Exception:
        pass
    return {"attachments": items}


class _ZenodoBody(BaseModel):
    title: str
    description: str
    creators: list
    files: Optional[list] = None
    keywords: Optional[list] = None
    upload_type: str = "software"


@app.post("/v1/zenodo/mint")
def zenodo_mint(body: _ZenodoBody):
    from opendna.notebook import mint_doi_zenodo
    return mint_doi_zenodo(
        body.title, body.description, body.creators,
        body.files, body.keywords, body.upload_type,
    )


@app.get("/v1/zenodo/deposits")
def zenodo_deposits():
    from opendna.notebook import list_local_deposits
    return {"deposits": list_local_deposits()}


class _FigureBody(BaseModel):
    data: dict
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    format: str = "svg"


@app.post("/v1/export/figure")
def export_figure(body: _FigureBody):
    from opendna.notebook import export_figure_png, export_figure_svg
    if body.format == "png":
        png = export_figure_png(body.data, body.title, body.xlabel, body.ylabel)
        import base64
        return {"format": "png", "base64": base64.b64encode(png).decode()}
    svg = export_figure_svg(body.data, body.title)
    return {"format": "svg", "svg": svg}


class _Pdb3DBody(BaseModel):
    pdb_string: str
    format: str = "gltf"


@app.post("/v1/export/3d")
def export_3d(body: _Pdb3DBody):
    from opendna.notebook import pdb_to_gltf, pdb_to_obj
    if body.format == "obj":
        return {"format": "obj", "text": pdb_to_obj(body.pdb_string)}
    return {"format": "gltf", "gltf": pdb_to_gltf(body.pdb_string)}


# =============================================================================
# Phase 13: Yjs CRDT real-time co-editing
# =============================================================================
from opendna.collab import register_crdt_routes as _register_crdt
_register_crdt(app)


# =============================================================================
# Phase 14: Academy levels 4-7, badges, daily challenges, glossary
# =============================================================================

@app.get("/v1/academy/levels")
def academy_levels():
    from opendna.academy import list_levels
    return {"levels": list_levels()}


@app.get("/v1/academy/levels/{level_id}")
def academy_level(level_id: int):
    from opendna.academy import get_level
    lvl = get_level(level_id)
    if lvl is None:
        raise HTTPException(status_code=404, detail="level not found")
    return lvl


@app.get("/v1/academy/badges")
def academy_badges():
    from opendna.academy.content import BADGES
    return {"badges": BADGES}


@app.get("/v1/academy/glossary")
def academy_glossary():
    from opendna.academy.content import GLOSSARY
    return {"glossary": GLOSSARY}


@app.get("/v1/academy/daily")
def academy_daily(date: Optional[str] = None):
    from opendna.academy import daily_challenge
    return daily_challenge(date)


class _DailyAnswerBody(BaseModel):
    user_id: str
    sequence: str
    date: Optional[str] = None


@app.post("/v1/academy/daily/answer")
def academy_daily_answer(body: _DailyAnswerBody):
    from opendna.academy import check_answer
    return check_answer(body.user_id, body.sequence, body.date)


@app.get("/v1/academy/leaderboard")
def academy_leaderboard(limit: int = 20):
    from opendna.academy import leaderboard_top
    return {"leaderboard": leaderboard_top(limit)}


# =============================================================================
# Phase 15: LLM polish (Ollama manager + streaming + multi-turn memory)
# =============================================================================

@app.get("/v1/llm/ollama/status")
def ollama_status():
    from opendna.llm.ollama_manager import is_installed, is_running, list_local_models, DEFAULT_MODEL
    return {
        "installed": is_installed(),
        "running": is_running(),
        "default_model": DEFAULT_MODEL,
        "models": list_local_models(),
    }


@app.post("/v1/llm/ollama/install")
def ollama_install():
    from opendna.llm.ollama_manager import auto_install
    return auto_install()


class _PullBody(BaseModel):
    model: str = "llama3.2:3b"


@app.post("/v1/llm/ollama/pull")
def ollama_pull(body: _PullBody):
    from opendna.llm.ollama_manager import pull_model
    return pull_model(body.model)


class _ChatBody(BaseModel):
    session_id: str
    message: str
    system: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7


@app.post("/v1/llm/chat/stream")
async def llm_chat_stream(body: _ChatBody):
    from opendna.llm.ollama_manager import stream_chat, session_history, session_append, DEFAULT_MODEL
    from fastapi.responses import StreamingResponse

    session_append(body.session_id, "user", body.message)
    history = session_history(body.session_id)

    def _iter():
        acc = []
        for chunk in stream_chat(
            history, model=body.model or DEFAULT_MODEL,
            system=body.system, temperature=body.temperature,
        ):
            acc.append(chunk)
            yield chunk
        session_append(body.session_id, "assistant", "".join(acc))

    return StreamingResponse(_iter(), media_type="text/plain")


@app.get("/v1/llm/chat/history/{session_id}")
def llm_chat_history(session_id: str):
    from opendna.llm.ollama_manager import session_history
    return {"history": session_history(session_id)}


@app.delete("/v1/llm/chat/history/{session_id}")
def llm_chat_clear(session_id: str):
    from opendna.llm.ollama_manager import session_clear
    session_clear(session_id)
    return {"cleared": session_id}


# =============================================================================
# Phase 16: Compliance (SBOM, air-gap, HIPAA/GDPR)
# =============================================================================

@app.get("/v1/compliance/sbom")
def compliance_sbom():
    from opendna.compliance import generate_sbom
    return generate_sbom()


@app.get("/v1/compliance/airgap")
def compliance_airgap():
    from opendna.compliance import check_airgap_capability
    return check_airgap_capability()


@app.post("/v1/compliance/airgap/bundle")
def compliance_airgap_bundle(body: dict):
    from opendna.compliance import bundle_offline_artifacts
    return bundle_offline_artifacts(body.get("out_dir", "./opendna-airgap"))


@app.get("/v1/compliance/privacy")
def compliance_privacy():
    from opendna.compliance import privacy_report
    return privacy_report()


@app.get("/v1/compliance/hipaa")
def compliance_hipaa():
    from opendna.compliance import hipaa_checklist
    return {"checklist": hipaa_checklist()}


@app.get("/v1/compliance/gdpr")
def compliance_gdpr():
    from opendna.compliance import gdpr_checklist
    return {"checklist": gdpr_checklist()}


class _GdprUser(BaseModel):
    user_id: str
    out_path: Optional[str] = None


@app.post("/v1/compliance/export_user_data")
def compliance_export_user(body: _GdprUser):
    from opendna.compliance import export_user_data
    out = body.out_path or f"./{body.user_id}-export.zip"
    return export_user_data(body.user_id, out)


@app.post("/v1/compliance/delete_user_data")
def compliance_delete_user(body: _GdprUser):
    from opendna.compliance import delete_user_data
    from opendna.auth import get_audit_log
    result = delete_user_data(body.user_id)
    get_audit_log().append("gdpr.erasure", actor=body.user_id, details=result)
    return result


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
