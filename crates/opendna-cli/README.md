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

`--device cpu` forces the CPU on a build with GPU support compiled in, which
is what you want when the GPU is busy with someone else's job and what makes
it possible to check the two agree.

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

## Disorder probabilities are calibrated

The disorder head's probabilities are corrected before they are reported, and
the threshold for a call comes from the head rather than from a constant.

Measured on the held-out split: expected calibration error 0.217 before the
correction, 0.032 after. Where the raw head said 0.55, 13% of those residues
were actually annotated disordered. The correction is monotonic, so AUROC is
unchanged; what changes is the meaning of the number.

That moves the threshold. The conventional 0.5 was never right for this head —
on its raw scale the best threshold is 0.73 — and on the calibrated scale it is
0.34, chosen on the validation split. Both the map and the threshold live in
`disorder.metadata.json`, so `predict`, the desktop application and the CAID
output all use the same ones, and recalibrating the head changes the call
without changing any code.

A head carrying no recorded calibration falls back to 0.5 and its card says
calibration was not measured. "Measured and left alone" and "never measured"
are different states and the card distinguishes them.

## Regressor outputs carry an interval

`stability`, `solubility` and `burial` report `interval_low` and
`interval_high` beside their point estimate, and a `#` comment saying what
confidence they carry and what coverage that confidence actually achieved.

```
# interval_low/high: 90% prediction interval, +/-1.327 kcal/mol, which covered
# 93.7% of held-out cases. ...
name,mutation,ddg_kcal_per_mol,log_odds,interval_low,interval_high
ubiquitin,L8P,-0.779,-4.878,-2.1061,0.5481
ubiquitin,I44D,-1.589,-12.891,-2.9161,-0.2619
```

L8P's interval spans zero: at 90% confidence the head cannot say whether that
mutation destabilises. I44D's does not. That distinction is the useful
content, and it is invisible in the point estimate alone.

The intervals come from split conformal prediction, fitted on the validation
split and measured on the held-out one. The coverage actually achieved is
reported beside the level asked for, because they differ — the splits are
clustered by sequence identity, which is the right way to build them and
breaks the exchangeability a conformal guarantee assumes. The burial head
undercovers at every level. See each model card, and
[docs/VALIDATION.md](../../docs/VALIDATION.md).

A head with no recorded intervals gets no interval columns rather than
invented ones.

## Not every residue deserves equal trust

Every disorder output carries a `confidence` column: how far the calibrated
probability sits from the decision threshold. Measured on held-out data, it
orders residues by how likely the call is to be wrong.

```bash
opendna predict --task disorder -i candidates.fasta --min-confidence 0.25 -o out.csv
```

That adds a `low_confidence` column marking the rows below the cut-off, and
prints what the cut-off was measured to buy:

```
Marking calls below confidence 0.25. Measured at the nearest recorded cut-off
(0.25) on held-out data: 57% of residues clear it and 5.3% of those calls were
wrong, against 15.7% over all residues.
```

Rows are marked, never removed. A table quietly missing rows looks exactly like
a complete one. The cut-off is yours because the right one depends on what a
wrong call costs you; what the head supplies is the measured consequence of
each choice, recorded in its metadata.

The signal captures about half the error reduction an oracle would achieve, so
it is worth having and is not a guarantee. The one out-of-domain proxy measured
alongside it — whether a residue's 5-mer appeared in training — carried no
information about error, and the card records that so nobody re-tests it.

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

## Every run writes down what made it

The `#` comments say which head produced a file, which is what a person
reading it needs. It is not enough to reproduce the run: which input, which
bytes of that input, which build of the head, which embedding model, on what,
for how long. So every run that writes an output file writes a manifest beside
it.

```
out.csv
out.manifest.json
```

It is JSON because something else has to read it — a pipeline collecting
provenance, a notebook, a script checking two runs used the same model. One run
writes one file and never appends, so there is no race to worry about.

| | |
|---|---|
| `input` | path, SHA-256 of the bytes read, sequence and residue counts |
| `output` | path, SHA-256 of the bytes written, row count |
| `head` | task, version, build id, weights SHA-256, path |
| `embedding_model` | repo, where it came from, size, digest if known |
| `run` | UTC start, wall-clock seconds, device, the arguments as given |
| `limitations` | the model card's, so the manifest alone states the caveats |

The input is hashed from the bytes in memory rather than by re-reading the
file, so the digest describes what was actually used even when the input came
through a pipe and has no path at all.

The embedding model is the one thing not hashed by default: it is 568 MB and
digesting it takes about as long as a small run. A staged bundle already wrote
the digest into its `sha256sums.txt`, so for a staged install the manifest
carries it for free; otherwise the field is null and `sha256_source` says why.
An absent field with a reason is honest — a missing field somebody assumes was
checked is not.

`--no-manifest` turns it off, for the case where something downstream cannot
tolerate a second file appearing.

## Speed, and what it costs

Sequences are embedded in batches rather than one at a time. Every member of a
batch is padded to the longest, so the grouping sorts by length first and then
fills each batch to `--batch-tokens` padded tokens — which is also what bounds
the memory a batch needs.

Measured on 200 sequences and 35,033 residues, interleaving the settings across
rounds on an otherwise idle machine:

| device | `--batch-tokens 0` | `--batch-tokens 8192` |
|---|---|---|
| CPU | 60.8 s (59.1–63.8) | **54.5 s** (51.7–55.5) |
| RTX 2000 Ada | **6.4 s** (6.3–6.4) | 6.8 s (6.8–6.8) |

Batching helps the CPU by about a tenth and costs the GPU about a sixteenth,
which was the opposite of what we expected on the GPU: its arithmetic is
already wide enough that the padded work costs more than the per-call overhead
it saves. So one number cannot be right for both, and left unset
`--batch-tokens` follows the device. Your GPU may differ — the flag is there so
you can measure yours rather than inherit ours.

If you benchmark this, interleave the settings and report the spread. Two
earlier attempts here ran one setting after the other while a compile competed
for the cores, and produced first an overstated gain and then no detectable
one. A third, cleaner run of the same comparison put the CPU gain nearer a
sixth where this one says a tenth, so treat the size as approximate and the
direction as settled.

Sequences longer than the embedding model's limit cannot be batched — a
windowed embedding is assembled from several passes over the same sequence — so
they run one at a time and the progress line says so.

## How reproducible the numbers are

Exactly as reproducible as this, and no more:

| | |
|---|---|
| Same input, same device, same `--batch-tokens` | **byte-identical**, verified on both CPU and GPU |
| Same input, same device, different `--batch-tokens` | differs in the last digit of ~0.2% of values |
| Same input, interrupted and resumed at the same `--chunk` | **byte-identical** |
| Same input, different `--chunk`, above `--batch-tokens 0` | differs in the last digit of ~0.1% of values |
| Same input, CPU vs GPU | differs in the last digit of ~0.3% of values |

Across devices, 102 of 35,033 disorder probabilities differed, by at most
0.0001 and by 0.0000003 on average — the f32 rounding floor, not a disagreement
about biology. Nothing in those runs changes which residues are called
disordered at any sensible threshold. But it does mean a result file from the
GPU and one from the CPU are not the same bytes, so do not diff them and do not
compare their checksums.

Batch size and device are both recorded in every run manifest, which is what
makes this checkable rather than a claim: two manifests that agree on input
digest, head build, device and batch size should have produced the same output
digest, and if they did not, something is wrong that is worth finding.

`opendna selftest` is the tool for this. Its pinned values were recorded on
CPU; running it on a GPU checks that the GPU reproduces them inside the
fixture's tolerances, and on the hardware here all seventeen checks pass on
both.

The one thing to avoid: driving one model from several threads at once on
CUDA changes the low bits, because cuBLAS picks differently shaped reductions
under concurrent load. The CLI is serial, so this does not arise here, but it
is why it is serial.

## Running it across a cluster

`split` cuts a FASTA into parts balanced by residue count, because runtime
scales with residues and a scheduler waits for the slowest part. `merge` joins
the results back, reading each part's run manifest and refusing to join parts
produced with a different head build, on a different device, or at a different
batch size — which `cat` cannot notice and a cluster upgraded one node at a
time will eventually produce.

```bash
opendna stage --to /mnt/shared/opendna
opendna split -i candidates.fasta --out-dir parts --parts 20
# ... one task per part, each with --models /mnt/shared/opendna --offline ...
opendna merge --output disorder.csv parts/part-*.csv
```

**Stage the bundle first if parts will run at the same time.** This is not an
optimisation. Two runs that both load the embedding model through the Hugging
Face cache cannot do it at once: on Windows the second is refused the weights
file by the operating system and exits 3 saying the installation needs
fixing, which is unhelpful but not wrong — what needs fixing is that the
model is being read out of a cache instead of a bundle. Measured here: two
concurrent runs through the cache, one failed; three concurrent runs against a
staged directory, all three fine. A staged bundle is opened read-only and
shares without trouble, which is also why `--offline` is the right flag for a
cluster task.

Nextflow and Snakemake modules are in [pipelines/](../../pipelines), along with
the measurement showing that splitting and merging reproduces a whole-file run
exactly at `--batch-tokens 0`, and does not above it.

## Resuming a run that was interrupted

A run over fifty thousand sequences takes hours, and the things that stop it
are ordinary: a scheduler's wall-clock limit, a power cut, somebody else
needing the GPU. `--checkpoint` makes that survivable.

```bash
opendna predict --task disorder -i candidates.fasta -o disorder.csv \
  --checkpoint disorder.ckpt --chunk 64
```

Results are recorded in `disorder.ckpt` as they are produced and flushed to
disk after every chunk, so a process that is killed loses at most one chunk.
Give the same command again and it continues from where it stopped. The
results file is written only when the run finishes: the checkpoint is a record
of work done, not a results file.

**Being interrupted does not change the answer.** That is the point, and it is
the reason `--chunk` exists rather than the work being resumed at whatever
sequence it happened to reach. Sequences are batched for embedding within the
chunk they fall in, and batch composition changes the order of floating-point
sums, so a run cut at an arbitrary point would not match an uninterrupted one.
Cutting at the same boundaries every time removes the question. Verified on a
twelve-sequence file: a run resumed from a checkpoint whose last record had
been truncated mid-write produced the same 854 rows, byte for byte, as a run
that was never interrupted — the same output digest in both manifests.

What it costs is that chunking is itself a setting that changes the numbers,
in the same way and to the same degree as `--batch-tokens` does. Measured on
the same file, against a run with no checkpoint at all:

| | |
|---|---|
| `--chunk` anything, with `--batch-tokens 0` | **identical** |
| `--chunk 1` or `4`, at the CPU default of 8192 | 1 of 853 accessibility values differs, by 0.0001 |

At `--batch-tokens 0` every sequence is its own batch, so how the file is
divided cannot matter and chunking is free. Above it, the chunk size joins the
list of things a manifest has to record, and it does: a run that used a
checkpoint records its chunk size, a run that did not records nothing there,
and `opendna merge` treats those as different runs and refuses to join them.

Resuming is refused, naming the field that differs, if the input bytes, the
head build, the head's weights digest, the embedding model, the device, the
batch size, the mutation file or the confidence cut-off is not the one the
checkpoint was written with — or if the chunk size differs. A table that is
half one run and half another is the mixture `merge` exists to refuse between
files, and creating it inside one file would be worse, not better.

Two more things it does deliberately:

- A file that is not an OpenDNA checkpoint is refused and left alone. A
  mistyped `--checkpoint` must not destroy what it was pointed at.
- A truncated last record is dropped with a message saying so, and the file is
  cut back to its last complete record before anything is appended. An
  interrupted write costs one chunk, not the run.

## What the exit status means

A pipeline cannot read an error message. It reads a number, and what it needs
from that number is what to do next.

| | | |
|---|---|---|
| 0 | it worked | — |
| 1 | an unanticipated failure | report it |
| 2 | the command asked for something that does not exist | fix the command |
| 3 | the installation is wrong | fix the machine; retrying will not help |
| 4 | the data is wrong | fix the input; retrying will not help |
| 5 | the checks ran and did not hold | do not use results from this machine |

2 is deliberately the same code `clap` uses for a usage error, since a mistyped
flag and an impossible combination of valid ones want the same response.
3 covers a missing or corrupt head, a lockfile that does not match, and
`--offline` with nothing staged. 4 covers unparseable FASTA, a mutation naming
a residue the sequence does not have, and a sequence longer than the embedding
model takes. 5 comes only from `selftest`.

Anything not classified is 1. That is the honest default: a failure nobody
anticipated is not one a caller can be told how to handle, and filing it under
a known category would be worse than admitting it.

Every failure prints to standard error and names which of the above it is.
`predict` streams results to standard output, so a failing run leaves standard
output empty — a pipe collecting results never receives an error as though it
were data.

Checks that need only the arguments and the input happen before any model
loads, so a typo in a mutation file is refused in about 50 ms rather than after
568 MB has loaded for a run that cannot work.

The contract is exercised against the compiled binary in
[tests/exit_codes.rs](tests/exit_codes.rs). It needs the heads installed and
skips with a message when they are not, because a test that fails on every
machine without them gets disabled and then checks nothing at all.

## Licences travel with the weights

Three heads are Apache-2.0. The solubility head is not: it is trained on eSOL,
which is CC BY-SA 2.1 JP, and because that licence is share-alike — and
because whether trained weights are a derivative work of their training data
is an open legal question this project will not answer in its own favour — the
weights carry the same terms.

That matters when you pass a staged bundle on, which is a redistribution.
`opendna stage` writes a `LICENSES.md` grouping the heads by licence and saying
plainly when redistribution carries obligations, and each head's model card
travels beside its weights with the attribution its licence requires. The run
manifest records the licence of the head behind each result, so a number does
not outlive the knowledge that passing it on has conditions.

All of it is read out of the cards rather than written into the program, so the
notice cannot claim terms the file beside the weights does not. A head whose
card declares no licence is reported as `unstated` and treated as possibly
obliging — defaulting it to the permissive licence the others use would be a
false statement about a file somebody is about to redistribute.

## What it will not do

There is no fallback. A missing head is an error naming the files it looked
for and the command to fetch one. A sequence longer than the embedding model's
limit is refused for solubility, because that head pools over a single pass
and pooling across windows is a different quantity than the one it was trained
on — disorder windows instead, and says so in the output.

Read each head's model card before acting on a number. The stability head's
honest out-of-domain correlation is about 0.44 Spearman, which makes it a
ranking signal and not a measurement.
