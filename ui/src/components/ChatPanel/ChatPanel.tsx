import { useState } from "react";
import "./ChatPanel.css";

interface ChatPanelProps {
  onChat: (message: string) => Promise<string>;
}

interface Message {
  role: "user" | "assistant";
  content: string;
}

function ChatPanel({ onChat }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        'Welcome! Try: "fold MKTVRQERLKSIVRILER", "score MKTVRQERLK", "mutate G45D", or "help".',
    },
  ]);
  const [thinking, setThinking] = useState(false);

  const handleSubmit = async () => {
    if (!input.trim() || thinking) return;
    const userMessage = input.trim();
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setInput("");
    setThinking(true);
    try {
      const reply = await onChat(userMessage);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } finally {
      setThinking(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-message ${msg.role}`}>
            <span className="chat-role">
              {msg.role === "user" ? "You" : "OpenDNA"}
            </span>
            <span className="chat-content">{msg.content}</span>
          </div>
        ))}
        {thinking && (
          <div className="chat-message assistant">
            <span className="chat-role">OpenDNA</span>
            <span className="chat-content">thinking...</span>
          </div>
        )}
      </div>
      <div className="chat-input-area">
        <input
          className="chat-input"
          placeholder='Try "fold MKTVRQERLK" or "help"'
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={thinking}
        />
        <button className="chat-send" onClick={handleSubmit} disabled={thinking}>
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatPanel;
