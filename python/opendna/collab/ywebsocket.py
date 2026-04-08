"""y-websocket compatible server for Yjs CRDT documents.

The y-websocket wire protocol (v1) is very small. Each message is:
    [message_type_byte, ...payload]

Two message types matter:
    0 = sync    (followed by sync sub-type varint + Y.js update/vector)
    1 = awareness (followed by the awareness update blob)

For this initial implementation we operate as a pure **relay + buffer**:
  - Keep an in-memory buffer of recent updates per room
  - Rebroadcast every non-awareness message to all other peers in the room
  - Persist updates as an append-only blob log on disk
  - On new client connect: replay the persisted log so they catch up

This matches y-websocket's reference behaviour for the cases where the
server does not need to inspect document contents (we don't). Going through
y-py for semantic awareness can be added later without changing the API.
"""
from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect


def _crdt_dir() -> Path:
    p = Path(os.environ.get("OPENDNA_CRDT_DIR", Path.home() / ".opendna" / "crdt"))
    p.mkdir(parents=True, exist_ok=True)
    return p


class Room:
    def __init__(self, name: str):
        self.name = name
        self.clients: Set[WebSocket] = set()
        self.lock = asyncio.Lock()
        self.persist_path = _crdt_dir() / f"{name}.ylog"

    async def add(self, ws: WebSocket) -> None:
        async with self.lock:
            self.clients.add(ws)

    async def remove(self, ws: WebSocket) -> None:
        async with self.lock:
            self.clients.discard(ws)

    async def broadcast(self, data: bytes, sender: WebSocket) -> None:
        async with self.lock:
            dead: list[WebSocket] = []
            for c in self.clients:
                if c is sender:
                    continue
                try:
                    await c.send_bytes(data)
                except Exception:
                    dead.append(c)
            for d in dead:
                self.clients.discard(d)

    def persist(self, data: bytes) -> None:
        # Append-only log: 4-byte length prefix, then bytes
        try:
            with self.persist_path.open("ab") as f:
                f.write(len(data).to_bytes(4, "big"))
                f.write(data)
        except Exception:
            pass

    def replay(self) -> list[bytes]:
        out: list[bytes] = []
        if not self.persist_path.exists():
            return out
        try:
            with self.persist_path.open("rb") as f:
                while True:
                    hdr = f.read(4)
                    if len(hdr) < 4:
                        break
                    n = int.from_bytes(hdr, "big")
                    data = f.read(n)
                    if len(data) == n:
                        out.append(data)
        except Exception:
            pass
        return out


class RoomRegistry:
    def __init__(self):
        self._rooms: Dict[str, Room] = {}
        self._lock = asyncio.Lock()

    async def get(self, name: str) -> Room:
        async with self._lock:
            if name not in self._rooms:
                self._rooms[name] = Room(name)
            return self._rooms[name]

    def list_rooms(self) -> list[dict]:
        return [
            {
                "name": r.name,
                "clients": len(r.clients),
                "log_size": r.persist_path.stat().st_size if r.persist_path.exists() else 0,
            }
            for r in self._rooms.values()
        ]


_registry: RoomRegistry | None = None


def get_registry() -> RoomRegistry:
    global _registry
    if _registry is None:
        _registry = RoomRegistry()
    return _registry


def register_crdt_routes(app: FastAPI) -> None:
    @app.websocket("/v1/crdt/{room_name}")
    async def crdt_ws(websocket: WebSocket, room_name: str):
        await websocket.accept()
        registry = get_registry()
        room = await registry.get(room_name)
        await room.add(websocket)
        # Replay persisted state so this peer catches up
        for blob in room.replay():
            try:
                await websocket.send_bytes(blob)
            except Exception:
                break
        try:
            while True:
                msg = await websocket.receive()
                if "bytes" in msg and msg["bytes"] is not None:
                    data = msg["bytes"]
                    # Persist sync messages (type byte 0), skip pure awareness (1)
                    if data and data[0] == 0:
                        room.persist(data)
                    await room.broadcast(data, websocket)
                elif "text" in msg and msg["text"] is not None:
                    # Text ping/pong support
                    await websocket.send_text(msg["text"])
        except WebSocketDisconnect:
            pass
        finally:
            await room.remove(websocket)

    @app.get("/v1/crdt")
    def list_crdt_rooms():
        return {"rooms": get_registry().list_rooms()}
