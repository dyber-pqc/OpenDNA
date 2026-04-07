"""Data sources: UniProt, PDB, AlphaFold DB."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class UniProtEntry:
    accession: str
    name: str
    sequence: str
    organism: str
    length: int
    description: str


def fetch_uniprot(accession: str, timeout: float = 15.0) -> Optional[UniProtEntry]:
    """Fetch a UniProt entry by accession (e.g. 'P0CG48' for ubiquitin)."""
    url = f"https://rest.uniprot.org/uniprotkb/{accession}.json"
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(url)
            if r.status_code != 200:
                return None
            data = r.json()
    except Exception as e:
        logger.warning(f"UniProt fetch failed: {e}")
        return None

    sequence = data.get("sequence", {}).get("value", "")
    organism = data.get("organism", {}).get("scientificName", "Unknown")
    name = data.get("uniProtkbId", accession)

    desc_parts = []
    protein = data.get("proteinDescription", {})
    rec = protein.get("recommendedName", {})
    if rec:
        full = rec.get("fullName", {}).get("value")
        if full:
            desc_parts.append(full)

    return UniProtEntry(
        accession=accession,
        name=name,
        sequence=sequence,
        organism=organism,
        length=len(sequence),
        description="; ".join(desc_parts) or "No description",
    )


def fetch_pdb(pdb_id: str, timeout: float = 15.0) -> Optional[str]:
    """Fetch a PDB file by ID (e.g. '1UBQ' for ubiquitin)."""
    url = f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(url)
            if r.status_code != 200:
                return None
            return r.text
    except Exception as e:
        logger.warning(f"PDB fetch failed: {e}")
        return None


def fetch_alphafold(uniprot_id: str, timeout: float = 30.0) -> Optional[str]:
    """Fetch an AlphaFold DB predicted structure for a UniProt accession.

    Uses the AlphaFold DB API to find the latest model version, then downloads
    the PDB file. Returns None if no structure exists for this entry.
    """
    api_url = f"https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}"
    try:
        with httpx.Client(timeout=timeout) as client:
            api_r = client.get(api_url)
            if api_r.status_code != 200:
                return None
            data = api_r.json()
            if not isinstance(data, list) or len(data) == 0:
                return None
            entry = data[0]
            pdb_url = entry.get("pdbUrl")
            if not pdb_url:
                return None
            pdb_r = client.get(pdb_url)
            if pdb_r.status_code != 200:
                return None
            return pdb_r.text
    except Exception as e:
        logger.warning(f"AlphaFold fetch failed for {uniprot_id}: {e}")
        return None


# Common famous proteins for quick access
FAMOUS_PROTEINS = {
    "ubiquitin": "P0CG48",
    "insulin": "P01308",
    "gfp": "P42212",
    "lysozyme": "P00698",
    "myoglobin": "P02185",
    "hemoglobin_alpha": "P69905",
    "p53": "P04637",
    "spike_covid": "P0DTC2",
    "kras": "P01116",
    "egfr": "P00533",
    "her2": "P04626",
    "trypsin": "P00760",
    "bsa": "P02769",
    "actin": "P60709",
    "tubulin": "P68363",
}
