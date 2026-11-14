# OpenDNA Model Cards

This document lists every model that ships with, or is orchestrated by,
OpenDNA's component registry, along with the information responsible users
need to decide whether a model is fit for their purpose. Model cards follow
the structure proposed by Mitchell et al. (2019).

Cross references:

- [BENCHMARKS.md](BENCHMARKS.md) — quantitative validation against CASP15.
- [SCIENCE.md](SCIENCE.md) — methodology and per-phase scientific rationale.
- [../README.md](../README.md) — project overview.

---

## ESMFold

- **Identifier / version:** `facebook/esmfold_v1` (ESM-2 650M backbone).
- **Intended use:** single-sequence protein structure prediction of natural
  monomers up to ~700 residues without MSA search.
- **Out-of-scope uses:** large complexes, antibody-antigen interfaces,
  membrane proteins with long disordered regions, de novo designed sequences
  far from natural distributions.
- **Training data:** UniRef50 (ESM-2 pretraining) and PDB structures
  pre-2020 for the folding head.
- **Performance:** TM-score ~0.72 on CASP14, within ~0.05 of AlphaFold2 on
  easy targets, with 60x lower wall-clock on GPU.
- **Known limitations / biases:** degrades on low-homology families, does not
  produce side-chain rotamer confidences, single-chain only.
- **Ethical considerations:** general-purpose research tool; outputs should
  not be used as clinical structural evidence without experimental validation.
- **License:** MIT (model weights and code).
- **Citation:** Lin et al. 2022, *Language models of protein sequences at the
  scale of evolution enable accurate structure prediction* (bioRxiv).
- **Size / compute:** ~2.6 GB weights; 16 GB GPU recommended.

## Boltz

- **Identifier / version:** `boltz-community/boltz-1` (v1.0).
- **Intended use:** complex structure prediction (protein-protein,
  protein-ligand, protein-nucleic acid) under an open licence.
- **Out-of-scope uses:** large assemblies (>3 chains, >1500 residues),
  tight affinity prediction, covalent modifications.
- **Training data:** PDB snapshots curated to match AlphaFold3 split.
- **Performance:** matches AlphaFold3 within a few percentage points on
  public PoseBusters benchmarks.
- **Known limitations:** inherits training-set biases toward crystallised
  complexes; struggles on highly flexible loops.
- **Ethical considerations:** does not substitute for wet-lab validation of
  drug candidates.
- **License:** MIT.
- **Citation:** Wohlwend et al. 2024, *Boltz-1: Democratizing Biomolecular
  Interaction Modeling*.
- **Size / compute:** ~4 GB weights; 24 GB GPU recommended.

## ColabFold

- **Identifier / version:** `sokrypton/ColabFold` (MMseqs2 + AlphaFold2
  weights).
- **Intended use:** high-accuracy folding when MSA search is affordable;
  default fallback when ESMFold confidence is low.
- **Out-of-scope uses:** latency-critical loops, deep mutagenesis scans.
- **Training data:** AlphaFold2 weights trained on PDB (pre-2018 cutoff).
- **Performance:** CASP14 median TM ~0.88.
- **Known limitations:** MSA search dominates runtime; remote MMseqs2 server
  adds network dependency.
- **Ethical considerations:** same as AlphaFold2.
- **License:** MIT (ColabFold wrapper); AlphaFold2 parameters under CC BY 4.0
  non-commercial terms.
- **Citation:** Mirdita et al. 2022, *ColabFold: making protein folding
  accessible to all*, Nat. Methods.
- **Size / compute:** ~4 GB weights; 12 GB GPU.

## ESM-IF1 (inverse folding)

- **Identifier / version:** `esm_if1_gvp4_t16_142M_UR50`.
- **Intended use:** sequence design given a backbone structure; recover
  native-like sequences or propose mutations.
- **Out-of-scope uses:** designing function from scratch, ligand-binding site
  engineering without extra constraints.
- **Training data:** UniRef50 + predicted PDB structures.
- **Performance:** ~51 % sequence recovery on native backbones.
- **Known limitations:** discards non-protein context, no side-chain modelling.
- **Ethical considerations:** designs are not reviewed for dual-use; a
  biosecurity screen should gate synthesis requests.
- **License:** MIT.
- **Citation:** Hsu et al. 2022, *Learning inverse folding from millions of
  predicted structures*, ICML.
- **Size / compute:** ~550 MB; runs on CPU at modest speed.

## ESM-2

- **Identifier / version:** `facebook/esm2_t33_650M_UR50D`.
- **Intended use:** general protein embeddings, zero-shot variant effect
  prediction, feature extraction for downstream models.
- **Out-of-scope uses:** replacing supervised models on well-specified tasks
  without fine-tuning.
- **Training data:** UniRef50.
- **Performance:** SOTA zero-shot variant effect on ProteinGym (2022).
- **Known limitations / biases:** inherits taxonomic bias of UniRef50.
- **Ethical considerations:** standard dual-use caveats apply to
  variant-effect scores near pathogens of concern.
- **License:** MIT.
- **Citation:** Lin et al. 2022 (as above).
- **Size / compute:** 2.6 GB; 8 GB GPU.

## RFdiffusion

- **Identifier / version:** `RosettaCommons/RFdiffusion` v1.
- **Intended use:** protein backbone generation for motif scaffolding, binder
  design, and symmetric assemblies.
- **Out-of-scope uses:** sequence generation (use ProteinMPNN or ESM-IF1),
  nucleic-acid design, small molecules.
- **Training data:** PDB monomers and complexes, with synthetic augmentation.
- **Performance:** ~20 % experimental success for de novo binders in the
  original paper.
- **Known limitations:** outputs require downstream sequence design and
  filtering; compute-heavy diffusion steps.
- **Ethical considerations:** outputs must be screened for biosecurity risk
  before physical synthesis.
- **License:** BSD-3-Clause (code), CC BY-NC 4.0 (weights).
- **Citation:** Watson et al. 2023, *De novo design of protein structure and
  function with RFdiffusion*, Nature.
- **Size / compute:** 3 GB weights; 16 GB GPU.

## DiffDock

- **Identifier / version:** `gcorso/DiffDock` v1.1.
- **Intended use:** blind protein-ligand docking pose prediction.
- **Out-of-scope uses:** affinity ranking across unrelated targets, covalent
  ligands, metal coordination.
- **Training data:** PDBBind.
- **Performance:** 38 % top-1 < 2 Å on PDBBind test, better than classical
  docking but worse than AlphaFold3 on hard cases.
- **Known limitations:** sensitive to receptor conformation; no explicit
  water modelling.
- **Ethical considerations:** not for clinical decision making.
- **License:** MIT.
- **Citation:** Corso et al. 2023, *DiffDock: Diffusion Steps, Twists, and
  Turns for Molecular Docking*, ICLR.
- **Size / compute:** ~1 GB; 8 GB GPU.

## OpenMM

- **Identifier / version:** OpenMM 8.x.
- **Intended use:** molecular dynamics, energy minimisation, free-energy
  calculations using classical force fields (Amber ff14SB, CHARMM36, etc.).
- **Out-of-scope uses:** reactive chemistry, electronic structure.
- **Training data:** N/A (physics-based).
- **Performance:** GPU-accelerated, 10–100 ns/day on a modern consumer GPU
  for small systems.
- **Known limitations:** force-field accuracy, not a machine-learned model.
- **Ethical considerations:** standard research tool.
- **License:** MIT / LGPL (mixed modules).
- **Citation:** Eastman et al. 2017, *OpenMM 7: Rapid development of high
  performance algorithms for molecular dynamics*, PLOS Comp Biol.
- **Size / compute:** ~200 MB; CPU or GPU.

## xTB

- **Identifier / version:** `grimme-lab/xtb` 6.6.
- **Intended use:** semi-empirical quantum chemistry for small molecules and
  metal complexes (GFN2-xTB).
- **Out-of-scope uses:** transition metals outside the parametrised set,
  large biomolecules.
- **Training data:** DFT reference data used for parameter fitting.
- **Performance:** reasonable geometries within seconds; energies within
  ~2 kcal/mol for main-group organics.
- **Known limitations:** parametric; accuracy drops away from fit set.
- **Ethical considerations:** standard research tool.
- **License:** LGPL-3.0.
- **Citation:** Bannwarth, Ehlert, Grimme 2019, *GFN2-xTB*, JCTC.
- **Size / compute:** ~60 MB; CPU only.

## ANI-2x

- **Identifier / version:** `roitberg/ANI-2x` (TorchANI release).
- **Intended use:** fast machine-learned potentials for organic molecules
  containing H, C, N, O, F, Cl, S.
- **Out-of-scope uses:** elements outside the training set, transition
  states requiring very high accuracy.
- **Training data:** COMP6 + extensions, DFT ωB97X/6-31G*.
- **Performance:** near-DFT geometry and energies on drug-like molecules.
- **Known limitations:** no long-range dispersion unless augmented.
- **Ethical considerations:** standard research tool.
- **License:** MIT.
- **Citation:** Devereux et al. 2020, *Extending the applicability of the
  ANI deep-learning molecular potential to sulfur and halogens*, JCTC.
- **Size / compute:** ~30 MB; runs on CPU or GPU.

## Ollama (local LLM gateway)

- **Identifier / version:** Ollama runtime v0.1+, user-selected model
  (default: `llama3:8b-instruct`).
- **Intended use:** natural-language assistant inside OpenDNA for explaining
  structures, suggesting workflows, and summarising runs.
- **Out-of-scope uses:** clinical advice, autonomous experiment execution,
  safety-critical decisions.
- **Training data:** varies by selected model (Llama 3 is trained on a
  public text corpus up to early 2023).
- **Performance:** depends on model; 8B models run at 20+ tok/s on a 16 GB
  GPU.
- **Known limitations:** hallucinations, stale knowledge, no grounding to
  OpenDNA's live state unless via tool calls.
- **Ethical considerations:** outputs are advisory only; flagged with a
  "not medical advice" disclaimer in the UI.
- **License:** Ollama MIT; individual model weights carry their own licences
  (e.g. Llama 3 community licence).
- **Citation:** refer to the selected model's release notes.
- **Size / compute:** 4–30 GB depending on model; ideally a GPU with
  bf16 support.

---

_Last updated with the v0.5.0 release. See `CHANGELOG.md` for history._
