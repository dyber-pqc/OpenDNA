import { useEffect, useState } from "react";
import * as api from "../../api/client";
import "./BackendStatus.css";

type Status = "checking" | "connected" | "disconnected";

// Check if we're running inside the Tauri desktop shell
function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI__" in window;
}

// Call a Tauri command from the React side
async function tauriInvoke<T = any>(cmd: string, args: any = {}): Promise<T> {
  // @ts-ignore - __TAURI__ is injected at runtime by the Tauri shell
  const tauri = (window as any).__TAURI__;
  if (!tauri) throw new Error("Not running in Tauri");
  if (tauri.core && tauri.core.invoke) {
    return await tauri.core.invoke(cmd, args);
  }
  if (tauri.invoke) {
    return await tauri.invoke(cmd, args);
  }
  throw new Error("Tauri invoke API not available");
}

export default function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [retryCount, setRetryCount] = useState(0);
  const [dismissed, setDismissed] = useState(false);
  const [tauriMode] = useState(isTauri());
  const [pythonInfo, setPythonInfo] = useState<string>("");
  const [opendnaInfo, setOpendnaInfo] = useState<string>("");
  const [startError, setStartError] = useState<string>("");
  const [autoStartTried, setAutoStartTried] = useState(false);

  const checkConnection = async () => {
    setStatus("checking");
    try {
      await api.getHardware();
      setStatus("connected");
      setStartError("");
    } catch {
      setStatus("disconnected");
    }
  };

  const tryAutoStart = async () => {
    if (!tauriMode || autoStartTried) return;
    setAutoStartTried(true);
    try {
      const result = await tauriInvoke<string>("start_api_server");
      console.log("Backend auto-start:", result);
      // Wait a moment for the server to actually start, then retry
      setTimeout(() => setRetryCount((c) => c + 1), 2000);
    } catch (e: any) {
      setStartError(String(e));
    }
  };

  const runDiagnostics = async () => {
    if (!tauriMode) return;
    try {
      const py = await tauriInvoke<string>("check_python");
      setPythonInfo(py);
    } catch (e: any) {
      setPythonInfo(`Error: ${e}`);
    }
    try {
      const od = await tauriInvoke<string>("check_opendna_installed");
      setOpendnaInfo(od);
    } catch (e: any) {
      setOpendnaInfo(`Error: ${e}`);
    }
  };

  // Initial check
  useEffect(() => {
    checkConnection();
  }, [retryCount]);

  // When we go disconnected for the first time in Tauri, try auto-start
  useEffect(() => {
    if (status === "disconnected" && tauriMode && !autoStartTried) {
      tryAutoStart();
      runDiagnostics();
    }
  }, [status, tauriMode, autoStartTried]);

  // Periodic background check
  useEffect(() => {
    if (status === "connected") return;
    const id = setInterval(() => {
      setRetryCount((c) => c + 1);
    }, 10000);
    return () => clearInterval(id);
  }, [status]);

  const handleManualStart = async () => {
    setAutoStartTried(false);
    await tryAutoStart();
  };

  if (status === "connected" || dismissed) return null;

  return (
    <div className={`backend-status ${status}`}>
      <div className="bs-icon">{status === "checking" ? "⟳" : "⚠"}</div>
      <div className="bs-content">
        <div className="bs-title">
          {status === "checking"
            ? "Connecting to OpenDNA backend..."
            : "OpenDNA backend not reachable"}
        </div>
        {status === "disconnected" && (
          <div className="bs-body">
            {tauriMode ? (
              <>
                The Python API server is not running.
                {autoStartTried && !startError && (
                  <div className="bs-info">
                    ⏳ Trying to start it automatically...
                  </div>
                )}
                {startError && (
                  <div className="bs-error">
                    <strong>Auto-start failed:</strong>
                    <pre>{startError}</pre>
                  </div>
                )}
                {pythonInfo && (
                  <div className="bs-diag">
                    <strong>Detected Python interpreters:</strong>
                    <pre>{pythonInfo}</pre>
                  </div>
                )}
                {opendnaInfo && (
                  <div className="bs-diag">
                    <strong>OpenDNA package:</strong>
                    <pre>{opendnaInfo}</pre>
                  </div>
                )}
                <div className="bs-fallback">
                  If auto-start fails, open a terminal and run:
                  <pre>python -m opendna.api.server --port 8765</pre>
                </div>
              </>
            ) : (
              <>
                You're running OpenDNA in browser mode. The Python API server
                must be started manually. Open a terminal and run:
                <pre>python -m opendna.api.server --port 8765</pre>
                If you haven't installed OpenDNA yet:
                <pre>pip install opendna</pre>
                <span className="bs-hint">
                  (Run them as separate commands — PowerShell &lt; 7 doesn't
                  support &amp;&amp;.)
                </span>
              </>
            )}
            <br />
            The page will reconnect automatically once the server is up.
          </div>
        )}
      </div>
      <div className="bs-actions">
        {status === "disconnected" && tauriMode && (
          <button className="bs-btn" onClick={handleManualStart}>
            Start backend
          </button>
        )}
        {status === "disconnected" && (
          <button
            className="bs-btn"
            onClick={() => setRetryCount((c) => c + 1)}
          >
            Retry now
          </button>
        )}
        <button
          className="bs-btn bs-dismiss"
          onClick={() => setDismissed(true)}
          title="Hide"
        >
          ×
        </button>
      </div>
    </div>
  );
}
