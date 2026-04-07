"""Tool definitions for LLM function calling.

Each tool maps a high-level capability to one or more OpenDNA functions.
The LLM can call these tools to perform actions like fold, score, design, etc.
"""

from __future__ import annotations

from typing import Any, Callable


# Tool schemas in OpenAI function-calling format
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "fold_protein",
            "description": "Predict the 3D structure of a protein from its amino acid sequence using ESMFold. Use this when the user wants to fold or predict the structure of a sequence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {
                        "type": "string",
                        "description": "The amino acid sequence in single-letter code",
                    },
                },
                "required": ["sequence"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "score_protein",
            "description": "Compute a quick quality score for a protein sequence (stability, solubility, immunogenicity, developability).",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "string", "description": "The amino acid sequence"},
                },
                "required": ["sequence"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_protein",
            "description": "Run the comprehensive analysis suite: properties, Lipinski, hydropathy, disorder, transmembrane, signal peptide, aggregation, PTM sites, and (if structure provided) secondary structure, Ramachandran, pockets, bonds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "string"},
                    "include_structure": {"type": "boolean", "description": "Whether to fold first"},
                },
                "required": ["sequence"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "design_sequences",
            "description": "Generate alternative protein sequences for a given backbone using ESM-IF1 inverse folding. Requires a folded structure first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "string", "description": "Starting sequence to design alternatives for"},
                    "num_candidates": {"type": "integer", "description": "How many alternatives", "default": 10},
                },
                "required": ["sequence"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "iterative_design",
            "description": "Run an automated optimization loop: fold→design→fold→keep best→repeat. Best for improving an existing protein over multiple rounds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "string"},
                    "n_rounds": {"type": "integer", "default": 3},
                    "candidates_per_round": {"type": "integer", "default": 5},
                },
                "required": ["sequence"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mutate_protein",
            "description": "Apply a point mutation to a protein in standard format (e.g. K48R = mutate Lysine at position 48 to Arginine).",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "string"},
                    "mutation": {"type": "string", "description": "Mutation in format like K48R"},
                },
                "required": ["sequence", "mutation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predict_ddg",
            "description": "Predict the stability change (ΔΔG in kcal/mol) of a point mutation. Negative = destabilizing, positive = stabilizing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "string"},
                    "mutation": {"type": "string"},
                },
                "required": ["sequence", "mutation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "import_uniprot",
            "description": "Fetch a protein from UniProt by accession (e.g. P0CG48) or famous name (e.g. ubiquitin, insulin, gfp, p53, kras). Also fetches AlphaFold structure if available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name_or_id": {"type": "string"},
                },
                "required": ["name_or_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_structure",
            "description": "Run MolProbity-style validation on a folded structure: Ramachandran outliers, steric clashes, bond geometry, quality grade.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "string"},
                },
                "required": ["sequence"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_cdrs",
            "description": "Detect antibody Complementarity-Determining Regions (CDRs) using Kabat or Chothia numbering. Use for antibody sequences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "string"},
                    "scheme": {"type": "string", "enum": ["kabat", "chothia"], "default": "kabat"},
                },
                "required": ["sequence"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predict_pka",
            "description": "Predict pKa values for ionizable residues in a folded structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "string"},
                },
                "required": ["sequence"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "conservation_scores",
            "description": "Compute per-residue conservation using ESM language model perplexity. Higher score = more conserved.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "string"},
                },
                "required": ["sequence"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_cost",
            "description": "Estimate the cost to chemically synthesize this protein (Twist Bioscience, IDT, GenScript) and the carbon footprint.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "string"},
                },
                "required": ["sequence"],
            },
        },
    },
]


# Tool execution dispatch
def execute_tool(name: str, arguments: dict) -> dict:
    """Execute a tool call and return its result."""
    try:
        if name == "fold_protein":
            from opendna.engines.folding import fold
            r = fold(arguments["sequence"])
            return {
                "status": "ok",
                "mean_confidence": r.mean_confidence,
                "explanation": r.explanation,
                "pdb_size_bytes": len(r.pdb_string),
            }

        elif name == "score_protein":
            from opendna.engines.scoring import evaluate
            r = evaluate(arguments["sequence"])
            return {
                "overall": r.overall,
                "summary": r.summary,
                "breakdown": {
                    "stability": r.breakdown.stability,
                    "solubility": r.breakdown.solubility,
                    "immunogenicity": r.breakdown.immunogenicity,
                    "developability": r.breakdown.developability,
                },
            }

        elif name == "analyze_protein":
            from opendna.engines.analysis import compute_properties, lipinski_rule_of_five
            from opendna.engines.disorder import predict_disorder
            seq = arguments["sequence"]
            props = compute_properties(seq)
            ro5 = lipinski_rule_of_five(seq)
            dis = predict_disorder(seq)
            return {
                "molecular_weight": props.molecular_weight,
                "isoelectric_point": props.isoelectric_point,
                "gravy": props.gravy,
                "stability": props.classification,
                "lipinski_passes": ro5.passes_ro5,
                "disorder_pct": dis["disorder_percent"],
                "n_disordered_regions": len(dis["regions"]),
            }

        elif name == "mutate_protein":
            from opendna.engines.design import apply_mutation
            new_seq = apply_mutation(arguments["sequence"], arguments["mutation"])
            return {"original": arguments["sequence"], "mutated": new_seq}

        elif name == "predict_ddg":
            from opendna.engines.predictors import predict_ddg as p_ddg
            return p_ddg(arguments["sequence"], arguments["mutation"])

        elif name == "import_uniprot":
            from opendna.data.sources import fetch_uniprot, fetch_alphafold, FAMOUS_PROTEINS
            name_or_id = arguments["name_or_id"]
            if name_or_id.lower() in FAMOUS_PROTEINS:
                name_or_id = FAMOUS_PROTEINS[name_or_id.lower()]
            entry = fetch_uniprot(name_or_id)
            if not entry:
                return {"error": "Not found"}
            af = fetch_alphafold(name_or_id)
            return {
                "name": entry.name,
                "length": entry.length,
                "organism": entry.organism,
                "description": entry.description,
                "sequence_preview": entry.sequence[:60] + "...",
                "has_alphafold": af is not None,
            }

        elif name == "find_cdrs":
            from opendna.engines.antibody import find_cdrs
            return find_cdrs(arguments["sequence"], arguments.get("scheme", "kabat"))

        elif name == "conservation_scores":
            from opendna.engines.conservation import analyze_conservation
            r = analyze_conservation(arguments["sequence"])
            return {
                "method": r.method,
                "most_conserved_positions": r.most_conserved,
                "most_variable_positions": r.most_variable,
            }

        elif name == "estimate_cost":
            from opendna.data.synthesis import estimate_synthesis_cost, estimate_carbon, estimate_compute_time
            seq = arguments["sequence"]
            cost = estimate_synthesis_cost(seq)
            time = estimate_compute_time(len(seq), "fold", "cpu")
            carbon = estimate_carbon("fold", time, "cpu")
            return {
                "cheapest_vendor": cost.cheapest_vendor,
                "cheapest_price_usd": cost.cheapest_price,
                "twist": cost.twist_bioscience_usd,
                "idt": cost.idt_usd,
                "genscript": cost.genscript_usd,
                "co2_equivalent": carbon.equivalent,
            }

        elif name == "design_sequences":
            return {"status": "queued", "note": "Design is a long-running job; submit via /v1/design"}

        elif name == "iterative_design":
            return {"status": "queued", "note": "Iterative design is a long-running job; submit via /v1/iterative_design"}

        elif name == "validate_structure":
            return {"status": "needs_pdb", "note": "Validation requires the folded structure"}

        elif name == "predict_pka":
            return {"status": "needs_pdb", "note": "pKa prediction requires the folded structure"}

        else:
            return {"error": f"Unknown tool: {name}"}

    except Exception as e:
        return {"error": str(e)}
