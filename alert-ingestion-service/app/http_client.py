"""Shared httpx.AsyncClient for inter-service communication.

A single persistent client is created on application startup and closed on
shutdown, avoiding the overhead of establishing a new TCP connection for
every outgoing request.
"""

import httpx

_client: httpx.AsyncClient | None = None
_default_timeout: float = 10.0


async def init_http_client(timeout: float = 10.0) -> None:
    """Create the shared async HTTP client (called at startup)."""
    global _client, _default_timeout
    _default_timeout = timeout
    _client = httpx.AsyncClient(timeout=timeout)


async def close_http_client() -> None:
    """Gracefully close the client (called at shutdown)."""
    global _client
    if _client:
        await _client.aclose()
        _client = None


def get_http_client() -> httpx.AsyncClient:
    """Return the shared client.  Falls back to a fresh client if not
    initialised (e.g. during unit tests)."""
    if _client is None:
        return httpx.AsyncClient(timeout=_default_timeout)
    return _client
