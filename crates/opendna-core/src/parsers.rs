use crate::models::{Atom, Residue, Structure, StructureFormat};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ParseError {
    #[error("Invalid PDB format: {0}")]
    InvalidPdb(String),
    #[error("Invalid FASTA format: {0}")]
    InvalidFasta(String),
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

/// Parse a PDB file into a Structure.
pub fn parse_pdb(content: &str) -> Result<Structure, ParseError> {
    let mut atoms = Vec::new();
    let mut residues_map: std::collections::BTreeMap<(char, u32), Vec<usize>> =
        std::collections::BTreeMap::new();

    for line in content.lines() {
        if line.starts_with("ATOM") || line.starts_with("HETATM") {
            if line.len() < 54 {
                continue;
            }
            let atom = parse_pdb_atom(line)?;
            let key = (atom.chain_id, atom.residue_seq);
            residues_map
                .entry(key)
                .or_default()
                .push(atoms.len());
            atoms.push(atom);
        }
    }

    let residues: Vec<Residue> = residues_map
        .iter()
        .map(|((chain_id, seq_num), atom_indices)| {
            let name = atoms[atom_indices[0]].residue_name.clone();
            Residue {
                name,
                chain_id: *chain_id,
                seq_num: *seq_num,
                atoms: atom_indices.clone(),
            }
        })
        .collect();

    Ok(Structure {
        atoms,
        residues,
        confidence: None,
        format: StructureFormat::PDB,
    })
}

fn parse_pdb_atom(line: &str) -> Result<Atom, ParseError> {
    let parse = |s: &str, field: &str| -> Result<f64, ParseError> {
        s.trim()
            .parse::<f64>()
            .map_err(|_| ParseError::InvalidPdb(format!("Cannot parse {field}: '{s}'")))
    };

    Ok(Atom {
        serial: line[6..11]
            .trim()
            .parse()
            .unwrap_or(0),
        name: line[12..16].trim().to_string(),
        residue_name: line[17..20].trim().to_string(),
        chain_id: line.as_bytes().get(21).map(|&b| b as char).unwrap_or('A'),
        residue_seq: line[22..26].trim().parse().unwrap_or(0),
        x: parse(&line[30..38], "x")?,
        y: parse(&line[38..46], "y")?,
        z: parse(&line[46..54], "z")?,
        occupancy: line.get(54..60).and_then(|s| s.trim().parse().ok()).unwrap_or(1.0),
        temp_factor: line.get(60..66).and_then(|s| s.trim().parse().ok()).unwrap_or(0.0),
        element: line.get(76..78).map(|s| s.trim().to_string()).unwrap_or_default(),
    })
}

/// Parse a FASTA file into a list of (name, sequence) pairs.
pub fn parse_fasta(content: &str) -> Result<Vec<(String, String)>, ParseError> {
    let mut results = Vec::new();
    let mut current_name = String::new();
    let mut current_seq = String::new();

    for line in content.lines() {
        let line = line.trim();
        if line.starts_with('>') {
            if !current_name.is_empty() {
                results.push((current_name.clone(), current_seq.clone()));
                current_seq.clear();
            }
            current_name = line[1..].trim().to_string();
        } else if !line.is_empty() && !line.starts_with(';') {
            current_seq.push_str(line);
        }
    }

    if !current_name.is_empty() {
        results.push((current_name, current_seq));
    }

    if results.is_empty() {
        return Err(ParseError::InvalidFasta("No sequences found".to_string()));
    }

    Ok(results)
}

/// Write a Structure to PDB format.
pub fn write_pdb(structure: &Structure) -> String {
    let mut output = String::new();

    for atom in &structure.atoms {
        output.push_str(&format!(
            "ATOM  {:>5} {:<4} {:>3} {}{:>4}    {:>8.3}{:>8.3}{:>8.3}{:>6.2}{:>6.2}          {:>2}\n",
            atom.serial,
            atom.name,
            atom.residue_name,
            atom.chain_id,
            atom.residue_seq,
            atom.x,
            atom.y,
            atom.z,
            atom.occupancy,
            atom.temp_factor,
            atom.element,
        ));
    }

    output.push_str("END\n");
    output
}

/// Write sequences to FASTA format.
pub fn write_fasta(sequences: &[(String, String)]) -> String {
    let mut output = String::new();
    for (name, seq) in sequences {
        output.push_str(&format!(">{name}\n"));
        for chunk in seq.as_bytes().chunks(80) {
            output.push_str(&String::from_utf8_lossy(chunk));
            output.push('\n');
        }
    }
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_fasta() {
        let fasta = ">test_protein\nMKTVRQERLK\nSIVRILER\n>second\nACDEFG\n";
        let result = parse_fasta(fasta).unwrap();
        assert_eq!(result.len(), 2);
        assert_eq!(result[0].0, "test_protein");
        assert_eq!(result[0].1, "MKTVRQERLKSIVRILER");
        assert_eq!(result[1].1, "ACDEFG");
    }

    #[test]
    fn test_roundtrip_fasta() {
        let seqs = vec![
            ("protein_1".to_string(), "MKTVRQERLK".to_string()),
            ("protein_2".to_string(), "ACDEFGHIK".to_string()),
        ];
        let fasta = write_fasta(&seqs);
        let parsed = parse_fasta(&fasta).unwrap();
        assert_eq!(parsed.len(), 2);
        assert_eq!(parsed[0].1, "MKTVRQERLK");
    }

    #[test]
    fn test_parse_pdb_atom() {
        let line = "ATOM      1  N   ALA A   1       1.000   2.000   3.000  1.00  0.00           N  ";
        let atom = parse_pdb_atom(line).unwrap();
        assert_eq!(atom.name, "N");
        assert_eq!(atom.residue_name, "ALA");
        assert_eq!(atom.chain_id, 'A');
        assert!((atom.x - 1.0).abs() < 0.001);
    }
}
