//! Fetching model weights from the Hugging Face Hub.
//!
//! Files are cached by the `hf-hub` client (under `HF_HOME`, or the user's
//! cache directory), so a repository is downloaded once per machine.

use crate::MlError;
use hf_hub::HFClientSync;
use std::path::PathBuf;

/// Local paths to a downloaded checkpoint.
#[derive(Debug, Clone)]
pub struct Checkpoint {
    /// `config.json`
    pub config: PathBuf,
    /// `model.safetensors`
    pub weights: PathBuf,
}

/// Download `repo`'s `config.json` and `model.safetensors`, or return the
/// cached copies. `repo` is `owner/name`, e.g. `facebook/esm2_t6_8M_UR50D`.
///
/// # Errors
/// [`MlError::Download`] if `repo` is malformed, the Hub cannot be reached,
/// or a file is absent.
pub fn fetch(repo: &str) -> Result<Checkpoint, MlError> {
    let fail = |message: String| MlError::Download { repo: repo.to_string(), message };
    let (owner, name) = repo
        .split_once('/')
        .ok_or_else(|| fail("expected an \"owner/name\" repository identifier".to_string()))?;
    let client = HFClientSync::new().map_err(|e| fail(e.to_string()))?;
    let model = client.model(owner, name);
    let get =
        |file: &str| model.download_file().filename(file).send().map_err(|e| fail(format!("{file}: {e}")));
    Ok(Checkpoint { config: get("config.json")?, weights: get("model.safetensors")? })
}
