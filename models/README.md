# Models

Model weights are never committed to this repository; they are downloaded or
built on demand.

Two things live here:

- **OpenDNA's own prediction heads**, trained by the
  [training workspace](../training) and described below.
- **Third-party models** the Python backend downloads on first use —
  ESMFold, ProteinMPNN, ESM-2 and others, listed in `manifest.yaml` and
  cached under `~/.opendna/models/`. That backend is being replaced by the
  Rust crates and will be removed at cutover; the Rust side fetches ESM-2
  through `opendna-ml` instead, into the standard Hugging Face cache.

## OpenDNA prediction heads

Each is a small network on top of **frozen** ESM-2 embeddings — the language
model itself is never fine-tuned.

## What a trained head consists of

| File | Purpose |
|---|---|
| `<task>.safetensors` | the weights |
| `<task>.metadata.json` | which embedding model and width the head expects |
| `<task>.metrics.json` | validation and test metrics, and the baseline |
| `<task>.README.md` | the model card, generated from the metrics |

The metadata is checked at load time, so a head can never be paired with
embeddings it was not trained on — the application refuses rather than
returning numbers computed from the wrong input.

## Building them

```bash
cd training
cargo run --release -p opendna-train -- embed --task stability
cargo run --release -p opendna-train -- train --task stability
```

See [training/README.md](../training/README.md) for GPU setup and options.

## Publishing to Hugging Face

Publishing is a manual step, done by a maintainer. Nothing in this repository
uploads automatically, and no token is stored here.

1. Log in with your own account:

   ```bash
   hf auth login
   ```

2. Review the generated card. The metrics table, hyperparameters and kept
   epoch come from the run, but the intended-use and limitations sections are
   written by hand and should be re-read before each release — particularly
   if the training data changed.

3. Create the repository and upload:

   ```bash
   hf repo create <org>/opendna-stability --type model
   hf upload <org>/opendna-stability stability.safetensors
   hf upload <org>/opendna-stability stability.metadata.json
   hf upload <org>/opendna-stability stability.README.md README.md
   ```

Publish the dataset that produced the model first, or at least alongside it,
so the card's dataset link resolves.

## Honesty requirements

These apply to anything published from here:

- **Report the baseline.** Every card states what the model is compared
  against — the language model's zero-shot signal, the training mean, or the
  majority class. A model that does not beat its baseline is not published.
- **Test once.** The validation split chooses the epoch; the test split is
  evaluated afterwards, once. Nothing is tuned against test numbers.
- **Say what the data does not cover.** The limitation sections exist because
  each of these datasets is narrower than the task name suggests: stability
  is small single domains, solubility is one organism's expression assay, and
  disorder is annotated rather than exhaustive.
- **No silent fallbacks.** If a head is missing, the application says the
  prediction is unavailable. It never substitutes a heuristic and presents
  the result as a prediction.
