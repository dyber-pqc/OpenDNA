//! Scores every substitution at one position of a sequence.
//!
//! ```text
//! cargo run --release -p opendna-ml --example predict_stability -- models MQIFVKTLTGK 7
//! ```
//!
//! Needs a trained `stability` head in the given directory; see `training/`.

#![allow(clippy::print_stdout, clippy::unwrap_used)]

use opendna_core::AminoAcid;
use opendna_ml::esm2::{Esm2, ModelSize};
use opendna_ml::heads::{Heads, StabilityHead};
use std::path::PathBuf;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let dir = PathBuf::from(args.next().unwrap_or_else(|| "models".into()));
    let sequence = args.next().unwrap_or_else(|| {
        "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG".into()
    });
    let position: usize = args.next().map_or(Ok(7), |s| s.parse())?;

    let embedder = ModelSize::Large150M;
    let device = opendna_ml::best_device()?;
    println!("Loading on {}", opendna_ml::device_description(&device));

    let heads = Heads::load(&dir, embedder, &device)?;
    let Some(head) = heads.stability.as_ref() else {
        println!("No stability head in {}. Train one first; see training/README.md.", dir.display());
        return Ok(());
    };

    let model = Esm2::from_pretrained(embedder, &device)?;
    let embedding = model.embed(&[&sequence])?.remove(0);
    let log_probs = model.masked_log_probs(&sequence, &[position])?.remove(0);

    let wild_type = sequence.as_bytes()[position] as char;
    let site = embedding.residue(position).unwrap();
    let wt_index = AminoAcid::STANDARD.iter().position(|a| a.one_letter() == wild_type).unwrap();
    let wt_logp = log_probs[opendna_ml::esm2::alphabet::token_id(wild_type) as usize];

    let mut scored = Vec::new();
    for (index, aa) in AminoAcid::STANDARD.iter().enumerate() {
        if *aa == AminoAcid::STANDARD[wt_index] {
            continue;
        }
        let logp = log_probs[opendna_ml::esm2::alphabet::token_id(aa.one_letter()) as usize];
        let row = StabilityHead::features(site, wt_index, index, logp - wt_logp);
        let width = row.len();
        let input = candle_core::Tensor::from_vec(row, (1, width), &device)?;
        scored.push((aa.one_letter(), head.forward(&input)?.to_vec1::<f32>()?[0]));
    }
    scored.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());

    println!("\nPredicted ddG at position {} (wild type {wild_type}), kcal/mol", position + 1);
    println!("Negative is destabilising. Most to least destabilising:\n");
    for (residue, ddg) in &scored {
        println!("  {wild_type}{}{residue}  {ddg:+.2}", position + 1);
    }
    Ok(())
}
