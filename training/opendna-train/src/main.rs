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
            card::write(task, &report, &out)?;
            println!("\n{}", serde_json::to_string_pretty(&report)?);
        }
        Command::Card { task, out } => {
            let path = out.join(format!("{}.metrics.json", task.name()));
            let text = std::fs::read_to_string(&path)
                .with_context(|| format!("reading {}; train the head first", path.display()))?;
            let report: train::Report =
                serde_json::from_str(&text).with_context(|| format!("parsing {}", path.display()))?;
            card::write(task, &report, &out)?;
        }
    }
    Ok(())
}
