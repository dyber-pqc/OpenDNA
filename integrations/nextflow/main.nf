#!/usr/bin/env nextflow
// Example Nextflow pipeline that uses the OpenDNA Python SDK
// Run: nextflow run main.nf
nextflow.enable.dsl = 2

params.sequences = 'sequences.csv'

process EVALUATE {
    tag "$name"
    publishDir 'results', mode: 'copy'

    input:
    tuple val(name), val(sequence)

    output:
    path "${name}.score.json"

    script:
    """
    python - <<'PY'
import json
from opendna.sdk import Client
c = Client("http://localhost:8765")
result = c.evaluate("${sequence}")
with open("${name}.score.json","w") as f:
    json.dump(result, f, indent=2)
PY
    """
}

process FOLD {
    tag "$name"
    publishDir 'results', mode: 'copy'

    input:
    tuple val(name), val(sequence)

    output:
    path "${name}.pdb"

    script:
    """
    python - <<'PY'
from opendna.sdk import Client
c = Client("http://localhost:8765")
result = c.fold("${sequence}")
pdb = result.get("pdb","") if isinstance(result, dict) else str(result)
with open("${name}.pdb","w") as f:
    f.write(pdb)
PY
    """
}

workflow {
    Channel
        .fromPath(params.sequences)
        .splitCsv(header: true)
        .map { row -> tuple(row.name, row.sequence) }
        .set { inputs }

    EVALUATE(inputs)
    FOLD(inputs)
}
