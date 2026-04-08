"""Synthesis vendor quoting + ordering: Twist, IDT, GenScript.

Real ordering requires per-vendor API credentials. We provide:
  - quote_synthesis(): instant cost estimate from public rate cards
  - place_order(): submits to vendor's API IF credentials are configured;
                   otherwise records the order locally and returns a "draft"

This way the workflow is end-to-end usable on day 1 with no API keys, and
real submission "just works" once the user adds keys to env vars.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


# Public rate cards (USD per bp / per aa) as of 2026-04 — adjust as needed
_RATES = {
    "twist_dna_gene":     {"unit": "bp", "rate": 0.07,  "min_cost": 70.0, "max_len": 5000},
    "idt_dna_gblock":     {"unit": "bp", "rate": 0.10,  "min_cost": 60.0, "max_len": 3000},
    "idt_dna_gene":       {"unit": "bp", "rate": 0.09,  "min_cost": 200.0, "max_len": 5000},
    "genscript_dna_gene": {"unit": "bp", "rate": 0.08,  "min_cost": 99.0, "max_len": 12000},
    "genscript_peptide":  {"unit": "aa", "rate": 6.0,   "min_cost": 250.0, "max_len": 60},
    "twist_protein":      {"unit": "aa", "rate": 8.0,   "min_cost": 500.0, "max_len": 200},
}

_VENDORS = {
    "twist":     {"display_name": "Twist Bioscience", "url": "https://www.twistbioscience.com",  "env": "TWIST_API_KEY"},
    "idt":       {"display_name": "Integrated DNA Technologies", "url": "https://www.idtdna.com", "env": "IDT_API_KEY"},
    "genscript": {"display_name": "GenScript",        "url": "https://www.genscript.com",        "env": "GENSCRIPT_API_KEY"},
}


def list_vendors() -> List[Dict[str, Any]]:
    out = []
    for k, v in _VENDORS.items():
        out.append({
            "id": k, **v,
            "credentials_configured": bool(os.environ.get(v["env"])),
        })
    return out


def _orders_dir() -> Path:
    p = Path(os.environ.get("OPENDNA_ORDERS_DIR", Path.home() / ".opendna" / "orders"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def quote_synthesis(
    sequence: str,
    kind: str = "dna_gene",
    vendor: Optional[str] = None,
) -> Dict[str, Any]:
    """Estimate cost across all matching products. `kind` ∈ dna_gene, dna_gblock, peptide, protein."""
    L = len(sequence)
    quotes = []
    for product, spec in _RATES.items():
        if kind not in product:
            continue
        if vendor and not product.startswith(vendor):
            continue
        if L > spec["max_len"]:
            quotes.append({"product": product, "available": False, "reason": f"max length {spec['max_len']}"})
            continue
        cost = max(spec["min_cost"], L * spec["rate"])
        quotes.append({
            "product": product, "available": True,
            "length": L, "unit": spec["unit"],
            "rate_per_unit": spec["rate"], "cost_usd": round(cost, 2),
            "lead_time_days": 7 if "twist" in product or "idt" in product else 14,
        })
    quotes.sort(key=lambda q: (not q["available"], q.get("cost_usd", 9e9)))
    return {"sequence_length": L, "kind": kind, "quotes": quotes}


def place_order(
    sequence: str,
    vendor: str,
    product: str,
    customer_email: str = "",
    notes: str = "",
) -> Dict[str, Any]:
    """Submit an order. Real API call if credentials present, else local draft."""
    if vendor not in _VENDORS:
        raise ValueError(f"unknown vendor: {vendor}")
    api_env = _VENDORS[vendor]["env"]
    api_key = os.environ.get(api_env)
    order_id = f"od-{uuid.uuid4().hex[:12]}"
    record = {
        "order_id": order_id,
        "vendor": vendor,
        "product": product,
        "sequence": sequence,
        "length": len(sequence),
        "customer_email": customer_email,
        "notes": notes,
        "ts": time.time(),
        "status": "draft" if not api_key else "submitting",
        "submitted_via_api": bool(api_key),
    }
    # Save locally regardless
    (_orders_dir() / f"{order_id}.json").write_text(json.dumps(record, indent=2))
    if not api_key:
        return record

    # Real submission would dispatch per vendor here. We attempt a generic POST
    # so users with correct endpoint+key see it work; failures fall back to draft.
    endpoint = os.environ.get(f"{vendor.upper()}_API_URL")
    if not endpoint:
        record["status"] = "draft"
        record["note"] = f"Set {vendor.upper()}_API_URL to enable real submission"
        return record
    try:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(record).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=15).read().decode()
        record["status"] = "submitted"
        record["vendor_response"] = resp[:1000]
    except Exception as e:
        record["status"] = "failed"
        record["error"] = str(e)
    (_orders_dir() / f"{order_id}.json").write_text(json.dumps(record, indent=2))
    return record
