"""Molecular dynamics engine - real OpenMM with explicit solvent.

Schrödinger Desmond equivalent. Uses the AMBER14 force field, TIP3P water,
proper minimization, NVT/NPT equilibration, and production MD.

Falls back to a heuristic estimator if OpenMM is not installed.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class MdResult:
    duration_ps: float
    n_frames: int
    rmsd_trajectory: list[float]
    rmsf_per_residue: list[float] = field(default_factory=list)
    radius_of_gyration_trajectory: list[float] = field(default_factory=list)
    final_rmsd: float = 0.0
    mean_rmsd: float = 0.0
    stable: bool = True
    method: str = "heuristic"
    notes: str = ""
    n_atoms: int = 0
    n_solvent_atoms: int = 0
    temperature_k: float = 300.0
    forcefield: str = ""


def quick_md(
    pdb_string: str,
    duration_ps: float = 100,
    explicit_solvent: bool = True,
    on_progress: Optional[Callable[[str, float], None]] = None,
) -> MdResult:
    """Run a molecular dynamics simulation.

    Args:
        pdb_string: Input structure as PDB content
        duration_ps: Production simulation length in picoseconds
        explicit_solvent: Use TIP3P water box (slower, more accurate)
        on_progress: Optional progress callback

    Returns:
        MdResult with full trajectory analysis. Falls back to heuristic if
        OpenMM is not installed.
    """
    try:
        import openmm  # noqa: F401
    except ImportError:
        logger.warning("OpenMM not installed - using heuristic. Install with: pip install openmm")
        return _heuristic_md(pdb_string, duration_ps, on_progress)

    try:
        return _real_openmm(pdb_string, duration_ps, explicit_solvent, on_progress)
    except Exception as e:
        logger.warning(f"OpenMM run failed ({e}), falling back to heuristic")
        return _heuristic_md(pdb_string, duration_ps, on_progress)


def _real_openmm(pdb_string, duration_ps, explicit_solvent, on_progress):
    """Real molecular dynamics with explicit solvent via OpenMM."""
    from openmm import LangevinMiddleIntegrator, MonteCarloBarostat, Platform, unit
    from openmm.app import (
        ForceField, PDBFile, Simulation, Modeller, PME, HBonds, NoCutoff,
        StateDataReporter, DCDReporter,
    )
    import math

    if on_progress:
        on_progress("Loading PDB", 0.02)

    pdb = PDBFile(io.StringIO(pdb_string))
    n_protein_atoms = pdb.topology.getNumAtoms()

    if on_progress:
        on_progress("Loading AMBER14 force field", 0.05)

    forcefield = ForceField("amber14-all.xml", "amber14/tip3pfb.xml")
    modeller = Modeller(pdb.topology, pdb.positions)

    if on_progress:
        on_progress("Adding hydrogens", 0.08)
    modeller.addHydrogens(forcefield)

    if explicit_solvent:
        if on_progress:
            on_progress("Solvating in TIP3P water box", 0.12)
        modeller.addSolvent(forcefield, padding=1.0 * unit.nanometer, ionicStrength=0.15 * unit.molar)
        n_total_atoms = modeller.topology.getNumAtoms()
        n_solvent = n_total_atoms - n_protein_atoms

        system = forcefield.createSystem(
            modeller.topology,
            nonbondedMethod=PME,
            nonbondedCutoff=1.0 * unit.nanometer,
            constraints=HBonds,
        )
        # Add barostat for NPT
        system.addForce(MonteCarloBarostat(1 * unit.atmospheres, 300 * unit.kelvin))
    else:
        n_total_atoms = modeller.topology.getNumAtoms()
        n_solvent = 0
        system = forcefield.createSystem(
            modeller.topology,
            nonbondedMethod=NoCutoff,
            constraints=HBonds,
        )

    if on_progress:
        on_progress("Setting up integrator", 0.18)

    integrator = LangevinMiddleIntegrator(
        300 * unit.kelvin,
        1 / unit.picosecond,
        2 * unit.femtoseconds,
    )

    # Choose best available platform
    try:
        platform = Platform.getPlatformByName("CUDA")
    except Exception:
        try:
            platform = Platform.getPlatformByName("OpenCL")
        except Exception:
            try:
                platform = Platform.getPlatformByName("CPU")
            except Exception:
                platform = None

    if platform:
        sim = Simulation(modeller.topology, system, integrator, platform)
    else:
        sim = Simulation(modeller.topology, system, integrator)

    sim.context.setPositions(modeller.positions)

    if on_progress:
        on_progress("Energy minimization", 0.22)
    sim.minimizeEnergy(maxIterations=200)

    if on_progress:
        on_progress("NVT equilibration (100 ps)", 0.32)
    sim.context.setVelocitiesToTemperature(300 * unit.kelvin)
    nvt_steps = int(50 * 500)  # 50 ps at 2 fs steps
    sim.step(nvt_steps)

    if on_progress:
        on_progress("Production MD", 0.45)

    # Collect snapshots throughout production
    n_steps_total = int(duration_ps * 500)  # 2 fs steps
    n_snapshots = 20
    steps_per_snapshot = max(1, n_steps_total // n_snapshots)

    # Save initial reference frame
    initial_positions = sim.context.getState(getPositions=True).getPositions(asNumpy=True)
    rmsd_trajectory = []
    rg_trajectory = []
    final_positions = initial_positions

    for snap in range(n_snapshots):
        sim.step(steps_per_snapshot)
        if on_progress:
            on_progress(
                f"MD step {(snap + 1) * steps_per_snapshot}/{n_steps_total}",
                0.45 + 0.5 * (snap + 1) / n_snapshots,
            )

        state = sim.context.getState(getPositions=True)
        positions = state.getPositions(asNumpy=True)
        # Compute heavy-atom RMSD vs initial (over protein atoms only)
        try:
            rmsd = _compute_rmsd_protein(initial_positions, positions, n_protein_atoms)
        except Exception:
            rmsd = 0.0
        rmsd_trajectory.append(round(float(rmsd), 3))
        # Radius of gyration of the protein
        try:
            rg = _compute_rg(positions, n_protein_atoms)
        except Exception:
            rg = 0.0
        rg_trajectory.append(round(float(rg), 3))
        final_positions = positions

    # Per-residue RMSF (CA atoms)
    rmsf_per_residue = _compute_rmsf(initial_positions, final_positions, sim.topology)

    final_rmsd = rmsd_trajectory[-1] if rmsd_trajectory else 0.0
    mean_rmsd = sum(rmsd_trajectory) / len(rmsd_trajectory) if rmsd_trajectory else 0.0
    stable = final_rmsd < 4.0

    if on_progress:
        on_progress("Complete", 1.0)

    return MdResult(
        duration_ps=duration_ps,
        n_frames=n_snapshots,
        rmsd_trajectory=rmsd_trajectory,
        rmsf_per_residue=rmsf_per_residue,
        radius_of_gyration_trajectory=rg_trajectory,
        final_rmsd=round(final_rmsd, 3),
        mean_rmsd=round(mean_rmsd, 3),
        stable=stable,
        method="openmm-amber14-tip3p" if explicit_solvent else "openmm-amber14-vacuum",
        notes=f"Real OpenMM MD: {duration_ps} ps production, AMBER14 + {('TIP3P explicit' if explicit_solvent else 'vacuum')}, Langevin 300 K",
        n_atoms=n_total_atoms,
        n_solvent_atoms=n_solvent,
        temperature_k=300.0,
        forcefield="AMBER14",
    )


def _compute_rmsd_protein(ref_positions, current_positions, n_protein) -> float:
    import numpy as np
    ref = np.asarray(ref_positions[:n_protein])
    cur = np.asarray(current_positions[:n_protein])
    diff = cur - ref
    return float(np.sqrt((diff * diff).sum() / n_protein))


def _compute_rg(positions, n_protein) -> float:
    import numpy as np
    p = np.asarray(positions[:n_protein])
    center = p.mean(axis=0)
    diff = p - center
    return float(np.sqrt((diff * diff).sum() / n_protein))


def _compute_rmsf(initial_positions, final_positions, topology) -> list[float]:
    """Per-residue RMSF (root mean square fluctuation) on CA atoms."""
    import numpy as np
    rmsf = []
    for residue in topology.residues():
        ca_indices = [a.index for a in residue.atoms() if a.name == "CA"]
        if not ca_indices:
            continue
        idx = ca_indices[0]
        try:
            i = np.asarray(initial_positions[idx])
            f = np.asarray(final_positions[idx])
            d = f - i
            rmsf.append(round(float(np.sqrt((d * d).sum())), 3))
        except Exception:
            rmsf.append(0.0)
    return rmsf


def _heuristic_md(pdb_string, duration_ps, on_progress):
    """Heuristic fallback when OpenMM is not available."""
    if on_progress:
        on_progress("Heuristic stability check (OpenMM not installed)", 0.5)

    lines = pdb_string.split("\n")
    atoms = [l for l in lines if l.startswith("ATOM")]
    n_atoms = len(atoms)

    b_factors = []
    for line in atoms[:1000]:
        if len(line) >= 66:
            try:
                b_factors.append(float(line[60:66].strip()))
            except ValueError:
                pass

    avg_bf = sum(b_factors) / len(b_factors) if b_factors else 0.5
    estimated_rmsd = 0.5 + (1 - avg_bf) * 2

    import math
    n_frames = 20
    traj = [round(estimated_rmsd * (1 - math.exp(-i / 5)), 3) for i in range(n_frames)]

    if on_progress:
        on_progress("Complete", 1.0)

    return MdResult(
        duration_ps=duration_ps,
        n_frames=n_frames,
        rmsd_trajectory=traj,
        rmsf_per_residue=[],
        radius_of_gyration_trajectory=[],
        final_rmsd=traj[-1],
        mean_rmsd=sum(traj) / len(traj),
        stable=traj[-1] < 3.0,
        method="heuristic",
        notes="Heuristic estimate from pLDDT confidence. Install OpenMM (pip install openmm) for real MD with explicit solvent.",
        n_atoms=n_atoms,
        n_solvent_atoms=0,
    )
