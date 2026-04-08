# OpenDNA API Reference

Complete reference for the OpenDNA REST API. The server runs on `http://localhost:8765` by default.

## Table of Contents
- [Health & Meta](#health--meta)
- [Folding & Design](#folding--design)
- [Analysis](#analysis)
- [Mutation & Comparison](#mutation--comparison)
- [Docking](#docking)
- [Molecular Dynamics](#molecular-dynamics)
- [Data Sources](#data-sources)
- [Cost & Carbon](#cost--carbon)
- [Project Workspace](#project-workspace)
- [Job Status](#job-status)
- [Conventions](#conventions)

---

## Conventions

### Base URL
```
http://localhost:8765
```

### Content type
All POST requests use `application/json`.

### Job-based vs instant
Some endpoints return immediately with a `job_id` and run the work in the background. Others compute synchronously and return the result directly.

| Job-based (background) | Instant (synchronous) |
|---|---|
| `/v1/fold` | `/v1/evaluate` |
| `/v1/design` | `/v1/analyze` |
| `/v1/iterative_design` | `/v1/explain` |
| `/v1/md` | `/v1/mutate` |
| | `/v1/chat` |
| | `/v1/compare` |
| | `/v1/dock` |
| | `/v1/screen` |
| | `/v1/align` |
| | `/v1/predict_ddg` |
| | `/v1/cost` |
| | `/v1/fetch_uniprot` |
| | `/v1/fetch_pdb` |

For job-based endpoints, poll `/v1/jobs/{job_id}` until status is `completed` or `failed`.

### Job response format
```json
{
  "job_id": "abc12345",
  "status": "running" | "completed" | "failed",
  "progress": 0.0..1.0,
  "result": null | { ... },
  "error": null | "error message"
}
```

---

## Health & Meta

### `GET /health`
Server health check.

**Response:**
```json
{
  "status": "ok",
  "version": "0.2.0",
  "engines": ["fold", "design", "iterative_design", "evaluate", "analyze", "explain", "mutate", "compare", "dock", "screen", "md", "disorder"]
}
```

### `GET /v1/hardware`
Detected hardware info.

**Response:**
```json
{
  "cpu": "Intel(R) Core(TM) i7-12700K",
  "cores": 20,
  "ram_gb": 32.0,
  "gpu": {
    "name": "NVIDIA GeForce RTX 3070",
    "vram_gb": 8.0,
    "backend": "cuda"
  },
  "recommended_tier": "gaming",
  "recommended_backend": "cuda",
  "recommended_precision": "fp16"
}
```

---

## Folding & Design

### `POST /v1/fold`
Predict the 3D structure of a protein from its amino acid sequence using ESMFold.

**Request:**
```json
{
  "sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELS",
  "method": "auto",
  "device": null
}
```

**Parameters:**
- `sequence` (string, required) — Amino acid sequence (1-letter codes)
- `method` (string, optional) — `"auto"` or `"esmfold"`. Default: `"auto"`
- `device` (string, optional) — `"cuda"`, `"cpu"`, `"mps"`. Default: auto-detect

**Response:** `JobResponse` (poll `/v1/jobs/{job_id}`)

When complete, `result` contains:
```json
{
  "pdb": "ATOM      1  N   MET A   1      ...",
  "mean_confidence": 0.87,
  "method": "esmfold",
  "explanation": "Good confidence prediction. Most of the structure is reliable."
}
```

### `POST /v1/design`
Generate alternative protein sequences for a given backbone structure using ESM-IF1 inverse folding.

**Request:**
```json
{
  "pdb_string": "ATOM      1  N   MET ...",
  "num_candidates": 10,
  "temperature": 0.1,
  "device": null
}
```

**Parameters:**
- `pdb_string` (string, required) — PDB-format structure content
- `num_candidates` (int, 1-100, default 10) — How many sequences to generate
- `temperature` (float, 0.01-2.0, default 0.1) — Sampling temperature (higher = more diverse)
- `device` (string, optional) — Compute device

**Response:** `JobResponse`

When complete:
```json
{
  "candidates": [
    {"rank": 1, "sequence": "MKTVRQERLK...", "score": -0.85, "recovery": 0.62},
    ...
  ],
  "method": "esm-if1",
  "explanation": "Generated 10 candidate sequences using ESM-IF1 inverse folding..."
}
```

### `POST /v1/iterative_design`
Run an automated optimization loop: fold → design → score → keep best → repeat.

**Request:**
```json
{
  "sequence": "MKTVRQERLKSIVRILER",
  "n_rounds": 5,
  "candidates_per_round": 5,
  "temperature": 0.2
}
```

**Response:** `JobResponse`

When complete:
```json
{
  "initial_sequence": "MKTVRQERLKSIVRILER",
  "final_sequence": "MKTVRQERLKSIVRILER",
  "initial_score": 0.62,
  "final_score": 0.78,
  "improvement": 0.16,
  "history": [
    {"round": 0, "best_score": 0.62, "candidates_evaluated": 1},
    {"round": 1, "best_score": 0.71, "improved": true, "candidates_evaluated": 5},
    ...
  ],
  "rounds": [
    {"round": 0, "sequence": "...", "score": 0.62, "confidence": 0.85, "pdb": "ATOM..."},
    ...
  ]
}
```

---

## Analysis

### `POST /v1/evaluate`
Compute the composite quality score for a sequence.

**Request:**
```json
{ "sequence": "MKTVRQERLK..." }
```

**Response:**
```json
{
  "overall": 0.69,
  "confidence": 0.3,
  "breakdown": {
    "stability": 0.75,
    "solubility": 0.80,
    "immunogenicity": 0.97,
    "developability": 0.60,
    "novelty": 0.50
  },
  "summary": "This protein looks promising (69/100). ...",
  "recommendations": ["Note: this score is sequence-only..."]
}
```

### `POST /v1/analyze`
Run the comprehensive analysis suite (Schrödinger QikProp equivalent + extras).

**Request:**
```json
{
  "sequence": "MKTVRQERLK...",
  "pdb_string": "ATOM..."  // optional, enables structure-based analyses
}
```

**Response:** Full analysis object with sections:
- `properties` — MW, pI, GRAVY, instability, half-life, composition, etc.
- `lipinski` — Rule of Five with violations
- `hydropathy_profile` — Per-residue Kyte-Doolittle scores
- `disorder` — IUPred-like disorder scores and regions
- `transmembrane` — TMHMM-like helix prediction
- `signal_peptide` — Signal peptide detection
- `aggregation` — TANGO-like aggregation propensity
- `phosphorylation` — Phospho sites by kinase
- `glycosylation` — N/O-linked sites
- `structure` (if PDB provided) — Secondary structure, Ramachandran, RMSD, pockets, bonds

### `POST /v1/explain`
Generate a plain-English explanation of a protein.

**Request:**
```json
{
  "sequence": "MKTVRQERLK...",
  "pdb_string": "ATOM..."  // optional
}
```

**Response:**
```json
{
  "explanation": "This protein has 76 amino acids (8565 Da)..."
}
```

If Ollama is running locally with `llama3.2:3b`, uses real LLM. Otherwise falls back to a detailed heuristic explanation.

---

## Mutation & Comparison

### `POST /v1/mutate`
Apply a point mutation to a sequence.

**Request:**
```json
{ "sequence": "MKTV...", "mutation": "K2R" }
```

**Response:**
```json
{
  "original": "MKTV...",
  "mutated": "MRTV...",
  "mutation": "K2R"
}
```

Errors with 400 if the mutation format is invalid or the position doesn't match.

### `POST /v1/predict_ddg`
Estimate stability change (ΔΔG) for a mutation.

**Request:**
```json
{ "sequence": "MKTV...", "mutation": "K2R" }
```

**Response:**
```json
{
  "mutation": "K2R",
  "ddg_kcal_mol": -0.40,
  "classification": "destabilizing",
  "interpretation": "Mutating K at position 2 to R is predicted to be destabilizing..."
}
```

### `POST /v1/compare`
Compare two structures.

**Request:**
```json
{
  "pdb_a": "ATOM...",
  "pdb_b": "ATOM..."
}
```

**Response:**
```json
{
  "rmsd": 1.234,
  "length_1": 76,
  "length_2": 76,
  "aligned_residues": 76,
  "ss_identity": 0.91,
  "rg_1": 11.5,
  "rg_2": 11.7
}
```

### `POST /v1/align`
Pairwise sequence alignment via Needleman-Wunsch with BLOSUM62.

**Request:**
```json
{
  "seq1": "MKTVRQERLK",
  "seq2": "MKTVRAERLK"
}
```

**Response:**
```json
{
  "score": 48,
  "identity_pct": 90.0,
  "similarity_pct": 100.0,
  "aligned_length": 10,
  "alignment_1": "MKTVRQERLK",
  "alignment_2": "MKTVRAERLK",
  "comparison": "|||||:||||",
  "matches": 9
}
```

---

## Docking

### `POST /v1/dock`
Dock a small molecule (SMILES) into a protein.

**Request:**
```json
{
  "pdb_string": "ATOM...",
  "ligand_smiles": "CC(=O)Oc1ccccc1C(=O)O"
}
```

**Response:** Heuristic-based docking result. Real DiffDock integration is planned.

### `POST /v1/screen`
Virtual screen multiple ligands against one protein.

**Request:**
```json
{
  "pdb_string": "ATOM...",
  "ligands": ["CCO", "CC(=O)O", "CC(=O)Oc1ccccc1C(=O)O"]
}
```

**Response:** Ranked list of ligands by predicted affinity.

---

## Molecular Dynamics

### `POST /v1/md`
Run a quick MD simulation.

**Request:**
```json
{
  "pdb_string": "ATOM...",
  "duration_ps": 100
}
```

**Response:** `JobResponse`. When complete:
```json
{
  "duration_ps": 100,
  "n_frames": 20,
  "rmsd_trajectory": [0.0, 0.5, 0.8, ...],
  "final_rmsd": 1.5,
  "stable": true,
  "notes": "Heuristic estimate from pLDDT confidence..."
}
```

If OpenMM is installed (`pip install openmm`), runs real MD. Otherwise heuristic.

---

## Data Sources

### `POST /v1/fetch_uniprot`
Fetch a protein from UniProt.

**Request:**
```json
{ "accession": "P0CG48" }
```

You can also use famous names: `"ubiquitin"`, `"insulin"`, `"gfp"`, etc.

**Response:**
```json
{
  "accession": "P0CG48",
  "name": "UBC_HUMAN",
  "sequence": "MQIFVKTLTGK...",
  "organism": "Homo sapiens",
  "length": 685,
  "description": "Polyubiquitin-C"
}
```

### `POST /v1/fetch_pdb`
Fetch a structure from RCSB PDB.

**Request:**
```json
{ "pdb_id": "1UBQ" }
```

**Response:**
```json
{
  "pdb_id": "1UBQ",
  "pdb_string": "HEADER ...\nATOM ..."
}
```

### `GET /v1/famous_proteins`
List supported famous protein shortcuts.

**Response:**
```json
{
  "ubiquitin": "P0CG48",
  "insulin": "P01308",
  "gfp": "P42212",
  ...
}
```

---

## Cost & Carbon

### `POST /v1/cost`
Estimate synthesis cost and computational carbon footprint.

**Request:**
```json
{ "sequence": "MKTVRQERLK..." }
```

**Response:**
```json
{
  "synthesis": {
    "sequence_length": 10,
    "twist_bioscience_usd": 52.10,
    "idt_usd": 70.40,
    "genscript_usd": 103.50,
    "cheapest_vendor": "Twist Bioscience",
    "cheapest_price": 52.10,
    "notes": "Estimates based on 2024 average per-base-pair pricing..."
  },
  "compute_carbon_cpu": {
    "energy_kwh": 0.000144,
    "co2_kg": 0.0000578,
    "equivalent": "~58 mg CO2 (a single breath)"
  },
  "compute_carbon_gpu": {
    "energy_kwh": 0.0000347,
    "co2_kg": 0.0000139,
    "equivalent": "~14 mg CO2"
  }
}
```

---

## Project Workspace

### `POST /v1/projects/save`
Save a workspace.

**Request:**
```json
{
  "name": "my_cancer_binder",
  "data": {
    "structures": [...],
    "sequences": [...]
  }
}
```

### `POST /v1/projects/load`
Load a workspace.

**Request:**
```json
{ "name": "my_cancer_binder" }
```

### `GET /v1/projects`
List all saved projects.

### `DELETE /v1/projects/{name}`
Delete a project.

---

## Job Status

### `GET /v1/jobs/{job_id}`
Get the status of a specific job.

**Response:** `JobResponse`

### `GET /v1/jobs`
List all jobs (capped at 50, most recent first).

**Response:**
```json
{
  "jobs": [
    {"id": "abc123", "type": "fold", "status": "completed", "progress": 1.0, "started_at": 1704067200.0},
    ...
  ]
}
```

---

## Chat

### `POST /v1/chat`
Parse a natural language message into an intent.

**Request:**
```json
{ "message": "fold MKTVRQERLK" }
```

**Response:**
```json
{
  "action": "fold",
  "sequence": "MKTVRQERLK",
  "mutation": null,
  "response": "Folding sequence (10 residues)..."
}
```

Possible `action` values: `fold`, `score`, `design`, `mutate`, `explain`, `help`, `unknown`.

---

# v0.5.0-rc1 API surface

The sections below document every endpoint added in v0.5.0, grouped by phase.
All new endpoints share the same base URL (`http://127.0.0.1:8765` by default)
and JSON conventions as the v0.2-v0.4 API above. Auth headers are only enforced
when the server is started with `OPENDNA_AUTH_REQUIRED=1`; otherwise the API
remains in "open mode" for local desktop use.

Common status codes: `200 OK` on success, `400` on bad input, `401` when auth
is required but missing/invalid, `403` on scope mismatch, `404` on missing
resource, `409` on conflict (e.g. user already exists), `503` when a required
backend is not installed.

## Phase 2: Component Manager

Heavy ML models, MD engines, QM tools, and LLMs are installed on-demand via
the Component Manager. Every component is one of four install kinds
(`pip` / `hf` / `script` / `ollama`) and a marker file at
`~/.opendna/components/<name>.installed` tracks successful installs.

### `GET /v1/components`
List every registered component along with its current install status.

Response:
```json
{
  "components": [
    {
      "name": "esmfold",
      "display_name": "ESMFold v1",
      "category": "folding",
      "description": "Meta's single-sequence predictor. ~8 GB.",
      "size_mb": 8000,
      "version": "v1",
      "install_kind": "hf",
      "install_target": "facebook/esmfold_v1",
      "import_check": "import transformers; transformers.EsmForProteinFolding",
      "homepage": "https://github.com/facebookresearch/esm",
      "license": "MIT",
      "status": "not_installed"
    }
  ]
}
```

`status` is one of `installed`, `not_installed`, `unknown`.

```bash
curl http://127.0.0.1:8765/v1/components
```

### `GET /v1/components/{name}`
Return the full record for a single component. `404` if unknown.

```bash
curl http://127.0.0.1:8765/v1/components/diffdock
```

### `POST /v1/components/{name}/install`
Start a non-blocking install job. Returns a `job_id` that can be polled.

Response:
```json
{"job_id": "comp-a1b2c3d4e5f6", "component": "diffdock"}
```

```bash
curl -X POST http://127.0.0.1:8765/v1/components/diffdock/install
```

### `POST /v1/components/{name}/uninstall`
Removes the marker file and (for `pip` components) runs `pip uninstall -y`.

Response: `{"status": "uninstalled", "component": "diffdock"}`.

### `GET /v1/components/jobs/{job_id}`
Poll install progress. Response fields:

| Field | Type | Description |
|---|---|---|
| `component` | string | Component being installed |
| `status` | string | `running` / `completed` / `failed` |
| `progress` | float | 0.0 - 1.0 |
| `messages` | array of string | Tail of subprocess output (capped at 500 lines) |
| `result` | object | Present once status transitions to `completed` |
| `error` | string | Present on failure |

```bash
curl http://127.0.0.1:8765/v1/components/jobs/comp-a1b2c3d4e5f6
```

## Phase 3: Real heavy-model backends

These endpoints expose physics/ML backends that are opt-in via the Component
Manager. Each returns `503` with `{"error": "..."}` when the underlying
package (DiffDock, RFdiffusion, xTB, TorchANI) is not installed.

### `GET /v1/backends`
Report which Phase 3 backends are currently importable.

Response:
```json
{"backends": {"diffdock": true, "rfdiffusion": false, "xtb": true, "ani": true, "boltz": false}}
```

### `POST /v1/qm/single_point`
Run a semi-empirical (xTB) or ML-potential (TorchANI ANI-2x) single-point
energy on a PDB string. Tries xTB first by default, ANI second.

Request:
```json
{"pdb_string": "ATOM ...", "engine": "xtb"}
```

Response (example):
```json
{"engine": "xtb", "energy_hartree": -114.523, "energy_kcalmol": -71842.1, "gradient_norm": 0.0041}
```

```bash
curl -X POST http://127.0.0.1:8765/v1/qm/single_point \
  -H 'Content-Type: application/json' \
  -d '{"pdb_string": "...", "engine": "xtb"}'
```

### `POST /v1/design_denovo`
RFdiffusion de novo backbone generation.

Request:
```json
{"length": 100, "contigs": "A1-50/0 10-20", "num_designs": 4}
```

Response: `{"designs": [{"pdb": "..."}], "num": 4}`. `503` if RFdiffusion is not installed.

## Phase 4: PQC auth layer

PQC (ML-DSA-65 / ML-KEM-768 via liboqs) is used when available; otherwise an
HMAC-SHA256 fallback kicks in so CI and open-mode deployments still work.
All mutating auth actions are appended to the hash-chained audit log.

### `POST /v1/auth/register`
Create a new user and return a bearer token.

Request:
```json
{"user_id": "alice", "password": "s3cret", "scopes": ["user"]}
```

Response:
```json
{"user_id": "alice", "token": "eyJ...", "algorithm": "ML-DSA-65", "pqc_available": true}
```

Status codes: `200` on success, `409` if the user already exists.

```bash
curl -X POST http://127.0.0.1:8765/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"user_id": "alice", "password": "s3cret"}'
```

### `POST /v1/auth/login`
Verify credentials and issue a new token.

Request: `{"user_id": "alice", "password": "s3cret"}`
Response: `{"user_id": "alice", "token": "eyJ...", "pqc": true}`
`401` on invalid credentials.

### `GET /v1/auth/me`
Return the current auth context. In open mode returns `{"auth_required": false, "mode": "open"}`.

### `POST /v1/auth/api_keys`
Mint a new API key for the caller.

Request: `{"name": "ci-runner"}`
Response: `{"api_key": "od_...", "user_id": "alice"}`

### `GET /v1/auth/status`
Report whether PQC is available and which algorithms are in use.

Response:
```json
{"pqc_available": true, "auth_required": false, "sig_algorithm": "ML-DSA-65", "kem_algorithm": "ML-KEM-768"}
```

### `GET /v1/auth/audit?limit=100`
Return the tail of the hash-chained audit log plus a chain-verification result.
Requires the `admin` scope when auth is enforced.

Response:
```json
{"chain": {"ok": true, "verified": 132}, "entries": [{"id": 132, "ts": 1712500000.1, "actor": "alice", "action": "user.login", "resource": null, "ip": "127.0.0.1", "record_hash": "..."}]}
```

## Phase 5: Per-user workspaces

Workspaces live under `~/.opendna/workspaces/<user>/<name>/`. When a password
is supplied, projects are AES-256-GCM encrypted with a scrypt-derived key. A
wrap-check ciphertext verifies the password before anything is decrypted.

### `POST /v1/workspaces/open`
Open (create if missing) a workspace.

Request:
```json
{"user_id": "alice", "password": "s3cret", "name": "default"}
```

Response:
```json
{"user_id": "alice", "name": "default", "encrypted": true, "encryption_available": true, "projects": ["my-protein"]}
```

`401` if the password is wrong (wrap-check fails).

### `GET /v1/workspaces/{user_id}`
List every workspace name for a user.

Response: `{"workspaces": ["default", "research"]}`.

### `POST /v1/workspaces/save_project`
Persist a project payload to the workspace.

Request:
```json
{"user_id": "alice", "password": "s3cret", "name": "default",
 "project_name": "my-protein", "payload": {"pdb": "...", "notes": "..."}}
```

Response: `{"path": "/.../my-protein.json", "encrypted": true}`.

### `POST /v1/workspaces/load_project`
Load and return a project payload.

Response: `{"project": {...}}`. `404` if the project does not exist.

## Phase 6: Priority queue, pub/sub, GPU pool

All heavy jobs now flow through a single priority queue (SQLite-backed at
`~/.opendna/jobs.db`) with three priority levels: `0` interactive,
`1` normal, `2` batch. Progress events are streamed via WebSocket.

### `GET /v1/queue/stats`
Return queue + GPU pool snapshot.

Response:
```json
{
  "queue": {"queued": 1, "running": 1, "completed": 42, "failed": 0, "workers": 2},
  "gpu": {"backend": "cuda", "device": 0, "total_mb": 24564, "free_mb": 20800, "warm_models": 2}
}
```

### `GET /v1/queue/jobs?user_id=alice`
List jobs (optionally filtered by user).

### `GET /v1/queue/jobs/{job_id}`
Return a single job record: `id, type, status, progress, priority, user_id, created_at, started_at, finished_at, result, error, messages`.

### `POST /v1/queue/enqueue`
Submit a new job. Supported `kind`s: `fold`, `design`, `md`, `dock`, `multimer`.

Request:
```json
{"kind": "fold", "params": {"sequence": "MKT..."}, "priority": 0, "user_id": "alice"}
```

Response: `{"job_id": "job-...", "priority": 0}`.

```bash
curl -X POST http://127.0.0.1:8765/v1/queue/enqueue \
  -H 'Content-Type: application/json' \
  -d '{"kind": "fold", "params": {"sequence": "MKT"}, "priority": 0}'
```

### WS `/v1/ws/jobs/{job_id}`
Stream job progress. Messages are JSON objects with an `event` field:

| event | Description |
|---|---|
| `snapshot` | Initial state on connect |
| `progress` | `{stage, fraction}` update |
| `finished` | Terminal event, job succeeded |
| `final` | Catch-up terminal state for clients joining after completion |
| `heartbeat` | Sent every 30s when idle |
| `error` | `reason` field describes failure |

### `GET /v1/gpu/info`
Return GPU backend info: `{backend, device, total_mb, free_mb, warm_models}`.

### `POST /v1/gpu/evict_warm?older_than_s=300`
Evict warm-cached models older than N seconds. Response: `{"evicted": <int>}`.

## Phase 7: Reliability

### `GET /v1/health`
Run every registered health check once and return results.

Response:
```json
{"overall": "ok", "checks": [{"name": "gpu_memory", "ok": true, "fixed": false}, {"name": "disk_space", "ok": true}]}
```

### `GET /v1/crashes?limit=50`
Return the tail of the local crash log (PII redacted via regex).

### `DELETE /v1/crashes`
Clear the crash log. Response: `{"deleted": <int>}`.

## Phase 8: Provenance DAG + time machine

Every compute step can be recorded as a node in a per-project provenance
graph stored at `~/.opendna/provenance.db`. Nodes carry inputs, outputs, an
optional score, and parent node IDs.

### `POST /v1/provenance/record`
Record a step.

Request:
```json
{
  "project_id": "my-protein",
  "kind": "design",
  "inputs": {"pdb_string": "..."},
  "outputs": {"sequence": "MKT..."},
  "score": 0.82,
  "parent_ids": ["node-abc"],
  "actor": "alice"
}
```

Response: the created node record (`{id, ts, project_id, kind, inputs, outputs, score, actor}`).

### `GET /v1/provenance/{project_id}`
Return the full DAG for a project: `{nodes, edges, stats}`.

### `GET /v1/provenance/node/{node_id}`
Return a single node record. `404` if not found.

### `GET /v1/provenance/lineage/{node_id}`
Walk parents all the way back; returns every ancestor node in order.

### `GET /v1/provenance/diff?a=<id>&b=<id>`
Diff two provenance nodes, returning changed input/output keys and score delta.

### `GET /v1/provenance/blame?project_id=...&residue=<int>`
Given a residue index, return the sequence of design steps that touched it.

### `GET /v1/provenance/bisect?project_id=...&threshold=0.0`
Walk the DAG and report the first node whose score dropped below the threshold.

## Phase 9: Visual workflow editor

### `GET /v1/workflow/node_types`
Enumerate every registered node type for the graph editor. Built-ins include
`fold`, `design`, `evaluate`, `analyze`, `dock`, `md`, `multimer`,
`fetch_uniprot`, `fetch_pdb`, `constant`.

### `POST /v1/workflow/run_graph`
Submit a workflow DAG to the priority queue.

```json
{
  "workflow": {
    "nodes": [{"id": "n1", "kind": "fetch_uniprot", "params": {"accession": "P01308"}},
              {"id": "n2", "kind": "fold", "params": {}}],
    "edges": [{"source": "n1", "target": "n2", "out_key": "sequence", "in_key": "sequence"}]
  },
  "project_id": "insulin",
  "actor": "alice"
}
```

Response: `{"job_id": "job-..."}`. Subscribe to `/v1/ws/jobs/{job_id}` for progress.

## Phase 10: External services + vendors + webhooks

### `GET /v1/ncbi/search?db=protein&term=insulin&retmax=20`
ESearch against NCBI E-utils.

### `GET /v1/ncbi/fetch?db=protein&id=P01308&rettype=fasta`
EFetch a single record.

### `GET /v1/pubmed/search?query=alphafold&retmax=20`
PubMed literature search.

### `GET /v1/pubmed/summarize?pmid=35981056`
Return ESummary metadata for a single PMID.

### `GET /v1/uniprot/search?query=insulin&size=25&reviewed_only=true&organism=Homo+sapiens`
Search UniProt. Response is the UniProt REST JSON trimmed to essentials.

### `GET /v1/uniprot/{accession}`
Return the sequence + metadata for a UniProt accession.

### `GET /v1/alphafold/{uniprot_id}?with_meta=false`
Fetch the AlphaFold DB structure for a UniProt ID. With `with_meta=true` returns
pLDDT and PAE metadata alongside the PDB.

### `GET /v1/vendors`
List supported synthesis vendors.

### `POST /v1/vendors/quote`
Request a synthesis price quote.

Request: `{"sequence": "ATGCC...", "kind": "dna_gene", "vendor": "idt"}`
Response: `{"vendor": "idt", "price_usd": 285.0, "lead_time_days": 10}`

### `POST /v1/vendors/order`
Place a synthesis order. Fires webhooks on `vendor.order` and records an audit entry.

Request:
```json
{"sequence": "ATGCC...", "vendor": "idt", "product": "gblock",
 "customer_email": "alice@lab.org", "notes": ""}
```

Response: `{"order_id": "ord-...", "status": "submitted"}`.

### `POST /v1/notify`
Send a Slack/Teams/Discord notification via incoming webhook.

Request: `{"text": "MD finished!", "channel": "slack", "webhook_url": "https://hooks.slack.com/..."}`
Response: `{"sent": true}`.

### `GET /v1/webhooks`
List all registered outbound webhooks.

### `POST /v1/webhooks`
Register a webhook.

Request: `{"url": "https://example.com/hook", "event": "vendor.order", "secret": "sh..."}`
Response: `{"id": "wh-..."}`.

### `DELETE /v1/webhooks/{wid}`
Delete a webhook. Response: `{"deleted": true}`.

## Phase 12: Lab notebook, DOI/Zenodo, figure/3D export

### `POST /v1/notebook/entries`
Append a markdown entry to a project notebook. Optionally attach a list of
provenance node IDs.

Request:
```json
{"project_id": "my-protein", "title": "Run 3 design sweep", "body_md": "Results...",
 "tags": ["design"], "prov_node_ids": ["node-abc"], "author": "alice"}
```

### `GET /v1/notebook/{project_id}/entries`
List entries for a project.

### `GET /v1/notebook/{project_id}/entries/{entry_id}`
Return a single entry. `404` if not found.

### `GET /v1/notebook/{project_id}/attachments`
List files in the project's notebook attachment directory.

### `POST /v1/zenodo/mint`
Mint a Zenodo DOI for a dataset / software release. Creates a local deposit
stub when `ZENODO_TOKEN` is not set.

Request:
```json
{"title": "OpenDNA results", "description": "...", "creators": [{"name": "Alice"}],
 "files": ["report.pdf"], "keywords": ["protein design"], "upload_type": "software"}
```

### `GET /v1/zenodo/deposits`
List locally recorded Zenodo deposits.

### `POST /v1/export/figure`
Render a figure from a data dict to SVG or PNG.

Request: `{"data": {"x": [1,2,3], "y": [4,5,6]}, "title": "MD RMSD", "xlabel": "ns", "ylabel": "Å", "format": "svg"}`
Response: `{"format": "svg", "svg": "<svg>...</svg>"}` or `{"format": "png", "base64": "..."}`.

### `POST /v1/export/3d`
Convert a PDB string to glTF or OBJ for 3D printing / web viewers.

Request: `{"pdb_string": "...", "format": "gltf"}`
Response: `{"format": "gltf", "gltf": "..."}` or `{"format": "obj", "text": "..."}`.

### `POST /v1/export/trajectory_gif`
Render a multi-frame PDB trajectory to an animated GIF.

Request: `{"pdb_frames": ["FRAME1...", "FRAME2..."], "fps": 10}`
Response: `{"path": "/tmp/...gif", "frames": 50, "fps": 10, "gif_b64": "..."}`.

## Phase 13: CRDT real-time co-editing

The server acts as a y-websocket compatible relay with per-room append-only
persistent logs at `~/.opendna/crdt/<room>.ylog`.

### WS `/v1/crdt/{room_name}`
Connect to a Yjs room. Binary messages are relayed to all other peers; any
non-awareness update is persisted. New clients receive a replay of the log on
connect so they converge to current state.

### `GET /v1/crdt`
Return active room statistics: `{"rooms": [{"name": "alice/my-protein", "clients": 2, "log_size": 4096}]}`.

## Phase 14: Academy

### `GET /v1/academy/levels`
List every training level (1-7) with metadata.

### `GET /v1/academy/levels/{level_id}`
Return one level's full content. `404` if the level does not exist.

### `GET /v1/academy/badges`
Return the badge catalog.

### `GET /v1/academy/glossary`
Return the in-app glossary.

### `GET /v1/academy/daily?date=YYYY-MM-DD`
Return the daily challenge (today if date omitted).

### `POST /v1/academy/daily/answer`
Submit a daily-challenge answer.

Request: `{"user_id": "alice", "sequence": "MKT...", "date": "2026-04-07"}`
Response: `{"correct": true, "score": 0.95, "badge_awarded": "daily-streak-7"}`.

### `GET /v1/academy/leaderboard?limit=20`
Return the top N users with their points.

## Phase 15: LLM polish (Ollama manager)

### `GET /v1/llm/ollama/status`
Report install + runtime status of the local Ollama daemon.

Response:
```json
{"installed": true, "running": true, "default_model": "llama3.2:3b", "models": ["llama3.2:3b"]}
```

### `POST /v1/llm/ollama/install`
Attempt a best-effort auto-install of Ollama for the current platform.

### `POST /v1/llm/ollama/pull`
Pull a model.

Request: `{"model": "llama3.2:3b"}`
Response: `{"model": "llama3.2:3b", "status": "pulled"}`.

### `POST /v1/llm/chat/stream`
Streaming chat completion with multi-turn session memory.

Request:
```json
{"session_id": "sess-1", "message": "Explain the pLDDT score",
 "system": "You are...", "model": "llama3.2:3b", "temperature": 0.7}
```

Response: `text/plain` stream of token chunks. The assistant reply is auto-appended to session history.

### `GET /v1/llm/chat/history/{session_id}`
Return the stored chat history for a session.

### `DELETE /v1/llm/chat/history/{session_id}`
Clear a session's history.

## Phase 16: Compliance

### `GET /v1/compliance/sbom`
Generate a CycloneDX 1.5 SBOM of the running environment.

### `GET /v1/compliance/airgap`
Report air-gap readiness (cached models, sidecar present, external endpoints disabled).

### `POST /v1/compliance/airgap/bundle`
Build an offline artifact bundle.

Request: `{"out_dir": "./opendna-airgap"}`
Response: `{"out_dir": "...", "files": [...], "total_mb": 15234}`.

### `GET /v1/compliance/privacy`
Return the local data inventory + what leaves the machine.

### `GET /v1/compliance/hipaa`
Return the HIPAA readiness checklist with pass/fail per control.

### `GET /v1/compliance/gdpr`
Return the GDPR readiness checklist.

### `POST /v1/compliance/export_user_data`
GDPR right-to-data-portability. Packs every record tied to `user_id` into a zip.

Request: `{"user_id": "alice", "out_path": "./alice-export.zip"}`
Response: `{"zip": "./alice-export.zip", "items": 42, "bytes": 102400}`.

### `POST /v1/compliance/delete_user_data`
GDPR right-to-erasure. Deletes workspaces, audit entries, and chat history for the user, then appends a `gdpr.erasure` audit event.

Request: `{"user_id": "alice"}`
Response: `{"deleted": {"workspaces": 1, "projects": 7, "audit_entries": 0, "chat_sessions": 3}}`.

```bash
curl -X POST http://127.0.0.1:8765/v1/compliance/delete_user_data \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice"}'
```
