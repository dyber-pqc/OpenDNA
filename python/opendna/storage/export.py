"""Project export/import as .opendna zip files for sharing and reproducibility."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def export_project(project_data: dict, output_path: str | Path) -> str:
    """Export a project workspace as a .opendna zip file.

    The zip contains:
    - manifest.json (project metadata)
    - structures/ (PDB files for each structure)
    - sequences/ (FASTA files)
    - workflow.yaml (if present)
    - notes.md (if present)
    - provenance.json
    """
    output_path = Path(output_path)
    if not output_path.suffix:
        output_path = output_path.with_suffix(".opendna")

    manifest = {
        "name": project_data.get("name", "untitled"),
        "version": project_data.get("version", "0.4.0"),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "format_version": "1",
        "n_structures": len(project_data.get("structures", [])),
    }

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2))

        for i, struct in enumerate(project_data.get("structures", [])):
            label = struct.get("label", f"structure_{i}")
            safe_label = "".join(c for c in label if c.isalnum() or c in "-_")[:40]
            if struct.get("pdbData"):
                z.writestr(f"structures/{i:03d}_{safe_label}.pdb", struct["pdbData"])
            if struct.get("sequence"):
                fasta = f">{label}\n{struct['sequence']}\n"
                z.writestr(f"sequences/{i:03d}_{safe_label}.fasta", fasta)

        # Provenance: full project data minus huge PDB strings
        light = {**project_data}
        if "structures" in light:
            light["structures"] = [
                {**s, "pdbData": f"<see structures/{i:03d}_*.pdb>"}
                for i, s in enumerate(light["structures"])
            ]
        z.writestr("provenance.json", json.dumps(light, indent=2, default=str))

        if project_data.get("notes"):
            z.writestr("notes.md", project_data["notes"])

        if project_data.get("workflow"):
            z.writestr("workflow.yaml", project_data["workflow"])

    return str(output_path)


def import_project(input_path: str | Path) -> dict:
    """Import a .opendna zip file into a project workspace dict."""
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    with zipfile.ZipFile(input_path, "r") as z:
        names = z.namelist()
        manifest = {}
        if "manifest.json" in names:
            manifest = json.loads(z.read("manifest.json").decode())

        provenance = {}
        if "provenance.json" in names:
            provenance = json.loads(z.read("provenance.json").decode())

        # Reload structures from PDB files
        structures = []
        pdb_files = sorted([n for n in names if n.startswith("structures/") and n.endswith(".pdb")])
        for pdb_file in pdb_files:
            content = z.read(pdb_file).decode()
            label = Path(pdb_file).stem.split("_", 1)[-1]
            structures.append({
                "label": label,
                "pdbData": content,
                "sequence": "",
                "source": "imported",
            })

        notes = ""
        if "notes.md" in names:
            notes = z.read("notes.md").decode()

        workflow = ""
        if "workflow.yaml" in names:
            workflow = z.read("workflow.yaml").decode()

    return {
        "name": manifest.get("name", input_path.stem),
        "manifest": manifest,
        "structures": structures,
        "notes": notes,
        "workflow": workflow,
        "provenance": provenance,
    }
