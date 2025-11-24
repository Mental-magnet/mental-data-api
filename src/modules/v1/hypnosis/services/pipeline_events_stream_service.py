import asyncio
import logging
import typing
from collections import defaultdict, deque

import fastapi

from ..schemas.pipeline_schema import LoggingSchema

LOGGER = logging.getLogger("uvicorn").getChild("v1.hypnosis.pipeline.events")

_EVENT_BUFFER_MAX_LENGTH = 50
_ALL_ARTIFACT_KEY = "ALL"

_eventBuffer: dict[str, deque[LoggingSchema]] = defaultdict(
    lambda: deque(maxlen=_EVENT_BUFFER_MAX_LENGTH),
)
_activeConnections: dict[str, set[fastapi.WebSocket]] = defaultdict(set)
_bufferLock = asyncio.Lock()
_connectionsLock = asyncio.Lock()


def normalizeArtifact(value: typing.Optional[str]) -> str:
    """Normaliza nombres de artefacto para storage interno en buffers."""
    if isinstance(value, str) and value.strip():
        return value.upper()
    return "UNKNOWN"


def normalizeArtifactFilter(value: typing.Optional[str]) -> str:
    """Devuelve la clave de filtro usada para asignar conexiones a un canal."""
    if isinstance(value, str) and value.strip():
        return value.upper()
    return _ALL_ARTIFACT_KEY


async def snapshotEvents(artifact: str) -> list[LoggingSchema]:
    """Obtiene una copia de los eventos recientes para un artefacto o para todos."""
    async with _bufferLock:
        if artifact == _ALL_ARTIFACT_KEY:
            aggregated: list[LoggingSchema] = []
            for events in _eventBuffer.values():
                aggregated.extend(event.model_copy(deep=True) for event in events)
            aggregated.sort(key=lambda evt: getattr(evt, "timestamp", 0))
            return aggregated
        return [event.model_copy(deep=True) for event in _eventBuffer.get(artifact, [])]


async def registerConnection(artifact: str, websocket: fastapi.WebSocket) -> None:
    """Asocia un websocket a un artefacto para recibir eventos en vivo."""
    async with _connectionsLock:
        _activeConnections[artifact].add(websocket)


async def removeConnection(artifact: str, websocket: fastapi.WebSocket) -> None:
    """Elimina la conexión registrada y limpia el canal si queda vacío."""
    async with _connectionsLock:
        sockets = _activeConnections.get(artifact)
        if sockets is None:
            return
        sockets.discard(websocket)
        if not sockets:
            _activeConnections.pop(artifact, None)


async def _getConnections(artifact: str) -> list[fastapi.WebSocket]:
    """Devuelve una lista desconectada de websockets para el artefacto dado."""
    async with _connectionsLock:
        return list(_activeConnections.get(artifact, set()))


async def dispatchRealtimeEvent(event: LoggingSchema) -> None:
    """Bufferiza el evento y lo transmite a todos los sockets interesados."""
    artifact = normalizeArtifact(event.receivedArtifact)
    eventCopy = event.model_copy(deep=True)

    async with _bufferLock:
        _eventBuffer[artifact].append(eventCopy)

    payload = eventCopy.model_dump(mode="json", by_alias=True, round_trip=True)

    directConnections = await _getConnections(artifact)
    broadcastConnections = await _getConnections(_ALL_ARTIFACT_KEY)

    targets: list[fastapi.WebSocket] = []
    seen = set()
    for socket in directConnections + broadcastConnections:
        if id(socket) in seen:
            continue
        seen.add(id(socket))
        targets.append(socket)

    if not targets:
        return

    disconnected: list[tuple[str, fastapi.WebSocket]] = []
    for socket in targets:
        try:
            await socket.send_json(payload)
        except (fastapi.WebSocketDisconnect, RuntimeError):
            disconnected.append(
                (artifact if socket in directConnections else _ALL_ARTIFACT_KEY, socket)
            )
        except Exception:  # pragma: no cover - diagnostic logging only
            LOGGER.exception("[PIPELINE][EVENTS] Failed to send realtime event")
            disconnected.append(
                (artifact if socket in directConnections else _ALL_ARTIFACT_KEY, socket)
            )

    if disconnected:
        for artifactKey, socket in disconnected:
            await removeConnection(artifactKey, socket)
