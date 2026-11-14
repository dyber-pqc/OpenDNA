"""Foldseek web API client for structural similarity search.

Posts a PDB string to https://search.foldseek.com and polls until results are
ready. Falls back gracefully when the public API is unreachable.
"""

from __future__ import annotations

import time
from typing import Any

FOLDSEEK_BASE = "https://search.foldseek.com/api"
DEFAULT_TIMEOUT = 15
POLL_INTERVAL = 2.0
MAX_POLLS = 45


def foldseek_search(pdb_string: str, database: str = "afdb") -> dict:
    """Run a structural similarity search via the Foldseek web API.

    Parameters
    ----------
    pdb_string : str
        PDB file contents to search with.
    database : str
        Target database. Common values: "afdb", "pdb100", "mgnify_esm30".

    Returns
    -------
    dict
        ``{"ticket_id", "database", "hits": [...]}`` on success, or
        ``{"error", "hits": []}`` on failure.
    """
    if not pdb_string or "ATOM" not in pdb_string:
        return {"error": "empty or invalid pdb_string", "hits": []}

    try:
        import requests  # type: ignore
    except Exception as exc:  # pragma: no cover
        return {"error": f"requests unavailable: {exc}", "hits": []}

    db_map = {
        "afdb": "afdb50",
        "afdb50": "afdb50",
        "afdb-proteome": "afdb-proteome",
        "pdb": "pdb100",
        "pdb100": "pdb100",
        "mgnify": "mgnify_esm30",
        "mgnify_esm30": "mgnify_esm30",
    }
    target_db = db_map.get(database.lower(), database)

    try:
        files = {"q": ("query.pdb", pdb_string.encode("utf-8"), "chemical/x-pdb")}
        data = {"database[]": target_db, "mode": "3diaa"}
        resp = requests.post(
            f"{FOLDSEEK_BASE}/ticket",
            files=files,
            data=data,
            timeout=DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            return {"error": f"ticket failed: HTTP {resp.status_code}", "hits": []}
        ticket = resp.json()
        ticket_id = ticket.get("id") or ticket.get("ticket") or ticket.get("ticketId")
        if not ticket_id:
            return {"error": f"no ticket id in response: {ticket}", "hits": []}
    except Exception as exc:
        return {"error": f"Foldseek unreachable: {exc}", "hits": []}

    # Poll for completion
    try:
        for _ in range(MAX_POLLS):
            time.sleep(POLL_INTERVAL)
            tr = requests.get(
                f"{FOLDSEEK_BASE}/ticket/{ticket_id}", timeout=DEFAULT_TIMEOUT
            )
            if tr.status_code >= 400:
                return {
                    "error": f"poll failed: HTTP {tr.status_code}",
                    "ticket_id": ticket_id,
                    "hits": [],
                }
            status = (tr.json() or {}).get("status", "")
            if status == "COMPLETE":
                break
            if status == "ERROR":
                return {
                    "error": "Foldseek reported ERROR status",
                    "ticket_id": ticket_id,
                    "hits": [],
                }
        else:
            return {
                "error": "Foldseek polling timed out",
                "ticket_id": ticket_id,
                "hits": [],
            }

        res = requests.get(
            f"{FOLDSEEK_BASE}/result/{ticket_id}/0", timeout=DEFAULT_TIMEOUT
        )
        if res.status_code >= 400:
            return {
                "error": f"result fetch failed: HTTP {res.status_code}",
                "ticket_id": ticket_id,
                "hits": [],
            }
        payload = res.json()
    except Exception as exc:
        return {
            "error": f"Foldseek poll/result error: {exc}",
            "ticket_id": ticket_id,
            "hits": [],
        }

    return {
        "ticket_id": ticket_id,
        "database": target_db,
        "hits": _parse_hits(payload),
    }


def _parse_hits(payload: Any) -> list[dict]:
    """Normalize Foldseek JSON results into a flat list of hits."""
    hits: list[dict] = []
    # Foldseek result schema: {"results": [{"alignments": [[{target, eval, score, ...}]]}]}
    try:
        results = payload.get("results") if isinstance(payload, dict) else None
        if not results:
            return hits
        for result in results:
            alignments = result.get("alignments") or []
            # alignments is list of lists (per query chain)
            for group in alignments:
                if isinstance(group, dict):
                    group = [group]
                for aln in group or []:
                    hits.append(
                        {
                            "target_id": (
                                aln.get("target")
                                or aln.get("targetId")
                                or aln.get("targetHeader")
                                or "unknown"
                            ),
                            "evalue": float(aln.get("eval", aln.get("evalue", 0.0)) or 0.0),
                            "score": float(aln.get("score", 0.0) or 0.0),
                            "length": int(aln.get("alnLength", aln.get("length", 0)) or 0),
                            "alignment": {
                                "qStart": aln.get("qStartPos", aln.get("qStart")),
                                "qEnd": aln.get("qEndPos", aln.get("qEnd")),
                                "tStart": aln.get("dbStartPos", aln.get("tStart")),
                                "tEnd": aln.get("dbEndPos", aln.get("tEnd")),
                                "seqId": aln.get("seqId"),
                                "qAln": aln.get("qAln"),
                                "dbAln": aln.get("dbAln"),
                            },
                        }
                    )
    except Exception:
        return hits
    return hits
