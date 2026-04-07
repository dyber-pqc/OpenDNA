"""OpenDNA command-line interface."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(
    name="opendna",
    help="OpenDNA: The People's Protein Engineering Platform",
    no_args_is_help=True,
)
console = Console()


@app.command()
def fold(
    sequence: str = typer.Argument(..., help="Amino acid sequence to fold"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output PDB file path"),
    method: str = typer.Option("auto", "--method", help="Folding method (auto, esmfold)"),
    device: Optional[str] = typer.Option(None, "--device", help="Compute device (cuda, cpu, mps)"),
):
    """Predict the 3D structure of a protein from its amino acid sequence."""
    from opendna.engines.folding import fold as fold_protein

    console.print(f"[bold]Folding protein[/bold] ({len(sequence)} residues)")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing...", total=None)

        def on_progress(stage: str, frac: float):
            progress.update(task, description=stage)

        try:
            result = fold_protein(sequence, method=method, device=device, on_progress=on_progress)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    # Display results
    console.print(Panel(
        f"[green]Structure predicted successfully![/green]\n\n"
        f"Method: {result.method}\n"
        f"Mean confidence (pLDDT): {result.mean_confidence:.3f}\n"
        f"Residues: {len(result.confidence)}\n\n"
        f"{result.explanation}",
        title="Folding Result",
    ))

    if output:
        result.save(output)
        console.print(f"Structure saved to: [bold]{output}[/bold]")
    else:
        # Default output
        default_path = Path(f"folded_{sequence[:8]}.pdb")
        result.save(default_path)
        console.print(f"Structure saved to: [bold]{default_path}[/bold]")


@app.command()
def design(
    target: Path = typer.Argument(..., help="Target PDB structure file"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output FASTA file"),
    n: int = typer.Option(10, "-n", "--num-candidates", help="Number of candidates to generate"),
    temperature: float = typer.Option(0.1, "-t", "--temperature", help="Sampling temperature"),
    device: Optional[str] = typer.Option(None, "--device", help="Compute device"),
):
    """Design protein sequences for a given backbone structure."""
    from opendna.engines.design import DesignConstraints, design as design_protein

    if not target.exists():
        console.print(f"[red]File not found: {target}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Designing sequences[/bold] for {target.name} ({n} candidates)")

    constraints = DesignConstraints(num_candidates=n, temperature=temperature)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing...", total=None)

        def on_progress(stage: str, frac: float):
            progress.update(task, description=stage)

        try:
            result = design_protein(target, constraints=constraints, device=device, on_progress=on_progress)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    # Display results
    table = Table(title="Design Candidates")
    table.add_column("Rank", style="cyan")
    table.add_column("Score", style="green")
    table.add_column("Recovery", style="yellow")
    table.add_column("Sequence (first 40)", style="dim")

    for c in result.top(10):
        table.add_row(
            str(c.rank),
            f"{c.score:.3f}",
            f"{c.recovery:.1%}",
            str(c.sequence)[:40] + "...",
        )

    console.print(table)
    console.print(f"\n{result.explanation}")

    if output:
        result.to_fasta(output)
        console.print(f"\nSequences saved to: [bold]{output}[/bold]")


@app.command()
def evaluate(
    sequence: str = typer.Argument(..., help="Amino acid sequence to evaluate"),
):
    """Score and evaluate a protein sequence."""
    from opendna.engines.scoring import evaluate as eval_protein

    result = eval_protein(sequence)

    console.print(Panel(
        f"Overall Score: [bold]{result.overall:.2f}[/bold] / 1.00\n"
        f"Confidence: {result.confidence:.2f}\n\n"
        f"[bold]Breakdown:[/bold]\n"
        f"  Stability:      {result.breakdown.stability:.2f}\n"
        f"  Solubility:     {result.breakdown.solubility:.2f}\n"
        f"  Immunogenicity: {result.breakdown.immunogenicity:.2f}\n"
        f"  Developability: {result.breakdown.developability:.2f}\n"
        f"  Novelty:        {result.breakdown.novelty:.2f}\n\n"
        f"[bold]Summary:[/bold] {result.summary}\n\n"
        f"[bold]Recommendations:[/bold]\n"
        + "\n".join(f"  - {r}" for r in result.recommendations),
        title="Protein Evaluation",
    ))


@app.command()
def serve(
    port: int = typer.Option(8765, "-p", "--port", help="Port to serve on"),
    host: str = typer.Option("127.0.0.1", "-h", "--host", help="Host to bind to"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open the UI in your browser"),
):
    """Start the OpenDNA API server (the backend that powers the UI)."""
    from opendna.api.server import start_server
    console.print(Panel(
        f"[bold cyan]OpenDNA Server[/bold cyan]\n\n"
        f"API: http://{host}:{port}\n"
        f"Docs: http://{host}:{port}/docs\n"
        f"Health: http://{host}:{port}/health\n\n"
        f"Press Ctrl+C to stop.",
        title="Starting...",
    ))
    if open_browser:
        try:
            import webbrowser
            webbrowser.open(f"http://{host}:{port}/docs")
        except Exception:
            pass
    start_server(host=host, port=port)


@app.command()
def status():
    """Show hardware information and OpenDNA status."""
    from opendna.hardware.detect import detect_hardware

    hw = detect_hardware()

    console.print(Panel(
        hw.summary(),
        title="Hardware Status",
    ))

    # Check for installed models
    from opendna.storage.database import get_models_dir
    models_dir = get_models_dir()
    model_count = len(list(models_dir.iterdir())) if models_dir.exists() else 0
    console.print(f"\nModels directory: {models_dir}")
    console.print(f"Installed models: {model_count}")


@app.command()
def init(
    name: str = typer.Argument(..., help="Project name"),
    path: Optional[Path] = typer.Option(None, help="Project directory (default: current dir)"),
):
    """Initialize a new OpenDNA project."""
    project_dir = (path or Path.cwd()) / name
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create project structure
    (project_dir / "proteins").mkdir(exist_ok=True)
    (project_dir / "results").mkdir(exist_ok=True)
    (project_dir / "notebooks").mkdir(exist_ok=True)

    # Create project config
    config = {
        "name": name,
        "version": "0.1.0",
        "created": "auto",
    }

    import yaml
    (project_dir / "opendna.yaml").write_text(yaml.dump(config, default_flow_style=False))

    console.print(f"[green]Project '{name}' created at {project_dir}[/green]")
    console.print(f"\nProject structure:")
    console.print(f"  {name}/")
    console.print(f"  ├── proteins/      # Protein sequences and structures")
    console.print(f"  ├── results/       # Computation outputs")
    console.print(f"  ├── notebooks/     # Analysis notebooks")
    console.print(f"  └── opendna.yaml   # Project configuration")


models_app = typer.Typer(help="Manage ML models")
app.add_typer(models_app, name="models")


@models_app.command("download")
def models_download(
    model: Optional[str] = typer.Argument(None, help="Specific model to download (default: all required)"),
):
    """Download required ML model weights."""
    from opendna.storage.database import get_models_dir

    models_dir = get_models_dir()
    console.print(f"Models directory: {models_dir}")

    required_models = [
        ("facebook/esmfold_v1", "ESMFold - Structure prediction"),
        ("proteinmpnn", "ProteinMPNN - Sequence design"),
    ]

    if model:
        required_models = [(m, d) for m, d in required_models if model.lower() in m.lower()]

    for model_name, desc in required_models:
        console.print(f"\n[bold]Downloading {desc}...[/bold]")
        console.print(f"  Model: {model_name}")
        console.print(f"  Note: Models will be cached by HuggingFace/PyTorch on first use.")
        console.print(f"  Run 'opendna fold <sequence>' to trigger download.")

    console.print(f"\n[green]Model info complete.[/green]")
    console.print("Models are downloaded automatically on first use via HuggingFace Hub.")


@models_app.command("list")
def models_list():
    """List available and installed models."""
    table = Table(title="OpenDNA Models")
    table.add_column("Model", style="cyan")
    table.add_column("Size", style="yellow")
    table.add_column("Purpose", style="green")
    table.add_column("Status", style="bold")

    table.add_row("ESMFold", "~2.5 GB", "Structure prediction", "Available")
    table.add_row("ProteinMPNN", "~150 MB", "Sequence design", "Available (stub)")
    table.add_row("ESM-2 (650M)", "~2.5 GB", "Sequence embeddings", "Planned")
    table.add_row("DiffDock", "~500 MB", "Molecular docking", "Planned")

    console.print(table)


def main():
    app()


if __name__ == "__main__":
    main()
