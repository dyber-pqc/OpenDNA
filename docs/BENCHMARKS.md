# OpenDNA Benchmarks

This page describes how OpenDNA is validated against community standards and
how to reproduce the numbers locally.

## About OpenDNA benchmarks

OpenDNA ships a self-contained benchmark suite that compares its folding engine
(ESMFold by default) against strong external baselines — AlphaFold2 and Rosetta
public-server models from the CASP15 experiment.

**Methodology**

1. A curated set of 10 CASP15 monomer targets is hard-coded in
   [`python/opendna/benchmarks/casp.py`](../python/opendna/benchmarks/casp.py).
   The set mixes five "easy" single-domain targets (~80–120 aa) with five
   "hard" free-modelling targets (~180 aa).
2. For each target the reference PDB is fetched lazily from RCSB.
3. OpenDNA folds the target with ESMFold, superposes Cα atoms via Kabsch
   alignment, computes RMSD, and converts to a length-normalised TM-score proxy
   (`1 / (1 + (RMSD/d0)^2)`, d0 following the Zhang & Skolnick definition).
4. Reference TM-scores are curated from the public CASP15 results pages. Every
   entry records a `reference_source` string so reviewers can check provenance.
5. Results are cached at `~/.opendna/benchmarks.json` and are also served by
   the API (see below).

**Data sources**

- Target sequences: CASP15 public target list.
- Reference structures: RCSB PDB (experimental, where available) or AlphaFold
  DB (for UniProt-backed targets).
- Baseline TM-scores: CASP15 server group medians, curated conservatively.

## Latest results

The latest cached results are exposed via:

```
GET /v1/benchmarks/latest
```

Run `python -m opendna.benchmarks.casp` or `POST /v1/benchmarks/casp` to
populate or refresh them.

## Comparison vs AlphaFold2

| Metric               | OpenDNA (ESMFold) | AlphaFold2 / Rosetta (CASP15 median) |
|----------------------|-------------------|--------------------------------------|
| Mean TM-score (easy) | ~0.90             | ~0.92                                |
| Mean TM-score (hard) | ~0.55             | ~0.63                                |
| Mean Cα RMSD         | 1.5 – 5 Å         | 1.0 – 4 Å                            |
| Time-to-solution     | seconds (GPU)     | minutes–hours (with MSA search)      |

OpenDNA is deliberately optimised for **latency**, not peak accuracy: ESMFold
avoids the costly MSA search that dominates AlphaFold2 runtimes and gets within
a few TM-score points on most easy targets at an order of magnitude less
compute.

## How to run locally

From the project root, with the Python environment installed:

```bash
python -m opendna.benchmarks.casp
```

This runs the full 10-target suite, writes a JSON cache to
`~/.opendna/benchmarks.json`, and prints a markdown leaderboard to stdout.

To start the job from the API:

```bash
curl -X POST http://localhost:8000/v1/benchmarks/casp
curl http://localhost:8000/v1/benchmarks/latest
```

## Contributing benchmarks

1. Fork the repository.
2. Add a new entry to `CASP_TARGETS` in
   `python/opendna/benchmarks/casp.py` with `target_id`, `sequence`,
   `reference_pdb_url`, `reference_tm_score`, and a `reference_source` string
   that documents where the reference score came from.
3. Re-run the suite and commit the refreshed `benchmarks.json` if appropriate.
4. Open a pull request describing the new target, its difficulty class, and
   why it is worth tracking.

Community benchmark contributions are peer-reviewed on the PR before merge.
