import { useEffect, useState } from "react";
import * as api from "../../api/client";
import "./BackendStatus.css";

type Status = "checking" | "connected" | "disconnected";

export default function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [retryCount, setRetryCount] = useState(0);
  const [dismissed, setDismissed] = useState(false);

  const checkConnection = async () => {
    setStatus("checking");
    try {
      await api.getHardware();
      setStatus("connected");
    } catch {
      setStatus("disconnected");
    }
  };

  // Initial check + auto-retry on disconnect
  useEffect(() => {
    let mounted = true;
    const run = async () => {
      if (!mounted) return;
      await checkConnection();
    };
    run();
    return () => {
      mounted = false;
    };
  }, [retryCount]);

  // Periodic background check (every 10s) so the banner clears
  // automatically once the server starts
  useEffect(() => {
    if (status === "connected") return;
    const id = setInterval(() => {
      setRetryCount((c) => c + 1);
    }, 10000);
    return () => clearInterval(id);
  }, [status]);

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
            The Python API server isn't running. Open a terminal and run:
            <pre>pip install opendna && opendna serve --port 8765</pre>
            Or, if you've already installed it, just:
            <pre>opendna serve --port 8765</pre>
            The page will reconnect automatically once the server is up.
          </div>
        )}
      </div>
      <div className="bs-actions">
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
