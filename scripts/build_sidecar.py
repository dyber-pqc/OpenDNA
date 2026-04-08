#!/usr/bin/env python3
"""Build the OpenDNA sidecar binary using PyInstaller.

This produces a single-file executable that bundles Python + FastAPI +
OpenDNA core (NOT the heavy ML libraries — those get installed lazily
via the Component Manager).

Usage:
    python scripts/build_sidecar.py

Output:
    dist/opendna-server.exe                              (Windows)
    dist/opendna-server                                  (Linux/macOS)

For Tauri sidecar bundling, the binary needs a platform-triple suffix:
    opendna-server-x86_64-pc-windows-msvc.exe
    opendna-server-x86_64-apple-darwin
    opendna-server-aarch64-apple-darwin
    opendna-server-x86_64-unknown-linux-gnu

This script copies the built binary to the right name in
ui/src-tauri/binaries/ so Tauri can bundle it.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent.resolve()
SPEC_FILE = REPO_ROOT / "scripts" / "sidecar.spec"
TAURI_BINARIES_DIR = REPO_ROOT / "ui" / "src-tauri" / "binaries"


def get_target_triple() -> str:
    """Return the Rust-style target triple for the current platform."""
    system = platform.system()
    machine = platform.machine().lower()

    if system == "Windows":
        return "x86_64-pc-windows-msvc"
    if system == "Darwin":
        if machine in ("arm64", "aarch64"):
            return "aarch64-apple-darwin"
        return "x86_64-apple-darwin"
    if system == "Linux":
        if machine in ("aarch64", "arm64"):
            return "aarch64-unknown-linux-gnu"
        return "x86_64-unknown-linux-gnu"
    raise RuntimeError(f"Unsupported platform: {system}")


def ensure_pyinstaller():
    """Make sure PyInstaller is available."""
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller not found, installing...", flush=True)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"])


def build_with_pyinstaller():
    """Run PyInstaller against our spec file."""
    print(f"Building sidecar from {SPEC_FILE}...", flush=True)
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            "--distpath",
            str(REPO_ROOT / "dist"),
            "--workpath",
            str(REPO_ROOT / "build"),
            str(SPEC_FILE),
        ],
        cwd=REPO_ROOT,
    )


def copy_to_tauri_binaries():
    """Copy the built binary to ui/src-tauri/binaries/ with the target triple suffix."""
    triple = get_target_triple()
    is_windows = platform.system() == "Windows"
    suffix = ".exe" if is_windows else ""

    src = REPO_ROOT / "dist" / f"opendna-server{suffix}"
    if not src.exists():
        print(f"ERROR: Built binary not found at {src}", file=sys.stderr)
        sys.exit(1)

    TAURI_BINARIES_DIR.mkdir(parents=True, exist_ok=True)
    dst = TAURI_BINARIES_DIR / f"opendna-server-{triple}{suffix}"
    print(f"Copying {src} -> {dst}", flush=True)
    shutil.copy2(src, dst)

    if not is_windows:
        # Make sure it's executable
        dst.chmod(0o755)

    print(f"Sidecar binary ready: {dst}", flush=True)
    print(f"Size: {dst.stat().st_size / 1024 / 1024:.1f} MB", flush=True)


def main():
    print(f"Repo root: {REPO_ROOT}", flush=True)
    print(f"Target triple: {get_target_triple()}", flush=True)
    ensure_pyinstaller()
    build_with_pyinstaller()
    copy_to_tauri_binaries()
    print("Sidecar build complete.", flush=True)


if __name__ == "__main__":
    main()
