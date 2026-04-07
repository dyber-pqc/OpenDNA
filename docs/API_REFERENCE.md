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
