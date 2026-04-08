"""UniProt REST search — full-text query, returns hits with accession + name + sequence."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


_BASE = "https://rest.uniprot.org/uniprotkb"


def _http(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "OpenDNA/0.5.0"})
    return urllib.request.urlopen(req, timeout=20).read().decode()


def uniprot_search(
    query: str,
    size: int = 25,
    reviewed_only: bool = True,
    organism: Optional[str] = None,
) -> Dict[str, Any]:
    """Search UniProt by free text. Examples:
        'blood'
        'brain cancer'
        'hemoglobin human'
        'gene:TP53 AND organism_id:9606'
    """
    q = query
    if reviewed_only:
        q = f"({q}) AND reviewed:true"
    if organism:
        q = f"({q}) AND organism_name:{organism}"
    fields = "accession,id,protein_name,gene_names,organism_name,length,sequence,annotation_score,cc_function"
    params = {"query": q, "format": "json", "size": str(size), "fields": fields}
    url = f"{_BASE}/search?{urllib.parse.urlencode(params)}"
    data = json.loads(_http(url))
    hits: List[Dict[str, Any]] = []
    for r in data.get("results", []):
        protein_names = r.get("proteinDescription", {}) or {}
        rec_name = protein_names.get("recommendedName", {}).get("fullName", {}).get("value", "")
        gene = ""
        genes = r.get("genes", [])
        if genes:
            gene = (genes[0].get("geneName", {}) or {}).get("value", "")
        org = ((r.get("organism") or {}).get("scientificName")) or ""
        seq = ((r.get("sequence") or {}).get("value")) or ""
        functions: List[str] = []
        for c in r.get("comments", []) or []:
            if c.get("commentType") == "FUNCTION":
                for t in c.get("texts", []) or []:
                    if t.get("value"):
                        functions.append(t["value"])
        hits.append({
            "accession": r.get("primaryAccession"),
            "id": r.get("uniProtkbId"),
            "name": rec_name,
            "gene": gene,
            "organism": org,
            "length": (r.get("sequence") or {}).get("length"),
            "sequence": seq,
            "annotation_score": r.get("annotationScore"),
            "function": " ".join(functions)[:600] if functions else "",
        })
    return {
        "query": query,
        "total": data.get("results", []) and len(data["results"]),
        "hits": hits,
    }


def uniprot_fetch_sequence(accession: str) -> Dict[str, Any]:
    url = f"{_BASE}/{accession}.fasta"
    txt = _http(url)
    lines = txt.splitlines()
    header = lines[0] if lines else ""
    seq = "".join(line for line in lines[1:] if not line.startswith(">"))
    return {"accession": accession, "header": header, "sequence": seq, "length": len(seq)}
