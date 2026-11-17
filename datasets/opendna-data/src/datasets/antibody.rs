//! `antibody`: heavy-chain variable regions from human and mouse repertoires.
//!
//! License review (2026-11-17):
//! * Observed Antibody Space (OAS): CC BY 4.0, stated by the maintainers on
//!   <https://opig.stats.ox.ac.uk/webapps/oas/> -- "the data contained within
//!   OAS is available under a CC-BY 4.0 license". Redistribution is permitted
//!   with attribution, so the derived dataset is CC BY 4.0.
//! * SAbDab: not used. It holds structures, and this is a sequence dataset.
//!   Its terms were not relied on and so were not reviewed.
//!
//! # What the label is, and what it is not
//!
//! Each row carries `is_human`: whether the sequence came out of a human
//! repertoire rather than a mouse one. That is a fact recorded by the study
//! that deposited it, not a prediction and not a measurement of anything
//! about the molecule.
//!
//! It is emphatically not an immunogenicity label. A sequence that resembles
//! a human repertoire is not thereby safe in humans, and the reverse is not
//! true either. What a head trained on this can answer is "does this look
//! like something a human B cell made", which is the question asked of a
//! humanised candidate -- and no more than that.
//!
//! # Three traps in the upstream metadata
//!
//! **The species field names the animal, not the immunoglobulin.** OAS
//! contains `HIS-Mouse` (a mouse carrying an engrafted human immune system)
//! and `Kymouse` (a transgenic mouse carrying human immunoglobulin loci).
//! Both are mice whose antibody V genes are human. Labelling them non-human
//! would teach a head that human V genes are mouse, on millions of sequences.
//! They are excluded from the labelled splits and kept as a separate
//! diagnostic set, where calling them human is the correct behaviour: that is
//! the humanisation question rather than a species-identification one.
//!
//! **One donor can appear in several studies.** Fifty individual identifiers
//! in OAS occur under more than one study. Some are the same person -- CAP256
//! is one HIV donor in Bhiman 2015, Doria-Rose 2015 and Johnson 2018 -- and
//! some are study-local placeholders, where `Donor-1` in two papers is two
//! people. Keying a donor by name alone merges those placeholders, which
//! costs a little data; keying by study would split a real donor across
//! train and test, which inflates every number. [`donor_key`] takes the first
//! trade, and says so.
//!
//! **A unit is two gzip members, not one.** OAS writes the metadata line as
//! its own gzip member and the CSV body as a second one. A single-member
//! decoder -- `flate2::read::GzDecoder`, the obvious choice -- stops after the
//! first, so it yields the metadata and no sequences at all, with no error.
//! Everything here reads units through [`open_unit`], which uses
//! `MultiGzDecoder`, and [`read_unit`] refuses a unit whose body is empty
//! rather than returning nothing and letting a build quietly produce a
//! dataset of zero rows.
//!
//! **Only mouse has enough independent studies to hold one out.** Human has
//! 69 studies and mouse 15, but rat, rabbit and bactrian camel have exactly
//! one study each, and rhesus two. A test score for those species would be
//! inseparable from one laboratory's protocol, so they are not trained on and
//! not part of the labelled splits either; they are kept as an
//! out-of-distribution set whose single-study origin the card states.

use std::collections::BTreeMap;
use std::io::{BufRead, BufReader, Read};

use anyhow::{bail, Context, Result};
use serde::Deserialize;

use crate::is_standard_protein;

pub const NAME: &str = "antibody";

/// Shortest and longest heavy-chain variable region kept, in residues.
///
/// A rearranged IGH V(D)J region runs about 110 to 130 residues. The band is
/// wide enough to keep unusual but real sequences and narrow enough to drop
/// the truncated reads that a sequencing run leaves behind; what falls outside
/// it is counted rather than discarded quietly.
pub const MIN_RESIDUES: usize = 90;
pub const MAX_RESIDUES: usize = 200;

/// What a unit's own metadata header says about it.
///
/// OAS puts this as a JSON object in the first line of every `csv.gz`, so the
/// organism and donor travel with the sequences rather than being recorded
/// separately here and going stale.
#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct UnitMetadata {
    #[serde(rename = "Species")]
    pub species: String,
    #[serde(rename = "Subject")]
    pub subject: String,
    #[serde(rename = "Chain")]
    pub chain: String,
    #[serde(rename = "Author")]
    pub author: String,
    /// Reported, never depended on. See [`loose_string`] for why these three
    /// are not plain strings.
    #[serde(rename = "Isotype", default, deserialize_with = "loose_string")]
    pub isotype: String,
    #[serde(rename = "Disease", default, deserialize_with = "loose_string")]
    pub disease: String,
    #[serde(rename = "BType", default, deserialize_with = "loose_string")]
    pub b_type: String,
}

/// Read a metadata field that upstream does not type consistently.
///
/// OAS writes `Isotype` as `"Bulk"` in Greiff 2017 and as `["Bulk"]` in Li
/// 2017, and `Age` as `"no"` in one and `5` in another. The three fields this
/// is used on are reported in the card and never decide anything, so the
/// honest handling is to render whatever is there and carry on -- failing a
/// whole build over the shape of a field nothing depends on would be a
/// strictness that costs data and buys nothing.
///
/// The fields that do decide something -- `Species`, `Subject`, `Chain` --
/// stay plain strings, so a change in any of those is still an error.
fn loose_string<'de, D: serde::Deserializer<'de>>(d: D) -> std::result::Result<String, D::Error> {
    use serde::Deserialize as _;
    Ok(match serde_json::Value::deserialize(d)? {
        serde_json::Value::Null => String::new(),
        serde_json::Value::String(s) => s,
        serde_json::Value::Array(items) => items
            .iter()
            .map(|i| i.as_str().map_or_else(|| i.to_string(), str::to_owned))
            .collect::<Vec<_>>()
            .join(";"),
        other => other.to_string(),
    })
}

/// Which side of the question a unit is on.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Cohort {
    /// Human repertoire. Labelled, trained on.
    Human,
    /// Mouse repertoire. Labelled, trained on.
    Mouse,
    /// A mouse whose immunoglobulin loci are human: `HIS-Mouse`, `Kymouse`.
    /// Never labelled, never trained on; the humanisation diagnostic.
    HumanLociInMouse,
    /// Another species, held out entirely. One study each for most of them.
    OutOfDistribution,
}

impl Cohort {
    /// The split file a cohort's rows are written to.
    pub fn table(self) -> &'static str {
        match self {
            Self::Human | Self::Mouse => "labelled",
            Self::HumanLociInMouse => "diagnostic",
            Self::OutOfDistribution => "out_of_distribution",
        }
    }

    /// The label, where there is one.
    ///
    /// `None` for the two held-out cohorts, rather than a default. A
    /// transgenic mouse recorded as `is_human = false` is the exact mistake
    /// this enum exists to prevent, and a column that cannot hold "no answer"
    /// invites it.
    pub fn is_human(self) -> Option<bool> {
        match self {
            Self::Human => Some(true),
            Self::Mouse => Some(false),
            Self::HumanLociInMouse | Self::OutOfDistribution => None,
        }
    }
}

/// Read a cohort off the `Species` string.
///
/// Matched exactly against the values OAS actually uses, listed here in full,
/// so a new species appearing upstream is an error rather than a silent
/// assignment to whichever arm the match arms happen to end with.
///
/// # Errors
/// If the species is not one of the values this has been checked against.
pub fn cohort_of(species: &str) -> Result<Cohort> {
    Ok(match species {
        "human" => Cohort::Human,
        // Strains, all of them ordinary mice.
        "mouse" | "mouse_C57BL/6" | "mouse_BALB/c" | "mouse_RAG2-GFP/129Sve" | "mouse_Swiss-Webster" => {
            Cohort::Mouse
        }
        // Mice with human immunoglobulin. See the module documentation.
        "HIS-Mouse" | "Kymouse" => Cohort::HumanLociInMouse,
        "rat" | "rabbit" | "rhesus" | "bactrian_camel" => Cohort::OutOfDistribution,
        other => bail!(
            "unknown OAS species {other:?}. Add it to `cohort_of` deliberately: a mouse \
             carrying human immunoglobulin loci must not be labelled non-human, and a species \
             with one study behind it must not be trained on."
        ),
    })
}

/// The identifier a split may never be drawn through.
///
/// A named subject is global, because the same donor is deposited under the
/// same name by different studies. An absent name is a missing field rather
/// than a person, so those units fall back to the study, which keeps the
/// boundary safe without inventing an identity.
pub fn donor_key(metadata: &UnitMetadata, study: &str) -> String {
    let subject = metadata.subject.trim();
    if matches!(subject, "" | "no" | "No" | "NA" | "n/a" | "none" | "None" | "unknown") {
        format!("study:{study}")
    } else {
        format!("person:{subject}")
    }
}

/// One kept sequence.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AntibodySequence {
    /// The amino-acid V(D)J region, as OAS aligned it.
    pub sequence: String,
    /// IMGT V gene call, as given. Kept for reporting, never as a feature.
    pub v_call: String,
    /// IMGT J gene call, as given.
    pub j_call: String,
    /// CDR3, amino acids.
    pub cdr3: String,
    /// How many identical reads OAS collapsed into this row.
    pub redundancy: u32,
}

/// Why rows were dropped, so the card can account for every one.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ReadStats {
    pub rows: u64,
    pub not_productive: u64,
    pub stop_codon: u64,
    pub out_of_frame: u64,
    pub wrong_locus: u64,
    pub empty_sequence: u64,
    pub nonstandard_residue: u64,
    pub out_of_length_band: u64,
    pub duplicate_within_unit: u64,
    pub kept: u64,
}

fn column(header: &csv::StringRecord, name: &str) -> Result<usize> {
    header
        .iter()
        .position(|field| field.trim() == name)
        .with_context(|| format!("OAS unit has no column {name:?}"))
}

/// Read one OAS `csv.gz` data unit: its metadata header and its usable rows.
///
/// The first line is a single CSV field holding a JSON object; the AIRR
/// header is the second line. Rows are filtered on the flags OAS already
/// computed -- productive, in frame, no stop codon -- rather than on anything
/// re-derived here, and every rejection is counted.
///
/// # Errors
/// If the stream is not an OAS unit: no metadata line, unparsable JSON, or a
/// missing AIRR column.
pub fn read_unit(reader: impl Read) -> Result<(UnitMetadata, Vec<AntibodySequence>, ReadStats)> {
    let mut buffered = BufReader::new(reader);
    let mut first = String::new();
    if buffered.read_line(&mut first)? == 0 {
        bail!("empty OAS unit: expected a metadata line");
    }
    let field = csv::ReaderBuilder::new()
        .has_headers(false)
        .from_reader(first.as_bytes())
        .records()
        .next()
        .transpose()?
        .and_then(|record| record.get(0).map(str::to_owned))
        .context("OAS metadata line is not a CSV record")?;
    let metadata: UnitMetadata =
        serde_json::from_str(&field).context("OAS metadata line is not the expected JSON")?;

    let mut rdr = csv::ReaderBuilder::new().flexible(true).from_reader(buffered);
    let header = rdr.headers()?.clone();
    let (c_seq, c_prod, c_stop, c_frame, c_locus) = (
        column(&header, "sequence_alignment_aa")?,
        column(&header, "productive")?,
        column(&header, "stop_codon")?,
        column(&header, "vj_in_frame")?,
        column(&header, "locus")?,
    );
    let (c_v, c_j, c_cdr3, c_red) = (
        column(&header, "v_call")?,
        column(&header, "j_call")?,
        column(&header, "cdr3_aa")?,
        column(&header, "Redundancy")?,
    );

    let mut stats = ReadStats::default();
    let mut seen = std::collections::HashSet::new();
    let mut out = Vec::new();
    for record in rdr.records() {
        let record = record?;
        stats.rows += 1;
        let get = |i: usize| record.get(i).unwrap_or("").trim();

        // OAS writes T/F. Anything else is treated as not asserted, which is
        // the conservative reading for a flag that gates inclusion.
        if get(c_prod) != "T" {
            stats.not_productive += 1;
            continue;
        }
        if get(c_stop) != "F" {
            stats.stop_codon += 1;
            continue;
        }
        if get(c_frame) != "T" {
            stats.out_of_frame += 1;
            continue;
        }
        if get(c_locus) != "H" {
            stats.wrong_locus += 1;
            continue;
        }
        let sequence = get(c_seq).to_ascii_uppercase();
        if sequence.is_empty() {
            stats.empty_sequence += 1;
            continue;
        }
        // Rejects alignment gaps and ambiguity codes together, which is what
        // we want: an embedder should not be fed a dot.
        if !is_standard_protein(&sequence) {
            stats.nonstandard_residue += 1;
            continue;
        }
        if !(MIN_RESIDUES..=MAX_RESIDUES).contains(&sequence.len()) {
            stats.out_of_length_band += 1;
            continue;
        }
        if !seen.insert(sequence.clone()) {
            stats.duplicate_within_unit += 1;
            continue;
        }
        stats.kept += 1;
        out.push(AntibodySequence {
            sequence,
            v_call: get(c_v).to_owned(),
            j_call: get(c_j).to_owned(),
            cdr3: get(c_cdr3).to_owned(),
            redundancy: get(c_red).parse().unwrap_or(1),
        });
    }
    // A unit that parsed its metadata and then found no rows at all is the
    // signature of reading only the first gzip member. It is never a real
    // unit: OAS does not publish empty ones.
    if stats.rows == 0 {
        bail!(
            "OAS unit for {} / {} has metadata but no rows. If it was opened with a              single-member gzip decoder, that is the cause: a unit is two concatenated              members and the body is the second.",
            metadata.species,
            metadata.subject
        );
    }
    Ok((metadata, out, stats))
}

/// Open a cached OAS unit for reading.
///
/// The only way units are opened, so the two-member gzip layout is handled in
/// exactly one place.
///
/// # Errors
/// If the file cannot be opened.
pub fn open_unit(path: &std::path::Path) -> Result<impl Read> {
    let file = std::fs::File::open(path).with_context(|| format!("opening {}", path.display()))?;
    Ok(flate2::read::MultiGzDecoder::new(std::io::BufReader::new(file)))
}

/// Add one unit's counts into a running total.
pub fn accumulate(total: &mut ReadStats, one: &ReadStats) {
    total.rows += one.rows;
    total.not_productive += one.not_productive;
    total.stop_codon += one.stop_codon;
    total.out_of_frame += one.out_of_frame;
    total.wrong_locus += one.wrong_locus;
    total.empty_sequence += one.empty_sequence;
    total.nonstandard_residue += one.nonstandard_residue;
    total.out_of_length_band += one.out_of_length_band;
    total.duplicate_within_unit += one.duplicate_within_unit;
    total.kept += one.kept;
}

/// Every V gene seen in a cohort, with how often, for the card.
///
/// Reported because it is the first thing to check when a species classifier
/// looks too good: if one cohort's sequences are separable by their V call
/// alone, the head has learnt the germline catalogue rather than anything
/// about the molecule, and a reader deserves to see the overlap.
pub fn v_gene_counts<'a>(sequences: impl IntoIterator<Item = &'a AntibodySequence>) -> BTreeMap<String, u64> {
    let mut counts = BTreeMap::new();
    for s in sequences {
        // IGHV1-52*01 -> IGHV1-52: the allele is finer than anything here
        // needs and splits the counts across near-identical genes.
        let gene = s.v_call.split('*').next().unwrap_or(&s.v_call);
        if !gene.is_empty() {
            *counts.entry(gene.to_owned()).or_default() += 1;
        }
    }
    counts
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A minimal OAS unit: the JSON metadata line, the AIRR header, and rows.
    fn unit(rows: &[&str]) -> String {
        let metadata = r#"{"Run": "ERR1", "Author": "Greiff et al., 2017", "Species": "mouse_C57BL/6", "Subject": "HP-HEL-Mouse-1", "Chain": "Heavy", "Isotype": "Bulk", "Disease": "None", "BType": "Plasma-B-Cells"}"#;
        let mut text = String::new();
        // The metadata line is a single CSV field, so its quotes are doubled.
        text.push('"');
        text.push_str(&metadata.replace('"', "\"\""));
        text.push_str("\"\n");
        text.push_str("sequence_alignment_aa,productive,stop_codon,vj_in_frame,locus,v_call,j_call,cdr3_aa,Redundancy\n");
        for row in rows {
            text.push_str(row);
            text.push('\n');
        }
        text
    }

    /// 117 residues, the length of the real first row in the fixture unit.
    fn good_sequence() -> String {
        "QVQLQQPGAELVRPGSSVKLSCKASGYTFTSYWMHWVKQRPIQGLEWIGNIDPSDSETHYNQKFKDKATLTVDKSSSTAYMQLSSLTSEDSAVYSVALLRWYPACYAYWGRGNLVTVS".to_string()
    }

    fn row(sequence: &str, productive: &str, stop: &str, frame: &str, locus: &str) -> String {
        format!("{sequence},{productive},{stop},{frame},{locus},IGHV1-52*01,IGHJ3*01,ALLRWYPACYAY,3")
    }

    #[test]
    fn a_unit_carries_its_own_organism_and_donor() {
        let text = unit(&[&row(&good_sequence(), "T", "F", "T", "H")]);
        let (metadata, sequences, stats) = read_unit(text.as_bytes()).unwrap();
        assert_eq!(metadata.species, "mouse_C57BL/6");
        assert_eq!(metadata.subject, "HP-HEL-Mouse-1");
        assert_eq!(metadata.chain, "Heavy");
        assert_eq!(sequences.len(), 1);
        assert_eq!(sequences[0].redundancy, 3);
        assert_eq!(sequences[0].cdr3, "ALLRWYPACYAY");
        assert_eq!(stats.kept, 1);
        assert_eq!(stats.rows, 1);
    }

    /// Every rejection is counted, because a card that cannot account for the
    /// difference between rows read and rows kept is a card nobody can check.
    #[test]
    fn every_kind_of_rejection_is_counted() {
        let long = "A".repeat(MAX_RESIDUES + 1);
        let short = "A".repeat(MIN_RESIDUES - 1);
        let text = unit(&[
            &row(&good_sequence(), "T", "F", "T", "H"),
            &row(&good_sequence(), "F", "F", "T", "H"),
            &row(&good_sequence(), "T", "T", "T", "H"),
            &row(&good_sequence(), "T", "F", "F", "H"),
            &row(&good_sequence(), "T", "F", "T", "K"),
            &row("", "T", "F", "T", "H"),
            &row("QVQLXQPGAELVRPGSSVKLSCKASGYTFTSYWMHWVKQRPIQGLEWIGNIDPSDSETHYNQKFKDKATLTVDKSSSTAYMQLSSLTSEDSAVYSVALLRWYPACYAYWGRGNLVTVS", "T", "F", "T", "H"),
            &row(&long, "T", "F", "T", "H"),
            &row(&short, "T", "F", "T", "H"),
        ]);
        let (_, sequences, stats) = read_unit(text.as_bytes()).unwrap();
        assert_eq!(stats.rows, 9);
        assert_eq!(stats.kept, 1);
        assert_eq!(sequences.len(), 1);
        assert_eq!(stats.not_productive, 1);
        assert_eq!(stats.stop_codon, 1);
        assert_eq!(stats.out_of_frame, 1);
        assert_eq!(stats.wrong_locus, 1);
        assert_eq!(stats.empty_sequence, 1);
        assert_eq!(stats.nonstandard_residue, 1, "an X is not a residue to embed");
        assert_eq!(stats.out_of_length_band, 2);
        // Nothing may vanish between the two totals.
        let accounted = stats.not_productive
            + stats.stop_codon
            + stats.out_of_frame
            + stats.wrong_locus
            + stats.empty_sequence
            + stats.nonstandard_residue
            + stats.out_of_length_band
            + stats.duplicate_within_unit
            + stats.kept;
        assert_eq!(accounted, stats.rows);
    }

    #[test]
    fn an_identical_sequence_is_kept_once() {
        let text =
            unit(&[&row(&good_sequence(), "T", "F", "T", "H"), &row(&good_sequence(), "T", "F", "T", "H")]);
        let (_, sequences, stats) = read_unit(text.as_bytes()).unwrap();
        assert_eq!(sequences.len(), 1);
        assert_eq!(stats.duplicate_within_unit, 1);
    }

    /// The trap this dataset exists to avoid. A transgenic mouse's V genes are
    /// human, so it must not be labelled non-human -- and it must not be
    /// labelled human either, since the animal is a mouse. It gets no label.
    #[test]
    fn a_mouse_with_human_loci_is_never_given_a_species_label() {
        for species in ["HIS-Mouse", "Kymouse"] {
            let cohort = cohort_of(species).unwrap();
            assert_eq!(cohort, Cohort::HumanLociInMouse, "{species}");
            assert_eq!(cohort.is_human(), None, "{species} must carry no label");
            assert_eq!(cohort.table(), "diagnostic");
        }
    }

    #[test]
    fn ordinary_mice_and_humans_are_labelled_and_trained_on() {
        assert_eq!(cohort_of("human").unwrap().is_human(), Some(true));
        for strain in ["mouse", "mouse_C57BL/6", "mouse_BALB/c", "mouse_Swiss-Webster"] {
            assert_eq!(cohort_of(strain).unwrap().is_human(), Some(false), "{strain}");
            assert_eq!(cohort_of(strain).unwrap().table(), "labelled");
        }
    }

    /// Rat, rabbit and camel have one study each. They are kept, unlabelled,
    /// so a head can be reported against them without being trained on one
    /// laboratory's protocol.
    #[test]
    fn single_study_species_are_held_out_rather_than_trained_on() {
        for species in ["rat", "rabbit", "rhesus", "bactrian_camel"] {
            let cohort = cohort_of(species).unwrap();
            assert_eq!(cohort, Cohort::OutOfDistribution, "{species}");
            assert_eq!(cohort.is_human(), None);
            assert_eq!(cohort.table(), "out_of_distribution");
        }
    }

    /// A species nobody has looked at must stop the build. The alternative is
    /// a catch-all arm that quietly decides for us.
    #[test]
    fn an_unrecognised_species_is_an_error_not_a_guess() {
        let error = cohort_of("llama").unwrap_err().to_string();
        assert!(error.contains("llama"), "{error}");
        assert!(error.contains("must not be labelled non-human"), "{error}");
    }

    /// CAP256 is one HIV donor deposited by three studies. Keying by name
    /// keeps the three on the same side of every split.
    #[test]
    fn one_donor_in_several_studies_gets_one_key() {
        let metadata = |subject: &str| UnitMetadata {
            species: "human".into(),
            subject: subject.into(),
            chain: "Heavy".into(),
            author: "x".into(),
            isotype: String::new(),
            disease: String::new(),
            b_type: String::new(),
        };
        assert_eq!(
            donor_key(&metadata("CAP256"), "Bhiman_2015"),
            donor_key(&metadata("CAP256"), "Doria-Rose_2015")
        );
    }

    /// An absent subject is a missing field, not a person. Those units fall
    /// back to the study, so the boundary is still safe.
    #[test]
    fn a_missing_subject_falls_back_to_the_study() {
        let metadata = UnitMetadata {
            species: "rat".into(),
            subject: "no".into(),
            chain: "Heavy".into(),
            author: "x".into(),
            isotype: String::new(),
            disease: String::new(),
            b_type: String::new(),
        };
        assert_eq!(donor_key(&metadata, "VanDuijn_2017"), "study:VanDuijn_2017");
        // And two studies with no subject stay apart.
        assert_ne!(donor_key(&metadata, "A"), donor_key(&metadata, "B"));
    }

    #[test]
    fn v_genes_are_counted_by_gene_not_allele() {
        let make = |v: &str| AntibodySequence {
            sequence: good_sequence(),
            v_call: v.into(),
            j_call: "IGHJ3*01".into(),
            cdr3: "AAA".into(),
            redundancy: 1,
        };
        let sequences = [make("IGHV1-52*01"), make("IGHV1-52*02"), make("IGHV3-23*01")];
        let counts = v_gene_counts(&sequences);
        assert_eq!(counts["IGHV1-52"], 2);
        assert_eq!(counts["IGHV3-23"], 1);
        assert_eq!(counts.len(), 2);
    }

    /// The fixtures above state what an OAS unit looks like. This checks that
    /// against real ones, which is the only way to find out that the shape
    /// was written down wrong -- a fixture agrees with whatever built it.
    ///
    /// Skipped unless `OPENDNA_OAS_CACHE` points at a directory of downloaded
    /// `.csv.gz` units, because the units are not in the repository and a
    /// test that fails on every machine without them gets switched off.
    #[test]
    fn real_units_parse_and_every_species_is_recognised() {
        let Some(dir) = std::env::var_os("OPENDNA_OAS_CACHE") else {
            println!("OPENDNA_OAS_CACHE unset; skipping the real-unit check");
            return;
        };
        let mut checked = 0_usize;
        let mut cohorts: BTreeMap<String, usize> = BTreeMap::new();
        for entry in std::fs::read_dir(&dir).expect("OPENDNA_OAS_CACHE is not readable").flatten() {
            let path = entry.path();
            if path.extension().is_none_or(|e| e != "gz") {
                continue;
            }
            let (metadata, sequences, stats) = read_unit(open_unit(&path).expect("opening a cached unit"))
                .unwrap_or_else(|e| panic!("{} is not readable as an OAS unit: {e:#}", path.display()));
            let cohort = cohort_of(&metadata.species).unwrap_or_else(|e| panic!("{}: {e:#}", path.display()));
            *cohorts.entry(format!("{cohort:?}")).or_default() += 1;

            assert_eq!(metadata.chain, "Heavy", "{} is not a heavy chain", path.display());
            assert!(stats.rows > 0, "{} has no rows", path.display());
            assert_eq!(
                stats.kept as usize,
                sequences.len(),
                "{}: the kept count and the sequences disagree",
                path.display()
            );
            for s in &sequences {
                assert!(
                    (MIN_RESIDUES..=MAX_RESIDUES).contains(&s.sequence.len()),
                    "{}: a kept sequence is {} residues",
                    path.display(),
                    s.sequence.len()
                );
                assert!(is_standard_protein(&s.sequence), "{}: a kept sequence is not", path.display());
            }
            checked += 1;
        }
        assert!(checked > 0, "OPENDNA_OAS_CACHE held no .csv.gz units");
        println!("{checked} real units parsed; cohorts: {cohorts:?}");
    }

    /// Upstream types these fields two ways. Both are real: the strings come
    /// from Greiff 2017 and the list from Li 2017, in the same release.
    #[test]
    fn a_metadata_field_typed_two_ways_upstream_is_read_either_way() {
        let read = |isotype: &str| -> UnitMetadata {
            let json = format!(
                r#"{{"Species": "human", "Subject": "S1", "Chain": "Heavy", "Author": "a", "Isotype": {isotype}}}"#
            );
            serde_json::from_str(&json).unwrap_or_else(|e| panic!("{isotype}: {e}"))
        };
        assert_eq!(read(r#""Bulk""#).isotype, "Bulk");
        assert_eq!(read(r#"["Bulk"]"#).isotype, "Bulk");
        assert_eq!(read(r#"["IGHG","IGHM"]"#).isotype, "IGHG;IGHM");
        assert_eq!(read("null").isotype, "");
        assert_eq!(read("5").isotype, "5");
        // An absent field is fine too.
        let bare: UnitMetadata =
            serde_json::from_str(r#"{"Species": "human", "Subject": "S1", "Chain": "Heavy", "Author": "a"}"#)
                .unwrap();
        assert_eq!(bare.isotype, "");
    }

    /// The fields that decide something stay strict: a `Species` that is not
    /// a string is a change upstream that must stop the build.
    #[test]
    fn a_load_bearing_field_is_still_strict() {
        let json = r#"{"Species": ["human"], "Subject": "S1", "Chain": "Heavy", "Author": "a"}"#;
        assert!(serde_json::from_str::<UnitMetadata>(json).is_err());
    }

    #[test]
    fn a_stream_that_is_not_an_oas_unit_is_rejected() {
        assert!(read_unit(b"".as_slice()).unwrap_err().to_string().contains("empty OAS unit"));
        let error = read_unit(b"not json\nheader\n".as_slice()).unwrap_err().to_string();
        assert!(error.contains("expected JSON"), "{error}");
    }
}
