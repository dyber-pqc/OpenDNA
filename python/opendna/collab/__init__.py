"""Real-time co-editing CRDT bridge (Phase 13).

FastAPI WebSocket endpoint that speaks the y-websocket wire protocol for
Yjs documents. Each room corresponds to one project and has a Y.Doc on
the server storing the authoritative state (persisted as a blob in
~/.opendna/crdt/<room>.bin so sessions survive restart).
"""
from .ywebsocket import register_crdt_routes, RoomRegistry, get_registry

__all__ = ["register_crdt_routes", "RoomRegistry", "get_registry"]
