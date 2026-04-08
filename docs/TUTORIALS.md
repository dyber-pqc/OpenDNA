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

## Tutorial 11: Install and use DiffDock via the Component Manager

**Goal:** Install the DiffDock docking engine from inside the desktop app and dock a small-molecule ligand against a folded protein.

### Prerequisites
- Desktop app or browser UI running
- ~1.5 GB free disk space
- A folded structure (we'll use ubiquitin from the Import tab)

### Steps

1. **Open the Component Manager**
   - Click **Components** in the header
   - You'll see 11 engine cards. Filter to the **Docking** category.

2. **Install DiffDock**
   - Click **Install** on the DiffDock card
   - A progress bar streams from `POST /v1/components/install`
   - Wait ~2 minutes for the weights to download (~1.1 GB)
   - Status changes to **Installed** when done

3. **Load your receptor**
   - Close the Component Manager
   - Import tab → click **ubiquitin**
   - Click **Predict Structure** (ESMFold must be installed — if not, install it first)

4. **Supply a ligand**
   - In the sidebar, open the **Docking** section
   - Paste a SMILES string for your ligand:
     ```
     CC(=O)OC1=CC=CC=C1C(=O)O
     ```
   - (That's aspirin — a nice small test ligand.)

5. **Run the dock via CLI equivalent**
   ```bash
   curl -X POST http://127.0.0.1:8765/v1/dock \
     -H "Content-Type: application/json" \
     -d '{
       "receptor_pdb": "...",
       "ligand_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
       "engine": "diffdock",
       "num_poses": 10
     }'
   ```

6. **View the results**
   - The viewer displays the top-scoring pose by default
   - Use the pose slider at the bottom to flip through ranked poses
   - Each pose carries an affinity estimate

### What you learned
- How the Component Manager gates heavy ML engines
- How DiffDock differs from AutoDock Vina (diffusion vs. lattice search)
- How to inspect pose rankings from the UI and the API

### Next
- Try AutoDock Vina via `"engine": "vina"` and compare
- Feed the best pose into an MD run to see if it stays bound

---

## Tutorial 12: Build a fold → design → evaluate workflow in the Visual Editor

**Goal:** Use the visual workflow editor to build a reproducible pipeline without writing any Python.

### Steps

1. **Open the editor**
   - Click **Workflow** in the header
   - The canvas opens empty

2. **Load a template**
   - Click **Templates → Fold → Design → Evaluate**
   - A pre-built 5-node graph appears:
     ```
     [Sequence] → [Fold] → [Design] → [Fold] → [Score]
     ```

3. **Configure the Sequence node**
   - Double-click the Sequence node
   - Paste ubiquitin:
     ```
     MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG
     ```

4. **Configure the Design node**
   - Double-click the Design node
   - Set engine: `esm_if1`
   - Candidates: `10`

5. **Run**
   - Click **Run** in the toolbar
   - Nodes light up green as they complete. Progress is streamed via WebSocket.
   - Total runtime: ~4 minutes on GPU, ~25 minutes on CPU

6. **Save the workflow**
   - Click **Save → YAML**
   - Name it `ubiquitin-redesign.yaml`
   - It lands in `~/.opendna/workflows/`

7. **Inspect the provenance**
   - Click **History** in the bottom bar
   - You'll see one DAG node per workflow step with inputs, outputs, and hashes
   - Drag the timeline handle back to the Design step to inspect the 10 candidates

8. **Re-run from YAML via CLI**
   ```bash
   opendna workflow run ~/.opendna/workflows/ubiquitin-redesign.yaml
   ```

### What you learned
- How to use templates as a starting point
- How node types and edges enforce type safety
- How provenance is automatically recorded
- How to save / replay workflows without opening the UI

---

## Tutorial 13: Real-time collaboration with a teammate via Yjs

**Goal:** Co-edit a project with a colleague in real time.

### Steps

1. **Start a room**
   - Open your project in OpenDNA
   - Click **Collab** in the header
   - Click **New room**
   - Copy the room URL (it looks like `opendna://collab/8a4f...`)

2. **Share it**
   - Send the URL to your teammate via Slack / Teams / email
   - They click it, the app opens, and they join the same project

3. **Use the Notes tab**
   - Both of you can type in the shared Markdown document
   - You'll see each other's cursors live
   - Try `**bold**`, `# headings`, ` ```python ` code blocks

4. **Pin residue comments**
   - Click residue K48 in the viewer
   - Click **Comment**
   - Type "Suspected catalytic nucleophile — let's mutate to R"
   - Your teammate sees the comment instantly and can reply

5. **Simulate offline tolerance**
   - Disable your Wi-Fi
   - Keep editing the notes
   - Re-enable Wi-Fi — the Yjs CRDT auto-merges without conflicts

6. **Verify sync via the API**
   ```bash
   curl http://127.0.0.1:8765/v1/collab/rooms/<room-id>
   ```
   Shows current participants and last-update timestamp.

### What you learned
- How Yjs CRDTs give conflict-free real-time editing
- How comments are pinned to residues and persist forever
- How the system tolerates network interruptions

---

## Tutorial 14: Search UniProt for cancer proteins and fold the top hit

**Goal:** Use the unified search to find a relevant protein and fold it.

### Steps

1. **Open the search overlay**
   - Click **Search** in the header (or press `Ctrl+Shift+F`)

2. **Search with filters**
   - Query: `cancer kinase`
   - Check **Reviewed only**
   - Organism: `Homo sapiens`
   - Length: `100`–`500`
   - Click **Search**

3. **Inspect results**
   - You'll see ~20 Swiss-Prot reviewed hits
   - Each row: accession, name, length, review badge
   - Click the first result — say, **BRAF_HUMAN**

4. **Fold it**
   - Back in the Tools tab the sequence is loaded
   - Click **Predict Structure**
   - ESMFold runs (installed from Tutorial 11 or Component Manager)

5. **Analyze**
   - Click **Full Analysis Suite**
   - Look at disorder (BRAF has a disordered N-terminus), binding pockets (the ATP pocket should rank #1)

6. **Equivalent cURL**
   ```bash
   curl "http://127.0.0.1:8765/v1/search/uniprot?q=cancer+kinase&reviewed=true&organism=Homo+sapiens"
   ```

### What you learned
- How to compose filters in the unified search
- How results integrate seamlessly with the Tools tab
- How to reach the same functionality from the API

---

## Tutorial 15: Enable PQC auth and create API keys

**Goal:** Turn on post-quantum authentication and mint a scoped API key.

### Prerequisites
```bash
pip install "opendna[pqc]"
# macOS
brew install liboqs
# Debian/Ubuntu
sudo apt install liboqs-dev
```

### Steps

1. **Start the server with auth required**
   ```bash
   export OPENDNA_AUTH_REQUIRED=1
   export OPENDNA_AUTH_DB=~/.opendna/auth.db
   python -c "from opendna.api.server import start_server; start_server(port=8765)"
   ```

2. **Register the first user (admin)**
   ```bash
   curl -X POST http://127.0.0.1:8765/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"username": "alice", "password": "correct horse battery staple"}'
   ```

   Response:
   ```json
   {
     "user_id": "u_001",
     "role": "admin",
     "api_key": "odna_pqc_9f3a...",
     "ml_dsa_public_key": "...base64..."
   }
   ```

   **Save the API key now — it is only shown once.**

3. **Test it**
   ```bash
   export KEY="odna_pqc_9f3a..."
   curl http://127.0.0.1:8765/v1/auth/me -H "Authorization: Bearer $KEY"
   ```

4. **Create a scoped API key for a CI pipeline**
   ```bash
   curl -X POST http://127.0.0.1:8765/v1/auth/api-keys \
     -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "github-ci",
       "scopes": ["fold", "analyze"],
       "expires_in_days": 90
     }'
   ```

5. **Register a second user**
   ```bash
   curl -X POST http://127.0.0.1:8765/v1/auth/register \
     -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"username": "bob", "password": "..."}'
   ```
   Bob is created as a regular user (not admin) because he is registered by alice.

6. **Verify the audit log**
   ```bash
   opendna audit verify
   opendna audit tail --n 20
   ```

### What you learned
- How to enable PQC auth
- How the first-user-is-admin pattern works
- How to mint scoped API keys for automation
- How the hash-chained audit log is verified end-to-end

---

## Tutorial 16: Mint a Zenodo DOI for your project

**Goal:** Publish a reproducible package of your project to Zenodo and get a citable DOI.

### Prerequisites
- A Zenodo account (free at [zenodo.org](https://zenodo.org))
- A personal access token from [zenodo.org/account/settings/applications/](https://zenodo.org/account/settings/applications/)
- An OpenDNA project with at least one folded structure

### Steps

1. **Set your token**
   ```bash
   export ZENODO_TOKEN="your_token_here"
   ```

2. **Open the Lab Notebook**
   - In the desktop app, click **Save → Notebook**
   - Fill in at least:
     - Title (e.g. "Computational redesign of ubiquitin K48")
     - Authors (e.g. "Alice Smith; Bob Jones")
     - Description / abstract
     - Keywords (comma-separated)

3. **Click Publish → Zenodo**
   - OpenDNA bundles:
     - Provenance DAG (YAML)
     - Every structure (PDB)
     - Every figure (PNG + SVG)
     - Notebook (Markdown + PDF)
     - Workflow YAML (if present)
     - CycloneDX SBOM
     - Manifest with SHA-256 hashes
   - Uploaded as a single `.zip`

4. **Confirm**
   - The response dialog shows the DOI:
     ```
     10.5281/zenodo.12345678
     ```
   - Click **Copy DOI** or **Open on Zenodo**

5. **CLI alternative**
   ```bash
   opendna publish zenodo \
     --project ~/.opendna/projects/ubiquitin_study \
     --title "Computational redesign of ubiquitin K48" \
     --author "Alice Smith" \
     --keyword "protein,design,ESMFold"
   ```

6. **Re-fetch your published package later**
   ```bash
   opendna fetch zenodo 10.5281/zenodo.12345678
   ```
   This pulls the `.zip`, verifies hashes, and reconstructs the project locally — a complete reproducibility round-trip.

### What you learned
- How the lab notebook bundles a project into a single artifact
- How to mint a DOI programmatically
- How to round-trip a published project for reproducibility

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
