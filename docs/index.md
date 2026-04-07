# OpenDNA

**The People's Protein Engineering Platform**

OpenDNA is a free, open-source protein engineering and structural biology platform that runs on consumer hardware. It combines structure prediction, sequence design, property analysis, mutation effect prediction, and 3D visualization in a single integrated desktop application.

## Why OpenDNA?

The dominant commercial protein engineering platforms cost ~$50,000–$200,000 per seat per year, lock features behind paywalls, run only on workstations or HPC clusters, and require days of training. Academic alternatives like Rosetta exist but are command-line driven, written in C++, and steep enough to learn that most undergraduates never get past the first tutorial.

OpenDNA closes that gap. The features you'd use Schrödinger Maestro/Prime/BioLuminate for — structure prediction, inverse folding design, property analysis, mutation effects, basic MD — all run on a gaming laptop, all free, all open source.

## Quick links

- [Getting Started](GETTING_STARTED.md) — install and first run
- [User Guide](USER_GUIDE.md) — every feature explained
- [Tutorials](TUTORIALS.md) — step-by-step walkthroughs
- [Cookbook](COOKBOOK.md) — recipes for common tasks
- [API Reference](API_REFERENCE.md) — REST endpoints
- [Architecture](ARCHITECTURE.md) — how the system works
- [The Science](SCIENCE.md) — what each algorithm does
- [FAQ](FAQ.md) — common questions
- [Troubleshooting](TROUBLESHOOTING.md) — when things break
- [Roadmap](ROADMAP.md) — what's next

## Highlights

### Structure prediction
ESMFold v1 from Meta AI runs in seconds on GPU and produces atomic-resolution predictions from a single sequence — no MSA needed.

### Inverse folding design
ESM-IF1 generates alternative sequences that fold into the same backbone. Use it for stability optimization, removing problematic regions, or aggressive redesign.

### Iterative optimization
The killer feature: automated fold→design→fold→keep best loop. The platform handles the boilerplate.

### ~50 analyses out of the box
Lipinski's Rule of Five, hydropathy, disorder, transmembrane prediction, signal peptides, aggregation, phosphorylation, glycosylation, secondary structure, Ramachandran, pockets, bonds, pKa, MolProbity validation, antibody CDR detection, QSAR descriptors, multi-objective Pareto optimization, and more.

### LLM agent framework
First protein engineering platform with built-in tool-calling LLM agent. Issue natural language goals like *"Analyze p53 and predict the effect of R175H"* and the system plans, executes, and reports.

### Cross-platform desktop installer
Tauri-based installer for Windows, macOS, and Linux. The Python backend runs as a sidecar process.

## License

Apache 2.0 + Commons Clause. Free for academia, research, education, and personal use. Contact for commercial licensing terms.
