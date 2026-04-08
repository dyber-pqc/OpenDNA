import { useEffect, useState } from "react";
import { useYDoc } from "../../collab/useYDoc";
import "./CollabPanel.css";

interface Props {
  roomName: string;
  userName?: string;
  onClose?: () => void;
}

interface ResidueComment {
  text: string;
  author: string;
  ts: number;
}

const CHAINS = ["A", "B", "C", "D", "E", "F"];

export default function CollabPanel({ roomName, userName = "anonymous", onClose }: Props) {
  const { peers, connected, getText, getMap } = useYDoc(roomName, userName);
  const [text, setText] = useState("");
  const [tab, setTab] = useState<"notes" | "comments">("notes");
  const [comments, setComments] = useState<Array<{ key: string; data: ResidueComment }>>([]);
  const [chain, setChain] = useState("A");
  const [position, setPosition] = useState<number>(1);
  const [commentText, setCommentText] = useState("");

  useEffect(() => {
    const y = getText("notes");
    if (!y) return;
    const sync = () => setText(y.toString());
    y.observe(sync);
    sync();
    return () => y.unobserve(sync);
  }, [getText]);

  useEffect(() => {
    const m = getMap("residue_comments");
    if (!m) return;
    const sync = () => {
      const items: Array<{ key: string; data: ResidueComment }> = [];
      m.forEach((value: any, key: string) => {
        items.push({ key, data: value as ResidueComment });
      });
      items.sort((a, b) => b.data.ts - a.data.ts);
      setComments(items);
    };
    m.observe(sync);
    sync();
    return () => m.unobserve(sync);
  }, [getMap]);

  const updateText = (val: string) => {
    const y = getText("notes");
    if (!y) return;
    y.delete(0, y.length);
    y.insert(0, val);
  };

  const addResidueComment = () => {
    const m = getMap("residue_comments");
    if (!m || !commentText.trim()) return;
    const key = `${chain}:${position}`;
    m.set(key, {
      text: commentText.trim(),
      author: userName,
      ts: Date.now(),
    } as ResidueComment);
    setCommentText("");
  };

  const deleteComment = (key: string) => {
    const m = getMap("residue_comments");
    if (!m) return;
    m.delete(key);
  };

  return (
    <div className="collab-panel">
      <div className="cp-header">
        <h2>Real-time collaboration</h2>
        {onClose && <button onClick={onClose}>✕</button>}
      </div>
      <div className="cp-meta">
        <span className={`cp-status ${connected ? "ok" : "bad"}`}>
          {connected ? "● connected" : "○ disconnected"}
        </span>
        <span>Room: <code>{roomName}</code></span>
        <span>Peers: {peers.length}</span>
      </div>
      <div className="cp-peers">
        {peers.map((p, i) => <span key={i} className="cp-peer">👤 {p}</span>)}
      </div>

      <div className="cp-tabs">
        <button
          className={`cp-tab ${tab === "notes" ? "active" : ""}`}
          onClick={() => setTab("notes")}
        >
          Notes
        </button>
        <button
          className={`cp-tab ${tab === "comments" ? "active" : ""}`}
          onClick={() => setTab("comments")}
        >
          Residue comments ({comments.length})
        </button>
      </div>

      {tab === "notes" && (
        <>
          <label className="cp-label">Shared notes (edits sync live)</label>
          <textarea
            className="cp-textarea"
            value={text}
            onChange={e => updateText(e.target.value)}
            placeholder="Type here — every keystroke syncs to all peers via Yjs CRDT…"
            rows={12}
          />
        </>
      )}

      {tab === "comments" && (
        <div className="cp-comments">
          <div className="cp-comment-form">
            <label className="cp-label">Add comment on residue</label>
            <div className="cp-form-row">
              <select value={chain} onChange={e => setChain(e.target.value)}>
                {CHAINS.map(c => <option key={c} value={c}>Chain {c}</option>)}
              </select>
              <input
                type="number"
                min={1}
                value={position}
                onChange={e => setPosition(parseInt(e.target.value) || 1)}
                placeholder="#"
                style={{ width: 70 }}
              />
              <input
                type="text"
                value={commentText}
                onChange={e => setCommentText(e.target.value)}
                placeholder="Comment…"
                style={{ flex: 1 }}
                onKeyDown={e => { if (e.key === "Enter") addResidueComment(); }}
              />
              <button onClick={addResidueComment} disabled={!commentText.trim()}>
                Add
              </button>
            </div>
          </div>

          <div className="cp-comment-list">
            {comments.length === 0 && <em>No residue comments yet.</em>}
            {comments.map(({ key, data }) => (
              <div key={key} className="cp-comment-item">
                <div className="cp-comment-head">
                  <strong>{key}</strong>
                  <span className="cp-comment-author">— {data.author}</span>
                  <span className="cp-comment-ts">
                    {new Date(data.ts).toLocaleString()}
                  </span>
                  <button
                    className="cp-comment-del"
                    onClick={() => deleteComment(key)}
                    title="Delete"
                  >
                    ✕
                  </button>
                </div>
                <div className="cp-comment-text">{data.text}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
