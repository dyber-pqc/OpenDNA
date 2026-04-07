// OpenDNA Desktop - Tauri shell that hosts the React UI and manages the
// Python API server as a sidecar process.

use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

struct PythonSidecar(Mutex<Option<Child>>);

#[tauri::command]
fn get_api_url() -> String {
    "http://127.0.0.1:8765".to_string()
}

#[tauri::command]
fn check_python() -> Result<String, String> {
    Command::new("python")
        .arg("--version")
        .output()
        .map(|o| String::from_utf8_lossy(&o.stdout).to_string())
        .or_else(|_| {
            Command::new("python3")
                .arg("--version")
                .output()
                .map(|o| String::from_utf8_lossy(&o.stdout).to_string())
        })
        .map_err(|e| {
            format!(
                "Python not found: {}. Please install Python 3.10+ from python.org",
                e
            )
        })
}

#[tauri::command]
fn start_api_server(state: tauri::State<PythonSidecar>) -> Result<String, String> {
    let mut child_lock = state.0.lock().unwrap();
    if child_lock.is_some() {
        return Ok("API server already running".to_string());
    }

    let attempts: &[(&str, &[&str])] = &[
        (
            "python",
            &[
                "-m",
                "opendna.cli.main",
                "serve",
                "--no-open",
                "--port",
                "8765",
            ],
        ),
        (
            "python3",
            &[
                "-m",
                "opendna.cli.main",
                "serve",
                "--no-open",
                "--port",
                "8765",
            ],
        ),
    ];

    for (cmd, args) in attempts {
        let result = Command::new(cmd)
            .args(*args)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn();
        if let Ok(child) = result {
            *child_lock = Some(child);
            return Ok(format!("Started API server via {}", cmd));
        }
    }

    Err(
        "Could not launch the OpenDNA Python API server. Make sure Python is installed and OpenDNA is installed via 'pip install opendna'."
            .to_string(),
    )
}

#[tauri::command]
fn stop_api_server(state: tauri::State<PythonSidecar>) -> Result<String, String> {
    let mut child_lock = state.0.lock().unwrap();
    if let Some(mut child) = child_lock.take() {
        let _ = child.kill();
        return Ok("Stopped".to_string());
    }
    Ok("No server running".to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::default().build())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_process::init())
        .manage(PythonSidecar(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![
            get_api_url,
            check_python,
            start_api_server,
            stop_api_server
        ])
        .run(tauri::generate_context!())
        .expect("error while running OpenDNA desktop application");
}
