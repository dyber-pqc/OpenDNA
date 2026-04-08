"""Component Manager - Altium/Vivado-style on-demand installer for heavy ML models.

The desktop installer ships small (~150 MB bundled sidecar). Users pick which
heavy components (ESMFold, DiffDock, Boltz, RFdiffusion, OpenMM, xTB, Ollama)
to install on first run via the Component Manager UI.
"""
from .registry import Component, list_components, get_component
from .manager import (
    get_status,
    install_component,
    uninstall_component,
    total_disk_usage,
)

__all__ = [
    "Component",
    "list_components",
    "get_component",
    "get_status",
    "install_component",
    "uninstall_component",
    "total_disk_usage",
]
