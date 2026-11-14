"""Directory watcher: auto-process new FASTA files dropped into a folder.

Usage:
    opendna watch <dir>

Monitors ``<dir>`` for new ``.fasta`` / ``.fa`` files. For each new file, parses
every sequence, runs :func:`opendna.engines.scoring.evaluate`, folds the
structure, and writes companion outputs next to the source file:

- ``<name>.opendna.json`` -- score results as JSON
- ``<name>.opendna.pdb``  -- predicted 3D structure

Requires the optional ``watchdog`` dependency. Install with::

    pip install opendna[watch]
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Iterable


_FASTA_EXTS = {".fasta", ".fa", ".faa"}


def _parse_fasta(text: str) -> list[tuple[str, str]]:
    """Return a list of ``(name, sequence)`` tuples from FASTA text."""
    entries: list[tuple[str, str]] = []
    name: str | None = None
    buf: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if name is not None:
                entries.append((name, "".join(buf)))
            name = line[1:].split()[0] if len(line) > 1 else "seq"
            buf = []
        else:
            buf.append(line.replace(" ", ""))
    if name is not None:
        entries.append((name, "".join(buf)))
    if not entries and text.strip():
        # Plain sequence, no header
        entries.append(("seq", text.strip().replace("\n", "").replace(" ", "")))
    return entries


def _score_to_dict(result) -> dict:
    if is_dataclass(result):
        return asdict(result)
    return {
        "overall": getattr(result, "overall", None),
        "confidence": getattr(result, "confidence", None),
        "summary": getattr(result, "summary", None),
        "recommendations": list(getattr(result, "recommendations", []) or []),
    }


def _process_fasta_file(path: Path, log=print) -> None:
    """Score + fold each sequence in *path* and write sibling outputs."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:  # pragma: no cover
        log(f"[watch] failed to read {path}: {e}")
        return

    entries = _parse_fasta(text)
    if not entries:
        log(f"[watch] no sequences found in {path.name}")
        return

    from opendna.engines.scoring import evaluate

    all_scores: list[dict] = []
    pdb_chunks: list[str] = []
    for name, seq in entries:
        if not seq:
            continue
        log(f"[watch] scoring {path.name}::{name} ({len(seq)} aa)")
        try:
            score = evaluate(seq)
            all_scores.append({"name": name, "sequence": seq, "score": _score_to_dict(score)})
        except Exception as e:
            log(f"[watch] scoring failed for {name}: {e}")
            all_scores.append({"name": name, "sequence": seq, "error": str(e)})

        # Best-effort folding
        try:
            from opendna.engines.folding import fold as fold_protein

            fr = fold_protein(seq)
            pdb = getattr(fr, "pdb_string", None)
            if callable(pdb):
                pdb = pdb()
            if pdb:
                pdb_chunks.append(f"REMARK   OpenDNA fold for {name}\n{pdb}")
        except Exception as e:
            log(f"[watch] folding skipped for {name}: {e}")

    stem = path.with_suffix("").name
    json_out = path.parent / f"{stem}.opendna.json"
    pdb_out = path.parent / f"{stem}.opendna.pdb"

    try:
        json_out.write_text(json.dumps(all_scores, indent=2), encoding="utf-8")
        log(f"[watch] wrote {json_out.name}")
    except Exception as e:
        log(f"[watch] failed to write {json_out}: {e}")

    if pdb_chunks:
        try:
            pdb_out.write_text("\n".join(pdb_chunks), encoding="utf-8")
            log(f"[watch] wrote {pdb_out.name}")
        except Exception as e:
            log(f"[watch] failed to write {pdb_out}: {e}")


def _iter_existing_fasta(directory: Path) -> Iterable[Path]:
    for ext in _FASTA_EXTS:
        yield from directory.glob(f"*{ext}")


def watch_directory(
    directory: str | Path,
    *,
    process_existing: bool = False,
    poll_interval: float = 1.0,
    log=print,
) -> None:
    """Watch *directory* for new FASTA files and process each as it appears.

    Raises ``RuntimeError`` with an installation hint if ``watchdog`` is not
    available.
    """
    directory = Path(directory).expanduser().resolve()
    if not directory.exists() or not directory.is_dir():
        raise NotADirectoryError(f"not a directory: {directory}")

    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError as e:
        raise RuntimeError(
            "opendna watch requires the 'watchdog' package. "
            "Install it with:\n\n    pip install watchdog\n\n"
            "or:\n\n    pip install opendna[watch]"
        ) from e

    if process_existing:
        for p in _iter_existing_fasta(directory):
            _process_fasta_file(p, log=log)

    class _Handler(FileSystemEventHandler):
        def on_created(self, event):  # type: ignore[override]
            if event.is_directory:
                return
            p = Path(event.src_path)
            if p.suffix.lower() in _FASTA_EXTS:
                # Small delay so the writer has time to finish flushing
                time.sleep(0.2)
                _process_fasta_file(p, log=log)

        def on_moved(self, event):  # type: ignore[override]
            if event.is_directory:
                return
            p = Path(getattr(event, "dest_path", ""))
            if p.suffix.lower() in _FASTA_EXTS:
                time.sleep(0.2)
                _process_fasta_file(p, log=log)

    observer = Observer()
    observer.schedule(_Handler(), str(directory), recursive=False)
    observer.start()
    log(f"[watch] watching {directory} for *.fasta / *.fa (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        log("[watch] stopping...")
    finally:
        observer.stop()
        observer.join()
