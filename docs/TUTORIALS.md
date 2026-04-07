# OpenDNA Tutorials

Step-by-step walkthroughs for common protein engineering tasks.

## Tutorial 1: Analyze Your First Protein (5 minutes)

**Goal:** Learn the basic OpenDNA workflow on a real protein.

### Steps

1. **Start the platform** (if not already running):
   - Terminal 1: `python -c "from opendna.api.server import start_server; start_server(port=8765)"`
   - Terminal 2: `cd ui && npm run dev`
   - Browser: `http://localhost:5173`

2. **Import ubiquitin** from the famous proteins list:
   - Click the **Import** tab in the sidebar
   - Click **ubiquitin** in the famous proteins grid
   - You should see a green toast: "UBC_HUMAN — Loaded 685 aa from Homo sapiens"
   - The sidebar switches to the **Tools** tab automatically

3. **Score the sequence instantly** (no model download needed):
   - Click **Score Protein**
   - A score card appears showing the overall quality and breakdown

4. **Run the full analysis suite**:
   - Click **Full Analysis Suite**
   - Browse through ~12 sections of analysis
   - **Look for:** disorder prediction (UBC has some disorder), aggregation risk, phosphorylation sites

5. **Try a famous mutation:**
   - In the **Mutate Active Protein** field, type `K48R`
   - Click **Apply Mutation & Refold**
   - This is the famous K48R mutation that disrupts polyubiquitin chain formation

### What you learned
- How to import proteins from UniProt
- The instant scoring system
- The comprehensive analysis suite
- How to apply point mutations

---

## Tutorial 2: Predict and Visualize a 3D Structure (10 minutes)

**Goal:** Fold a small protein and explore the 3D viewer.

### Prerequisites
First-time only: ESMFold model will download (~8 GB). Make sure you have a fast internet connection and ~10 GB free disk space.

### Steps

1. **Use a small test sequence:**
   - Paste this in the Tools tab:
     ```
     MKTVRQERLKSIVRILERSKEPVSGAQLAEELS
     ```
   - That's 33 residues, perfect for a quick fold

2. **Click Predict Structure**
   - First time: ESMFold downloads (~8 GB, watch the API terminal)
   - Subsequent runs: instant model load
   - For 33 residues on CPU: ~1-2 minutes
   - For 33 residues on GPU: ~5 seconds

3. **Explore the 3D structure:**
   - **Drag** the protein to rotate
   - **Scroll** to zoom
   - **Right-click drag** to pan

4. **Switch to confidence coloring:**
   - Click **pLDDT colors** at the bottom-left
   - Blue regions are high confidence
   - Orange/red regions are low confidence (often loops or disordered)

5. **Save the structure:**
   - Click **Save PDB** in the header
   - The PDB file downloads to your computer
   - You can open it in any other molecular viewer (PyMOL, ChimeraX, etc.)

### What you learned
- How to fold proteins with ESMFold
- 3D viewer controls
- Confidence visualization
- Exporting PDB files

---

## Tutorial 3: Design Alternative Sequences with ESM-IF1 (15 minutes)

**Goal:** Take a folded protein and generate alternative sequences that should fold into the same shape.

### Steps

1. **First, fold a protein** (use Tutorial 2's sequence or any other)

2. **Click "Design 10 Sequences (ESM-IF1)"**
   - First time: ESM-IF1 model downloads (~600 MB)
   - Generates 10 alternative sequences
   - Each is scored by recovery (% of residues matching the original)

3. **Review the results:**
   - A panel appears with the 10 candidates ranked by score
   - Notice the recovery percentages (typically 4-30% with default temperature)
   - High recovery = conservative redesign
   - Low recovery = aggressive redesign of the same fold

4. **Verify a candidate by folding it:**
   - Click **Fold** on candidate #1
   - This folds the new sequence
   - Add it to your structures list

5. **Compare original vs designed:**
   - Switch to the **Structures** tab
   - Click **vs** on the original structure
   - The viewer splits to show both side-by-side
   - Visually compare — they should have similar topology if ESM-IF1 worked

### What you learned
- How inverse folding works
- Sequence recovery interpretation
- How to verify designed sequences by re-folding
- Side-by-side structure comparison

---

## Tutorial 4: Iterative Design Loop (30 minutes)

**Goal:** Use OpenDNA's killer feature — automated protein optimization over multiple rounds.

### Steps

1. **Pick a starting sequence:**
   ```
   MKTVRQERLKSIVRILER
   ```
   (18 residues — small enough to iterate quickly on CPU)

2. **Configure iterative design:**
   - In the **Iterative Design Loop** section
   - Set **rounds: 3** and **candidates: 5**
   - That's 15 total designs across 3 rounds

3. **Click "Run Iterative Design"**
   - You'll see a series of toasts as each round runs
   - Rounds typically take 1-3 minutes each on CPU
   - Total: ~10 minutes

4. **Review the results panel:**
   - Initial score → Final score with improvement %
   - Optimization history chart
   - Best sequence per round
   - The final structure is auto-added to your structures list

5. **Compare initial and final:**
   - Initial sequence is in your history
   - Final sequence is the new active structure
   - Use the **vs** button to compare them in 3D

### What you learned
- The iterative optimization concept
- How to read the score history
- How to interpret improvement
- The fold ↔ design feedback loop

### Try this variation
Set rounds to 5, candidates to 10. Watch a longer optimization. See if it converges or keeps improving.

---

## Tutorial 5: Famous Mutations to Try

These are real mutations from biology and disease. Try them in OpenDNA.

### Tumor suppressors and oncogenes

**KRAS G12D** (most common cancer mutation):
1. Import → kras
2. Mutate → `G12D`
3. This is the famous G12D KRAS mutation found in pancreatic cancer

**p53 R175H** (tumor suppressor mutation):
1. Import → p53
2. Mutate → `R175H`
3. This is one of the most common p53 mutations in human cancer

### Insulin variants

**Insulin lispro** (Humalog) — switch the position of B28 and B29 to make a fast-acting insulin
- Import insulin → mutate `K28P` then `P29K` (sequentially)

### Hemoglobin S (sickle cell)

- Import hemoglobin_alpha → not the right chain
- Try fetching `P68871` (hemoglobin beta) → mutate `E6V`

### CFTR ΔF508 (cystic fibrosis)

- Fetch `P13569` (CFTR)
- Note: very large protein, don't fold on CPU

---

## Tutorial 6: Use the Command Palette (3 minutes)

**Goal:** Master the keyboard-driven workflow.

### Steps

1. **Open the palette anywhere:** Press **Ctrl+K** (or Cmd+K on Mac)

2. **Try fuzzy search:**
   - Type "ubiq" → finds "Import ubiquitin"
   - Type "fold" → finds the fold action
   - Type "score" → finds the score action

3. **Quick imports:**
   - Ctrl+K → "import gfp" → Enter
   - The sequence loads automatically

4. **Quick analysis:**
   - Ctrl+K → "analyze" → Enter
   - Skips clicking

5. **Navigate without a mouse:**
   - Ctrl+K → up/down arrows → Enter
   - Esc to close

### Power user tip
With single-letter shortcuts (only when not focused on an input):
- **F** = fold current sequence
- **S** = score
- **A** = analyze
- **Esc** = close everything

---

## Tutorial 7: The Protein Academy (15 minutes)

**Goal:** Learn protein basics through interactive games.

### Steps

1. Click **Academy** in the header

2. **Level 1: Amino Acid Match (5 min, +50 XP):**
   - Click letters and names to match them up
   - 8 random amino acids per game
   - +10 score per match
   - Complete to earn 50 XP

3. **Level 2: Memory Quiz (3 min, +75 XP):**
   - 5 multiple-choice questions about amino acid properties
   - Test your knowledge of charge, structure, function

4. **Level 3: Sequence Reader (5 min, +100 XP):**
   - Tutorial on reading protein sequences
   - Learn the meaning of each letter
   - Pattern recognition tips

5. **Watch your XP grow** in the header badge

### Educational notes
- The 20 standard amino acids are the building blocks of all proteins
- Their letter codes (A, C, D, E, F, G, H, I, K, L, M, N, P, Q, R, S, T, V, W, Y) are universally used
- Each has different properties: charge, size, hydrophobicity, special function
- Reading a sequence and predicting properties is the foundational skill

---

## Tutorial 8: Compare Two Structures (10 minutes)

**Goal:** Use OpenDNA to compare a wild-type protein and a mutant.

### Steps

1. **Fold the wild-type:**
   - Paste: `MKTVRQERLKSIVRILER`
   - Click Predict Structure
   - Wait for the fold

2. **Apply a mutation:**
   - Mutate field: `K2D`
   - Click Apply Mutation & Refold
   - Wait for the new fold

3. **Compare them:**
   - Click the **Structures** tab
   - You should see 2 structures
   - Click **vs** on the first one (the wild-type)
   - The viewer splits into two

4. **Visually inspect:**
   - Are they similar topology?
   - Did the mutation cause any visible changes?
   - Use both viewers' rotation independently

5. **Quantitative comparison** (via API):
   ```bash
   curl -X POST http://localhost:8765/v1/compare \
     -H "Content-Type: application/json" \
     -d '{"pdb_a": "...", "pdb_b": "..."}'
   ```
   Returns RMSD, secondary structure identity, radius of gyration.

---

## Tutorial 9: Estimate the Cost of Your Protein

**Goal:** Find out how much it would cost to actually synthesize and produce your designed protein.

### Steps

1. Have a sequence loaded (any size)

2. Click **Cost & Carbon Estimate**

3. Review:
   - **Synthesis costs** from Twist Bioscience, IDT, GenScript
   - **Cheapest vendor** highlighted
   - **Carbon footprint** comparison: CPU vs GPU compute

4. Use this to plan budget for wet-lab experiments

### What the estimates mean
- Synthesis = ordering the DNA gene that codes for your protein
- After ordering: clone into vector → transform into E. coli → grow → purify → assay
- Total wet-lab cost typically 5-20x the synthesis cost

---

## Tutorial 10: Save and Reload a Project

**Goal:** Don't lose your work between sessions.

### Steps

1. Build up some structures (fold a few proteins)

2. **Save:**
   - Press **Ctrl+Shift+S** (or use Cmd+K → "save project")
   - Enter a project name (e.g. `my_first_project`)
   - Toast confirms save

3. **Find your saved project:**
   - Open the Dashboard (header button)
   - "Saved Projects" section lists all your projects

4. **Load a project** (manually via API for now):
   ```bash
   curl -X POST http://localhost:8765/v1/projects/load \
     -d '{"name":"my_first_project"}'
   ```
   - UI auto-load is coming in v0.3

### Where projects live
`~/.opendna/projects/<name>/workspace.json`

---

## Tutorial Cheat Sheet

| Goal | Click path |
|---|---|
| Fold a protein | Tools → paste seq → Predict Structure |
| Score instantly | Tools → paste seq → Score Protein |
| Full analysis | Tools → Full Analysis Suite |
| Apply mutation | Tools → Mutate field → Apply |
| Design alternatives | Tools → Design 10 Sequences |
| Iterative optimization | Tools → Run Iterative Design |
| Import famous protein | Import → click name (or Cmd+K → "import X") |
| Compare two structures | Structures tab → vs button |
| AI explanation | Tools → Explain This Protein |
| Cost estimate | Tools → Cost & Carbon Estimate |
| Quick MD | Tools → Quick MD |
| Open Dashboard | Header → Dashboard |
| Open Academy | Header → Academy |
| Command palette | Ctrl+K |
| Save project | Ctrl+Shift+S |
| Save PDB | Ctrl+S or header button |
