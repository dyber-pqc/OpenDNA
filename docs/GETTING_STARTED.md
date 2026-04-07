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

```bash
pip install -e ".[dev]"
```

This installs:
- PyTorch (CPU version by default)
- transformers, fair-esm (for ESMFold and ESM-IF1)
- biotite (for structure I/O)
- FastAPI + Uvicorn (for the API server)
- Typer + Rich (for the CLI)
- All Python dependencies from `pyproject.toml`

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
