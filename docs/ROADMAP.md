# Roadmap

What is coming next, and what is not.

This file was rewritten for `v0.6.0-rc1`. The version before it listed
nineteen phases of a Python application as done — structure prediction,
docking, molecular dynamics, a plugin marketplace, a VR mode — none of which
exists any more. Leaving it in place would have made the published roadmap
contradict the software it was shipped with.

## Current status: v0.6.0-rc1

Four trained heads over frozen ESM-2 embeddings — disorder, solvent
accessibility, stability and solubility — with a command-line tool for batch
work and a Tauri desktop application with a structure viewer. Everything a
prediction rests on is recorded: head build, weights digest, device, batch and
chunk size, input and output digests, and the limitations from the model card.

The command-line tool is the measured and tested part. What makes this a
release candidate rather than a release is below.

## Before dropping the `-rc1`

In order. Each is a thing that is currently unknown or unfinished, not a
feature.

- **Produce the artefacts at all.** The release workflow has never run. The
  tag that triggers it is its first test, and no installer has ever been built
  on macOS or Linux.
- **Signed installers.** Apple notarization, Windows Authenticode, GPG for the
  AppImage. Blocked on obtaining certificates, which costs money rather than
  effort.
- **Agree across platforms.** Every number in the documentation comes from one
  Windows workstation. CI builds and tests on three operating systems, but
  nothing has checked that they produce the same values. `opendna selftest`
  is the tool for this; it needs running on the other two.
- **Load the embedding model concurrently.** Two runs cannot read the Hugging
  Face cache at the same time; on Windows the second is refused the weights
  file. Staging a bundle works around it and is documented, but a tool whose
  own `split` command exists to run parts in parallel should not need a
  workaround for it.
- **Let `selftest` check the heads that are present.** It needs all four
  installed and exits 3 with fewer, which is wrong for the common case: a lab
  that wants only disorder cannot verify the head it has. `opendna models`
  hashes the weights against their recorded digest and works on one head, so
  the model cards point there instead, but the stronger check should not be
  all-or-nothing.
- **Check resuming at the scale it is for.** `--checkpoint` is verified
  byte-identical across an interruption on runs of a few chunks, including a
  real process kill. Nothing has tested a run of tens of thousands of
  sequences interrupted hours in, and none of it has been repeated on a GPU.

## After that

Ordered by how much it would change what somebody can conclude from a result.

### Measurement

- **An external benchmark for solubility and accessibility.** Neither has one.
  For solubility the obstacle is real: the reference sets are behind terms
  that forbid redistribution or belong to retired services. Saying there is no
  number beats quoting the in-domain figure as though it were comparable, but
  it is still a gap.
- **A CAID entry rather than a reimplementation.** The 0.941 on CAID3
  Disorder-PDB was produced by running the published protocol against the
  reference file, independently recomputed in numpy, and is not an official
  entry. The CAID4 deadline needs checking.
- **Out-of-domain detection.** The disorder head's confidence predicts error,
  which is not the same thing: a sequence from a family it never saw can still
  produce a confident wrong answer. The one proxy tried here — whether a
  residue's 5-mer appeared in training — carried no information at all, and
  that rejection is recorded so it is not retried blindly.
- **Intervals that vary with the input.** Split conformal gives a constant
  half-width, so a regressor's interval is wider than it needs to be where the
  head is reliable and narrower where it is not. The conditional coverage on
  each card shows where. A normalised or locally adaptive variant would fix
  the shape; it also needs more held-out data than some of these splits have.
- **Honest coverage for accessibility.** Its intervals undercover at every
  level, because clustering the splits by sequence identity breaks the
  exchangeability conformal assumes. Clustering is the right way to build the
  splits, so the fix is a method that does not need the assumption.

### Operations

- **Run the pipelines against their engines.** The Nextflow and Snakemake
  modules have never been executed by Nextflow or Snakemake: neither is
  installed on the machine they were written on. What is verified is the
  behaviour they depend on.
- **Resume inside a pipeline.** Both engines give a retried task a fresh
  working directory, so a checkpoint has to live somewhere that outlives the
  attempt. Where that is depends on the cluster's filesystem.
- **A GPU other than one.** The finding that batching costs time on a GPU
  comes from a single RTX 2000 Ada. `--batch-tokens` exists so somebody can
  measure theirs.

### Possibly

Not promised, and each would need its own justification before being started.

- More heads, where a dataset exists that can be redistributed and a baseline
  exists to be measured against.
- A larger embedding model, if one ever helps. ESM-2 650M was tried and
  rejected: it made disorder worse on every external metric for four times the
  weights.
- Structure-aware features, now that the accessibility head exists.

## Not planned

Stated so nobody waits for them. All of these were advertised by `v0.5.x` and
removed in the rewrite:

- Structure prediction, inverse folding, docking, molecular dynamics, free
  energy perturbation
- Antibody-specific models, plasmid tools, a model hub, project templates
- A server deployment, a plugin marketplace, real-time co-editing, a VR mode

The reason for removing them is the reason for not planning them: a platform
advertising nine things it did badly was worth less than a tool doing four
things with numbers attached. Anything added back has to arrive with a
measured number and a stated baseline, like the four heads did.

## Versioning

[Semantic versioning](https://semver.org): `MAJOR.MINOR.PATCH[-pre]`.

Pre-1.0, the command-line interface, the output formats and the head metadata
schema may change between minor versions. When they do, the changelog says so.
Head versions are separate from the project's: a head carries its own version
and a build id derived from its weights, configuration and data, so a result
can be traced to the exact model that produced it regardless of which release
ran it.

## Contributing to the roadmap

Open an issue or a pull request with the use case, a rough idea of the effort,
and what it depends on. For anything in the Measurement section, the most
useful contribution is a number: a benchmark run, a reference set that can be
redistributed, or a counter-measurement on hardware that is not this one.
