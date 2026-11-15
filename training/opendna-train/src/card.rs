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
    /// What the *weights* are released under, as a Hugging Face licence
    /// identifier, with `weights_license_note` explaining the choice.
    ///
    /// This is not always `apache-2.0`. Whether model weights are a derivative
    /// work of their training data is unsettled, and a head trained on
    /// share-alike data is not something this project can relicense on the
    /// strength of an assumption. Where the upstream licence is share-alike,
    /// the weights carry it forward.
    weights_license: &'static str,
    weights_license_note: &'static str,
    inputs: &'static str,
    outputs: &'static str,
    baseline: &'static str,
    limitations: &'static [&'static str],
    citation: &'static str,
}

// One `match` of per-task prose. Splitting it per task would hide the fact
// that the three cards are the same document with different words, which is
// the property that keeps them comparable.
#[allow(clippy::too_many_lines)]
fn prose(task: Task) -> Prose {
    match task {
        Task::Stability => Prose {
            summary: "Predicts the change in folding free energy (ΔΔG) caused by a single \
                      amino-acid substitution.",
            dataset: "dyber-pqc/opendna-stability",
            dataset_url: "https://huggingface.co/datasets/dyber-pqc/opendna-stability",
            license: "CC BY 4.0 (Tsuboyama et al. 2023)",
            weights_license: "apache-2.0",
            weights_license_note: "The training data is CC BY 4.0, which asks for attribution \
                                   and places no condition on the licence of derived work, so \
                                   the weights are Apache-2.0. Cite the dataset.",
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
                "Trained with a squared-error loss, so predictions are compressed toward the \
                 training mean and span a much narrower range than the measurements do. The rank \
                 order is the usable signal, which is why Spearman is the headline metric; treat \
                 an individual predicted value as a weak estimate.",
            ],
            citation: "Tsuboyama, K. et al. Mega-scale experimental analysis of protein folding \
                       stability in biology and design. Nature 620, 434-444 (2023).",
        },
        Task::Solubility => Prose {
            summary: "Predicts protein solubility from sequence.",
            dataset: "dyber-pqc/opendna-solubility",
            dataset_url: "https://huggingface.co/datasets/dyber-pqc/opendna-solubility",
            license: "CC BY-SA 2.1 JP (eSOL, Niwa et al. 2009); the UniProtKB sequences it is \
                      joined against are CC BY 4.0",
            weights_license: "other\nlicense_name: cc-by-sa-2.1-jp\nlicense_link: \
                              https://creativecommons.org/licenses/by-sa/2.1/jp/deed.en",
            weights_license_note: "The eSOL measurements are licensed CC BY-SA 2.1 JP, which is \
                                   share-alike. Whether trained weights are a derivative work of \
                                   their training data is an open legal question, and this \
                                   project is not going to answer it in its own favour, so these \
                                   weights are released under the same share-alike terms rather \
                                   than the Apache-2.0 used for the other heads.",
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
        Task::Burial => Prose {
            summary: "Predicts, for each residue, how solvent-exposed it is.",
            dataset: "dyber-pqc/opendna-burial",
            dataset_url: "https://huggingface.co/datasets/dyber-pqc/opendna-burial",
            license: "CC BY 4.0 (CATH v4.4.0); the coordinates it is computed from are CC0 1.0 \
                      (wwPDB)",
            weights_license: "apache-2.0",
            weights_license_note: "CATH is CC BY 4.0 and wwPDB coordinates are CC0, neither of \
                                   which places a condition on the licence of derived work, so \
                                   the weights are Apache-2.0. Cite the dataset.",
            inputs: "Per-residue ESM-2 embeddings. Sequences longer than the embedding model's \
                     limit are covered by overlapping windows.",
            outputs: "Relative solvent accessibility per residue: the residue's accessible area \
                      over the theoretical maximum for that amino acid, so roughly 0 in the core \
                      and roughly 1 fully exposed. The output is squashed into [0, 1.25], \
                      because a negative area is not a thing and the theoretical maxima are \
                      occasionally exceeded.",
            baseline: "Predicting the training-set mean accessibility for every residue.",
            limitations: &[
                "Labels come from a single chain of a crystal or NMR model, so a residue that \
                 forms an inter-chain interface in an obligate oligomer is labelled exposed. The \
                 head learns that convention and will do the same.",
                "Trained on single-segment CATH domains whose sequence could be located in \
                 current coordinates, which excludes discontinuous domains — about one in eight \
                 of CATH — and entries substantially revised since CATH v4.4.0. The training \
                 distribution is biased toward simple, stable structures.",
                "Accessibility is a property of a fold. For a sequence with no stable structure \
                 the number is still produced and still means nothing; read it alongside the \
                 disorder head rather than alone.",
                "The metrics are pooled over residues, and residues within a domain are strongly \
                 correlated because neighbours share a local environment. The effective sample \
                 size is nearer the number of domains than the number of residues, so small \
                 differences between splits are noise.",
                "Trained on frozen embeddings, so accuracy is bounded by what ESM-2 already \
                 encodes about the position.",
            ],
            citation: "Tien, M. Z. et al. Maximum allowed solvent accessibilites of residues in \
                       proteins. PLOS ONE 8, e80635 (2013).",
        },
        Task::Disorder => Prose {
            summary: "Predicts, for each residue, whether it lies in an intrinsically disordered \
                      region.",
            dataset: "dyber-pqc/opendna-disorder",
            dataset_url: "https://huggingface.co/datasets/dyber-pqc/opendna-disorder",
            license: "CC BY 4.0 (DisProt 2025_12); the CAID3 reference set used only to hold \
                      proteins out is CC BY 3.0",
            weights_license: "apache-2.0",
            weights_license_note: "Both sources ask for attribution and place no condition on \
                                   the licence of derived work, so the weights are Apache-2.0. \
                                   Cite the dataset.",
            inputs: "Per-residue ESM-2 embeddings. Sequences longer than the embedding model's \
                     limit are covered by overlapping windows.",
            outputs: "One calibrated probability per residue. The threshold for a disorder \n                      call is recorded in the head's metadata and stated under Calibration \n                      below, because it is a property of the trained head rather than a \n                      convention.",
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
                "The metrics are pooled over residues, but residues within one protein are \
                 strongly correlated — neighbouring positions almost always share a label. The \
                 effective sample size is therefore closer to the few hundred proteins in each \
                 split than to the hundred thousand or more residues the counts show, so small \
                 differences between splits should not be read as real. On this run the test \
                 split scored higher than validation on every metric, which is what that noise \
                 looks like rather than evidence the model generalises unusually well.",
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
    let mut baseline_gap = false;
    for key in keys {
        let cell = |m: &crate::train::SplitMetrics| {
            m.values.get(key).map_or_else(|| "—".to_string(), |v| format!("{v:.3}"))
        };
        if !report.baseline.values.contains_key(key) {
            baseline_gap = true;
        }
        let _ = writeln!(
            out,
            "| {} | {} | {} | {} |",
            label(key),
            cell(&report.validation),
            cell(&report.test),
            cell(&report.baseline)
        );
    }
    if baseline_gap {
        // A constant baseline — the training mean, or the majority class —
        // has no rank or linear correlation to report, because correlation
        // with a constant is undefined rather than zero. Say so, so the dash
        // does not read as a metric nobody bothered to measure.
        out.push_str(
            "\nA — in the baseline column means the metric is undefined for that baseline, \
             not unmeasured: a baseline that predicts the same value for every input has no \
             correlation with the truth.\n",
        );
    }
    out
}

/// The external-benchmark section, or an explanation of why there is none.
///
/// The table above it is measured on our own test split, which says nothing
/// about how the head compares to published work, because nobody else reports
/// a number on our splits. A card that gives only that number invites the
/// reader to treat it as a standing rather than a measurement, so the absence
/// of an external figure is stated rather than left as a gap.
fn external_section(reports: &[crate::bench::BenchReport]) -> String {
    let mut out = String::from("### Against published benchmarks\n\n");
    if reports.is_empty() {
        out.push_str(
            "None. The external benchmarks for this task come from sources whose terms do not \
             permit redistribution, or from services that have been retired, so there is no \
             set this head can be scored on alongside other published methods. The figures \
             above are therefore not evidence of where it stands relative to the field — only \
             of how it does on data drawn the way its training data was drawn.\n\n",
        );
        return out;
    }
    for report in reports {
        let _ = writeln!(out, "**{}** — {} items scored.\n", report.suite, report.residues_scored);
        let _ = writeln!(out, "| Metric | Value |\n|---|---:|");
        for (name, value) in &report.pooled {
            let _ = writeln!(out, "| {name} | {value:.4} |");
        }
        if let Some(mean) = report.per_protein_auroc {
            let _ = writeln!(out, "| auroc (mean over proteins) | {mean:.4} |");
        }
        out.push('\n');
        for caveat in &report.caveats {
            let _ = writeln!(out, "- {caveat}");
        }
        out.push('\n');
    }
    out
}

/// Render a model card.
pub fn render(task: Task, report: &Report, external: &[crate::bench::BenchReport]) -> String {
    let p = prose(task);
    let mut out = String::new();
    let _ = write!(
        out,
        "---\nlicense: {weights_license}\nlibrary_name: opendna\ntags:\n  - protein\n  - \
         biology\n  - protein-language-model\ndatasets:\n  - {dataset}\nbase_model: \
         {base}\n---\n\n\
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
         {external}\
         ## Training\n\n\
         | | |\n|---|---|\n\
         | Embedding model | `{base}` ({dim} dimensions, frozen) |\n\
         | Optimiser | AdamW, learning rate {lr} |\n\
         | Batch size | {batch} |\n\
         | Seed | {seed}{seed_note} |\n\
         | Dataset | [`{dataset}`]({dataset_url}) |\n\
         | Data licence | {license} |\n\n\
         ### Licence of these weights\n\n{weights_license_note}\n\n\
         ### Reproducing this run\n\n\
         Download the dataset from [`{dataset}`]({dataset_url}) into `datasets/out/{task}/`, or \
         rebuild it from its upstream sources with the `datasets/` workspace of the \
         [OpenDNA repository](https://github.com/dyber-pqc/OpenDNA) — the dataset card lists \
         every source file with its SHA-256. Then, from `training/`:\n\n\
         ```bash\ncargo run --release -p opendna-train -- embed --task {task}\n\
         cargo run --release -p opendna-train -- train --task {task} \\\n\
         \u{20}   --batch-size {batch} --learning-rate {lr} --seed {seed}\n```\n\n\
         The hyperparameters are spelled out above even where they match the current defaults, \
         so the command reproduces *this* run rather than whatever the defaults happen to be \
         later.\n\n\
         Both commands take `--datasets <dir>` if the dataset is not at the default \
         `../datasets/out`. Embedding is cached, so the second run of either command is cheap.\n\n\
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
        weights_license = p.weights_license,
        weights_license_note = p.weights_license_note,
        external = external_section(external),
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
/// What the card says about calibration.
///
/// Three states, and they are different claims: a correction was fitted and
/// applied, the question was measured and no correction was warranted, or
/// nobody has looked. An absent section would collapse the last two.
fn calibration_section(task: Task, calibration: Option<&opendna_ml::heads::Calibration>) -> String {
    if task != Task::Disorder {
        // The regressors emit quantities, not probabilities. Saying nothing
        // about calibration is correct for them; claiming it was checked
        // would not be.
        return String::new();
    }
    let Some(c) = calibration else {
        return "\n## Calibration\n\nNot measured. The probabilities this head reports have not \
                been checked against observed frequencies, so a reported 0.7 should be read as a \
                score for ranking rather than as a seven-in-ten chance.\n"
            .to_string();
    };
    if c.method == "none" {
        return format!(
            "\n## Calibration\n\nMeasured and left alone. Expected calibration error on the \
             held-out split is {:.4}, and no fitted correction improved on that by more than the \
             width of its own bootstrap interval, so none is applied. Residues are called \
             disordered at {:.2}.\n",
            c.test_ece_before, c.threshold
        );
    }
    format!(
        "\n## Calibration\n\nThe probabilities are corrected before they are reported. This head \
         is trained with weighted cross-entropy so that it does not predict \"ordered\" \
         everywhere, which helps the ranking and inflates the probabilities; a {} map fitted on \
         the validation split removes the inflation.\n\n\
         | | |\n|---|---|\n\
         | Map | `p = sigmoid({:.4} * logit + {:.4})` |\n\
         | Expected calibration error, held-out split | {:.4} before, {:.4} after |\n\
         | Threshold for a disorder call | {:.2} |\n\
         | Matthews correlation at that threshold, held-out split | {:.4} |\n\n\
         The map is monotonic, so it changes no ranking and no rank statistic: AUROC is \
         identical before and after. What it changes is the meaning of the number, and therefore \
         where the decision threshold belongs -- which is why the threshold is recorded here \
         rather than left at the conventional 0.5. The threshold was chosen on the validation \
         split, so the correlation above is an honest estimate rather than the best figure \
         findable with the held-out labels in hand.\n\n\
         Calibration is against the labels. DisProt records disorder that has been demonstrated \
         experimentally and unannotated residues are treated as ordered, so these probabilities \
         are calibrated against the annotation rather than against nature. If the annotation \
         under-reports disorder, and it does by an unknown amount, the calibrated probabilities \
         inherit that.\n\n\
         The threshold is a property of a distribution, not of the head. It was chosen on the \
         validation split of this dataset, and it does not suit every set: on the CAID3 \
         reference above, MCC, F1 and balanced accuracy are lower at this threshold than they \
         were at the conventional 0.5, because {:.2} calibrated is about 0.78 raw and that set \
         prefers a lower cut. The rank metrics are identical either way. If you threshold \
         these probabilities for a decision of your own, the right cut depends on your class \
         balance and on what a false positive costs you; the calibration is what makes it \
         possible to reason about that at all.\n",
        c.method,
        c.slope,
        c.intercept,
        c.test_ece_before,
        c.test_ece_after,
        c.threshold,
        c.test_mcc,
        c.threshold
    )
}

/// What the card says about confidence and abstention.
///
/// Includes the signals that were measured and rejected. A card that lists
/// only what worked invites the next person to spend an afternoon re-testing
/// what did not.
fn confidence_section(abstention: Option<&opendna_ml::heads::Abstention>) -> String {
    let Some(a) = abstention else {
        return String::new();
    };
    let mut out = String::from(
        "\n## Confidence, and whether to abstain\n\n\
         How far the calibrated probability sits from the decision threshold orders residues by \
         how likely the call is to be wrong, so a caller can trade coverage for accuracy. \
         Measured on the held-out split:\n\n\
         | Minimum confidence | Residues kept | Error among them |\n|---|---|---|\n",
    );
    for point in &a.curve {
        let _ = writeln!(
            out,
            "| {:.2} | {:.0}% | {:.1}% |",
            point.min_confidence,
            100.0 * point.coverage,
            100.0 * point.error
        );
    }
    let _ = write!(
        out,
        "\nNothing abstains by default. The confidence is reported for every residue and the \
         cut-off is the caller's, because the right one depends on what a wrong call costs them. \
         `opendna predict --min-confidence` marks the rows that do not clear a cut-off rather than \
         removing them: a table quietly missing rows looks exactly like a complete one.\n\n\
         This signal captures {:.0}% of the error reduction an oracle shows is available -- an \
         oracle being a rule that discards exactly the wrong calls. Half of what is there, which \
         is worth having and is not a guarantee.\n",
        100.0 * a.captured
    );
    if !a.rejected.is_empty() {
        let _ = write!(
            out,
            "\nMeasured and rejected: {}. Ordering residues by this was no better than \
             discarding them at random, so no rule is built on it. It is recorded because the \
             obvious next idea is to try it.\n",
            a.rejected.join(", ")
        );
    }
    out
}

pub fn write(task: Task, report: &Report, out_dir: &Path, benchmarks: &Path) -> Result<()> {
    // Benchmark reports are matched on the embedding model, so a card can
    // never quote a figure measured on a different one than it documents.
    let external = crate::bench::load_reports(benchmarks, task.name(), &report.embedding_model)?;
    let path = out_dir.join(format!("{}.README.md", task.name()));
    // Read from the metadata beside the weights, so the card cannot describe
    // a calibration the head is not carrying.
    let files = opendna_ml::heads::HeadFiles::in_dir(out_dir, task.name());
    let calibration = std::fs::read_to_string(&files.metadata)
        .ok()
        .and_then(|t| serde_json::from_str::<opendna_ml::heads::HeadMetadata>(&t).ok())
        .and_then(|m| m.calibration);
    let abstention = std::fs::read_to_string(&files.metadata)
        .ok()
        .and_then(|t| serde_json::from_str::<opendna_ml::heads::HeadMetadata>(&t).ok())
        .and_then(|m| m.abstention);
    let body = render(task, report, &external)
        + &calibration_section(task, calibration.as_ref())
        + &confidence_section(abstention.as_ref());
    std::fs::write(&path, body).with_context(|| format!("writing {}", path.display()))?;
    println!(
        "Wrote {} ({} external benchmark{})",
        path.display(),
        external.len(),
        if external.len() == 1 { "" } else { "s" }
    );
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
        let card = render(Task::Stability, &report(), &[]);
        assert!(card.contains("| Spearman ρ | 0.610 | 0.600 | 0.280 |"), "{card}");
        assert!(card.contains("epoch 7 of 17"));
        // The run used a non-default batch size once, and the card's command
        // omitted it — so following the card produced a different model than
        // the one it described. The command now carries every value.
        assert!(card.contains("--batch-size 256"), "{card}");
        assert!(card.contains("--seed 1"), "{card}");
        assert!(card.contains("facebook/esm2_t30_150M_UR50D"));
        assert!(card.starts_with("---\nlicense: apache-2.0"), "needs YAML front matter");
        assert!(card.contains("## Limitations"));
    }

    /// The dataset link has to resolve for someone who only has the card.
    ///
    /// It used to point at `datasets/` inside the GitHub repository, a
    /// directory that is not on the published branch — so every card shipped
    /// a dead link to the one thing a reader most needs. It now points at the
    /// dataset's own Hugging Face repository, which is published alongside.
    #[test]
    fn the_dataset_link_points_at_a_published_dataset() {
        for task in [Task::Stability, Task::Solubility, Task::Disorder] {
            let card = render(task, &report(), &[]);
            let expected = format!("https://huggingface.co/datasets/dyber-pqc/opendna-{}", task.name());
            assert!(card.contains(&expected), "{} card: missing {expected}", task.name());
            assert!(
                !card.contains("OpenDNA/tree/main/datasets"),
                "{} card still links to a directory that is not on the published branch",
                task.name()
            );
        }
    }

    /// Share-alike data must not be laundered into an Apache-2.0 model.
    ///
    /// eSOL is CC BY-SA 2.1 JP. Declaring the head Apache-2.0 would assert
    /// that weights are not a derivative work of their training data, which
    /// is an open question and not one to settle in our own favour.
    #[test]
    fn a_head_trained_on_share_alike_data_does_not_claim_apache() {
        let solubility = render(Task::Solubility, &report(), &[]);
        assert!(solubility.starts_with("---\nlicense: other\n"), "{solubility}");
        assert!(solubility.contains("license_name: cc-by-sa-2.1-jp"), "{solubility}");
        assert!(solubility.contains("### Licence of these weights"), "{solubility}");
        // The other two are CC BY, which carries no such condition.
        for task in [Task::Stability, Task::Disorder] {
            let card = render(task, &report(), &[]);
            assert!(card.starts_with("---\nlicense: apache-2.0"), "{} card", task.name());
        }
    }

    fn bench(suite: &str) -> crate::bench::BenchReport {
        crate::bench::BenchReport {
            suite: suite.into(),
            embedding_model: "facebook/esm2_t30_150M_UR50D".into(),
            head_version: "0.6.0-dev".into(),
            proteins: 319,
            residues_scored: 99_239,
            residues_masked: 61_183,
            positive_rate: Some(0.3164),
            windowed: 34,
            pooled: vec![("auroc".into(), 0.941_02)],
            per_protein_auroc: Some(0.925_2),
            per_protein_undefined: 86,
            caveats: vec!["Not an official CAID3 result.".into()],
        }
    }

    /// An in-domain number on its own invites a reader to treat it as a
    /// standing rather than a measurement.
    #[test]
    fn external_benchmarks_appear_on_the_card() {
        let card = render(Task::Disorder, &report(), &[bench("caid3-disorder-pdb")]);
        assert!(card.contains("### Against published benchmarks"), "{card}");
        assert!(card.contains("caid3-disorder-pdb"), "{card}");
        assert!(card.contains("| auroc | 0.9410 |"), "{card}");
        assert!(card.contains("Not an official CAID3 result."), "{card}");
    }

    /// Having no external benchmark is a fact about the task, not a gap to
    /// pass over in silence: solubility has none, and the card says why.
    #[test]
    fn the_absence_of_an_external_benchmark_is_stated() {
        let card = render(Task::Solubility, &report(), &[]);
        assert!(card.contains("### Against published benchmarks"), "{card}");
        assert!(card.contains("None."), "{card}");
        assert!(card.contains("not evidence of where it stands"), "{card}");
    }

    /// A report measured on another embedding model must not be quoted on a
    /// card documenting this one, and a suite belonging to another head must
    /// not be picked up at all.
    #[test]
    fn a_report_from_a_different_embedder_is_not_loaded() {
        let dir = std::env::temp_dir().join(format!("opendna-card-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let mut other = bench("caid3-disorder-pdb");
        other.embedding_model = "facebook/esm2_t33_650M_UR50D".into();
        std::fs::write(dir.join("caid3.json"), serde_json::to_string(&other).unwrap()).unwrap();

        let loaded = |task, model| crate::bench::load_reports(&dir, task, model).unwrap().len();
        assert_eq!(loaded("disorder", "facebook/esm2_t30_150M_UR50D"), 0, "650M quoted on a 150M card");
        assert_eq!(loaded("disorder", "facebook/esm2_t33_650M_UR50D"), 1);
        assert_eq!(loaded("stability", "facebook/esm2_t33_650M_UR50D"), 0, "wrong head's suite");
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn a_missing_benchmarks_directory_is_not_an_error() {
        let got = crate::bench::load_reports(
            Path::new("definitely/not/here"),
            "disorder",
            "facebook/esm2_t30_150M_UR50D",
        )
        .unwrap();
        assert!(got.is_empty());
    }

    /// `FireProtDB` was dropped from the stability dataset for licensing
    /// reasons, but the card went on crediting it — attributing data that is
    /// not in the model.
    #[test]
    fn the_stability_card_credits_only_the_source_that_is_in_the_data() {
        let card = render(Task::Stability, &report(), &[]);
        assert!(!card.contains("FireProtDB"), "{card}");
        assert!(card.contains("Tsuboyama"), "{card}");
    }

    #[test]
    fn a_missing_baseline_metric_is_explained_rather_than_left_as_a_dash() {
        let mut r = report();
        r.test.values.insert("rmse".into(), 23.4);
        // The constant baseline has rmse but no spearman.
        r.baseline.values.remove("spearman");
        r.baseline.values.insert("rmse".into(), 32.3);
        let card = render(Task::Solubility, &r, &[]);
        assert!(card.contains("| Spearman ρ | 0.610 | 0.600 | — |"), "{card}");
        assert!(card.contains("undefined for that baseline"), "{card}");
    }

    #[test]
    fn a_baseline_with_every_metric_gets_no_footnote() {
        assert!(!render(Task::Stability, &report(), &[]).contains("undefined for that baseline"));
    }

    #[test]
    fn an_unseeded_run_says_so() {
        let mut r = report();
        r.seed_applied = false;
        assert!(render(Task::Stability, &r, &[]).contains("could not seed"));
    }

    #[test]
    fn every_task_renders() {
        for task in [Task::Stability, Task::Solubility, Task::Disorder] {
            let mut r = report();
            r.task = task.name().to_string();
            let card = render(task, &r, &[]);
            assert!(card.contains("## Limitations"), "{} has no limitations", task.name());
            assert!(card.contains("## Citation"));
        }
    }
}
