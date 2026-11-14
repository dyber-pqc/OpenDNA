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
from opendna.benchmarks.casp import (
    CASP_TARGETS,
    run_casp_benchmark,
    generate_leaderboard_md,
    load_cached_results as load_cached_casp_results,
)

__all__ = [
    "BenchmarkResult",
    "benchmark_folding",
    "run_benchmark_suite",
    "REFERENCE_PROTEINS",
    "CASP_TARGETS",
    "run_casp_benchmark",
    "generate_leaderboard_md",
    "load_cached_casp_results",
]
