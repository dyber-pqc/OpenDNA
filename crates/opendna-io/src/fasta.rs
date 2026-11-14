//! FASTA reader and writer.

use crate::IoError;
use opendna_core::{Protein, Sequence};
use std::fmt::Write;

/// Parse FASTA text into proteins. Lines starting with `;` are comments.
/// Sequences are parsed strictly; see [`Sequence::parse`].
///
/// # Errors
/// [`IoError::Malformed`] if sequence data appears before the first header,
/// [`IoError::InvalidSequence`] for a bad record body, and
/// [`IoError::Empty`] if there are no records.
pub fn read(content: &str) -> Result<Vec<Protein>, IoError> {
    let mut records: Vec<(String, String)> = Vec::new();
    for (idx, raw) in content.lines().enumerate() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with(';') {
            continue;
        }
        if let Some(header) = line.strip_prefix('>') {
            records.push((header.trim().to_string(), String::new()));
        } else if let Some((_, body)) = records.last_mut() {
            body.push_str(line);
        } else {
            return Err(IoError::malformed(idx + 1, "sequence data before first '>' header"));
        }
    }
    if records.is_empty() {
        return Err(IoError::Empty("FASTA records"));
    }
    records
        .into_iter()
        .map(|(name, body)| match Sequence::parse(&body) {
            Ok(seq) => Ok(Protein::new(name, seq)),
            Err(source) => Err(IoError::InvalidSequence { name, source }),
        })
        .collect()
}

/// Write proteins as FASTA with 60 residues per line.
pub fn write(proteins: &[Protein]) -> String {
    let mut out = String::new();
    for p in proteins {
        let _ = writeln!(out, ">{}", p.name);
        let s = p.sequence.to_string();
        for chunk in s.as_bytes().chunks(60) {
            out.push_str(std::str::from_utf8(chunk).unwrap_or_default());
            out.push('\n');
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    #[test]
    fn reads_multi_line_records() {
        let ps = read(">sp|P1|one\nMKTV\nRQER\n\n>two desc\nACDE\n").unwrap();
        assert_eq!(ps.len(), 2);
        assert_eq!(ps[0].name, "sp|P1|one");
        assert_eq!(ps[0].sequence.to_string(), "MKTVRQER");
    }

    #[test]
    fn rejects_body_without_header() {
        assert!(matches!(read("MKTV\n"), Err(IoError::Malformed { .. })));
    }

    #[test]
    fn names_the_bad_record() {
        let err = read(">ok\nMK\n>bad\nMK1Z\n").unwrap_err();
        assert!(matches!(err, IoError::InvalidSequence { ref name, .. } if name == "bad"), "{err}");
    }

    proptest! {
        #[test]
        fn write_read_round_trip(seqs in prop::collection::vec("[ACDEFGHIKLMNPQRSTVWY]{1,300}", 1..5)) {
            let proteins: Vec<_> = seqs.iter().enumerate()
                .map(|(i, s)| Protein::new(format!("p{i}"), Sequence::parse(s).unwrap()))
                .collect();
            let back = read(&write(&proteins)).unwrap();
            prop_assert_eq!(back, proteins);
        }
    }
}
