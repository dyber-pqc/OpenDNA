# OpenDNA Model Cards

OpenDNA wraps several open-source ML models. This document follows the [Model Cards for Model Reporting](https://arxiv.org/abs/1810.03993) framework so users understand the capabilities, limitations, and biases of each model we use.

---

## Model Card 1: ESMFold v1 (Structure Prediction)

### Model Details
- **Developer**: Meta AI Fundamental AI Research (FAIR)
- **Year**: 2022 (paper 2023)
- **Architecture**: Transformer (ESM-2 protein language model + folding head)
- **Parameters**: ~3 billion
- **Training data**: 65 million UniRef50 sequences (no MSA, no template info)
- **Reference**: Lin, Z. et al. (2023). Evolutionary-scale prediction of atomic-level protein structure. *Science* 379, 1123–1130.

### Intended Use
- Predict 3D structure of natural and designed protein sequences
- Single-sequence inference (no MSA needed)
- Educational and research purposes

### Out of Scope
- Predicting structures of intrinsically disordered proteins (will give low pLDDT)
- Predicting protein complexes / multimers (use Boltz)
- Predicting small molecules or non-protein entities

### Performance
- **Mean per-residue accuracy**: comparable to AlphaFold2 for proteins with rich evolutionary history
- **5–10% gap** behind AlphaFold2 with MSA on novel folds
- **~60× faster** than AlphaFold2 (single-sequence vs MSA computation)
- **Memory**: ~6–8 GB peak for 200-residue protein

### Known Limitations
- Lower accuracy on **orphan proteins** (no homologs in training data)
- **Hallucinates confident structures** for nonsense or random sequences
- **Cannot handle non-standard amino acids** (selenocysteine, pyrrolysine, etc.)
- **Disordered regions** appear as low-pLDDT noise

### Biases
- **Dataset bias**: trained on UniRef which over-represents well-studied organisms (E. coli, human, yeast). Underrepresented organisms (viruses, archaea) may fold less accurately.
- **Length bias**: trained primarily on proteins under 1024 residues; longer proteins are folded in chunks with possible context loss.

### How to Verify Outputs
- Check the **mean pLDDT score** (>70 = trustworthy, <50 = likely incorrect)
- Compare to AlphaFold DB if a UniProt entry exists
- Run **MolProbity-style validation** (built into OpenDNA)

---

## Model Card 2: ESM-IF1 (Inverse Folding)

### Model Details
- **Developer**: Meta AI FAIR
- **Year**: 2022
- **Architecture**: Geometric Vector Perceptron (GVP) transformer
- **Parameters**: 142 million
- **Training data**: 12 million predicted structures from AlphaFold DB
- **Reference**: Hsu, C. et al. (2022). Learning inverse folding from millions of predicted structures. *ICML*.

### Intended Use
- Generate amino acid sequences predicted to fold into a given backbone
- Sequence diversification (vary residues, keep fold)
- Stability optimization
- Removing problematic regions (aggregation, immunogenicity)

### Out of Scope
- Designing entirely new backbones (use RFdiffusion)
- Predicting binding affinity changes
- Designing for specific function (just for fold)

### Performance
- **Native sequence recovery**: ~50% on test backbones
- **Generated sequences fold correctly**: typically 70–90% of the time when verified by re-folding with ESMFold
- **Inference time**: ~1–5 seconds per candidate on GPU

### Known Limitations
- Generated sequences may not preserve **active site geometry** unless explicitly fixed
- May introduce **aggregation-prone or hard-to-express** variants
- **Diversity-fidelity tradeoff** is controlled by temperature parameter
- **Backbone needs reasonable Cα geometry** to work well

### Recommended Workflow
1. Fold input → get backbone
2. ESM-IF1 design → get N candidates
3. Re-fold each candidate with ESMFold → verify
4. Score for stability, solubility, immunogenicity
5. Use **constrained design** if active site preservation is critical

---

## Model Card 3: ESM-2 8M (Conservation Scoring)

### Model Details
- **Developer**: Meta AI FAIR
- **Year**: 2022
- **Architecture**: Transformer encoder (BERT-style)
- **Parameters**: 8 million (smallest variant)
- **Training data**: 65 million UniRef50 sequences

### Intended Use in OpenDNA
- Per-residue conservation scoring via masked language model perplexity
- Each position is masked and the model's probability for the true amino acid is the conservation score
- Faster alternative to multiple sequence alignment for novel sequences

### Performance
- **Conservation correlates** with evolutionary conservation from MSA-based methods
- **Trade-off vs accuracy**: 8M is 200× smaller than ESM-2 650M; we use it for speed

### Limitations
- **Smaller than typical conservation models**, so noise is higher
- **Not as accurate as MSA-based methods** like ConSurf or Rate4Site for well-aligned families

---

## Model Card 4: LLM Providers (Optional)

OpenDNA supports multiple LLM providers for the chat and agent features. Each has different model cards published by their developers:

- **Ollama models** (local): each model has its own card on the Ollama hub
- **Anthropic Claude** (API): see https://www.anthropic.com/transparency
- **OpenAI GPT** (API): see https://openai.com/policies

### How OpenDNA uses LLMs
- **Intent parsing**: map natural language to actions
- **Tool calling**: invoke OpenDNA functions on the user's behalf
- **Explanation generation**: summarize results in plain language
- **Agent workflows**: multi-step protein engineering tasks

### Privacy
- **Local Ollama models** keep all data on the user's machine
- **API providers** send your prompts to their servers per their privacy policies
- Users can disable LLM features entirely; the platform always works without them via heuristic fallback

---

## General Caveats

For all models:

1. **Confidence intervals are not perfect.** A high-confidence wrong answer is still wrong.
2. **Out-of-distribution inputs** (unusual sequences, very large proteins) produce unreliable outputs.
3. **No model in OpenDNA should be used for clinical decisions** without independent expert review.
4. **Validate predictions experimentally** when stakes are high. Computational predictions are starting points, not endpoints.

## Reporting issues

If you find a case where OpenDNA's predictions are systematically wrong, please open an issue with:
- The input sequence/structure
- The expected output (and source)
- The actual output
- Hardware and version info

We can use these to improve model selection and add to our test cases.
