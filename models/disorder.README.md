---
license: apache-2.0
library_name: opendna
tags:
  - protein
  - biology
  - protein-language-model
datasets:
  - dyber-pqc/opendna-disorder
base_model: facebook/esm2_t30_150M_UR50D
---

# OpenDNA disorder head

Predicts, for each residue, whether it lies in an intrinsically disordered region.

This is a small head trained on **frozen** [facebook/esm2_t30_150M_UR50D](https://huggingface.co/facebook/esm2_t30_150M_UR50D) embeddings. It is not a fine-tuned language model: the embedding model is unchanged, and only the head below was trained.

## Inputs and outputs

**Input.** Per-residue ESM-2 embeddings. Sequences longer than the embedding model's limit are covered by overlapping windows.

**Output.** One probability per residue. The reported threshold is 0.5.

## Results

| Metric | Validation | Test | Baseline (test) |
|---|---|---|---|
| AUPRC | 0.540 | 0.611 | 0.179 |
| AUROC | 0.840 | 0.883 | 0.500 |
| Balanced accuracy | 0.772 | 0.812 | 0.500 |
| F1 | 0.535 | 0.573 | 0.304 |
| MCC | 0.434 | 0.493 | — |

A — in the baseline column means the metric is undefined for that baseline, not unmeasured: a baseline that predicts the same value for every input has no correlation with the truth.

Baseline: Labelling every residue disordered.

Validation chose the epoch that was kept (epoch 5 of 15 run). The test split was evaluated once, afterwards. Splits come from the dataset builder, which clusters by sequence identity so near-identical proteins cannot appear on both sides.

## Training

| | |
|---|---|
| Embedding model | `facebook/esm2_t30_150M_UR50D` (640 dimensions, frozen) |
| Optimiser | AdamW, learning rate 0.001 |
| Batch size | 256 |
| Seed | 20260101 |
| Dataset | [`dyber-pqc/opendna-disorder`](https://huggingface.co/datasets/dyber-pqc/opendna-disorder) |
| Data licence | CC BY 4.0 (DisProt 2025_12); the CAID3 reference set used only to hold proteins out is CC BY 3.0 |

### Licence of these weights

Both sources ask for attribution and place no condition on the licence of derived work, so the weights are Apache-2.0. Cite the dataset.

### Reproducing this run

Download the dataset from [`dyber-pqc/opendna-disorder`](https://huggingface.co/datasets/dyber-pqc/opendna-disorder) into `datasets/out/disorder/`, or rebuild it from its upstream sources with the `datasets/` workspace of the [OpenDNA repository](https://github.com/dyber-pqc/OpenDNA) — the dataset card lists every source file with its SHA-256. Then, from `training/`:

```bash
cargo run --release -p opendna-train -- embed --task disorder
cargo run --release -p opendna-train -- train --task disorder \
    --batch-size 256 --learning-rate 0.001 --seed 20260101
```

The hyperparameters are spelled out above even where they match the current defaults, so the command reproduces *this* run rather than whatever the defaults happen to be later.

Both commands take `--datasets <dir>` if the dataset is not at the default `../datasets/out`. Embedding is cached, so the second run of either command is cheap.

## Limitations

- DisProt records disorder that has been experimentally demonstrated. Residues that are simply unannotated are treated as ordered during training, so the negative class contains an unknown number of undiscovered disordered residues.
- Annotation is biased toward proteins people chose to study, and toward longer disordered regions. Short linkers are under-represented.
- CAID test-set proteins are held out of training here, but numbers below are on this dataset's own test split and are not comparable to published CAID results without running the CAID protocol.
- The metrics are pooled over residues, but residues within one protein are strongly correlated — neighbouring positions almost always share a label. The effective sample size is therefore closer to the few hundred proteins in each split than to the hundred thousand or more residues the counts show, so small differences between splits should not be read as real. On this run the test split scored higher than validation on every metric, which is what that noise looks like rather than evidence the model generalises unusually well.

## Intended use

Ranking and triage during protein engineering: comparing candidate mutations or constructs against each other. It is not a substitute for measurement, and it should not be used to make claims about a specific protein without experimental confirmation.

## Citation

The training data comes from:

> Aspromonte, M. C. et al. DisProt in 2024: improving function annotation of intrinsically disordered proteins. Nucleic Acids Research 52, D434-D441 (2024).

Please cite that work as well as this model.
