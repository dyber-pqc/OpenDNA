//! Prediction heads trained on frozen ESM-2 embeddings.
//!
//! Each head is defined once here and used both for training (in the
//! `training/` workspace) and for inference in the desktop app, so the two
//! cannot drift apart. A head is small — a few hundred thousand parameters —
//! and is distributed as its own safetensors file alongside a JSON
//! description of the embedding it expects.
//!
//! Heads deliberately do **not** fall back to a heuristic when weights are
//! missing: [`crate::MlError`] is returned instead, so the caller can say the
//! prediction is unavailable rather than present a fabricated number.

mod burial;
mod disorder;
mod loader;
mod mlp;
mod solubility;
mod stability;

pub use burial::BurialHead;
pub use disorder::DisorderHead;
pub use loader::{read_metadata, sha256_file, HeadFiles, Heads, Integrity, License};
pub use mlp::Mlp;
pub use solubility::SolubilityHead;
pub use stability::{StabilityFeatures, StabilityHead};

use serde::{Deserialize, Serialize};

/// A fitted map from a head's raw logit to a calibrated probability.
///
/// `probability = sigmoid(slope * logit + intercept)`.
///
/// The disorder head is trained with weighted cross-entropy to stop it
/// predicting "ordered" everywhere, which helps the ranking and inflates the
/// probabilities. This undoes the inflation without touching the ranking:
/// the map is monotonic, so AUROC and every other rank statistic are
/// unchanged by it.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Calibration {
    /// Multiplier on the logit.
    pub slope: f64,
    /// Added to the scaled logit.
    pub intercept: f64,
    /// Which family the map was fitted from, for the record.
    pub method: String,
    /// Expected calibration error on the held-out split before the map.
    pub test_ece_before: f64,
    /// And after. Both recorded so the card can state what it bought
    /// rather than asserting that it helped.
    pub test_ece_after: f64,
    /// Probability at or above which a residue is called positive.
    ///
    /// Measured alongside the map and meaningless without it: 0.34 on a
    /// calibrated scale and 0.34 on a raw one are different decisions. Chosen
    /// on the validation split, so the accompanying MCC is an honest estimate
    /// rather than the best number findable with the test labels in hand.
    pub threshold: f64,
    /// Matthews correlation at that threshold on the held-out split.
    pub test_mcc: f64,
}

impl Calibration {
    /// Apply the map to a raw logit.
    pub fn apply(&self, logit: f32) -> f32 {
        let z = self.slope * f64::from(logit) + self.intercept;
        #[allow(clippy::cast_possible_truncation)]
        let p = if z >= 0.0 { 1.0 / (1.0 + (-z).exp()) } else { z.exp() / (1.0 + z.exp()) } as f32;
        p
    }
}

/// What a head was trained against. Stored next to the weights so inference
/// cannot silently pair a head with the wrong embedding model.
///
/// Not `Eq`: a recorded calibration holds floating-point coefficients, and
/// pretending two of those compare exactly would be a lie the type system
/// would then enforce.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HeadMetadata {
    /// Head identifier, e.g. `stability`.
    pub task: String,
    /// Hugging Face repository of the embedding model.
    pub embedding_model: String,
    /// Embedding width the head expects.
    pub embedding_dim: usize,
    /// Version of the trained head. Semantic, and distinct per head: two
    /// heads that differ must not share a version string.
    pub version: String,
    /// Identifies the exact training run: a digest over the dataset files,
    /// the hyperparameters, the embedding model and the code version.
    ///
    /// Two heads with the same `version` and the same `build` were produced
    /// by the same inputs. A differing build with the same version means
    /// somebody retrained without bumping, which is worth knowing.
    #[serde(default)]
    pub build: Option<String>,
    /// SHA-256 of the weights file this metadata describes.
    ///
    /// Lets an installation prove the weights on disk are the ones the
    /// metadata names, which is the question an audit asks and the one a
    /// half-finished download answers wrongly.
    #[serde(default)]
    pub weights_sha256: Option<String>,
    /// Whether the head takes predicted solvent accessibility at the mutated
    /// position as an extra feature. Stability only.
    ///
    /// Defaults to false so metadata written before this existed still
    /// parses, and so a head that does not say otherwise is the plain
    /// variant — which is the one that was published.
    #[serde(default)]
    pub with_burial: bool,
    /// How to turn this head's raw output into a calibrated probability.
    ///
    /// Absent means uncalibrated, which is what every head trained before
    /// this was measured is. Absent is not the same as "calibration was
    /// checked and found unnecessary", and the model card says which.
    #[serde(default)]
    pub calibration: Option<Calibration>,
}
