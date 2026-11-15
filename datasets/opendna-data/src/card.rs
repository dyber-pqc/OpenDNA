//! Hugging Face dataset card rendering.
//!
//! Cards are generated from the same data the pipeline writes: split sizes
//! and the schema come from the actual tables, and source checksums come from
//! the lockfile. Prose sections are supplied by each dataset module.

use std::fmt::Write as _;

use crate::cache::Lockfile;
use crate::parquet_out::Table;
use crate::sources::{ExcludedSource, Source};
use crate::split::{Split, SplitSummary};

/// License declared in the card's YAML header.
#[derive(Debug, Clone)]
pub enum CardLicense {
    /// A license id from the Hugging Face list, e.g. `cc-by-4.0`.
    Known(&'static str),
    /// A license not on the Hugging Face list (`license: other`).
    Other { name: &'static str, link: &'static str },
}

pub struct CardInput<'a> {
    pub pretty_name: &'static str,
    pub license: CardLicense,
    /// One paragraph explaining what the license of the derived dataset is and why.
    pub license_note: &'static str,
    pub tags: &'static [&'static str],
    pub summary: String,
    pub sources: &'a [Source],
    pub excluded: Vec<&'static ExcludedSource>,
    pub construction: String,
    pub schema: &'a Table,
    /// What a row is, plural ("mutations", "proteins", "domains").
    pub row_unit: &'static str,
    /// What a split group is, plural ("clusters", "components").
    pub group_unit: &'static str,
    pub splits: &'a SplitSummary,
    pub statistics: Vec<(String, String)>,
    pub citations: &'static str,
    pub limitations: &'static [&'static str],
    pub lock: &'a Lockfile,
}

pub fn size_category(n: u64) -> &'static str {
    match n {
        0..1_000 => "n<1K",
        1_000..10_000 => "1K<n<10K",
        10_000..100_000 => "10K<n<100K",
        100_000..1_000_000 => "100K<n<1M",
        1_000_000..10_000_000 => "1M<n<10M",
        _ => "10M<n<100M",
    }
}

pub fn render(c: &CardInput<'_>) -> String {
    let mut s = String::new();
    // YAML front matter.
    s.push_str("---\n");
    match &c.license {
        CardLicense::Known(id) => {
            let _ = writeln!(s, "license: {id}");
        }
        CardLicense::Other { name, link } => {
            let _ = writeln!(s, "license: other\nlicense_name: {name}\nlicense_link: {link}");
        }
    }
    let _ = writeln!(s, "pretty_name: {}", c.pretty_name);
    s.push_str("tags:\n");
    for t in c.tags {
        let _ = writeln!(s, "- {t}");
    }
    let _ = writeln!(s, "size_categories:\n- {}", size_category(c.splits.total_rows()));
    s.push_str("configs:\n- config_name: default\n  data_files:\n");
    for sp in Split::ALL {
        if c.splits.get(sp).rows > 0 {
            let _ = writeln!(s, "  - split: {sp}\n    path: data/{sp}.parquet");
        }
    }
    s.push_str("---\n\n");

    let _ = writeln!(s, "# {}\n\n{}\n", c.pretty_name, c.summary.trim());

    s.push_str("## Sources and licenses\n\n");
    s.push_str("| Source | License | File | SHA-256 |\n|---|---|---|---|\n");
    for src in c.sources {
        let sha = c.lock.sources.get(src.id).map_or("(not locked)".to_owned(), |e| format!("`{}`", e.sha256));
        let _ = writeln!(
            s,
            "| {} | [{}]({}) | [{}]({}) | {} |",
            src.description,
            src.license.name(),
            src.license.url(),
            src.file_name,
            src.url,
            sha
        );
    }
    let _ = writeln!(s, "\n{}\n", c.license_note.trim());
    if !c.excluded.is_empty() {
        s.push_str("### Sources considered and excluded\n\n");
        for e in &c.excluded {
            let _ = writeln!(s, "- **{}**: {}", e.name, e.reason);
        }
        s.push('\n');
    }

    let _ = writeln!(s, "## Construction\n\n{}\n", c.construction.trim());

    s.push_str("## Schema\n\n| Column | Type | Description |\n|---|---|---|\n");
    for col in &c.schema.columns {
        let _ = writeln!(s, "| `{}` | {} | {} |", col.name, col.data.type_name(), col.description);
    }

    let _ = writeln!(s, "\n## Splits\n\n| Split | {} | {} |\n|---|---:|---:|", c.row_unit, c.group_unit);
    for sp in Split::ALL {
        let k = c.splits.get(sp);
        let _ = writeln!(s, "| {sp} | {} | {} |", k.rows, k.groups);
    }
    let _ = writeln!(s, "| total | {} | |\n", c.splits.total_rows());

    if !c.statistics.is_empty() {
        s.push_str("### Cleaning statistics\n\n| Step | Count |\n|---|---:|\n");
        for (k, v) in &c.statistics {
            let _ = writeln!(s, "| {k} | {v} |");
        }
        s.push('\n');
    }

    s.push_str("## Known limitations\n\n");
    for l in c.limitations {
        let _ = writeln!(s, "- {l}");
    }
    let _ = writeln!(
        s,
        "\n## Citation\n\nIf you use this dataset, cite the upstream sources:\n\n```bibtex\n{}\n```\n",
        c.citations.trim()
    );
    s.push_str(
        "## Reproduction\n\nBuilt with `opendna-data` from the OpenDNA repository \
         (`datasets/`). The exact upstream files are pinned by SHA-256 in \
         `datasets/sources.lock`; `manifest.json` next to this card records the \
         pipeline parameters and the checksum of every Parquet file.\n",
    );
    s
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::parquet_out::ColumnData;
    use crate::split::SplitCounts;

    #[test]
    fn renders_front_matter_and_sections() {
        let mut t = Table::new();
        t.push("id", "identifier", ColumnData::Utf8(vec![]));
        let splits = SplitSummary {
            train: SplitCounts { rows: 8, groups: 4 },
            validation: SplitCounts { rows: 1, groups: 1 },
            test: SplitCounts::default(),
        };
        let lock = Lockfile::default();
        let card = render(&CardInput {
            pretty_name: "Example",
            license: CardLicense::Other { name: "cc-by-sa-2.1-jp", link: "https://example.invalid" },
            license_note: "note",
            tags: &["biology"],
            summary: "Summary.".into(),
            sources: &[],
            excluded: vec![],
            construction: "Steps.".into(),
            schema: &t,
            row_unit: "rows",
            group_unit: "clusters",
            splits: &splits,
            statistics: vec![("dropped".into(), "3".into())],
            citations: "@misc{x}",
            limitations: &["small"],
            lock: &lock,
        });
        assert!(card.starts_with("---\nlicense: other\nlicense_name: cc-by-sa-2.1-jp\n"));
        assert!(card.contains("- split: train\n    path: data/train.parquet"));
        // Empty splits are not declared, so the HF loader does not look for missing files.
        assert!(!card.contains("path: data/test.parquet"));
        assert!(card.contains("| `id` | string | identifier |"));
        assert!(card.contains("| train | 8 | 4 |"));
        assert!(card.contains("- n<1K"));
    }

    #[test]
    fn size_buckets() {
        assert_eq!(size_category(999), "n<1K");
        assert_eq!(size_category(1_000), "1K<n<10K");
        assert_eq!(size_category(400_000), "100K<n<1M");
    }
}
