//! Loading trained heads from disk.
//!
//! A head is a pair of files written by the training workspace:
//! `<task>.safetensors` and `<task>.metadata.json`. The metadata records
//! which embedding model the head was trained against, and loading checks it,
//! so a head can never be paired with embeddings it was not trained on.

use super::{DisorderHead, HeadMetadata, SolubilityHead, StabilityHead};
use crate::esm2::ModelSize;
use crate::MlError;
use candle_core::{DType, Device};
use candle_nn::VarBuilder;
use std::path::{Path, PathBuf};

/// Where a head's two files live.
#[derive(Debug, Clone)]
pub struct HeadFiles {
    /// Weights.
    pub weights: PathBuf,
    /// Description of what the head expects.
    pub metadata: PathBuf,
}

impl HeadFiles {
    /// The conventional file names for `task` inside `dir`.
    pub fn in_dir(dir: &Path, task: &str) -> Self {
        Self {
            weights: dir.join(format!("{task}.safetensors")),
            metadata: dir.join(format!("{task}.metadata.json")),
        }
    }

    /// Whether both files are present.
    pub fn exist(&self) -> bool {
        self.weights.is_file() && self.metadata.is_file()
    }
}

/// Read and check a head's metadata.
///
/// # Errors
/// [`MlError::File`] if the metadata cannot be read, or [`MlError::Config`]
/// if it does not describe `task` or does not match `embedder`.
pub fn read_metadata(files: &HeadFiles, task: &str, embedder: ModelSize) -> Result<HeadMetadata, MlError> {
    let text = std::fs::read_to_string(&files.metadata)
        .map_err(|source| MlError::File { path: files.metadata.display().to_string(), source })?;
    let metadata: HeadMetadata = serde_json::from_str(&text)
        .map_err(|e| MlError::Config(format!("{}: {e}", files.metadata.display())))?;

    if metadata.task != task {
        return Err(MlError::Config(format!(
            "{} describes the {:?} head, not {task:?}",
            files.metadata.display(),
            metadata.task
        )));
    }
    if metadata.embedding_model != embedder.repo() {
        return Err(MlError::Config(format!(
            "the {task} head was trained on {} but {} is loaded; predictions would be meaningless",
            metadata.embedding_model,
            embedder.repo()
        )));
    }
    if metadata.embedding_dim != embedder.hidden_size() {
        return Err(MlError::Config(format!(
            "the {task} head expects {}-wide embeddings but {} produces {}",
            metadata.embedding_dim,
            embedder.repo(),
            embedder.hidden_size()
        )));
    }
    Ok(metadata)
}

fn var_builder<'a>(path: &Path, device: &Device) -> Result<VarBuilder<'a>, MlError> {
    let tensors = candle_core::safetensors::load(path, device)?;
    Ok(VarBuilder::from_tensors(tensors, DType::F32, device))
}

/// Every head trained against one embedding model, as far as they are present.
///
/// A missing head is `None` rather than an error: the application reports the
/// prediction as unavailable instead of inventing one.
pub struct Heads {
    /// ΔΔG head.
    pub stability: Option<StabilityHead>,
    /// Solubility head.
    pub solubility: Option<SolubilityHead>,
    /// Per-residue disorder head.
    pub disorder: Option<DisorderHead>,
}

impl Heads {
    /// Load whichever heads are present in `dir`.
    ///
    /// # Errors
    /// [`MlError`] if a head is present but unreadable or mismatched. A head
    /// that is simply absent is not an error.
    pub fn load(dir: &Path, embedder: ModelSize, device: &Device) -> Result<Self, MlError> {
        let dim = embedder.hidden_size();
        let load_one = |task: &str| -> Result<Option<VarBuilder<'_>>, MlError> {
            let files = HeadFiles::in_dir(dir, task);
            if !files.exist() {
                return Ok(None);
            }
            read_metadata(&files, task, embedder)?;
            Ok(Some(var_builder(&files.weights, device)?))
        };

        Ok(Self {
            stability: load_one("stability")?.map(|vb| StabilityHead::new(dim, vb)).transpose()?,
            solubility: load_one("solubility")?.map(|vb| SolubilityHead::new(dim, vb)).transpose()?,
            disorder: load_one("disorder")?.map(|vb| DisorderHead::new(dim, vb)).transpose()?,
        })
    }

    /// Names of the heads that loaded, for display.
    pub fn available(&self) -> Vec<&'static str> {
        let mut out = Vec::new();
        if self.stability.is_some() {
            out.push("stability");
        }
        if self.solubility.is_some() {
            out.push("solubility");
        }
        if self.disorder.is_some() {
            out.push("disorder");
        }
        out
    }
}
