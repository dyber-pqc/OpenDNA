# OpenDNA

A desktop application for protein engineering. It runs locally, in Rust, with
no server and no network service: sequences stay on the machine they were
opened on.

Three trained models predict mutation effects on folding stability, protein
solubility, and per-residue disorder. Each is a small head on frozen
[ESM-2](https://huggingface.co/facebook/esm2_t30_150M_UR50D) embeddings. When
a model is missing the application says the prediction is unavailable; there
is no heuristic fallback anywhere, and no number shown in the interface comes
from anything but a trained model.

## Status

The project is being rewritten from a Python service with a React front end to
a single Rust application. That rewrite is the current state of the repository:
the Python backend and React UI have been removed, along with the REST API and
the deployment and workflow integrations that targeted it.

What works today:

| | |
|---|---|
| Structure and sequence I/O | PDB, mmCIF, FASTA |
| Structure analysis | geometry, contacts, secondary structure, SASA |
| Embeddings | ESM-2 (8M–650M) in [candle](https://github.com/huggingface/candle), CPU, CUDA or Metal |
| Predictions | ΔΔG of substitution, solubility, per-residue disorder |
| Desktop application | Tauri 2 shell, Leptos UI, Mol\* structure viewer |
| Dataset pipeline | four datasets built from pinned upstream sources |

What it does **not** do. Earlier versions of this README advertised these; none
of them exists in the Rust application:

- structure prediction (no ESMFold, no AlphaFold)
- docking, molecular dynamics, or free-energy calculation
- sequence or backbone design
- antibody-specific modelling
- any HTTP API, hosted service, or notebook integration

## Predictions, and how good they are

Two kinds of number. **In-domain** is our own held-out test split: how the head
does on data drawn the way its training data was drawn. **External** is a
reference set that other published methods also report on, which is the only
kind of number that says where the head stands relative to the field.

| Head | In-domain test | External |
|---|---|---|
| Stability (ΔΔG) | Spearman 0.674 | Spearman 0.442 mean over 4 ProteinGym assays |
| Solubility | Spearman 0.701 | none — see below |
| Disorder | AUROC 0.883 | AUROC 0.941 on CAID3 Disorder-PDB |

The two columns disagree in both directions, and the reasons matter more than
the numbers:

- **Stability falls from 0.674 to 0.442.** The head is trained on single
  domains of 32–74 residues. The external assays are whole proteins of 164–403
  residues measuring variant abundance and thermostability. The in-domain
  figure overstates how well this generalises by roughly 0.23 Spearman, and
  the external one is the honest estimate for a protein you care about. All
  four assays correlate positively, so the ordering is right even where the
  strength is modest.
- **Disorder rises from 0.883 to 0.941.** Not an improvement: a different
  target. Our split uses DisProt labels, where any unannotated residue counts
  as ordered, so the negative class contains disordered residues nobody has
  demonstrated yet. CAID masks the residues it did not assess and scores only
  the rest. For context, published CAID3 Disorder-PDB figures include AIUPred
  v3 at 0.925 and MUSE-IDR at 0.954. This is our reimplementation of the
  protocol against the published reference file, not an official CAID3 entry.
- **Solubility has no external number.** The benchmarks that exist for it come
  from sources whose terms do not permit redistribution, or from services that
  have been retired. Saying so is more useful than quoting the in-domain
  figure as though it were comparable.

Reproduce either with `opendna-train bench`; see [training/](training). The
benchmark data is never redistributed or built into a dataset — some of it
carries no licence at all, which permits evaluation but not republication.

## Datasets and models

Built by [datasets/](datasets) from pinned upstream sources, every file
checksummed, with a licence review recorded per source — including the sources
that were **excluded** because their terms forbid redistribution.

| Dataset | Rows | Source |
|---|---:|---|
| stability | 389,068 | Tsuboyama et al. 2023 |
| solubility | 3,127 | eSOL, UniProtKB |
| disorder | 3,186 | DisProt 2025_12 |
| structures | 106,910 | CATH v4.4.0, wwPDB |

Splits are by 30% sequence-identity cluster, so no close homolog spans two
splits. Validation chooses the epoch; the test split is scored once,
afterwards. The published datasets and heads are listed in
[models/README.md](models/README.md).

## Build

Rust 1.95 or newer. `unsafe` is forbidden across the workspace.

```bash
cargo test --workspace
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

Predictions need the trained heads. Download them into a directory and point
`OPENDNA_MODELS` at it:

```bash
hf download dyber-pqc/opendna-stability --local-dir models
```

GPU builds need a `cuda` feature and a toolkit candle supports; on Windows use
`scripts/cargo-cuda.ps1`, which loads nvcc and MSVC and explains the version
bounds.

## Layout

| Directory | Workspace | Contents |
|---|---|---|
| [crates/](crates) | root | core types, I/O, analysis, storage, ESM-2 and the heads |
| [app/](app) | `app` | Tauri desktop shell, Leptos UI, IPC protocol |
| [datasets/](datasets) | `datasets` | the dataset builder |
| [training/](training) | `training` | embedding cache, training, model cards, benchmarks |
| [models/](models) | — | trained heads and their cards; weights are not committed |

Each workspace is built, linted with `clippy -D warnings`, and tested in CI.

## License

[Apache-2.0](LICENSE), which is what the `LICENSE` file and every crate's
metadata say. An earlier README claimed "Apache 2.0 + Commons Clause", a
different and more restrictive grant that appears nowhere in the repository;
that claim has been removed rather than acted on.

Datasets and model weights carry the licences their training data requires,
which are not all the same — the solubility head is share-alike because eSOL
is. Each card states its own.
