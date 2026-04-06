use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A protein sequence with metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Protein {
    pub id: String,
    pub name: String,
    pub sequence: Sequence,
    pub structure: Option<Structure>,
    pub metadata: HashMap<String, serde_json::Value>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl Protein {
    pub fn new(name: impl Into<String>, sequence: impl Into<String>) -> Self {
        let now = Utc::now();
        let seq = Sequence::new(sequence);
        let id = seq.hash();
        Self {
            id,
            name: name.into(),
            sequence: seq,
            structure: None,
            metadata: HashMap::new(),
            created_at: now,
            updated_at: now,
        }
    }

    pub fn len(&self) -> usize {
        self.sequence.len()
    }

    pub fn is_empty(&self) -> bool {
        self.sequence.is_empty()
    }
}

/// An amino acid sequence.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Sequence {
    pub residues: String,
}

impl Sequence {
    pub fn new(residues: impl Into<String>) -> Self {
        let residues = residues.into().to_uppercase().replace(" ", "");
        Self { residues }
    }

    pub fn len(&self) -> usize {
        self.residues.len()
    }

    pub fn is_empty(&self) -> bool {
        self.residues.is_empty()
    }

    pub fn hash(&self) -> String {
        use sha2::{Digest, Sha256};
        let mut hasher = Sha256::new();
        hasher.update(self.residues.as_bytes());
        format!("{:x}", hasher.finalize())[..12].to_string()
    }

    pub fn is_valid(&self) -> bool {
        let valid_aa = "ACDEFGHIKLMNPQRSTVWY";
        self.residues.chars().all(|c| valid_aa.contains(c))
    }
}

/// A 3D protein structure.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Structure {
    pub atoms: Vec<Atom>,
    pub residues: Vec<Residue>,
    pub confidence: Option<Vec<f32>>,
    pub format: StructureFormat,
}

impl Structure {
    pub fn num_atoms(&self) -> usize {
        self.atoms.len()
    }

    pub fn num_residues(&self) -> usize {
        self.residues.len()
    }

    pub fn mean_confidence(&self) -> Option<f32> {
        self.confidence.as_ref().map(|c| {
            if c.is_empty() {
                return 0.0;
            }
            c.iter().sum::<f32>() / c.len() as f32
        })
    }
}

/// A single atom in a structure.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Atom {
    pub serial: u32,
    pub name: String,
    pub residue_name: String,
    pub chain_id: char,
    pub residue_seq: u32,
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub occupancy: f64,
    pub temp_factor: f64,
    pub element: String,
}

/// A residue in a structure.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Residue {
    pub name: String,
    pub chain_id: char,
    pub seq_num: u32,
    pub atoms: Vec<usize>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum StructureFormat {
    PDB,
    MmCIF,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_protein_creation() {
        let p = Protein::new("Test Protein", "MKTVRQERLKSIVRILERSKEPVSGAQLAEELS");
        assert_eq!(p.name, "Test Protein");
        assert_eq!(p.len(), 33);
        assert!(!p.is_empty());
    }

    #[test]
    fn test_sequence_validation() {
        let valid = Sequence::new("MKTVRQERLK");
        assert!(valid.is_valid());

        let invalid = Sequence::new("MKTXZJ");
        assert!(!invalid.is_valid());
    }

    #[test]
    fn test_sequence_hash() {
        let s1 = Sequence::new("MKTVRQERLK");
        let s2 = Sequence::new("MKTVRQERLK");
        assert_eq!(s1.hash(), s2.hash());

        let s3 = Sequence::new("DIFFERENT");
        assert_ne!(s1.hash(), s3.hash());
    }
}
