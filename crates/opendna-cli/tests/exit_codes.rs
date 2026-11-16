//! The exit-code contract, checked against the real binary.
//!
//! A pipeline reads the status, not the message. The codes are documented in
//! the README and in `exit.rs`, and a documented contract nobody exercises is
//! a comment. So this runs the compiled `opendna` and asserts what each kind
//! of failure returns.
//!
//! It needs trained heads, which are not in the repository: they are hundreds
//! of kilobytes of weights published separately. With none installed the test
//! prints what it would have needed and passes, rather than failing on every
//! machine that has not downloaded them. That is a deliberate trade — a test
//! that fails for everybody gets disabled, and then it checks nothing at all.
//!
//! Every fixture is built in a temporary directory from a copy of the real
//! models, so nothing here can damage the installation it is testing.
//!
//! The cases split by cost. Most of the contract is about refusing before any
//! inference happens, which is fast even unoptimised. Two cases have to embed
//! a sequence, and candle in a debug build turns that from seconds into
//! minutes, so they are `#[ignore]`d and run deliberately:
//!
//! ```text
//! cargo test --release -p opendna-cli -- --ignored
//! ```

#![allow(clippy::unwrap_used, clippy::print_stdout)]

use std::path::{Path, PathBuf};
use std::process::Command;

/// Where the heads are, if they are anywhere.
fn models() -> Option<PathBuf> {
    let dir = std::env::var_os("OPENDNA_MODELS").map_or_else(|| PathBuf::from("models"), PathBuf::from);
    // The second candidate is relative to the workspace root, since cargo may
    // run us from either there or the crate directory.
    [dir.clone(), Path::new("../..").join(&dir)]
        .into_iter()
        .find(|candidate| candidate.join("disorder.safetensors").is_file())
}

fn scratch(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("opendna-exit-{name}-{}", std::process::id()));
    std::fs::remove_dir_all(&dir).ok();
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

/// Copy a directory's files one level deep, which is all a models directory is.
fn copy_models(from: &Path, to: &Path) {
    std::fs::create_dir_all(to).unwrap();
    for entry in std::fs::read_dir(from).unwrap() {
        let entry = entry.unwrap();
        if entry.file_type().unwrap().is_file() {
            std::fs::copy(entry.path(), to.join(entry.file_name())).unwrap();
        }
    }
}

fn sha256(bytes: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

/// Held for the whole of any test that spawns a run which embeds something.
///
/// The Hugging Face cache cannot be read by two processes at once: on Windows
/// the second one is refused the weights file. Cargo runs tests in parallel,
/// so without this the two inference tests race and whichever loses reports a
/// broken installation. Not a workaround for a test bug -- it is the same
/// constraint real users have, and `staging::open_embedder` says so in its
/// error.
static EMBEDDER: std::sync::Mutex<()> = std::sync::Mutex::new(());

/// Take that lock, ignoring poisoning: a panic in the other test tells us
/// nothing about whether the cache is readable now.
fn one_at_a_time() -> std::sync::MutexGuard<'static, ()> {
    EMBEDDER.lock().unwrap_or_else(std::sync::PoisonError::into_inner)
}

/// Run the binary and return (status code, stdout).
fn run(args: &[&str]) -> (i32, String) {
    let output = Command::new(env!("CARGO_BIN_EXE_opendna")).args(args).output().unwrap();
    (output.status.code().unwrap_or(-1), String::from_utf8_lossy(&output.stdout).into_owned())
}

/// The failures that are refused before any inference starts.
// Long because it is a list. Splitting a table of cases across functions to
// satisfy a line count would make it harder to read and easier to forget a
// case in.
#[allow(clippy::too_many_lines)]
#[test]
fn every_kind_of_failure_returns_the_status_the_contract_promises() {
    let Some(installed) = models() else {
        println!("no heads installed; skipping. Set OPENDNA_MODELS or run `opendna stage`.");
        return;
    };
    let base = scratch("fixtures");
    let fasta = base.join("ubq.fasta");
    std::fs::write(
        &fasta,
        ">ubiquitin\nMQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG\n",
    )
    .unwrap();

    // Each case is (expected status, what it is, arguments).
    let empty = base.join("empty");
    std::fs::create_dir_all(&empty).unwrap();

    // Corrupt: one byte appended, so the weights no longer hash to what the
    // metadata records. This is what a truncated download looks like.
    let corrupt = base.join("corrupt");
    copy_models(&installed, &corrupt);
    {
        let path = corrupt.join("disorder.safetensors");
        let mut bytes = std::fs::read(&path).unwrap();
        bytes.push(b'x');
        std::fs::write(&path, bytes).unwrap();
    }

    // Swapped: burial's weights presented as the disorder head, with the
    // metadata rewritten to match so the file verifies. Nothing about the
    // files is wrong; the numbers are.
    let swapped = base.join("swapped");
    copy_models(&installed, &swapped);
    {
        let weights = std::fs::read(swapped.join("burial.safetensors")).unwrap();
        std::fs::write(swapped.join("disorder.safetensors"), &weights).unwrap();
        let path = swapped.join("disorder.metadata.json");
        let mut meta: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
        meta["weights_sha256"] = sha256(&weights).into();
        std::fs::write(&path, serde_json::to_string_pretty(&meta).unwrap()).unwrap();
    }

    let bad_fasta = base.join("bad.fasta");
    std::fs::write(&bad_fasta, "not a fasta at all\n").unwrap();
    let wrong_mutation = base.join("wrong.csv");
    // Position 8 is a leucine, so a label calling it Q cannot be scored: a
    // list numbered against a different construct must stop the run.
    std::fs::write(&wrong_mutation, "name,mutation\nubiquitin,Q8P\n").unwrap();

    let checkpoint = base.join("run.jsonl");
    let checkpoint = checkpoint.to_str().unwrap().to_owned();
    let installed = installed.to_str().unwrap().to_owned();
    let (fasta, bad_fasta) = (fasta.to_str().unwrap(), bad_fasta.to_str().unwrap());
    let wrong_mutation = wrong_mutation.to_str().unwrap();
    let (empty, corrupt, swapped) =
        (empty.to_str().unwrap(), corrupt.to_str().unwrap(), swapped.to_str().unwrap());

    let cases: Vec<(i32, &str, Vec<&str>)> = vec![
        (2, "an unknown flag", vec!["predict", "--task", "disorder", "--nonsense"]),
        (
            2,
            "stability without --mutations",
            vec!["--models", &installed, "predict", "--task", "stability", "-i", fasta],
        ),
        (
            2,
            "the CAID format on the wrong task",
            vec!["--models", &installed, "predict", "--task", "burial", "--format", "caid", "-i", fasta],
        ),
        (3, "no heads installed", vec!["--models", empty, "predict", "--task", "disorder", "-i", fasta]),
        (3, "corrupt weights", vec!["--models", corrupt, "predict", "--task", "disorder", "-i", fasta]),
        (
            3,
            "--offline with nothing staged",
            vec!["--models", &installed, "--offline", "predict", "--task", "disorder", "-i", fasta],
        ),
        (
            4,
            "a file that is not FASTA",
            vec!["--models", &installed, "predict", "--task", "disorder", "-i", bad_fasta],
        ),
        (
            2,
            "a chunk size of zero",
            vec![
                "--models",
                &installed,
                "predict",
                "--task",
                "disorder",
                "-i",
                fasta,
                "--checkpoint",
                &checkpoint,
                "--chunk",
                "0",
            ],
        ),
        (
            2,
            "a checkpoint with the CAID format",
            vec![
                "--models",
                &installed,
                "predict",
                "--task",
                "disorder",
                "--format",
                "caid",
                "-i",
                fasta,
                "--checkpoint",
                &checkpoint,
            ],
        ),
        (
            4,
            "a mutation the sequence contradicts",
            vec![
                "--models",
                &installed,
                "predict",
                "--task",
                "stability",
                "-i",
                fasta,
                "--mutations",
                wrong_mutation,
            ],
        ),
    ];
    let _ = swapped;

    let mut wrong = Vec::new();
    for (want, what, args) in &cases {
        let (got, stdout) = run(args);
        if got != *want {
            wrong.push(format!("{what}: wanted {want}, got {got}"));
        }
        // `predict` streams results to standard output, so a failing run must
        // leave it empty: a pipe collecting results must never receive an
        // error as though it were data. `selftest` is a report command whose
        // standard output is the report, so this does not apply to it.
        if got != 0 && args.contains(&"predict") && !stdout.is_empty() {
            wrong.push(format!("{what}: wrote {} bytes to stdout while failing", stdout.len()));
        }
    }
    // A refused run must not leave a checkpoint behind. A file created by a
    // run that never started would be resumed by the next one.
    if Path::new(&checkpoint).exists() {
        wrong.push("a refused run created its checkpoint file".to_string());
    }
    std::fs::remove_dir_all(&base).ok();
    assert!(wrong.is_empty(), "the exit-code contract does not hold:\n  {}", wrong.join("\n  "));
}

/// Resuming is only safe if continuing the wrong checkpoint is impossible.
///
/// Needs real inference, because the checkpoint under test has to be one the
/// binary itself wrote: hand-building the header here would be a second
/// statement of its shape, and the two would drift.
#[test]
#[ignore = "embeds a sequence; run with --release -- --ignored"]
fn a_checkpoint_from_another_run_is_refused_and_an_interrupted_one_is_continued() {
    let _one_at_a_time = one_at_a_time();
    let Some(installed) = models() else {
        println!("no heads installed; skipping.");
        return;
    };
    let installed = installed.to_str().unwrap().to_owned();
    let base = scratch("resume");
    let ubq = base.join("ubq.fasta");
    std::fs::write(
        &ubq,
        ">ubiquitin\nMQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG\n",
    )
    .unwrap();
    // Two sequences, so a chunk size of one gives a run with two chunks.
    let pair = base.join("pair.fasta");
    std::fs::write(
        &pair,
        ">ubiquitin\nMQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG\n\
         >fragment\nMQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEG\n",
    )
    .unwrap();

    let reference = base.join("reference.csv");
    let checkpoint = base.join("run.jsonl");
    let predict = |input: &Path, output: &Path, checkpoint: &Path| -> (i32, String) {
        let output = Command::new(env!("CARGO_BIN_EXE_opendna"))
            .args([
                "--models",
                &installed,
                "predict",
                "--task",
                "disorder",
                "-i",
                input.to_str().unwrap(),
                "-o",
                output.to_str().unwrap(),
                "--checkpoint",
                checkpoint.to_str().unwrap(),
                "--chunk",
                "1",
                "--no-manifest",
            ])
            .output()
            .unwrap();
        (output.status.code().unwrap_or(-1), String::from_utf8_lossy(&output.stderr).into_owned())
    };

    let (code, stderr) = predict(&pair, &reference, &checkpoint);
    assert_eq!(code, 0, "the reference run must finish:\n{stderr}");

    // The same checkpoint against a different input. The rows in it describe
    // sequences this run is not predicting, so continuing would produce a
    // table that is half one run and half another.
    let (code, stderr) = predict(&ubq, &base.join("wrong.csv"), &checkpoint);
    assert_eq!(code, 4, "a checkpoint for another input must be refused:\n{stderr}");
    assert!(stderr.contains("input digest"), "the refusal must name the field:\n{stderr}");

    // An interrupted run, as a kill partway through a write leaves it: the
    // first chunk intact and the second one half-written.
    let interrupted = base.join("interrupted.jsonl");
    let full = std::fs::read_to_string(&checkpoint).unwrap();
    let mut lines = full.lines();
    let header = lines.next().unwrap();
    let first = lines.next().unwrap();
    let torn = &lines.next().unwrap()[..20];
    std::fs::write(&interrupted, format!("{header}\n{first}\n{torn}")).unwrap();

    let resumed = base.join("resumed.csv");
    let (code, stderr) = predict(&pair, &resumed, &interrupted);
    assert_eq!(code, 0, "an interrupted run must continue:\n{stderr}");
    assert!(stderr.contains("Resuming"), "it should say it is resuming:\n{stderr}");

    // The point of the whole exercise: being interrupted changed nothing.
    assert_eq!(
        std::fs::read_to_string(&resumed).unwrap(),
        std::fs::read_to_string(&reference).unwrap(),
        "a resumed run must produce the same bytes as an uninterrupted one"
    );
    std::fs::remove_dir_all(&base).ok();
}

/// The two cases that need real inference.
///
/// Slow unoptimised, so run with `--release -- --ignored`. They are still
/// worth having: a contract that only describes failures says nothing about
/// the success it is contrasted with, and exit 5 is the only code that proves
/// the checks themselves can fail the run.
#[test]
#[ignore = "embeds a sequence; run with --release -- --ignored"]
fn a_working_run_exits_zero_and_a_wrong_model_exits_five() {
    let _one_at_a_time = one_at_a_time();
    let Some(installed) = models() else {
        println!("no heads installed; skipping.");
        return;
    };
    let base = scratch("inference");
    let fasta = base.join("ubq.fasta");
    std::fs::write(
        &fasta,
        ">ubiquitin\nMQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG\n",
    )
    .unwrap();

    let (code, out) = run(&[
        "--models",
        installed.to_str().unwrap(),
        "predict",
        "--task",
        "disorder",
        "-i",
        fasta.to_str().unwrap(),
    ]);
    assert_eq!(code, 0, "a good install must predict");
    assert!(out.contains("probability"), "the table should reach standard output");

    // Burial's weights as the disorder head, metadata rewritten so the file
    // verifies: the install is intact and the numbers are wrong, which is
    // exactly what exit 5 is for.
    let swapped = base.join("swapped");
    copy_models(&installed, &swapped);
    let weights = std::fs::read(swapped.join("burial.safetensors")).unwrap();
    std::fs::write(swapped.join("disorder.safetensors"), &weights).unwrap();
    let path = swapped.join("disorder.metadata.json");
    let mut meta: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
    meta["weights_sha256"] = sha256(&weights).into();
    std::fs::write(&path, serde_json::to_string_pretty(&meta).unwrap()).unwrap();

    let (code, out) = run(&["--models", swapped.to_str().unwrap(), "selftest"]);
    assert_eq!(code, 5, "a model that does not reproduce must exit 5");
    assert!(out.contains("FAILED"), "the report should name what failed:\n{out}");
    std::fs::remove_dir_all(&base).ok();
}

/// A corrupt head must stop `models` too, not only a prediction: the whole
/// point of the command is to be the thing an install script runs first.
#[test]
fn models_fails_on_corrupt_weights_and_passes_on_a_good_install() {
    let Some(installed) = models() else {
        println!("no heads installed; skipping.");
        return;
    };
    let base = scratch("models");
    let good = base.join("good");
    copy_models(&installed, &good);
    assert_eq!(run(&["--models", good.to_str().unwrap(), "models"]).0, 0);

    let path = good.join("stability.safetensors");
    let mut bytes = std::fs::read(&path).unwrap();
    bytes.push(0);
    std::fs::write(&path, bytes).unwrap();
    assert_eq!(run(&["--models", good.to_str().unwrap(), "models"]).0, 3);
    std::fs::remove_dir_all(&base).ok();
}
