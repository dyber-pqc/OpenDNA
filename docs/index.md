# OpenDNA

Protein property prediction that runs on your own machine. No server, no
account, no network: sequences stay where you opened them.

Four trained models score candidate sequences for per-residue disorder,
per-residue solvent accessibility, solubility, and the stability effect of a
point mutation, from a command line or a desktop application. The disorder head is competitive with the CAID3
field — AUROC 0.941 on Disorder-PDB, against published figures of 0.925 for
AIUPred v3 and 0.954 for MUSE-IDR.

The reason to use it is usually not that it predicts better, but that it
predicts at all somewhere that sending unpublished sequences to a vendor is
not allowed.

If you have to sign off on using this for real work, start with
[Validation](VALIDATION.md): what has been checked, how, and what has not.

This documentation set is deliberately thin. OpenDNA was rewritten from a
Python service with a React front end into Rust, and most of what used to be
here described the Python REST API, its deployment and its analysis engines —
all of which have been removed. Pages that documented them have been deleted
rather than left to describe software that no longer exists.

[The changelog](CHANGELOG.md) lists what the rewrite removed, and
[the roadmap](ROADMAP.md) what is unfinished.

The accurate documentation lives next to the code it describes:

| | |
|---|---|
| [Project overview and model accuracy](https://github.com/dyber-pqc/OpenDNA/blob/main/README.md) | what works, what does not, and how the heads score on external benchmarks |
| [Development guide](https://github.com/dyber-pqc/OpenDNA/blob/main/DEVELOPMENT.md) | workspace layout, builds, GPU setup, the ground rules |
| [Datasets](https://github.com/dyber-pqc/OpenDNA/blob/main/datasets/README.md) | sources, licences, construction, reproducibility |
| [Training](https://github.com/dyber-pqc/OpenDNA/blob/main/training/README.md) | embedding caches, training the heads, external benchmarks |
| [Models](https://github.com/dyber-pqc/OpenDNA/blob/main/models/README.md) | the trained heads, their cards, and publishing |
| [Command line](https://github.com/dyber-pqc/OpenDNA/blob/main/crates/opendna-cli/README.md) | batch predictions over a FASTA file |
| [CAID submissions](https://github.com/dyber-pqc/OpenDNA/blob/main/crates/opendna-cli/CAID.md) | the assessment format, and the two ways it fails silently |
| [Pipelines](https://github.com/dyber-pqc/OpenDNA/blob/main/pipelines/README.md) | running parts in parallel under Nextflow or Snakemake |
| [Signing](SIGNING.md) | what is signed, what is not, and what each signature buys |
| [Python bindings](https://github.com/dyber-pqc/OpenDNA/blob/main/bindings/python/README.md) | calling the heads from a notebook, with the run manifest attached |

Each trained head carries its own model card stating its baseline, its
measured metrics, and its limitations.

## What it does not do

Earlier documentation advertised structure prediction, docking, molecular
dynamics, sequence design, antibody modelling, and an HTTP API. The rewrite
shipped with none of them, and OpenDNA still computes no structure and no
trajectory itself.

Two have since come back, each in the only form that is honest.

`opendna fold` drives an ESMFold or ColabFold that you installed, checks that
the chain it returns is the sequence it was sent, and records which engine
produced each file. With no engine installed it refuses.

`opendna humanness` reports, for each overlapping 9-residue window of an
antibody heavy chain, the fraction of human donors whose repertoire contains
that exact peptide. It is a count over a table of 150 donors, not a model:
there is no accuracy figure because nothing is predicted. The trained
antibody head that was planned instead was dropped on measurement — a lookup
table on the V gene call separates human from mouse at 98.5% against a 68.9%
baseline, so a head's accuracy would have restated the germline catalogue.

Docking and molecular dynamics are declared to the same engine adapter and not
yet driven; sequence design and the HTTP API are not built, and antibody work
beyond humanness — light chains, paired chains, developability — is not either.
[The roadmap](ROADMAP.md) says what is next and in what order.

The rest is listed here because a reader who remembers the old pages deserves a
straight answer rather than silence.
