//! What produced a number, carried alongside it.
//!
//! A prediction that travels without its model version and its limitations
//! becomes a fact in a spreadsheet, and then in a slide, and nobody can tell
//! later which model made it or what it does not cover. Every output this CLI
//! writes carries that information in the file itself, so losing it takes
//! deliberate effort rather than a copy-paste.

use opendna_ml::esm2::ModelSize;
use opendna_ml::heads::HeadMetadata;
use std::fmt::Write as _;

/// How a result file records what produced it.
pub struct Provenance {
    /// The task predicted.
    pub task: &'static str,
    /// Head version from the head's own metadata.
    pub head_version: String,
    /// Embedding model repository.
    pub embedding_model: String,
    /// Device the run used.
    pub device: String,
    /// Things a reader needs in order not to over-read the numbers. Taken
    /// from the model card's limitations, not written here, so the two cannot
    /// drift apart.
    pub limitations: Vec<String>,
}

impl Provenance {
    /// Collect provenance for a run.
    pub fn new(
        task: &'static str,
        metadata: &HeadMetadata,
        embedder: ModelSize,
        device: &str,
        limitations: Vec<String>,
    ) -> Self {
        Self {
            task,
            head_version: metadata.version.clone(),
            embedding_model: embedder.repo().to_string(),
            device: device.to_string(),
            limitations,
        }
    }

    /// Comment lines for a delimited file.
    ///
    /// `#` is the convention most readers already skip — pandas with
    /// `comment='#'`, R with `comment.char='#'`, and `csvkit` by default — so
    /// the provenance does not break a downstream parse.
    pub fn comment_block(&self) -> String {
        let mut out = String::new();
        let _ = writeln!(out, "# OpenDNA {} prediction", self.task);
        let _ = writeln!(out, "# head version: {}", self.head_version);
        let _ = writeln!(out, "# embedding model: {}", self.embedding_model);
        let _ = writeln!(out, "# device: {}", self.device);
        if self.limitations.is_empty() {
            let _ = writeln!(out, "# limitations: see the model card next to the weights");
        } else {
            let _ = writeln!(out, "# limitations:");
            for limitation in &self.limitations {
                // One limitation can be a paragraph; keep each on one line so
                // a reader skipping '#' lines skips whole lines.
                let flat = limitation.split_whitespace().collect::<Vec<_>>().join(" ");
                let _ = writeln!(out, "#   - {flat}");
            }
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_comment_block_names_the_model_and_is_all_comments() {
        let p = Provenance {
            task: "disorder",
            head_version: "0.6.0-dev".into(),
            embedding_model: "facebook/esm2_t30_150M_UR50D".into(),
            device: "CUDA GPU".into(),
            limitations: vec!["Annotated, not exhaustive.".into()],
        };
        let block = p.comment_block();
        assert!(block.lines().all(|l| l.starts_with('#')), "{block}");
        assert!(block.contains("0.6.0-dev"));
        assert!(block.contains("facebook/esm2_t30_150M_UR50D"));
        assert!(block.contains("Annotated, not exhaustive."));
    }

    /// A limitation spanning several lines in the card must not become several
    /// comment lines in a way that breaks when a reader strips only the first.
    #[test]
    fn a_wrapped_limitation_becomes_one_comment_line() {
        let p = Provenance {
            task: "disorder",
            head_version: "v".into(),
            embedding_model: "m".into(),
            device: "CPU".into(),
            limitations: vec!["one\n  two\n  three".into()],
        };
        let block = p.comment_block();
        assert!(block.contains("#   - one two three"), "{block}");
    }
}
