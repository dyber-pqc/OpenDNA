//! Builds embedding caches and trains the `OpenDNA` prediction heads.
//!
//! ```text
//! # once per dataset: pass every sequence through ESM-2 (the slow step)
//! cargo run --release -p opendna-train --features cuda -- embed --task disorder
//!
//! # then train, which takes minutes
//! cargo run --release -p opendna-train --features cuda -- train --task disorder
//! ```
//!
//! On Windows a CUDA build needs `scripts/cargo-cuda.ps1` in place of `cargo`.

#![allow(clippy::print_stdout)]

mod bench;
mod cache;
mod card;
mod data;
mod embed;
mod metrics;
mod train;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand, ValueEnum};
use opendna_ml::esm2::ModelSize;
use std::path::PathBuf;

/// A prediction task, matching a dataset produced by the `datasets` workspace.
#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum Task {
    /// Change in folding free energy for a point mutation.
    Stability,
    /// Whole-protein solubility.
    Solubility,
    /// Per-residue intrinsic disorder.
    Disorder,
}

impl Task {
    /// Name used for dataset directories and output files.
    pub fn name(self) -> &'static str {
        match self {
            Self::Stability => "stability",
            Self::Solubility => "solubility",
            Self::Disorder => "disorder",
        }
    }
}

/// Which ESM-2 checkpoint to embed with.
#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum Embedder {
    /// 8M parameters. Fast, and weak; intended for smoke tests.
    Esm2Small,
    /// 35M parameters.
    Esm2Medium,
    /// 150M parameters. The default: the best quality that still embeds
    /// these datasets in minutes on a 16 GB GPU.
    Esm2Large,
    /// 650M parameters.
    Esm2XLarge,
}

impl From<Embedder> for ModelSize {
    fn from(value: Embedder) -> Self {
        match value {
            Embedder::Esm2Small => ModelSize::Small8M,
            Embedder::Esm2Medium => ModelSize::Medium35M,
            Embedder::Esm2Large => ModelSize::Large150M,
            Embedder::Esm2XLarge => ModelSize::XLarge650M,
        }
    }
}

#[derive(Debug, Parser)]
#[command(name = "opendna-train", about = "Embed datasets and train OpenDNA's prediction heads")]
struct Cli {
    /// Directory holding the built datasets (`<root>/<task>/data/*.parquet`).
    #[arg(long, default_value = "../datasets/out", global = true)]
    datasets: PathBuf,
    /// Where embedding caches are written.
    #[arg(long, default_value = "cache", global = true)]
    cache: PathBuf,
    /// Embedding model.
    #[arg(long, value_enum, default_value_t = Embedder::Esm2Large, global = true)]
    embedder: Embedder,
    /// Where `bench` writes its reports, and where a card looks for the
    /// external numbers to quote. Reports are matched on the embedding model,
    /// so a card cannot pick up a figure measured on a different one.
    #[arg(long, default_value = "benchmarks", global = true)]
    benchmarks: PathBuf,
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Pass every sequence in a dataset through the embedding model and cache
    /// the result. Safe to re-run: cached sequences are skipped.
    Embed {
        /// Task whose sequences to embed.
        #[arg(long, value_enum)]
        task: Task,
    },
    /// Train a head on cached embeddings.
    Train {
        /// Task to train.
        #[arg(long, value_enum)]
        task: Task,
        /// Where to write weights, metadata and metrics.
        #[arg(long, default_value = "../models")]
        out: PathBuf,
        /// Maximum epochs.
        #[arg(long, default_value_t = 100)]
        epochs: usize,
        /// Rows per optimisation step. Ignored by the disorder head, which
        /// steps once per protein because sequences differ in length.
        #[arg(long, default_value_t = 256)]
        batch_size: usize,
        /// `AdamW` learning rate.
        #[arg(long, default_value_t = 1e-3)]
        learning_rate: f64,
        /// Stop after this many epochs with no validation improvement.
        #[arg(long, default_value_t = 10)]
        patience: usize,
        /// Seed for shuffling and initialisation.
        #[arg(long, default_value_t = 20_260_101)]
        seed: u64,
    },
    /// Re-render a model card from a run's saved `<task>.metrics.json`.
    ///
    /// Training writes the card already; this exists so that editing the
    /// hand-written prose — the summary, the limitations — does not mean
    /// retraining, and so that a card is never edited in place. The numbers
    /// always come from the report the run produced.
    Card {
        /// Task whose card to re-render.
        #[arg(long, value_enum)]
        task: Task,
        /// Directory holding `<task>.metrics.json`, where the card is written.
        #[arg(long, default_value = "../models")]
        out: PathBuf,
    },
    /// Score a head against an external reference set, so its numbers can be
    /// compared with published ones.
    ///
    /// The reference file is supplied rather than downloaded. Some of these
    /// sets carry no licence, which permits evaluation but not
    /// redistribution, so none of them is bundled or built into a dataset.
    Bench {
        /// Which reference set.
        #[arg(long, value_enum)]
        suite: Suite,
        /// Path to the reference file. For `caid3-disorder-pdb` this is
        /// `disorder_pdb.fasta` from the CAID repository, which the
        /// `datasets` workspace downloads into its cache.
        #[arg(long)]
        reference: PathBuf,
        /// Directory of per-assay score files, for suites whose reference is
        /// an index rather than the data itself (`proteingym-stability`).
        #[arg(long)]
        assays: Option<PathBuf>,
        /// Directory holding the trained heads.
        #[arg(long, default_value = "../models")]
        models: PathBuf,
        /// Where to write the report. Printed to standard output as well.
        #[arg(long)]
        out: Option<PathBuf>,
        /// Decision threshold for the threshold-dependent metrics. Left at
        /// the value training used; tuning it here would be fitting to the
        /// benchmark.
        #[arg(long, default_value_t = 0.5)]
        threshold: f64,
    },
}

/// External reference sets this command knows how to score.
#[derive(Copy, Clone, Debug, PartialEq, Eq, ValueEnum)]
enum Suite {
    /// CAID3 Disorder-PDB: 319 proteins with per-residue disorder labels and
    /// a mask for residues the assessment did not cover.
    Caid3DisorderPdb,
    /// `ProteinGym`'s stability-like assays, excluding every assay derived from
    /// Tsuboyama 2023 — which is the stability head's training data. What is
    /// left is whole proteins far larger than anything the head was trained
    /// on, so it measures generalisation rather than fit.
    ProteingymStability,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    let model: ModelSize = cli.embedder.into();

    match cli.command {
        Command::Embed { task } => {
            embed::run(task, model, &cli.datasets, &cli.cache)
                .with_context(|| format!("embedding the {} dataset", task.name()))?;
        }
        Command::Train { task, out, epochs, batch_size, learning_rate, patience, seed } => {
            let config = train::TrainConfig { epochs, batch_size, learning_rate, patience, seed };
            let report = match task {
                Task::Stability => train::stability(&cli.datasets, &cli.cache, &out, model, &config),
                Task::Solubility => train::solubility(&cli.datasets, &cli.cache, &out, model, &config),
                Task::Disorder => train::disorder(&cli.datasets, &cli.cache, &out, model, &config),
            }
            .with_context(|| format!("training the {} head", task.name()))?;
            card::write(task, &report, &out, &cli.benchmarks)?;
            println!("\n{}", serde_json::to_string_pretty(&report)?);
        }
        Command::Card { task, out } => {
            let path = out.join(format!("{}.metrics.json", task.name()));
            let text = std::fs::read_to_string(&path)
                .with_context(|| format!("reading {}; train the head first", path.display()))?;
            let report: train::Report =
                serde_json::from_str(&text).with_context(|| format!("parsing {}", path.display()))?;
            card::write(task, &report, &out, &cli.benchmarks)?;
        }
        Command::Bench { suite, reference, assays, models, out, threshold } => {
            let report = match suite {
                Suite::Caid3DisorderPdb => {
                    let text = std::fs::read_to_string(&reference)
                        .with_context(|| format!("reading the reference set {}", reference.display()))?;
                    let entries = bench::read_caid_reference(&text)
                        .with_context(|| format!("parsing {}", reference.display()))?;
                    println!("{} proteins in {}", entries.len(), reference.display());
                    bench::disorder(&entries, &models, model, threshold)
                }
                Suite::ProteingymStability => {
                    let dir = assays.ok_or_else(|| {
                        anyhow::anyhow!(
                            "--assays <dir> is required for this suite: it holds the per-assay \
                             score files that --reference indexes"
                        )
                    })?;
                    let (assays, notes) = bench::read_proteingym(&reference, &dir)?;
                    for note in &notes {
                        println!("  note: {note}");
                    }
                    println!("{} assays to score", assays.len());
                    bench::stability(&assays, &models, model)
                }
            }
            .with_context(|| format!("benchmarking against {suite:?}"))?;
            println!("\n{}", bench::render(&report));
            if let Some(path) = out {
                std::fs::write(&path, serde_json::to_string_pretty(&report)?)
                    .with_context(|| format!("writing {}", path.display()))?;
                println!("Wrote {}", path.display());
            }
        }
    }
    Ok(())
}
