"""Cross-cutting FastAPI wiring shared by every service in the stack.

The curator (writer) and dataexplorer (reader) are separate apps with disjoint
route sets, but they must behave identically at the edges: the same CORS policy,
the same access-log line, the same 503 when object storage is unreachable. Those
three concerns are the whole of this module.

**Requires the ``web`` extra** (``rfdb-core[web]``). It is the only module here
that imports a web framework; the rest of the library is deliberately
framework-free so nothing forces a service to inherit another's web stack. An
import of this module without the extra installed fails on ``import fastapi``,
which is the intended signal.

What stays in each service: its own ``FastAPI(...)`` construction (title,
version, lifespan), its router includes, and its ``/health`` payload — all three
genuinely differ between the writer and the reader.
"""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from rfdb_core.file_storage import StorageError, StorageNotInitialized

logger = logging.getLogger(__name__)

# Access log stays on this fixed name across services so one log pipeline can
# select request lines regardless of which backend emitted them.
_req_logger = logging.getLogger("api.access")


# ---------------------------------------------------------------------------
# Storage-error copy
# ---------------------------------------------------------------------------

# Client-facing 503 details, one per StorageError family. Deliberately generic
# (no internals); the operator hint goes to the service log only.
_NOT_INITIALIZED_DETAIL = (
    "The document-storage component is not correctly initialized. Please consult the backend logs."
)
_UNAVAILABLE_DETAIL = (
    "The document-storage service is temporarily unavailable. Please try again; "
    "if it persists, consult the backend logs."
)

# Operator hints (service log only) — the obvious first thing to try per family.
_NOT_INITIALIZED_HINT = (
    "Most common cause: the Garage bucket/access key are not initialized on this "
    "volume (e.g. a fresh volume or `docker compose down -v`).\n"
    "  Obvious fix to try first — (re)run the idempotent bootstrap:\n"
    "      ./scripts/garage-init.sh        (dev, from the repo root)\n"
    "  It imports the predefined S3 key from .env and grants it on the bucket."
)
_UNAVAILABLE_HINT = (
    "Storage endpoint unreachable or erroring. Check the Garage service is up and "
    "reachable at S3_ENDPOINT:\n"
    "      docker compose ps garage && docker compose logs --tail=50 garage"
)


def assert_no_wildcard_cors(origins: list[str]) -> None:
    """Fail loudly at import time if the CORS origin list contains ``"*"``.

    The CORS spec forbids ``allow_credentials=True`` alongside a wildcard
    origin, and the middleware responds by silently misbehaving rather than
    erroring. A stray ``CORS_ORIGINS=["*"]`` in a ``.env`` would therefore
    produce a subtly broken deployment; this turns it into a startup crash.

    Raises:
        ValueError: when ``"*"`` appears in ``origins``.
    """
    if "*" in origins:
        raise ValueError(
            "CORS_ORIGINS must not contain '*' when allow_credentials=True. "
            "List explicit origins in your .env or docker-compose.yml."
        )


class _HeadAsGetMiddleware:
    """Answer ``HEAD`` on every ``GET`` route instead of a blanket 405.

    Neither Starlette's ``APIRouter`` nor FastAPI adds ``HEAD`` to a route
    declared with ``@router.get(...)``, so link checkers and harvesters that
    probe a URL with ``HEAD`` before fetching it — the ``/rdf/`` identifiers
    especially — see every route reject them. Fixing this per-route would mean
    touching all 21 routes across both services for the same one-line reason,
    so it is handled once, here, at the ASGI level: the request is rewritten to
    ``GET`` for the duration of the call, and only the outgoing body bytes are
    dropped, so headers (including ``content-length``) stay exactly what a
    ``GET`` would have sent, per HTTP's definition of ``HEAD``.

    Plain ASGI callable rather than ``BaseHTTPMiddleware``: the latter buffers
    the whole response before it can inspect it, which would defeat streaming
    responses (e.g. file downloads). Rewriting ``scope`` and filtering
    ``http.response.body`` messages works unchanged for both.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "HEAD":
            await self.app(scope, receive, send)
            return

        scope = {**scope, "method": "GET"}

        async def send_wrapper(message):
            if message["type"] == "http.response.body":
                message = {**message, "body": b""}
            await send(message)

        await self.app(scope, receive, send_wrapper)


def configure_app(app: FastAPI, *, cors_origins: list[str]) -> FastAPI:
    """Attach the cross-cutting middleware and error handling every service needs.

    Call once, immediately after constructing the ``FastAPI`` instance and
    before including routers.

    Applies, in order:

    1. :func:`assert_no_wildcard_cors` on ``cors_origins``.
    2. :class:`_HeadAsGetMiddleware`, so every ``GET`` route also answers ``HEAD``.
    3. ``CORSMiddleware`` with credentials enabled.
    4. A ``StorageError`` → 503 handler, branched by family (see
       :func:`_storage_error_handler`).
    5. The ``api.access`` request/response log line.

    Args:
        app: The service's FastAPI instance.
        cors_origins: Explicit allowed origins; must not contain ``"*"``.

    Returns:
        ``app``, so this can be chained onto the construction expression.

    Note — middleware order:
        ``_HeadAsGetMiddleware`` is added first, which makes it the *innermost*
        layer (Starlette builds its stack so that the last-registered middleware
        runs first, i.e. outermost) — closest to the router, so CORS and the
        access log still see the request's real ``HEAD`` method rather than the
        rewritten ``GET``. CORS is registered before the access log for the same
        reason: the access log stays the outer layer, logging the status code the
        client actually sees, including CORS preflight rejections. Reordering any
        of these changes what gets logged or matched.
    """
    assert_no_wildcard_cors(cors_origins)

    app.add_middleware(_HeadAsGetMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(StorageError, _storage_error_handler)
    app.middleware("http")(_log_requests)
    return app


async def _storage_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Turn any object-storage failure into a clean 503, branched by family.

    The seam (``rfdb_core.file_storage``) raises a ``StorageError`` subclass —
    never a raw boto exception — so the client sees one clear message while the
    full cause plus the family-specific first-fix hint go to the service log.
    Two families need different action:

    * :class:`StorageNotInitialized` — bucket/key/creds not set up → (re)run the
      bootstrap; retrying won't help.
    * everything else (:class:`StorageUnavailable`) — endpoint down / transient →
      check the service is running; may succeed on retry.

    Covers every route that touches storage: upload/stage and the write-path
    promotion in the curator, the download stream and file stats in the reader.

    Note:
        Typed ``exc: Exception`` rather than ``StorageError`` to match the
        signature Starlette's handler registry expects; it is only ever invoked
        for ``StorageError`` and its subclasses.
    """
    not_initialized = isinstance(exc, StorageNotInitialized)
    detail = _NOT_INITIALIZED_DETAIL if not_initialized else _UNAVAILABLE_DETAIL
    hint = _NOT_INITIALIZED_HINT if not_initialized else _UNAVAILABLE_HINT
    logger.error(
        "Object storage error on %s %s: %s\n  %s",
        request.method,
        request.url.path,
        exc,
        hint,
        exc_info=exc,
    )
    return JSONResponse(status_code=503, content={"detail": detail})


async def _log_requests(request: Request, call_next):
    """Log every HTTP request with method, path, status code, and duration.

    Emits one structured log line per request to both the console and the
    JSON-lines log file, e.g.::

        {"ts": "…", "level": "INFO", "logger": "api.access",
         "msg": "GET /api/v1/dataexplorer/entities 200", "method": "GET",
         "path": "/api/v1/dataexplorer/entities", "status": 200, "ms": 8}
    """
    t0 = time.perf_counter()
    response = await call_next(request)
    ms = round((time.perf_counter() - t0) * 1000)
    _req_logger.info(
        "%s %s %s",
        request.method,
        request.url.path,
        response.status_code,
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": ms,
        },
    )
    return response
