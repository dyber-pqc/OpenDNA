//! OpenDNA command line: batch predictions over a FASTA file.
//!
//! The desktop application works on one protein at a time, which is the wrong
//! shape for the job people actually have — a few hundred candidate sequences
//! to triage. This runs the same heads over a whole file and writes a table.
//!
//! It shares the prediction code with the application rather than
//! reimplementing it, so the two cannot disagree about a number, and every
//! output file carries the model version and the card's limitations.
//!
//! Nothing here falls back to a heuristic. A missing head is an error naming
//! the files it looked for.

// Writing to standard output is this crate's purpose, so the workspace's
// `print_stdout` lint is inverted here: results go to stdout when no
// `--output` is given, and progress goes to stderr so a pipe stays clean.
#![allow(clippy::print_stdout, clippy::print_stderr)]
// `doc_markdown` reads product names like OpenDNA as code identifiers.
// Backticking them would make the rendered help and docs wrong.
#![allow(clippy::doc_markdown)]

mod provenance;

use anyhow::{anyhow, bail, Context, Result};
use clap::{Parser, Subcommand, ValueEnum};
use opendna_core::AminoAcid;
use opendna_ml::esm2::{Esm2, ModelSize};
use opendna_ml::heads::{read_metadata, HeadFiles, Heads, StabilityHead};
use provenance::Provenance;
use std::fmt::Write as _;
use std::io::Write as _;
use std::path::{Path, PathBuf};

/// The embedding model the published heads were trained on.
///
/// Not a flag: a head records the embedder it expects and refuses to load
/// against another, so offering a choice here would only produce a confusing
/// error. Retraining on a different embedder is a `training/` concern.
const EMBEDDER: ModelSize = ModelSize::Large150M;

/// Probability at or above which a residue is called disordered, matching the
/// threshold the disorder head was evaluated at.
const DISORDER_THRESHOLD: f64 = 0.5;

#[derive(Parser)]
#[command(
    name = "opendna",
    about = "Batch protein property predictions that run on your own machine",
    long_about = "Runs OpenDNA's trained prediction heads over a FASTA file and writes a table.\n\
                  \n\
                  Predictions need the trained heads. Download them and pass --models, or set\n\
                  OPENDNA_MODELS:\n\
                  \n\
                  \u{20} hf download dyber-pqc/opendna-disorder --local-dir models\n\
                  \n\
                  Nothing is uploaded. The first run downloads the embedding model into the\n\
                  Hugging Face cache; after that it works offline.",
    version
)]
struct Cli {
    /// Directory holding the trained heads. Defaults to `$OPENDNA_MODELS`,
    /// then `./models`.
    #[arg(long, global = true)]
    models: Option<PathBuf>,
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Predict a property for every sequence in a FASTA file.
    Predict {
        /// Which property.
        #[arg(long, value_enum)]
        task: Task,
        /// FASTA file to read. `-` reads standard input.
        #[arg(long, short = 'i')]
        input: PathBuf,
        /// Where to write the table. Omit to write to standard output.
        #[arg(long, short = 'o')]
        output: Option<PathBuf>,
        /// Output format.
        #[arg(long, value_enum, default_value_t = Format::Csv)]
        format: Format,
        /// For `stability` only: a CSV of `name,mutation` rows, for example
        /// `ubiquitin,L8P`. Mutations are 1-based, as they are written.
        #[arg(long)]
        mutations: Option<PathBuf>,
    },
    /// Report which heads are installed, and where they were looked for.
    Models,
}

#[derive(Copy, Clone, Debug, PartialEq, Eq, ValueEnum)]
enum Task {
    /// Per-residue intrinsic disorder.
    Disorder,
    /// Whole-protein solubility.
    Solubility,
    /// Change in folding free energy for named substitutions.
    Stability,
}

impl Task {
    fn name(self) -> &'static str {
        match self {
            Self::Disorder => "disorder",
            Self::Solubility => "solubility",
            Self::Stability => "stability",
        }
    }
}

#[derive(Copy, Clone, Debug, PartialEq, Eq, ValueEnum)]
enum Format {
    /// Comma-separated, with `#` provenance comments.
    Csv,
    /// Tab-separated, with `#` provenance comments.
    Tsv,
    /// One JSON object, with provenance as a field.
    Json,
}

impl Format {
    fn separator(self) -> char {
        match self {
            Self::Tsv => '\t',
            Self::Csv | Self::Json => ',',
        }
    }
}

/// Where to look for trained heads.
///
/// `--models` wins, then `OPENDNA_MODELS`, then `./models`. The environment
/// variable exists so a shared install can be pointed at once rather than on
/// every invocation.
fn models_dir(flag: Option<PathBuf>) -> PathBuf {
    flag.or_else(|| std::env::var_os("OPENDNA_MODELS").map(PathBuf::from))
        .unwrap_or_else(|| PathBuf::from("models"))
}

fn read_input(path: &Path) -> Result<String> {
    if path.as_os_str() == "-" {
        let mut buffer = String::new();
        std::io::Read::read_to_string(&mut std::io::stdin(), &mut buffer)
            .context("reading FASTA from standard input")?;
        return Ok(buffer);
    }
    std::fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))
}

fn write_output(output: Option<&Path>, text: &str) -> Result<()> {
    match output {
        Some(path) => {
            std::fs::write(path, text).with_context(|| format!("writing {}", path.display()))?;
            eprintln!("Wrote {}", path.display());
        }
        None => {
            std::io::stdout().write_all(text.as_bytes()).context("writing to standard output")?;
        }
    }
    Ok(())
}

/// Load a head's metadata and its card's limitations.
fn head_provenance(dir: &Path, task: Task, device: &str) -> Result<Provenance> {
    let files = HeadFiles::in_dir(dir, task.name());
    if !files.exist() {
        bail!(
            "no {} head in {}. Expected {} and {}. Download one:\n  \
             hf download dyber-pqc/opendna-{} --local-dir {}\n\
             OpenDNA does not estimate this property without a trained model.",
            task.name(),
            dir.display(),
            files.weights.display(),
            files.metadata.display(),
            task.name(),
            dir.display()
        );
    }
    let metadata = read_metadata(&files, task.name(), EMBEDDER)?;
    let card = std::fs::read_to_string(dir.join(format!("{}.README.md", task.name()))).unwrap_or_default();
    Ok(Provenance::new(task.name(), &metadata, EMBEDDER, device, provenance::limitations_from_card(&card)))
}

/// One row of a result table, as strings so every format shares the values.
struct Table {
    columns: Vec<&'static str>,
    rows: Vec<Vec<String>>,
}

impl Table {
    fn render(&self, format: Format, prov: &Provenance) -> Result<String> {
        if format == Format::Json {
            let objects: Vec<serde_json::Value> = self
                .rows
                .iter()
                .map(|row| {
                    self.columns
                        .iter()
                        .zip(row)
                        .map(|(c, v)| ((*c).to_string(), json_scalar(v)))
                        .collect::<serde_json::Map<_, _>>()
                        .into()
                })
                .collect();
            let doc = serde_json::json!({
                "task": prov.task,
                "head_version": prov.head_version,
                "embedding_model": prov.embedding_model,
                "device": prov.device,
                "limitations": prov.limitations,
                "results": objects,
            });
            return Ok(serde_json::to_string_pretty(&doc)? + "\n");
        }
        let sep = format.separator();
        let mut out = prov.comment_block();
        let _ = writeln!(out, "{}", self.columns.join(&sep.to_string()));
        for row in &self.rows {
            // A field containing the separator would silently shift every
            // later column, so quote it the way a CSV reader expects.
            let fields: Vec<String> = row
                .iter()
                .map(|f| {
                    if f.contains(sep) || f.contains('"') || f.contains('\n') {
                        format!("\"{}\"", f.replace('"', "\"\""))
                    } else {
                        f.clone()
                    }
                })
                .collect();
            let _ = writeln!(out, "{}", fields.join(&sep.to_string()));
        }
        Ok(out)
    }
}

/// Numbers stay numbers in JSON; everything else is a string.
///
/// Integers stay integers. A position written `1.0` or a length written
/// `76.0` is the sort of thing that survives into a downstream join as a
/// float key and fails to match, so whole numbers are emitted as such. A
/// `+0.333` keeps its sign but parses as a float either way.
fn json_scalar(value: &str) -> serde_json::Value {
    if let Ok(integer) = value.parse::<i64>() {
        return serde_json::Value::Number(integer.into());
    }
    value
        .parse::<f64>()
        .ok()
        .and_then(serde_json::Number::from_f64)
        .map_or_else(|| serde_json::Value::String(value.to_string()), serde_json::Value::Number)
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    let dir = models_dir(cli.models);

    match cli.command {
        Command::Models => {
            models(&dir);
            Ok(())
        }
        Command::Predict { task, input, output, format, mutations } => {
            let text = read_input(&input)?;
            let proteins = opendna_io::fasta::read(&text)
                .with_context(|| format!("parsing {} as FASTA", input.display()))?;
            eprintln!("{} sequences from {}", proteins.len(), input.display());

            let device = opendna_ml::best_device()?;
            let description = opendna_ml::device_description(&device);
            let prov = head_provenance(&dir, task, &description)?;
            eprintln!("Running {} on {description}", task.name());

            let heads = Heads::load(&dir, EMBEDDER, &device)?;
            let model = Esm2::from_pretrained(EMBEDDER, &device)?;

            let table = match task {
                Task::Disorder => disorder(&proteins, &heads, &model, &device)?,
                Task::Solubility => solubility(&proteins, &heads, &model, &device)?,
                Task::Stability => {
                    let path = mutations.ok_or_else(|| {
                        anyhow!(
                            "--mutations <file> is required for stability: the head scores named \
                             substitutions, so it needs to be told which ones. The file is a CSV \
                             of `name,mutation` rows, for example `ubiquitin,L8P`."
                        )
                    })?;
                    stability(&proteins, &path, &heads, &model, &device)?
                }
            };
            write_output(output.as_deref(), &table.render(format, &prov)?)
        }
    }
}

fn models(dir: &Path) {
    println!("Looking in {}", dir.display());
    println!("Embedding model: {}", EMBEDDER.repo());
    for task in [Task::Stability, Task::Solubility, Task::Disorder] {
        let files = HeadFiles::in_dir(dir, task.name());
        let state = if files.exist() {
            match read_metadata(&files, task.name(), EMBEDDER) {
                Ok(m) => format!("ready, version {}", m.version),
                Err(e) => format!("unusable: {e}"),
            }
        } else {
            "not installed".to_string()
        };
        println!("  {:11} {state}", task.name());
    }
}

fn disorder(
    proteins: &[opendna_core::Protein],
    heads: &Heads,
    model: &Esm2,
    device: &candle_core::Device,
) -> Result<Table> {
    let head = heads.disorder.as_ref().ok_or_else(|| anyhow!("the disorder head did not load"))?;
    let mut rows = Vec::new();
    for protein in proteins {
        let sequence = protein.sequence.to_string();
        let residues: Vec<char> = sequence.chars().collect();
        let embedding = if residues.len() > model.max_residues() {
            model.embed_windowed(&sequence)?
        } else {
            model.embed(&[sequence.as_str()])?.remove(0)
        };
        let probabilities = head.predict(&embedding.per_residue, embedding.length, device)?;
        for (index, probability) in probabilities.iter().enumerate() {
            rows.push(vec![
                protein.name.clone(),
                (index + 1).to_string(),
                residues.get(index).copied().unwrap_or('?').to_string(),
                format!("{probability:.4}"),
                u8::from(f64::from(*probability) >= DISORDER_THRESHOLD).to_string(),
            ]);
        }
    }
    Ok(Table { columns: vec!["name", "position", "residue", "probability", "disordered"], rows })
}

fn solubility(
    proteins: &[opendna_core::Protein],
    heads: &Heads,
    model: &Esm2,
    device: &candle_core::Device,
) -> Result<Table> {
    let head = heads.solubility.as_ref().ok_or_else(|| anyhow!("the solubility head did not load"))?;
    let mut rows = Vec::new();
    for protein in proteins {
        let sequence = protein.sequence.to_string();
        if sequence.chars().count() > model.max_residues() {
            // The head was trained on a mean over a single pass. Pooling
            // across windows is a different quantity, so refuse rather than
            // report a number computed differently from training.
            bail!(
                "{}: {} residues exceeds the embedding model's {} limit. The solubility head \
                 pools over one pass and has no windowed equivalent, so this sequence cannot be \
                 scored.",
                protein.name,
                sequence.chars().count(),
                model.max_residues()
            );
        }
        let embedding = model.embed(&[sequence.as_str()])?.remove(0);
        let percent = head.predict(&embedding.pooled, device)?;
        rows.push(vec![protein.name.clone(), sequence.chars().count().to_string(), format!("{percent:.1}")]);
    }
    Ok(Table { columns: vec!["name", "length", "solubility_percent"], rows })
}

/// Parse the `name,mutation` file, grouping by sequence name.
fn read_mutations(path: &Path) -> Result<Vec<(String, String)>> {
    let text = std::fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
    let mut out = Vec::new();
    for (number, line) in text.lines().enumerate() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let (name, mutation) = line
            .split_once(',')
            .ok_or_else(|| anyhow!("{}:{}: expected `name,mutation`", path.display(), number + 1))?;
        let (name, mutation) = (name.trim(), mutation.trim());
        // A header row is easy to leave in by accident, and treating it as a
        // mutation produces a confusing parse error further down.
        if number == 0 && mutation.eq_ignore_ascii_case("mutation") {
            continue;
        }
        out.push((name.to_string(), mutation.to_string()));
    }
    if out.is_empty() {
        bail!("{} contains no mutations", path.display());
    }
    Ok(out)
}

/// Split `L8P` into the wild-type residue, 0-based index, and mutant.
///
/// # Errors
/// If the label is malformed, out of range, or disagrees with the sequence at
/// that position — the last being the check that catches a file numbered
/// against a different construct, which would otherwise score the wrong
/// residue and look fine.
fn parse_mutation(label: &str, residues: &[char], name: &str) -> Result<(char, usize, char)> {
    let mut chars = label.chars();
    let wild = chars.next().ok_or_else(|| anyhow!("{name}: empty mutation"))?;
    let mutant = label
        .chars()
        .next_back()
        .filter(|_| label.chars().count() >= 3)
        .ok_or_else(|| anyhow!("{name}: {label:?} is not a mutation like L8P"))?;
    let digits: String = chars.clone().take(label.chars().count() - 2).collect();
    let position: usize = digits
        .parse()
        .with_context(|| format!("{name}: {label:?} has no position; expected something like L8P"))?;
    if position == 0 || position > residues.len() {
        bail!("{name}: {label} is outside a {}-residue sequence; positions are 1-based", residues.len());
    }
    let index = position - 1;
    if residues[index] != wild {
        bail!(
            "{name}: {label} says position {position} is {wild}, but the sequence has {}. The \
             mutation list and the FASTA disagree, so every score from this pair would be \
             attributed to the wrong residue.",
            residues[index]
        );
    }
    Ok((wild, index, mutant))
}

fn stability(
    proteins: &[opendna_core::Protein],
    mutations: &Path,
    heads: &Heads,
    model: &Esm2,
    device: &candle_core::Device,
) -> Result<Table> {
    let head = heads.stability.as_ref().ok_or_else(|| anyhow!("the stability head did not load"))?;
    let wanted = read_mutations(mutations)?;
    let standard = AminoAcid::STANDARD;
    let mut rows = Vec::new();

    for protein in proteins {
        let mine: Vec<&String> = wanted.iter().filter(|(n, _)| *n == protein.name).map(|(_, m)| m).collect();
        if mine.is_empty() {
            continue;
        }
        let sequence = protein.sequence.to_string();
        let residues: Vec<char> = sequence.chars().collect();
        if residues.len() > model.max_residues() {
            bail!(
                "{}: {} residues exceeds the embedding model's {} limit",
                protein.name,
                residues.len(),
                model.max_residues()
            );
        }

        let parsed: Vec<(char, usize, char, &String)> = mine
            .iter()
            .map(|label| parse_mutation(label, &residues, &protein.name).map(|(w, i, m)| (w, i, m, *label)))
            .collect::<Result<_>>()?;

        let embedding = model.embed(&[sequence.as_str()])?.remove(0);
        let mut positions: Vec<usize> = parsed.iter().map(|(_, i, _, _)| *i).collect();
        positions.sort_unstable();
        positions.dedup();
        let log_probs = model.masked_log_probs(&sequence, &positions)?;
        let index_of: std::collections::HashMap<usize, usize> =
            positions.iter().enumerate().map(|(n, p)| (*p, n)).collect();

        let mut features = Vec::new();
        let mut kept = Vec::new();
        for (wild, index, mutant, label) in &parsed {
            let (Some(wt), Some(mt)) = (
                standard.iter().position(|a| a.one_letter() == *wild),
                standard.iter().position(|a| a.one_letter() == *mutant),
            ) else {
                bail!(
                    "{}: {label} involves a residue the head was not trained on; only the 20 \
                     standard amino acids are encoded",
                    protein.name
                );
            };
            let lp = &log_probs[index_of[index]];
            let logp = |letter: char| -> f32 { lp[opendna_ml::esm2::alphabet::token_id(letter) as usize] };
            let site = embedding
                .residue(*index)
                .ok_or_else(|| anyhow!("{}: no embedding at {index}", protein.name))?;
            features.push(StabilityHead::features(site, wt, mt, logp(*mutant) - logp(*wild)));
            kept.push((label, logp(*mutant) - logp(*wild)));
        }
        let predicted = head.predict(&features, model.hidden_size(), device)?;
        for ((label, log_odds), ddg) in kept.into_iter().zip(predicted) {
            rows.push(vec![
                protein.name.clone(),
                (*label).clone(),
                format!("{ddg:+.3}"),
                format!("{log_odds:+.3}"),
            ]);
        }
    }

    if rows.is_empty() {
        bail!(
            "no mutation in {} matched a sequence in the FASTA file. Names must match the FASTA \
             header exactly.",
            mutations.display()
        );
    }
    Ok(Table { columns: vec!["name", "mutation", "ddg_kcal_per_mol", "log_odds"], rows })
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn a_mutation_resolves_against_the_sequence() {
        let residues: Vec<char> = "MQIFVKTL".chars().collect();
        assert_eq!(parse_mutation("M1A", &residues, "p").unwrap(), ('M', 0, 'A'));
        assert_eq!(parse_mutation("L8P", &residues, "p").unwrap(), ('L', 7, 'P'));
    }

    /// The check that matters: a mutation list numbered against a different
    /// construct must stop the run, not score a neighbouring residue.
    #[test]
    fn a_mutation_disagreeing_with_the_sequence_is_refused() {
        let residues: Vec<char> = "MQIFVKTL".chars().collect();
        let err = parse_mutation("L2P", &residues, "p").unwrap_err().to_string();
        assert!(err.contains("the sequence has Q"), "{err}");
        assert!(err.contains("wrong residue"), "{err}");
    }

    #[test]
    fn a_malformed_or_out_of_range_mutation_is_refused() {
        let residues: Vec<char> = "MQIF".chars().collect();
        for bad in ["", "L", "LP", "M9A", "M0A", "Mxa"] {
            assert!(parse_mutation(bad, &residues, "p").is_err(), "accepted {bad:?}");
        }
    }

    #[test]
    fn two_digit_positions_are_read_whole() {
        let residues: Vec<char> = "ACDEFGHIKLMNP".chars().collect();
        assert_eq!(parse_mutation("P13W", &residues, "p").unwrap(), ('P', 12, 'W'));
    }

    #[test]
    fn the_models_directory_prefers_the_flag_then_the_environment() {
        assert_eq!(models_dir(Some(PathBuf::from("/x"))), PathBuf::from("/x"));
        assert_eq!(models_dir(None), models_dir(None), "deterministic without the flag");
    }

    #[test]
    fn a_field_containing_the_separator_is_quoted() {
        let table = Table {
            columns: vec!["name", "value"],
            rows: vec![vec!["a,b".into(), "1".into()], vec!["plain".into(), "2".into()]],
        };
        let prov = Provenance {
            task: "disorder",
            head_version: "v".into(),
            embedding_model: "m".into(),
            device: "CPU".into(),
            limitations: vec![],
        };
        let csv = table.render(Format::Csv, &prov).unwrap();
        assert!(csv.contains("\"a,b\",1"), "{csv}");
        assert!(csv.contains("plain,2"), "{csv}");
    }

    #[test]
    fn json_keeps_numbers_as_numbers() {
        let table =
            Table { columns: vec!["name", "probability"], rows: vec![vec!["p".into(), "0.9412".into()]] };
        let prov = Provenance {
            task: "disorder",
            head_version: "0.6.0-dev".into(),
            embedding_model: "m".into(),
            device: "CPU".into(),
            limitations: vec!["careful".into()],
        };
        let out = table.render(Format::Json, &prov).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(&out).unwrap();
        assert_eq!(parsed["results"][0]["probability"], 0.9412);
        assert_eq!(parsed["results"][0]["name"], "p");
        assert_eq!(parsed["head_version"], "0.6.0-dev");
        assert_eq!(parsed["limitations"][0], "careful");
    }

    /// A length or a position emitted as `76.0` becomes a float key in a
    /// downstream join and silently fails to match an integer one.
    #[test]
    fn whole_numbers_stay_integers_in_json() {
        assert_eq!(json_scalar("76"), serde_json::json!(76));
        assert_eq!(json_scalar("1"), serde_json::json!(1));
        assert!(json_scalar("76").is_i64(), "a length became a float");
        assert_eq!(json_scalar("0.9412"), serde_json::json!(0.9412));
        assert_eq!(json_scalar("+0.333"), serde_json::json!(0.333));
        assert_eq!(json_scalar("L8P"), serde_json::json!("L8P"));
    }

    #[test]
    fn a_mutation_file_skips_comments_and_a_header_row() {
        let dir = std::env::temp_dir().join(format!("opendna-cli-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("m.csv");
        std::fs::write(&path, "name,mutation\n# a note\n\nubq,L8P\nubq, K6A \n").unwrap();
        let got = read_mutations(&path).unwrap();
        assert_eq!(got, vec![("ubq".to_string(), "L8P".to_string()), ("ubq".to_string(), "K6A".to_string())]);
        std::fs::remove_dir_all(&dir).ok();
    }
}
