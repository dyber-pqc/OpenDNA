# OpenDNA

A desktop application for protein engineering. It runs locally, in Rust, with
no server and no network service.

This documentation set is deliberately thin. OpenDNA is mid-rewrite from a
Python service with a React front end to a single Rust application, and most
of what used to be here described the Python REST API, its deployment, and its
analysis engines — all of which have been removed. Pages that documented them
have been deleted rather than left to describe software that no longer exists.

The accurate documentation lives next to the code it describes:

| | |
|---|---|
| [Project overview and model accuracy](https://github.com/dyber-pqc/OpenDNA/blob/main/README.md) | what works, what does not, and how the heads score on external benchmarks |
| [Development guide](https://github.com/dyber-pqc/OpenDNA/blob/main/DEVELOPMENT.md) | workspace layout, builds, GPU setup, the ground rules |
| [Datasets](https://github.com/dyber-pqc/OpenDNA/blob/main/datasets/README.md) | sources, licences, construction, reproducibility |
| [Training](https://github.com/dyber-pqc/OpenDNA/blob/main/training/README.md) | embedding caches, training the heads, external benchmarks |
| [Models](https://github.com/dyber-pqc/OpenDNA/blob/main/models/README.md) | the trained heads, their cards, and publishing |

Each trained head carries its own model card stating its baseline, its
measured metrics, and its limitations.

## What it does not do

Earlier documentation advertised structure prediction, docking, molecular
dynamics, sequence design, antibody modelling, and an HTTP API. None of those
exists in the Rust application. They are listed here because a reader who
remembers the old pages deserves a straight answer rather than silence.
