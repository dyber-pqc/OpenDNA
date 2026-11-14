"""Paper extractor: scan scientific text for protein references.

Finds FASTA blocks, UniProt accessions, PDB IDs, and inline protein sequences.
Returns a structured list of extraction dicts suitable for UI display.
"""
from __future__ import annotations

import re
from typing import List, Dict

# UniProt accession regex (official spec).
UNIPROT_RE = re.compile(
    r"\b([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})\b"
)

# PDB ID: 4 chars starting with a digit.
PDB_RE = re.compile(r"\b([0-9][A-Za-z0-9]{3})\b")

# Amino acid set used for inline-sequence detection.
AA_SET = set("ACDEFGHIKLMNPQRSTVWY")
AA_RE = re.compile(r"[ACDEFGHIKLMNPQRSTVWY]{15,}")

_MIN_INLINE_LEN = 15


def _context(text: str, start: int, end: int, pad: int = 60) -> str:
    s = max(0, start - pad)
    e = min(len(text), end + pad)
    snippet = text[s:e].replace("\n", " ").strip()
    return re.sub(r"\s+", " ", snippet)


def _extract_fasta_blocks(text: str) -> List[Dict]:
    out: List[Dict] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(">"):
            header = line[1:].strip()
            seq_lines: List[str] = []
            j = i + 1
            while j < len(lines) and not lines[j].startswith(">"):
                stripped = lines[j].strip()
                if stripped and all(ch.upper() in AA_SET or ch in " \t" for ch in stripped):
                    seq_lines.append(stripped.replace(" ", "").replace("\t", ""))
                elif not stripped:
                    pass
                else:
                    break
                j += 1
            seq = "".join(seq_lines).upper()
            if len(seq) >= 5:
                out.append(
                    {
                        "type": "fasta",
                        "value": seq,
                        "context": f">{header}",
                    }
                )
            i = j
        else:
            i += 1
    return out


def _extract_uniprot(text: str) -> List[Dict]:
    seen = set()
    out: List[Dict] = []
    for m in UNIPROT_RE.finditer(text):
        acc = m.group(1)
        if acc in seen:
            continue
        seen.add(acc)
        out.append(
            {
                "type": "uniprot",
                "value": acc,
                "context": _context(text, m.start(), m.end()),
            }
        )
    return out


def _extract_pdb(text: str) -> List[Dict]:
    seen = set()
    out: List[Dict] = []
    for m in PDB_RE.finditer(text):
        pdb_id = m.group(1).upper()
        if pdb_id in seen:
            continue
        ctx = _context(text, m.start(), m.end(), pad=80).lower()
        if "pdb" not in ctx and "structure" not in ctx:
            continue
        seen.add(pdb_id)
        out.append(
            {
                "type": "pdb",
                "value": pdb_id,
                "context": _context(text, m.start(), m.end(), pad=80),
            }
        )
    return out


def _extract_inline_sequences(text: str, already: List[Dict]) -> List[Dict]:
    # Exclude regions already consumed by FASTA blocks.
    fasta_seqs = {d["value"] for d in already if d["type"] == "fasta"}
    out: List[Dict] = []
    seen = set()
    for m in AA_RE.finditer(text):
        seq = m.group(0).upper()
        if len(seq) < _MIN_INLINE_LEN:
            continue
        if seq in seen:
            continue
        if any(seq in fs or fs in seq for fs in fasta_seqs):
            continue
        # Skip runs that look like words (require reasonable diversity).
        uniq = len(set(seq))
        if uniq < 5:
            continue
        seen.add(seq)
        out.append(
            {
                "type": "sequence",
                "value": seq,
                "context": _context(text, m.start(), m.end()),
            }
        )
    return out


def extract_sequences_from_text(text: str) -> List[Dict]:
    """Scan text for protein references and return extraction dicts.

    Each entry has keys: type (fasta|uniprot|pdb|sequence), value, context.
    """
    if not text:
        return []
    results: List[Dict] = []
    results.extend(_extract_fasta_blocks(text))
    results.extend(_extract_uniprot(text))
    results.extend(_extract_pdb(text))
    results.extend(_extract_inline_sequences(text, results))
    return results


def extract_from_pdf_bytes(data: bytes) -> str:
    """Try to extract plain text from a PDF byte blob. Returns '' on failure."""
    try:
        import io

        import pypdf  # type: ignore

        reader = pypdf.PdfReader(io.BytesIO(data))
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pages.append("")
        return "\n".join(pages)
    except Exception:
        return ""
