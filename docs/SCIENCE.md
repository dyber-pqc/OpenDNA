# The Science Behind OpenDNA

This document explains what each algorithm in OpenDNA actually does, the science behind it, and what the results mean.

## Table of Contents
1. [Protein Folding (ESMFold)](#1-protein-folding-esmfold)
2. [Inverse Folding (ESM-IF1)](#2-inverse-folding-esm-if1)
3. [Sequence Properties](#3-sequence-properties)
4. [Lipinski's Rule of Five](#4-lipinskis-rule-of-five)
5. [Hydropathy Analysis](#5-hydropathy-analysis)
6. [Intrinsic Disorder](#6-intrinsic-disorder)
7. [Secondary Structure](#7-secondary-structure)
8. [Ramachandran Plot](#8-ramachandran-plot)
9. [Transmembrane Prediction](#9-transmembrane-prediction)
10. [Signal Peptide Detection](#10-signal-peptide-detection)
11. [Aggregation Prediction](#11-aggregation-prediction)
12. [Post-Translational Modifications](#12-post-translational-modifications)
13. [Mutation Effects (ΔΔG)](#13-mutation-effects-ddg)
14. [Bond Detection](#14-bond-detection)
15. [Iterative Design](#15-iterative-design)

---

## 1. Protein Folding (ESMFold)

**What it does:** Takes an amino acid sequence and predicts the 3D coordinates of every atom in the protein.

**The model:** ESMFold v1 by Meta AI (Lin et al., 2022). A transformer-based language model trained on 65 million protein sequences. Unlike AlphaFold2, ESMFold doesn't need a multiple sequence alignment — it works on a single sequence directly, which makes it ~60x faster.

**How it works (in 3 sentences):**
1. The sequence is fed through ESM-2, a protein language model that learns evolutionary patterns from raw sequences.
2. The internal embeddings capture which residues are likely to be near each other in 3D.
3. A folding head decodes those embeddings into atomic coordinates.

**Output:**
- 3D coordinates in PDB format
- **pLDDT confidence score** (per-residue, 0-100): how sure the model is about each position
  - 90+: very high confidence
  - 70-90: confident
  - 50-70: low confidence (often disordered)
  - <50: very low confidence (random)

**Limitations:**
- Less accurate than full AlphaFold2 with MSA, especially for novel folds
- Hard time with multimers (use AlphaFold-Multimer instead)
- Can hallucinate confident-looking structures for sequences with no evolutionary history

**Why it matters:** This used to require a HPC cluster and weeks of compute. Now it runs on a gaming laptop in minutes.

---

## 2. Inverse Folding (ESM-IF1)

**What it does:** Takes a 3D backbone structure and generates amino acid sequences that should fold into that shape.

**The model:** ESM-IF1 by Meta AI (Hsu et al., 2022). A geometric vector perceptron transformer trained on 12 million predicted structures.

**How it works:**
1. Read the backbone N, Cα, C, O atom coordinates
2. The encoder builds a representation of the 3D environment around each residue
3. The decoder samples a new amino acid for each position, conditioned on the geometry
4. Higher temperature = more diverse sequences (less native-like)

**Output:**
- Multiple alternative sequences
- **Recovery** percentage: how many residues match the original sequence
  - High recovery (50%+) = conservative redesign
  - Low recovery (10-30%) = aggressive redesign of the same fold
- A score (lower is better — derived from negative log-likelihood)

**Use cases:**
- **Stabilize a protein** without changing its function
- **Diversify a binder** to find better variants
- **Remove problematic regions** (e.g. aggregation-prone, immunogenic)
- **Make a protein easier to manufacture**

**The trick of "design then verify":** Generated sequences should fold into the original backbone. To verify, fold them with ESMFold and compare. This is exactly what OpenDNA's iterative design loop does.

---

## 3. Sequence Properties

**Molecular Weight (MW):** Sum of amino acid masses minus water for each peptide bond. Reported in Daltons. A 100 aa protein is ~11,000 Da (≈11 kDa).

**Isoelectric Point (pI):** The pH at which the protein has zero net charge. Calculated by bisection on the net charge equation, summing contributions from each ionizable group:
```
charge(pH) = Σ positive groups (1 / (1 + 10^(pH - pKa)))
           - Σ negative groups (1 / (1 + 10^(pKa - pH)))
```
- pI < 5: very acidic (likely DNA-binding or calcium-binding)
- pI 5-7: typical cytoplasmic
- pI 7-9: typical secreted
- pI > 9: very basic (histones, ribosomal proteins)

**GRAVY (Grand Average of Hydropathy):** Average Kyte-Doolittle hydropathy across the sequence.
- GRAVY > 0: hydrophobic (membrane proteins, oils)
- GRAVY < 0: hydrophilic (soluble, cytoplasmic)

**Aromaticity:** Fraction of F+W+Y residues. Affects UV absorbance and folding.

**Instability Index (Guruprasad et al. 1990):** Sum of dipeptide instability values.
- Score < 40: stable in vivo
- Score > 40: unstable, may degrade quickly

**Aliphatic Index (Ikai 1980):** Volume occupied by aliphatic side chains (A, V, I, L). Higher = more thermostable.

**N-terminal Half-life:** Predicted half-life in mammalian cells based on the N-terminal amino acid (the "N-end rule" - Bachmair et al. 1986). Methionine and valine give long half-lives; arginine, lysine, glutamate give short ones.

**Extinction Coefficient (Pace et al.):** Predicts UV absorbance at 280 nm:
```
ε(280nm) = (Trp × 5500) + (Tyr × 1490) + (Cys/2 × 125)
```
Used to determine protein concentration spectrophotometrically.

---

## 4. Lipinski's Rule of Five

**What it is:** A quick drug-likeness check developed by Christopher Lipinski at Pfizer in 1997 for predicting oral bioavailability of small molecules.

**The rules:**
1. Molecular weight ≤ 500 Da
2. Hydrogen bond donors ≤ 5
3. Hydrogen bond acceptors ≤ 10
4. LogP (lipophilicity) ≤ 5

A drug should violate **at most one** rule to be likely orally available.

**Why we apply it to peptides:** Most peptides will fail RO5 (they're too big), but the analysis still gives useful info on whether a small peptide could be a drug.

**Caveats:**
- Originally designed for small molecules, not proteins
- Doesn't predict everything (membrane permeability, toxicity, etc.)
- Many useful drugs violate it (Lipinski himself estimates 40% of drugs fail)

---

## 5. Hydropathy Analysis

**Algorithm:** Kyte-Doolittle (1982). Each amino acid has a hydropathy value:

| Most hydrophobic | Most hydrophilic |
|---|---|
| I (+4.5), V (+4.2), L (+3.8) | R (-4.5), K (-3.9), D/N/Q/E (-3.5) |
| F (+2.8), C (+2.5), M (+1.9) | H (-3.2), Y (-1.3), P (-1.6) |

**Output:** A sliding window average across the sequence (window=9 by default).

**What to look for:**
- **Peaks above +1.6 over ~19 residues** = transmembrane helices
- **Long stretches above 0** = hydrophobic domains (membrane interaction, oily core)
- **Long stretches below 0** = hydrophilic surface or disordered regions
- **Sharp transitions** = signal peptides, hinge regions

---

## 6. Intrinsic Disorder

**What it is:** Many proteins (or regions of proteins) don't fold into a fixed structure. They remain flexible and dynamic in solution. These "intrinsically disordered proteins/regions" (IDPs/IDRs) account for 30-50% of the human proteome.

**Why it matters:**
- Disordered regions are common in transcription factors, signaling proteins, and scaffolds
- Drug targets often have disordered regions that are hard to crystallize
- p53 (the famous tumor suppressor) is mostly disordered
- Disorder is biologically functional, not just noise

**Algorithm:** IUPred-like sliding window on a per-residue propensity scale (Linding et al. 2003 simplified).

**Output:**
- Per-residue probability (0-1)
- Identified disordered regions (≥5 consecutive residues with score ≥0.5)
- Overall disorder percentage

**Try this:** Fetch p53 (`P04637`), run analysis. You'll see ~70% disorder.

---

## 7. Secondary Structure

**What it is:** Beyond the linear amino acid sequence, the local 3D shape forms recurring patterns:
- **α-helix (H):** Right-handed coil, 3.6 residues per turn, stabilized by H-bonds
- **β-strand (E):** Extended chain, often paired with other strands to form sheets
- **Coil (C):** Everything else (loops, turns, disordered)

**Algorithm:** OpenDNA uses a simplified DSSP-like assignment based on phi/psi dihedral angles:
- Helix region: -160 < φ < -40 AND -70 < ψ < -10
- Strand region: -180 < φ < -40 AND 90 < ψ < 180
- Otherwise: coil

**Output:** Per-residue assignment string like `HHHHCCCEEECC...` and percentages.

**Real DSSP (Kabsch & Sander 1983)** uses backbone hydrogen bond patterns and is more accurate. OpenDNA's version is fast and good enough for visualization.

---

## 8. Ramachandran Plot

**What it is:** A scatter plot of phi (φ) vs psi (ψ) backbone dihedral angles for every residue. Named after G.N. Ramachandran (1963).

**Why it's useful:**
- Most residues cluster in two regions: alpha-helical (-60, -45) and beta-sheet (-120, +120)
- Outliers indicate strain, errors, or unusual conformations (often glycine or proline)
- A "good" structure has >90% of residues in favored regions

**How OpenDNA computes it:**
- For each residue, compute φ from the previous C-N-CA-C atoms
- Compute ψ from the current N-CA-C-N atoms
- Plot all pairs

**Visual interpretation:**
- **Top-left cluster** (~-60, -45) = right-handed α-helix
- **Top-right cluster** (~-120, +120) = β-sheet
- **Bottom-left** = left-handed α-helix (rare, mostly glycines)
- **Sparse points everywhere** = bad structure or many disordered residues

---

## 9. Transmembrane Prediction

**What it is:** Identifies regions that span a lipid membrane. Membrane proteins have hydrophobic helices long enough to cross the bilayer (~20 Å, typically 17-25 amino acids).

**Algorithm:** Sliding-window hydropathy. A region of ≥17 consecutive residues with average hydropathy >1.4 is flagged as a transmembrane (TM) helix.

**Output:**
- Per-residue scores
- TM region boundaries
- Total helix count
- "Is membrane protein" flag

**Real TMHMM (Krogh et al.)** uses a hidden Markov model that's more accurate for distinguishing TM helices from signal peptides and predicting topology (which side is in/out). Our version is the simple version.

**Test it:** Try the COVID spike protein (`spike_covid` or `P0DTC2`) — it has 1 TM helix.

---

## 10. Signal Peptide Detection

**What they are:** Short N-terminal sequences (15-30 aa) that direct proteins to be secreted from the cell. Cleaved off by signal peptidase during translocation.

**Structure of a signal peptide:**
- **n-region** (positively charged, 1-5 aa)
- **h-region** (hydrophobic core, 7-15 aa)
- **c-region** (polar, 3-7 aa, ends with cleavage motif)

**Algorithm (heuristic):** Score the first 30 residues for these three regions. If all three look right, predict a signal peptide and find the cleavage site (usually after a small residue like A, G, S, C, T at position -1, with another small residue at position -3).

**Real SignalP** uses neural networks trained on thousands of validated signal peptides. Our heuristic catches the obvious cases.

**Use case:** Knowing if your designed protein will be secreted vs cytoplasmic.

---

## 11. Aggregation Prediction

**What it is:** Many designed proteins form insoluble aggregates instead of folding properly. This is one of the biggest problems in protein engineering.

**Algorithm:** TANGO/Aggrescan-like. Each residue has an aggregation propensity:
- **High (aggregating):** I, F, V, L, Y, W
- **Low (gatekeeper):** P, K, R, D, E (charged residues block aggregation)

A region of ≥5 residues with average propensity >1.0 is flagged as an "aggregation-prone region" (APR).

**Output:**
- Per-residue scores
- Identified APRs with sequences
- Overall aggregation score
- Risk level (low / medium / high)

**Real TANGO and Aggrescan** are slightly different approaches but the principle is the same. Our version is good enough for screening.

**Engineering tip:** If your protein has high aggregation risk, mutate hydrophobic residues in the APR to charged residues (D, E, K, R) — they act as "gatekeepers."

---

## 12. Post-Translational Modifications

### Phosphorylation

Adding a phosphate group to S, T, or Y residues. Regulates ~30% of all proteins.

**OpenDNA detects:** Sequence motifs matching consensus sites for major kinases:
- **PKA** (Protein Kinase A): R-R/K-X-S/T
- **PKC** (Protein Kinase C): S/T-X-R/K
- **CK2** (Casein Kinase 2): S/T-X-X-D/E
- **CDK** (Cyclin-Dependent Kinase): S/T-P-X-K/R
- **GSK3** (Glycogen Synthase Kinase 3): S/T-X-X-X-S/T
- **MAPK**: P-X-S/T-P

**Real prediction:** NetPhos uses ML models. Motif-based gives many false positives but catches the obvious ones.

### Glycosylation

Adding sugar chains to specific residues. Very common in secreted and membrane proteins.

- **N-linked:** N-X-S/T sequon (X is any residue except proline). Most common.
- **O-linked:** S/T residues, often in mucin-like (Pro/Ser/Thr-rich) regions.

**Why it matters:** Glycosylation affects folding, stability, immunogenicity, and half-life. Missing or wrong glycosylation can ruin a therapeutic.

---

## 13. Mutation Effects (ΔΔG)

**What it is:** Predict whether a mutation will stabilize or destabilize the protein.

**Convention:**
- ΔΔG = ΔG(mutant) - ΔG(wild-type), in kcal/mol
- **Negative** ΔΔG = destabilizing (mutation makes protein less stable)
- **Positive** ΔΔG = stabilizing
- **|ΔΔG| < 0.5**: probably neutral
- **|ΔΔG| > 1.5**: significant change

**OpenDNA's algorithm:** A heuristic based on:
1. Per-residue stability propensity differences
2. Penalty for radical changes (e.g. hydrophobic → charged)
3. Penalty for changes in special residues (P, G, C)

**Real prediction:** FoldX, Rosetta Cartesian_ddG, or trained ML models like ProTSTaB. These do explicit physics or learn from thermal melting datasets.

**Use case:** Quick screen of which mutations to try in the lab.

---

## 14. Bond Detection

OpenDNA scans the structure for:

### Hydrogen Bonds
N-H...O or O-H...N pairs within 2.5-3.5 Å between non-adjacent residues. Stabilize secondary structure.

### Salt Bridges
Charged side chain pairs within 4 Å:
- **Positive:** Lys (NZ), Arg (NH1, NH2, NE), His (ND1, NE2)
- **Negative:** Asp (OD1, OD2), Glu (OE1, OE2)

Salt bridges are strong electrostatic interactions, especially valuable for thermostability.

### Disulfide Bonds
Cys SG-SG pairs within 3 Å. Covalent bonds that staple two cysteines together. Very common in secreted proteins (their extra stability helps survive outside the cell). Insulin has 3 disulfides.

---

## 15. Iterative Design

The killer feature. Combines folding + design in a loop.

**Algorithm:**
1. Fold the input sequence with ESMFold → get backbone + score
2. For N rounds:
   a. Use ESM-IF1 to generate K candidate sequences for the current backbone
   b. Score each candidate (sequence-based scoring is fast)
   c. Find the highest-scoring candidate
   d. If it's better than current best, fold it with ESMFold to confirm
   e. Update current best if confirmed
3. Return the optimized protein

**Why it works:** Each round explores the local sequence space around a stable backbone. Over multiple rounds, it climbs toward higher-scoring proteins while maintaining the structural fold.

**Comparable commercial features:**
- **Schrödinger BioLuminate** Mutation/Stability calculations + Manual loop
- **Rosetta** Cartesian_ddG + scripts
- **Schrödinger IFD-MD** Induced Fit Docking + MD refinement loop

**Cost in commercial software:** $50,000-$200,000/year per seat.
**Cost in OpenDNA:** $0. Runs on your laptop.

---

## References

- **ESMFold:** Lin, Z. et al. (2023). "Evolutionary-scale prediction of atomic-level protein structure." *Science* 379, 1123-1130.
- **ESM-IF1:** Hsu, C. et al. (2022). "Learning inverse folding from millions of predicted structures." *ICML*.
- **Kyte-Doolittle:** Kyte, J. & Doolittle, R.F. (1982). *J. Mol. Biol.* 157, 105-132.
- **DSSP:** Kabsch, W. & Sander, C. (1983). *Biopolymers* 22, 2577-2637.
- **Ramachandran:** Ramachandran, G.N. et al. (1963). *J. Mol. Biol.* 7, 95-99.
- **TMHMM:** Krogh, A. et al. (2001). *J. Mol. Biol.* 305, 567-580.
- **SignalP:** Almagro Armenteros, J.J. et al. (2019). *Nat. Biotechnol.* 37, 420-423.
- **TANGO:** Fernandez-Escamilla, A.M. et al. (2004). *Nat. Biotechnol.* 22, 1302-1306.
- **IUPred:** Dosztányi, Z. et al. (2005). *J. Mol. Biol.* 347, 827-839.
- **Lipinski:** Lipinski, C.A. et al. (1997). *Adv. Drug Deliv. Rev.* 23, 3-25.
- **Instability Index:** Guruprasad, K. et al. (1990). *Protein Eng.* 4, 155-161.
- **N-end rule:** Bachmair, A. et al. (1986). *Science* 234, 179-186.
