"""Self-benchmarking framework for OpenDNA.

Run benchmarks against reference structures and compute standard metrics
(TM-score, RMSD, GDT-TS, lDDT) to validate the platform.
"""

from opendna.benchmarks.runner import (
    BenchmarkResult,
    benchmark_folding,
    run_benchmark_suite,
    REFERENCE_PROTEINS,
)

__all__ = [
    "BenchmarkResult",
    "benchmark_folding",
    "run_benchmark_suite",
    "REFERENCE_PROTEINS",
]
