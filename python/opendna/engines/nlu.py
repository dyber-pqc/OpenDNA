"""Natural language understanding for OpenDNA chat.

Tries Ollama for real LLM, falls back to a deterministic command parser.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:1b"  # Small, fast


@dataclass
class Intent:
    action: str  # fold | score | design | mutate | explain | help | unknown
    sequence: Optional[str] = None
    mutation: Optional[str] = None
    target: Optional[str] = None
    raw: str = ""
    response: str = ""


def parse_intent(message: str) -> Intent:
    """Parse user intent. Tries Ollama first, falls back to regex."""
    intent = _try_ollama(message)
    if intent is not None:
        return intent
    return _fallback_parser(message)


def _try_ollama(message: str) -> Optional[Intent]:
    """Try to use a local Ollama LLM for intent parsing."""
    try:
        with httpx.Client(timeout=2.0) as client:
            health = client.get(f"{OLLAMA_URL}/api/tags")
            if health.status_code != 200:
                return None
    except Exception:
        return None

    system_prompt = (
        "You are an intent parser for OpenDNA, a protein engineering tool. "
        "Given a user message, output a JSON object with these fields:\n"
        "  action: one of [fold, score, design, mutate, explain, help, unknown]\n"
        "  sequence: extracted protein sequence if any (uppercase amino acid letters)\n"
        "  mutation: extracted mutation in format like 'G45D' if any\n"
        "  response: a brief friendly reply\n"
        "Only output valid JSON, no other text."
    )

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message},
                    ],
                    "stream": False,
                    "format": "json",
                },
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            parsed = json.loads(content)
            return Intent(
                action=parsed.get("action", "unknown"),
                sequence=parsed.get("sequence"),
                mutation=parsed.get("mutation"),
                target=parsed.get("target"),
                raw=message,
                response=parsed.get("response", ""),
            )
    except Exception as e:
        logger.debug(f"Ollama parse failed: {e}")
        return None


def _fallback_parser(message: str) -> Intent:
    """Deterministic regex-based intent parser."""
    text = message.strip()
    lower = text.lower()

    # Extract sequence (long uppercase amino acid stretch)
    seq_match = re.search(r"\b([ACDEFGHIKLMNPQRSTVWY]{6,})\b", text.upper())
    sequence = seq_match.group(1) if seq_match else None

    # Extract mutation
    mut_match = re.search(r"\b([A-Z]\d+[A-Z])\b", text.upper())
    mutation = mut_match.group(1) if mut_match else None

    if lower.startswith("help") or "what can you" in lower or "commands" in lower:
        return Intent(
            action="help",
            raw=message,
            response=(
                "I can help you with: \n"
                "  - 'fold <SEQUENCE>' -- predict 3D structure\n"
                "  - 'score <SEQUENCE>' -- evaluate protein quality\n"
                "  - 'design <PDB>' -- design new sequences (needs structure)\n"
                "  - 'mutate G45D' -- apply a mutation to current protein\n"
                "  - 'explain' -- explain the current result\n"
                "Tip: install Ollama with 'llama3.2:1b' for natural language."
            ),
        )

    if lower.startswith("fold ") or "fold this" in lower or lower.startswith("predict "):
        return Intent(
            action="fold",
            sequence=sequence,
            raw=message,
            response=f"Folding sequence ({len(sequence) if sequence else '?'} residues)..." if sequence else "Please provide a sequence to fold.",
        )

    if lower.startswith("score ") or "evaluate" in lower or "rate" in lower:
        return Intent(
            action="score",
            sequence=sequence,
            raw=message,
            response="Scoring..." if sequence else "Please provide a sequence to score.",
        )

    if lower.startswith("design") or "redesign" in lower:
        return Intent(
            action="design",
            raw=message,
            response="Design needs a structure. Fold something first or upload a PDB.",
        )

    if "mutate" in lower or "mutation" in lower or mutation:
        return Intent(
            action="mutate",
            mutation=mutation,
            raw=message,
            response=f"Applying mutation {mutation}..." if mutation else "Specify a mutation like 'G45D'.",
        )

    if "explain" in lower or "why" in lower or "what does" in lower:
        return Intent(
            action="explain",
            raw=message,
            response="I'll explain the current result. (LLM coming soon - install Ollama for richer responses.)",
        )

    if sequence:
        return Intent(
            action="fold",
            sequence=sequence,
            raw=message,
            response=f"I see a sequence. Folding it ({len(sequence)} residues)...",
        )

    return Intent(
        action="unknown",
        raw=message,
        response=(
            "I'm not sure what you mean. Try: 'fold MKTVRQERLK', 'score MKTVRQERLK', "
            "'mutate G45D', or 'help'."
        ),
    )
