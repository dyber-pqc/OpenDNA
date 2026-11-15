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
opendna predict --task burial      -i candidates.fasta -o accessibility.csv
```

`burial` gives relative solvent accessibility per residue — roughly 0 for a
residue in the core, roughly 1 for one fully exposed — which is what answers
where a mutation is tolerable and where a linker can go. Read it beside
`disorder`: accessibility describes a folded structure, so for a region with
no stable fold the number is still produced and still means nothing.

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

## Knowing what you ran

A result is only defensible if the model behind it can be named and checked.

```bash
opendna models                       # what is installed, and does it verify
opendna models --lock models.lock    # pin it
opendna models --check models.lock   # fail unless the install is still that
```

Each head records a semantic version, a build id digesting everything that
determined the weights (the dataset manifest, the hyperparameters, the
embedding model, the training code), and the SHA-256 of the weights file
beside it. `models` rehashes the weights and reports one of three states:

| | |
|---|---|
| `verified` | the weights are the file the metadata names |
| `NOT VERIFIABLE` | metadata predating hashes; usable, but unprovable |
| `CORRUPT` | the weights are not that file |

Corrupt weights make `models` exit non-zero, and `predict` refuses before
loading anything. A half-finished download otherwise produces numbers from a
file nobody can identify, which is worse than no numbers.

`--check` exits non-zero when the installed heads differ from the lockfile,
including a retrain that kept the same version number — the build id catches
that. Commit the lockfile beside the analysis it produced.

## Running on a machine with no network

The heads are about a megabyte each and copy anywhere. The embedding model does
not: it is 568 MB, it lives in the Hugging Face cache rather than beside the
heads, and a machine that has never run a prediction downloads it on its first
one. On an instrument computer or anything behind an air gap that is not a slow
first run, it is a failure at the moment somebody needs a result.

```bash
opendna stage --to /mnt/usb/opendna-models        # on a connected machine
opendna --models ./opendna-models --offline selftest
```

`stage` writes one directory holding the four heads, their cards, the embedding
model's own files, `models.lock`, and a `sha256sums.txt` in the format
`sha256sum -c` reads. It copies what this machine already resolved rather than
re-fetching on the target, so the bundle is exactly what was tested here. It
refuses to stage an installation that does not verify — a bundle nobody can
trust, carried to a machine where nobody can re-download, is the worst possible
place to discover a bad file.

`--offline` is a hard promise, not a preference: nothing will reach the
network, and if the embedding model is not staged the command says so and names
the two files it wanted. Without the flag a missing model is downloaded, which
is right on a laptop and wrong on anything validated.

`opendna models` says which of the two situations a directory is in.

Verified by staging a bundle, pointing `HF_HOME` at an empty directory so the
cache held nothing, and running `--offline`: the self-test passed all
seventeen checks and a disorder run gave values identical to the online one.

## Proving the install works here

Verifying the files is not the same as checking the machine. A head can hash
correctly and still produce nonsense because this computer resolved a different
BLAS, because the GPU path is broken, or because the embedding model in the
cache is not the one the head was trained against.

```bash
opendna selftest
```

It runs all four heads over ubiquitin and checks seventeen things, going
through the same code `predict` does rather than a parallel harness. Eight are
invariants that hold for any build of these heads — the output has one value
per residue, probabilities stay in `[0, 1]`, the hydrophobic core reads as less
accessible than the chain-forming lysines, `L8P` is more destabilising than
`L8M`, and a second identical run gives identical values. Nine are numbers
measured from named builds, with a tolerance.

A pinned number is only checked against the build it was measured from. Against
any other build it reports `not checked`, naming both builds, because nobody
has measured what that head does on this fixture. A retrain is therefore
expected to leave those unchecked until someone records new values; the
invariants still run.

Exit status is 0 when nothing failed and non-zero when anything did, so it goes
straight into an installation script. It catches what `models` cannot: swapping
the burial weights into the disorder head and rewriting the metadata to match
passes `opendna models` completely clean and fails three of the pinned checks.

The tolerances are a judgement, not a measurement — the recorded values come
from one machine, on CPU. A failure that lands just outside one is worth
reporting rather than assuming the bound is too tight.

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
