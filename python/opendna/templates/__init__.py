"""Project templates for OpenDNA.

Each template is a ready-to-run starting point for a common protein engineering
scenario. A template bundles:
  - a starter sequence (amino acids) and/or a PDB id to fetch
  - a workflow YAML string (format compatible with the visual WorkflowEditor)
  - pedagogy metadata (academy level, tags)

Templates are instantiated by the API -- see ``/v1/templates/...`` in
``opendna.api.server``.  Instantiating a template creates a workspace project
pre-populated with the starter data and the workflow graph so the user can
immediately click "Run".
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Starter sequences
# ---------------------------------------------------------------------------
# KRAS G12D (human) -- the most common oncogenic KRAS mutation.  Sequence below
# is the canonical KRAS4B (UniProt P01116-2) with G12D applied.
KRAS_G12D = (
    "MTEYKLVVVGADGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQ"
    "YMRTGEGFLCVFAINNTKSFEDIHHYREQIKRVKDSEDVPMVLVGNKCDLPSRTVDTKQAQDLARSYGIP"
    "FIETSAKTRQGVDDAFYTLVREIRKHKEKMSKDGKKKKKKSKTKCVIM"
)

# Trastuzumab (Herceptin) -- heavy-chain variable domain (VH), simplified.
TRASTUZUMAB_VH = (
    "EVQLVESGGGLVQPGGSLRLSCAASGFNIKDTYIHWVRQAPGKGLEWVARIYPTNGYTRYADSVKGRFTI"
    "SADTSKNTAYLQMNSLRAEDTAVYYCSRWGGDGFYAMDYWGQGTLVTVSS"
)

# Human ubiquitin (UniProt P0CG48, residues 1-76)
UBIQUITIN = (
    "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLV"
    "LRLRGG"
)

# Enhanced GFP (EGFP)
EGFP = (
    "MVSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTLTYGVQ"
    "CFSRYPDHMKQHDFFKSAMPEGYVQERTIFFKDDGNYKTRAEVKFEGDTLVNRIELKGIDFKEDGNILGH"
    "KLEYNYNSHNVYIMADKQKNGIKVNFKIRHNIEDGSVQLADHYQQNTPIGDGPVLLPDNHYLSTQSALSK"
    "DPNEKRDHMVLLEFVTAAGITLGMDELYK"
)


# ---------------------------------------------------------------------------
# Workflow YAML snippets
# ---------------------------------------------------------------------------
# Each YAML string parses to {nodes: [...], edges: [...]} per WorkflowEditor.
# Node kinds are drawn from opendna.workflows.graph_runner.list_node_types().

_WF_CANCER_BINDER = """
nodes:
  - id: seq
    kind: constant
    params:
      value: "{seq}"
  - id: fold
    kind: fold
    params: {}
  - id: design
    kind: design
    params:
      num_candidates: 20
  - id: score
    kind: evaluate
    params: {}
edges:
  - {source: seq, target: fold, out_key: value, in_key: sequence}
  - {source: fold, target: design, out_key: pdb, in_key: pdb_string}
  - {source: design, target: score, out_key: best, in_key: sequence}
""".strip()

_WF_ANTIBODY = """
nodes:
  - id: seq
    kind: constant
    params:
      value: "{seq}"
  - id: evaluate
    kind: evaluate
    params: {}
  - id: fold
    kind: fold
    params: {}
  - id: scan
    kind: design
    params:
      num_candidates: 15
edges:
  - {source: seq, target: evaluate, out_key: value, in_key: sequence}
  - {source: seq, target: fold, out_key: value, in_key: sequence}
  - {source: fold, target: scan, out_key: pdb, in_key: pdb_string}
""".strip()

_WF_ENZYME = """
nodes:
  - id: seq
    kind: constant
    params:
      value: "{seq}"
  - id: fold
    kind: fold
    params: {}
  - id: design
    kind: design
    params:
      num_candidates: 10
      fixed_positions: [44, 48, 68]
  - id: score
    kind: evaluate
    params: {}
edges:
  - {source: seq, target: fold, out_key: value, in_key: sequence}
  - {source: fold, target: design, out_key: pdb, in_key: pdb_string}
  - {source: design, target: score, out_key: best, in_key: sequence}
""".strip()

_WF_DENOVO = """
nodes:
  - id: len
    kind: constant
    params:
      value: 60
  - id: diffuse
    kind: denovo
    params:
      length: 60
  - id: fold
    kind: fold
    params: {}
  - id: score
    kind: evaluate
    params: {}
edges:
  - {source: diffuse, target: fold, out_key: sequence, in_key: sequence}
  - {source: fold, target: score, out_key: sequence, in_key: sequence}
""".strip()

_WF_MEMBRANE = """
nodes:
  - id: seq
    kind: constant
    params:
      value: "{seq}"
  - id: fold
    kind: fold
    params: {}
  - id: design
    kind: design
    params:
      num_candidates: 8
  - id: analyze
    kind: evaluate
    params: {}
edges:
  - {source: seq, target: fold, out_key: value, in_key: sequence}
  - {source: fold, target: design, out_key: pdb, in_key: pdb_string}
  - {source: design, target: analyze, out_key: best, in_key: sequence}
""".strip()

_WF_PEPTIDE = """
nodes:
  - id: seed
    kind: constant
    params:
      value: "CYKRWCG"
  - id: fold
    kind: fold
    params: {}
  - id: design
    kind: design
    params:
      num_candidates: 10
  - id: evaluate
    kind: evaluate
    params: {}
edges:
  - {source: seed, target: fold, out_key: value, in_key: sequence}
  - {source: fold, target: design, out_key: pdb, in_key: pdb_string}
  - {source: design, target: evaluate, out_key: best, in_key: sequence}
""".strip()


TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "cancer_binder",
        "name": "Cancer Target Binder (KRAS G12D)",
        "description": (
            "Start from the oncogenic KRAS G12D mutant (a top undruggable cancer "
            "target) and design candidate peptide/mini-protein binders.  Runs a "
            "fold + inverse-folding design pass and scores each candidate."
        ),
        "starter_sequence": KRAS_G12D,
        "starter_pdb_id": None,
        "starter_uniprot_id": "P01116",
        "workflow_yaml": _WF_CANCER_BINDER.replace("{seq}", KRAS_G12D),
        "academy_level": 5,
        "tags": ["cancer", "binder", "KRAS", "oncology", "design"],
    },
    {
        "id": "antibody_optimization",
        "name": "Antibody Humanization & Stability (Trastuzumab)",
        "description": (
            "Start from the trastuzumab VH domain and run a humanization + "
            "stability scan.  Useful for teaching CDR grafting and developability."
        ),
        "starter_sequence": TRASTUZUMAB_VH,
        "starter_pdb_id": "1N8Z",
        "starter_uniprot_id": None,
        "workflow_yaml": _WF_ANTIBODY.replace("{seq}", TRASTUZUMAB_VH),
        "academy_level": 6,
        "tags": ["antibody", "humanization", "stability", "trastuzumab"],
    },
    {
        "id": "enzyme_engineering",
        "name": "Enzyme Engineering (Ubiquitin scaffold)",
        "description": (
            "Take ubiquitin as a rigid, well-characterized scaffold and run "
            "constrained design preserving the conserved active-site-like "
            "residues (K48, G75, G76).  Good for teaching constrained design."
        ),
        "starter_sequence": UBIQUITIN,
        "starter_pdb_id": "1UBQ",
        "starter_uniprot_id": "P0CG48",
        "workflow_yaml": _WF_ENZYME.replace("{seq}", UBIQUITIN),
        "academy_level": 5,
        "tags": ["enzyme", "constrained", "ubiquitin", "active site"],
    },
    {
        "id": "de_novo_mini",
        "name": "De Novo Mini-Protein (60 aa)",
        "description": (
            "Use RFdiffusion to generate a 60-residue de novo protein from "
            "scratch, then fold + score it.  Great introduction to generative "
            "backbone design."
        ),
        "starter_sequence": "",
        "starter_pdb_id": None,
        "starter_uniprot_id": None,
        "workflow_yaml": _WF_DENOVO,
        "academy_level": 7,
        "tags": ["de novo", "RFdiffusion", "generative", "mini protein"],
    },
    {
        "id": "membrane_sensor",
        "name": "Membrane-Anchored Sensor (GFP)",
        "description": (
            "Turn EGFP into a membrane-anchored fluorescent sensor by designing "
            "a hydrophobic transmembrane segment and a linker.  Teaches "
            "multi-objective design with localization constraints."
        ),
        "starter_sequence": EGFP,
        "starter_pdb_id": "1EMA",
        "starter_uniprot_id": "P42212",
        "workflow_yaml": _WF_MEMBRANE.replace("{seq}", EGFP),
        "academy_level": 6,
        "tags": ["membrane", "sensor", "GFP", "fluorescent"],
    },
    {
        "id": "peptide_drug",
        "name": "Cyclic Peptide Drug",
        "description": (
            "Design a small cyclic peptide binder (7-12 residues) with a "
            "disulfide staple.  Quick to run and great for teaching the "
            "peptide-drug discovery workflow."
        ),
        "starter_sequence": "CYKRWCG",
        "starter_pdb_id": None,
        "starter_uniprot_id": None,
        "workflow_yaml": _WF_PEPTIDE,
        "academy_level": 4,
        "tags": ["peptide", "cyclic", "drug", "small"],
    },
]


def list_templates() -> List[Dict[str, Any]]:
    """Return a lightweight listing of all templates (no YAML body)."""
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "academy_level": t["academy_level"],
            "tags": list(t["tags"]),
            "has_starter_sequence": bool(t.get("starter_sequence")),
            "starter_pdb_id": t.get("starter_pdb_id"),
            "starter_uniprot_id": t.get("starter_uniprot_id"),
        }
        for t in TEMPLATES
    ]


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Return a full template dict (including workflow YAML) or None."""
    for t in TEMPLATES:
        if t["id"] == template_id:
            return dict(t)
    return None


def instantiate_template(
    template_id: str,
    user_id: str,
    project_id: str,
) -> Dict[str, Any]:
    """Create a new workspace project pre-populated with the template's data.

    Returns a dict describing what was created.
    """
    t = get_template(template_id)
    if t is None:
        raise ValueError(f"unknown template id: {template_id}")

    payload: Dict[str, Any] = {
        "template_id": t["id"],
        "template_name": t["name"],
        "starter_sequence": t.get("starter_sequence") or "",
        "starter_pdb_id": t.get("starter_pdb_id"),
        "starter_uniprot_id": t.get("starter_uniprot_id"),
        "workflow_yaml": t["workflow_yaml"],
        "academy_level": t["academy_level"],
        "tags": list(t["tags"]),
        "created_from_template": True,
    }

    # Best-effort save to both the workspace store (if available) and the
    # plain project store.  Neither is fatal if missing.
    saved_to: List[str] = []
    try:
        from opendna.workspaces import get_workspace  # type: ignore
        ws = get_workspace(user_id)
        ws.save_project(project_id, payload)
        saved_to.append("workspace")
    except Exception:
        pass
    try:
        from opendna.storage.projects import save_project  # type: ignore
        save_project(project_id, payload)
        saved_to.append("projects")
    except Exception:
        pass

    return {
        "template_id": t["id"],
        "project_id": project_id,
        "user_id": user_id,
        "saved_to": saved_to,
        "payload": payload,
    }


__all__ = [
    "TEMPLATES",
    "list_templates",
    "get_template",
    "instantiate_template",
]
