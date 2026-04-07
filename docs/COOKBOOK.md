# OpenDNA Cookbook

Recipes for common protein engineering tasks. Each recipe is short, copy-pasteable, and focused on one goal.

## Table of Contents
1. [Fold a sequence and check confidence](#1-fold-a-sequence-and-check-confidence)
2. [Score a designed protein quickly](#2-score-a-designed-protein-quickly)
3. [Generate 100 alternative sequences](#3-generate-100-alternative-sequences)
4. [Auto-optimize a protein over 5 rounds](#4-auto-optimize-a-protein-over-5-rounds)
5. [Find binding pockets in a structure](#5-find-binding-pockets-in-a-structure)
6. [Apply a known oncogenic mutation](#6-apply-a-known-oncogenic-mutation)
7. [Compare wild-type and mutant structures](#7-compare-wild-type-and-mutant-structures)
8. [Predict if a protein is intrinsically disordered](#8-predict-if-a-protein-is-intrinsically-disordered)
9. [Find aggregation-prone regions](#9-find-aggregation-prone-regions)
10. [Detect a signal peptide](#10-detect-a-signal-peptide)
11. [Predict transmembrane helices](#11-predict-transmembrane-helices)
12. [Find phosphorylation and glycosylation sites](#12-find-phosphorylation-and-glycosylation-sites)
13. [Estimate stability change of a mutation](#13-estimate-stability-change-of-a-mutation)
14. [Align two sequences](#14-align-two-sequences)
15. [Estimate the cost to synthesize a protein](#15-estimate-the-cost-to-synthesize-a-protein)
16. [Run a quick MD stability check](#16-run-a-quick-md-stability-check)
17. [Get an AI explanation of a protein](#17-get-an-ai-explanation-of-a-protein)
18. [Save and reload a project](#18-save-and-reload-a-project)
19. [Use the CLI from the terminal](#19-use-the-cli-from-the-terminal)
20. [Use the API from a Python script](#20-use-the-api-from-a-python-script)

---

## 1. Fold a sequence and check confidence

**UI:**
1. Tools tab → paste sequence → Predict Structure
2. View pLDDT colors at bottom-left

**API (PowerShell):**
```powershell
$body = @{sequence = "MKTVRQERLKSIVRILER"} | ConvertTo-Json
$job = Invoke-RestMethod -Uri "http://localhost:8765/v1/fold" -Method Post -ContentType "application/json" -Body $body
# Poll for completion
do {
    Start-Sleep -Seconds 2
    $status = Invoke-RestMethod -Uri "http://localhost:8765/v1/jobs/$($job.job_id)"
} while ($status.status -eq "running")
$status.result.mean_confidence
```

**API (curl):**
```bash
JOB=$(curl -s -X POST http://localhost:8765/v1/fold \
  -H "Content-Type: application/json" \
  -d '{"sequence":"MKTVRQERLKSIVRILER"}' | jq -r .job_id)

while true; do
  STATUS=$(curl -s http://localhost:8765/v1/jobs/$JOB)
  if echo "$STATUS" | grep -q '"completed"'; then break; fi
  sleep 2
done
echo "$STATUS" | jq .result.mean_confidence
```

---

## 2. Score a designed protein quickly

**UI:**
1. Paste sequence → Score Protein

**API:**
```powershell
$body = @{sequence = "MKTVRQERLK"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8765/v1/evaluate" -Method Post -ContentType "application/json" -Body $body
```

```bash
curl -s -X POST http://localhost:8765/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"sequence":"MKTVRQERLK"}' | jq .
```

---

## 3. Generate 100 alternative sequences

**UI:** Fold a protein first, then click "Design 10 Sequences" multiple times, OR change the request to 100.

**API:**
```bash
PDB=$(cat folded.pdb)
curl -X POST http://localhost:8765/v1/design \
  -H "Content-Type: application/json" \
  -d "{\"pdb_string\":\"$PDB\",\"num_candidates\":100,\"temperature\":0.2}"
```

---

## 4. Auto-optimize a protein over 5 rounds

**UI:**
1. Paste sequence
2. Set rounds=5, candidates=5
3. Click Run Iterative Design

**API:**
```bash
curl -X POST http://localhost:8765/v1/iterative_design \
  -H "Content-Type: application/json" \
  -d '{"sequence":"MKTVRQERLK","n_rounds":5,"candidates_per_round":5}'
```

---

## 5. Find binding pockets in a structure

**UI:** Fold or import a structure, then click "Full Analysis Suite". Look for the "Putative Binding Pockets" section.

**API:**
```bash
curl -X POST http://localhost:8765/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"sequence":"...","pdb_string":"..."}' | jq .structure.pockets
```

---

## 6. Apply a known oncogenic mutation

**Example:** KRAS G12D (the most common cancer mutation).

**UI:**
1. Import → kras
2. Mutate field: `G12D`
3. Apply Mutation & Refold

**API:**
```bash
curl -X POST http://localhost:8765/v1/mutate \
  -H "Content-Type: application/json" \
  -d '{"sequence":"MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHHYREQIKRVKDSEDVPMVLVGNKCDLPSRTVDTKQAQDLARSYGIPFIETSAKTRQGVDDAFYTLVREIRKHKEKMSKDGKKKKKKSKTKCVIM","mutation":"G12D"}'
```

---

## 7. Compare wild-type and mutant structures

**UI:**
1. Fold the wild-type
2. Apply mutation → it auto-folds
3. Switch to Structures tab → click "vs" on the wild-type → side-by-side viewer

**API:**
```bash
curl -X POST http://localhost:8765/v1/compare \
  -H "Content-Type: application/json" \
  -d '{"pdb_a":"ATOM...","pdb_b":"ATOM..."}'
```
Returns RMSD, ss_identity, radius of gyration for each.

---

## 8. Predict if a protein is intrinsically disordered

Famous example: p53. ~70% disordered.

**UI:**
1. Import → p53
2. Click Full Analysis Suite
3. Scroll to "Intrinsic Disorder" section

**API:**
```bash
curl -X POST http://localhost:8765/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"sequence":"..."}' | jq .disorder
```

---

## 9. Find aggregation-prone regions

**UI:** Full Analysis Suite → "Aggregation Risk" section.

**API response shape:**
```json
{
  "aggregation": {
    "scores": [...],
    "aggregation_prone_regions": [
      {"start": 12, "end": 19, "length": 8, "sequence": "IFAGKQLE"}
    ],
    "n_apr": 1,
    "overall_aggregation_score": 0.34,
    "risk_level": "medium"
  }
}
```

**Engineering tip:** To reduce aggregation, mutate hydrophobic residues in APRs to charged ones (D, E, K, R).

---

## 10. Detect a signal peptide

Signal peptides direct proteins to be secreted. Try insulin (`P01308`) — has a 24-residue signal peptide.

**API:**
```bash
curl -X POST http://localhost:8765/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"sequence":"MALWMRLLPLLALLALWGPDPAAA..."}' | jq .signal_peptide
```

---

## 11. Predict transmembrane helices

Membrane proteins have 1+ TM helices.

**API:**
```bash
curl -X POST http://localhost:8765/v1/analyze \
  -d '{"sequence":"..."}' | jq .transmembrane
```

Try the COVID spike protein (`spike_covid` or `P0DTC2`) — has 1 TM helix.

---

## 12. Find phosphorylation and glycosylation sites

**API:**
```bash
curl -X POST http://localhost:8765/v1/analyze \
  -d '{"sequence":"..."}' | jq '.phosphorylation, .glycosylation'
```

Returns kinase sites by motif (PKA, PKC, CK2, CDK, GSK3, MAPK) and N/O-glycosylation sites.

---

## 13. Estimate stability change of a mutation

**API:**
```bash
curl -X POST http://localhost:8765/v1/predict_ddg \
  -H "Content-Type: application/json" \
  -d '{"sequence":"MKTVRQERLK","mutation":"K2R"}'
```

Returns ΔΔG in kcal/mol with classification (stabilizing/destabilizing/neutral).

**Tip:** Run this on dozens of candidate mutations to triage which ones to test in the lab.

---

## 14. Align two sequences

Pairwise Needleman-Wunsch alignment with BLOSUM62.

**API:**
```bash
curl -X POST http://localhost:8765/v1/align \
  -H "Content-Type: application/json" \
  -d '{"seq1":"MKTVRQERLK","seq2":"MKTVRAERLK"}'
```

Returns identity %, similarity %, alignment string with `|` for matches and `:` for similar.

---

## 15. Estimate the cost to synthesize a protein

**UI:** Tools → Cost & Carbon Estimate.

**API:**
```bash
curl -X POST http://localhost:8765/v1/cost \
  -H "Content-Type: application/json" \
  -d '{"sequence":"MKTVRQERLK"}'
```

Returns Twist Bioscience, IDT, and GenScript quotes plus the cheapest vendor and CO₂ footprint.

---

## 16. Run a quick MD stability check

**UI:** With a folded structure, click "Quick MD".

**API:**
```bash
curl -X POST http://localhost:8765/v1/md \
  -H "Content-Type: application/json" \
  -d '{"pdb_string":"ATOM...","duration_ps":100}'
```

Returns a job ID. Poll until complete to get RMSD trajectory.

If you `pip install openmm`, it runs real MD. Otherwise it uses a heuristic from pLDDT.

---

## 17. Get an AI explanation of a protein

**UI:** Tools → Explain This Protein (AI).

**API:**
```bash
curl -X POST http://localhost:8765/v1/explain \
  -H "Content-Type: application/json" \
  -d '{"sequence":"MKTVRQERLK","pdb_string":"..."}'
```

If [Ollama](https://ollama.com) is running with `llama3.2:3b`, uses real LLM. Otherwise uses a detailed heuristic.

---

## 18. Save and reload a project

**UI:** Press Ctrl+Shift+S → enter name.

**API:**
```bash
# Save
curl -X POST http://localhost:8765/v1/projects/save \
  -d '{"name":"my_proj","data":{"structures":[...]}}'

# Load
curl -X POST http://localhost:8765/v1/projects/load \
  -d '{"name":"my_proj"}'

# List
curl http://localhost:8765/v1/projects

# Delete
curl -X DELETE http://localhost:8765/v1/projects/my_proj
```

Projects live at `~/.opendna/projects/<name>/workspace.json`.

---

## 19. Use the CLI from the terminal

```bash
# Hardware status
opendna status

# Score a sequence
opendna evaluate MKTVRQERLKSIVRILER

# Initialize a project
opendna init my_research_project

# Fold (downloads model on first run)
opendna fold MKTVRQERLKSIVRILER -o output.pdb
```

---

## 20. Use the API from a Python script

```python
import httpx

API = "http://localhost:8765"

# Score a sequence
r = httpx.post(f"{API}/v1/evaluate", json={"sequence": "MKTVRQERLK"})
print(r.json())

# Submit a fold and poll
fold_resp = httpx.post(f"{API}/v1/fold", json={"sequence": "MKTVRQERLK"})
job_id = fold_resp.json()["job_id"]

import time
while True:
    status = httpx.get(f"{API}/v1/jobs/{job_id}").json()
    if status["status"] == "completed":
        print(f"pLDDT: {status['result']['mean_confidence']}")
        with open("out.pdb", "w") as f:
            f.write(status["result"]["pdb"])
        break
    elif status["status"] == "failed":
        print(f"Failed: {status['error']}")
        break
    time.sleep(2)

# Analyze
analysis = httpx.post(f"{API}/v1/analyze", json={"sequence": "MKTVRQERLK"}).json()
print(f"MW: {analysis['properties']['molecular_weight']}")
print(f"pI: {analysis['properties']['isoelectric_point']}")

# Iterative design
iter_resp = httpx.post(f"{API}/v1/iterative_design", json={
    "sequence": "MKTVRQERLK",
    "n_rounds": 3,
    "candidates_per_round": 5,
})
job_id = iter_resp.json()["job_id"]
# ... poll ...
```
