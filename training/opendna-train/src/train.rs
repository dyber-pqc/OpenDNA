//! Training loops for the three prediction heads.
//!
//! Every head is trained on frozen ESM-2 embeddings read from the cache, so
//! a run takes minutes rather than hours and is reproducible from a seed.
//! The validation split chooses when to stop; the test split is read once,
//! at the end, for the numbers that go in the model card.

// Each training function is a complete, linear recipe: load, train,
// evaluate, save. Splitting them would scatter a procedure that reads better
// in one piece.
#![allow(clippy::too_many_lines)]

use crate::cache::MatrixCache;
use crate::data::{self, Split};
use crate::metrics;
use crate::Task;
use anyhow::{bail, Context, Result};
use candle_core::{DType, Tensor};
use candle_nn::{AdamW, Optimizer, ParamsAdamW, VarBuilder, VarMap};
use opendna_core::AminoAcid;
use opendna_ml::esm2::ModelSize;
use opendna_ml::heads::{DisorderHead, HeadMetadata, SolubilityHead, StabilityHead};
use rand::prelude::*;
use rand::rngs::StdRng;
use serde::Serialize;
use std::collections::HashMap;
use std::path::Path;

/// Knobs shared by the three training runs.
#[derive(Debug, Clone)]
pub struct TrainConfig {
    /// Maximum passes over the training split.
    pub epochs: usize,
    /// Rows per optimisation step.
    pub batch_size: usize,
    /// `AdamW` learning rate.
    pub learning_rate: f64,
    /// Stop after this many epochs without a better validation score.
    pub patience: usize,
    /// Seed for shuffling and weight initialisation.
    pub seed: u64,
}

impl Default for TrainConfig {
    fn default() -> Self {
        Self { epochs: 100, batch_size: 256, learning_rate: 1e-3, patience: 10, seed: 20_260_101 }
    }
}

/// Metrics for one split.
#[derive(Debug, Clone, Serialize)]
pub struct SplitMetrics {
    /// Rows evaluated.
    pub n: usize,
    /// Metric name to value. Absent metrics are omitted rather than reported
    /// as zero.
    #[serde(flatten)]
    pub values: std::collections::BTreeMap<String, f64>,
}

/// Everything a training run produces, written next to the weights.
#[derive(Debug, Clone, Serialize)]
pub struct Report {
    /// Task name.
    pub task: String,
    /// Embedding model used.
    pub embedding_model: String,
    /// Embedding width.
    pub embedding_dim: usize,
    /// Epoch whose weights were kept.
    pub best_epoch: usize,
    /// Training configuration, flattened for readability.
    pub epochs_run: usize,
    /// Learning rate used.
    pub learning_rate: f64,
    /// Batch size used.
    pub batch_size: usize,
    /// Seed used.
    pub seed: u64,
    /// Whether the compute device accepted the seed. When false, only the
    /// data order was reproducible, not the initial weights.
    pub seed_applied: bool,
    /// Validation metrics at the kept epoch.
    pub validation: SplitMetrics,
    /// Test metrics at the kept epoch.
    pub test: SplitMetrics,
    /// Metrics for the trivial baseline a useful model must beat.
    pub baseline: SplitMetrics,
}

fn metric_map(pairs: &[(&str, Option<f64>)]) -> std::collections::BTreeMap<String, f64> {
    pairs.iter().filter_map(|(k, v)| v.map(|v| ((*k).to_string(), (v * 1e6).round() / 1e6))).collect()
}

/// Seed the device's generator if it supports one.
///
/// candle's CPU backend has no seedable generator, so weight initialisation
/// there is not reproducible. Shuffling always is: it uses this crate's own
/// generator. The return value records which case applied, and goes into the
/// report rather than being quietly ignored.
fn apply_seed(device: &candle_core::Device, seed: u64) -> bool {
    if device.set_seed(seed).is_ok() {
        return true;
    }
    eprintln!(
        "note: {} cannot be seeded, so weight initialisation is not reproducible; data order still is",
        opendna_ml::device_description(device)
    );
    false
}

fn amino_index(residue: char) -> Option<usize> {
    let aa = AminoAcid::from_one_letter(residue)?;
    AminoAcid::STANDARD.iter().position(|s| *s == aa)
}

/// Index of a residue in the ESM-2 alphabet, for reading log-probability rows.
fn token_index(residue: char) -> usize {
    opendna_ml::esm2::alphabet::token_id(residue) as usize
}

/// Save weights, metadata and metrics.
fn save(
    varmap: &VarMap,
    out_dir: &Path,
    task: Task,
    model_size: ModelSize,
    embedding_dim: usize,
    report: &Report,
) -> Result<()> {
    std::fs::create_dir_all(out_dir)?;
    let weights = out_dir.join(format!("{}.safetensors", task.name()));
    varmap.save(&weights).with_context(|| format!("writing {}", weights.display()))?;

    let metadata = HeadMetadata {
        task: task.name().to_string(),
        embedding_model: model_size.repo().to_string(),
        embedding_dim,
        version: env!("CARGO_PKG_VERSION").to_string(),
    };
    std::fs::write(
        out_dir.join(format!("{}.metadata.json", task.name())),
        serde_json::to_string_pretty(&metadata)?,
    )?;
    std::fs::write(
        out_dir.join(format!("{}.metrics.json", task.name())),
        serde_json::to_string_pretty(report)?,
    )?;
    println!("Wrote {}", weights.display());
    Ok(())
}

/// Mean of a slice, or 0 when empty.
fn mean(values: &[f64]) -> f64 {
    if values.is_empty() {
        0.0
    } else {
        values.iter().sum::<f64>() / values.len() as f64
    }
}

// ---------------------------------------------------------------------------
// Stability
// ---------------------------------------------------------------------------

struct StabilityData {
    features: Vec<f32>,
    targets: Vec<f32>,
    width: usize,
}

impl StabilityData {
    fn len(&self) -> usize {
        self.targets.len()
    }
}

/// Build the feature matrix for one split from the cached embeddings.
fn stability_features(
    rows: &[data::StabilityRow],
    embeddings: &HashMap<String, (Vec<f32>, usize)>,
    log_probs: &HashMap<String, (Vec<f32>, usize)>,
    hidden: usize,
    vocab: usize,
) -> Result<StabilityData> {
    let width = StabilityHead::input_width(hidden);
    let mut features = Vec::with_capacity(rows.len() * width);
    let mut targets = Vec::with_capacity(rows.len());

    for row in rows {
        let (embedding, _) = embeddings
            .get(&row.wt_sequence)
            .with_context(|| "a wild-type sequence is missing from the embedding cache")?;
        let (log_prob, _) = log_probs
            .get(&row.wt_sequence)
            .with_context(|| "a wild-type sequence is missing from the log-probability cache")?;

        let start = row.position * hidden;
        let site = embedding
            .get(start..start + hidden)
            .with_context(|| format!("position {} is past the cached embedding", row.position))?;

        let base = row.position * vocab;
        let wt_logp = log_prob[base + token_index(row.wild_type)];
        let mut_logp = log_prob[base + token_index(row.mutant)];

        let (Some(wt), Some(mt)) = (amino_index(row.wild_type), amino_index(row.mutant)) else {
            bail!("mutation {}{}{} uses a non-standard residue", row.wild_type, row.position + 1, row.mutant);
        };
        features.extend(StabilityHead::features(site, wt, mt, mut_logp - wt_logp));
        targets.push(row.ddg as f32);
    }
    Ok(StabilityData { features, targets, width })
}

/// Train the ΔΔG head.
///
/// # Errors
/// If the datasets or caches cannot be read, or training fails.
pub fn stability(
    datasets_root: &Path,
    cache_dir: &Path,
    out_dir: &Path,
    model_size: ModelSize,
    config: &TrainConfig,
) -> Result<Report> {
    let device = opendna_ml::best_device()?;
    let seed_applied = apply_seed(&device, config.seed);
    let hidden = model_size.hidden_size();
    let vocab = opendna_ml::esm2::alphabet::TOKENS.len();

    let embeddings_cache = MatrixCache::open(
        cache_dir,
        &crate::embed::embedding_cache_name(Task::Stability, model_size),
        model_size.repo(),
        hidden,
    )?;
    let log_probs_cache = MatrixCache::open(
        cache_dir,
        &crate::embed::log_prob_cache_name(model_size),
        model_size.repo(),
        vocab,
    )?;

    let splits: Vec<Vec<data::StabilityRow>> =
        Split::all().iter().map(|s| data::stability(datasets_root, *s)).collect::<Result<_>>()?;

    // Only a few hundred unique wild-type sequences back hundreds of
    // thousands of mutations, so everything fits comfortably in memory.
    let mut embeddings = HashMap::new();
    let mut log_probs = HashMap::new();
    for split in &splits {
        for row in split {
            if !embeddings.contains_key(&row.wt_sequence) {
                embeddings.insert(row.wt_sequence.clone(), embeddings_cache.get(&row.wt_sequence)?);
                log_probs.insert(row.wt_sequence.clone(), log_probs_cache.get(&row.wt_sequence)?);
            }
        }
    }
    println!("{} unique wild-type sequences in memory", embeddings.len());

    let data: Vec<StabilityData> = splits
        .iter()
        .map(|rows| stability_features(rows, &embeddings, &log_probs, hidden, vocab))
        .collect::<Result<_>>()?;
    let (train, validation, test) = (&data[0], &data[1], &data[2]);
    println!("{} train / {} validation / {} test mutations", train.len(), validation.len(), test.len());

    let mut varmap = VarMap::new();
    let vb = VarBuilder::from_varmap(&varmap, DType::F32, &device);
    let head = StabilityHead::new(hidden, vb)?;
    let mut optimizer =
        AdamW::new(varmap.all_vars(), ParamsAdamW { lr: config.learning_rate, ..Default::default() })?;

    let predict = |head: &StabilityHead, d: &StabilityData| -> Result<Vec<f64>> {
        let mut out = Vec::with_capacity(d.len());
        for chunk_start in (0..d.len()).step_by(4096) {
            let n = (d.len() - chunk_start).min(4096);
            let slice = &d.features[chunk_start * d.width..(chunk_start + n) * d.width];
            let x = Tensor::from_slice(slice, (n, d.width), &device)?;
            out.extend(head.forward(&x)?.to_vec1::<f32>()?.into_iter().map(f64::from));
        }
        Ok(out)
    };

    let mut rng = StdRng::seed_from_u64(config.seed);
    let mut order: Vec<usize> = (0..train.len()).collect();
    let mut best = f64::NEG_INFINITY;
    let mut best_epoch = 0;
    let mut epochs_run = 0;
    let mut best_weights: Option<Vec<u8>> = None;

    for epoch in 1..=config.epochs {
        epochs_run = epoch;
        order.shuffle(&mut rng);
        let mut losses = Vec::new();
        for batch in order.chunks(config.batch_size) {
            let mut xs = Vec::with_capacity(batch.len() * train.width);
            let mut ys = Vec::with_capacity(batch.len());
            for &i in batch {
                xs.extend_from_slice(&train.features[i * train.width..(i + 1) * train.width]);
                ys.push(train.targets[i]);
            }
            let x = Tensor::from_vec(xs, (batch.len(), train.width), &device)?;
            let y = Tensor::from_vec(ys, batch.len(), &device)?;
            let loss = candle_nn::loss::mse(&head.forward(&x)?, &y)?;
            optimizer.backward_step(&loss)?;
            losses.push(f64::from(loss.to_scalar::<f32>()?));
        }

        let predicted = predict(&head, validation)?;
        let actual: Vec<f64> = validation.targets.iter().map(|v| f64::from(*v)).collect();
        let score = metrics::spearman(&predicted, &actual).unwrap_or(f64::NEG_INFINITY);
        println!(
            "epoch {epoch:3}  loss {:.4}  validation spearman {score:.4}{}",
            mean(&losses),
            if score > best { "  *" } else { "" }
        );
        if score > best {
            best = score;
            best_epoch = epoch;
            // Keep the best weights in memory; the file is written once, at the end.
            let tmp =
                std::env::temp_dir().join(format!("opendna-stability-{}.safetensors", std::process::id()));
            varmap.save(&tmp)?;
            best_weights = Some(std::fs::read(&tmp)?);
            let _ = std::fs::remove_file(&tmp);
        } else if epoch - best_epoch >= config.patience {
            println!("No improvement for {} epochs; stopping.", config.patience);
            break;
        }
    }

    if let Some(bytes) = best_weights {
        let tmp =
            std::env::temp_dir().join(format!("opendna-stability-best-{}.safetensors", std::process::id()));
        std::fs::write(&tmp, bytes)?;
        varmap.load(&tmp)?;
        let _ = std::fs::remove_file(&tmp);
    }

    let evaluate = |d: &StabilityData| -> Result<SplitMetrics> {
        let predicted = predict(&head, d)?;
        let actual: Vec<f64> = d.targets.iter().map(|v| f64::from(*v)).collect();
        Ok(SplitMetrics {
            n: d.len(),
            values: metric_map(&[
                ("spearman", metrics::spearman(&predicted, &actual)),
                ("pearson", metrics::pearson(&predicted, &actual)),
                ("rmse", Some(metrics::rmse(&predicted, &actual))),
                ("mae", Some(metrics::mae(&predicted, &actual))),
            ]),
        })
    };

    // The language model's log-odds alone, with no trained head: a useful
    // head has to beat this.
    let last = test.width - 1;
    let zero_shot: Vec<f64> =
        (0..test.len()).map(|i| f64::from(test.features[i * test.width + last])).collect();
    let test_actual: Vec<f64> = test.targets.iter().map(|v| f64::from(*v)).collect();
    let baseline = SplitMetrics {
        n: test.len(),
        values: metric_map(&[
            ("spearman", metrics::spearman(&zero_shot, &test_actual)),
            ("pearson", metrics::pearson(&zero_shot, &test_actual)),
        ]),
    };

    let report = Report {
        task: Task::Stability.name().to_string(),
        embedding_model: model_size.repo().to_string(),
        embedding_dim: hidden,
        best_epoch,
        epochs_run,
        learning_rate: config.learning_rate,
        batch_size: config.batch_size,
        seed: config.seed,
        seed_applied,
        validation: evaluate(validation)?,
        test: evaluate(test)?,
        baseline,
    };
    save(&varmap, out_dir, Task::Stability, model_size, hidden, &report)?;
    Ok(report)
}

// ---------------------------------------------------------------------------
// Solubility
// ---------------------------------------------------------------------------

/// Train the solubility head.
///
/// # Errors
/// If the datasets or caches cannot be read, or training fails.
pub fn solubility(
    datasets_root: &Path,
    cache_dir: &Path,
    out_dir: &Path,
    model_size: ModelSize,
    config: &TrainConfig,
) -> Result<Report> {
    let device = opendna_ml::best_device()?;
    let seed_applied = apply_seed(&device, config.seed);
    let hidden = model_size.hidden_size();
    let cache = MatrixCache::open(
        cache_dir,
        &crate::embed::embedding_cache_name(Task::Solubility, model_size),
        model_size.repo(),
        hidden,
    )?;

    let mut features = Vec::new();
    let mut targets = Vec::new();
    for split in Split::all() {
        let rows = data::solubility(datasets_root, split)?;
        let mut x = Vec::with_capacity(rows.len() * hidden);
        let mut y = Vec::with_capacity(rows.len());
        for row in &rows {
            let (values, _) = cache.get(&row.sequence)?;
            x.extend(values);
            y.push(row.solubility as f32);
        }
        features.push(x);
        targets.push(y);
    }
    println!(
        "{} train / {} validation / {} test proteins",
        targets[0].len(),
        targets[1].len(),
        targets[2].len()
    );

    let mut varmap = VarMap::new();
    let vb = VarBuilder::from_varmap(&varmap, DType::F32, &device);
    let head = SolubilityHead::new(hidden, vb)?;
    let mut optimizer =
        AdamW::new(varmap.all_vars(), ParamsAdamW { lr: config.learning_rate, ..Default::default() })?;

    let predict = |head: &SolubilityHead, x: &[f32], n: usize| -> Result<Vec<f64>> {
        let t = Tensor::from_slice(x, (n, hidden), &device)?;
        Ok(head.forward(&t)?.to_vec1::<f32>()?.into_iter().map(f64::from).collect())
    };

    let mut rng = StdRng::seed_from_u64(config.seed);
    let mut order: Vec<usize> = (0..targets[0].len()).collect();
    let mut best = f64::NEG_INFINITY;
    let mut best_epoch = 0;
    let mut epochs_run = 0;
    let mut best_weights: Option<Vec<u8>> = None;

    for epoch in 1..=config.epochs {
        epochs_run = epoch;
        order.shuffle(&mut rng);
        let mut losses = Vec::new();
        for batch in order.chunks(config.batch_size) {
            let mut xs = Vec::with_capacity(batch.len() * hidden);
            let mut ys = Vec::with_capacity(batch.len());
            for &i in batch {
                xs.extend_from_slice(&features[0][i * hidden..(i + 1) * hidden]);
                ys.push(targets[0][i]);
            }
            let x = Tensor::from_vec(xs, (batch.len(), hidden), &device)?;
            let y = Tensor::from_vec(ys, batch.len(), &device)?;
            let loss = candle_nn::loss::mse(&head.forward(&x)?, &y)?;
            optimizer.backward_step(&loss)?;
            losses.push(f64::from(loss.to_scalar::<f32>()?));
        }

        let predicted = predict(&head, &features[1], targets[1].len())?;
        let actual: Vec<f64> = targets[1].iter().map(|v| f64::from(*v)).collect();
        let score = metrics::spearman(&predicted, &actual).unwrap_or(f64::NEG_INFINITY);
        println!(
            "epoch {epoch:3}  loss {:.2}  validation spearman {score:.4}{}",
            mean(&losses),
            if score > best { "  *" } else { "" }
        );
        if score > best {
            best = score;
            best_epoch = epoch;
            let tmp = std::env::temp_dir().join(format!("opendna-sol-{}.safetensors", std::process::id()));
            varmap.save(&tmp)?;
            best_weights = Some(std::fs::read(&tmp)?);
            let _ = std::fs::remove_file(&tmp);
        } else if epoch - best_epoch >= config.patience {
            println!("No improvement for {} epochs; stopping.", config.patience);
            break;
        }
    }

    if let Some(bytes) = best_weights {
        let tmp = std::env::temp_dir().join(format!("opendna-sol-best-{}.safetensors", std::process::id()));
        std::fs::write(&tmp, bytes)?;
        varmap.load(&tmp)?;
        let _ = std::fs::remove_file(&tmp);
    }

    let evaluate = |index: usize| -> Result<SplitMetrics> {
        let predicted = predict(&head, &features[index], targets[index].len())?;
        let actual: Vec<f64> = targets[index].iter().map(|v| f64::from(*v)).collect();
        Ok(SplitMetrics {
            n: actual.len(),
            values: metric_map(&[
                ("spearman", metrics::spearman(&predicted, &actual)),
                ("pearson", metrics::pearson(&predicted, &actual)),
                ("rmse", Some(metrics::rmse(&predicted, &actual))),
                ("mae", Some(metrics::mae(&predicted, &actual))),
            ]),
        })
    };

    // Predicting the training mean for every protein.
    let train_mean = f64::from(targets[0].iter().sum::<f32>()) / targets[0].len() as f64;
    let test_actual: Vec<f64> = targets[2].iter().map(|v| f64::from(*v)).collect();
    let constant = vec![train_mean; test_actual.len()];
    let baseline = SplitMetrics {
        n: test_actual.len(),
        values: metric_map(&[
            ("rmse", Some(metrics::rmse(&constant, &test_actual))),
            ("mae", Some(metrics::mae(&constant, &test_actual))),
        ]),
    };

    let report = Report {
        task: Task::Solubility.name().to_string(),
        embedding_model: model_size.repo().to_string(),
        embedding_dim: hidden,
        best_epoch,
        epochs_run,
        learning_rate: config.learning_rate,
        batch_size: config.batch_size,
        seed: config.seed,
        seed_applied,
        validation: evaluate(1)?,
        test: evaluate(2)?,
        baseline,
    };
    save(&varmap, out_dir, Task::Solubility, model_size, hidden, &report)?;
    Ok(report)
}

// ---------------------------------------------------------------------------
// Disorder
// ---------------------------------------------------------------------------

/// Train the per-residue disorder head.
///
/// Proteins are streamed from the cache one at a time: the full set of
/// per-residue embeddings is several gigabytes and does not need to be
/// resident.
///
/// # Errors
/// If the datasets or caches cannot be read, or training fails.
pub fn disorder(
    datasets_root: &Path,
    cache_dir: &Path,
    out_dir: &Path,
    model_size: ModelSize,
    config: &TrainConfig,
) -> Result<Report> {
    let device = opendna_ml::best_device()?;
    let seed_applied = apply_seed(&device, config.seed);
    let hidden = model_size.hidden_size();
    let cache = MatrixCache::open(
        cache_dir,
        &crate::embed::embedding_cache_name(Task::Disorder, model_size),
        model_size.repo(),
        hidden,
    )?;

    let splits: Vec<Vec<data::DisorderRow>> =
        Split::all().iter().map(|s| data::disorder(datasets_root, *s)).collect::<Result<_>>()?;
    println!(
        "{} train / {} validation / {} test proteins",
        splits[0].len(),
        splits[1].len(),
        splits[2].len()
    );

    // Disordered residues are the minority; weight them up so the head does
    // not simply predict "ordered" everywhere.
    let positives: usize = splits[0].iter().map(|r| r.disorder.iter().filter(|d| **d).count()).sum();
    let total: usize = splits[0].iter().map(|r| r.disorder.len()).sum();
    let positive_weight = (total - positives) as f64 / positives.max(1) as f64;
    println!("positive rate {:.3}, positive weight {positive_weight:.2}", positives as f64 / total as f64);

    let mut varmap = VarMap::new();
    let vb = VarBuilder::from_varmap(&varmap, DType::F32, &device);
    let head = DisorderHead::new(hidden, vb)?;
    let mut optimizer =
        AdamW::new(varmap.all_vars(), ParamsAdamW { lr: config.learning_rate, ..Default::default() })?;

    let weight = positive_weight as f32;
    let forward = |head: &DisorderHead, row: &data::DisorderRow| -> Result<Tensor> {
        let (values, rows) = cache.get(&row.sequence)?;
        if rows != row.disorder.len() {
            bail!("cached embedding has {rows} residues but the label array has {}", row.disorder.len());
        }
        let x = Tensor::from_vec(values, (rows, hidden), &device)?;
        Ok(head.forward(&x)?)
    };

    let evaluate = |head: &DisorderHead, rows: &[data::DisorderRow]| -> Result<(Vec<f64>, Vec<bool>)> {
        let mut scores = Vec::new();
        let mut labels = Vec::new();
        for row in rows {
            let logits = forward(head, row)?.to_vec1::<f32>()?;
            scores.extend(logits.into_iter().map(|v| f64::from(1.0 / (1.0 + (-v).exp()))));
            labels.extend(row.disorder.iter().copied());
        }
        Ok((scores, labels))
    };

    let mut rng = StdRng::seed_from_u64(config.seed);
    let mut order: Vec<usize> = (0..splits[0].len()).collect();
    let mut best = f64::NEG_INFINITY;
    let mut best_epoch = 0;
    let mut epochs_run = 0;
    let mut best_weights: Option<Vec<u8>> = None;

    for epoch in 1..=config.epochs {
        epochs_run = epoch;
        order.shuffle(&mut rng);
        let mut losses = Vec::new();
        for &i in &order {
            let row = &splits[0][i];
            let logits = forward(&head, row)?;
            let targets: Vec<f32> = row.disorder.iter().map(|d| f32::from(u8::from(*d))).collect();
            let y = Tensor::from_vec(targets, row.disorder.len(), &device)?;
            // Weighted binary cross-entropy, written out because candle's
            // helper has no class-weight parameter.
            let max = logits.relu()?;
            let stable = logits.abs()?.neg()?.exp()?.affine(1.0, 1.0)?.log()?;
            let base = (max + stable)?;
            let weights = (y.affine(f64::from(weight) - 1.0, 1.0))?;
            let loss = (((base - (&logits * &y)?)? * weights)?).mean_all()?;
            optimizer.backward_step(&loss)?;
            losses.push(f64::from(loss.to_scalar::<f32>()?));
        }

        let (scores, labels) = evaluate(&head, &splits[1])?;
        let score = metrics::auroc(&scores, &labels).unwrap_or(f64::NEG_INFINITY);
        println!(
            "epoch {epoch:3}  loss {:.4}  validation auroc {score:.4}{}",
            mean(&losses),
            if score > best { "  *" } else { "" }
        );
        if score > best {
            best = score;
            best_epoch = epoch;
            let tmp = std::env::temp_dir().join(format!("opendna-dis-{}.safetensors", std::process::id()));
            varmap.save(&tmp)?;
            best_weights = Some(std::fs::read(&tmp)?);
            let _ = std::fs::remove_file(&tmp);
        } else if epoch - best_epoch >= config.patience {
            println!("No improvement for {} epochs; stopping.", config.patience);
            break;
        }
    }

    if let Some(bytes) = best_weights {
        let tmp = std::env::temp_dir().join(format!("opendna-dis-best-{}.safetensors", std::process::id()));
        std::fs::write(&tmp, bytes)?;
        varmap.load(&tmp)?;
        let _ = std::fs::remove_file(&tmp);
    }

    let summarise = |rows: &[data::DisorderRow]| -> Result<SplitMetrics> {
        let (scores, labels) = evaluate(&head, rows)?;
        let confusion = metrics::Confusion::at(&scores, &labels, 0.5);
        Ok(SplitMetrics {
            n: labels.len(),
            values: metric_map(&[
                ("auroc", metrics::auroc(&scores, &labels)),
                ("auprc", metrics::auprc(&scores, &labels)),
                ("mcc", confusion.mcc()),
                ("f1", confusion.f1()),
                ("balanced_accuracy", confusion.balanced_accuracy()),
            ]),
        })
    };

    // Always predicting "disordered" — the floor any real model must clear.
    let (_, test_labels) = evaluate(&head, &splits[2])?;
    let ones = vec![1.0; test_labels.len()];
    let confusion = metrics::Confusion::at(&ones, &test_labels, 0.5);
    let baseline = SplitMetrics {
        n: test_labels.len(),
        values: metric_map(&[
            ("auroc", Some(0.5)),
            ("auprc", Some(test_labels.iter().filter(|l| **l).count() as f64 / test_labels.len() as f64)),
            ("f1", confusion.f1()),
            ("balanced_accuracy", confusion.balanced_accuracy()),
        ]),
    };

    let report = Report {
        task: Task::Disorder.name().to_string(),
        embedding_model: model_size.repo().to_string(),
        embedding_dim: hidden,
        best_epoch,
        epochs_run,
        learning_rate: config.learning_rate,
        batch_size: config.batch_size,
        seed: config.seed,
        seed_applied,
        validation: summarise(&splits[1])?,
        test: summarise(&splits[2])?,
        baseline,
    };
    save(&varmap, out_dir, Task::Disorder, model_size, hidden, &report)?;
    Ok(report)
}
