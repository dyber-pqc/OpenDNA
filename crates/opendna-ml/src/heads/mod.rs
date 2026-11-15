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

/// What a head was trained against. Stored next to the weights so inference
/// cannot silently pair a head with the wrong embedding model.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
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
}
