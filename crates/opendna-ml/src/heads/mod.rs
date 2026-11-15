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
pub use loader::{read_metadata, HeadFiles, Heads};
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
    /// Version of the trained head.
    pub version: String,
}
