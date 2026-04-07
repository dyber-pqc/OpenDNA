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
