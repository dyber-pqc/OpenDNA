# OpenDNA

**The People's Protein Engineering Platform**

OpenDNA democratizes protein engineering for everyone -- from curious high schoolers to professional researchers. It runs on a gaming laptop and speaks plain English.

## Quick Start

```bash
# Install
pip install opendna

# Download models
opendna models download

# Fold a protein
opendna fold MKTVRQERLKSIVRILERSKEPVSGAQLAEELS...

# Design binders
opendna design --target my_protein.pdb

# Launch the desktop app
opendna ui
```

## Features

- Protein structure prediction (ESMFold)
- Protein sequence design (ProteinMPNN)
- Runs on consumer hardware (RTX 3060+, Apple Silicon, CPU fallback)
- Plain English interface
- Version control for proteins
- Desktop app with 3D visualization

## Development

```bash
# Rust core
cargo build
cargo test

# Python
uv sync
uv run pytest
uv run opendna --help

# Desktop UI
cd ui && npm install && npm run tauri dev
```

## License

Apache 2.0 + Commons Clause (core) / MIT (community modules)
