# OpenDNA

Protein property prediction that runs on your own machine. No server, no
account, no network: sequences stay where you opened them.

Three trained models score candidate sequences for per-residue disorder,
solubility, and the stability effect of a point mutation. Each is a small head
on frozen [ESM-2](https://huggingface.co/facebook/esm2_t30_150M_UR50D)
embeddings. When a model is missing the answer is an error saying so — there
is no heuristic fallback anywhere, and no number in the interface comes from
anything but a trained model.

## Who this is for

**If you have candidate sequences you cannot upload, and you want to triage
them before committing bench time**, this is built for you. Of the commercial
protein-design platforms, essentially all are cloud-only; the reason to use
OpenDNA is usually not that it predicts better but that it predicts at all
inside an environment where sending unpublished constructs to a vendor is not
allowed.

Concretely, it is useful today if you are:

- **Working on intrinsic disorder.** The disorder head is competitive with the
  CAID3 field (below), runs over a whole proteome from one command, and costs
  nothing.
- **Screening constructs under IP or data-governance constraints.** Nothing
  leaves the machine, so there is no review to pass.
- **Somewhere that has to show its work.** Every prediction carries the model
  version, the embedding model, and the limitations from that model's card;
  every dataset file is checksummed; the published models and this repository
  provably describe the same build.

It is **not** yet useful if you need structure prediction, docking, sequence
design, antibody-specific models, a signed installer, or a support contract.
Those are either absent or unfinished, and the section below says which.

## Quick start

Predictions need the trained heads, which are not bundled:

```bash
hf download dyber-pqc/opendna-disorder --local-dir models
export OPENDNA_MODELS=$PWD/models
```

Then score a whole FASTA file:

```bash
cargo run --release -p opendna-cli -- predict --task disorder \
    --input candidates.fasta --output disorder.csv
```

`--task` takes `disorder`, `solubility` or `stability`; `--format` takes
`csv`, `tsv`, `json`, or `caid` for a CAID submission. See
[crates/opendna-cli](crates/opendna-cli) for the command, and
[CAID.md](crates/opendna-cli/CAID.md) for the assessment format.

The desktop application is the same models with a structure viewer; see
[Build](#build).

## How good the models are

Two kinds of number, and the distinction matters more than the values.
**In-domain** is our own held-out test split: how a head does on data drawn
the way its training data was drawn. **External** is a reference set that
other published methods also report on, which is the only kind that says where
a head stands relative to the field.

| Head | In-domain test | External |
|---|---|---|
| **Disorder** | AUROC 0.883 | **AUROC 0.941** on CAID3 Disorder-PDB |
| Stability (ΔΔG) | Spearman 0.674 | Spearman 0.442 over 4 ProteinGym assays |
| Solubility | Spearman 0.701 | none exists under usable terms |

**Disorder is the strong one.** Published CAID3 Disorder-PDB figures include
AIUPred v3 at 0.925 and MUSE-IDR at 0.954, so 0.941 sits inside that field.
Two caveats, both ours: this is a reimplementation of the CAID protocol
against their published reference file, not an official CAID entry; and 34 of
the 319 targets exceed ESM-2's length limit and were covered by overlapping
windows, which no published entrant does. The number was independently
recomputed in numpy at 0.9409 by `scripts/validate_caid.py`, so it is not an
artefact of one implementation.

It scores *higher* externally than in-domain, which is not an improvement but
a different target: our split labels unannotated residues ordered, because
DisProt records only demonstrated disorder, so the negative class contains
disordered residues nobody has shown yet. CAID masks what it did not assess.

**Stability is a ranking signal, not a measurement.** It falls from 0.674 to
0.442 out of domain because it trains on single domains of 32–74 residues and
the external assays are whole proteins of 164–403. The in-domain figure
overstates generalisation by roughly 0.23 Spearman. All four assays correlate
positively, so the ordering is right; treat an individual ΔΔG as weak.

**Solubility has no external number** because the benchmarks for it come from
sources whose terms forbid redistribution, or from services that have been
retired. Saying so beats quoting the in-domain figure as though it were
comparable.

Both suites are reproducible with `opendna-train bench`; the reports and the
reasoning are in [training/benchmarks](training/benchmarks). A bigger
embedding model was tried and rejected: ESM-2 650M made the disorder head
*worse* on every external metric, for 2.61 GB of weights against 0.60 GB.

## What it does not do

Earlier versions of this README advertised all of these. None exists:

- structure prediction (no ESMFold, no AlphaFold)
- docking, molecular dynamics, or free-energy calculation
- sequence or backbone design
- antibody-specific modelling
- any HTTP API, hosted service, or notebook integration

## Datasets

Built by [datasets/](datasets) from pinned upstream sources, every file
checksummed, with a licence review recorded per source — including the sources
**excluded** because their terms forbid redistribution.

| Dataset | Rows | Source |
|---|---:|---|
| stability | 389,068 | Tsuboyama et al. 2023 |
| solubility | 3,127 | eSOL, UniProtKB |
| disorder | 3,186 | DisProt 2025_12 |
| structures | 106,910 | CATH v4.4.0, wwPDB |

Splits are by 30% sequence-identity cluster, so no close homolog spans two
splits. Validation chooses the epoch; the test split is scored once,
afterwards; external benchmarks are never tuned against at all. The published
datasets and heads are listed in [models/README.md](models/README.md).

## Build

Rust 1.95 or newer. `unsafe` is forbidden across the workspace.

```bash
cargo test --workspace
cargo run --release -p opendna-cli -- models
```

The desktop application is a separate workspace:

```bash
cd app
rustup target add wasm32-unknown-unknown
cargo install trunk
cargo run -p xtask -- fetch-molstar
cd ui && trunk build --release && cd ..
cargo run -p opendna-desktop
```

GPU builds need a `cuda` feature and a toolkit candle supports; on Windows use
`scripts/cargo-cuda.ps1`, which loads nvcc and MSVC and documents the version
bounds and the PowerShell argument traps.

## Layout

| Directory | Workspace | Contents |
|---|---|---|
| [crates/](crates) | root | core types, I/O, analysis, storage, ESM-2, the heads, the CLI |
| [app/](app) | `app` | Tauri desktop shell, Leptos UI, IPC protocol |
| [datasets/](datasets) | `datasets` | the dataset builder |
| [training/](training) | `training` | embedding cache, training, model cards, benchmarks |
| [models/](models) | — | trained heads and their cards; weights are not committed |

Each workspace is built, linted with `clippy -D warnings`, and tested in CI.
[DEVELOPMENT.md](DEVELOPMENT.md) has the ground rules a change is held to.

## Licence

The code is [Apache-2.0](LICENSE), which is what the `LICENSE` file and every
crate's metadata say. An earlier README claimed "Apache 2.0 + Commons Clause",
a different and more restrictive grant that appears nowhere in the repository;
it was removed rather than acted on.

**Model weights are not all under the same licence, because their training
data is not.** The stability and disorder heads are Apache-2.0: their sources
are CC BY, which asks for attribution and sets no condition on derived work.
The solubility head is **CC BY-SA 2.1 JP**, following eSOL — whether weights
are a derivative work of their training data is unsettled, and a share-alike
condition is not something to assume away in our own favour. If you are
embedding OpenDNA commercially, that distinction is the one to take to
counsel. Each model card states its own licence and the reasoning.
