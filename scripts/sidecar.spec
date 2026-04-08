# PyInstaller spec for the OpenDNA sidecar binary.
#
# Build with: python scripts/build_sidecar.py
# Or directly: pyinstaller scripts/sidecar.spec
#
# Output: dist/opendna-server  (or dist/opendna-server.exe on Windows)

# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

REPO_ROOT = Path(SPECPATH).parent.resolve()
PYTHON_DIR = REPO_ROOT / "python"

sys.path.insert(0, str(PYTHON_DIR))

block_cipher = None

a = Analysis(
    [str(PYTHON_DIR / "opendna_server" / "__main__.py")],
    pathex=[str(PYTHON_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # FastAPI / Uvicorn
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "starlette",
        "starlette.routing",
        "pydantic",
        "pydantic_core",
        "sse_starlette",
        # OpenDNA
        "opendna",
        "opendna.api",
        "opendna.api.server",
        "opendna.engines",
        "opendna.engines.scoring",
        "opendna.engines.analysis",
        "opendna.engines.disorder",
        "opendna.engines.predictors",
        "opendna.engines.bonds",
        "opendna.engines.alignment",
        "opendna.engines.qsar",
        "opendna.engines.antibody",
        "opendna.engines.pharmacophore",
        "opendna.engines.validation",
        "opendna.engines.mmgbsa",
        "opendna.engines.constrained_design",
        "opendna.engines.multi_objective",
        "opendna.engines.iterative",
        "opendna.engines.conservation",
        "opendna.engines.docking",
        "opendna.engines.dynamics",
        "opendna.engines.multimer",
        "opendna.engines.explain",
        "opendna.engines.nlu",
        "opendna.data",
        "opendna.data.sources",
        "opendna.data.synthesis",
        "opendna.storage",
        "opendna.storage.database",
        "opendna.storage.projects",
        "opendna.storage.export",
        "opendna.storage.jobs",
        "opendna.hardware",
        "opendna.hardware.detect",
        "opendna.cli",
        "opendna.cli.main",
        "opendna.llm",
        "opendna.llm.providers",
        "opendna.llm.tools",
        "opendna.llm.agent",
        "opendna.sdk",
        "opendna.workflows",
        "opendna.benchmarks",
        # NumPy / SQLAlchemy / Biopython core
        "numpy",
        "sqlalchemy",
        "sqlalchemy.dialects",
        "sqlalchemy.dialects.sqlite",
        "Bio",
        "Bio.Seq",
        # HTTP
        "httpx",
        "httpcore",
        "anyio",
        # Misc
        "yaml",
        "psutil",
        "typer",
        "rich",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Heavy ML libs explicitly EXCLUDED - they get installed lazily by Component Manager
        "torch",
        "transformers",
        "esm",
        "fair_esm",
        "biotite",
        "torch_geometric",
        "openmm",
        "tkinter",
        "matplotlib",
        "scipy",
        "pandas",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="opendna-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX adds compression but slows startup; not worth it
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Sidecar runs in background, console=True helps with logging
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
