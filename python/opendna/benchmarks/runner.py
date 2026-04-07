"""Benchmark runner that compares OpenDNA predictions against reference structures.

Reference structures come from RCSB PDB (experimental) or AlphaFold DB
(state-of-the-art predictions). Metrics computed:
- RMSD (Kabsch superposition)
- TM-score-like normalized similarity
- Sequence recovery (for design benchmarks)
- pLDDT vs reference quality
- Inference time
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


# Reference test set: small, well-characterized proteins from PDB.
# (UniProt ID, expected length, name, description)
REFERENCE_PROTEINS = [
    {
        "uniprot_id": "P0CG48",
        "name": "Ubiquitin",
        "description": "76aa, well-folded beta-grasp",
        "expected_length": 76,
    },
    {
        "uniprot_id": "P01308",
        "name": "Insulin",
        "description": "110aa precursor, two chains",
        "expected_length": 110,
    },
    {
        "uniprot_id": "P00698",
        "name": "Lysozyme C",
        "description": "147aa, all-alpha enzyme",
        "expected_length": 147,
    },
    {
        "uniprot_id": "P02185",
        "name": "Myoglobin",
        "description": "154aa, oxygen storage",
        "expected_length": 154,
    },
    {
        "uniprot_id": "P42212",
        "name": "GFP",
        "description": "238aa beta-barrel",
        "expected_length": 238,
    },
]


@dataclass
class BenchmarkResult:
    name: str
    uniprot_id: str
    sequence_length: int
    method: str
    rmsd_vs_reference: float
    tm_score_proxy: float  # Normalized similarity (0-1)
    sequence_recovery: float  # For design benchmarks (1.0 for folding)
    mean_plddt: float
    inference_time_seconds: float
    success: bool
    error: str = ""


@dataclass
class BenchmarkSuiteResult:
    n_total: int
    n_success: int
    mean_rmsd: float
    mean_tm_score: float
    mean_plddt: float
    mean_inference_time: float
    results: list[BenchmarkResult] = field(default_factory=list)
    methodology: str = ""
    opendna_version: str = "0.4.0"
    timestamp: str = ""

    def to_dict(self):
        return {
            "n_total": self.n_total,
            "n_success": self.n_success,
            "success_rate": self.n_success / max(self.n_total, 1),
            "mean_rmsd": round(self.mean_rmsd, 3),
            "mean_tm_score": round(self.mean_tm_score, 3),
            "mean_plddt": round(self.mean_plddt, 3),
            "mean_inference_time_seconds": round(self.mean_inference_time, 1),
            "results": [asdict(r) for r in self.results],
            "methodology": self.methodology,
            "opendna_version": self.opendna_version,
            "timestamp": self.timestamp,
        }


def benchmark_folding(uniprot_id: str, name: str = "") -> BenchmarkResult:
    """Benchmark OpenDNA folding against the AlphaFold DB structure for this entry.

    Steps:
    1. Fetch sequence from UniProt
    2. Fetch reference AlphaFold DB structure (gold standard)
    3. Fold sequence with OpenDNA's ESMFold
    4. Compute RMSD between OpenDNA prediction and AlphaFold reference
    5. Compute TM-score-like similarity
    """
    from opendna.data.sources import fetch_uniprot, fetch_alphafold
    from opendna.engines.folding import fold
    from opendna.engines.analysis import rmsd_kabsch, get_ca_coords
    from opendna.models.protein import Structure

    try:
        entry = fetch_uniprot(uniprot_id)
        if entry is None:
            return BenchmarkResult(
                name=name or uniprot_id,
                uniprot_id=uniprot_id,
                sequence_length=0,
                method="esmfold-vs-alphafold",
                rmsd_vs_reference=0.0,
                tm_score_proxy=0.0,
                sequence_recovery=1.0,
                mean_plddt=0.0,
                inference_time_seconds=0.0,
                success=False,
                error="UniProt entry not found",
            )

        sequence = entry.sequence
        ref_pdb_string = fetch_alphafold(uniprot_id)
        if ref_pdb_string is None:
            return BenchmarkResult(
                name=name or entry.name,
                uniprot_id=uniprot_id,
                sequence_length=len(sequence),
                method="esmfold-vs-alphafold",
                rmsd_vs_reference=0.0,
                tm_score_proxy=0.0,
                sequence_recovery=1.0,
                mean_plddt=0.0,
                inference_time_seconds=0.0,
                success=False,
                error="No AlphaFold reference available",
            )

        # Fold with OpenDNA
        start = time.time()
        result = fold(sequence)
        inference_time = time.time() - start

        # Compute RMSD
        ref_structure = Structure.from_pdb_string(ref_pdb_string)
        pred_structure = Structure.from_pdb_string(result.pdb_string)

        ref_coords = get_ca_coords(ref_structure)
        pred_coords = get_ca_coords(pred_structure)

        n = min(len(ref_coords), len(pred_coords))
        if n == 0:
            raise ValueError("No CA atoms found")

        rmsd = rmsd_kabsch(ref_coords[:n], pred_coords[:n])

        # TM-score proxy: 1 / (1 + (RMSD / d0)^2) where d0 depends on length
        d0 = max(0.5, 1.24 * (n - 15) ** (1 / 3) - 1.8) if n > 15 else 0.5
        tm_proxy = 1.0 / (1.0 + (rmsd / d0) ** 2)

        return BenchmarkResult(
            name=name or entry.name,
            uniprot_id=uniprot_id,
            sequence_length=len(sequence),
            method="esmfold-vs-alphafold",
            rmsd_vs_reference=round(rmsd, 3),
            tm_score_proxy=round(tm_proxy, 3),
            sequence_recovery=1.0,
            mean_plddt=round(result.mean_confidence, 3),
            inference_time_seconds=round(inference_time, 1),
            success=True,
        )
    except Exception as e:
        return BenchmarkResult(
            name=name or uniprot_id,
            uniprot_id=uniprot_id,
            sequence_length=0,
            method="esmfold-vs-alphafold",
            rmsd_vs_reference=0.0,
            tm_score_proxy=0.0,
            sequence_recovery=1.0,
            mean_plddt=0.0,
            inference_time_seconds=0.0,
            success=False,
            error=str(e),
        )


def run_benchmark_suite(
    proteins: Optional[list[dict]] = None,
    output_path: Optional[str] = None,
) -> BenchmarkSuiteResult:
    """Run the full benchmark suite against the reference proteins.

    Returns a BenchmarkSuiteResult with aggregate statistics and per-protein results.
    Optionally writes the result as JSON to output_path.
    """
    from datetime import datetime, timezone

    proteins = proteins or REFERENCE_PROTEINS
    results = []
    for p in proteins:
        print(f"Benchmarking {p['name']} ({p['uniprot_id']})...")
        r = benchmark_folding(p["uniprot_id"], p["name"])
        results.append(r)
        if r.success:
            print(f"  RMSD: {r.rmsd_vs_reference:.2f} Å, TM-proxy: {r.tm_score_proxy:.3f}, time: {r.inference_time_seconds}s")
        else:
            print(f"  FAILED: {r.error}")

    successes = [r for r in results if r.success]
    n_success = len(successes)

    if n_success > 0:
        mean_rmsd = sum(r.rmsd_vs_reference for r in successes) / n_success
        mean_tm = sum(r.tm_score_proxy for r in successes) / n_success
        mean_plddt = sum(r.mean_plddt for r in successes) / n_success
        mean_time = sum(r.inference_time_seconds for r in successes) / n_success
    else:
        mean_rmsd = mean_tm = mean_plddt = mean_time = 0.0

    suite = BenchmarkSuiteResult(
        n_total=len(results),
        n_success=n_success,
        mean_rmsd=mean_rmsd,
        mean_tm_score=mean_tm,
        mean_plddt=mean_plddt,
        mean_inference_time=mean_time,
        results=results,
        methodology=(
            "OpenDNA's ESMFold predictions are compared against AlphaFold DB "
            "structures (the same ones UniProt displays) for the same sequence. "
            "RMSD is computed via Kabsch superposition on Cα atoms. "
            "TM-score proxy uses the standard d0 length-dependent normalization."
        ),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    if output_path:
        Path(output_path).write_text(json.dumps(suite.to_dict(), indent=2))

    return suite


if __name__ == "__main__":
    suite = run_benchmark_suite(output_path="benchmark_results.json")
    print(f"\n=== SUMMARY ===")
    print(f"Success: {suite.n_success}/{suite.n_total}")
    print(f"Mean RMSD: {suite.mean_rmsd:.2f} Å")
    print(f"Mean TM-score-proxy: {suite.mean_tm_score:.3f}")
    print(f"Mean pLDDT: {suite.mean_plddt:.2f}")
