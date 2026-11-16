# Changelog

Entries are written for somebody deciding whether to upgrade, so removals come
first and known limitations are stated rather than left to be discovered.

Versions follow [semantic versioning](https://semver.org). The project is
pre-1.0: the command-line interface, the file formats and the head metadata
schema may still change between minor versions, and when they do it will be
said here.

## v0.6.0-rc1 — unreleased

**A rewrite, not an upgrade.** Everything between `v0.5.0-rc1` and here
replaced the Python backend and the React front end with Rust. Most of what
`v0.5.x` advertised no longer exists. Read the removals before upgrading.

A release candidate rather than a release because of what has not been
exercised: this tag is the first thing the release workflow has ever built, the
macOS and Linux installers have never been produced on any machine, and the
installers are unsigned. The command-line tool is the part that has been
measured and tested.

The desktop application reports version `0.6.0` rather than `0.6.0-rc1`. The
MSI bundler requires a pre-release identifier to be numeric, so `rc1` would
fail the Windows build outright; the JSON it is configured in cannot carry a
comment saying so, which is why it is said here.

### Removed

- **The Python backend and the React user interface.** Both are gone from the
  repository, along with the FastAPI server, the PyInstaller sidecar and the
  wheel.
- **ESMFold structure prediction.** No structures are predicted. The desktop
  application can open and view a PDB or mmCIF file you already have.
- **ESM-IF1 inverse folding.** No sequence design.
- **Molecular dynamics.** No simulation of any kind.
- **The antibody and plasmid tools, the model hub and the project
  templates.** These were added after `v0.5.0-rc1` and were never part of a
  tagged release: a commit calls itself `v0.5.0-rc2` but no such tag exists.
- **The deployment configuration** for running OpenDNA as a server. It is not
  a server; it opens no network port.

If you depend on any of these, stay on `v0.5.0-rc1`, the last release that
has them. They are not coming back
in this line: the reason for the rewrite was that a platform advertising nine
things it did badly was worth less than a tool doing four things with numbers
attached.

### Added — four trained heads with measured accuracy

Each predicts one property from frozen ESM-2 150M embeddings, and each ships a
model card generated from its own training report.

| Head | In-domain test | External |
|---|---|---|
| Disorder | AUROC 0.883 | AUROC 0.941 on CAID3 Disorder-PDB |
| Accessibility (burial) | Spearman 0.737 | not benchmarked externally |
| Stability (ΔΔG) | Spearman 0.674 | Spearman 0.442 over 4 ProteinGym assays |
| Solubility | Spearman 0.701 | none exists under usable terms |

Disorder is the strong one and sits inside the published CAID3 field. Stability
is a ranking signal and the in-domain figure overstates generalisation by about
0.23 Spearman — the README says so beside the table, and so does the card.
ESM-2 650M was tried and rejected: it made disorder worse on every external
metric for four times the weights.

A missing head is an error naming the files it looked for. Nothing falls back
to a heuristic and reports it as a prediction.

### Added — a command-line tool

`opendna` runs the heads over a FASTA file and writes a table. The desktop
application works on one protein at a time, which is the wrong shape for
triaging a few hundred candidates.

- `predict` for all four tasks, in `csv`, `tsv`, `json` or `caid` format.
- `models` lists what is installed, verifies each head's weights against the
  digest in its metadata, and can write or check a lockfile.
- `selftest` runs the installed heads over a bundled sequence and checks 18
  recorded values and invariants. It exists because `models` passes a correct
  install with the wrong weights in it — the files are intact and the numbers
  are wrong, and only running them catches that.
- `stage` copies an installation, embedding model included, into one directory
  that works on a machine with no network.
- `split` and `merge` for running parts in parallel. `merge` reads each part's
  manifest and refuses to join parts produced by different software, on
  different devices or at different batch sizes, which `cat` cannot notice.
- `--checkpoint` records results as they are produced and continues an
  interrupted run from the last complete chunk. Verified byte-identical to an
  uninterrupted run, including after a real process kill.

### Added — provenance, so a number can be defended

- **Every head has a build id**, derived from its weights, its training
  configuration and its data, that a lab can pin and verify.
- **Every output file carries** the head version, the embedding model, the
  device and the card's limitations as comments, taken from the card rather
  than written twice.
- **Every run writes a manifest** beside its output: the input's digest, the
  output's digest, the head build, the weights digest, the device, the batch
  size, the chunk size, the licence and how long it took.
- **Licences travel with the weights.** One head is trained on share-alike
  data and released on the same terms; `stage` writes a `LICENSES.md` grouping
  the heads by licence and flagging that one, because a result passed on
  without it is an obligation somebody does not know they have.
- **The exit status says what to do about the failure**: 2 for usage, 3 for the
  installation, 4 for the input, 5 for a failed check, 1 for anything
  unanticipated. Checked against the compiled binary.

### Added — what the numbers mean, measured rather than asserted

- **Disorder probabilities are calibrated.** They were inflated about
  threefold by class-weighted training; where the head said 0.55, 13% of
  residues were disordered. Platt scaling on held-out data fixed the scale and
  moved the decision threshold, which the head now records and the CLI and the
  application both read, so the two cannot disagree. Calibration changed the
  meaning of the number and not the ranking: AUROC is identical before and
  after.
- **Confidence predicts error, and abstaining helps.** The distance from the
  threshold recovers 55% of the reduction in error that a perfect oracle would
  give. `--min-confidence` marks rows below a cut-off against the head's own
  measured trade-off, and never removes them: a table quietly missing rows
  looks exactly like a complete one. A k-mer novelty signal was tested, found
  worse than random, and the rejection is recorded so nobody re-tests it.
- **The regressors report prediction intervals.** Split conformal on the
  validation split: ±1.33 kcal/mol for stability at 90% (achieving 93.7%),
  ±38.9 percentage points for solubility, ±0.237 RSA for burial. Coverage
  achieved is printed beside the level asked for because they differ — burial
  undercovers at every level, since clustering the splits by sequence identity
  breaks the exchangeability conformal assumes.

### Added — the supporting workspaces

- **`datasets/`** builds all four datasets from primary sources, clusters by
  sequence identity so near-identical proteins cannot straddle a split, and
  commits a card recording exactly what it produced.
- **`training/`** trains, benchmarks, calibrates, measures abstention and fits
  intervals, and generates each head's card from the measured report.
- **`pipelines/`** holds Nextflow and Snakemake modules. Neither has been run
  against its engine; what has been verified is the behaviour they rely on.
- **`docs/VALIDATION.md`** is written for whoever has to sign this off, and
  includes a section on what has not been checked.

### Changed

- The desktop application is Tauri 2 with a Leptos front end compiled to
  WebAssembly. No Node toolchain, no bundled Python.
- CI builds and tests on Windows, macOS and Linux, audits dependencies, and
  checks the minimum supported Rust version (1.95).
- **The dependency audit passes again.** `cargo deny check licenses` had been
  failing, so the CI audit job was red: three dependencies carry licences the
  allow list did not cover. Two of them, `colored` and `option-ext`, are
  MPL-2.0 and reach the shipped binary through the Hugging Face client, and
  `hf-hub` 1.0 has no feature that drops it. They are now allowed with the
  reason recorded in `deny.toml` and disclosed in the command-line README and
  the release notes, rather than by widening the list quietly.
- **The Dockerfile builds the command-line tool.** The previous one built a
  Python API server from directories the rewrite deleted, so it could not have
  worked. The new one is multi-stage, runs as a non-root user, exposes no port,
  and is built and smoke-tested by CI on every commit because the machine it
  was written on has Docker installed but not running.
- **`MODEL_CARD.md` and `docs/ROADMAP.md` were rewritten.** Both described the
  removed software: the first carried cards for ESMFold, ESM-IF1 and
  ProteinMPNN, and the second listed nineteen phases of it as done. `CITATION.cff`
  likewise still claimed version 0.4.0 and an abstract about structure
  prediction and inverse folding.
- `unsafe` code is forbidden in the three workspaces that ship: the root
  crates, the desktop application and the training tools. The dataset builder
  is a maintainers' tool and is not covered.

### Known limitations

- **No signed installers.** Operating systems will warn. Code-signing
  certificates have not been obtained.
- **Two runs cannot load the embedding model through the Hugging Face cache at
  once**; on Windows the second is refused the weights file. Run `opendna
  stage` once and point `--models` at the bundle, which several runs can
  share. This matters because `split` and the pipelines exist to run parts
  side by side.
- **One machine.** Every measurement in the documentation comes from a single
  Windows workstation with an RTX 2000 Ada. Cross-platform numerical agreement
  is untested.
- **No clinical or diagnostic validation of any kind.**
- **Nothing detects out-of-domain input.** The disorder head's confidence
  predicts error, which is not the same thing.

## Everything below this line

The entries below describe a different program: the Python and React
application this release replaced. They are kept because they are the
project's history, not because a feature can be traced from them to anything
here.

## [v0.5.0-rc1] - 2026-04-07

Mega-session release spanning 19 phases from foundation fixes to big-corp compliance.

### Added
- **Phase 0** Fixed multi-rep viewer + wired click-residue popup (Molstar)
- **Phase 1** PyInstaller bundled sidecar + Tauri `externalBin` + per-platform CI build
- **Phase 2** Component Manager (11 ML engines, Altium/Vivado-style UI, install/progress API)
- **Phase 3** Real heavy models: DiffDock, RFdiffusion, Boltz-1, ColabFold, xTB, ANI-2x with graceful fallback
- **Phase 4** PQC auth — ML-KEM-768 + ML-DSA-65 via liboqs, hash-chained tamper-evident audit log
- **Phase 5** Per-user workspaces with AES-256-GCM encryption-at-rest (password-derived key)
- **Phase 6** Priority job queue (interactive/normal/batch) + `WebSocket /v1/ws/jobs/{id}` streaming + GPU pool with warm-model cache
- **Phase 7** Local-first crash reporter with secret redaction, `@retry` decorator, `SelfHealer` background thread
- **Phase 8** Provenance DAG + time machine + `diff_steps` / `blame_residue` / `bisect_regression`
- **Phase 9** Visual workflow editor (React Flow, 10 node types, auto-records to provenance)
- **Phase 10** NCBI/PubMed/Twist/IDT/GenScript/Slack/Teams/Discord/webhooks
- **Phase 11** R SDK + Jupyter magics + Galaxy/Snakemake/Nextflow plugins
- **Phase 12** Lab notebook + Zenodo DOI minting + PNG/SVG figure export + GLTF/OBJ 3D export
- **Phase 13** Real-time co-editing via Yjs CRDT (y-websocket-compatible relay)
- **Phase 14** Academy Levels 4–7, 13 badges, 7 daily-challenge templates, 23-term glossary, SQLite leaderboard with streaks
- **Phase 15** Ollama auto-install + streaming chat + multi-turn session memory
- **Phase 16** CycloneDX 1.5 SBOM, air-gap capability check, GDPR export/erasure, HIPAA checklist
- **Phase 17** Dockerfile, Homebrew formula, Playwright E2E suite, pytest smoke suite (11/11 passing)
- **Phase 18** 7-step onboarding tour, sequence ruler with AA coloring, global drag-and-drop FASTA/PDB, light-theme polish

## [v0.4.10] - 2026-04-07

### Fixed (the actual root cause of all desktop app auto-start issues)
- **Pipe deadlock in Tauri sidecar**: previous code spawned the Python API server with `Stdio::piped()` for stdout/stderr but never read from those pipes. uvicorn's startup output filled the pipe buffer within seconds and the child process froze on `write()` before opening port 8765. Fix: use `Stdio::null()` so the child can never block on parent I/O.
- **Console window popup on Windows**: every Python sidecar spawn produced a black `cmd.exe` window. Fix: added `CREATE_NO_WINDOW = 0x08000000` flag (Windows-specific) via the new `configure_child_command()` helper. Applied to all child process spawns.
- **VERIFIED LOCALLY** with `npx tauri build`: built `opendna-desktop.exe`, killed all running Python processes, launched the desktop app, watched logs say `Sidecar startup: Started API server`, and confirmed `curl http://127.0.0.1:8765/health` returned 200 OK with no manual intervention.

## [v0.4.9] - 2026-04-07

### Added
- **BackendStatus banner is now Tauri-aware**: detects whether running in the desktop shell or browser dev mode
- **Auto-invoke `start_api_server` in Tauri mode**: even on older installers without the `.setup()` hook, the banner will trigger sidecar startup from the UI
- **Diagnostic info in banner**: shows detected Python interpreters and which ones have opendna installed
- **"Start backend" button**: manual retry from inside the app
- **Tauri invoke wrapper** that handles both old and new `__TAURI__` APIs

## [v0.4.8] - 2026-04-07

### Fixed
- **`python -m opendna.api.server`** now defaults to `127.0.0.1:8765` (was `0.0.0.0:8000`)
- **Server `__main__` accepts CLI args** `--port N` and `--host H` plus `OPENDNA_PORT` / `OPENDNA_HOST` env vars
- **Tauri sidecar scans Windows Python install paths**: `%USERPROFILE%\AppData\Roaming\Python\Python3xx\Scripts`, `AppData\Local\Programs\Python\`, `C:\Python{ver}`, `C:\Program Files\Python{ver}` — finds Python even when not on PATH
- **Sidecar verifies opendna is importable** in each Python before trying to launch
- **Sidecar tries 3 invocation styles** in order: `python -m opendna.api.server`, `python -m opendna.cli.main serve`, and inline `python -c "..."`

## [v0.4.7] - 2026-04-07

### Fixed
- **PowerShell-friendly setup commands** in BackendStatus banner — Windows PowerShell <7 doesn't support `&&`, so the banner now shows the install and serve commands on separate lines with a hint

## [v0.4.6] - 2026-04-07

### Added
- **Tauri auto-start hook**: `.setup()` hook spawns `try_auto_start()` on a background thread when the desktop app launches, so the Python API sidecar runs without manual intervention
- **`.on_window_event()` handler**: cleanly stops the sidecar when the main window closes (no orphaned processes)
- **Multiple Python interpreter candidates**: tries `python`, `python3`, `py`
- **`check_opendna_installed()` Tauri command** for diagnostics
- **`BackendStatus` React component**: pings `/v1/hardware` to detect backend availability, shows a banner with setup instructions, auto-retries every 10 seconds
- **`ErrorBoundary` component** wrapping the App in `main.tsx`

## [v0.4.5] - 2026-04-06

### Changed
- **Merged Tauri desktop builds into `release.yml`** as a single unified release. Previously had two separate releases per version (`v0.4.4` for Python/UI, `v0.4.4-desktop` for installers) which was confusing.
- New job graph: `python-package` + `ui-bundle` + `desktop-build` (matrix mac/linux/windows) → `github-release` waits for all 5 and creates ONE release with all artifacts.
- Calls `npx tauri build` directly instead of `tauri-action` to avoid the side-effect of creating its own release.
- Massively expanded release notes with download table for all 7 desktop installer formats, 3 install paths, full feature list, per-OS unsigned-build workarounds.
- Deleted `tauri-build.yml` (functionality merged into `release.yml`).

## [v0.4.4] - 2026-04-07

### Fixed
- **Tauri build job permissions**: added `permissions: contents: write` to `build-desktop` job in `tauri-build.yml`. The job was successfully compiling all installers but failing at the very last step (release creation) with `Resource not accessible by integration`.

## [v0.4.3] - 2026-04-07

### Fixed
- **Missing `tauri` npm script**: tauri-action runs `npm run tauri build` but `ui/package.json` had no `tauri` script. Added `tauri`, `tauri:dev`, `tauri:build` to scripts.

### Changed
- **Massively expanded release notes** for both Python and desktop releases with complete download tables, install paths, security workarounds, feature lists, citation blocks, and support actions.

## [v0.4.2] - 2026-04-07

### Fixed
- **Molstar API misuse** in multi-rep viewer toggle: `updateRepresentationsTheme()` only accepts `color` and `size` keys, not `type`. Switched to using preset selection via `addRepresentation()` for surface/spacefill modes.

## [v0.4.1] - 2026-04-07

### Fixed
- **`pyproject.toml` heavy dependencies**: split `torch`, `transformers`, `fair-esm`, `biotite`, `torch-geometric` into optional `[ml]` extra. Core install is now lightweight.
- **`python -m opendna` lazy loading**: replaced eager imports with `__getattr__` so just importing the package doesn't pull in torch.
- **CI workflows**: removed reference to non-existent `[test-light]` extra, removed signing key requirements that weren't set as secrets, made `--strict` mkdocs build less aggressive.
- **Workspace conflict**: added `exclude = ["ui/src-tauri"]` so the Tauri Cargo project can build standalone.
- **`mkdocs.yml`**: added `docs_dir: docs` and created `docs/index.md` (was pointing to `README.md` outside `docs_dir`).

## [v0.4.0] - 2026-04-06

### Added
- **Tauri desktop app**: full `tauri.conf.json` + `src-tauri/Cargo.toml` with shell/dialog/fs/process/log plugins, Python sidecar manager
- **Cross-platform CI matrix** for desktop installers (Win/Mac/Linux)
- **Real OpenMM with explicit TIP3P solvent** in `engines/dynamics.py` — AMBER14 force field, energy minimization, NVT equilibration, production MD with RMSD/RMSF/Rg trajectories
- **Real DiffDock integration** in `engines/docking.py` (tries `diffdock_pp`, official `diffdock`, and pip-installable variants)
- **Boltz multimer prediction** in `engines/multimer.py` (NEW) — falls back to per-chain ESMFold + spatial separation
- **Self-benchmarking framework** in `benchmarks/runner.py` — compares OpenDNA against AlphaFold DB references with RMSD, TM-score proxy, pLDDT
- **Multi-representation viewer toggle**: cartoon, ball-and-stick, spacefill, surface
- **bioRxiv-ready preprint** in `paper/preprint.md` (~3300 words, 11 references)
- **`MODEL_CARD.md`** following Mitchell et al. framework for ESMFold, ESM-IF1, ESM-2
- **`paper/BENCHMARKS.md`** with reproducibility methodology

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
