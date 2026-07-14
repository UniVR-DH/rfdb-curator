"""FastAPI application entrypoint for the RossijskijFeatrDB data-entry backend.

Startup sequence (lifespan context manager):
  1. Parse ``schema/schema.ttl`` into a ``SchemaExtractor`` and a
     ``ShaclValidator`` (both read the same file; see note in lifespan).
  2. Instantiate an ``OxigraphClient`` pointing at the running Oxigraph container.
  3. Optionally call ``OxigraphClient.clear_store()`` when ``reset_data_on_startup``
     is ``true`` — wipes all named graphs and the default graph before seeding.
     If this step fails the process aborts; the app must not start with a
     partially-cleared store.
  4. Call ``seed_store()`` to load ``vocab.ttl`` (and optionally ``data.ttl``) into
     Oxigraph.  When ``reset_data_on_startup`` is ``false`` this is idempotent;
     duplicate triples are silently merged by Oxigraph.

All three service objects are stored on ``app.state`` so every route handler
can access them via ``request.app.state.<name>`` without global imports.

Note — startup blocking I/O:
    All startup work (file parsing, HTTP calls to Oxigraph) is synchronous and
    runs on the event loop thread inside the lifespan context manager.  This is
    safe because no requests are served until after ``yield``.  If startup time
    becomes a concern, wrap each blocking call in ``asyncio.to_thread()``.

Note — Oxigraph readiness:
    There is no built-in retry loop waiting for Oxigraph to become available.
    In Docker Compose, use a ``healthcheck`` + ``depends_on: condition:
    service_healthy`` on the Oxigraph service, or add a wait-for-it script,
    to ensure Oxigraph is ready before this process starts.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from rdflib.plugins.parsers.notation3 import BadSyntax

from api.data import router as data_router
from api.entities import router as entities_router
from api.meta import router as meta_router
from api.shapes import router as shapes_router
from api.validate import router as validate_router
from core.config import settings
from core.logging_config import configure_logging
from core.oxigraph_client import OxigraphClient
from core.schema_extractor import SchemaExtractor
from core.seeder import seed_store
from core.shacl_validator import ShaclValidator
from core.validation_merge import _build_shape_dep_graph

# Configure structured file + console logging before anything else runs.
configure_logging(
    settings.log_file,
    settings.log_level,
    truncate_on_startup=settings.truncate_log_on_startup,
    truncate_on_fresh_container_start=settings.truncate_log_on_fresh_container_start,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CORS safety guard
# ---------------------------------------------------------------------------

# The CORS spec forbids allow_credentials=True when any origin is the wildcard
# "*".  If someone accidentally sets CORS_ORIGINS=["*"] in .env the middleware
# will silently misbehave.  Fail loudly at import time instead.
if "*" in settings.cors_origins:
    raise ValueError(
        "CORS_ORIGINS must not contain '*' when allow_credentials=True. "
        "List explicit origins in your .env or docker-compose.yml."
    )


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise shared services before the server starts accepting requests.

    Follows the FastAPI lifespan protocol: everything before ``yield`` runs at
    startup; everything after ``yield`` runs at shutdown (nothing to tear down
    here because Oxigraph runs as a separate container).

    All work is synchronous and blocking — see the module-level note on startup
    blocking I/O for the rationale and a migration path if needed.

    Steps
    -----
    1. Build the in-memory SHACL index (``SchemaExtractor``) and validator
       (``ShaclValidator``).  Both parse ``settings.schema_path`` independently;
       this is a known redundancy that can be eliminated by passing a pre-parsed
       rdflib ``Graph`` to ``ShaclValidator`` once the interface supports it.
    2. Connect to Oxigraph (``OxigraphClient``).
    3. If ``reset_data_on_startup`` is ``True``, wipe the store completely via
       ``clear_store()``.  Any exception here propagates and aborts startup
       intentionally — the app must not serve requests with a partially-cleared
       or unconfirmed store state.
    4. Seed vocab and optional test data via ``seed_store()``.
    5. Store the seed report on ``app.state`` for the ``/health`` endpoint.
    """
    logger.info("Starting up RossijskijFeatrDB backend…")

    # -- 1. Schema services ------------------------------------------------
    # NOTE: SchemaExtractor and ShaclValidator both open and parse schema_path
    # independently.  Consolidate if schema parsing becomes a bottleneck.
    try:
        app.state.schema_extractor = SchemaExtractor(settings.schema_path)
        app.state.shape_dep_graph = _build_shape_dep_graph(app.state.schema_extractor)
        app.state.shacl_validator = ShaclValidator(settings.schema_path)
    except BadSyntax as exc:
        logger.error(
            "Invalid Turtle syntax in schema '%s'. Details: %s",
            settings.schema_path,
            exc,
            exc_info=True,
        )
        raise
    logger.info("Schema loaded from '%s'.", settings.schema_path)

    # -- 2. Oxigraph client ------------------------------------------------
    # Pydantic v2 AnyHttpUrl is not a plain str — cast explicitly so
    # OxigraphClient.base_url is always a regular string.
    app.state.oxigraph = OxigraphClient(
        str(settings.oxigraph_url),
        settings.data_graph_uri,
    )
    logger.info("OxigraphClient initialised (base_url='%s').", settings.oxigraph_url)

    # -- 3. Optional store reset -------------------------------------------
    # If Oxigraph is not yet reachable (e.g. still starting in Docker Compose)
    # clear_store() will raise and abort startup.  Use a readiness dependency
    # (healthcheck + depends_on) in docker-compose.yml to prevent this.
    if settings.reset_data_on_startup:
        logger.warning(
            "reset_data_on_startup=true — clearing all triples from Oxigraph. "
            "This is a destructive operation; do NOT enable in production."
        )
        app.state.oxigraph.clear_store()
        logger.warning("Oxigraph store cleared successfully.")

    # -- 4. Seed store -----------------------------------------------------
    seed_report = seed_store(
        oxigraph=app.state.oxigraph,
        vocab_paths=settings.vocab_paths,
        test_data_path=settings.data_path,
        seed_vocab=settings.seed_vocab_on_startup,
        seed_test_data=settings.seed_test_data_on_startup,
    )
    app.state.seed_report = seed_report
    logger.info("Seed complete: %s", seed_report)

    logger.info("Startup complete — accepting requests.")
    yield
    # Shutdown: nothing to tear down (Oxigraph runs as a separate container).


# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RossijskijFeatrDB Data Entry API",
    description="SHACL-driven data entry backend for the Russian Theatre DB.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(shapes_router, prefix="/api", tags=["shapes"])
app.include_router(data_router, prefix="/api", tags=["data"])
app.include_router(entities_router, prefix="/api", tags=["entities"])
app.include_router(validate_router, prefix="/api", tags=["validation"])
app.include_router(meta_router, prefix="/api", tags=["meta"])


# ---------------------------------------------------------------------------
# Request / response logging middleware
# ---------------------------------------------------------------------------

_req_logger = logging.getLogger("api.access")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every HTTP request with method, path, status code, and duration.

    Emits one structured log line per request to both the console and the
    JSON-lines log file, e.g.::

        {"ts": "…", "level": "INFO", "logger": "api.access",
         "msg": "GET /api/data/list 200", "method": "GET",
         "path": "/api/data/list", "status": 200, "ms": 8}
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


# ---------------------------------------------------------------------------
# Meta routes
# ---------------------------------------------------------------------------


@app.get("/health", tags=["meta"])
def health():
    """Liveness and readiness check consumed by Docker and the frontend status bar.

    This route is intentionally synchronous: ``OxigraphClient.health()`` uses
    a synchronous ``httpx.Client``, and FastAPI correctly runs sync routes in a
    threadpool so the event loop is not blocked.

    Returns:
        A JSON object with three keys:

        - ``status``: always ``"ok"`` when the application process is alive
          (Oxigraph may still be down).
        - ``oxigraph``: ``"up"`` when Oxigraph responds with HTTP < 500,
          ``"down"`` otherwise.
        - ``seed``: the seed report dict produced during startup, or ``null``
          if startup has not yet completed (should not occur in normal operation).
    """
    ox_ok = app.state.oxigraph.health()
    return {
        "status": "ok",
        "oxigraph": "up" if ox_ok else "down",
        "seed": getattr(app.state, "seed_report", None),
    }
