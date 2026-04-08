# OpenDNA FAQ

Common questions and answers.

## v0.5.0 questions

### Do I have to install ESMFold / DiffDock / RFdiffusion / Boltz myself?

No. Open the **Component Manager** (Altium/Vivado-style catalog in the desktop app, or `GET /v1/components`). You get 11 ML engines with one-click install, live progress streaming, and uninstall. Models download on demand and are cached under `~/.opendna/models/`.

### Can I use OpenDNA completely offline?

Yes. Run `opendna compliance airgap-check` to audit which engines are already cached and which need network. An **air-gap bundle** builds a portable mirror of every model, wheel, and npm package so you can sneakernet the whole stack onto a disconnected machine.

### Is OpenDNA quantum-safe?

Yes. Auth tokens use **ML-KEM-768** (Kyber) for key exchange and **ML-DSA-65** (Dilithium) for signatures, via liboqs. The audit log is hash-chained and every entry is ML-DSA-signed. Install with `pip install "opendna[pqc]"` and set `OPENDNA_PQC=1`.

### Where are my workspaces stored?

`~/.opendna/workspaces/<user>/`. Each workspace is encrypted at rest with **AES-256-GCM** using a scrypt-derived key from your password. Nothing leaves the machine unless you explicitly export.

### How do I recover a crashed job?

You don't have to — the priority job queue is **persisted to SQLite** and reloads on restart. Interactive / normal / batch tiers all survive a hard kill. Check `/v1/jobs` after restart; the self-healer also retries transient failures automatically via the `@retry` decorator.

### How do multiple users share a project in real time?

OpenDNA ships a **Yjs CRDT relay** (y-websocket compatible). Join a room at `ws://host:8765/v1/crdt/{room}` and every sequence edit, residue comment, and workflow-editor node change syncs live. List active rooms with `GET /v1/crdt`.

### Can I export all my data for a GDPR request?

Yes. `POST /v1/compliance/export_user_data` returns a signed ZIP of every workspace, audit log row, and provenance entry for a given user. `POST /v1/compliance/erase_user` performs a verified erasure and returns the audit-log proof.

### Does the desktop app need Python installed?

No. The desktop installer bundles a **PyInstaller sidecar** so the Tauri shell launches the Python API on localhost:8765 automatically — no `pip`, no PATH setup, no interpreters. Verified working on Windows, macOS universal, and Linux.

### How do I run a visual workflow?

Open the **Workflow Editor** (React Flow canvas), drag nodes from the palette (fold, design, dock, md, analyze, fetch, export, branch, merge, notify), wire them up, and click **Run**. Every step is recorded into the provenance DAG automatically, and you can save the canvas as a template.

### What is the provenance DAG?

Every fold, design, analysis, mutation, and parameter is recorded as a node in a directed acyclic graph. You can `diff_steps(a, b)` to compare two runs, `blame_residue(n)` to see every change that touched residue *n*, and `bisect_regression(metric)` to auto-find the step that tanked a score. This is the "time machine" behind the Academy and lab-notebook views.

### Can I mint a DOI for my dataset?

Yes. `POST /v1/zenodo/mint` uploads your project bundle to Zenodo and returns a citable DOI. Set `ZENODO_ACCESS_TOKEN` first (the default is a draft deposit).

### How do I enable HTTPS / authentication?

Set `OPENDNA_AUTH_REQUIRED=1` before starting the server. The API will then require a PQC-signed token on every endpoint and will refuse unauthenticated requests. Combine with a reverse proxy (Caddy, nginx) for TLS termination, or use the `--ssl-certfile` / `--ssl-keyfile` flags on uvicorn.

### Does it run on Apple Silicon?

Yes. PyTorch's **MPS backend** is detected automatically by the hardware abstraction layer and used for ESMFold, ESM-IF1, DiffDock, and RFdiffusion. The desktop app ships a universal macOS build.

### How big is the installer?

The Tauri bundle + PyInstaller sidecar is **~150 MB**. Models are downloaded on first use (ESMFold ~8 GB, ESM-IF1 ~600 MB, DiffDock ~2 GB, RFdiffusion ~4 GB, Boltz ~3 GB) and cached forever. The Component Manager shows disk usage live.

### Which LLM does the agent use?

Ollama with **`llama3.2:3b`** by default. OpenDNA auto-installs Ollama on first use (Phase 15) and streams chat with multi-turn session memory. Swap the model with `OPENDNA_LLM_MODEL=llama3.2:7b` or any Ollama-compatible tag.

---


## General

### What is OpenDNA?

OpenDNA is a free, open-source protein engineering platform that combines structure prediction, sequence design, property analysis, and visualization in a single integrated app. It's designed to replace ~80% of what you'd use Schrödinger or commercial tools for, but free and running on a laptop.

### Who is it for?

- **Curious learners** who want to explore protein science
- **Students** in biochemistry, bioengineering, structural biology
- **Citizen scientists** who want to contribute to research
- **Underfunded labs** that can't afford $200k/year commercial software
- **Indie biotech founders** prototyping ideas
- **Anyone** who thinks tools shouldn't be locked behind paywalls

### Is it free?

Yes. Apache 2.0 + Commons Clause for the core (free for non-commercial; contact for commercial licensing). MIT for community modules. CC-BY-4.0 for documentation.

### How accurate is it compared to AlphaFold or Schrödinger?

ESMFold (used by OpenDNA) is generally 5-10% less accurate than full AlphaFold2 with MSA, but ~60x faster. For most workflows, ESMFold is good enough. For publication-quality structures of novel folds, you may want to verify with AlphaFold2 + MSA.

The other analyses (Lipinski, hydropathy, etc.) are mathematically equivalent to commercial software since they're based on published formulas.

### Can I use it for real research?

Yes, but understand the limitations:
- ESMFold can hallucinate confident-looking structures for novel sequences
- ML-based predictions are best when supported by experimental data
- Don't make medical decisions based on OpenDNA output
- Always verify critical results with established tools and wet-lab experiments

---

## Installation & Setup

### What are the system requirements?

**Minimum:** 8 GB RAM, any modern CPU, 20 GB free disk, Python 3.10+
**Recommended:** 16 GB RAM, NVIDIA GPU with 8+ GB VRAM or Apple Silicon, 50 GB disk
**Optimal:** 32 GB RAM, RTX 4090 or A6000, 200 GB disk

### Why does ESMFold need 8 GB?

The model itself is ~3 GB. During inference, intermediate activations need additional RAM proportional to sequence length squared. For a 200-residue protein, peak memory is ~6-8 GB.

### Can I run it on a laptop without a GPU?

Yes. CPU folding works but is much slower:
- 30 residues: ~1 minute
- 100 residues: ~5-10 minutes
- 200 residues: ~30 minutes
- 500 residues: don't try this on CPU, you'll run out of RAM

Sequence-only analyses (score, analyze, mutate) are instant on any CPU.

### Why are model downloads so big?

ESMFold is 8 GB, ESM-IF1 is 600 MB. These are large transformer models trained on millions of protein sequences. The download is one-time — they're cached forever in `~/.cache/huggingface/`.

### Can I use a different folding model?

Currently OpenDNA only supports ESMFold. Adding RoseTTAFold, OpenFold, AlphaFold2, or Boltz support is on the v0.3 roadmap.

### Does it work offline?

After the initial model download, yes. The only network calls are:
- ML model downloads (one-time)
- UniProt/PDB import (only when you use them)
- Ollama (only if you have it installed for explanations)

---

## Usage

### Why are my fold results all blue?

Two things:
1. The pLDDT colors show confidence. Blue = high confidence. If your protein is mostly blue, ESMFold is confident across the whole structure. That's a good sign.
2. The "uncertainty" theme uses B-factor inverse coloring. The new pLDDT theme in v0.2.1+ shows proper AlphaFold-style colors (blue-cyan-yellow-orange for very-high to very-low confidence).

### Why can't I fold p53?

p53 is 393 residues. On CPU, that would take ~30 minutes and 12+ GB RAM. You can:
- Get a GPU
- Fold a smaller fragment (e.g. just the DNA-binding domain, residues 94-312)
- Wait it out
- Use OpenDNA on a workstation

### My designed sequences have very low recovery (5-10%). Is that bad?

Not necessarily. ESM-IF1 with default temperature (0.1) generates fairly diverse alternatives. Low recovery means the model found very different sequences that should still fold into the same shape. This is actually valuable for engineering — you want options!

To get more conservative redesigns, lower the temperature to 0.01.

### What does "Iterative design" actually do?

It runs this loop:
1. Fold your sequence
2. Generate N candidate alternatives via ESM-IF1
3. Score each candidate
4. If any beat the current best, fold it to confirm and keep it
5. Repeat for N rounds

The goal is automated optimization toward higher quality scores while maintaining the same fold.

### Why does my score say "Note: this score is sequence-only"?

The /v1/evaluate endpoint computes scores from sequence properties only. It doesn't use structure data even if you have a fold. To get a structure-aware score, look at the pLDDT confidence and the Full Analysis Suite — those use the structure.

This is a known limitation in v0.2 and will be improved in v0.3.

### Why does the chat panel sometimes give weird responses?

The chat panel uses Ollama (`llama3.2:3b`) if installed, otherwise a regex-based fallback parser. The fallback understands common commands like "fold X" and "score X" but isn't a real LLM. Install Ollama for better natural language understanding.

---

## Errors & Issues

### "ERROR: bind on address ('0.0.0.0', 8000): permission denied"

Port 8000 is reserved on many Windows installs. Use 8765 instead:
```bash
python -c "from opendna.api.server import start_server; start_server(port=8765)"
```

### "Torch not compiled with CUDA enabled"

You have an NVIDIA GPU but installed CPU-only PyTorch. Either:
- Install CUDA torch: `pip install torch --index-url https://download.pytorch.org/whl/cu124`
- Or accept CPU mode (it works, just slower)

For Python 3.14 specifically, CUDA torch wheels may not yet exist. Check the PyTorch wheel index.

### "Cannot fetch http://localhost:8765"

The API server isn't running, or it's running on a different port. Check Terminal 1 output. Look for "Uvicorn running on http://0.0.0.0:8765".

### Folding hangs forever

Check the API terminal:
- If you see "Loading weights" repeating: model is being loaded (normal)
- If you see no output: it might be stuck in inference. Check Task Manager for high CPU usage on python.exe
- If RAM is filling up: you've run out of memory. Use a smaller protein or get more RAM

### Can't import via UniProt

Check your internet connection. Sometimes UniProt's REST API is slow. Try again in a minute.

If it's a famous protein, use the famous name (e.g. "ubiquitin") instead of accession.

### UI is blank

Open browser DevTools (F12) → Console tab. Look for red errors. Common causes:
- API server not running
- Port mismatch (UI expects 8765, server on different port)
- CORS error (very rare on localhost)

---

## Privacy & Security

### Does OpenDNA send my data anywhere?

No telemetry. No analytics. The only network calls:
- Downloading ML models from HuggingFace (one time)
- Fetching from UniProt/PDB only when YOU click Import
- Calling Ollama (localhost only)
- Calling our API (localhost only)

Your sequences, structures, and projects stay on your machine.

### Is the API secure?

The API listens on `localhost` by default (only accessible from your own machine). There's no authentication in v0.2 — adding auth is in the v0.3 roadmap.

**Do not expose the API to the internet without adding authentication.** A malicious user could waste your compute, fill your disk, or extract any sequences you've worked with.

### Are my saved projects encrypted?

No. Project files in `~/.opendna/projects/` are plain JSON. If you have sensitive sequences, encrypt the directory yourself or use a tool like VeraCrypt.

---

## Comparison with Other Tools

### vs Schrödinger Maestro

| Feature | Schrödinger | OpenDNA |
|---|---|---|
| Cost | ~$200k/year | Free |
| 3D viewer | Yes (proprietary) | Yes (Molstar, open) |
| Folding | Prime (paid module) | ESMFold built-in |
| Sequence design | Prime | ESM-IF1 built-in |
| QikProp properties | Yes | Yes (built-in) |
| Glide docking | Yes | Heuristic only |
| Desmond MD | Yes ($$$$) | OpenMM (optional) |
| Free | No | Yes |
| Source code | Closed | Open (Apache 2.0) |
| Runs on laptop | Workstation needed | Yes |

### vs PyMOL

PyMOL is just a viewer. OpenDNA does folding, design, analysis, and includes a viewer. They complement each other — you can save PDBs from OpenDNA and load them in PyMOL for figure-quality rendering.

### vs ChimeraX

Same as PyMOL — ChimeraX is a viewer. OpenDNA is a full workbench.

### vs ColabFold

ColabFold is a Google Colab notebook for folding with AlphaFold2. It's free but:
- Requires uploading your sequence to Google's servers
- Limited compute time (~12 hours)
- Just folding, no design/analysis/UI

OpenDNA runs locally, has design + analysis + UI, but uses ESMFold (less accurate than AF2 with MSA).

### vs Rosetta

Rosetta is the gold standard for academic protein design. It's free for academia but very complex (C++ codebase, command-line driven, steep learning curve). OpenDNA is faster to learn but less powerful at the cutting edge.

---

## Future Plans

### When will multimer folding work?

v0.3. Currently ESMFold doesn't natively support multimers. We'll integrate AlphaFold-Multimer or Boltz.

### Will there be a desktop app installer?

Yes, planned for v0.3 (Tauri-based). For now you need to clone and run from source.

### Will there be cloud sync?

Optional, planned for v0.4. Privacy-preserving design (you opt-in, your data is encrypted client-side).

### Mobile app?

Companion app planned for v0.4. View jobs, AR protein view, push notifications.

### Will you accept contributions?

Yes! See [DEVELOPER.md](DEVELOPER.md). PRs welcome for engines, UI improvements, docs, tests.

### Can I sponsor development?

Reach out via GitHub. Sponsorship goes to compute, models, hosting, and developer time.

---

## Philosophy

### Why is this free?

Because protein engineering is too important to be locked behind paywalls. The next pandemic vaccine, the next cancer drug, the next sustainable enzyme — these shouldn't depend on whether your lab can afford $200k/year software.

### What's your business model?

There isn't one (yet). The core is and will remain free under Apache 2.0 + Commons Clause. We may eventually offer:
- Hosted compute for users without GPUs
- Premium support for commercial users
- Custom models or features

But the core platform stays free, forever.

### Will this kill commercial software?

Probably not. Schrödinger has decades of polish, validation, and specialized features we won't match for years. But we don't need to match all of it to be useful — we need to be 80% as good for 100% of people.

### What can I do to help?

- **Use it** and report bugs
- **Star the repo** to signal interest
- **Share it** with someone who can't afford commercial software
- **Contribute code** if you're a developer
- **Write tutorials** if you're a teacher
- **Test on real problems** if you're a scientist
- **Spread the word** if you believe in democratizing science
