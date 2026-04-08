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

---

# v0.5.0 architecture additions

v0.5.0-rc1 introduces sixteen subsystems on top of the original three-process
core (UI + Python API + Rust helpers). Every subsystem is optional and each
one degrades gracefully when its heavy dependencies are missing, so the
"laptop install" path never breaks.

## Bundled sidecar (Phase 1)

Previous releases required the user to `pip install opendna` into a system
Python before the Tauri shell could find a backend. v0.5.0 ships a
PyInstaller-built `opendna-server` binary through Tauri's `externalBin`
mechanism. When the user launches the desktop app, `lib.rs` tries three
strategies in order:

```text
                       start_api_server()
                               |
           +-------------------+-------------------+
           |                   |                   |
           v                   v                   v
   find_bundled_sidecar()  verify_opendna()    error: "reinstall"
   (externalBin-copied     on discovered       or install Python
    opendna-server)        Python interps      manually
           |
     spawn with
     stdin/out/err -> /dev/null
     CREATE_NO_WINDOW (Windows)
```

The sidecar lookup checks the exe dir, `resources/binaries/`, and
`../binaries/` (for cargo-run dev mode). The triple `stdio::null()` avoids
the deadlock we used to hit when pipe buffers filled during long model loads,
and `CREATE_NO_WINDOW` stops Windows from flashing a `cmd.exe` console.

`python/opendna_server/__main__.py` is the PyInstaller entry point; it
unpacks, installs a `sys.path` shim, and calls `start_server()` from
`opendna.api.server`.

## Component Manager (Phase 2)

Heavy models (ESMFold, RFdiffusion, DiffDock, Boltz-1, xTB, ANI-2x, Ollama
models) are not installed by default. Instead there is a *registry* of
`Component` dataclasses and a *manager* that installs them on request:

```text
opendna.components.registry          opendna.components.manager
  [Component(name, install_kind,         install_component(name) ->
             install_target, ...)]         _run(subprocess)
                                              | pip  : pip install <target>
                                              | hf   : huggingface-cli download
                                              | script: pip + docs fallback
                                              | ollama: ollama pull <tag>
                                           marker: ~/.opendna/components/<name>.installed
```

Status is resolved in this order: marker file present → `installed`,
else try the component's `import_check` snippet, else `not_installed`. A
successful install always writes the marker, so subsequent boots avoid the
import probe entirely.

Each install runs as a subprocess with output streamed line-by-line back to
an in-memory progress dict keyed by `job_id`, which the
`GET /v1/components/jobs/{id}` endpoint polls. This keeps the FastAPI event
loop free during multi-minute downloads.

## PQC auth layer (Phase 4)

Why post-quantum now? A long-lived audit log and encrypted workspace payload
must remain secure for years. NIST standardised ML-DSA (Dilithium, signatures)
and ML-KEM (Kyber, key exchange) in FIPS 204/203 in 2024. We use both:

- **ML-DSA-65** signs bearer tokens (user identity)
- **ML-KEM-768** is reserved for forward-secret session keys in a future collab
  transport (currently unused)
- **SPHINCS+** is staged as a hash-based backup in case a Dilithium weakness emerges

liboqs is loaded opportunistically. If `import oqs` fails, the module flips
`PQC_AVAILABLE = False` and every token is signed with HMAC-SHA256 over the
user's derived secret. Tokens carry an `algorithm` field so downstream services
can reject non-PQC sessions in hardened mode.

The audit log (`python/opendna/auth/audit.py`) is an append-only SQLite table
with hash-chained records: each record's hash is
`sha256(prev_hash || ts || actor || action || resource || ip || details)`.
Tampering with any historical row breaks every subsequent hash, which
`verify_chain()` walks on demand. This gives us tamper-evident logging without
a blockchain.

```text
+----+-----+-------+-------+---------+----------+-----------+----------------+
| id | ts  | actor | action| resource| ip       | details   | record_hash    |
+----+-----+-------+-------+---------+----------+-----------+----------------+
|  1 | ... | alice | login | -       | 127.0.0.1| {...}     | hash(prev=GEN..)|
|  2 | ... | alice | save  | proj-1  | 127.0.0.1| {enc:T}   | hash(prev=r1..) |
|  3 | ... | bob   | login | -       | 10.0.0.4 | {pqc:T}   | hash(prev=r2..) |
+----+-----+-------+-------+---------+----------+-----------+----------------+
```

## Workspaces and encryption-at-rest (Phase 5)

Each user gets a per-workspace directory under `~/.opendna/workspaces/`. Inside
is a `meta.json` holding the workspace descriptor plus `projects/*.json.enc`
payloads. When a password is provided:

1. Generate or load a 16-byte `key_salt` from meta
2. `data_key = scrypt(password, salt=key_salt, n=2^14, r=8, p=1, dklen=32)`
3. Encrypt each project with `AES-256-GCM(data_key, nonce=random12, payload)`
4. Persist a short "wrap-check" ciphertext (a fixed plaintext encrypted with the
   same key). Wrong passwords fail AEAD auth on this small blob *before* we
   decrypt user data, producing a clean 401.

When the `cryptography` package is missing, we store blobs with a `PLAIN` prefix
so dev installs keep working; the `encryption_available` flag surfaces this in
API responses.

## Priority queue + pub/sub (Phase 6)

`opendna.runtime.job_queue.JobQueue` is a binary heap keyed on
`(priority, seq)`. Workers wait on an `asyncio.Condition`; `submit()` pushes
an entry and calls `cond.notify_all()`, which wakes a single worker to pull
from the heap.

```text
            submit(fn, priority)
                 |
                 v
     +----------------------+
     |  min-heap (priority, |  <-- workers pop smallest priority
     |  seq, job_id, fn)    |
     +----------------------+
                 |
       on_progress callback
                 |
                 v
     +-----------------------+
     | _subscribers[job_id]  |-----> WS /v1/ws/jobs/{id}
     |  (Set[asyncio.Queue]) |
     +-----------------------+
                 |
                 v
       SQLite persistence
       (~/.opendna/jobs.db)
```

Every job is mirrored into SQLite so `list()`/`get()` survive restarts.
Running jobs on shutdown are rolled back to `queued` so the next boot sees a
consistent state. The WebSocket handler registers a subscriber queue, replays a
current-state snapshot, then streams live events until `finished`/`failed`, with
30-second heartbeats in between.

## Reliability (Phase 7)

Three cooperating pieces:

- `crash.py` installs a `sys.excepthook` that writes a redacted trace to
  `~/.opendna/crashes/` (paths, emails, IPs scrubbed by regex).
- `retry.py` exposes a `@retry(attempts, backoff)` decorator with jitter.
- `health.py`'s `SelfHealer` runs registered checks on a thread loop. Default
  checks cover GPU OOM (evict warm models + `torch.cuda.empty_cache()`), DB
  locked (reopen WAL), model load (re-fetch via Component Manager), and disk
  space (truncate crash dumps + cache). Each check has an optional `fix`
  callback, so `run_once()` reports `fixed: true` when the healer recovered a
  failing component.

## Provenance DAG (Phase 8)

Every compute step is recorded as a node with `inputs`, `outputs`, optional
`score`, and parent IDs:

```text
+---------+     +---------+     +---------+
| fold A  | --> | design  | --> | evaluate|  score=0.82
+---------+     +---------+     +---------+
                     \
                      \--> +---------+
                           | mutate  | score=0.55  <-- regression
                           +---------+
```

SQLite tables: `prov_nodes(id, project_id, kind, ts, score, actor,
inputs_json, outputs_json)` and `prov_edges(parent, child)`. The store supports:

- **lineage** — recursive `WITH RECURSIVE` back-walk to genesis nodes
- **diff** — shallow set-difference of `inputs`/`outputs` keys + score delta
- **blame** — given a residue index, trawl steps whose outputs touched that residue
- **bisect** — BFS until we find the first node below a score threshold; the
  Phase 3 multi-fidelity `score` column is what makes this work (see SCIENCE.md)

## CRDT collab (Phase 13)

`opendna/collab/ywebsocket.py` speaks the y-websocket wire protocol v1:
binary messages with a one-byte type prefix (`0=sync`, `1=awareness`), followed
by a Yjs update payload. We operate as a *relay + persistent log* rather than a
CRDT-aware server: each room keeps an in-memory set of WebSocket peers and an
append-only `~/.opendna/crdt/<room>.ylog` file. New clients get a replay of the
log on connect, then join the broadcast set.

```text
 client A -->\            /--> client B
              --> Room -->
 client C -->/   |    \--> ylog (append-only)
                 v
           replay on new connect
```

## Compliance stack (Phase 16)

- **SBOM** — `compliance/sbom.py` walks `importlib.metadata` and emits a
  CycloneDX 1.5 JSON (name, version, license, PURL). Usable as-is by Grype and
  Trivy.
- **Air-gap** — `compliance/airgap.py` checks which components have been
  installed, whether the bundled sidecar is present, and which outbound
  endpoints would be used. `bundle_offline_artifacts()` copies the HF cache,
  the marker files, and the Ollama models directory into a single output tree.
- **GDPR** — `compliance/privacy.py` implements `export_user_data()`
  (portability) and `delete_user_data()` (erasure). Both walk the workspace
  directory, the audit table, the notebook database, and the chat sessions
  table, either zipping or deleting every record keyed on the user ID. Erasure
  appends a `gdpr.erasure` record to the audit log so the deletion itself is
  audited.
