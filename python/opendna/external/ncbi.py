"""NCBI E-utilities + PubMed search/summarization."""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_API_KEY = os.environ.get("NCBI_API_KEY")  # optional, raises rate limit


def _http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "OpenDNA/0.5.0"})
    return urllib.request.urlopen(req, timeout=15).read().decode()


def _add_key(params: Dict[str, str]) -> Dict[str, str]:
    if _API_KEY:
        params["api_key"] = _API_KEY
    return params


def ncbi_search(db: str, term: str, retmax: int = 20) -> Dict[str, Any]:
    """eSearch on any NCBI db (nuccore, protein, gene, etc.). Returns id list."""
    params = _add_key({"db": db, "term": term, "retmax": str(retmax), "retmode": "json"})
    url = f"{_BASE}/esearch.fcgi?{urllib.parse.urlencode(params)}"
    data = json.loads(_http_get(url))
    return {
        "db": db,
        "term": term,
        "ids": data.get("esearchresult", {}).get("idlist", []),
        "count": int(data.get("esearchresult", {}).get("count", "0")),
    }


def ncbi_fetch(db: str, id_: str, rettype: str = "fasta") -> Dict[str, Any]:
    """eFetch — pull a single record by id."""
    params = _add_key({"db": db, "id": id_, "rettype": rettype, "retmode": "text"})
    url = f"{_BASE}/efetch.fcgi?{urllib.parse.urlencode(params)}"
    text = _http_get(url)
    return {"db": db, "id": id_, "rettype": rettype, "text": text}


def pubmed_search(query: str, retmax: int = 20) -> Dict[str, Any]:
    return ncbi_search("pubmed", query, retmax)


def pubmed_summarize(pmid: str) -> Dict[str, Any]:
    """eSummary for a PubMed id — returns title, authors, abstract, journal, year."""
    params = _add_key({"db": "pubmed", "id": pmid, "retmode": "json"})
    summary_url = f"{_BASE}/esummary.fcgi?{urllib.parse.urlencode(params)}"
    s = json.loads(_http_get(summary_url)).get("result", {}).get(pmid, {})
    # Pull abstract via efetch
    abs_params = _add_key({"db": "pubmed", "id": pmid, "rettype": "abstract", "retmode": "text"})
    abs_text = _http_get(f"{_BASE}/efetch.fcgi?{urllib.parse.urlencode(abs_params)}")
    return {
        "pmid": pmid,
        "title": s.get("title", ""),
        "authors": [a.get("name") for a in s.get("authors", [])],
        "journal": s.get("fulljournalname", ""),
        "year": (s.get("pubdate", "") or "").split(" ")[0],
        "doi": next((a.get("value") for a in s.get("articleids", []) if a.get("idtype") == "doi"), None),
        "abstract": abs_text,
    }
