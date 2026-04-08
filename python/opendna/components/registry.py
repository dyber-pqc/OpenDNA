"""Registry of installable heavy components (ML models, MD engines, QM tools, LLMs)."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any


@dataclass
class Component:
    name: str
    display_name: str
    category: str  # folding | design | docking | md | qm | llm | multimer
    description: str
    size_mb: int
    version: str
    install_kind: str  # "pip" | "hf" | "script" | "ollama"
    install_target: str  # package spec, HF repo id, script path, or ollama model tag
    import_check: Optional[str] = None  # python statement to verify install
    homepage: Optional[str] = None
    license: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_REGISTRY: List[Component] = [
    # -------- Folding --------
    Component(
        name="esmfold",
        display_name="ESMFold v1",
        category="folding",
        description="Meta's single-sequence structure predictor. No MSA required. ~8 GB.",
        size_mb=8000,
        version="v1",
        install_kind="hf",
        install_target="facebook/esmfold_v1",
        import_check="import transformers; transformers.EsmForProteinFolding",
        homepage="https://github.com/facebookresearch/esm",
        license="MIT",
    ),
    Component(
        name="boltz",
        display_name="Boltz-1 Multimer",
        category="multimer",
        description="Open-source AlphaFold-Multimer-grade complex predictor.",
        size_mb=5500,
        version="1.0",
        install_kind="pip",
        install_target="boltz>=0.3",
        import_check="import boltz",
        homepage="https://github.com/jwohlwend/boltz",
        license="MIT",
    ),
    Component(
        name="colabfold",
        display_name="ColabFold (AF2-Multimer)",
        category="multimer",
        description="ColabFold wrapper around AlphaFold2 including multimer mode.",
        size_mb=2500,
        version="1.5",
        install_kind="pip",
        install_target="colabfold",
        import_check="import colabfold",
        homepage="https://github.com/sokrypton/ColabFold",
        license="MIT",
    ),
    # -------- Design --------
    Component(
        name="esm-if1",
        display_name="ESM-IF1 Inverse Folding",
        category="design",
        description="Structure → sequence design. Samples diverse sequences for a backbone.",
        size_mb=650,
        version="1.0",
        install_kind="hf",
        install_target="facebook/esm_if1_gvp4_t16_142M_UR50",
        import_check="import esm",
        homepage="https://github.com/facebookresearch/esm",
        license="MIT",
    ),
    Component(
        name="esm2",
        display_name="ESM-2 650M",
        category="design",
        description="Protein language model for conservation/perplexity scoring.",
        size_mb=2600,
        version="650M",
        install_kind="hf",
        install_target="facebook/esm2_t33_650M_UR50D",
        import_check="import transformers",
        license="MIT",
    ),
    Component(
        name="rfdiffusion",
        display_name="RFdiffusion",
        category="design",
        description="De novo protein backbone generation with diffusion (Baker lab).",
        size_mb=5200,
        version="1.0",
        install_kind="script",
        install_target="rfdiffusion",
        import_check="import rfdiffusion",
        homepage="https://github.com/RosettaCommons/RFdiffusion",
        license="BSD-3-Clause",
    ),
    # -------- Docking --------
    Component(
        name="diffdock",
        display_name="DiffDock",
        category="docking",
        description="Diffusion-based protein–ligand docking with state-of-the-art accuracy.",
        size_mb=1400,
        version="1.1",
        install_kind="pip",
        install_target="diffdock",
        import_check="import diffdock",
        homepage="https://github.com/gcorso/DiffDock",
        license="MIT",
    ),
    # -------- MD --------
    Component(
        name="openmm",
        display_name="OpenMM",
        category="md",
        description="GPU-accelerated molecular dynamics engine.",
        size_mb=350,
        version="8.1",
        install_kind="pip",
        install_target="openmm",
        import_check="import openmm",
        homepage="https://openmm.org",
        license="MIT",
    ),
    # -------- Quantum --------
    Component(
        name="xtb",
        display_name="xTB Semiempirical QM",
        category="qm",
        description="Grimme's GFN-xTB semiempirical tight-binding quantum chemistry.",
        size_mb=120,
        version="6.6",
        install_kind="pip",
        install_target="xtb-python",
        import_check="import xtb",
        license="LGPL-3.0",
    ),
    Component(
        name="ani2x",
        display_name="TorchANI ANI-2x",
        category="qm",
        description="ML potential for near-DFT energies at force-field speed.",
        size_mb=250,
        version="2x",
        install_kind="pip",
        install_target="torchani",
        import_check="import torchani",
        license="MIT",
    ),
    # -------- LLM --------
    Component(
        name="ollama",
        display_name="Ollama + llama3.2:3b",
        category="llm",
        description="Local LLM runner + small chat model for the on-device AI agent.",
        size_mb=2100,
        version="llama3.2:3b",
        install_kind="ollama",
        install_target="llama3.2:3b",
        homepage="https://ollama.com",
        license="Llama-3 Community",
    ),
]


def list_components() -> List[Component]:
    return list(_REGISTRY)


def get_component(name: str) -> Optional[Component]:
    for c in _REGISTRY:
        if c.name == name:
            return c
    return None
