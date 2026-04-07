# OpenDNA Roadmap

The plan for what's coming next.

## Current Status: v0.2.0-beta (Pre-alpha)

Working but not production-ready. Used for exploration, learning, and research prototyping.

---

## v0.2.1 (Patch — current)

**Theme:** Bug fixes + 8 new analyses + comprehensive docs.

- ✅ Fix imported sequence sync to sidebar textarea
- ✅ Fix Academy match game shuffle bug
- ✅ Better pLDDT coloring (proper AlphaFold theme)
- ✅ Warn before folding huge proteins on CPU
- ✅ New: H-bond, salt bridge, disulfide bond detection
- ✅ New: Transmembrane region prediction
- ✅ New: Signal peptide detection
- ✅ New: Aggregation/solubility prediction
- ✅ New: Phosphorylation site prediction
- ✅ New: Glycosylation site prediction
- ✅ New: Mutation effect (ΔΔG) prediction
- ✅ New: Pairwise sequence alignment (Needleman-Wunsch + BLOSUM62)
- ✅ Massive documentation expansion

---

## v0.3.0 — "Closing the Loop"

**Theme:** Make the science loop complete and the UX feel premium.

### Compute
- **Multi-fidelity folding cascade** — Tier 0 instant secondary structure → Tier 1 ESMFold → Tier 2 OpenFold → AlphaFold-Multimer for hard cases
- **Multimer prediction** — fold protein complexes (2+ chains)
- **Membrane protein prediction** — special handling for transmembrane regions
- **Loop modeling** — refine flexible regions with conformational sampling
- **Real DiffDock integration** — actual ligand docking, not heuristic
- **DiffDock-PP** — protein-protein docking
- **Antibody-antigen docking** — AbDock specialized model
- **Virtual screening** — dock 1000 ligands and rank
- **Real OpenMM MD** — full setup with explicit solvent
- **Free energy estimation** — MMGBSA for binding affinity

### Design
- **Constrained design** — fix active site residues, only mutate the rest
- **Multi-objective optimization** — balance stability vs binding vs solubility
- **De novo design** — RFdiffusion integration for novel backbones
- **Antibody design** — specialized loop generation
- **Structure-aware scoring** — use the structure when scoring sequences

### UI/UX
- **Click residue → popup** with name, position, conservation, suggested mutations
- **Drag amino acid letters** onto residues to mutate visually
- **Multiple representations** — cartoon, surface, ball-and-stick toggle
- **Surface coloring** by electrostatic potential
- **Trajectory player** — scrub through MD frames or design iterations
- **Sequence ruler** at bottom of viewer with hover/click sync
- **Highlight residues** by property (charge, hydrophobicity, conservation)
- **Project workspace UI** — load/save/list with thumbnails
- **Markdown notebook** per project
- **Batch processing UI** — submit many sequences at once
- **Auto-save** every 30 seconds
- **Light theme polish**
- **Onboarding tour** for first-time users
- **WebSocket streaming** for progress (instead of polling)

### Quality
- **Persistent jobs** in SQLite (survive server restart)
- **Result caching** with TTL
- **Error boundaries** in React
- **Engine tests** with reference data
- **CI/CD** with cross-platform builds

---

## v0.4.0 — "Democratization"

**Theme:** Truly accessible to non-experts.

### Natural Language
- **Bundled local LLM** (auto-download Phi-3-mini or Llama 3.2 on first run)
- **Tool calling** — LLM can directly invoke fold/design/score actions
- **Streaming responses** in chat panel
- **Multi-turn conversations** with memory
- **Voice input** (Whisper local model)

### Smart Features
- **"Explain this protein"** — context-aware LLM explanation
- **"Why is this region uncertain?"** — explains low pLDDT regions
- **"Make it more stable"** — LLM suggests mutations and applies them
- **"Design a binder for cancer protein X"** — full natural language workflow
- **"Compare these two structures"** — auto-generates diff report

### AI Research Assistant
- **PubMed search integration** — chat asks "find papers about KRAS binders"
- **Paper summarization** — paste a PDF, get the protocol extracted
- **Method recommendation** — "what should I do to validate this design?"
- **Hover-to-explain** — hover any technical term, get a tooltip definition
- **Auto-citations** — when LLM mentions a fact, adds a paper link

### Protein Academy
- **Level 4: Famous Proteins Tour** — interactive 3D walkthrough
- **Level 5: Drug Design 101** — design a binder against a target
- **Level 6: Fix the Broken Antibody** — challenge with scoring
- **Level 7: Cure the Zombie Virus** — story-driven campaign
- **Daily challenges** — new puzzle each day
- **XP, badges, leaderboards**
- **Skill tree** for specializations

### Real-World
- **One-click DNA synthesis ordering** — Twist Bioscience / IDT API integration
- **Cost estimator** — show $ before submitting
- **Carbon footprint tracker** — kg CO₂ per computation
- **Expression protocol auto-generator**
- **Plasmid map generator**
- **PDB import from UniProt ID** — `opendna fold P0CG48`
- **AlphaFold DB integration** — fetch any predicted structure

---

## v0.5.0 — "Community"

**Theme:** Network effects.

### Hub
- **OpenDNA Hub web** — public protein sharing platform
- **Real-time co-editing** like Google Docs
- **Comments on residues** — annotate and discuss
- **Forks and pull requests** for proteins
- **Embeddable viewers** for blog posts and papers
- **Star/follow/discover** other users

### Distributed Computing
- **Swarm mode** — donate idle GPU cycles
- **Federated design** — community-trained models on shared data
- **Credits system** — earn from contributing, spend on heavy jobs

### Mobile
- iOS/Android app (Flutter)
- Push notifications when long jobs finish
- Quick protein lookups
- AR viewer (point camera at desk → see protein floating)

### Collaboration
- **Team mode** — shared projects across multiple users
- **Project permissions** — owner/editor/viewer
- **Activity feed** for team projects

---

## v1.0.0 — "Production"

**Theme:** Make it actually deployable and trustworthy.

- **Tauri desktop installer** for Win/Mac/Linux (no Python install needed!)
- **Pre-bundled models** in installer
- **Auto-updater** built into the app
- **Documentation site** at opendna.org (Docusaurus)
- **Tutorial videos** for every major feature
- **Reproducible benchmarks** vs Schrödinger / Rosetta
- **Published paper** / preprint
- **Community-driven challenges** running monthly
- **Plugin marketplace**
- **Premium support** for commercial users (separate license)

---

## Beyond v1.0

### Hardware
- **VR mode** — manipulate proteins in WebXR
- **Custom accelerator** support (FPGAs, custom silicon)
- **Distributed multi-GPU** for large multimers
- **Cloud burst** to Lambda Labs / RunPod / Vast.ai

### Science
- **Cryo-EM map fitting**
- **Crystallographic refinement**
- **Enhanced sampling** (REMD, metadynamics)
- **MMGBSA / MMPBSA** for binding affinity
- **NMR ensemble fitting**
- **Coarse-grained models** for very large systems

### AI
- **Custom-trained models** for specific protein families
- **Active learning** loops
- **Multi-modal models** (sequence + structure + function)
- **Generative diffusion models** for backbone design

### Integrations
- **Lab automation** (OT-2, Hamilton, Tecan)
- **LIMS systems** (Benchling, SciNote, LabArchives)
- **Notebook integration** (Jupyter, Marimo)
- **Cytoscape network analysis**

---

## Versioning Scheme

We use [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH-status**
- **MAJOR**: Breaking changes
- **MINOR**: New features, no breaking changes
- **PATCH**: Bug fixes only
- **status**: alpha, beta, rc (release candidate), or omitted for stable

Pre-1.0 releases are not API-stable.

---

## Contributing to the Roadmap

Want to influence priorities? Open an issue or PR with:
- **Use case**: who would use this and why
- **Effort estimate**: rough idea of complexity
- **Dependencies**: what it needs

Or just start building it. Working code beats arguing.
