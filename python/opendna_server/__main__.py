"""PyInstaller entry point for the OpenDNA API server.

This is the script that gets compiled into opendna-server.exe (or .app or
binary) and bundled as a Tauri sidecar. It only depends on the lightweight
core stack (FastAPI + Uvicorn + the opendna package) - heavy ML libraries
are not bundled and get installed lazily by the Component Manager.
"""

from __future__ import annotations

import os
import sys


def main():
    # Allow port/host override via env var or CLI arg
    port = int(os.environ.get("OPENDNA_PORT", "8765"))
    host = os.environ.get("OPENDNA_HOST", "127.0.0.1")

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        elif args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        else:
            i += 1

    print(f"OpenDNA bundled server starting on http://{host}:{port}", flush=True)
    try:
        from opendna.api.server import start_server
    except ImportError as e:
        print(f"FATAL: opendna package not bundled correctly: {e}", file=sys.stderr)
        sys.exit(2)

    start_server(host=host, port=port)


if __name__ == "__main__":
    main()
