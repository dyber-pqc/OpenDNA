import { useEffect, useState } from "react";
import "./ProteinOfDayBanner.css";

interface PotD {
  name: string;
  description: string;
  fun_fact: string;
  sequence: string;
  category?: string;
  year_discovered?: number;
}

interface ProteinOfDayBannerProps {
  onLoadSequence: (sequence: string, label: string) => void;
}

const STORAGE_KEY = "opendna.potd.dismissed";

export default function ProteinOfDayBanner({ onLoadSequence }: ProteinOfDayBannerProps) {
  const [potd, setPotd] = useState<PotD | null>(null);
  const [dismissed, setDismissed] = useState<boolean>(false);

  useEffect(() => {
    const today = new Date().toISOString().slice(0, 10);
    if (localStorage.getItem(STORAGE_KEY) === today) {
      setDismissed(true);
      return;
    }
    fetch("http://localhost:8765/v1/protein_of_the_day")
      .then((r) => r.json())
      .then(setPotd)
      .catch(() => {});
  }, []);

  if (dismissed || !potd) return null;

  const handleDismiss = () => {
    const today = new Date().toISOString().slice(0, 10);
    localStorage.setItem(STORAGE_KEY, today);
    setDismissed(true);
  };

  return (
    <div className="potd-banner">
      <div className="potd-banner-icon">🧬</div>
      <div className="potd-banner-body">
        <div className="potd-banner-title">
          Protein of the Day: <strong>{potd.name}</strong>
        </div>
        <div className="potd-banner-desc">{potd.description}</div>
      </div>
      <div className="potd-banner-actions">
        <button
          className="potd-banner-btn primary"
          onClick={() => onLoadSequence(potd.sequence, potd.name)}
        >
          Load this protein
        </button>
        <button className="potd-banner-btn" onClick={handleDismiss}>
          Dismiss
        </button>
      </div>
    </div>
  );
}
