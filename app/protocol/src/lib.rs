//! IPC message types shared by the desktop backend and the WebAssembly UI.
//!
//! Every Tauri command takes and returns types from this crate, so the two
//! sides cannot drift apart: a field rename is a compile error on both.
//! Command names are constants in [`command`].

use serde::{Deserialize, Serialize};

/// Tauri command names.
pub mod command {
    /// `() -> Vec<ProteinSummary>`
    pub const LIST_PROTEINS: &str = "list_proteins";
    /// `{ path: Option<String> } -> Vec<ProteinSummary>`; `None` opens a file dialog.
    pub const IMPORT_FILE: &str = "import_file";
    /// `{ id } -> ProteinDetail`
    pub const GET_PROTEIN: &str = "get_protein";
    /// `{ id } -> ()`
    pub const DELETE_PROTEIN: &str = "delete_protein";
    /// `{ id } -> SequenceReport`
    pub const ANALYZE_SEQUENCE: &str = "analyze_sequence";
    /// `{ id } -> StructureReport`
    pub const ANALYZE_STRUCTURE: &str = "analyze_structure";
}

/// One row in the project explorer.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProteinSummary {
    /// Content id.
    pub id: String,
    /// Display name.
    pub name: String,
    /// Residue count.
    pub length: usize,
    /// Whether 3D coordinates are available.
    pub has_structure: bool,
}

/// Everything the main view needs to show one protein.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProteinDetail {
    /// Summary fields.
    pub summary: ProteinSummary,
    /// One-letter sequence.
    pub sequence: String,
    /// Coordinate file for the viewer.
    pub structure: Option<StructurePayload>,
}

/// A coordinate file as handed to the 3D viewer.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StructurePayload {
    /// `pdb` or `mmcif`.
    pub format: String,
    /// Chain the sequence belongs to.
    pub chain: String,
    /// File contents.
    pub content: String,
}

/// Sequence-derived properties. See `opendna_analysis::properties`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SequenceReport {
    /// Residue count.
    pub length: usize,
    /// Average mass, Da.
    pub molecular_weight: f64,
    /// Isoelectric point.
    pub isoelectric_point: f64,
    /// Net charge at pH 7.
    pub charge_at_ph7: f64,
    /// Kyte–Doolittle grand average.
    pub gravy: f64,
    /// Fraction F+W+Y.
    pub aromaticity: f64,
    /// Ikai aliphatic index.
    pub aliphatic_index: f64,
    /// ε280, cysteines reduced (M⁻¹cm⁻¹).
    pub extinction_reduced: f64,
    /// ε280, all cystines formed.
    pub extinction_cystines: f64,
    /// Nine-residue Kyte–Doolittle window means, one per window start.
    pub hydropathy: Vec<f64>,
}

/// Per-residue structural annotation, aligned with the chain's observed residues.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ResidueAnnotation {
    /// Depositor residue number (with insertion code), as shown to users.
    pub label: String,
    /// Residue number without insertion code, for viewer selection.
    pub number: i32,
    /// One-letter amino acid.
    pub amino_acid: char,
    /// DSSP code (`H`, `E`, `G`, `I`, `T`, `S`, `B`, `-`).
    pub dssp: char,
    /// Relative solvent accessibility (Tien 2013 maxima), if defined.
    pub relative_sasa: Option<f64>,
    /// φ in degrees.
    pub phi: Option<f64>,
    /// ψ in degrees.
    pub psi: Option<f64>,
}

/// A residue pair interaction for display.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Contact {
    /// e.g. `A:CYS3`
    pub a: String,
    /// e.g. `A:CYS40`
    pub b: String,
    /// Å
    pub distance: f64,
}

/// Structure-derived analysis of one chain.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StructureReport {
    /// Chain analysed.
    pub chain: String,
    /// One entry per observed amino-acid residue in the chain.
    pub residues: Vec<ResidueAnnotation>,
    /// Cα radius of gyration, Å.
    pub radius_of_gyration: f64,
    /// Total SASA of the whole structure (heavy atoms, no waters), Å².
    pub total_sasa: f64,
    /// Disulfide bonds anywhere in the structure.
    pub disulfides: Vec<Contact>,
    /// Salt bridges anywhere in the structure.
    pub salt_bridges: Vec<Contact>,
}

/// Error returned by every command. `message` is safe to show to users.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CommandError {
    /// Human-readable description.
    pub message: String,
}
