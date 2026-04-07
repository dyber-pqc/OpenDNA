// OpenDNA Desktop - Tauri shell that hosts the React UI and manages the
// Python API server as a sidecar process.

use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::Manager;

struct PythonSidecar(Mutex<Option<Child>>);

#[tauri::command]
fn get_api_url() -> String {
    "http://127.0.0.1:8765".to_string()
}

#[tauri::command]
fn check_python() -> Result<String, String> {
    let candidates = ["python", "python3", "py"];
    for cmd in &candidates {
        if let Ok(output) = Command::new(cmd).arg("--version").output() {
            if output.status.success() {
                let version = String::from_utf8_lossy(&output.stdout).trim().to_string();
                let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
                let combined = if version.is_empty() { stderr } else { version };
                return Ok(format!("{} ({})", combined, cmd));
            }
        }
    }
    Err("Python not found. Please install Python 3.10+ from https://python.org".to_string())
}

#[tauri::command]
fn check_opendna_installed() -> Result<String, String> {
    let candidates = ["python", "python3", "py"];
    for cmd in &candidates {
        if let Ok(output) = Command::new(cmd)
            .args(["-c", "import opendna; print(opendna.__version__)"])
            .output()
        {
            if output.status.success() {
                let version = String::from_utf8_lossy(&output.stdout).trim().to_string();
                return Ok(version);
            }
        }
    }
    Err("OpenDNA Python package not installed. Run 'pip install opendna' in a terminal.".to_string())
}

#[tauri::command]
fn start_api_server(state: tauri::State<PythonSidecar>) -> Result<String, String> {
    let mut child_lock = state.0.lock().unwrap();
    if child_lock.is_some() {
        return Ok("API server already running".to_string());
    }

    // Try multiple python interpreter names AND multiple invocation styles.
    // The CLI command is preferred but we have a fallback that uses the API directly.
    let cli_args: &[&str] = &[
        "-m",
        "opendna.cli.main",
        "serve",
        "--no-open",
        "--port",
        "8765",
        "--host",
        "127.0.0.1",
    ];
    let direct_args: &[&str] = &[
        "-c",
        "from opendna.api.server import start_server; start_server(host='127.0.0.1', port=8765)",
    ];

    let interpreters = ["python", "python3", "py"];
    for interp in &interpreters {
        // Try CLI first
        if let Ok(child) = Command::new(interp)
            .args(cli_args)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
        {
            *child_lock = Some(child);
            return Ok(format!("Started API server: {} -m opendna.cli.main", interp));
        }
        // Fallback to direct invocation
        if let Ok(child) = Command::new(interp)
            .args(direct_args)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
        {
            *child_lock = Some(child);
            return Ok(format!("Started API server: {} -c (direct)", interp));
        }
    }

    Err(
        "Could not launch the OpenDNA Python API server. Make sure Python 3.10+ is installed and OpenDNA is installed via 'pip install opendna'."
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

fn try_auto_start(app: &tauri::AppHandle) {
    let state: tauri::State<PythonSidecar> = app.state();
    match start_api_server(state) {
        Ok(msg) => log::info!("Sidecar startup: {}", msg),
        Err(e) => log::warn!("Sidecar startup failed: {}", e),
    }
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
            check_opendna_installed,
            start_api_server,
            stop_api_server
        ])
        .setup(|app| {
            // Auto-start the Python API sidecar so the UI has a backend to talk to
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                try_auto_start(&handle);
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Stop the Python sidecar when the main window closes
                let state: tauri::State<PythonSidecar> = window.state();
                let _ = stop_api_server(state);
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running OpenDNA desktop application");
}
