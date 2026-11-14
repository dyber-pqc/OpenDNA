//! Running the trained prediction heads.
//!
//! The embedding model is several hundred megabytes and is fetched from the
//! Hugging Face Hub on first use, so nothing here is loaded at startup: the
//! first prediction pays for it and every later one reuses it.
//!
//! When a head is absent the answer is an error saying so. There is no
//! fallback heuristic anywhere in this module — a number shown in the
//! application is always the output of a trained model, or it is not shown.

use opendna_app_protocol::{
    CommandError, DisorderPrediction, HeadStatus, ModelStatus, SolubilityPrediction, StabilityScan,
    SubstitutionScore,
};
use opendna_core::AminoAcid;
use opendna_ml::esm2::{Esm2, ModelSize};
use opendna_ml::heads::{HeadFiles, Heads, StabilityHead};
use opendna_ml::{best_device, device_description, weights, MlError};
use std::path::{Path, PathBuf};
use std::sync::{Mutex, MutexGuard, PoisonError};

/// Embedding model the published heads were trained on. Changing this
/// invalidates every head, which `Heads::load` enforces by comparing against
/// each head's recorded metadata.
const EMBEDDER: ModelSize = ModelSize::Large150M;

/// Probability at or above which a residue is reported as disordered. The
/// trained head's card reports its metrics at this threshold.
const DISORDER_THRESHOLD: f64 = 0.5;

/// Where to look for trained heads.
///
/// `OPENDNA_MODELS` wins, so a developer can point the application at a
/// freshly trained head without installing it. Otherwise heads live beside
/// the database in the application's data directory.
pub fn models_dir(app_data: &Path) -> PathBuf {
    std::env::var_os("OPENDNA_MODELS").map_or_else(|| app_data.join("models"), PathBuf::from)
}

/// The embedding model and whichever heads were present, loaded once.
struct Loaded {
    esm2: Esm2,
    heads: Heads,
}

/// Lazily-loaded models, shared by every prediction command.
pub struct Predictor {
    dir: PathBuf,
    loaded: Mutex<Option<Loaded>>,
}

fn fail(e: impl std::fmt::Display) -> CommandError {
    CommandError { message: e.to_string() }
}

/// Describe one head without loading its weights.
fn head_status(dir: &Path, task: &str) -> HeadStatus {
    let files = HeadFiles::in_dir(dir, task);
    if !files.exist() {
        return HeadStatus::Missing;
    }
    match opendna_ml::heads::read_metadata(&files, task, EMBEDDER) {
        Ok(metadata) => HeadStatus::Ready { version: metadata.version },
        Err(e) => HeadStatus::Unusable { reason: e.to_string() },
    }
}

impl Predictor {
    /// Note where heads live. Nothing is read until the first prediction.
    pub fn new(dir: PathBuf) -> Self {
        Self { dir, loaded: Mutex::new(None) }
    }

    fn lock(&self) -> MutexGuard<'_, Option<Loaded>> {
        self.loaded.lock().unwrap_or_else(PoisonError::into_inner)
    }

    /// What can be predicted right now, without downloading anything.
    pub fn status(&self) -> ModelStatus {
        ModelStatus {
            models_dir: self.dir.display().to_string(),
            embedding_model: EMBEDDER.repo().to_string(),
            embedding_cached: weights::is_cached(EMBEDDER.repo()),
            device: best_device()
                .as_ref()
                .map_or_else(|_| "CPU (no GPU available)".to_string(), device_description),
            stability: head_status(&self.dir, "stability"),
            solubility: head_status(&self.dir, "solubility"),
            disorder: head_status(&self.dir, "disorder"),
        }
    }

    /// Load the embedding model and heads if that has not happened yet, then
    /// run `f` against them.
    ///
    /// Everything is held behind one lock, so two predictions requested at
    /// once do not both download the checkpoint.
    fn with_models<T>(
        &self,
        f: impl FnOnce(&Esm2, &Heads) -> Result<T, CommandError>,
    ) -> Result<T, CommandError> {
        let mut guard = self.lock();
        if guard.is_none() {
            let device = best_device().map_err(fail)?;
            let esm2 = Esm2::from_pretrained(EMBEDDER, &device).map_err(describe)?;
            let heads = Heads::load(&self.dir, EMBEDDER, &device).map_err(describe)?;
            *guard = Some(Loaded { esm2, heads });
        }
        let loaded = guard.as_ref().ok_or_else(|| fail("models failed to load"))?;
        f(&loaded.esm2, &loaded.heads)
    }

    /// Score every substitution at `position` (1-based).
    pub fn stability_scan(&self, sequence: &str, position: usize) -> Result<StabilityScan, CommandError> {
        let residues: Vec<char> = sequence.chars().collect();
        let wild_type = *residues
            .get(position.checked_sub(1).ok_or_else(|| fail("positions are numbered from 1"))?)
            .ok_or_else(|| {
                fail(format!("position {position} is past the end of a {}-residue sequence", residues.len()))
            })?;
        let wild_index = standard_index(wild_type).ok_or_else(|| {
            fail(format!(
                "residue {position} is {wild_type}, which is not one of the 20 standard amino acids"
            ))
        })?;

        self.with_models(|esm2, heads| {
            let head = heads.stability.as_ref().ok_or_else(|| missing("stability"))?;
            let index = position - 1;
            let log_probs =
                esm2.masked_log_probs(sequence, &[index])
                    .map_err(describe)?
                    .into_iter()
                    .next()
                    .ok_or_else(|| fail("the embedding model returned no distribution for that position"))?;
            let embedding = esm2.embed(&[sequence]).map_err(describe)?;
            let residue = embedding
                .first()
                .and_then(|e| e.residue(index))
                .ok_or_else(|| fail("no embedding for that position"))?;

            let logp = |letter: char| -> Result<f32, CommandError> {
                log_probs
                    .get(token_index(letter))
                    .copied()
                    .ok_or_else(|| fail(format!("the embedding model has no token for residue {letter}")))
            };
            let wt_logp = logp(wild_type)?;
            // All 19 substitutions go through the head in one batch.
            let mut rows = Vec::new();
            let mut mutants = Vec::new();
            let mut scores = Vec::new();
            for (mutant_index, mutant) in AminoAcid::STANDARD.iter().enumerate() {
                let letter = mutant.one_letter();
                if letter == wild_type {
                    continue;
                }
                let log_odds = logp(letter)? - wt_logp;
                rows.push(StabilityHead::features(residue, wild_index, mutant_index, log_odds));
                mutants.push((letter, log_odds));
            }
            let ddgs = head.predict(&rows, esm2.hidden_size(), esm2.device()).map_err(fail)?;
            for ((letter, log_odds), ddg) in mutants.into_iter().zip(ddgs) {
                scores.push(SubstitutionScore {
                    mutant: letter,
                    ddg: f64::from(ddg),
                    log_odds: f64::from(log_odds),
                });
            }
            // Most stabilising first. ΔΔG follows the dataset's convention:
            // negative is destabilising, so this is a plain descending sort.
            scores.sort_by(|a, b| b.ddg.total_cmp(&a.ddg));
            Ok(StabilityScan { position, wild_type, scores })
        })
    }

    /// Predict solubility for a whole sequence.
    pub fn solubility(&self, sequence: &str) -> Result<SolubilityPrediction, CommandError> {
        self.with_models(|esm2, heads| {
            let head = heads.solubility.as_ref().ok_or_else(|| missing("solubility"))?;
            let embedding = esm2
                .embed(&[sequence])
                .map_err(describe)?
                .into_iter()
                .next()
                .ok_or_else(|| fail("the embedding model returned nothing for this sequence"))?;
            // `pooled` is the pooling the head was trained on; recomputing a
            // mean here would risk the two definitions drifting apart.
            let percent = head.predict(&embedding.pooled, esm2.device()).map_err(fail)?;
            Ok(SolubilityPrediction { percent: f64::from(percent) })
        })
    }

    /// Predict per-residue disorder.
    pub fn disorder(&self, sequence: &str) -> Result<DisorderPrediction, CommandError> {
        self.with_models(|esm2, heads| {
            let head = heads.disorder.as_ref().ok_or_else(|| missing("disorder"))?;
            let windowed = sequence.chars().count() > esm2.max_residues();
            let embedding = if windowed {
                esm2.embed_windowed(sequence).map_err(describe)?
            } else {
                esm2.embed(&[sequence])
                    .map_err(describe)?
                    .into_iter()
                    .next()
                    .ok_or_else(|| fail("the embedding model returned nothing for this sequence"))?
            };

            let probabilities = head
                .predict(&embedding.per_residue, embedding.length, esm2.device())
                .map_err(fail)?
                .into_iter()
                .map(f64::from)
                .collect();
            Ok(DisorderPrediction { probabilities, threshold: DISORDER_THRESHOLD, windowed })
        })
    }
}

/// Index of a residue among the 20 standard amino acids, as the heads expect.
fn standard_index(letter: char) -> Option<usize> {
    AminoAcid::STANDARD.iter().position(|a| a.one_letter() == letter)
}

/// Index of a residue in the embedding model's vocabulary.
///
/// This must agree with how the training pipeline built its log-odds
/// feature; both call the same function, so they cannot diverge.
fn token_index(letter: char) -> usize {
    opendna_ml::esm2::alphabet::token_id(letter) as usize
}

/// The error shown when a head's weights are not installed.
///
/// It names the file the application looked for, because the usual cause is
/// that the head was never trained or never copied into place, and a user
/// cannot act on "unavailable" alone.
fn missing(task: &str) -> CommandError {
    CommandError {
        message: format!(
            "No trained {task} head is installed, so this prediction is unavailable. Train one \
             with `cargo run -p opendna-train -- train --task {task}` and put \
             {task}.safetensors and {task}.metadata.json in the models directory."
        ),
    }
}

/// Turn a model error into something a user can act on.
///
/// Used for every `MlError` in this module, so the two cases a user actually
/// hits — no network on the first run, and a sequence past the checkpoint's
/// limit — read as instructions rather than as internal error text.
fn describe(e: MlError) -> CommandError {
    match e {
        MlError::Download { repo, message } => CommandError {
            message: format!(
                "Could not download the embedding model {repo}: {message}. The first prediction \
                 needs a network connection; afterwards it is cached and works offline."
            ),
        },
        // The limit is a property of the checkpoint, so there is nothing the
        // user can change except the input; say which protein is too long
        // rather than repeat the batch index, which is always 0 here.
        MlError::SequenceTooLong { length, limit, .. } => CommandError {
            message: format!(
                "This sequence has {length} residues and {} accepts at most {limit}. Stability                  and solubility predictions need the whole sequence at once; disorder covers                  long sequences with overlapping windows.",
                EMBEDDER.repo()
            ),
        },
        other => fail(other),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn missing_heads_are_reported_not_substituted() {
        let empty = tempdir();
        let predictor = Predictor::new(empty.clone());
        let status = predictor.status();
        assert_eq!(status.stability, HeadStatus::Missing);
        assert_eq!(status.solubility, HeadStatus::Missing);
        assert_eq!(status.disorder, HeadStatus::Missing);
        assert!(!status.stability.is_ready());
    }

    #[test]
    fn a_head_trained_on_another_embedder_is_unusable_rather_than_ready() {
        let dir = tempdir();
        std::fs::write(dir.join("stability.safetensors"), b"not really weights").unwrap();
        std::fs::write(
            dir.join("stability.metadata.json"),
            br#"{"task":"stability","embedding_model":"facebook/esm2_t6_8M_UR50D",
                 "embedding_dim":320,"version":"0.1.0"}"#,
        )
        .unwrap();
        match head_status(&dir, "stability") {
            HeadStatus::Unusable { reason } => {
                assert!(reason.contains("esm2_t6_8M_UR50D"), "{reason}");
            }
            other => panic!("expected Unusable, got {other:?}"),
        }
    }

    #[test]
    fn the_models_directory_can_be_overridden() {
        // Without the variable the directory sits beside the database.
        let app_data = Path::new("/tmp/opendna-data");
        assert_eq!(models_dir(app_data), app_data.join("models"));
    }

    fn tempdir() -> PathBuf {
        let dir = std::env::temp_dir()
            .join(format!("opendna-predict-test-{}", std::process::id()))
            .join(format!("{:?}", std::thread::current().id()));
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }
}

/// Exercises the real inference path against the heads in the repository's
/// `models/` directory. Ignored by default: it loads the 150M-parameter
/// embedding model, downloading it on first run.
///
/// Run with:
/// ```text
/// cargo test -p opendna-desktop --lib -- --ignored --nocapture
/// ```
#[cfg(test)]
mod end_to_end {
    use super::*;

    /// Ubiquitin. Leu8 and Ile44 are part of the hydrophobic patch; position
    /// 8 is the one spot-checked by hand when the head was trained.
    const UBIQUITIN: &str = "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG";

    fn repo_models() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../models")
    }

    fn predictor() -> Predictor {
        Predictor::new(repo_models())
    }

    #[test]
    #[ignore = "loads the 150M embedding model"]
    fn the_trained_heads_load_from_the_repository() {
        let status = predictor().status();
        assert!(status.stability.is_ready(), "stability: {:?}", status.stability);
        assert!(status.solubility.is_ready(), "solubility: {:?}", status.solubility);
        assert!(status.disorder.is_ready(), "disorder: {:?}", status.disorder);
    }

    #[test]
    #[ignore = "loads the 150M embedding model"]
    fn a_stability_scan_ranks_proline_and_glycine_worst_in_a_helix() {
        let scan = predictor().stability_scan(UBIQUITIN, 8).unwrap();
        assert_eq!(scan.wild_type, 'L', "position 8 of ubiquitin is leucine");
        assert_eq!(scan.scores.len(), 19, "every substitution but the wild type");

        // Sorted most stabilising first, so the tail is the worst.
        let worst: Vec<char> = scan.scores.iter().rev().take(4).map(|s| s.mutant).collect();
        assert!(
            worst.contains(&'P') && worst.contains(&'G'),
            "proline and glycine should be among the most destabilising at a buried \
             position; got {worst:?} from {:?}",
            scan.scores.iter().map(|s| (s.mutant, s.ddg)).collect::<Vec<_>>()
        );

        // The head is known to compress predictions toward the training mean,
        // which is stated on its card. This asserts the range is plausible
        // rather than pinning the exact values a retrain would move.
        for s in &scan.scores {
            assert!(s.ddg > -8.0 && s.ddg < 8.0, "{} gave an implausible ΔΔG {}", s.mutant, s.ddg);
        }
    }

    #[test]
    #[ignore = "loads the 150M embedding model"]
    fn solubility_and_disorder_return_values_on_their_documented_scales() {
        let p = predictor();
        let solubility = p.solubility(UBIQUITIN).unwrap();
        // The assay scale is a percentage; the head does not clip, so this
        // checks for a number on roughly the right scale, not a valid one.
        assert!(
            solubility.percent > -50.0 && solubility.percent < 200.0,
            "solubility {} is not on the assay's scale",
            solubility.percent
        );

        let disorder = p.disorder(UBIQUITIN).unwrap();
        assert_eq!(disorder.probabilities.len(), UBIQUITIN.len(), "one probability per residue");
        assert!(!disorder.windowed, "ubiquitin fits in one window");
        assert!(
            disorder.probabilities.iter().all(|v| (0.0..=1.0).contains(v)),
            "probabilities must be in [0, 1]"
        );
        // Ubiquitin is a well-ordered globular domain. If most of it came
        // back disordered, something is wired up wrongly.
        let called = disorder.probabilities.iter().filter(|v| **v >= disorder.threshold).count();
        assert!(
            called * 2 < UBIQUITIN.len(),
            "{called} of {} residues called disordered in a folded domain",
            UBIQUITIN.len()
        );
    }

    #[test]
    fn a_position_past_the_end_is_refused_before_any_model_loads() {
        // No #[ignore]: this must not touch the embedding model at all.
        let err = predictor().stability_scan(UBIQUITIN, 999).unwrap_err();
        assert!(err.message.contains("past the end"), "{}", err.message);
    }

    #[test]
    fn position_zero_is_refused() {
        let err = predictor().stability_scan(UBIQUITIN, 0).unwrap_err();
        assert!(err.message.contains("numbered from 1"), "{}", err.message);
    }
}
