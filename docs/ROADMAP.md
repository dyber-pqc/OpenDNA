# OpenDNA Roadmap

The plan for what's coming next.

## Current Status: v0.5.0-rc1

A release-candidate mega-drop spanning 19 phases from foundation fixes to big-corp compliance. Working, documented, and smoke-tested. One more stabilization pass before GA.

---

## Done in v0.5.0-rc1

All nineteen phases, at a glance (full details in [CHANGELOG.md](CHANGELOG.md)):

- ✅ **Phase 0** — Multi-rep Molstar viewer + click-residue popup
- ✅ **Phase 1** — PyInstaller bundled sidecar wired into Tauri `externalBin`, per-platform CI
- ✅ **Phase 2** — Component Manager (11 ML engines, Altium/Vivado-style UI, install/progress API)
- ✅ **Phase 3** — Real heavy models: DiffDock, RFdiffusion, Boltz-1, ColabFold, xTB, ANI-2x, graceful fallback
- ✅ **Phase 4** — PQC auth: ML-KEM-768 + ML-DSA-65 via liboqs, hash-chained audit log
- ✅ **Phase 5** — Per-user workspaces with AES-256-GCM encryption-at-rest (scrypt-derived)
- ✅ **Phase 6** — Priority job queue (interactive/normal/batch) + WebSocket job streaming + GPU pool
- ✅ **Phase 7** — Local crash reporter with secret redaction, `@retry` decorator, `SelfHealer` thread
- ✅ **Phase 8** — Provenance DAG + time machine + `diff_steps` / `blame_residue` / `bisect_regression`
- ✅ **Phase 9** — Visual workflow editor (React Flow, 10 node types, provenance-recording)
- ✅ **Phase 10** — NCBI/PubMed/UniProt/AlphaFold DB/Twist/IDT/GenScript/Slack/Teams/Discord/webhooks
- ✅ **Phase 11** — R SDK + Jupyter magics + Galaxy/Snakemake/Nextflow plugins
- ✅ **Phase 12** — Lab notebook + Zenodo DOI minting + PNG/SVG figure + GLTF/OBJ 3D export
- ✅ **Phase 13** — Real-time co-editing via Yjs CRDT (y-websocket-compatible relay)
- ✅ **Phase 14** — Academy Levels 4–7, 13 badges, daily challenges, glossary, SQLite leaderboard
- ✅ **Phase 15** — Ollama auto-install + streaming chat + multi-turn session memory
- ✅ **Phase 16** — CycloneDX 1.5 SBOM, air-gap capability check, GDPR export/erasure, HIPAA checklist
- ✅ **Phase 17** — Dockerfile, Homebrew formula, Playwright E2E, pytest smoke suite
- ✅ **Phase 18** — 7-step onboarding tour, sequence ruler with AA coloring, global FASTA/PDB drop, light-theme polish

---

## Next: v0.5.0 GA stabilization

Short list of what has to happen before we drop the `-rc1` suffix:

- **Expand Playwright coverage** — currently a smoke suite, need per-overlay regression tests and a CI matrix (chromium/webkit/firefox × win/mac/linux)
- **Fix deprecation warnings** — pydantic v2, SQLAlchemy 2.0, FastAPI lifespan, React 19
- **Pin all deps** — generate a reproducible `requirements.lock` and `package-lock.json` from the CycloneDX SBOM
- **Final documentation pass** — screenshots for every overlay, updated tutorials, verified code snippets
- **Signed installers** — Apple notarization, Windows Authenticode, Linux AppImage GPG
- **One more benchmark run** on ubiquitin, insulin, GFP, lysozyme, p53 DBD, KRAS, EGFR kinase

Target: **v0.5.0 GA** within a few weeks of rc1.

---

## v0.6.0 candidates

Items from the latest "what's still missing" audit. Not promised, but prioritized.

### Science
- **Multi-fidelity folding cascade** — Tier 0 (secondary-structure instant) → Tier 1 (ESMFold) → Tier 2 (OpenFold) → Tier 3 (AlphaFold-Multimer) routed automatically by confidence
- **Membrane protein support** — lipid-bilayer placement, implicit-membrane OpenMM, specialized scoring
- **AbDock** — antibody-antigen docking with CDR-aware sampling
- **DiffDock-PP** — diffusion-based protein-protein docking
- **REMD / metadynamics** — enhanced sampling wrappers around OpenMM
- **QM/MM coupling** — xTB inside an OpenMM region, for mechanism work
- **FEP+** — alchemical free-energy perturbation for binding affinity
- **Cryo-EM map fitting** — real-space refinement into density maps
- **Electrostatic surface coloring** — APBS-backed Poisson-Boltzmann surface

### UX
- **Trajectory scrubber integration with Molstar** — frame-accurate MD playback synced with sequence ruler
- **Project explorer persistence** — sidebar tree of workspaces, provenance branches, and lab notebooks with drag-reorder
- **Richer diff viewer** for provenance DAG — side-by-side structure + score + notebook diff

### Compliance & operations
- **SOC 2 audit** — controls documentation, vendor review, third-party assessment
- **LTS line** — long-term-support branch with backports-only policy
- **Commercial support** — paid tier for corporations needing SLAs (core stays free)

---

## Wild cards

Things we'd love to build if the universe cooperates:

- **VR / WebXR mode** — manipulate proteins in a Quest or Vision Pro
- **AR mobile** — point an iPhone at your desk and see a protein floating there
- **MIDI controller support** — knob-twiddle through rotamers like a Eurorack
- **Twitch integration** — stream a design session, viewers vote on mutations
- **Plugin marketplace** — signed third-party engines, themes, and analyses
- **Auto-paper writer** — from a provenance DAG to a draft methods + results + figures bundle

---

## Versioning Scheme

We use [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH-status**
- **MAJOR**: breaking changes
- **MINOR**: new features, no breaking changes
- **PATCH**: bug fixes only
- **status**: alpha, beta, rc (release candidate), or omitted for stable

Pre-1.0 releases are not API-stable, but provenance DAGs and workspace formats are versioned and migratable.

---

## Contributing to the Roadmap

Want to influence priorities? Open an issue or PR with:
- **Use case**: who would use this and why
- **Effort estimate**: rough complexity
- **Dependencies**: what it needs

Or just start building it. Working code beats arguing.
