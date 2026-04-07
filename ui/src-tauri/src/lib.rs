// OpenDNA Desktop - Tauri shell that hosts the React UI and manages the
// Python API server as a sidecar process.

use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::Manager;

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

// Windows-specific flag to hide the console window when spawning a child process.
// Without this, every Python sidecar launch pops up a black cmd.exe window.
#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x08000000;

/// Apply platform-specific spawn settings to a Command:
/// - Use Stdio::null() so the child can't deadlock on pipe buffers
/// - Hide the console window on Windows
fn configure_child_command(cmd: &mut Command) {
    cmd.stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    #[cfg(target_os = "windows")]
    {
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
}

struct PythonSidecar(Mutex<Option<Child>>);

#[tauri::command]
fn get_api_url() -> String {
    "http://127.0.0.1:8765".to_string()
}

/// Find Python interpreters on the system. Tries PATH first, then common
/// install locations on Windows, macOS, and Linux.
fn find_python_interpreters() -> Vec<String> {
    let mut found: Vec<String> = Vec::new();

    // First, try standard PATH-based names
    let path_candidates = ["python", "python3", "python3.12", "python3.11", "python3.10", "py"];
    for cmd_name in &path_candidates {
        let mut cmd = Command::new(cmd_name);
        cmd.arg("--version");
        #[cfg(target_os = "windows")]
        {
            cmd.creation_flags(CREATE_NO_WINDOW);
        }
        if let Ok(output) = cmd.output() {
            if output.status.success() {
                found.push(cmd_name.to_string());
            }
        }
    }

    // Common install locations on Windows
    #[cfg(target_os = "windows")]
    {
        if let Ok(home) = std::env::var("USERPROFILE") {
            let home_path = PathBuf::from(home);
            // AppData\Roaming\Python\Python3XX\Scripts (per-user pip install location)
            for ver in ["Python314", "Python313", "Python312", "Python311", "Python310"] {
                let p = home_path
                    .join("AppData")
                    .join("Roaming")
                    .join("Python")
                    .join(ver)
                    .join("Scripts");
                if p.exists() {
                    let py = p.join("python.exe");
                    if py.exists() {
                        found.push(py.to_string_lossy().into_owned());
                    }
                }
                // The actual interpreter is in AppData\Local\Programs\Python\
                let p2 = home_path
                    .join("AppData")
                    .join("Local")
                    .join("Programs")
                    .join("Python")
                    .join(ver)
                    .join("python.exe");
                if p2.exists() {
                    found.push(p2.to_string_lossy().into_owned());
                }
            }
        }
        // System-wide Python installs
        for ver in ["314", "313", "312", "311", "310"] {
            let candidates = [
                format!("C:\\Python{}\\python.exe", ver),
                format!("C:\\Program Files\\Python{}\\python.exe", ver),
                format!("C:\\Program Files (x86)\\Python{}\\python.exe", ver),
            ];
            for p in &candidates {
                if PathBuf::from(p).exists() {
                    found.push(p.clone());
                }
            }
        }
    }

    // Common install locations on macOS
    #[cfg(target_os = "macos")]
    {
        let candidates = [
            "/usr/local/bin/python3",
            "/usr/local/bin/python",
            "/opt/homebrew/bin/python3",
            "/opt/homebrew/bin/python",
            "/usr/bin/python3",
            "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
            "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
            "/Library/Frameworks/Python.framework/Versions/3.10/bin/python3",
        ];
        for p in &candidates {
            if PathBuf::from(p).exists() {
                found.push(p.to_string());
            }
        }
    }

    // Common install locations on Linux
    #[cfg(target_os = "linux")]
    {
        let candidates = [
            "/usr/bin/python3",
            "/usr/bin/python",
            "/usr/local/bin/python3",
            "/usr/local/bin/python",
        ];
        for p in &candidates {
            if PathBuf::from(p).exists() {
                found.push(p.to_string());
            }
        }
    }

    // Deduplicate while preserving order
    let mut seen = std::collections::HashSet::new();
    found.retain(|p| seen.insert(p.clone()));
    found
}

/// Verify that a python interpreter has opendna installed.
/// Returns the version string on success.
fn verify_opendna(python: &str) -> Result<String, String> {
    let mut cmd = Command::new(python);
    cmd.args(["-c", "import opendna, sys; print(opendna.__version__); sys.exit(0)"]);
    #[cfg(target_os = "windows")]
    {
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    let output = cmd
        .output()
        .map_err(|e| format!("Failed to run {}: {}", python, e))?;
    if !output.status.success() {
        let err = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("opendna not importable: {}", err));
    }
    let version = String::from_utf8_lossy(&output.stdout).trim().to_string();
    Ok(version)
}

#[tauri::command]
fn check_python() -> Result<String, String> {
    let interpreters = find_python_interpreters();
    if interpreters.is_empty() {
        return Err(
            "No Python interpreter found. Please install Python 3.10+ from https://python.org and check 'Add to PATH' during install.".to_string()
        );
    }
    Ok(interpreters.join("\n"))
}

#[tauri::command]
fn check_opendna_installed() -> Result<String, String> {
    let interpreters = find_python_interpreters();
    let mut errors = Vec::new();
    for py in &interpreters {
        match verify_opendna(py) {
            Ok(version) => return Ok(format!("{} (via {})", version, py)),
            Err(e) => errors.push(format!("{}: {}", py, e)),
        }
    }
    Err(format!(
        "OpenDNA Python package not installed in any detected interpreter.\n\nTried:\n{}\n\nFix:\n  pip install opendna",
        errors.join("\n")
    ))
}

#[tauri::command]
fn start_api_server(state: tauri::State<PythonSidecar>) -> Result<String, String> {
    let mut child_lock = state.0.lock().unwrap();
    if child_lock.is_some() {
        return Ok("API server already running".to_string());
    }

    let interpreters = find_python_interpreters();
    if interpreters.is_empty() {
        return Err("No Python interpreter found. Please install Python 3.10+ from https://python.org".to_string());
    }

    // Try invocation styles in order of robustness:
    // 1. python -m opendna.api.server --port 8765 (most direct, works in any version)
    // 2. python -m opendna.cli.main serve --no-open --port 8765 (uses CLI, v0.2+)
    // 3. python -c "from opendna.api.server import start_server; start_server(host='127.0.0.1', port=8765)"
    let invocation_styles: Vec<Vec<&str>> = vec![
        vec!["-m", "opendna.api.server", "--host", "127.0.0.1", "--port", "8765"],
        vec!["-m", "opendna.cli.main", "serve", "--no-open", "--host", "127.0.0.1", "--port", "8765"],
        vec!["-c", "from opendna.api.server import start_server; start_server(host='127.0.0.1', port=8765)"],
    ];

    let mut last_error = String::new();

    for python in &interpreters {
        // First verify opendna is importable in this interpreter
        match verify_opendna(python) {
            Ok(_version) => {}
            Err(e) => {
                last_error = format!("{} - {}", python, e);
                continue;
            }
        }

        for args in &invocation_styles {
            let mut cmd = Command::new(python);
            cmd.args(args);
            configure_child_command(&mut cmd);
            let result = cmd.spawn();
            if let Ok(child) = result {
                *child_lock = Some(child);
                return Ok(format!("Started API server: {} {}", python, args.join(" ")));
            }
        }
    }

    Err(format!(
        "Could not launch the OpenDNA Python API server.\n\nLast error: {}\n\nFix:\n  1. Install Python 3.10+ from https://python.org\n  2. Run: pip install opendna\n  3. Restart the OpenDNA desktop app",
        last_error
    ))
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
