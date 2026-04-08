# OpenDNA User Guide

The complete reference for using OpenDNA. Every feature, every button, every panel.

## Table of Contents
1. [Interface Overview](#interface-overview)
2. [The Sidebar](#the-sidebar)
3. [The 3D Viewer](#the-3d-viewer)
4. [The Chat Panel](#the-chat-panel)
5. [The Header Bar](#the-header-bar)
6. [The Command Palette](#the-command-palette)
7. [Notifications (Toasts)](#notifications-toasts)
8. [Analysis Panel](#analysis-panel)
9. [Dashboard](#dashboard)
10. [Protein Academy](#protein-academy)
11. [Iterative Design](#iterative-design)
12. [Keyboard Shortcuts](#keyboard-shortcuts)

---

## Interface Overview

OpenDNA's interface is divided into 5 main areas:

```
┌─────────────────────────────────────────────────────────┐
│  HEADER:  Logo │ Version │ XP │ Buttons │ Theme         │
├─────────────────────────────────────────────────────────┤
│            │                                            │
│            │                                            │
│  SIDEBAR   │              3D VIEWER                     │
│  (Tools /  │     (Molstar protein visualization)        │
│ Structures │                                            │
│  / Import) │                                            │
│            │                                            │
│            ├────────────────────────────────────────────┤
│            │            CHAT PANEL                      │
└────────────┴────────────────────────────────────────────┘
                         JOB MONITOR (bottom bar)
```

---

## The Sidebar

The sidebar has **3 tabs**:

### Tools Tab
The main workspace. Contains:

#### Protein Sequence
- **Textarea** — Paste any amino acid sequence here. Updates in real-time as you import or edit.
- **Length indicator** — Shows residue count once a sequence is loaded.
- **Predict Structure** button — Submits to ESMFold (folds the protein in 3D).
- **Score Protein** button — Instant sequence-only quality score.

#### Iterative Design Loop
- **Rounds × Candidates** controls — Set how many optimization rounds and how many candidates per round.
- **Run Iterative Design** button — Automated optimization loop.

#### Mutate Active Protein
- **Mutation input** — Format like `K48R` (from-position-to). 1-indexed.
- **Apply Mutation & Refold** — Applies the mutation and immediately refolds the new sequence.

#### Active Structure Tools
Available actions on the currently-loaded protein:
- **Design 10 Sequences (ESM-IF1)** — Generate 10 alternative sequences for the active backbone.
- **Full Analysis Suite** — Open the comprehensive analysis panel.
- **Explain This Protein (AI)** — Get a plain-English explanation (uses Ollama if available).
- **Quick MD (stability check)** — Run a fast molecular dynamics check.
- **Cost & Carbon Estimate** — Show synthesis $$ and CO₂ estimates.

### Structures Tab
History of all folded structures in the current session.
- Click any structure to make it active in the viewer.
- Click the **vs** button to compare it side-by-side with the active structure.
- Active structure has a highlighted border.
- Each shows: name preview, length, mean pLDDT confidence.

### Import Tab
Load proteins from external databases.
- **Source toggle** — UniProt or PDB
- **ID input** — Enter accession (e.g. `P0CG48`) or famous name (e.g. `ubiquitin`)
- **Fetch button** — Loads the protein and switches to the Tools tab
- **Famous proteins grid** — Quick-access for ubiquitin, insulin, GFP, lysozyme, myoglobin, p53, KRAS, EGFR

---

## The 3D Viewer

The main visualization area, powered by Molstar.

### Mouse Controls
- **Drag** — Rotate
- **Scroll** — Zoom
- **Right-click drag** — Translate
- **Click an atom** — Show info popup

### Color Modes (bottom-left buttons)
- **pLDDT colors** — AlphaFold-style confidence coloring (blue=high, red=low)
- **Chain colors** — Color by chain ID (default Molstar)

### Stats Overlay (top-right)
Shows total atoms and residues in the loaded structure.

### Side-by-Side Compare
When you click "vs" on a structure in the Structures tab, the viewer splits in half showing both structures simultaneously. Each viewer can be controlled independently.

---

## The Chat Panel

A natural-language interface at the bottom of the main area.

### What you can say
- `fold MKTVRQERLKSIVRILER` — Predicts structure for any sequence
- `score MKTVRQERLK` — Evaluates a sequence
- `mutate K48R` — Applies a mutation to the active protein
- `explain` — Gets an AI explanation of the active protein
- `help` — Lists available commands

### Behind the scenes
The chat panel sends your message to `/v1/chat` which:
1. Tries Ollama (`llama3.2:3b`) if running
2. Falls back to a deterministic regex-based intent parser
3. Maps the intent to UI actions

If you install [Ollama](https://ollama.com) and run `ollama pull llama3.2:3b`, you get richer natural language understanding for free.

---

## The Header Bar

### Left side
- **Logo** — OpenDNA brand
- **Version** — Current build version (e.g. v0.2.0-beta)
- **XP badge** — Your accumulated experience points from Academy

### Right side
- **⌘K button** — Opens the command palette (or press Ctrl+K)
- **Dashboard button** — Opens the Dashboard overlay
- **Academy button** — Opens the Protein Academy
- **Save PDB** — Downloads the active structure (only shown when one is loaded)
- **☀/☾** — Toggle dark/light theme

---

## The Command Palette

Press **Ctrl+K** (or Cmd+K on Mac) anywhere in the app.

A modal appears with a search box and list of all available commands grouped by category:

- **Action** — fold, score, analyze, explain, design, iterative, MD, cost
- **File** — save PDB, save project
- **Import** — quick load famous proteins (ubiquitin, insulin, GFP, lysozyme, p53, KRAS, etc.)
- **View** — open Dashboard, Academy, toggle theme

### Navigation
- **Type** to filter (fuzzy match)
- **↑/↓** to navigate
- **Enter** to execute the highlighted command
- **Esc** to close

---

## Notifications (Toasts)

Toast notifications appear in the top-right whenever:
- A job starts, completes, or fails
- An action succeeds (sequence loaded, mutation applied, etc.)
- An error occurs

Each toast has:
- An icon (✓ success, ✕ error, ⓘ info, ⚠ warning)
- A title (sometimes)
- A message
- A close button (×)

Toasts auto-dismiss after 5 seconds.

---

## Analysis Panel

The **Full Analysis Suite** opens a comprehensive analysis overlay with these sections:

### 1. Sequence Properties
QikProp-equivalent table:
- Length, MW, isoelectric point (pI)
- GRAVY hydropathy
- Aromaticity, aliphatic index
- Charge at pH 7
- Instability index (with stable/unstable classification)
- Extinction coefficient (reduced and oxidized cysteines)
- N-terminal half-life (mammalian reticulocytes)

### 2. Lipinski's Rule of Five
Drug-likeness check:
- MW ≤ 500
- H-bond donors ≤ 5
- H-bond acceptors ≤ 10
- LogP ≤ 5

Pass/fail badge with violation list.

### 3. Hydropathy Profile
SVG line chart showing Kyte-Doolittle hydropathy across the sequence with a 9-residue window. Peaks above 1.6 over ~19 residues suggest transmembrane regions.

### 4. Intrinsic Disorder
Per-residue disorder scores with identified disordered regions. p53 famously shows ~70% disorder.

### 5. Amino Acid Composition
Bar chart of all 20 amino acid percentages.

### 6. Transmembrane Prediction
TMHMM-like prediction of membrane-spanning helices.

### 7. Signal Peptide
SignalP-like detection of N-terminal signal peptides for secreted proteins. Shows score and predicted cleavage site.

### 8. Aggregation Risk
TANGO-like prediction of aggregation-prone regions. Color-coded risk level (low/medium/high).

### 9. Post-Translational Modifications
- Phosphorylation sites by kinase consensus motif (PKA, PKC, CK2, CDK, GSK3, MAPK)
- N-glycosylation sites (NXS/T sequon)
- O-glycosylation sites (mucin-like regions)

### 10. Secondary Structure (if structure is loaded)
- Helix / strand / coil percentages
- Visual ribbon showing per-residue assignment
- Radius of gyration
- SASA estimate

### 11. Ramachandran Plot
Phi/psi scatter for all residues. Background regions show typical alpha-helix (blue) and beta-sheet (orange) zones.

### 12. Binding Pockets
Heuristic pocket detection ranked by score.

### 13. Bond Network (if structure loaded)
- H-bond count
- Salt bridge count
- Disulfide bond count with paired cysteines

---

## Dashboard

Click **Dashboard** in the header (or Cmd+K → Dashboard).

Shows:
- **Stat cards**: structures in session, completed jobs, running jobs, failed jobs, saved projects
- **Hardware table**: CPU, cores, RAM, GPU, backend, tier
- **Recent jobs table**: ID, type, status, progress for the last 10 jobs
- **Saved projects table**: name, structure count, save date

---

## Protein Academy

Click **Academy** in the header.

### Available Levels
- **Level 1: Amino Acid Match** (5 min, +50 XP)
  - Drag-drop matching game for 8 random amino acids
  - Match the 1-letter code to the full name
- **Level 2: Memory Quiz** (3 min, +75 XP)
  - 5 multiple-choice questions about amino acid properties
- **Level 3: Sequence Reader** (5 min, +100 XP)
  - Tutorial on reading protein sequences
- **Level 4: Famous Proteins Tour** (planned)
- **Level 5: Drug Design 101** (planned)

### XP and Badges
Each completed level awards XP that's displayed in the header badge. Future versions will add badges and a skill tree.

---

## Iterative Design

The killer feature. Automated protein optimization loop.

### How it works
1. **Round 0**: Fold your starting sequence and score it
2. **Round 1**: Use ESM-IF1 to generate N candidate alternatives. Score each.
3. **Keep best**: If any candidate scored higher, fold it to confirm and keep it as the new best.
4. **Repeat** for the configured number of rounds.

### Settings
- **Rounds** (1-10): How many iterations to run
- **Candidates per round** (1-20): How many alternatives to try each round

### Output
A panel with:
- Initial score → Final score with improvement %
- Optimization history chart (score per round)
- Best sequence per round with view buttons
- Final structure auto-added to your structures list

### Cost
- 3 rounds × 5 candidates = 15 design samples + ~6 fold operations
- On CPU: ~30 minutes for a 50-residue protein
- On GPU: ~2 minutes

---

## Component Manager

The Component Manager (header → **Components**) is the primary way to install, update, and uninstall the 11 ML engines bundled with OpenDNA. It behaves like a package catalog — nothing heavy is installed until you ask for it.

### The 11 engines

| Engine | Category | Size | Purpose |
|---|---|---|---|
| ESMFold | Folding | ~2.0 GB | Single-chain structure prediction |
| ColabFold | Folding | ~3.5 GB | MSA-based folding (AlphaFold2 weights) |
| Boltz-1 | Multimer | ~4.2 GB | Complex / multimer structure prediction |
| ESM-IF1 | Design | ~0.6 GB | Inverse folding / sequence design |
| RFdiffusion | Design | ~1.8 GB | Backbone generation from scratch |
| DiffDock | Docking | ~1.1 GB | Diffusion-based ligand docking |
| AutoDock Vina | Docking | ~0.05 GB | Classic lattice-based docking |
| OpenMM | Dynamics | ~0.3 GB | Molecular dynamics with AMBER14 + TIP3P |
| xTB | QM | ~0.2 GB | Semi-empirical quantum mechanics |
| ANI-2x | NNP | ~0.5 GB | Neural-network potential for small molecules |
| Ollama (llama3.2:3b) | LLM | ~2.0 GB | On-device chat and protein explanations |

Totals are displayed at the top of the manager and pulled live from disk via `GET /v1/components/disk-usage`.

### Install / Uninstall

Every card exposes four states: **Not installed**, **Installing (NN%)**, **Installed**, and **Update available**. Clicking **Install** calls `POST /v1/components/install` which streams progress through a Server-Sent Events channel. Installs are resumable — if you close the app mid-download it will pick up where it left off the next time.

Uninstall removes the weights directory and the HuggingFace cache entry. OpenDNA never touches other caches outside `~/.opendna/components/`.

### Categories

The sidebar groups engines by **Folding**, **Design**, **Docking**, **Dynamics**, **QM / NNP**, **Multimer**, and **LLM**. Filter chips at the top let you narrow to one category. A search box performs case-insensitive substring matching on name, description, and citation.

### Disk usage

At the bottom of the manager you'll see a sparkline-style bar for each installed engine, plus a total across all components. Click **Clean up** to remove any orphaned files (e.g. partial downloads from crashed installs).

---

## Visual Workflow Editor

Press **Workflow** in the header to open the node-based pipeline editor powered by React Flow. This replaces hand-written Python scripts for most end-to-end pipelines.

### The canvas

A zoomable, pannable infinite canvas. Drag from the node palette on the left onto the canvas to add a node. Connect nodes by dragging from an output port (right side) to an input port (left side). Edges are typed — an output of type `Structure` will only connect to inputs that accept `Structure`.

### The 10 node types

| Node | Inputs | Outputs | Description |
|---|---|---|---|
| **Sequence** | — | `seq: str` | Literal amino acid sequence entered by the user |
| **Import UniProt** | `accession` | `seq, metadata` | Fetches from UniProt REST |
| **Import PDB** | `pdb_id` | `structure` | Fetches from RCSB |
| **Fold** | `seq` | `structure, plddt` | Runs ESMFold / ColabFold / Boltz |
| **Design** | `structure` | `candidates[]` | Runs ESM-IF1 or RFdiffusion |
| **Score** | `seq` or `structure` | `score, breakdown` | Sequence + structure scoring |
| **Analyze** | `seq, structure` | `analysis (full 18+ suite)` | Runs the full analysis suite |
| **Dock** | `structure, ligand` | `poses[], affinity` | DiffDock or AutoDock Vina |
| **MD** | `structure` | `trajectory, rmsd, rmsf` | OpenMM molecular dynamics |
| **Export** | `anything` | — | Writes to file (PDB / PNG / SVG / GLTF / OBJ / YAML) |

### 5 built-in templates

Click **Templates** to spawn a pre-built graph:

1. **Fold → Score** — Classic 2-node pipeline
2. **Fold → Design → Evaluate** — Iterative design loop
3. **Fold → Dock → MD** — Structure-based drug design chain
4. **Import PDB → Analyze** — Analysis-only pipeline for an existing structure
5. **Import UniProt → Fold → Compare AF DB** — Benchmark against AlphaFold DB

### Save / Load

Click **Save** to serialize the current canvas to YAML:

```yaml
nodes:
  - id: n1
    type: sequence
    data:
      value: "MKTVRQERLK"
  - id: n2
    type: fold
    data:
      engine: esmfold
edges:
  - source: n1
    target: n2
    sourceHandle: seq
    targetHandle: seq
```

YAML files live in `~/.opendna/workflows/`. Drag a `.yaml` file onto the canvas to load it.

### Provenance

Every run of a workflow automatically writes a provenance DAG. Each node execution produces a `record_step` call with inputs, outputs, timestamps, engine version, and a content hash. You can later use `diff_steps`, `blame_residue`, and `bisect_regression` to investigate differences between runs.

---

## Real-Time Collaboration

The **Collab** button in the header opens the real-time collaboration panel. It uses Yjs CRDTs over a `y-websocket`-compatible relay so multiple users can edit the same project simultaneously without conflicts.

### Rooms

A room is identified by a UUID and is pinned to a specific project. Click **New room** to get a URL you can paste to a collaborator. Anyone with the URL can join.

### Cursors & presence

You see every teammate's cursor in the viewer (labeled with their username / color). The Collab panel lists who's currently in the room and how long they've been idle.

### Notes tab

A shared rich-text document powered by y-prosemirror. Use it for lab notebook entries that everyone in the room can edit together. Changes sync in under 200 ms on a LAN. Formatting: bold, italic, headings, bullet lists, code blocks, `$latex$` math.

### Residue comments tab

Click any residue in the 3D viewer, then click **Comment**. The comment is pinned to that residue and visible to everyone in the room, forever. Useful for review meetings ("I think R42 is the catalytic nucleophile — thoughts?"). Resolved comments are archived but preserved for provenance.

### Offline tolerance

If you lose your network connection the Yjs document keeps accepting edits locally. When you reconnect, the CRDT merge is automatic and conflict-free.

---

## Protein Search

The **Search** button in the header opens a unified search overlay covering UniProt, RCSB PDB, and AlphaFold DB.

### UniProt full-text search

Under the hood this calls `GET /v1/search/uniprot` which proxies to the UniProt REST API. You can search by:

- **Free text** — any keyword matching name, function, or organism
- **Reviewed only** — restrict to Swiss-Prot manually reviewed entries
- **Organism** — scientific or common name (e.g. `Homo sapiens`, `E. coli`)
- **Length range** — min/max residues
- **Has structure** — only entries with an AlphaFold DB or PDB entry

Results show accession, protein name, organism, length, and a review badge. Click any row to load that protein into the Tools tab.

### PDB search

Full-text search over RCSB PDB titles and abstracts, plus experimental method filter (X-ray, NMR, cryo-EM).

### AlphaFold DB fetch

Enter a UniProt accession to pull the pre-computed AlphaFold DB structure without running a fold.

---

## Academy: Levels 4–7 and Mini-games

The Protein Academy gained four new levels and three standalone mini-games in v0.5.0.

### New levels

- **Level 4: Secondary Structure** (+100 XP) — Interactive helix / sheet / coil labelling exercise
- **Level 5: Binding Sites** (+125 XP) — Identify catalytic residues in chymotrypsin, lysozyme, HIV protease
- **Level 6: Drug Design 101** (+150 XP) — Walkthrough of fragment-based drug discovery
- **Level 7: Fold Recognition** (+200 XP) — Classify folds into SCOP superfamilies

### 13 badges

Earn badges by completing challenges:

Rookie, Folder, Designer, Dynamicist, Crystallographer, Inverse Guru, Compiler, Night Owl, Speed Demon, Mutagenist, Cavity Seeker, Multimerist, Streak Master (7-day streak).

### 7 daily-challenge templates

Each day a challenge is rotated from one of 7 templates (mutate-and-fold, spot-the-difference, predict-pLDDT, etc.). Completing adds to your streak.

### 23-term glossary

A searchable glossary of 23 fundamental terms (alpha helix, beta sheet, pLDDT, RMSD, etc.). Each term has an illustrated flashcard that links to the Molstar viewer for examples.

### SQLite leaderboard + streaks

Your XP, badges, and streak are persisted to `~/.opendna/academy.db`. The leaderboard view shows top 100 locally (or globally if you opt in to the optional cloud sync).

### Mini-games

Standalone games accessible from the **Mini-games** header button without having to enter the Academy:

1. **AA Match** — Fast-paced drag-drop matching game. Score rises with speed and accuracy.
2. **Build-a-Helix** — Place residues onto a helical wheel to maximize amphipathicity.
3. **Famous Proteins Tour** — Guided exploration of ubiquitin, insulin, GFP, lysozyme, myoglobin, p53, KRAS, and EGFR with one-paragraph stories.

---

## Provenance & Time Machine

Every non-trivial action in OpenDNA is recorded as a provenance step — a node in a DAG that captures inputs, outputs, timestamps, engine versions, and content hashes. This powers the time-machine feature and makes reproducibility automatic.

### `record_step`

The primitive:

```python
from opendna.provenance import record_step

step_id = record_step(
    operation="fold",
    inputs={"sequence": "MKTV..."},
    outputs={"pdb_hash": "sha256:..."},
    engine="esmfold",
    engine_version="1.0.3",
    parent_ids=["step_abc123"],
)
```

Most steps are recorded automatically — you rarely call this directly.

### `diff_steps`

Compare two steps (or two runs) and get a structured diff:

```python
from opendna.provenance import diff_steps
d = diff_steps("step_a", "step_b")
print(d.rmsd, d.plddt_delta, d.mutation_list)
```

### `blame_residue`

Given a structure and a residue, walk the DAG backwards to find the exact step that introduced the current value:

```python
from opendna.provenance import blame_residue
source = blame_residue(structure_id="s_42", residue_index=48)
print(source.operation, source.step_id)
```

### `bisect_regression`

Binary-search across the history of a project to find when a regression was introduced:

```python
from opendna.provenance import bisect_regression
culprit = bisect_regression(
    project_id="proj_1",
    good_step="step_initial",
    bad_step="step_latest",
    test=lambda s: s.mean_plddt >= 80,
)
```

### Time machine UI

Click **History** in the bottom bar to open a timeline scrubber. Drag the handle to rewind the project to any earlier state — your structures, analyses, and notes revert atomically. Release and you're back at the latest state.

---

## Priority Job Queue & WebSocket Streaming

v0.5.0 replaces the old flat job list with a 3-tier priority queue plus real-time WebSocket streaming.

### The 3 tiers

| Tier | Use case | Pre-emption |
|---|---|---|
| **interactive** | Small jobs from the UI | Never pre-empted |
| **normal** | Standard jobs | Pre-empted by `interactive` if GPU is saturated |
| **batch** | Overnight / bulk runs | Pre-empted by both other tiers |

Enqueue with:

```bash
curl -X POST http://127.0.0.1:8765/v1/queue/enqueue \
  -H "Content-Type: application/json" \
  -d '{"type": "fold", "priority": "interactive", "payload": {"sequence": "MKTV..."}}'
```

### GPU pool + warm-model cache

The scheduler keeps the most recently used model in GPU memory so back-to-back jobs against the same engine pay zero load time. LRU eviction when memory is tight.

### WebSocket streaming

Subscribe to a job's events:

```js
const ws = new WebSocket(`ws://127.0.0.1:8765/v1/ws/jobs/${jobId}`);
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  console.log(msg.phase, msg.progress, msg.partial_result);
};
```

Events include `queued`, `started`, `progress`, `partial_result`, `completed`, `failed`.

---

## Lab Notebook & Zenodo DOI Minting

The header's **Notebook** entry (inside Save → Notebook) opens a per-project lab notebook.

### Notebook features

- Rich text with `$latex$` math and code blocks
- Embed any structure, figure, or analysis from the current project inline
- Auto-populated timestamps from provenance steps
- Export to Markdown, PDF, or `.ipynb`

### Mint a DOI on Zenodo

When you're ready to publish:

1. Go to **Notebook → Publish → Zenodo**
2. Enter your Zenodo token (or set `ZENODO_TOKEN` in your environment)
3. Fill in title, authors, keywords, description
4. Click **Mint DOI**

OpenDNA bundles the entire project (provenance DAG, structures, notebook, SBOM, YAML workflow) into a single `.zip`, uploads it, and returns the permanent DOI. The DOI is pinned into the notebook for future reference.

---

## Figure & 3D Export

Click **Save → Export** to open the export dialog:

- **PNG / SVG figure** — Snapshot of the current viewer at any resolution (up to 8K). SVG is vector.
- **GLTF / OBJ 3D mesh** — Export the current representation as a 3D mesh for use in Blender, Maya, or a web WebGL scene.
- **Animated GIF trajectory** — Record a short GIF of the protein rotating, or of an MD trajectory played back.
- **Multi-frame PDB** — Write every frame of an MD trajectory as a single PDB with `MODEL` records.

All exports write to your chosen path and log a provenance step.

---

## Ramachandran Plot

Click **Ramachandran** in the header (or press `R`) to open the interactive phi/psi scatter plot.

- Each dot is a residue. Background density contours show favored, allowed, and disallowed regions.
- **Hover** a dot to see residue number, amino acid, phi, psi.
- **Click** a dot — the corresponding residue is highlighted in the 3D viewer and scrolled into view.
- **Filter by region**: click **Favored**, **Allowed**, or **Outlier** chips to show only residues in that region.
- **Export** to PNG or SVG with one click.

This is the fastest way to spot structural outliers in a predicted model.

---

## PQC Auth Layer

When `OPENDNA_AUTH_REQUIRED=1` is set, every API call must carry `Authorization: Bearer <api-key>` and every user is authenticated with post-quantum crypto.

### Key primitives

- **ML-KEM-768** — NIST-standardized post-quantum KEM, used for wrapping the user's API key at login
- **ML-DSA-65** — NIST-standardized post-quantum signature, used to sign every audit log entry

These are provided by `liboqs-python`. OpenDNA does **not** roll its own crypto.

### Endpoints

- `POST /v1/auth/register` — create a user (first user becomes admin)
- `POST /v1/auth/login` — authenticate and receive a wrapped API key
- `POST /v1/auth/rotate` — rotate your API key
- `GET /v1/auth/me` — your profile
- `POST /v1/auth/api-keys` — mint a new API key with custom scopes

### Audit log

Every request is appended to `~/.opendna/audit.log` with a hash-chained, ML-DSA-65-signed entry. The log is verified on server startup; if tampering is detected the server refuses to boot. Inspect the log with:

```bash
opendna audit verify
opendna audit tail --n 100
```

### GDPR export & erasure

A user can request a full export of their data or ask for erasure:

```bash
curl -X POST http://127.0.0.1:8765/v1/compliance/gdpr/export \
  -H "Authorization: Bearer $KEY" \
  -d '{"user_id": "alice"}' -o alice.zip

curl -X POST http://127.0.0.1:8765/v1/compliance/gdpr/erase \
  -H "Authorization: Bearer $KEY" \
  -d '{"user_id": "alice"}'
```

Erasure is permanent and audit-logged but leaves hashes in the audit log so the chain remains verifiable.

---

## Error Boundaries & Self-Healing

### React error boundaries

Every major panel is wrapped in an `ErrorBoundary`. When a panel crashes you see a friendly card with the error message, a "Report" button (which writes to `~/.opendna/crashes/` with secrets redacted), and a "Retry" button — instead of the whole UI going blank.

### `@retry` decorator

Python-side engine calls are wrapped in a `@retry(attempts=3, backoff=exp)` decorator so transient errors (HuggingFace 5xx, connection resets) don't fail the whole job.

### `SelfHealer` background thread

A daemon thread checks every 30 s for common failure modes and repairs them:

- Stale lock files in `~/.opendna/jobs/`
- Orphaned GPU allocations
- Corrupt SQLite journal files
- Dangling PyInstaller temp directories

All repairs are logged and auditable.

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| **Ctrl+K** / Cmd+K | Open command palette |
| **Ctrl+/** | Open command palette |
| **F** | Fold current sequence |
| **S** | Score current sequence |
| **A** | Run analysis suite |
| **Esc** | Close any open overlay |
| **Ctrl+S** | Save current PDB |
| **Ctrl+Shift+S** | Save project workspace |

Shortcuts that don't conflict with text inputs work everywhere. Single-letter shortcuts only work when not focused on an input.

---

## Tips & Tricks

### Speed up CPU folding
- Use **shorter sequences** first to test (under 50 aa folds in seconds)
- The result cache means folding the same sequence twice is instant
- If you have NVIDIA GPU, install CUDA torch for ~50x speedup

### Get richer AI explanations
Install Ollama and pull a small model:
```bash
ollama pull llama3.2:3b
ollama serve  # in background
```
Then "Explain This Protein" uses real LLM responses instead of the heuristic fallback.

### Analyze multiple proteins
Use the Structures tab to keep a history. The compare button lets you put two side-by-side.

### Find binding pockets
Run **Full Analysis Suite** on a folded protein. The "Putative Binding Pockets" section ranks the top 5 cavities.

### Understand your protein in plain English
Use **Explain This Protein (AI)** for a friendly summary that even a high school student can understand.
