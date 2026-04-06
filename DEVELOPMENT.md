# OpenDNA Development Guide

## Project Structure
- `crates/` - Rust core (data models, HAL, Python bindings via PyO3)
- `python/opendna/` - Python ML layer (engines, CLI, API)
- `ui/` - Tauri v2 + React desktop app
- `models/` - ML model weights (not committed, downloaded via CLI)
- `tests/` - Test suites for Rust and Python

## Build Commands
- Rust: `cargo build`, `cargo test`
- Python: `uv sync`, `uv run pytest`, `uv run opendna --help`
- UI: `cd ui && npm install && npm run tauri dev`

## Conventions
- Rust: standard rustfmt, clippy clean
- Python: ruff for linting/formatting, type hints everywhere
- TypeScript: strict mode, ESLint + Prettier
- All public APIs need docstrings
- Error handling: Result types in Rust, exceptions in Python with clear messages
- User-facing text should be plain English, no jargon without explanation

## Architecture Principles
- Offline-first: everything works without internet
- Progressive enhancement: basic on CPU, fast on GPU
- Explain by default: no black boxes
- Fail gracefully: never crash, always recover
- Privacy respecting: user data stays local
