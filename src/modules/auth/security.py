"""Definitions of FastAPI security schemes used across the API."""

from typing import Optional
from fastapi import Request, WebSocket
from fastapi.security import OAuth2PasswordBearer

from .guards.token_guard import PUBLIC_PATH_PREFIXES as GUARDED_PUBLIC_PATHS


class SafeOAuth2PasswordBearer(OAuth2PasswordBearer):
    """
    OAuth2PasswordBearer that supports both Request and WebSocket.
    
    Standard OAuth2PasswordBearer fails on WebSockets because it expects a 'request' argument
    which is not provided in WebSocket dependency injection context by default.
    """
    async def __call__(self, request: Request = None, websocket: WebSocket = None) -> Optional[str]:
        if request:
            if request.url and _is_public_path(request.url.path):
                return None
            return await super().__call__(request)
        # For WebSockets, we skip this check here as it's handled by the middleware/guard
        # or manual token extraction.
        return None


# OAuth2 password flow so Swagger UI exposes the Authorize modal for bearer tokens.
oauth2Scheme = SafeOAuth2PasswordBearer(
    tokenUrl="/auth/login",
    scopes={
        "default": "Acceso a los endpoints protegidos de la API.",
    },
)

__all__ = ["oauth2Scheme"]


def _is_public_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in GUARDED_PUBLIC_PATHS)
