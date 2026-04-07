import { useEffect, useRef, useState } from "react";
import "./CommandPalette.css";

export interface Command {
  id: string;
  label: string;
  group: string;
  shortcut?: string;
  action: () => void;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  commands: Command[];
}

export default function CommandPalette({ open, onClose, commands }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setQuery("");
      setSelected(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const filtered = commands.filter((c) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return c.label.toLowerCase().includes(q) || c.group.toLowerCase().includes(q);
  });

  useEffect(() => {
    setSelected(0);
  }, [query]);

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onClose();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const cmd = filtered[selected];
      if (cmd) {
        cmd.action();
        onClose();
      }
    }
  };

  if (!open) return null;

  return (
    <div className="cmdp-backdrop" onClick={onClose}>
      <div className="cmdp-panel" onClick={(e) => e.stopPropagation()}>
        <input
          ref={inputRef}
          className="cmdp-input"
          placeholder="Type a command or search..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKey}
        />
        <div className="cmdp-results">
          {filtered.length === 0 && (
            <div className="cmdp-empty">No commands match "{query}"</div>
          )}
          {filtered.map((cmd, i) => (
            <div
              key={cmd.id}
              className={`cmdp-item ${i === selected ? "selected" : ""}`}
              onMouseEnter={() => setSelected(i)}
              onClick={() => {
                cmd.action();
                onClose();
              }}
            >
              <span className="cmdp-group">{cmd.group}</span>
              <span className="cmdp-label">{cmd.label}</span>
              {cmd.shortcut && <span className="cmdp-shortcut">{cmd.shortcut}</span>}
            </div>
          ))}
        </div>
        <div className="cmdp-footer">
          <span>↑↓ navigate</span>
          <span>↵ select</span>
          <span>esc close</span>
        </div>
      </div>
    </div>
  );
}
