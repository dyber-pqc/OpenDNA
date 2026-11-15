# Validation

This page is for whoever has to sign off on using OpenDNA for real work: a QA
reviewer, a core facility lead, somebody writing a methods section. It states
what has been checked, by whom, how, and what has not been.

It is not a claim that OpenDNA is validated for your purpose. Validation is
against an intended use, and only you know yours. What this gives you is the
evidence to do that assessment, and an honest account of where the evidence
runs out.

Everything below was measured on the hardware named with it. Where a number
comes from one machine, it says so, because a number from one machine is
weaker evidence than it looks.

## What the software is

Four small networks on top of frozen ESM-2 embeddings. The language model is
never fine-tuned, so each head is a few hundred kilobytes of weights over a
568 MB embedding model that is itself a published third-party checkpoint
(`facebook/esm2_t30_150M_UR50D`).

| Head | Predicts | Honest out-of-domain performance |
|---|---|---|
| `disorder` | per-residue intrinsic disorder | AUROC 0.941 on CAID3 Disorder-PDB |
| `burial` | per-residue relative solvent accessibility | see model card |
| `solubility` | whole-protein solubility, *E. coli* cell-free | see model card |
| `stability` | ΔΔG for a named point substitution | ~0.44 Spearman out of domain |

The stability figure is the one to read carefully. 0.44 Spearman makes it a
ranking signal for prioritising constructs, not a measurement of ΔΔG. Each
head's model card states its own limitations and the CLI copies them into
every output file, so a number cannot travel without them.

There is no fallback anywhere. A missing head is an error naming the files it
looked for. A sequence too long for the solubility head is refused rather than
scored by a different method. Nothing in OpenDNA estimates a property without
a trained model for it.

## Can I identify what I ran?

Yes, and it is checkable rather than asserted.

Each head records a semantic version, a build id digesting everything that
determined the weights (the dataset manifest, the hyperparameters, the
embedding model, the training code version), and the SHA-256 of its weights
file. `opendna models` rehashes the weights and reports `verified`,
`NOT VERIFIABLE` (metadata predating hashes) or `CORRUPT`.

```bash
opendna models --lock models.lock    # pin
opendna models --check models.lock   # fail unless the install is still that
```

`--check` catches a retrain that kept the same version number, because the
build id changes even when the version does not. Commit the lockfile beside
the analysis it produced.

**Checked:** appending one byte to a weights file is reported `CORRUPT`, makes
`opendna models` exit 3, and makes `opendna predict` refuse before loading
anything. A head whose build id differs from a lockfile fails `--check` with
both values named.

## Can I prove it works on this machine?

```bash
opendna selftest
```

Seventeen checks over a bundled ubiquitin sequence, through the same code path
`predict` uses rather than a parallel harness. Eight are invariants that hold
for any build of these heads — one value per residue, probabilities within
`[0,1]`, accessibility within `[0,1.25]`, the hydrophobic core less accessible
than the chain-forming lysines, L8P more destabilising than L8M, and a second
identical run giving identical values. Nine are numbers recorded from named
builds, with tolerances.

A pinned number is checked only against the build it was recorded from.
Against another build it reports `not checked` and names both, because nobody
has measured what that head does on this fixture. A retrain is therefore
expected to leave those unchecked until new values are recorded; the invariants
still run.

**Checked, and this is the part worth reading:** burial's weights were copied
over the disorder head and the metadata rewritten so the file hashes correctly.
`opendna models` passed that installation completely clean — every head
`verified`. The self-test failed three pinned checks and exited 5. A checksum
cannot detect a model that is intact and wrong; this can.

The fixture's positions were chosen for that case. Disorder and burial share
an architecture and differ only in the squash on the output, so at some
positions their numbers agree to 0.004 and a pin there would survive the
swap. The positions used are ones where the two disagree by more than a
quarter.

**Tolerances are a judgement, not a measurement.** They were set wide enough
to absorb a different BLAS or device and narrow enough that a wrong model
fails. A failure that lands just outside one is worth reporting, not widening.

## How reproducible are the numbers?

Exactly this much:

| | |
|---|---|
| Same input, same device, same `--batch-tokens` | **byte-identical** |
| Same input, same device, different `--batch-tokens` | ~0.2% of values differ |
| Same input, CPU vs GPU | ~0.3% of values differ |

Measured on 200 sequences and 35,033 residues. Across devices, 102 of 35,033
disorder probabilities differed, by at most 0.0001 and 0.0000003 on average.
That is the f32 rounding floor, not a disagreement about biology, and it moves
no disorder call at any sensible threshold.

It does mean a result file from a GPU and one from a CPU are **not the same
bytes**. Do not diff them and do not compare their checksums.

The cause in both cases is the order of floating-point summation: padding
changes it, and so does different silicon. Device and batch size are recorded
in every run manifest, which makes the table above checkable — two manifests
agreeing on input digest, head build, device and batch size should have
produced the same output digest, and if they did not, something is wrong worth
finding.

Driving one model from several threads at once on CUDA perturbs the low bits,
because cuBLAS picks differently shaped reductions under concurrent load. The
CLI is serial, which is why.

**Checked:** byte-identical repeat runs on both CPU and an RTX 2000 Ada. All
seventeen self-test checks pass on both, with values pinned on CPU.

## Can I run it without a network?

```bash
opendna stage --to /mnt/usb/opendna-models   # on a connected machine
opendna --models ./opendna-models --offline selftest
```

`stage` writes one directory holding the four heads, their model cards, the
embedding model's own files, `models.lock`, a `sha256sums.txt` in the format
`sha256sum -c` reads, and a `LICENSES.md`. It copies what the staging machine
already resolved rather than re-fetching on the target, so the bundle is what
was tested. It refuses to stage an installation that does not verify.

`--offline` is a hard promise: nothing reaches the network, and a missing
embedding model is an error naming the two files it wanted and the command
that makes them, rather than a stall.

**Checked:** with `HF_HOME` pointed at an empty directory so the cache held
nothing, `--offline` passed all seventeen self-test checks against a staged
bundle and produced disorder values identical to the online run.
`sha256sum -c sha256sums.txt` verified all fourteen files (four heads with
weights, metadata and card each, plus the embedding model's two). With nothing
staged, `--offline` exits 3 with the staging instructions.

## What does a failure tell my pipeline?

| | | |
|---|---|---|
| 0 | it worked | — |
| 1 | an unanticipated failure | report it |
| 2 | the command asked for something that does not exist | fix the command |
| 3 | the installation is wrong | fix the machine; retrying will not help |
| 4 | the data is wrong | fix the input; retrying will not help |
| 5 | the checks ran and did not hold | do not use results from this machine |

Anything not classified is 1, deliberately: a failure nobody anticipated is
not one a caller can be told how to handle.

`predict` streams results to standard output, so a failing run leaves standard
output empty — a pipe collecting results never receives an error as though it
were data.

**Checked:** all twelve cases in
[`tests/exit_codes.rs`](https://github.com/dyber-pqc/OpenDNA/blob/main/crates/opendna-cli/tests/exit_codes.rs),
against the compiled binary, with the corrupt and swapped fixtures built from
a copy of the real models.

## Can I show what produced a result?

Every run that writes an output file writes `out.manifest.json` beside it:
input path and SHA-256 **of the bytes read**, output path and SHA-256, row
count, head task/version/build/weights-hash, embedding model, device, batch
size, UTC start, wall-clock duration, the arguments as given, the head's
licence, and the model card's limitations.

The input is hashed from the bytes in memory rather than by re-reading the
file, so the digest describes what was used even when the input arrived
through a pipe and has no path.

The embedding model is not hashed by default: at 568 MB it costs about as long
as a small run. A staged bundle already records the digest, so a staged install
carries it for free; otherwise the field is null and `sha256_source` says why.
An absent field with a reason is honest. A missing field somebody assumes was
checked is not.

## What are my obligations if I pass this on?

Three heads are Apache-2.0. The `solubility` head is **CC BY-SA 2.1 JP**: it is
trained on eSOL, which carries that licence, and because the licence is
share-alike — and because whether trained weights are a derivative work of
their training data is an open legal question this project will not answer in
its own favour — the weights carry the same terms.

A staged bundle is a redistribution. `opendna stage` writes a `LICENSES.md`
grouping heads by licence and stating when passing the bundle on carries
obligations, and each card travels beside its weights with the attribution its
licence requires. Required attribution for eSOL: *"eSOL © Hideki Taguchi
(Tokyo Institute of Technology) licensed under CC Attribution-Share Alike 2.1
Japan"*.

All of it is read out of the model cards rather than written into the program,
so a notice cannot claim terms the file beside the weights does not. A head
whose card declares no licence is reported as `unstated` and treated as
possibly obliging.

## What has not been checked

Stated plainly, because a validation document that lists only successes is
marketing.

- **One machine.** Every number here comes from a single Windows workstation
  with an RTX 2000 Ada. CI builds on three operating systems, but the
  measurements above were not repeated on them. Cross-platform numerical
  agreement is untested.
- **No GPU other than one.** The finding that batching costs time on a GPU is
  from that one card. Another may behave differently, which is why
  `--batch-tokens` is a flag.
- **Timing figures are approximate.** The CPU gain from batching measured a
  tenth in one session and a sixth in another. Two earlier attempts, taken
  while a compile competed for the cores, produced an overstated figure and
  then none at all. If you benchmark, interleave the settings and report the
  spread.
- **Tolerances in the self-test are a judgement**, set on one machine, not a
  measured bound on acceptable variation.
- **No clinical or diagnostic validation of any kind.** These are research
  tools. The stability head in particular is a ranking signal at ~0.44
  Spearman out of domain.
- **Metrics on each head's own test split are not comparable to published
  leaderboard figures** without running that leaderboard's protocol. The
  disorder head's CAID3 number was produced by running the CAID protocol; the
  others' were not.
- **No signed installers.** Binaries are unsigned, so operating systems will
  warn. Code-signing certificates have not been obtained.
- **Calibration is unmeasured.** Nothing here establishes that a disorder
  probability of 0.7 corresponds to a 70% chance of disorder, and no head
  abstains on inputs unlike its training data. Treat the outputs as scores for
  ranking, not as probabilities to threshold against a cost model.

## Reproducing the checks

```bash
opendna models --check models.lock   # the install is what it was
opendna selftest                     # it computes what it recorded
opendna --device cpu selftest        # and on the CPU too, where a GPU exists
cargo test --workspace               # unit and contract tests
cargo test --release -p opendna-cli -- --ignored   # the two needing inference
```

The exit-code test needs trained heads installed and skips with a message when
they are absent, because a test that fails on every machine without them gets
disabled and then checks nothing at all.
