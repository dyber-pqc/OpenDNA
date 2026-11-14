use super::Mlp;
use candle_core::{Module, Tensor};
use candle_nn::{conv1d, Conv1d, Conv1dConfig, VarBuilder};

/// Width of the convolution that smooths predictions along the chain.
/// Disorder comes in runs rather than isolated residues, so a little local
/// context helps; 9 residues is roughly the span of a short linker.
const KERNEL: usize = 9;
const CHANNELS: usize = 128;

/// Predicts, for each residue, whether it is intrinsically disordered.
///
/// A per-residue projection is followed by one convolution along the
/// sequence, then a per-residue output. The output is a **logit**; apply a
/// sigmoid for a probability.
#[derive(Debug)]
pub struct DisorderHead {
    project: Mlp,
    conv: Conv1d,
    output: Mlp,
}

impl DisorderHead {
    /// Build the head.
    ///
    /// # Errors
    /// Propagates tensor errors.
    pub fn new(embedding_dim: usize, vb: VarBuilder<'_>) -> candle_core::Result<Self> {
        let cfg = Conv1dConfig { padding: KERNEL / 2, ..Conv1dConfig::default() };
        Ok(Self {
            project: Mlp::new(&[embedding_dim, CHANNELS], vb.pp("project"))?,
            conv: conv1d(CHANNELS, CHANNELS, KERNEL, cfg, vb.pp("conv"))?,
            output: Mlp::new(&[CHANNELS, 64, 1], vb.pp("output"))?,
        })
    }

    /// Per-residue logits for one sequence.
    ///
    /// `embeddings` is `(length, embedding_dim)`; the result is `(length,)`.
    ///
    /// # Errors
    /// Propagates tensor errors.
    pub fn forward(&self, embeddings: &Tensor) -> candle_core::Result<Tensor> {
        let hidden = self.project.forward(embeddings)?.gelu_erf()?;
        // Conv1d wants (batch, channels, length).
        let shaped = hidden.transpose(0, 1)?.unsqueeze(0)?.contiguous()?;
        let convolved = self.conv.forward(&shaped)?.gelu_erf()?;
        let per_residue = convolved.squeeze(0)?.transpose(0, 1)?.contiguous()?;
        self.output.forward(&per_residue)?.squeeze(1)
    }
}
