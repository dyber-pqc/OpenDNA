"""AlphaFold DB direct fetcher.

Pulls predicted structures and metadata straight from EBI's AlphaFold DB
without requiring a local model. Designed for quick lookups by UniProt
accession.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict


_PDB_URL = "https://alphafold.ebi.ac.uk/files/AF-{acc}-F1-model_v4.pdb"
_META_URL = "https://alphafold.ebi.ac.uk/api/prediction/{acc}"


def _http(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "OpenDNA/0.5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode()


def fetch_alphafold(uniprot_id: str) -> Dict[str, Any]:
    """Fetch AlphaFold-predicted PDB for a UniProt accession.

    Returns: {"uniprot_id", "pdb", "source": "alphafold-db"}
    """
    acc = uniprot_id.strip().upper()
    pdb = _http(_PDB_URL.format(acc=acc))
    return {"uniprot_id": acc, "pdb": pdb, "source": "alphafold-db"}


def fetch_alphafold_meta(uniprot_id: str) -> Dict[str, Any]:
    """Fetch PDB plus the prediction metadata blob from the AF DB API."""
    base = fetch_alphafold(uniprot_id)
    try:
        meta_raw = _http(_META_URL.format(acc=base["uniprot_id"]))
        base["meta"] = json.loads(meta_raw)
    except Exception as e:  # noqa: BLE001
        base["meta"] = None
        base["meta_error"] = str(e)
    return base
