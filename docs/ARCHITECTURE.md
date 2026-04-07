# OpenDNA Architecture

How the system is put together. Read this if you want to understand or contribute to the codebase.

## High-Level Overview

OpenDNA is a multi-language, multi-process system:

```
┌──────────────────────────────────────────────────────────┐
│                   USER INTERFACE                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │  React + TypeScript + Vite + Molstar             │    │
│  │  ui/src/                                         │    │
│  │  - App.tsx (state, routing)                      │    │
│  │  - components/ (Sidebar, Viewer, Panels, etc.)   │    │
│  │  - api/client.ts (HTTP client)                   │    │
│  │  - hooks/ (useToasts, useKeyboard)               │    │
│  └──────────────────────────────────────────────────┘    │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP/JSON (localhost:8765)
                         │
┌────────────────────────▼─────────────────────────────────┐
│                  PYTHON API LAYER                         │
│  ┌──────────────────────────────────────────────────┐    │
│  │  FastAPI + Uvicorn                               │    │
│  │  python/opendna/api/server.py                    │    │
│  │  - 25+ REST endpoints                            │    │
│  │  - Background job queue (ThreadPoolExecutor)     │    │
│  │  - Result caching (in-memory dict)               │    │
│  └──────────────────────────────────────────────────┘    │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                   ENGINES LAYER                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │  folding     │ │  design      │ │  scoring     │    │
│  │  ESMFold     │ │  ESM-IF1     │ │  composite   │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │  analysis    │ │  iterative   │ │  disorder    │    │
│  │  QikProp-eq  │ │  loop opt.   │ │  IUPred-like │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │  predictors  │ │  bonds       │ │  alignment   │    │
│  │  TM/SP/agg/  │ │  H/SB/SS     │ │  NW + BLOSUM │    │
│  │  PTM/DDG     │ │  detection   │ │              │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │  dynamics    │ │  docking     │ │  explain     │    │
│  │  OpenMM      │ │  DiffDock    │ │  Ollama LLM  │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │  data/       │ │  data/       │ │  storage/    │    │
│  │  sources     │ │  synthesis   │ │  projects    │    │
│  │  (UniProt/   │ │  (cost/      │ │  (workspace  │    │
│  │   PDB/AF)    │ │   carbon)    │ │   save/load) │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                 RUST CORE (via PyO3)                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │ opendna-core │ │ opendna-hal  │ │ opendna-     │    │
│  │ data models  │ │ hardware     │ │ bindings     │    │
│  │ PDB parsers  │ │ detection    │ │ PyO3 glue    │    │
│  │ versioning   │ │ tier select  │ │              │    │
│  │ SQLite       │ │              │ │              │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
└──────────────────────────────────────────────────────────┘
```

---

## Directory Layout

```
opendna/
├── Cargo.toml                  # Rust workspace
├── pyproject.toml              # Python project
├── README.md
├── LICENSE
├── DEVELOPMENT.md              # Dev conventions
│
├── crates/                     # Rust core
│   ├── opendna-core/           # Data models, PDB/FASTA parsing, version control, SQLite
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── models.rs       # Protein, Sequence, Structure, Atom
│   │       ├── parsers.rs      # PDB / FASTA read/write
│   │       ├── storage.rs      # SQLite layer
│   │       └── versioning.rs   # ProteinRepository, branches, commits
│   ├── opendna-hal/            # Hardware abstraction
│   │   └── src/
│   │       ├── lib.rs
│   │       └── detect.rs       # CUDA/Metal/CPU detection, tier selection
│   └── opendna-bindings/       # PyO3 Python bindings
│       └── src/lib.rs          # Exposes Rust types to Python
│
├── python/opendna/             # Python ML layer
│   ├── __init__.py
│   ├── models/
│   │   └── protein.py          # Pure-Python data models (alternative to Rust)
│   ├── engines/
│   │   ├── folding.py          # ESMFold wrapper
│   │   ├── design.py           # ESM-IF1 wrapper
│   │   ├── scoring.py          # Composite scoring
│   │   ├── analysis.py         # Schrödinger-equivalent suite
│   │   ├── iterative.py        # Iterative design loop
│   │   ├── disorder.py         # IUPred-like disorder
│   │   ├── predictors.py       # TM, SP, aggregation, PTM, DDG
│   │   ├── bonds.py            # H-bond, salt bridge, disulfide detection
│   │   ├── alignment.py        # Needleman-Wunsch
│   │   ├── dynamics.py         # OpenMM MD wrapper
│   │   ├── docking.py          # Docking (heuristic + DiffDock-ready)
│   │   ├── explain.py          # AI explanation (Ollama + fallback)
│   │   └── nlu.py              # Natural language intent parser
│   ├── data/
│   │   ├── sources.py          # UniProt, PDB, AlphaFold DB
│   │   └── synthesis.py        # Cost & carbon estimates
│   ├── storage/
│   │   ├── database.py         # SQLAlchemy + SQLite
│   │   └── projects.py         # Project workspace save/load
│   ├── hardware/
│   │   └── detect.py           # Pure-Python hardware detection
│   ├── api/
│   │   └── server.py           # FastAPI server with all endpoints
│   └── cli/
│       └── main.py             # Typer CLI
│
├── ui/                         # React frontend
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx            # Entry point
│       ├── App.tsx             # Top-level state and routing
│       ├── App.css             # Theme variables
│       ├── api/
│       │   └── client.ts       # HTTP client + types
│       ├── hooks/
│       │   ├── useToasts.ts
│       │   └── useKeyboard.ts
│       └── components/
│           ├── Sidebar/
│           ├── ProteinViewer/  # Molstar 3D viewer
│           ├── ChatPanel/
│           ├── JobMonitor/
│           ├── CommandPalette/
│           ├── Toasts/
│           ├── AnalysisPanel/
│           ├── Dashboard/
│           ├── Academy/
│           └── IterativePanel/
│
├── tests/
│   ├── python/                 # pytest
│   │   ├── test_models.py
│   │   ├── test_scoring.py
│   │   └── test_storage.py
│   └── rust/                   # cargo test
│
├── models/                     # ML model manifest (weights downloaded at runtime)
│   ├── manifest.yaml
│   └── README.md
│
└── docs/                       # All documentation
    ├── README.md (you are here)
    ├── GETTING_STARTED.md
    ├── USER_GUIDE.md
    ├── API_REFERENCE.md
    ├── ARCHITECTURE.md
    ├── SCIENCE.md
    ├── TUTORIALS.md
    ├── COOKBOOK.md
    ├── FAQ.md
    ├── TROUBLESHOOTING.md
    ├── DEVELOPER.md
    └── ROADMAP.md
```

---

## Data Flow Examples

### Example 1: User folds a protein from the UI

```
1. User pastes sequence, clicks "Predict Structure"
   └─> ui/App.tsx::handleFold()

2. UI calls API
   └─> ui/api/client.ts::fold(sequence)
       └─> POST http://localhost:8765/v1/fold

3. API receives request
   └─> python/opendna/api/server.py::submit_fold()
       - Checks result_cache for existing result
       - If not cached, creates job in jobs dict
       - Submits _run_fold to ThreadPoolExecutor
       - Returns job_id immediately

4. Background worker runs
   └─> python/opendna/api/server.py::_run_fold()
       └─> python/opendna/engines/folding.py::fold()
           - Detects hardware via opendna.hardware.detect
           - Loads ESMFold model (cached after first run)
           - Runs inference
           - Parses output PDB string
           - Extracts pLDDT confidence
           - Updates jobs dict with result

5. UI polls job status
   └─> ui/App.tsx::pollFoldJob()
       └─> GET /v1/jobs/{job_id}
       (every 1 second)

6. When job is "completed":
   └─> UI adds the structure to state
   └─> ProteinViewer renders the PDB via Molstar
   └─> Toast appears: "Fold complete, pLDDT: 87"
```

### Example 2: User runs full analysis on a sequence

```
1. User clicks "Full Analysis Suite"
   └─> handleAnalyze()

2. POST /v1/analyze with sequence + optional pdb_string

3. Server runs sequentially (instant, no job queue):
   - compute_properties (MW, pI, GRAVY...)
   - lipinski_rule_of_five
   - hydropathy_profile
   - predict_disorder
   - predict_transmembrane
   - predict_signal_peptide
   - predict_aggregation
   - predict_phosphorylation
   - predict_glycosylation
   - If PDB: secondary_structure, ramachandran, pockets, bonds
   - Returns JSON with all results

4. UI receives response
   └─> setAnalysis(result)
   └─> AnalysisPanel renders with all sections
```

### Example 3: User imports ubiquitin via command palette

```
1. Ctrl+K → "import ubiquitin" → Enter
   └─> CommandPalette executes the registered action
       └─> handleImport("uniprot", "ubiquitin")

2. POST /v1/fetch_uniprot { accession: "ubiquitin" }

3. Server resolves "ubiquitin" → "P0CG48" via FAMOUS_PROTEINS dict
   └─> data/sources.py::fetch_uniprot()
       - HTTP GET https://rest.uniprot.org/uniprotkb/P0CG48.json
       - Parses sequence, name, organism, description
       - Returns UniProtEntry

4. UI receives entry
   └─> setCurrentSequence(entry.sequence)
   └─> setSwitchToToolsTrigger() to switch tab
   └─> Toast: "UBC_HUMAN — Loaded 685 aa from Homo sapiens"

5. Sidebar's Tools tab now shows the sequence in the textarea
```

---

## State Management

### Frontend
React `useState` hooks in `App.tsx` hold:
- `structures`: array of `StoredStructure` objects (folded proteins history)
- `activeStructureId`: which structure is currently shown in the viewer
- `compareStructureId`: optional second structure for side-by-side
- `currentSequence`: the sequence in the Tools textarea
- `score`: most recent score result
- `analysis`: most recent full analysis result
- `designResults`: array of design candidates
- `iterativeResult`: iterative design output
- `jobs`: array of running/completed jobs
- `xp`: gamification points
- `darkMode`: theme

State is **session-only** unless explicitly saved as a project.

### Backend
The Python server holds:
- `jobs: dict[str, dict]` — In-memory job store. Keys are 8-char IDs.
- `result_cache: dict[str, dict]` — Hash-based cache (e.g. `fold:SEQUENCE:method`)

These are **process-lifetime** — restarting the server clears them. Persistent storage is via SQLite (for proteins/projects) and the filesystem (for PDB files).

### Disk
- `~/.opendna/database.sqlite` — protein and job metadata
- `~/.opendna/projects/<name>/workspace.json` — saved project workspaces
- `~/.cache/huggingface/hub/` — downloaded ML models (ESMFold ~8 GB, ESM-IF1 ~600 MB)

---

## How Engines Are Added

To add a new engine (e.g. `myengine`):

1. **Write the engine**:
   ```python
   # python/opendna/engines/myengine.py
   def my_function(sequence: str) -> dict:
       return {"result": ...}
   ```

2. **Add an API endpoint**:
   ```python
   # In python/opendna/api/server.py
   @app.post("/v1/my_endpoint")
   async def my_endpoint(request: MyRequest):
       from opendna.engines.myengine import my_function
       return my_function(request.sequence)
   ```

3. **Add a client method**:
   ```typescript
   // ui/src/api/client.ts
   export const myEndpoint = (sequence: string) =>
     post<MyResult>("/v1/my_endpoint", { sequence });
   ```

4. **Wire it into the UI** (sidebar button, command palette, or analysis panel section)

5. **Add tests** in `tests/python/test_myengine.py`

---

## Performance Considerations

### Hot paths
- ESMFold inference: dominated by the model forward pass. Cache results aggressively.
- ESM-IF1 sampling: single forward pass per candidate. Batch where possible.
- Sequence analyses: O(N) where N is sequence length. Negligible.
- Structure analyses: O(N²) for distance-based things like bond detection. Cap at sequence length 500.

### Memory
- ESMFold needs ~8 GB RAM for inference on a 100-residue protein
- ESM-IF1 is ~600 MB, much lighter
- Result cache grows unbounded (clear on server restart)

### Threading
- FastAPI + Uvicorn handles concurrent requests
- Compute-heavy work runs in `ThreadPoolExecutor` (4 workers by default)
- Python's GIL limits true parallelism, but works well for a single user

---

## Security & Privacy

OpenDNA is **local-first**:
- No data leaves your machine unless you explicitly use Import (UniProt/PDB) or Cloud Burst
- No telemetry, no analytics, no tracking
- API only listens on `localhost` by default
- Models are downloaded from HuggingFace on first use, cached locally
- Projects are saved as plain JSON in your home directory

If you want to expose the API to your network or cloud, you accept the risks (no auth, no rate limiting in v0.2).

---

## Why this architecture?

### Why Python for engines?
The ML ecosystem is Python-first. PyTorch, transformers, ESM, Biotite — all Python. Trying to do this in Rust would mean reimplementing or wrapping everything.

### Why Rust for the core?
For the data model layer (PDB parsing, version control, SQLite), Rust gives:
- No memory leaks
- Cross-platform without #ifdefs
- Easy to compile to WASM later for browser-only mode
- PyO3 makes Rust callable from Python with minimal overhead

### Why a separate UI process?
- Web UI is universal — works on any device with a browser
- Separates compute (heavy) from rendering (light)
- Easy to swap with a Tauri desktop wrapper later
- Hot-reload during development

### Why FastAPI not Flask?
- Async support
- Automatic OpenAPI docs
- Type-safe with Pydantic
- Better performance under concurrent load

### Why Molstar not Three.js directly?
- Purpose-built for molecular visualization
- Handles PDB parsing, secondary structure, color schemes natively
- Battle-tested by RCSB, EBI, Mol* community
- Saves us from reimplementing molecular graphics
