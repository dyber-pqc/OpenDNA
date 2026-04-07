# Changelog

All notable changes to OpenDNA. Format based on [Keep a Changelog](https://keepachangelog.com/).

## [v0.2.1] - 2026-04-06

### Fixed
- Imported sequences (UniProt) now properly populate the sidebar textarea
- Academy "Amino Acid Match" game no longer reshuffles between clicks (memoization)
- pLDDT coloring now uses proper AlphaFold-style theme via B-factor scaling
- Warn before folding proteins >250 residues on CPU (memory and time concerns)
- Score recommendation message no longer says "run prediction" when one is loaded

### Added — 8 new sequence and structure analyses

- **Hydrogen bond detection** — finds N-H...O / O-H...N pairs in structures
- **Salt bridge detection** — finds positively-negatively charged side chain pairs
- **Disulfide bond detection** — finds Cys-Cys covalent bonds
- **Transmembrane prediction** (TMHMM-like) — sliding window hydrophobicity
- **Signal peptide detection** (SignalP-like) — N-terminal n/h/c region scoring
- **Aggregation prediction** (TANGO-like) — aggregation-prone regions with risk levels
- **Phosphorylation site prediction** — kinase consensus motif matching (PKA, PKC, CK2, CDK, GSK3, MAPK)
- **N/O-glycosylation site prediction** — sequon scanning
- **Mutation stability prediction (ΔΔG)** — heuristic estimate
- **Pairwise sequence alignment** — Needleman-Wunsch with BLOSUM62

### Added — API endpoints
- `POST /v1/align` — pairwise sequence alignment
- `POST /v1/predict_ddg` — mutation effect prediction
- `/v1/analyze` now includes all 8 new analyses in the response

### Documentation
- Massively expanded documentation in `docs/`:
  - `README.md` (rewritten)
  - `GETTING_STARTED.md` (new)
  - `USER_GUIDE.md` (new)
  - `API_REFERENCE.md` (new)
  - `ARCHITECTURE.md` (new)
  - `SCIENCE.md` (new — explains every algorithm)
  - `TUTORIALS.md` (new — 10 walkthroughs)
  - `COOKBOOK.md` (new — 20 recipes)
  - `FAQ.md` (new)
  - `TROUBLESHOOTING.md` (new)
  - `DEVELOPER.md` (new)
  - `ROADMAP.md` (new)
  - `CHANGELOG.md` (this file)

### UI improvements
- Analysis Panel now shows: Transmembrane, Signal Peptide, Aggregation, PTM sites, and Bond Network sections
- Sidebar Tools tab textarea is bound to shared `currentSequence` state
- Sidebar shows residue count next to "Protein Sequence" label

---

## [v0.2.0-beta] - 2026-04-06

### Added — 9 new backend engines/modules
- **`analysis.py`** — Schrödinger QikProp-equivalent suite
  - Molecular weight, isoelectric point, GRAVY hydropathy
  - Aromaticity, instability index, aliphatic index
  - Charge at pH 7, extinction coefficients
  - N-terminal half-life prediction
  - Lipinski's Rule of Five
  - Kyte-Doolittle hydropathy profile
  - Secondary structure assignment
  - Ramachandran phi/psi computation
  - Radius of gyration, SASA estimate
  - Binding pocket detection
  - Kabsch RMSD for structure comparison
- **`iterative.py`** — Automated optimization loop (fold→design→fold→keep best)
- **`disorder.py`** — Intrinsic disorder prediction (IUPred-like)
- **`dynamics.py`** — OpenMM molecular dynamics wrapper with heuristic fallback
- **`docking.py`** — Ligand docking with virtual screening (DiffDock-ready interface)
- **`explain.py`** — AI-powered protein explanation via Ollama with rich fallback
- **`data/sources.py`** — UniProt, PDB, AlphaFold DB import + 15 famous proteins
- **`data/synthesis.py`** — Synthesis cost estimator (Twist/IDT/GenScript) + carbon footprint
- **`storage/projects.py`** — Project workspace save/load with provenance

### Added — API endpoints
- `/v1/iterative_design`
- `/v1/analyze` (full Schrödinger-equivalent suite)
- `/v1/explain`
- `/v1/compare` (RMSD between two structures)
- `/v1/dock`
- `/v1/screen` (virtual screening)
- `/v1/md` (molecular dynamics)
- `/v1/fetch_uniprot`
- `/v1/fetch_pdb`
- `/v1/famous_proteins`
- `/v1/cost`
- `/v1/projects/save`
- `/v1/projects/load`
- `GET /v1/projects`
- `DELETE /v1/projects/{name}`

### Added — Frontend
- **Command Palette** (Cmd+K) with fuzzy search across all actions
- **Toast notification system**
- **Keyboard shortcuts** hook (F=fold, S=score, A=analyze, Esc=close, Cmd+S=save)
- **Comprehensive Analysis Panel** with:
  - Properties grid, Lipinski badge, hydropathy SVG plot
  - Disorder score plot, AA composition bars
  - Secondary structure ribbon, Ramachandran scatter plot
  - Binding pocket list
- **Dashboard** with hardware info, job stats, project list
- **Protein Academy** with Level 1-3 (Match game, Quiz, Sequence Reader)
- **XP system** + gamification badges
- **Iterative Design Panel** with optimization history chart
- **3-tab Sidebar** (Tools / Structures / Import)
- **Famous proteins** quick-access buttons
- **Cost & carbon estimate** overlay
- **AI explanation overlay**
- **Result caching** (instant re-fold of cached sequences)

### Changed
- Version badge: v0.2.0-beta
- Better dark theme palette
- Persistent header buttons for Dashboard, Academy, Save PDB

---

## [v0.1.0-alpha] - 2026-04-06

### Added — Initial release
- **Rust core** (data models, PDB/FASTA parsing, version control, SQLite storage)
- **Hardware abstraction layer** (CUDA / Metal / CPU detection, model tier selection)
- **Python ML layer** with ESMFold (folding) and ESM-IF1 (inverse folding / design)
- **Composite scoring engine** (stability, solubility, immunogenicity, developability)
- **FastAPI server** with background job queue
- **Tauri + React desktop UI** with Molstar 3D viewer
- **Mutation playground** with auto-refold
- **Side-by-side structure comparison**
- **Natural language chat** (Ollama support with deterministic fallback parser)

### Tested
- End-to-end on ubiquitin: fold → mutate K48R → design 10 alternatives via ESM-IF1 → fold a candidate → compare structures
