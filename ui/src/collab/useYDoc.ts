import { useEffect, useRef, useState } from "react";
import * as Y from "yjs";
import { WebsocketProvider } from "y-websocket";

/**
 * Join a Yjs room for real-time co-editing.
 *
 * The server endpoint is `ws://localhost:8765/v1/crdt/<room>`. Returns the
 * Y.Doc, a shared Y.Text, a Y.Map for structured state, and the list of
 * currently connected peer names from the awareness protocol.
 */
export function useYDoc(roomName: string, userName = "anonymous") {
  const docRef = useRef<Y.Doc | null>(null);
  const providerRef = useRef<WebsocketProvider | null>(null);
  const [peers, setPeers] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!roomName) return;
    const doc = new Y.Doc();
    const provider = new WebsocketProvider(
      "ws://localhost:8765/v1/crdt",
      roomName,
      doc,
      { connect: true },
    );
    provider.awareness.setLocalStateField("user", { name: userName, color: "#7aa2ff" });

    const onChange = () => {
      const states = Array.from(provider.awareness.getStates().values()) as any[];
      setPeers(states.map(s => s?.user?.name).filter(Boolean));
    };
    provider.awareness.on("change", onChange);
    provider.on("status", (e: any) => setConnected(e.status === "connected"));

    docRef.current = doc;
    providerRef.current = provider;
    onChange();

    return () => {
      provider.awareness.off("change", onChange);
      provider.destroy();
      doc.destroy();
      docRef.current = null;
      providerRef.current = null;
    };
  }, [roomName, userName]);

  return {
    doc: docRef.current,
    peers,
    connected,
    getText: (key: string) => docRef.current?.getText(key) as Y.Text | undefined,
    getMap: (key: string) => docRef.current?.getMap(key) as Y.Map<any> | undefined,
  };
}
