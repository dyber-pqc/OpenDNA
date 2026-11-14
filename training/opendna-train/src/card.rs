//! Generates a Hugging Face model card from a training report.
//!
//! The card is assembled from the metrics the run actually produced, so the
//! numbers in it cannot drift from the numbers that were measured. The parts
//! that need judgement — what the model is for, where it fails — are written
//! here as prose, per task, and reviewed by hand before publishing.

use crate::train::Report;
use crate::Task;
use anyhow::{Context, Result};
use std::fmt::Write;
use std::path::Path;

/// Text that cannot be derived from the metrics.
struct Prose {
    summary: &'static str,
    dataset: &'static str,
    dataset_url: &'static str,
    license: &'static str,
    inputs: &'static str,
    outputs: &'static str,
    baseline: &'static str,
    limitations: &'static [&'static str],
    citation: &'static str,
}

fn prose(task: Task) -> Prose {
    match task {
        Task::Stability => Prose {
            summary: "Predicts the change in folding free energy (ΔΔG) caused by a single \
                      amino-acid substitution.",
            dataset: "opendna-stability",
            dataset_url: "https://github.com/dyber-pqc/OpenDNA/tree/main/datasets",
            license: "CC BY 4.0 (Tsuboyama et al. 2023, FireProtDB)",
            inputs: "The wild-type sequence's ESM-2 embedding at the mutated position, one-hot \
                     encodings of the wild-type and mutant residues, and the masked \
                     log-odds `log P(mutant) - log P(wild type)` at that position.",
            outputs: "A single ΔΔG value in kcal/mol, following the dataset's sign convention: \
                      negative is destabilising.",
            baseline: "The language model's masked log-odds used directly, with no trained head.",
            limitations: &[
                "Trained almost entirely on small, single-domain proteins of 32-72 residues. \
                 Behaviour on large multi-domain proteins, membrane proteins and complexes is \
                 untested.",
                "The source assay infers ΔΔG from protease resistance over a range of roughly \
                 -1 to 5 kcal/mol for ΔG. Mutations outside that range are absent from training, \
                 so strongly destabilising substitutions are under-represented.",
                "Only single substitutions. The model says nothing about combined mutations, \
                 insertions or deletions.",
                "Trained on frozen embeddings, so accuracy is bounded by what ESM-2 already \
                 encodes about the position.",
            ],
            citation: "Tsuboyama, K. et al. Mega-scale experimental analysis of protein folding \
                       stability in biology and design. Nature 620, 434-444 (2023).",
        },
        Task::Solubility => Prose {
            summary: "Predicts protein solubility from sequence.",
            dataset: "opendna-solubility",
            dataset_url: "https://github.com/dyber-pqc/OpenDNA/tree/main/datasets",
            license: "see the dataset card; sources differ",
            inputs: "The mean-pooled ESM-2 embedding of the sequence.",
            outputs: "A solubility percentage on the source assay's scale. Values above 100 occur \
                      in the source data and are not clipped.",
            baseline: "Predicting the training-set mean for every protein.",
            limitations: &[
                "Trained on E. coli cell-free expression measurements. Solubility in other hosts, \
                 or under different expression conditions, is a different quantity.",
                "Sequences are UniProtKB canonical sequences, not the exact expressed constructs; \
                 tags and truncations in the real experiments are not represented.",
                "A few thousand proteins is a small training set. Treat the output as a ranking \
                 signal for prioritising constructs, not as a predicted assay value.",
            ],
            citation: "Niwa, T. et al. Bimodal protein solubility distribution revealed by an \
                       aggregation analysis of the entire ensemble of Escherichia coli proteins. \
                       PNAS 106, 4201-4206 (2009).",
        },
        Task::Disorder => Prose {
            summary: "Predicts, for each residue, whether it lies in an intrinsically disordered \
                      region.",
            dataset: "opendna-disorder",
            dataset_url: "https://github.com/dyber-pqc/OpenDNA/tree/main/datasets",
            license: "CC BY 4.0 (DisProt)",
            inputs: "Per-residue ESM-2 embeddings. Sequences longer than the embedding model's \
                     limit are covered by overlapping windows.",
            outputs: "One probability per residue. The reported threshold is 0.5.",
            baseline: "Labelling every residue disordered.",
            limitations: &[
                "DisProt records disorder that has been experimentally demonstrated. Residues \
                 that are simply unannotated are treated as ordered during training, so the \
                 negative class contains an unknown number of undiscovered disordered residues.",
                "Annotation is biased toward proteins people chose to study, and toward longer \
                 disordered regions. Short linkers are under-represented.",
                "CAID test-set proteins are held out of training here, but numbers below are on \
                 this dataset's own test split and are not comparable to published CAID results \
                 without running the CAID protocol.",
            ],
            citation: "Aspromonte, M. C. et al. DisProt in 2024: improving function annotation of \
                       intrinsically disordered proteins. Nucleic Acids Research 52, D434-D441 (2024).",
        },
    }
}

/// Display name for a metric key, so the card reads as prose rather than as
/// field names.
fn label(key: &str) -> &str {
    match key {
        "spearman" => "Spearman ρ",
        "pearson" => "Pearson r",
        "rmse" => "RMSE",
        "mae" => "MAE",
        "auroc" => "AUROC",
        "auprc" => "AUPRC",
        "mcc" => "MCC",
        "f1" => "F1",
        "balanced_accuracy" => "Balanced accuracy",
        other => other,
    }
}

fn metrics_table(report: &Report) -> String {
    let mut keys: Vec<&String> = report.test.values.keys().collect();
    for k in report.validation.values.keys() {
        if !keys.contains(&k) {
            keys.push(k);
        }
    }
    keys.sort();

    let mut out = String::from("| Metric | Validation | Test | Baseline (test) |\n|---|---|---|---|\n");
    for key in keys {
        let cell = |m: &crate::train::SplitMetrics| {
            m.values.get(key).map_or_else(|| "—".to_string(), |v| format!("{v:.3}"))
        };
        let _ = writeln!(
            out,
            "| {} | {} | {} | {} |",
            label(key),
            cell(&report.validation),
            cell(&report.test),
            cell(&report.baseline)
        );
    }
    out
}

/// Render a model card.
pub fn render(task: Task, report: &Report) -> String {
    let p = prose(task);
    let mut out = String::new();
    let _ = write!(
        out,
        "---\nlicense: apache-2.0\nlibrary_name: opendna\ntags:\n  - protein\n  - biology\n  - \
         protein-language-model\ndatasets:\n  - {dataset}\nbase_model: {base}\n---\n\n\
         # OpenDNA {task} head\n\n{summary}\n\n\
         This is a small head trained on **frozen** [{base}](https://huggingface.co/{base}) \
         embeddings. It is not a fine-tuned language model: the embedding model is unchanged, and \
         only the head below was trained.\n\n\
         ## Inputs and outputs\n\n**Input.** {inputs}\n\n**Output.** {outputs}\n\n\
         ## Results\n\n{table}\n\
         Baseline: {baseline}\n\n\
         Validation chose the epoch that was kept (epoch {best_epoch} of {epochs_run} run). The \
         test split was evaluated once, afterwards. Splits come from the dataset builder, which \
         clusters by sequence identity so near-identical proteins cannot appear on both sides.\n\n\
         ## Training\n\n\
         | | |\n|---|---|\n\
         | Embedding model | `{base}` ({dim} dimensions, frozen) |\n\
         | Optimiser | AdamW, learning rate {lr} |\n\
         | Batch size | {batch} |\n\
         | Seed | {seed}{seed_note} |\n\
         | Dataset | [`{dataset}`]({dataset_url}) |\n\
         | Data licence | {license} |\n\n\
         Reproduce with:\n\n```bash\ncargo run --release -p opendna-train -- embed --task {task}\n\
         cargo run --release -p opendna-train -- train --task {task}\n```\n\n\
         ## Limitations\n\n",
        dataset = p.dataset,
        base = report.embedding_model,
        task = task.name(),
        summary = p.summary,
        inputs = p.inputs,
        outputs = p.outputs,
        table = metrics_table(report),
        baseline = p.baseline,
        best_epoch = report.best_epoch,
        epochs_run = report.epochs_run,
        dim = report.embedding_dim,
        lr = report.learning_rate,
        batch = report.batch_size,
        seed = report.seed,
        seed_note = if report.seed_applied {
            ""
        } else {
            " (data order only; the training device could not seed weight initialisation)"
        },
        dataset_url = p.dataset_url,
        license = p.license,
    );
    for limitation in p.limitations {
        let _ = writeln!(out, "- {limitation}");
    }
    let _ = write!(
        out,
        "\n## Intended use\n\nRanking and triage during protein engineering: comparing candidate \
         mutations or constructs against each other. It is not a substitute for measurement, and \
         it should not be used to make claims about a specific protein without experimental \
         confirmation.\n\n\
         ## Citation\n\nThe training data comes from:\n\n> {citation}\n\n\
         Please cite that work as well as this model.\n",
        citation = p.citation
    );
    out
}

/// Write a model card next to the weights.
///
/// # Errors
/// If the file cannot be written.
pub fn write(task: Task, report: &Report, out_dir: &Path) -> Result<()> {
    let path = out_dir.join(format!("{}.README.md", task.name()));
    std::fs::write(&path, render(task, report)).with_context(|| format!("writing {}", path.display()))?;
    println!("Wrote {}", path.display());
    Ok(())
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;
    use crate::train::SplitMetrics;
    use std::collections::BTreeMap;

    fn report() -> Report {
        let values = |pairs: &[(&str, f64)]| SplitMetrics {
            n: 100,
            values: pairs.iter().map(|(k, v)| ((*k).to_string(), *v)).collect::<BTreeMap<_, _>>(),
        };
        Report {
            task: "stability".into(),
            embedding_model: "facebook/esm2_t30_150M_UR50D".into(),
            embedding_dim: 640,
            best_epoch: 7,
            epochs_run: 17,
            learning_rate: 1e-3,
            batch_size: 256,
            seed: 1,
            seed_applied: true,
            validation: values(&[("spearman", 0.61)]),
            test: values(&[("spearman", 0.6)]),
            baseline: values(&[("spearman", 0.28)]),
        }
    }

    #[test]
    fn card_reports_the_measured_numbers_and_the_baseline() {
        let card = render(Task::Stability, &report());
        assert!(card.contains("| Spearman ρ | 0.610 | 0.600 | 0.280 |"), "{card}");
        assert!(card.contains("epoch 7 of 17"));
        assert!(card.contains("facebook/esm2_t30_150M_UR50D"));
        assert!(card.starts_with("---\nlicense: apache-2.0"), "needs YAML front matter");
        assert!(card.contains("## Limitations"));
    }

    #[test]
    fn an_unseeded_run_says_so() {
        let mut r = report();
        r.seed_applied = false;
        assert!(render(Task::Stability, &r).contains("could not seed"));
    }

    #[test]
    fn every_task_renders() {
        for task in [Task::Stability, Task::Solubility, Task::Disorder] {
            let mut r = report();
            r.task = task.name().to_string();
            let card = render(task, &r);
            assert!(card.contains("## Limitations"), "{} has no limitations", task.name());
            assert!(card.contains("## Citation"));
        }
    }
}
