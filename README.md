# OpenDNA v0.5.0-rc1 — The People's Protein Engineering Platform

[![Version](https://img.shields.io/badge/version-0.5.0--rc1-blue)](https://github.com/dyber-pqc/OpenDNA/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0%20%2B%20Commons%20Clause-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)
[![Platform](https://img.shields.io/badge/platform-Win%20%7C%20macOS%20%7C%20Linux-lightgrey)]()
[![Desktop](https://img.shields.io/badge/desktop-Tauri%202-orange)]()
[![PQC](https://img.shields.io/badge/crypto-ML--KEM%20%2B%20ML--DSA-purple)]()
[![SBOM](https://img.shields.io/badge/SBOM-CycloneDX%201.5-informational)]()
[![DOI](https://img.shields.io/badge/DOI-Zenodo%20ready-blue)]()

> OpenDNA is a complete, open-source protein engineering workbench that runs on a gaming laptop, bundles 11 ML engines behind a one-click Component Manager, stores your work in per-user AES-256-GCM encrypted workspaces, talks post-quantum (ML-KEM + ML-DSA) to its own audit log, and ships as a signed desktop installer with no Python required — the features that cost $200,000+/year in commercial software, available for free, for everyone.

---

## What's new in v0.5.0

Nineteen phases, one release. Every phase is documented in [docs/CHANGELOG.md](docs/CHANGELOG.md).

- **Phase 0** — Multi-rep 3D viewer (cartoon/stick/spacefill/surface) + click-residue popup with per-residue detail via Molstar
- **Phase 1** — PyInstaller-bundled Python sidecar wired into Tauri `externalBin`, per-platform CI builds, no system Python required
- **Phase 2** — **Component Manager**: Altium/Vivado-style catalog for 11 ML engines with live install progress and uninstall
- **Phase 3** — Real heavy models: **DiffDock, RFdiffusion, Boltz-1, ColabFold, xTB, ANI-2x** with graceful fallback when a model is absent
- **Phase 4** — **Post-quantum auth**: ML-KEM-768 key exchange + ML-DSA-65 signatures via liboqs, hash-chained tamper-evident audit log
- **Phase 5** — **Per-user workspaces** with AES-256-GCM encryption-at-rest, scrypt-derived keys
- **Phase 6** — Priority job queue (interactive/normal/batch) + WebSocket `/v1/ws/jobs/{id}` streaming + GPU pool with warm-model cache
- **Phase 7** — Local-first crash reporter with secret redaction, `@retry` decorator, `SelfHealer` background thread
- **Phase 8** — **Provenance DAG + time machine**: every step recorded, `diff_steps` / `blame_residue` / `bisect_regression`
- **Phase 9** — **Visual workflow editor** in React Flow (10 node types, auto-records to provenance)
- **Phase 10** — NCBI / PubMed / UniProt / AlphaFold DB / Twist / IDT / GenScript / Slack / Teams / Discord / generic webhooks
- **Phase 11** — **R SDK + Jupyter magics + Galaxy / Snakemake / Nextflow plugins**
- **Phase 12** — Lab notebook, **Zenodo DOI minting**, PNG/SVG figure export, GLTF/OBJ 3D export
- **Phase 13** — **Real-time co-editing** via Yjs CRDT (y-websocket-compatible relay, rooms on `/v1/crdt/{room}`)
- **Phase 14** — Academy Levels 4–7, 13 badges, 7 daily-challenge templates, 23-term glossary, SQLite leaderboard with streaks
- **Phase 15** — **Ollama auto-install** + streaming chat + multi-turn session memory for the LLM agent
- **Phase 16** — **CycloneDX 1.5 SBOM**, air-gap capability check, GDPR export/erasure, HIPAA checklist
- **Phase 17** — **Dockerfile**, Homebrew formula, Playwright E2E suite, pytest smoke suite (11/11 passing)
- **Phase 18** — 7-step onboarding tour, sequence ruler with AA coloring, global drag-and-drop FASTA/PDB, light-theme polish

---

## At a glance

| | Feature | What it does |
|---|---|---|
| 🧬 | **ESMFold** | Fast single-sequence structure prediction (Tier 1, Meta AI) |
| 🔁 | **ESM-IF1** | Inverse folding / sequence design from a backbone |
| 🎯 | **DiffDock** | Diffusion-based ligand docking, real integration (not heuristic) |
| 🧪 | **RFdiffusion** | De novo backbone generation for novel folds |
| 🔗 | **Boltz-1 multimer** | Protein complex prediction with graceful per-chain fallback |
| ⚛️ | **xTB** | Semi-empirical quantum mechanics for small-molecule energetics |
| 🌀 | **ANI-2x** | ML potential for ligand geometry refinement |
| 💧 | **OpenMM MD** | Explicit TIP3P solvent, AMBER14, NVT equilibration, production MD |
| 📊 | **MMGBSA** | Implicit-solvent binding free energy estimates |
| 🔬 | **50+ analyses** | Lipinski, hydropathy, pI, Ramachandran, disorder, TM, signal, aggregation, PTMs, Δ ΔG, H-bonds, salt bridges, SS, pockets |
| ♻️ | **Iterative design loop** | Automated fold → design → score → keep-best |
| 🎛️ | **Multi-objective Pareto** | Balance stability vs binding vs solubility with Pareto front |
| 🧩 | **Component Manager** | Altium/Vivado-style catalog for all 11 ML engines, one-click install |
| 🎨 | **Visual workflow editor** | React Flow canvas, 10 node types, run-as-template |
| 📜 | **Provenance DAG** | Every step recorded, diffable, blame-able, bisectable |
| 👥 | **Real-time collab (CRDT)** | Yjs rooms via `/v1/crdt/{room}`, y-websocket compatible |
| 🔐 | **PQC auth** | ML-KEM-768 + ML-DSA-65 via liboqs, quantum-safe tokens |
| 🔒 | **Encryption at rest** | AES-256-GCM, scrypt-derived keys, per-user workspaces |
| 📬 | **Priority job queue** | interactive / normal / batch tiers with persistence |
| 📡 | **WebSocket streaming** | Live progress on `/v1/ws/jobs/{id}` |
| 🎮 | **GPU pool** | Warm-model cache and fair scheduling |
| 🤖 | **Ollama LLM agent** | Auto-install `llama3.2:3b`, streaming chat with session memory |
| 🌐 | **Data fetchers** | NCBI, PubMed, UniProt, AlphaFold DB |
| 📄 | **Zenodo DOI minting** | `/v1/zenodo/mint` for citable datasets |
| 🧾 | **Synthesis quoting** | Twist Bioscience, IDT, GenScript live quotes |
| 🔔 | **Integrations** | Slack, Teams, Discord, generic webhooks |
| 📈 | **R SDK** | `opendna` R package for statisticians |
| 📓 | **Jupyter magics** | `%opendna_fold`, `%opendna_design`, inline viewers |
| 🛠 | **Galaxy / Snakemake / Nextflow** | First-class plugins for HPC workflow engines |
| 📦 | **CycloneDX SBOM** | 1.5 spec, every dependency pinned |
| ✈️ | **Air-gap bundle** | Offline capability check + portable mirror |
| 🇪🇺 | **GDPR export/erasure** | `/v1/compliance/export_user_data` and erasure endpoints |
| 🏥 | **HIPAA checklist** | Safeguard self-audit and policy templates |
| 🐳 | **Docker** | Single-image deployment with non-root user |
| 🍺 | **Homebrew** | `brew install opendna` formula |
| 🧪 | **Playwright E2E** | Full UI regression coverage |
| 🧭 | **Onboarding tour** | 7-step interactive walkthrough |
| 📐 | **Ramachandran plot** | φ/ψ scatter with quadrant overlay |
| 📏 | **Sequence ruler** | AA-colored strip with hover/click sync |
| 📝 | **Lab notebook** | Per-project markdown journal with autosave |
| 🎞 | **Trajectory GIF export** | MD or design-iteration reels |
| 🧊 | **GLTF / OBJ 3D export** | Drop structures into Blender or three.js |
| 🎓 | **Academy Levels 1–7** | Progressive curriculum from AA basics to drug design |
| 🎲 | **Mini-games** | Match game, quiz, sequence reader, daily challenges |
| 🏆 | **Leaderboard** | SQLite-backed streaks + 13 badges |

---

## Install

### Desktop installers (no Python required)

Download the signed installer for your OS from the [latest release](https://github.com/dyber-pqc/OpenDNA/releases/latest):

| OS | Installer |
|---|---|
| Windows | `opendna-desktop_0.5.0-rc1_x64-setup.exe` or `.msi` |
| macOS | `opendna-desktop_0.5.0-rc1_universal.dmg` |
| Linux | `.AppImage`, `.deb`, `.rpm` |

The desktop app bundles the Python sidecar via PyInstaller — nothing to `pip install`.

### From pip

```bash
pip install opendna                 # core
pip install "opendna[ml]"           # with torch / transformers / fair-esm
pip install "opendna[pqc]"          # with liboqs bindings
pip install "opendna[full]"         # everything
```

### Docker

```bash
docker run -p 8765:8765 ghcr.io/dyber-pqc/opendna:0.5.0-rc1
```

### Homebrew (macOS / Linux)

```bash
brew tap dyber-pqc/opendna
brew install opendna
```

### From source

```bash
git clone https://github.com/dyber-pqc/OpenDNA.git
cd OpenDNA
pip install -e ".[full]"
cd ui && npm install && cd ..
```

---

## Quick start — 5 minute tour

Start the API:

```bash
python -m opendna.api.server --port 8765
```

Fold, design, and analyze a protein in Python:

```python
from opendna import fold, design, analyze

# Fold ubiquitin
result = fold("MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG")
print(result.plddt_mean, len(result.pdb))

# Design 10 alternatives via ESM-IF1
candidates = design(result.pdb, n=10, temperature=0.1)

# Full 50-analysis suite
report = analyze(result.pdb)
print(report["lipinski"], report["ramachandran_outliers"])
```

Or from the CLI:

```bash
opendna fold "MQIFVKTLTGKTITLEVEPSDTIENVK..." --out ubi.pdb
opendna design ubi.pdb --n 10 --out candidates.fasta
opendna analyze ubi.pdb --format json
opendna serve --port 8765
```

Open the UI at <http://localhost:5173> (dev) or launch the desktop app. Press **Ctrl+K** to open the command palette, type **import ubiquitin**, then click **Predict Structure**.

---

## Screenshots

<!-- TODO: screenshot — main 3D viewer with multi-rep toggle and click-residue popup -->
<!-- TODO: screenshot — Component Manager catalog with install progress -->
<!-- TODO: screenshot — Visual workflow editor with a 6-node pipeline -->
<!-- TODO: screenshot — Provenance DAG time machine with diff view -->
<!-- TODO: screenshot — Lab notebook overlay with embedded plots -->
<!-- TODO: screenshot — Real-time collaboration overlay with two cursors -->
<!-- TODO: screenshot — Academy Level 5 (Drug Design 101) in progress -->
<!-- TODO: screenshot — Onboarding tour step 3 -->
<!-- TODO: screenshot — Ramachandran plot + sequence ruler -->
<!-- TODO: screenshot — Dashboard with hardware, GPU pool, queue -->

---

## Documentation

Everything under [docs/](docs/):

- [GETTING_STARTED.md](docs/GETTING_STARTED.md) — install & first run
- [USER_GUIDE.md](docs/USER_GUIDE.md) — every feature, with screenshots
- [TUTORIALS.md](docs/TUTORIALS.md) — 10 end-to-end walkthroughs
- [COOKBOOK.md](docs/COOKBOOK.md) — 20 recipes
- [API_REFERENCE.md](docs/API_REFERENCE.md) — REST + WebSocket endpoints
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — how the system fits together
- [SCIENCE.md](docs/SCIENCE.md) — what every algorithm does and why
- [FAQ.md](docs/FAQ.md) — common questions
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — when things break
- [DEVELOPER.md](docs/DEVELOPER.md) — contributing and extending
- [ROADMAP.md](docs/ROADMAP.md) — what's next
- [CHANGELOG.md](docs/CHANGELOG.md) — every release
- [MODEL_CARD.md](MODEL_CARD.md) — Mitchell-et-al. cards for ESMFold / ESM-IF1 / ESM-2
- [paper/preprint.md](paper/preprint.md) — bioRxiv-ready writeup
- [paper/BENCHMARKS.md](paper/BENCHMARKS.md) — reproducibility methodology

---

## Architecture

OpenDNA is a three-layer stack: a **Rust core** (data models, PDB/FASTA parsing, version control, SQLite storage) exposed to Python via PyO3; a **Python engine layer** wrapping ESMFold, ESM-IF1, DiffDock, RFdiffusion, Boltz-1, OpenMM, xTB, ANI-2x and 50+ analyses behind a FastAPI server with priority job queue, WebSocket streaming, and a warm-model GPU pool; and a **TypeScript/React frontend** rendered in Molstar and React Flow, packaged as a Tauri 2 desktop app with a PyInstaller sidecar. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for diagrams and data flow.

---

## Post-quantum cryptography

Harvest-now-decrypt-later is a real threat for biology data that stays sensitive for decades. OpenDNA ships quantum-safe primitives out of the box:

- **ML-KEM-768** (Kyber, NIST FIPS 203) for key exchange on auth tokens and workspace unlock
- **ML-DSA-65** (Dilithium, NIST FIPS 204) for signing provenance entries and the hash-chained audit log
- Implemented via **liboqs** through the `opendna[pqc]` extra
- Hybrid mode available — PQC primitive wrapped around classical X25519/Ed25519 so compromise of either leaves the other standing

Enable it:

```bash
pip install "opendna[pqc]"
export OPENDNA_AUTH_REQUIRED=1
export OPENDNA_PQC=1
python -m opendna.api.server
```

Details in [docs/ARCHITECTURE.md#post-quantum](docs/ARCHITECTURE.md).

---

## For corporations

OpenDNA is built for regulated environments as well as hobbyists:

- **CycloneDX 1.5 SBOM** generated on every release
- **Air-gap bundle** and capability check — run fully offline
- **GDPR export & erasure** endpoints (`/v1/compliance/export_user_data`, `/v1/compliance/erase_user`)
- **HIPAA safeguard checklist** under [docs/](docs/) and an in-app self-audit
- **Post-quantum auth** and hash-chained tamper-evident audit log
- **Per-user workspaces** with AES-256-GCM encryption-at-rest
- **Team workspaces** with owner/editor/viewer permissions

Commercial licensing contact: see [LICENSE](LICENSE).

---

## For researchers

- **Provenance DAG**: every fold, design, analysis, and parameter is recorded as a node in a directed acyclic graph
- **Time machine**: step backward and forward through any project
- **diff / blame / bisect**: `diff_steps(a, b)`, `blame_residue(n)`, `bisect_regression(metric)`
- **Zenodo DOI minting** via `/v1/zenodo/mint` for citable datasets
- **Lab notebook** per project, markdown, auto-saved
- **R SDK** and **Jupyter magics** for statisticians and notebook users

---

## For educators

- **Academy Levels 1–7**: from amino acids to drug design
- **Mini-games**: Match, Quiz, Sequence Reader, plus 7 daily-challenge templates
- **23-term glossary** with hover tooltips everywhere
- **SQLite leaderboard** with streaks and 13 badges
- **Onboarding tour** for first-time users (7 steps)

---

## Contributing

We love contributions — code, docs, tutorials, bug reports, or just stars. See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/DEVELOPER.md](docs/DEVELOPER.md).

---

## License

OpenDNA Core: **Apache 2.0 + Commons Clause** (free for non-commercial; contact us for commercial licenses).
OpenDNA Community Modules: **MIT**.
OpenDNA Documentation: **CC-BY-4.0**.

---

## Citation

If you use OpenDNA in published research, please cite:

```bibtex
@software{opendna2026,
  title        = {OpenDNA: The People's Protein Engineering Platform},
  author       = {{The OpenDNA Contributors}},
  year         = {2026},
  version      = {0.5.0-rc1},
  url          = {https://github.com/dyber-pqc/OpenDNA},
  doi          = {10.5281/zenodo.OPENDNA},
  license      = {Apache-2.0 with Commons Clause}
}
```
