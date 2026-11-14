---
license: apache-2.0
library_name: opendna
tags:
  - protein
  - biology
  - protein-language-model
datasets:
  - opendna-solubility
base_model: facebook/esm2_t30_150M_UR50D
---

# OpenDNA solubility head

Predicts protein solubility from sequence.

This is a small head trained on **frozen** [facebook/esm2_t30_150M_UR50D](https://huggingface.co/facebook/esm2_t30_150M_UR50D) embeddings. It is not a fine-tuned language model: the embedding model is unchanged, and only the head below was trained.

## Inputs and outputs

**Input.** The mean-pooled ESM-2 embedding of the sequence.

**Output.** A solubility percentage on the source assay's scale. Values above 100 occur in the source data and are not clipped.

## Results

| Metric | Validation | Test | Baseline (test) |
|---|---|---|---|
| MAE | 18.313 | 18.823 | 28.416 |
| Pearson r | 0.740 | 0.691 | — |
| RMSE | 23.015 | 23.388 | 32.256 |
| Spearman ρ | 0.737 | 0.701 | — |

A — in the baseline column means the metric is undefined for that baseline, not unmeasured: a baseline that predicts the same value for every input has no correlation with the truth.

Baseline: Predicting the training-set mean for every protein.

Validation chose the epoch that was kept (epoch 35 of 45 run). The test split was evaluated once, afterwards. Splits come from the dataset builder, which clusters by sequence identity so near-identical proteins cannot appear on both sides.

## Training

| | |
|---|---|
| Embedding model | `facebook/esm2_t30_150M_UR50D` (640 dimensions, frozen) |
| Optimiser | AdamW, learning rate 0.001 |
| Batch size | 256 |
| Seed | 20260101 |
| Dataset | [`opendna-solubility`](https://github.com/dyber-pqc/OpenDNA/tree/main/datasets) |
| Data licence | see the dataset card; sources differ |

Reproduce by building the dataset first — see [`datasets/README.md`](https://github.com/dyber-pqc/OpenDNA/tree/main/datasets) — and then, from `training/`:

```bash
cargo run --release -p opendna-train -- embed --task solubility
cargo run --release -p opendna-train -- train --task solubility \
    --batch-size 256 --learning-rate 0.001 --seed 20260101
```

The hyperparameters are spelled out above even where they match the current defaults, so the command reproduces *this* run rather than whatever the defaults happen to be later.

Both commands take `--datasets <dir>` if the dataset is not at the default `../datasets/out`. Embedding is cached, so the second run of either command is cheap.

## Limitations

- Trained on E. coli cell-free expression measurements. Solubility in other hosts, or under different expression conditions, is a different quantity.
- Sequences are UniProtKB canonical sequences, not the exact expressed constructs; tags and truncations in the real experiments are not represented.
- A few thousand proteins is a small training set. Treat the output as a ranking signal for prioritising constructs, not as a predicted assay value.

## Intended use

Ranking and triage during protein engineering: comparing candidate mutations or constructs against each other. It is not a substitute for measurement, and it should not be used to make claims about a specific protein without experimental confirmation.

## Citation

The training data comes from:

> Niwa, T. et al. Bimodal protein solubility distribution revealed by an aggregation analysis of the entire ensemble of Escherichia coli proteins. PNAS 106, 4201-4206 (2009).

Please cite that work as well as this model.
