"""Toy plasmid map generator.

Reverse-translates a protein sequence into E. coli optimized DNA and wraps it
in a small, canned vector backbone (pET28a-like by default). Returns a
GenBank flat-file representation and a feature table suitable for rendering
as a circular plasmid.
"""

from __future__ import annotations

from typing import Dict, List

# ---------------------------------------------------------------------------
# Codon table (high-usage codons for E. coli K-12)
# ---------------------------------------------------------------------------
ECOLI_CODON: Dict[str, str] = {
    "A": "GCG", "R": "CGT", "N": "AAC", "D": "GAT", "C": "TGC",
    "E": "GAA", "Q": "CAG", "G": "GGC", "H": "CAT", "I": "ATT",
    "L": "CTG", "K": "AAA", "M": "ATG", "F": "TTT", "P": "CCG",
    "S": "AGC", "T": "ACC", "W": "TGG", "Y": "TAT", "V": "GTG",
    "*": "TAA",
}

# Common affinity tag amino-acid sequences.
TAGS: Dict[str, str] = {
    "His6": "HHHHHH",
    "His8": "HHHHHHHH",
    "FLAG": "DYKDDDDK",
    "Myc": "EQKLISEEDL",
    "HA": "YPYDVPDYA",
    "StrepII": "WSHPQFEK",
    "none": "",
}

# Vector backbones -- (promoter_dna, rbs_dna, linker_aa, terminator_dna, origin_dna, resistance_dna)
VECTORS: Dict[str, dict] = {
    "pET28a": {
        "promoter": "T7",
        "promoter_seq": "TAATACGACTCACTATAGGG",
        "rbs_seq": "AAGGAGATATACC",
        "linker_aa": "SSGLVPRGSHM",
        "terminator_seq": "CTAGCATAACCCCTTGGGGCCTCTAAACGGGTCTTGAGGGGTTTTTTG",
        "origin_seq": "G" * 589,       # placeholder pBR322 ori stub
        "resistance": "KanR",
        "resistance_seq": "A" * 795,     # placeholder neomycin phosphotransferase stub
    },
    "pUC19": {
        "promoter": "lac",
        "promoter_seq": "TTTACACTTTATGCTTCCGGCTCGTATGTTGTGTGG",
        "rbs_seq": "AGGAAACAGCT",
        "linker_aa": "GSGSG",
        "terminator_seq": "CTGTTGACAATTAATCATCGGCTCGTATAATG",
        "origin_seq": "G" * 589,
        "resistance": "AmpR",
        "resistance_seq": "A" * 861,
    },
}


def _reverse_translate(protein: str) -> str:
    return "".join(ECOLI_CODON.get(aa.upper(), "NNN") for aa in protein)


def generate_plasmid(
    protein_sequence: str,
    vector: str = "pET28a",
    tag: str = "His6",
    promoter: str = "T7",
) -> dict:
    """Assemble a simple circular plasmid carrying the given protein.

    Returns dict with keys: ``dna_sequence``, ``features``, ``genbank``,
    ``vector``, ``tag``, ``promoter``, ``length``.
    """
    protein = (protein_sequence or "").strip().upper()
    if not protein:
        return {"error": "empty protein_sequence", "features": [], "genbank": ""}

    vec = VECTORS.get(vector) or VECTORS["pET28a"]
    tag_aa = TAGS.get(tag, TAGS["His6"])
    linker_aa = vec["linker_aa"]

    # ------------------------------------------------------------------
    # Assemble the DNA
    # ------------------------------------------------------------------
    promoter_seq = vec["promoter_seq"]
    rbs_seq = vec["rbs_seq"]
    atg = ECOLI_CODON["M"]
    tag_dna = _reverse_translate(tag_aa)
    linker_dna = _reverse_translate(linker_aa)
    orf_body_dna = _reverse_translate(protein if not protein.startswith("M") else protein[1:])
    stop_dna = ECOLI_CODON["*"]
    terminator_seq = vec["terminator_seq"]
    origin_seq = vec["origin_seq"]
    resistance_seq = vec["resistance_seq"]

    spacer = "GAATTC"  # EcoRI, used as visible separator
    parts: List[tuple] = []  # (name, type, strand, seq)
    parts.append(("promoter", "promoter", 1, promoter_seq))
    parts.append(("RBS", "RBS", 1, rbs_seq))
    parts.append(("spacer", "misc_feature", 1, "CATATG"))  # NdeI
    parts.append(("start", "CDS_start", 1, atg))
    if tag_dna:
        parts.append((f"{tag} tag", "tag", 1, tag_dna))
    if linker_dna:
        parts.append(("linker", "linker", 1, linker_dna))
    parts.append(("ORF", "CDS", 1, orf_body_dna))
    parts.append(("stop", "terminator", 1, stop_dna))
    parts.append(("T7 terminator", "terminator", 1, terminator_seq))
    parts.append(("spacer", "misc_feature", 1, spacer))
    parts.append((vec["resistance"], "resistance", 1, resistance_seq))
    parts.append(("spacer", "misc_feature", 1, spacer))
    parts.append(("ori", "rep_origin", 1, origin_seq))

    dna_chunks: List[str] = []
    features: List[dict] = []
    cursor = 1  # 1-indexed like GenBank
    for name, ftype, strand, seq in parts:
        start = cursor
        end = cursor + len(seq) - 1
        dna_chunks.append(seq)
        if name != "spacer":
            features.append(
                {
                    "name": name,
                    "type": ftype,
                    "start": start,
                    "end": end,
                    "strand": strand,
                }
            )
        cursor = end + 1
    dna_sequence = "".join(dna_chunks)

    genbank = _render_genbank(
        name=f"{vector}_{tag}_insert",
        dna=dna_sequence,
        features=features,
        vector=vector,
    )

    return {
        "vector": vector,
        "tag": tag,
        "promoter": promoter or vec["promoter"],
        "length": len(dna_sequence),
        "dna_sequence": dna_sequence,
        "features": features,
        "genbank": genbank,
    }


def _render_genbank(name: str, dna: str, features: List[dict], vector: str) -> str:
    """Minimal, valid-ish GenBank flat file."""
    total = len(dna)
    lines: List[str] = []
    lines.append(
        f"LOCUS       {name[:16]:<16} {total:>8} bp    DNA     circular SYN 01-JAN-2026"
    )
    lines.append(f"DEFINITION  OpenDNA synthetic construct based on {vector}.")
    lines.append("ACCESSION   .")
    lines.append("VERSION     .")
    lines.append("KEYWORDS    synthetic; opendna.")
    lines.append("SOURCE      synthetic DNA construct")
    lines.append("  ORGANISM  synthetic DNA construct")
    lines.append("FEATURES             Location/Qualifiers")
    lines.append(f"     source          1..{total}")
    lines.append('                     /organism="synthetic DNA construct"')
    lines.append('                     /mol_type="other DNA"')
    type_map = {
        "promoter": "promoter",
        "RBS": "RBS",
        "CDS_start": "misc_feature",
        "tag": "misc_feature",
        "linker": "misc_feature",
        "CDS": "CDS",
        "terminator": "terminator",
        "rep_origin": "rep_origin",
        "resistance": "CDS",
        "misc_feature": "misc_feature",
    }
    for f in features:
        gb_type = type_map.get(f["type"], "misc_feature")
        loc = f"{f['start']}..{f['end']}"
        if f["strand"] == -1:
            loc = f"complement({loc})"
        lines.append(f"     {gb_type:<15} {loc}")
        lines.append(f'                     /label="{f["name"]}"')
    lines.append("ORIGIN")
    # Sequence in 60-char rows, 10-char chunks, 1-indexed.
    lower = dna.lower()
    for i in range(0, len(lower), 60):
        row = lower[i : i + 60]
        chunks = [row[j : j + 10] for j in range(0, len(row), 10)]
        lines.append(f"{i + 1:>9} " + " ".join(chunks))
    lines.append("//")
    return "\n".join(lines) + "\n"
