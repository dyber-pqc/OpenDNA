---
license: apache-2.0
library_name: opendna
tags:
  - protein
  - biology
  - protein-language-model
datasets:
  - opendna-stability
base_model: facebook/esm2_t30_150M_UR50D
---

# OpenDNA stability head

Predicts the change in folding free energy (ΔΔG) caused by a single amino-acid substitution.

This is a small head trained on **frozen** [facebook/esm2_t30_150M_UR50D](https://huggingface.co/facebook/esm2_t30_150M_UR50D) embeddings. It is not a fine-tuned language model: the embedding model is unchanged, and only the head below was trained.

## Inputs and outputs

**Input.** The wild-type sequence's ESM-2 embedding at the mutated position, one-hot encodings of the wild-type and mutant residues, and the masked log-odds `log P(mutant) - log P(wild type)` at that position.

**Output.** A single ΔΔG value in kcal/mol, following the dataset's sign convention: negative is destabilising.

## Results

| Metric | Validation | Test | Baseline (test) |
|---|---|---|---|
| MAE | 0.605 | 0.532 | — |
| Pearson r | 0.678 | 0.717 | 0.497 |
| RMSE | 0.802 | 0.699 | — |
| Spearman ρ | 0.674 | 0.674 | 0.445 |

Baseline: The language model's masked log-odds used directly, with no trained head.

Validation chose the epoch that was kept (epoch 1 of 11 run). The test split was evaluated once, afterwards. Splits come from the dataset builder, which clusters by sequence identity so near-identical proteins cannot appear on both sides.

## Training

| | |
|---|---|
| Embedding model | `facebook/esm2_t30_150M_UR50D` (640 dimensions, frozen) |
| Optimiser | AdamW, learning rate 0.001 |
| Batch size | 512 |
| Seed | 20260101 |
| Dataset | [`opendna-stability`](https://github.com/dyber-pqc/OpenDNA/tree/main/datasets) |
| Data licence | CC BY 4.0 (Tsuboyama et al. 2023, FireProtDB) |

Reproduce with:

```bash
cargo run --release -p opendna-train -- embed --task stability
cargo run --release -p opendna-train -- train --task stability
```

## Limitations

- Trained almost entirely on small, single-domain proteins of 32-72 residues. Behaviour on large multi-domain proteins, membrane proteins and complexes is untested.
- The source assay infers ΔΔG from protease resistance over a range of roughly -1 to 5 kcal/mol for ΔG. Mutations outside that range are absent from training, so strongly destabilising substitutions are under-represented.
- Only single substitutions. The model says nothing about combined mutations, insertions or deletions.
- Trained on frozen embeddings, so accuracy is bounded by what ESM-2 already encodes about the position.
- Trained with a squared-error loss, so predictions are compressed toward the training mean and span a much narrower range than the measurements do. The rank order is the usable signal, which is why Spearman is the headline metric; treat an individual predicted value as a weak estimate.

## Intended use

Ranking and triage during protein engineering: comparing candidate mutations or constructs against each other. It is not a substitute for measurement, and it should not be used to make claims about a specific protein without experimental confirmation.

## Citation

The training data comes from:

> Tsuboyama, K. et al. Mega-scale experimental analysis of protein folding stability in biology and design. Nature 620, 434-444 (2023).

Please cite that work as well as this model.
