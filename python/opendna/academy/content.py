"""Academy levels 4-7, badge catalog, glossary."""
from __future__ import annotations

from typing import Dict, List, Optional


# Levels 4-7 (levels 1-3 live in the existing Academy component)
LEVELS: List[Dict] = [
    {
        "id": 4,
        "title": "Mutational scanning",
        "description": "Learn how ΔΔG predictions let you ask 'what if I mutated this residue?'",
        "xp": 300,
        "lessons": [
            {"id": "4.1", "title": "The free-energy landscape",
             "body": "Proteins fold to their lowest free-energy state. A point mutation shifts the landscape — ΔΔG measures the change in folding stability. Negative = more stable, positive = less stable.",
             "quiz": {"q": "A ΔΔG of +3.0 kcal/mol means the mutant is:", "a": ["more stable", "less stable", "unchanged"], "correct": 1}},
            {"id": "4.2", "title": "Alanine scanning",
             "body": "Replace each residue with Ala in turn and measure ΔΔG. Residues that give large positive ΔΔG are 'hot spots' — critical for stability or binding.",
             "quiz": {"q": "Hot-spot residues have ΔΔG:", "a": ["near 0", "large positive", "large negative"], "correct": 1}},
            {"id": "4.3", "title": "Try it",
             "body": "Pick a sequence and use the mutate() function. Compare the predicted ΔΔG for 3 substitutions.",
             "quiz": None},
        ],
    },
    {
        "id": 5,
        "title": "Molecular dynamics basics",
        "description": "What OpenMM is actually doing when you click 'Quick MD'.",
        "xp": 400,
        "lessons": [
            {"id": "5.1", "title": "Force fields",
             "body": "Classical MD uses a potential energy function (AMBER/CHARMM/OPLS) summing bond, angle, dihedral, electrostatic, and van der Waals terms. Integrating Newton's equations gives a trajectory.",
             "quiz": {"q": "MD force fields model:", "a": ["quantum effects", "classical interactions", "neural networks"], "correct": 1}},
            {"id": "5.2", "title": "Explicit vs implicit solvent",
             "body": "Explicit TIP3P water is accurate but expensive. Implicit solvent (GBSA) is 10-100x faster. OpenDNA supports both.",
             "quiz": {"q": "TIP3P is:", "a": ["a protein", "a water model", "an enzyme"], "correct": 1}},
            {"id": "5.3", "title": "Trajectory analysis",
             "body": "After running MD, compute RMSD vs the starting structure, radius of gyration, and residue flexibility (RMSF) to see which regions are rigid or floppy.",
             "quiz": {"q": "RMSF tells you:", "a": ["global stability", "per-residue flexibility", "binding affinity"], "correct": 1}},
        ],
    },
    {
        "id": 6,
        "title": "Inverse design & diffusion models",
        "description": "How RFdiffusion and ESM-IF1 turn a target structure into a sequence.",
        "xp": 500,
        "lessons": [
            {"id": "6.1", "title": "Forward vs inverse problem",
             "body": "Forward: sequence → structure (ESMFold). Inverse: structure → sequence (ESM-IF1). Inverse is the design problem — given a fold, what sequences achieve it?",
             "quiz": {"q": "Inverse folding predicts:", "a": ["structure from sequence", "sequence from structure", "function from sequence"], "correct": 1}},
            {"id": "6.2", "title": "Diffusion models for backbones",
             "body": "RFdiffusion is a denoising diffusion model over protein backbones. Starting from Gaussian noise in 3D, it iteratively denoises into a plausible backbone, then ESM-IF1 assigns a sequence.",
             "quiz": {"q": "RFdiffusion generates:", "a": ["sequences", "backbones", "SMILES"], "correct": 1}},
            {"id": "6.3", "title": "Motif scaffolding",
             "body": "A common task: hold a functional motif fixed and design a scaffold around it. Contig syntax like 5-20/A10-30/5-20 fixes chain A residues 10-30.",
             "quiz": None},
        ],
    },
    {
        "id": 7,
        "title": "Multi-objective optimization",
        "description": "Trading off stability, solubility, immunogenicity, and developability.",
        "xp": 600,
        "lessons": [
            {"id": "7.1", "title": "Pareto fronts",
             "body": "When objectives conflict (e.g. stability vs solubility), no single 'best' solution exists — instead you get a Pareto front of non-dominated points. NSGA-II explores this front.",
             "quiz": {"q": "A Pareto-optimal design is one where:", "a": ["all metrics are maximized", "you cannot improve one metric without hurting another", "metrics are averaged"], "correct": 1}},
            {"id": "7.2", "title": "Weighted scalarization",
             "body": "Simple alternative: combine objectives with weights. Fast but sensitive to the choice of weights and cannot find concave parts of the Pareto front.",
             "quiz": None},
            {"id": "7.3", "title": "Constrained design",
             "body": "Hold the active site fixed while optimizing stability. In OpenDNA: use constrained_design() with a list of positions to preserve.",
             "quiz": {"q": "Constrained design preserves:", "a": ["the backbone", "specific residue identities", "the sequence length"], "correct": 1}},
        ],
    },
]


BADGES: List[Dict] = [
    {"id": "first_fold",       "name": "First Fold",       "icon": "🧬", "criterion": "Fold your first sequence"},
    {"id": "designer",         "name": "Designer",         "icon": "🎨", "criterion": "Generate 5+ design candidates"},
    {"id": "marathon",         "name": "Marathon Runner",  "icon": "🏃", "criterion": "Run a 1 ns MD simulation"},
    {"id": "scholar",          "name": "Scholar",          "icon": "📚", "criterion": "Complete Academy Level 4"},
    {"id": "dynamicist",       "name": "Dynamicist",       "icon": "⚛️", "criterion": "Complete Academy Level 5"},
    {"id": "diffuser",         "name": "Diffuser",         "icon": "🌫️", "criterion": "Complete Academy Level 6"},
    {"id": "polymath",         "name": "Polymath",         "icon": "🧠", "criterion": "Complete Academy Level 7"},
    {"id": "streak_7",         "name": "Week Streak",      "icon": "🔥", "criterion": "Log in 7 days in a row"},
    {"id": "streak_30",        "name": "Month Streak",     "icon": "🔥🔥", "criterion": "30-day streak"},
    {"id": "challenger",       "name": "Challenger",       "icon": "🏆", "criterion": "Complete 10 daily challenges"},
    {"id": "publisher",        "name": "Publisher",        "icon": "📜", "criterion": "Mint your first DOI via Zenodo"},
    {"id": "collaborator",     "name": "Collaborator",     "icon": "🤝", "criterion": "Use real-time co-editing with a peer"},
    {"id": "pqc_pioneer",      "name": "PQC Pioneer",      "icon": "🛡️", "criterion": "Enable post-quantum auth"},
]


GLOSSARY: Dict[str, str] = {
    "ESMFold": "Meta's single-sequence protein structure predictor based on the ESM-2 language model. Requires no MSA.",
    "ESM-IF1": "Inverse folding model from Meta. Given a backbone, samples diverse sequences that could fold to it.",
    "RFdiffusion": "Denoising diffusion model from the Baker lab for de novo protein backbone generation.",
    "Boltz-1": "Open-source AlphaFold-Multimer-grade complex predictor.",
    "ΔΔG": "Change in folding free energy upon mutation. Positive = destabilizing, negative = stabilizing.",
    "pLDDT": "Per-residue model confidence score, 0-100. Above 90 is very high confidence.",
    "pTM / ipTM": "Predicted TM-score / interface pTM. Used by Boltz/AF-Multimer to score complex predictions.",
    "MSA": "Multiple sequence alignment. Used by AlphaFold2/ColabFold to capture coevolutionary signal.",
    "TIP3P": "Three-site rigid water model used in classical MD.",
    "Kabsch RMSD": "Root-mean-square deviation after optimal rigid-body alignment of two structures.",
    "MolProbity": "Structure validation suite checking Ramachandran, rotamers, clashes.",
    "PROPKA": "Empirical method for predicting pKa of ionizable residues.",
    "TANGO": "Aggregation propensity predictor based on beta-sheet formation statistics.",
    "NSGA-II": "Non-dominated Sorting Genetic Algorithm II — standard multi-objective optimizer.",
    "Pareto front": "Set of non-dominated solutions in a multi-objective optimization.",
    "ML-KEM-768": "NIST-standardized post-quantum key encapsulation (Kyber).",
    "ML-DSA-65": "NIST-standardized post-quantum digital signature (Dilithium).",
    "Yjs": "A CRDT library for shared data structures that enable real-time collaboration.",
    "CRDT": "Conflict-free Replicated Data Type — a data structure that multiple users can edit concurrently without conflicts.",
    "Provenance DAG": "Directed acyclic graph recording every computation step so runs are reproducible, diffable, and bisectable.",
    "DiffDock": "Diffusion-based protein-ligand docking, state-of-the-art accuracy.",
    "xTB": "Grimme's semi-empirical tight-binding quantum chemistry method.",
    "ANI-2x": "Neural network potential trained on DFT data for near-DFT accuracy at force-field speed.",
}


def list_levels() -> List[Dict]:
    return [
        {k: v for k, v in lvl.items() if k != "lessons"} | {"lesson_count": len(lvl["lessons"])}
        for lvl in LEVELS
    ]


def get_level(level_id: int) -> Optional[Dict]:
    for lvl in LEVELS:
        if lvl["id"] == level_id:
            return lvl
    return None
