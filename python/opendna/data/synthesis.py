"""Cost, carbon, and synthesis ordering estimates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostEstimate:
    sequence_length: int
    twist_bioscience_usd: float
    idt_usd: float
    genscript_usd: float
    cheapest_vendor: str
    cheapest_price: float
    notes: str


@dataclass
class CarbonEstimate:
    job_type: str
    duration_seconds: float
    backend: str  # "cpu" | "cuda" | "metal"
    energy_kwh: float
    co2_kg: float
    equivalent: str


def estimate_synthesis_cost(sequence: str) -> CostEstimate:
    """Estimate cost to chemically synthesize the gene + protein for this sequence.

    Uses 2024 average prices per amino acid for major vendors. Real prices vary
    by complexity, batch size, and vendor specials.
    """
    n = len(sequence)
    bp = n * 3  # codons

    # Very rough averages (USD per bp)
    twist = bp * 0.07 + 50  # Twist clonal genes
    idt = bp * 0.18 + 65  # IDT gBlocks
    genscript = bp * 0.15 + 99  # GenScript clonal

    prices = {"Twist Bioscience": twist, "IDT": idt, "GenScript": genscript}
    cheapest = min(prices, key=prices.get)

    return CostEstimate(
        sequence_length=n,
        twist_bioscience_usd=round(twist, 2),
        idt_usd=round(idt, 2),
        genscript_usd=round(genscript, 2),
        cheapest_vendor=cheapest,
        cheapest_price=round(prices[cheapest], 2),
        notes=(
            "Estimates based on 2024 average per-base-pair pricing. "
            "Actual quotes vary by sequence complexity, length, and vendor promotions."
        ),
    )


def estimate_carbon(
    job_type: str,
    duration_seconds: float,
    backend: str = "cpu",
) -> CarbonEstimate:
    """Estimate carbon footprint of a computation."""
    # Power draw estimates (watts)
    power_w = {
        "cpu": 65,    # Average modern CPU under load
        "cuda": 250,  # Mid-range GPU
        "metal": 30,  # Apple Silicon (efficient)
    }.get(backend, 65)

    energy_kwh = (power_w * duration_seconds) / 3_600_000
    # Average grid carbon intensity: 0.4 kg CO2 / kWh (US average)
    co2_kg = energy_kwh * 0.4

    # Equivalent
    if co2_kg < 0.001:
        equiv = f"~{int(co2_kg * 1000000)} mg CO2 (a single breath)"
    elif co2_kg < 0.01:
        equiv = f"~{co2_kg * 1000:.1f} g CO2 (sending an email)"
    elif co2_kg < 0.1:
        equiv = f"~{co2_kg * 1000:.0f} g CO2 (charging a phone)"
    else:
        equiv = f"~{co2_kg:.2f} kg CO2 (driving {co2_kg * 4:.1f} km)"

    return CarbonEstimate(
        job_type=job_type,
        duration_seconds=duration_seconds,
        backend=backend,
        energy_kwh=round(energy_kwh, 6),
        co2_kg=round(co2_kg, 6),
        equivalent=equiv,
    )


def estimate_compute_time(sequence_length: int, job_type: str, backend: str = "cpu") -> float:
    """Predict job duration in seconds."""
    base = {
        "fold": {"cpu": 8.0, "cuda": 0.5, "metal": 3.0},
        "design": {"cpu": 5.0, "cuda": 0.3, "metal": 2.0},
        "evaluate": {"cpu": 0.1, "cuda": 0.1, "metal": 0.1},
        "md": {"cpu": 60.0, "cuda": 5.0, "metal": 30.0},
        "dock": {"cpu": 30.0, "cuda": 2.0, "metal": 15.0},
    }
    per_residue = base.get(job_type, {"cpu": 2.0}).get(backend, 2.0)
    return per_residue * sequence_length
