# Getting Started with OpenDNA

A step-by-step guide to install OpenDNA and run your first protein analysis.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [First Run](#first-run)
4. [Your First Analysis](#your-first-analysis)
5. [Common Issues](#common-issues)

---

## Prerequisites

### Required
- **Python 3.10 or later** — [Download Python](https://www.python.org/downloads/)
- **Node.js 18 or later** — [Download Node.js](https://nodejs.org/)
- **Git** — [Download Git](https://git-scm.com/downloads)
- **8 GB RAM** minimum (16 GB recommended)
- **20 GB free disk space** (for ML models)

### Optional but recommended
- **NVIDIA GPU with CUDA 12.x** — makes folding ~50x faster
- **Apple Silicon Mac (M1/M2/M3)** — Metal acceleration works automatically
- **Ollama** — for AI-powered protein explanations: [https://ollama.com](https://ollama.com)

### Check your Python version

```powershell
python --version
# Should print Python 3.10.x or later
```

If you don't have Python 3.10+, install it from python.org. On Windows, make sure to check "Add Python to PATH" during installation.

---

## Installation

### Step 1: Clone the repository

```bash
git clone https://github.com/dyber-pqc/OpenDNA.git
cd OpenDNA
```

### Step 2: Install Python dependencies

OpenDNA ships a lightweight core plus optional extras. Pick the combination that matches your workflow:

```bash
# Minimal core (CLI + API + sequence analysis, no heavy ML)
pip install -e .

# Core + ML engines (ESMFold, ESM-IF1, Boltz, DiffDock, xTB, ANI-2x)
pip install -e ".[ml]"

# Core + molecular dynamics (OpenMM, AMBER14, explicit solvent)
pip install -e ".[md]"

# Core + post-quantum authentication (liboqs, ML-KEM-768, ML-DSA-65)
pip install -e ".[pqc]"

# Everything — the "kitchen sink" install
pip install -e ".[ml,md,pqc,dev]"
```

From PyPI the same extras are available:

```bash
pip install opendna                 # lightweight
pip install "opendna[ml]"           # + ML folding/design engines
pip install "opendna[md]"           # + OpenMM molecular dynamics
pip install "opendna[pqc]"          # + post-quantum auth
pip install "opendna[ml,md,pqc]"    # + everything
```

The core install brings in:
- FastAPI + Uvicorn (API server)
- Typer + Rich (CLI)
- biotite + biopython (structure / sequence I/O)
- numpy, scipy, matplotlib (scientific stack)

The `[ml]` extra adds PyTorch, transformers, fair-esm, torch-geometric, and the heavy dependencies needed to actually run ESMFold, ESM-IF1, DiffDock, RFdiffusion, Boltz-1, ColabFold, xTB, and ANI-2x. These are opt-in because the wheels total ~4 GB.

The `[pqc]` extra adds `liboqs-python`. You must also have the system `liboqs` library installed. On macOS: `brew install liboqs`. On Debian/Ubuntu: `sudo apt install liboqs-dev`. On Windows use the pre-built binaries from the [Open Quantum Safe project](https://github.com/open-quantum-safe/liboqs).

**For NVIDIA GPU users:** After the above, also install CUDA-enabled PyTorch:
```bash
pip uninstall torch -y
pip install torch --index-url https://download.pytorch.org/whl/cu124
```
*Note: As of Python 3.14, CUDA wheels may not yet be available. CPU-only torch still works.*

### Step 3: Install UI dependencies

```bash
cd ui
npm install
cd ..
```

This installs React, Vite, Molstar, and ~370 other packages. Takes ~3 minutes.

### Step 4: Verify installation

```bash
python -m pytest tests/python/
```

You should see `18 passed` (or similar). If anything fails, see [Troubleshooting](TROUBLESHOOTING.md).

---

## First Run

OpenDNA has two parts that need to run together:
1. **API server** (Python) — does the science
2. **Web UI** (TypeScript/React) — shows the visuals

You'll need **two terminals open simultaneously**.

### Terminal 1: Start the API server

```powershell
# Windows PowerShell
python -c "from opendna.api.server import start_server; start_server(port=8765)"
```

```bash
# Mac / Linux
python -c "from opendna.api.server import start_server; start_server(port=8765)"
```

You should see:
```
INFO:     Started server process [12345]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8765 (Press CTRL+C to quit)
```

**Why port 8765 and not 8000?** Port 8000 is reserved on many Windows installations. 8765 avoids the conflict.

### Terminal 2: Start the UI

```bash
cd ui
npm run dev
```

You should see:
```
  VITE v8.x.x  ready in 234 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h + enter to show help
```

### Open the browser

Navigate to **http://localhost:5173** in any modern browser (Chrome, Firefox, Edge, Safari).

You should see the OpenDNA interface with:
- Header bar with "OpenDNA" logo
- Sidebar on the left (Tools / Structures / Import tabs)
- Main viewer area with "No Protein Loaded"
- Chat panel at the bottom

---

## Your First Analysis

Let's analyze a real, well-known protein: **insulin A-chain** (21 amino acids).

### Step 1: Score a sequence (instant, no model download needed)

1. In the **Tools** tab, paste this into the sequence box:
   ```
   GIVEQCCTSICSLYQLENYCN
   ```
2. Click **Score Protein**
3. You'll see a property card with:
   - Overall score (0-100)
   - Stability, solubility, immunogenicity ratings
   - Plain-English summary
   - Recommendations

### Step 2: Run the full analysis suite

1. With the same sequence still loaded, click **Full Analysis Suite**
2. A new panel opens with **18+ analyses**:
   - Sequence properties (MW, pI, GRAVY, etc.)
   - Lipinski Rule of Five
   - Hydropathy profile (Kyte-Doolittle plot)
   - Disorder prediction
   - Amino acid composition
   - Transmembrane regions
   - Signal peptide detection
   - Aggregation risk
   - Phosphorylation sites
   - N/O-glycosylation sites

### Step 3: Predict the structure (downloads model, ~10 min first time)

1. Click **Predict Structure**
2. **First-time only:** ESMFold downloads (~8 GB). Watch the API terminal for progress.
3. After download, folding begins. For 21 residues on CPU it takes ~30 seconds.
4. The 3D structure appears in the viewer.
5. Click **pLDDT colors** at the bottom-left to see confidence coloring.

### Step 4: Save your work

1. Click **Save PDB** in the header to download the structure file
2. Or press **Cmd+K** → type "save project" → name it → it saves to `~/.opendna/projects/`

### Step 5: Try a famous protein

1. Click the **Import** tab in the sidebar
2. Click **ubiquitin** in the famous proteins grid
3. Real ubiquitin (76 aa) loads from UniProt
4. Click **Predict Structure** to fold it (~2 min on CPU)
5. Click **Design 10 Sequences (ESM-IF1)** to generate alternatives

---

## Common Issues

### "ERROR: bind on address ('0.0.0.0', 8000): permission denied"
Use a different port: `start_server(port=8765)`. Port 8000 is reserved on many Windows installations.

### "Torch not compiled with CUDA enabled"
You have an NVIDIA GPU but installed CPU-only PyTorch. Either:
- Install CUDA torch: `pip install torch --index-url https://download.pytorch.org/whl/cu124`
- Or just accept CPU mode (folding will be slower but works)

### "Cannot fetch http://localhost:8765/v1/..."
The API server isn't running. Check Terminal 1.

### Models won't download
Check your internet connection. ESMFold is ~8 GB from HuggingFace Hub. The first run is slow.

### UI is blank
Check browser console (F12) for errors. Make sure both terminals are running.

### "PermissionError: temp file ... in use" on Windows
Cosmetic issue with SQLite cleanup on Windows. Tests still pass. Ignored.

For more issues see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## The Desktop App (v0.5+)

As of v0.5.0, OpenDNA ships as a one-click Tauri desktop app in addition to the browser UI. The app bundles a PyInstaller-built Python sidecar so end users do **not** need to install Python at all for the GUI path.

Installers for Windows (`.msi`, `.exe`), macOS (`.dmg`, `.app`), and Linux (`.AppImage`, `.deb`, `.rpm`) are attached to every GitHub release under **Assets**. Download, install, launch. The sidecar auto-starts on first window open and the backend status banner at the top of the UI will turn green within a few seconds.

If you are a developer running from source, `npm run tauri:dev` inside `ui/` launches the desktop shell against your local API server.

---

## The Header Buttons (v0.5)

The top bar of the desktop app and web UI gained nine new buttons in v0.5.0. From left to right:

| Button | Opens | Purpose |
|---|---|---|
| Search | Search overlay | Full-text UniProt + PDB + AlphaFold DB search, reviewed-only filter, organism filter |
| Components | Component Manager | Install / uninstall the 11 ML engines on demand |
| Workflow | Visual workflow editor | React Flow canvas — drag nodes, connect edges, save/load YAML |
| Collab | Collaboration panel | Yjs CRDT rooms, shared notes, residue comments |
| Mini-games | Academy mini-games | AA Match, Build-a-Helix, Famous Proteins tour |
| Ramachandran | Ramachandran plot | Interactive phi/psi scatter, click dots to highlight residues |
| Explorer | File explorer | Browse `~/.opendna/projects/` from within the app |
| Save | Save dialog | PDB, project, figure, 3D export (GLTF/OBJ/animated GIF) |
| Account | Auth overlay | Log in / register / manage API keys (only shown when PQC auth is enabled) |

The legacy buttons (Command Palette, Dashboard, Academy, theme toggle) are still there — just to the right of the new ones.

---

## Component Manager Flow

Heavy ML models are no longer downloaded on first use. Instead they are installed explicitly from the Component Manager, which behaves like a package catalog:

1. Launch the desktop app (or browser UI).
2. Click **Components** in the header.
3. Browse the 11 engines, grouped by category:
   - **Folding**: ESMFold, ColabFold, Boltz-1
   - **Design**: ESM-IF1, RFdiffusion
   - **Docking**: DiffDock, AutoDock Vina
   - **Dynamics**: OpenMM, xTB
   - **QM / NNP**: ANI-2x
   - **Multimer**: Boltz-1 (multimer mode)
4. Each card shows: description, size on disk, citation, license, status (Not installed / Installing / Installed / Update available).
5. Click **Install**. A progress bar streams from `POST /v1/components/install` and the engine is ready the moment it hits 100%.
6. Uninstall at any time with the Uninstall button — the manager knows how to remove the model weights and clear the HuggingFace cache entry.

Disk usage totals are shown at the top of the manager and mirror `~/.opendna/components/`.

You can also drive the manager from the CLI:

```bash
opendna components list
opendna components install esmfold
opendna components install diffdock --force
opendna components uninstall boltz
opendna components disk-usage
```

---

## 5-Minute Tour

This tour touches the most important v0.5 features. Assumes the desktop app is running (or both dev servers plus `http://localhost:5173`).

1. **Search UniProt.** Click **Search** in the header. Type `kinase`, check **Reviewed only**, set Organism = `Homo sapiens`. Click any result — it loads into the sidebar.
2. **Fold it.** Click **Predict Structure** in the Tools tab. If ESMFold is not installed yet, the Component Manager opens automatically with the ESMFold card highlighted. Install it (~2 GB), then refold.
3. **Open the Ramachandran plot.** Click **Ramachandran** in the header. You'll see the phi/psi scatter for every residue. Click any dot — the corresponding residue is highlighted in the 3D viewer.
4. **Open the workflow editor.** Click **Workflow**. Click **Templates → Fold → Design → Evaluate**. A pre-built 5-node graph appears. Click **Run**. The viewer updates in real time as each node completes.
5. **Save the project.** Click **Save** → **Project**. Give it a name. It lands in `~/.opendna/projects/<name>/` along with a provenance DAG you can later diff.

Total time: under five minutes on a modern machine with ESMFold already installed.

---

## Post-Quantum Auth Setup

The API server runs unauthenticated by default. To turn on OpenDNA's PQC auth layer:

1. Install the optional extra:
   ```bash
   pip install "opendna[pqc]"
   ```
   You also need the system `liboqs` library. See the Installation section above.
2. Enable auth on the server by setting an environment variable before starting it:
   ```bash
   export OPENDNA_AUTH_REQUIRED=1
   export OPENDNA_AUTH_DB=~/.opendna/auth.db
   python -c "from opendna.api.server import start_server; start_server(port=8765)"
   ```
   On Windows PowerShell:
   ```powershell
   $env:OPENDNA_AUTH_REQUIRED="1"
   python -c "from opendna.api.server import start_server; start_server(port=8765)"
   ```
3. Register the first user (which automatically becomes admin):
   ```bash
   curl -X POST http://127.0.0.1:8765/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"username": "alice", "password": "correct horse battery staple"}'
   ```
   The response contains an ML-KEM-768 encapsulated API key and the public ML-DSA-65 verification key. Store the API key securely — it is the only time it will be shown.
4. All subsequent API calls must include `Authorization: Bearer <api-key>`.
5. Every authenticated request is appended to a hash-chained audit log at `~/.opendna/audit.log`. The log is tamper-evident — each entry is signed with ML-DSA-65 and the hash chain is verified on startup.

See the User Guide section **PQC Auth Layer** for advanced topics (key rotation, GDPR export, role-based access).

---

## Air-Gapped Install

For regulated environments (hospitals, defense labs, pharma) OpenDNA supports fully offline install via capability bundles.

1. On a machine **with** internet access, download the air-gap bundle for your target platform:
   ```bash
   curl -o opendna-airgap.tar.zst \
     "http://localhost:8765/v1/compliance/airgap/bundle?platform=linux-x64&include_models=esmfold,esm_if1"
   ```
   The bundle contains Python wheels for every dependency, the Tauri installer, selected model weights, a CycloneDX SBOM, and a manifest of SHA-256 hashes.
2. Transfer `opendna-airgap.tar.zst` to the offline machine via your approved transfer process (USB, data diode, etc.).
3. On the offline machine:
   ```bash
   tar --zstd -xvf opendna-airgap.tar.zst
   cd opendna-airgap/
   ./install-offline.sh   # or install-offline.ps1 on Windows
   ```
4. The installer verifies every file against the manifest, installs wheels into a local virtualenv, and drops model weights into `~/.opendna/components/`.
5. Run `opendna compliance verify` to confirm the SBOM matches what is actually installed.

See the User Guide section **Compliance & Air-gap** for the full HIPAA / GDPR checklist.

---

## Next Steps

Now that you have OpenDNA running:

1. **Read the [User Guide](USER_GUIDE.md)** — every feature explained
2. **Try the [Tutorials](TUTORIALS.md)** — guided walkthroughs
3. **Browse the [Cookbook](COOKBOOK.md)** — recipes for common tasks
4. **Learn the [Science](SCIENCE.md)** — what each algorithm does
5. **Open the Protein Academy** — interactive learning games

---

## Stopping OpenDNA

- In the API terminal, press **Ctrl+C** to stop the server
- In the UI terminal, press **Ctrl+C** to stop Vite
- Models stay cached in `~/.cache/huggingface/` — don't need to re-download
- Projects are saved to `~/.opendna/projects/`
