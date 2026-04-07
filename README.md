# OpenDNA

**The People's Protein Engineering Platform**

[![Version](https://img.shields.io/badge/version-0.2.0--beta-blue)](https://github.com/dyber-pqc/OpenDNA/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![Status](https://img.shields.io/badge/status-pre--alpha-orange)]()

> A free, open-source protein engineering and structural biology platform that runs on consumer hardware. The features that cost $200,000+/year in commercial software, available for free, on your laptop.

---

## What is OpenDNA?

OpenDNA is a complete protein engineering workbench that combines structure prediction, inverse folding design, molecular property analysis, mutation effect estimation, molecular dynamics, docking, and visualization — all in a single integrated desktop application. It is designed to:

- **Democratize protein engineering** so curious learners, students, citizen scientists, and underfunded labs have the same tools as Big Pharma
- **Run on consumer hardware** — gaming laptops, Apple Silicon, even CPU-only machines
- **Speak plain English** so non-experts can use it productively
- **Be transparent and explainable** — every prediction shows confidence and reasoning
- **Replace expensive commercial software** for the 80% of common workflows

---

## Quick Comparison with Commercial Software

| Feature | Schrödinger Suite | Rosetta Commons | OpenDNA |
|---|---|---|---|
| **Annual cost (per seat)** | ~$200,000 | Free for academia, $$$ for commercial | **Free, forever** |
| Structure prediction | Prime / Maestro | RoseTTAFold | ESMFold ✅ |
| Sequence design | Prime | ProteinMPNN | ESM-IF1 ✅ |
| Property analysis (QikProp) | ✅ | Manual | ✅ Built-in |
| Molecular dynamics | Desmond | RosettaMD | OpenMM (optional) |
| Docking | Glide | RosettaLigand | DiffDock (planned) |
| Lipinski / drug-likeness | ✅ | Manual | ✅ Built-in |
| Mutation effect (ΔΔG) | BioLuminate | Cartesian_ddG | ✅ Heuristic |
| Iterative optimization | IFD-MD | Loop in Python | ✅ Automated |
| Plain-English interface | ❌ | ❌ | ✅ |
| Runs on a gaming laptop | ❌ | ❌ | ✅ |
| 3D viewer | Maestro | PyMOL | ✅ Molstar |
| Source code available | ❌ | Partial | ✅ Apache 2.0 |

---

## Features

### Structure Prediction (Folding)
- **ESMFold v1** — Meta's fast structure prediction (Tier 1)
- Single-sequence inference, no MSA needed
- Confidence scoring (pLDDT) with rainbow visualization
- Cached results — fold the same sequence twice and the second time is instant

### Sequence Design (Inverse Folding)
- **ESM-IF1** — Generate alternative sequences that should fold into a given backbone
- Adjustable temperature for diversity vs. fidelity tradeoff
- Sequence recovery scoring against the original
- Up to 100 candidates per design run

### Iterative Design Loop
- Automated optimization: fold → design → score → keep best → repeat
- Configurable rounds and candidates per round
- Score history charting
- Each round's best is added to your structure library

### Sequence Analysis Suite (free QikProp equivalent)
- **Molecular weight, isoelectric point (pI), GRAVY hydropathy**
- **Aromaticity, instability index, aliphatic index**
- **Net charge at pH 7, extinction coefficients (reduced/oxidized)**
- **N-terminal half-life prediction (mammalian, yeast, E. coli)**
- **Amino acid composition (counts and percentages)**
- **Lipinski's Rule of Five for drug-likeness**
- **Kyte-Doolittle hydropathy profile (sliding window)**

### Structure-Based Analysis
- **Secondary structure assignment** (DSSP-like helix/strand/coil)
- **Ramachandran plot** with phi/psi scatter
- **Radius of gyration**
- **Solvent Accessible Surface Area (SASA) estimate**
- **Binding pocket detection**
- **H-bond, salt bridge, and disulfide bond detection**
- **Kabsch RMSD between any two structures**

### Predictors (Sequence-Only)
- **Intrinsic disorder** (IUPred-like)
- **Transmembrane helix prediction** (TMHMM-like)
- **Signal peptide detection** (SignalP-like)
- **Aggregation propensity** (TANGO-like) with risk classification
- **Phosphorylation sites** (kinase consensus motifs)
- **N- and O-glycosylation sites**
- **Mutation stability prediction** (ΔΔG heuristic)

### Visualization
- **Molstar 3D viewer** (rotate, zoom, click)
- **pLDDT confidence coloring** (AlphaFold-style blue→orange→red)
- **Chain coloring**
- **Side-by-side structure comparison**
- **Stats overlay** (atoms, residues)

### Data Sources
- **UniProt** import by accession or famous name
- **PDB** import by ID
- **AlphaFold DB** (planned)
- **Famous proteins quick-access**: ubiquitin, insulin, GFP, lysozyme, myoglobin, hemoglobin, p53, KRAS, EGFR, HER2, trypsin, BSA, actin, tubulin, COVID spike

### Drug Discovery / Real World
- **Synthesis cost estimator** — quotes for Twist Bioscience, IDT, GenScript
- **Carbon footprint tracker** — kg CO₂ per computation
- **Compute time estimator** — predict job duration before submission

### Project Workspace
- **Save / load projects** to disk
- **Persistent structure history**
- **Job queue with caching**
- **XP system** for gamification

### Natural Language
- **Chat-based control** — "fold MKTVRQERLK", "score this", "mutate K48R"
- **AI-powered explanations** — uses Ollama if installed (`llama3.2:3b`), falls back to detailed heuristic descriptions
- **Intent parser** for action mapping

### Education / Learning
- **Protein Academy** with interactive tutorials
- Level 1: Amino Acid Match (drag-drop game)
- Level 2: Property Quiz (5-question knowledge check)
- Level 3: Sequence Reader (decoding tutorial)
- XP system with badges

### Developer / UX
- **Command Palette** (Ctrl+K) — fuzzy search every action
- **Toast notifications** — never miss a result
- **Keyboard shortcuts** (F=fold, S=score, A=analyze, Cmd+S=save)
- **Dashboard** — hardware stats, job history, projects
- **Hot-reload UI** during development

---

## Quick Start

### Option 1: From source (recommended for now)

```bash
# Clone the repo
git clone https://github.com/dyber-pqc/OpenDNA.git
cd OpenDNA

# Install Python dependencies
pip install -e ".[dev]"

# Set up the UI
cd ui
npm install
cd ..
```

### Run the API server

```powershell
# Windows / Linux / Mac
python -c "from opendna.api.server import start_server; start_server(port=8765)"
```

### Run the UI (in another terminal)

```bash
cd ui
npm run dev
# Open http://localhost:5173 in your browser
```

### First protein

1. Open the UI in your browser
2. Click **Tools** tab → paste this sequence: `MKTVRQERLKSIVRILERSKEPVSGAQLAEELS`
3. Click **Score Protein** → instant property card
4. Click **Predict Structure** → watch the 3D fold appear (downloads model on first run, ~8 GB one-time)
5. Click **Full Analysis Suite** → see Ramachandran, hydropathy, all properties
6. Press **Ctrl+K** → type "import ubiquitin" → real ubiquitin loads
7. Try the **Academy** in the header for interactive tutorials

For comprehensive walkthroughs see [docs/USER_GUIDE.md](docs/USER_GUIDE.md) and [docs/TUTORIALS.md](docs/TUTORIALS.md).

---

## Documentation

- **[Getting Started](docs/GETTING_STARTED.md)** — installation, first run, troubleshooting
- **[User Guide](docs/USER_GUIDE.md)** — every feature, with screenshots
- **[Tutorials](docs/TUTORIALS.md)** — walkthroughs for common tasks
- **[API Reference](docs/API_REFERENCE.md)** — every endpoint, every parameter
- **[Architecture](docs/ARCHITECTURE.md)** — how the system fits together
- **[The Science](docs/SCIENCE.md)** — what each algorithm does and why
- **[Cookbook](docs/COOKBOOK.md)** — recipes for common workflows
- **[FAQ](docs/FAQ.md)** — common questions
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** — when things break
- **[Developer Guide](docs/DEVELOPER.md)** — contributing and extending
- **[Roadmap](docs/ROADMAP.md)** — what's next

---

## System Requirements

### Minimum (CPU only, slow but works)
- 8 GB RAM
- 20 GB free disk
- Python 3.10+
- Any 64-bit OS (Windows 10+, macOS 11+, Ubuntu 20.04+)

### Recommended (gaming laptop)
- 16 GB RAM
- NVIDIA RTX 3060+ (8 GB VRAM) **OR** Apple Silicon M1+
- 50 GB free disk
- CUDA 12.x for NVIDIA
- Python 3.10+

### Optimal (workstation)
- 32+ GB RAM
- NVIDIA RTX 4090 (24 GB VRAM) or A6000
- 200 GB free disk

---

## Tech Stack

- **Backend:** Python 3.10+ (FastAPI, PyTorch, ESM, Biotite, NumPy)
- **Rust core:** opendna-core (data models, version control), opendna-hal (hardware detection), opendna-bindings (PyO3 Python bindings)
- **Frontend:** TypeScript + React + Vite + Molstar
- **Desktop:** Tauri 2 (planned)
- **Storage:** SQLite (metadata) + JSON (projects)

---

## License

OpenDNA Core: **Apache 2.0** + Commons Clause (free for non-commercial; contact us for commercial licenses)
OpenDNA Community Modules: **MIT**
OpenDNA Documentation: **CC-BY-4.0**

---

## Acknowledgments

Built on the shoulders of giants:

- **ESMFold** by Meta AI for structure prediction
- **ESM-IF1** by Meta AI for inverse folding
- **Molstar** for 3D molecular visualization
- **Biotite** for structure I/O
- **HuggingFace** for model hosting

Inspired by the dream that protein engineering should be as accessible as web development.

---

## Status

**v0.2.0-beta** — Pre-alpha specification. Working but not production-ready. Use for learning, exploration, and research, not clinical decisions.

Current limits:
- Max sequence length: ~500 residues on consumer GPU, ~250 on CPU (memory limited)
- ESMFold downloads ~8 GB on first use (cached forever after)
- ESM-IF1 downloads ~600 MB on first use
- Single-machine only (no cluster support yet)
- No cloud sync (privacy-first by design)

---

## Get Involved

- **Star the repo** if you find this useful
- **Open an issue** if you find a bug or want a feature
- **Submit a PR** — see [docs/DEVELOPER.md](docs/DEVELOPER.md)
- **Share your discoveries** — tag projects with `#opendna`
