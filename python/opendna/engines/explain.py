"""LLM-powered explanation engine. Uses Ollama if available."""

from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"


def explain_protein(
    sequence: str,
    properties: dict,
    score: dict,
    structure_info: Optional[dict] = None,
) -> str:
    """Generate a plain-English explanation of a protein."""
    llm_response = _try_ollama_explain(sequence, properties, score, structure_info)
    if llm_response:
        return llm_response
    return _heuristic_explain(sequence, properties, score, structure_info)


def _try_ollama_explain(
    sequence: str,
    properties: dict,
    score: dict,
    structure_info: Optional[dict],
) -> Optional[str]:
    try:
        with httpx.Client(timeout=2.0) as client:
            health = client.get(f"{OLLAMA_URL}/api/tags")
            if health.status_code != 200:
                return None
    except Exception:
        return None

    context = (
        f"Protein sequence (first 50 of {len(sequence)} residues): {sequence[:50]}...\n"
        f"Molecular weight: {properties.get('molecular_weight')} Da\n"
        f"Isoelectric point (pI): {properties.get('isoelectric_point')}\n"
        f"GRAVY hydropathy: {properties.get('gravy')}\n"
        f"Stability: {properties.get('classification')}\n"
        f"Overall quality score: {score.get('overall')}\n"
    )
    if structure_info:
        context += f"Mean pLDDT confidence: {structure_info.get('mean_confidence')}\n"
        context += f"Helix: {structure_info.get('helix_pct')}%, "
        context += f"Strand: {structure_info.get('strand_pct')}%, "
        context += f"Coil: {structure_info.get('coil_pct')}%\n"

    prompt = (
        "You are a friendly protein biochemistry expert. Explain the following protein "
        "to a curious high school student in 3-4 paragraphs. Cover: what kind of protein "
        "it might be, its key properties, what its likely function could be based on size "
        "and composition, and what someone could do with it. Use plain English and be "
        "engaging.\n\n"
        f"PROTEIN DATA:\n{context}"
    )

    try:
        with httpx.Client(timeout=60.0) as client:
            r = client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            if r.status_code != 200:
                return None
            return r.json().get("message", {}).get("content", "")
    except Exception as e:
        logger.debug(f"Ollama explain failed: {e}")
        return None


def _heuristic_explain(
    sequence: str,
    properties: dict,
    score: dict,
    structure_info: Optional[dict],
) -> str:
    """Fallback explanation when Ollama unavailable."""
    n = len(sequence)
    mw = properties.get("molecular_weight", 0)
    pi = properties.get("isoelectric_point", 7)
    gravy = properties.get("gravy", 0)
    stability = properties.get("classification", "unknown")

    parts = []

    # Size class
    if n < 50:
        size = "a small peptide, often used as a hormone, signal, or short functional motif"
    elif n < 150:
        size = "a small protein domain, like a single binding pocket or compact enzyme"
    elif n < 300:
        size = "a typical-sized protein, large enough to have a complete fold and function"
    elif n < 500:
        size = "a medium-large protein, possibly with multiple domains"
    else:
        size = "a large multi-domain protein, often a complex enzyme or scaffold"

    parts.append(
        f"This protein has {n} amino acids ({mw:.0f} Da), making it {size}."
    )

    # Charge
    if pi < 5:
        charge_desc = "highly acidic — it carries strong negative charges at physiological pH, typical of nucleic-acid-binding or calcium-binding proteins"
    elif pi < 6.5:
        charge_desc = "slightly acidic — common for many cytoplasmic enzymes"
    elif pi < 8:
        charge_desc = "near-neutral, like many soluble proteins"
    elif pi < 9.5:
        charge_desc = "slightly basic — common for ribosomal proteins and DNA-binding factors"
    else:
        charge_desc = "highly basic, suggesting strong DNA/RNA-binding activity (histones, ribosomal proteins)"

    parts.append(f"Its isoelectric point is {pi:.2f}, meaning it is {charge_desc}.")

    # Hydropathy
    if gravy < -0.5:
        hyd = "very hydrophilic — likely a soluble protein that lives in water (cytoplasm or extracellular)"
    elif gravy < 0:
        hyd = "moderately hydrophilic — typical soluble protein"
    elif gravy < 0.5:
        hyd = "moderately hydrophobic — possibly contains a buried core or membrane-adjacent regions"
    else:
        hyd = "highly hydrophobic — likely a transmembrane or lipid-binding protein"

    parts.append(f"With a GRAVY score of {gravy:.2f}, this protein is {hyd}.")

    # Stability
    parts.append(
        f"It is classified as {stability} based on its instability index. "
        f"{'It should express well in standard hosts.' if stability == 'stable' else 'It may be challenging to produce in soluble form.'}"
    )

    # Structure
    if structure_info:
        helix = structure_info.get("helix_pct", 0)
        strand = structure_info.get("strand_pct", 0)
        if helix > 50:
            ss_desc = "predominantly alpha-helical (like myoglobin or many transcription factors)"
        elif strand > 30:
            ss_desc = "rich in beta-sheets (like immunoglobulin domains or beta-barrels)"
        else:
            ss_desc = "a mix of helices, strands, and loops"
        parts.append(
            f"Structurally, it is {ss_desc} ({helix:.0f}% helix, {strand:.0f}% strand)."
        )

    # Score
    overall = score.get("overall", 0) * 100
    parts.append(
        f"Its overall computational quality score is {overall:.0f}/100, "
        f"reflecting a balance of predicted stability, solubility, and developability."
    )

    parts.append(
        "Note: Install Ollama and run `ollama pull llama3.2:3b` for richer AI-powered explanations."
    )

    return "\n\n".join(parts)
