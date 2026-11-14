use super::Mlp;
use candle_core::{Module, Tensor};
use candle_nn::VarBuilder;

/// Number of standard amino acids, the width of each one-hot block.
const AMINO_ACIDS: usize = 20;
/// Wild-type one-hot, mutant one-hot, and the language model's log-odds.
const EXTRA_FEATURES: usize = AMINO_ACIDS * 2 + 1;

/// Predicts the change in folding free energy, ΔΔG, for a point mutation.
///
/// Features per mutation, concatenated:
/// - the wild-type sequence's embedding **at the mutated position**;
/// - one-hot encodings of the wild-type and mutant residues;
/// - the masked-language-model log-odds `log P(mutant) - log P(wild type)` at
///   that position, which is a strong predictor on its own (Meier et al., 2021)
///   and lets the head start from a sensible zero-shot signal.
///
/// The sign convention is the dataset's: negative ΔΔG is destabilising.
#[derive(Debug)]
pub struct StabilityHead {
    mlp: Mlp,
}

/// Assembled features for a batch of mutations.
#[derive(Debug, Clone)]
pub struct StabilityFeatures {
    /// Row-major `(batch, embedding_dim + 41)`.
    pub values: Vec<f32>,
    /// Number of mutations.
    pub batch: usize,
    /// Width of one row.
    pub width: usize,
}

impl StabilityHead {
    /// Width of one input row for a given embedding size.
    pub fn input_width(embedding_dim: usize) -> usize {
        embedding_dim + EXTRA_FEATURES
    }

    /// Hidden widths used by the released model.
    pub fn hidden_widths() -> [usize; 2] {
        [256, 64]
    }

    /// Build the head.
    ///
    /// # Errors
    /// Propagates tensor errors.
    pub fn new(embedding_dim: usize, vb: VarBuilder<'_>) -> candle_core::Result<Self> {
        let [a, b] = Self::hidden_widths();
        Ok(Self { mlp: Mlp::new(&[Self::input_width(embedding_dim), a, b, 1], vb)? })
    }

    /// Predict ΔΔG for each row of `features`, returning `(batch,)`.
    ///
    /// # Errors
    /// Propagates tensor errors.
    pub fn forward(&self, features: &Tensor) -> candle_core::Result<Tensor> {
        self.mlp.forward(features)?.squeeze(1)
    }

    /// Assemble one feature row.
    ///
    /// `embedding` is the wild-type embedding at the mutated position.
    /// `wild_type` and `mutant` are indices into the 20 standard amino acids.
    /// `log_odds` is the language model's `log P(mutant) - log P(wild type)`.
    pub fn features(embedding: &[f32], wild_type: usize, mutant: usize, log_odds: f32) -> Vec<f32> {
        let mut row = Vec::with_capacity(embedding.len() + EXTRA_FEATURES);
        row.extend_from_slice(embedding);
        for index in [wild_type, mutant] {
            let start = row.len();
            row.resize(start + AMINO_ACIDS, 0.0);
            if index < AMINO_ACIDS {
                row[start + index] = 1.0;
            }
        }
        row.push(log_odds);
        row
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[allow(clippy::float_cmp, reason = "one-hot entries are exactly 0.0 or 1.0")]
    fn feature_row_has_expected_layout() {
        let emb = [0.5f32; 8];
        let row = StabilityHead::features(&emb, 3, 7, -1.5);
        assert_eq!(row.len(), StabilityHead::input_width(8));
        assert_eq!(&row[..8], &emb);
        assert_eq!(row[8 + 3], 1.0, "wild-type one-hot");
        assert_eq!(row[8 + AMINO_ACIDS + 7], 1.0, "mutant one-hot");
        assert_eq!(row[row.len() - 1], -1.5, "log-odds is the last feature");
        assert_eq!(row[8..8 + AMINO_ACIDS].iter().sum::<f32>(), 1.0);
    }
}
