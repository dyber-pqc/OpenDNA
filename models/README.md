# OpenDNA Models

ML model weights are not committed to this repository due to their size.

## Automatic Download

Models are downloaded automatically on first use via HuggingFace Hub.

```bash
# Trigger download by running a fold
opendna fold MKTVRQERLKSIVRILERSKEPVSGAQLAEELS

# Or explicitly list available models
opendna models list
```

## Manual Download

Models are cached in `~/.opendna/models/` by default.

See `manifest.yaml` for the full list of supported models and their sources.
