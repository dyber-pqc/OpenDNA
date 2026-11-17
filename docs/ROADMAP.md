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
- **Signed installers.** The pipeline is wired for all of it and uses
  whichever credentials exist, so what is left is buying them: an Apple
  Developer account for notarization and a Windows code-signing certificate,
  which since June 2023 means renting signing from a cloud service rather than
  holding a key file. [SIGNING.md](SIGNING.md) says what each one buys and what
  secret it goes in. The checksum signature needs no certificate at all and is
  waiting only on a key being generated.
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

- A larger embedding model, if one ever helps. ESM-2 650M was tried and
  rejected: it made disorder worse on every external metric for four times the
  weights.
- More heads beyond the antibody one planned below, where a dataset exists that
  can be redistributed and a baseline exists to be measured against.
- Structure-aware features, which stop being speculative once predicted
  coordinates are available: see tranches 3 and 5 below.

## Putting the removed capabilities back

`v0.5.x` advertised structure prediction, docking, molecular dynamics,
free-energy calculation, sequence and backbone design, antibody modelling and
an HTTP API. The rewrite removed all of them, and the plan now is to put them
back — under the condition that made removing them worth doing.

**The condition.** A capability arrives with a measured number and a stated
baseline, or it does not arrive. That is what separates this from the version
that listed nine things and did them badly. For a trained head it means a
held-out split, a baseline it beats, and a generated card. For an integration
it means recording which engine ran, at which version, with which digest, in
the run manifest — and refusing when the engine is absent rather than
substituting something cheaper.

**Implement or integrate.** Six of these are decades of specialist work that
other people have already done and published. Writing a force field, a docking
search or an AlphaFold trunk here would produce a worse version of software
that already exists, which is the failure this project was rewritten to
escape. So the plan distinguishes:

- **Implemented here** where the model is small enough to port honestly and
  the licence permits it, and where doing so keeps the no-network, no-runtime
  promise.
- **Integrated** where the right answer is to drive an existing engine, with
  the same provenance discipline the heads get. OpenDNA has no concept of an
  external engine today; building one is the prerequisite for four of these,
  and it is the next structural piece of work.

### Order of work

Each tranche is shippable on its own, and each later one depends on an earlier
one rather than on all of them.

**1. Python bindings.** The notebook integration from the list. A package
wrapping the command-line tool, returning per-residue results as data frames
with the run manifest attached, so a notebook cannot lose the provenance the
CSV carries. Fits the local-only premise exactly and makes the four existing
heads reachable from where this audience works. Smallest item on the list and
first because everything after it is easier to demonstrate from a notebook.

**2. An external-engine adapter. Done.** `crates/opendna-engine` discovers an
installed engine, identifies it by the version string it prints and the digest
of the file that would run, and pins it in an `engines.lock` the way
`models.lock` pins a head. `opendna engines` is the command. Four engines are
declared — ESMFold, ColabFold, Vina and an OpenMM-capable interpreter — and
ESMFold and ColabFold are driven by tranche 3; Vina and an OpenMM-capable
interpreter are declared but not yet used, which the command says outright.

**3. Structure prediction, integrated. Done.** `opendna fold` drives a local
ESMFold or ColabFold install through the adapter and writes one PDB per
sequence with a manifest naming the engine, its version, the digest of the file
that ran and the command line it was given. Not a port: ESMFold is 2.6 GB with
a folding trunk whose faithful reimplementation is a project of its own, and a
half-faithful one would produce coordinates nobody should trust.

The part worth saying out loud is the check. Every file in the engine's output
directory is parsed and matched to a requested sequence by its residues rather
than by its filename, so a structure filed against the wrong sequence — the
ordinary way a folding batch goes quietly wrong — exits 5 instead of being
written. Ties that the residues cannot break are refused with the candidates
listed, not resolved by directory order.

What is not done: multimers, which need each engine's own chain-separator
convention and a different check than "one chain, this sequence"; and any use
of the coordinates beyond writing them out. The desktop application opens a PDB
file, so a folded model can be viewed, but nothing yet measures one or feeds it
back into a head. `opendna-analysis` already computes solvent accessibility
from a structure, which is the obvious next thing to connect and is not
connected.

**4. An antibody head.** The only item on the list that adds science rather
than access, and the one that fits the existing architecture without any new
machinery: a dataset built from OAS or SAbDab, a head trained on frozen ESM-2
embeddings, a measured baseline, a generated card. Developability or humanness
rather than structure. Licence terms of both sources need reading before
anything is built, as they did for eSOL.

**5. Sequence design.** ProteinMPNN is small enough to port honestly — on the
order of a million parameters, published under a permissive licence — and
inverse folding is a real capability rather than a wrapper. It needs a backbone
as input, which tranche 3 now produces.

**6. Docking, integrated.** AutoDock Vina through the adapter. A scoring
function and a conformational search written here would be a worse Vina.

**7. Molecular dynamics, integrated.** OpenMM through the adapter, which means
a Python dependency returning to the project — as a declared, optional engine
rather than as the backend the rewrite deleted. Free-energy calculation sits on
top of this and comes after it, not beside it.

**8. An HTTP API, if it is still wanted.** Technically days of work and the
only item here that cuts against the project's own premise: "no server, no
account, no network: sequences stay where you opened them" is in the first
paragraph of the README and is why some people can use this at all. If it
ships it ships as a separate opt-in binary, bound to loopback, off by default,
and documented as what it is. A hosted service is a different proposition
again, and this roadmap does not plan one: it would move other people's
unpublished sequences onto somebody else's machine, which is the problem
OpenDNA exists to avoid.

### Still not planned

- A plugin marketplace, real-time co-editing, a VR mode, plasmid tools and a
  model hub. These were in `v0.5.x` and nothing on the current list needs them.
- Backbone design by diffusion. RFdiffusion-class models are large, depend on
  the structure machinery of tranche 3, and would be an integration at best.
  Revisit after tranche 5, not before.

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
