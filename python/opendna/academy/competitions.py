"""In-app protein engineering competitions.

Five hardcoded ongoing competitions with a SQLite leaderboard persisted to
``~/.opendna/competitions.db``. Each competition uses a simple, fast-to-compute
scoring metric so submissions can be scored inline without running a full
folding job.
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List

_HYDRO = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5,
    "E": -3.5, "Q": -3.5, "G": -0.4, "H": -3.2, "I": 4.5,
    "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8, "P": -1.6,
    "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}

_COMPETITIONS: List[Dict[str, Any]] = [
    {
        "id": "smallest-stable-fold",
        "title": "Smallest stable fold",
        "description": "Design the shortest sequence that still scores well on hydrophobic-core packing.",
        "starts_at": "2026-01-01",
        "ends_at": "2026-12-31",
        "scoring_metric": "stability_per_length",
        "prize": "100 OpenDNA XP + featured on the hub",
    },
    {
        "id": "best-caffeine-binder",
        "title": "Best caffeine binder",
        "description": "Design a short peptide with a binding pocket estimated to bind caffeine.",
        "starts_at": "2026-01-01",
        "ends_at": "2026-12-31",
        "scoring_metric": "aromatic_density",
        "prize": "50 OpenDNA XP",
    },
    {
        "id": "shortest-her2-antibody",
        "title": "Shortest antibody that binds HER2",
        "description": "Design the shortest antibody CDR that preserves HER2 epitope contact motifs.",
        "starts_at": "2026-01-01",
        "ends_at": "2026-12-31",
        "scoring_metric": "her2_motif_score",
        "prize": "75 OpenDNA XP",
    },
    {
        "id": "ubiquitin-thermostable",
        "title": "Most thermostable variant of ubiquitin",
        "description": "Introduce mutations that maximize predicted thermostability relative to wild-type ubiquitin.",
        "starts_at": "2026-01-01",
        "ends_at": "2026-12-31",
        "scoring_metric": "thermostability",
        "prize": "125 OpenDNA XP",
    },
    {
        "id": "hydrophobic-50mer",
        "title": "Most hydrophobic 50-aa peptide",
        "description": "Design a 50-residue peptide with maximum Kyte-Doolittle hydrophobicity.",
        "starts_at": "2026-01-01",
        "ends_at": "2026-12-31",
        "scoring_metric": "hydrophobicity",
        "prize": "25 OpenDNA XP",
    },
]


def _db_path() -> Path:
    d = Path(os.path.expanduser("~/.opendna"))
    d.mkdir(parents=True, exist_ok=True)
    return d / "competitions.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_db_path()))
    c.execute(
        """CREATE TABLE IF NOT EXISTS entries (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               competition_id TEXT NOT NULL,
               user_id TEXT NOT NULL,
               sequence TEXT NOT NULL,
               score REAL NOT NULL,
               submitted_at REAL NOT NULL
           )"""
    )
    return c


def list_competitions() -> List[Dict[str, Any]]:
    """Return the five hardcoded competitions."""
    return [dict(c) for c in _COMPETITIONS]


def _get_comp(competition_id: str) -> Dict[str, Any]:
    for c in _COMPETITIONS:
        if c["id"] == competition_id:
            return c
    raise ValueError(f"Unknown competition: {competition_id}")


def _score(seq: str, metric: str) -> float:
    seq = (seq or "").upper()
    if not seq:
        return 0.0
    n = len(seq)
    if metric == "hydrophobicity":
        return sum(_HYDRO.get(a, 0.0) for a in seq) / n
    if metric == "stability_per_length":
        hydro = sum(max(_HYDRO.get(a, 0.0), 0.0) for a in seq) / n
        length_penalty = 1.0 / (1.0 + n / 50.0)
        return hydro * length_penalty
    if metric == "aromatic_density":
        aromatic = sum(1 for a in seq if a in "FWY")
        return aromatic / n
    if metric == "her2_motif_score":
        motifs = ["WGQ", "DYW", "YYD", "SRW"]
        hits = sum(seq.count(m) for m in motifs)
        return hits / max(1.0, (n / 10.0))
    if metric == "thermostability":
        # Favor proline, isoleucine, valine, leucine; penalize Gly/Met
        up = sum(1 for a in seq if a in "PIVL")
        dn = sum(1 for a in seq if a in "GM")
        return (up - 0.5 * dn) / n
    return 0.0


def submit_entry(competition_id: str, user_id: str, sequence: str) -> Dict[str, Any]:
    """Score a submission and persist it to the leaderboard."""
    comp = _get_comp(competition_id)
    score = _score(sequence, comp["scoring_metric"])
    ts = time.time()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO entries (competition_id, user_id, sequence, score, submitted_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (competition_id, user_id, sequence, float(score), ts),
        )
        entry_id = cur.lastrowid
    return {
        "entry_id": entry_id,
        "competition_id": competition_id,
        "user_id": user_id,
        "score": float(score),
        "submitted_at": ts,
        "metric": comp["scoring_metric"],
    }


def competition_leaderboard(competition_id: str, top_n: int = 20) -> List[Dict[str, Any]]:
    """Return the top-N entries (highest score first) for a competition."""
    _get_comp(competition_id)  # validate
    with _conn() as c:
        rows = c.execute(
            "SELECT id, user_id, sequence, score, submitted_at "
            "FROM entries WHERE competition_id = ? "
            "ORDER BY score DESC, submitted_at ASC LIMIT ?",
            (competition_id, int(top_n)),
        ).fetchall()
    return [
        {
            "entry_id": r[0],
            "user_id": r[1],
            "sequence": r[2],
            "score": r[3],
            "submitted_at": r[4],
            "rank": i + 1,
        }
        for i, r in enumerate(rows)
    ]
