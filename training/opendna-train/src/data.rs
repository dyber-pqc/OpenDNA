//! Reading the Parquet datasets produced by the `datasets/` workspace.

use anyhow::{anyhow, bail, Context, Result};
use arrow::array::{Array, Float64Array, Int32Array, Int64Array, ListArray, StringArray};
use arrow::record_batch::RecordBatch;
use parquet::arrow::arrow_reader::ParquetRecordBatchReaderBuilder;
use std::fs::File;
use std::path::Path;

/// Which portion of a dataset to read.
#[derive(Debug, Clone, Copy, PartialEq, Eq, clap::ValueEnum)]
pub enum Split {
    /// Training rows.
    Train,
    /// Model selection and early stopping.
    Validation,
    /// Held out; read once, for the final numbers.
    Test,
}

impl Split {
    /// File stem used by the dataset builder.
    pub fn name(self) -> &'static str {
        match self {
            Self::Train => "train",
            Self::Validation => "validation",
            Self::Test => "test",
        }
    }

    /// All three, in order.
    pub fn all() -> [Split; 3] {
        [Split::Train, Split::Validation, Split::Test]
    }
}

fn read_batches(root: &Path, dataset: &str, split: Split) -> Result<Vec<RecordBatch>> {
    let path = root.join(dataset).join("data").join(format!("{}.parquet", split.name()));
    let file = File::open(&path).with_context(|| {
        format!("opening {}; build the datasets first (see datasets/README.md)", path.display())
    })?;
    let reader = ParquetRecordBatchReaderBuilder::try_new(file)
        .with_context(|| format!("reading {}", path.display()))?
        .build()?;
    reader.collect::<Result<Vec<_>, _>>().with_context(|| format!("decoding {}", path.display()))
}

fn strings(batch: &RecordBatch, column: &str) -> Result<Vec<String>> {
    let array = batch.column_by_name(column).ok_or_else(|| anyhow!("missing column {column}"))?;
    let array = array
        .as_any()
        .downcast_ref::<StringArray>()
        .ok_or_else(|| anyhow!("column {column} is not a string column"))?;
    (0..array.len())
        .map(|i| {
            if array.is_null(i) {
                bail!("column {column} has a null at row {i}");
            }
            Ok(array.value(i).to_string())
        })
        .collect()
}

fn floats(batch: &RecordBatch, column: &str) -> Result<Vec<f64>> {
    let array = batch.column_by_name(column).ok_or_else(|| anyhow!("missing column {column}"))?;
    let array = array
        .as_any()
        .downcast_ref::<Float64Array>()
        .ok_or_else(|| anyhow!("column {column} is not a float column"))?;
    (0..array.len())
        .map(|i| {
            if array.is_null(i) {
                bail!("column {column} has a null at row {i}");
            }
            Ok(array.value(i))
        })
        .collect()
}

fn integers(batch: &RecordBatch, column: &str) -> Result<Vec<i64>> {
    let array = batch.column_by_name(column).ok_or_else(|| anyhow!("missing column {column}"))?;
    if let Some(a) = array.as_any().downcast_ref::<Int64Array>() {
        return Ok((0..a.len()).map(|i| a.value(i)).collect());
    }
    if let Some(a) = array.as_any().downcast_ref::<Int32Array>() {
        return Ok((0..a.len()).map(|i| i64::from(a.value(i))).collect());
    }
    bail!("column {column} is not an integer column")
}

/// One point mutation with its measured ΔΔG.
#[derive(Debug, Clone)]
pub struct StabilityRow {
    /// Wild-type sequence the mutation is applied to.
    pub wt_sequence: String,
    /// 0-based position of the substitution.
    pub position: usize,
    /// Wild-type residue.
    pub wild_type: char,
    /// Substituted residue.
    pub mutant: char,
    /// Measured change in folding free energy.
    pub ddg: f64,
}

/// Read the stability dataset.
///
/// # Errors
/// If the file is missing, malformed, or a mutation does not match its
/// wild-type sequence.
pub fn stability(root: &Path, split: Split) -> Result<Vec<StabilityRow>> {
    let mut out = Vec::new();
    for batch in read_batches(root, "stability", split)? {
        let sequences = strings(&batch, "wt_sequence")?;
        // The dataset stores 1-based positions.
        let positions = integers(&batch, "position")?;
        let wild = strings(&batch, "wt_aa")?;
        let mutant = strings(&batch, "mut_aa")?;
        let ddg = floats(&batch, "ddg")?;
        for i in 0..batch.num_rows() {
            let position = usize::try_from(positions[i] - 1)
                .with_context(|| format!("row {i}: position {} is out of range", positions[i]))?;
            let wt = wild[i].chars().next().ok_or_else(|| anyhow!("row {i}: empty wt_aa"))?;
            let mt = mutant[i].chars().next().ok_or_else(|| anyhow!("row {i}: empty mut_aa"))?;
            // Guard against an off-by-one in the position convention, which
            // would silently train the head on the wrong residue.
            let actual = sequences[i].as_bytes().get(position).map(|b| *b as char);
            if actual != Some(wt) {
                bail!("row {i}: sequence has {actual:?} at position {position} but the mutation says {wt:?}");
            }
            out.push(StabilityRow {
                wt_sequence: sequences[i].clone(),
                position,
                wild_type: wt,
                mutant: mt,
                ddg: ddg[i],
            });
        }
    }
    Ok(out)
}

/// One protein with its measured solubility.
#[derive(Debug, Clone)]
pub struct SolubilityRow {
    /// Amino-acid sequence.
    pub sequence: String,
    /// Solubility percentage as reported by the source assay.
    pub solubility: f64,
}

/// Read the solubility dataset.
///
/// # Errors
/// If the file is missing or malformed.
pub fn solubility(root: &Path, split: Split) -> Result<Vec<SolubilityRow>> {
    let mut out = Vec::new();
    for batch in read_batches(root, "solubility", split)? {
        let sequences = strings(&batch, "sequence")?;
        let values = floats(&batch, "solubility")?;
        for (sequence, solubility) in sequences.into_iter().zip(values) {
            out.push(SolubilityRow { sequence, solubility });
        }
    }
    Ok(out)
}

/// One protein with a per-residue disorder annotation.
#[derive(Debug, Clone)]
pub struct DisorderRow {
    /// Amino-acid sequence.
    pub sequence: String,
    /// One label per residue: `true` where the residue is disordered.
    pub disorder: Vec<bool>,
}

/// Read the disorder dataset.
///
/// # Errors
/// If the file is missing, malformed, or a label array does not match the
/// length of its sequence.
pub fn disorder(root: &Path, split: Split) -> Result<Vec<DisorderRow>> {
    let mut out = Vec::new();
    for batch in read_batches(root, "disorder", split)? {
        let sequences = strings(&batch, "sequence")?;
        let labels = batch
            .column_by_name("disorder")
            .ok_or_else(|| anyhow!("missing column disorder"))?
            .as_any()
            .downcast_ref::<ListArray>()
            .ok_or_else(|| anyhow!("column disorder is not a list column"))?
            .clone();
        for (i, sequence) in sequences.into_iter().enumerate() {
            let values = labels.value(i);
            let values = values
                .as_any()
                .downcast_ref::<Int64Array>()
                .map(|a| (0..a.len()).map(|j| a.value(j) != 0).collect::<Vec<_>>())
                .or_else(|| {
                    values
                        .as_any()
                        .downcast_ref::<Int32Array>()
                        .map(|a| (0..a.len()).map(|j| a.value(j) != 0).collect())
                })
                .ok_or_else(|| anyhow!("row {i}: disorder list is not an integer list"))?;
            if values.len() != sequence.len() {
                bail!("row {i}: {} labels for {} residues", values.len(), sequence.len());
            }
            out.push(DisorderRow { sequence, disorder: values });
        }
    }
    Ok(out)
}
