"""Daily challenges + leaderboard.

Each day, a deterministic challenge is generated from a date hash so all
users see the same one. Completions are stored in SQLite for streaks and
the leaderboard.
"""
from __future__ import annotations

import datetime
import hashlib
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


_CHALLENGES = [
    {
        "kind": "score_threshold",
        "prompt": "Find a 20-amino-acid sequence that scores at least 0.7. Submit the sequence.",
        "validate": "score>=0.7 and len==20",
        "xp": 75,
    },
    {
        "kind": "no_cysteine",
        "prompt": "Design a 30-aa sequence with no cysteines that scores >0.6.",
        "validate": "no_cys and score>=0.6 and len==30",
        "xp": 100,
    },
    {
        "kind": "alpha_helix",
        "prompt": "Design a 25-aa sequence rich in alanine and leucine — classical alpha-helix design.",
        "validate": "len==25 and (count(A)+count(L))/len>=0.4",
        "xp": 100,
    },
    {
        "kind": "small_charge",
        "prompt": "Design a 40-aa sequence with net charge between -2 and +2.",
        "validate": "len==40 and -2<=net_charge<=2",
        "xp": 125,
    },
    {
        "kind": "membrane",
        "prompt": "Design a 22-aa hydrophobic transmembrane helix.",
        "validate": "len==22 and gravy>=1.5",
        "xp": 150,
    },
    {
        "kind": "soluble",
        "prompt": "Design a 50-aa sequence predicted to be highly soluble.",
        "validate": "len==50 and solubility>=0.7",
        "xp": 150,
    },
    {
        "kind": "stable_mutation",
        "prompt": "Take 'MKTVRQERLKSIVRILER' and find a single point mutation that improves the score.",
        "validate": "single_mutation and score_delta>0",
        "xp": 200,
    },
]


def _today() -> str:
    return datetime.date.today().isoformat()


def daily_challenge(date_str: Optional[str] = None) -> Dict[str, Any]:
    d = date_str or _today()
    h = int(hashlib.sha256(d.encode()).hexdigest(), 16)
    c = _CHALLENGES[h % len(_CHALLENGES)]
    return {"date": d, **c}


def _db() -> sqlite3.Connection:
    p = Path(os.environ.get("OPENDNA_AUTH_DIR", Path.home() / ".opendna"))
    p.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(p / "academy.db", check_same_thread=False)
    c.execute(
        """CREATE TABLE IF NOT EXISTS completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            challenge_date TEXT NOT NULL,
            xp INTEGER NOT NULL,
            ts REAL NOT NULL,
            sequence TEXT,
            UNIQUE(user_id, challenge_date)
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS user_xp (
            user_id TEXT PRIMARY KEY,
            total_xp INTEGER NOT NULL DEFAULT 0,
            current_streak INTEGER NOT NULL DEFAULT 0,
            longest_streak INTEGER NOT NULL DEFAULT 0,
            last_active TEXT
        )"""
    )
    return c


def _eval_validate(rule: str, ctx: Dict[str, Any]) -> bool:
    """Tiny safe-ish DSL for validate strings — only the names we put in ctx are visible."""
    safe_globals = {"__builtins__": {}}
    safe_globals.update(ctx)
    try:
        return bool(eval(rule, safe_globals))  # noqa: S307 — controlled DSL
    except Exception:
        return False


def check_answer(user_id: str, sequence: str, date_str: Optional[str] = None) -> Dict[str, Any]:
    challenge = daily_challenge(date_str)
    # Build a very simple feature vector — keeps deps zero
    seq = sequence.upper()
    L = len(seq)
    no_cys = ("C" not in seq)
    A_pct = seq.count("A") / max(L, 1)
    L_pct = seq.count("L") / max(L, 1)
    pos = sum(seq.count(x) for x in "RKH")
    neg = sum(seq.count(x) for x in "DE")
    net_charge = pos - neg
    # GRAVY (Kyte-Doolittle, dummy approximation)
    KD = {"A":1.8,"R":-4.5,"N":-3.5,"D":-3.5,"C":2.5,"Q":-3.5,"E":-3.5,"G":-0.4,"H":-3.2,
          "I":4.5,"L":3.8,"K":-3.9,"M":1.9,"F":2.8,"P":-1.6,"S":-0.8,"T":-0.7,"W":-0.9,"Y":-1.3,"V":4.2}
    gravy = sum(KD.get(a, 0.0) for a in seq) / max(L, 1)
    # Score: tiny heuristic in 0..1
    score = max(0.0, min(1.0, 0.5 + 0.2 * (1 - abs(net_charge) / max(L, 1)) - 0.005 * abs(L - 30)))
    solubility = max(0.0, min(1.0, 0.6 - 0.05 * gravy))
    ctx = {
        "len": L, "no_cys": no_cys, "score": score, "net_charge": net_charge,
        "gravy": gravy, "solubility": solubility,
        "count": lambda a: seq.count(a),
        "single_mutation": False, "score_delta": 0.0,
    }
    valid = _eval_validate(challenge["validate"], ctx)

    if valid:
        record_completion(user_id, challenge.get("date", _today()), int(challenge["xp"]), sequence)

    return {
        "challenge": challenge,
        "valid": valid,
        "metrics": {
            "len": L, "no_cys": no_cys, "score": round(score, 3),
            "net_charge": net_charge, "gravy": round(gravy, 3),
            "solubility": round(solubility, 3),
        },
        "awarded_xp": challenge["xp"] if valid else 0,
    }


def record_completion(user_id: str, challenge_date: str, xp: int, sequence: str) -> None:
    c = _db()
    try:
        with c:
            c.execute(
                "INSERT OR IGNORE INTO completions (user_id, challenge_date, xp, ts, sequence) VALUES (?,?,?,?,?)",
                (user_id, challenge_date, xp, time.time(), sequence),
            )
            row = c.execute("SELECT total_xp, current_streak, longest_streak, last_active FROM user_xp WHERE user_id=?", (user_id,)).fetchone()
            today = challenge_date
            if row is None:
                c.execute(
                    "INSERT INTO user_xp (user_id, total_xp, current_streak, longest_streak, last_active) VALUES (?,?,?,?,?)",
                    (user_id, xp, 1, 1, today),
                )
            else:
                total, cur, longest, last = row
                yesterday = (datetime.date.fromisoformat(today) - datetime.timedelta(days=1)).isoformat()
                if last == yesterday:
                    cur += 1
                elif last == today:
                    pass
                else:
                    cur = 1
                longest = max(longest, cur)
                c.execute(
                    "UPDATE user_xp SET total_xp=total_xp+?, current_streak=?, longest_streak=?, last_active=? WHERE user_id=?",
                    (xp, cur, longest, today, user_id),
                )
    finally:
        c.close()


def leaderboard_top(n: int = 20) -> List[Dict[str, Any]]:
    c = _db()
    try:
        rows = c.execute(
            "SELECT user_id, total_xp, current_streak, longest_streak, last_active FROM user_xp ORDER BY total_xp DESC LIMIT ?",
            (n,),
        ).fetchall()
    finally:
        c.close()
    return [
        {"user_id": r[0], "total_xp": r[1], "current_streak": r[2], "longest_streak": r[3], "last_active": r[4]}
        for r in rows
    ]
