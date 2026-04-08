"""OpenDNA: The People's Protein Engineering Platform."""

__version__ = "0.5.0-rc1"

# Lightweight imports only - heavy ML modules are imported lazily inside their functions
from opendna.models.protein import Protein, Sequence, Structure

__all__ = [
    "Protein",
    "Sequence",
    "Structure",
    "fold",
    "design",
    "evaluate",
    "__version__",
]


def __getattr__(name):
    """Lazy attribute loader for heavy ML functions.

    `from opendna import fold` works without importing torch/esm at package load.
    """
    if name == "fold":
        from opendna.engines.folding import fold
        return fold
    if name == "design":
        from opendna.engines.design import design
        return design
    if name == "evaluate":
        from opendna.engines.scoring import evaluate
        return evaluate
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
