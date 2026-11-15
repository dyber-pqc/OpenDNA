# opendna-cli

The `opendna` command: runs the trained heads over a whole FASTA file.

The desktop application works one protein at a time, which is the wrong shape
for the job people actually have — a few hundred candidates to triage. This
runs the same prediction code, so the two cannot disagree about a number.

```bash
opendna models
opendna predict --task disorder    -i candidates.fasta -o disorder.csv
opendna predict --task solubility  -i candidates.fasta -o solubility.csv
opendna predict --task stability   -i candidates.fasta --mutations muts.csv -o ddg.csv
```

`--format` takes `csv`, `tsv`, `json`, or `caid` for a CAID submission — see
[CAID.md](CAID.md). With no `-o`, the table goes to standard output and
progress goes to standard error, so a pipe stays clean.

Sequences are read as written rather than validated against the twenty
standard amino acids. Real target files contain selenocysteine, pyrrolysine
and the ambiguity codes — CAID's own `DP03745` has a `U` at position 48 — and
ESM-2 has distinct tokens for all of them, so collapsing them to `X` would
feed the model a residue the file does not specify.

Heads are found via `--models`, then `$OPENDNA_MODELS`, then `./models`:

```bash
hf download dyber-pqc/opendna-disorder --local-dir models
export OPENDNA_MODELS=$PWD/models
```

## Stability needs to be told which mutations

The head scores named substitutions rather than scanning everything, so it
takes a CSV of `name,mutation` where the name matches the FASTA header and the
mutation is written the usual way, 1-based:

```csv
name,mutation
ubiquitin,L8P
ubiquitin,K6A
```

The wild-type letter in each label is checked against the sequence at that
position, and a disagreement stops the run. That check exists because a
mutation list numbered against a slightly different construct — a tagged
version, a different isoform — otherwise scores a neighbouring residue and
produces a table that looks completely normal.

## Every output says what produced it

Delimited output carries `#` comment lines with the head version, the
embedding model, the device, and the limitations taken from the model card.
JSON carries the same as fields. Readers skip `#` by convention: pandas with
`comment='#'`, R with `comment.char='#'`.

The limitations are read out of the card rather than written here, so the CLI
cannot state a different set than the card does. This matters more than it
looks: a prediction that travels without them becomes a number in a
spreadsheet, then a number in a slide, and by then nobody can tell which model
made it or what it does not cover.

## What it will not do

There is no fallback. A missing head is an error naming the files it looked
for and the command to fetch one. A sequence longer than the embedding model's
limit is refused for solubility, because that head pools over a single pass
and pooling across windows is a different quantity than the one it was trained
on — disorder windows instead, and says so in the output.

Read each head's model card before acting on a number. The stability head's
honest out-of-domain correlation is about 0.44 Spearman, which makes it a
ranking signal and not a measurement.
