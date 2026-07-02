"""
Application settings loaded exclusively from environment variables or a ``.env`` file.

No default values are hardcoded here.  Every setting MUST be supplied through:

  - A ``.env`` file placed next to this module (copy ``.env.example`` to ``.env``).
  - Environment variables injected by Docker Compose or the host shell.

This ensures a single source of truth per deployment: the ``.env`` file for local
development, the ``environment:`` block in ``docker-compose.yml`` for Docker.

See ``README.md`` for a full reference of every variable.
"""

from __future__ import annotations

import json

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object; instantiated once as a module-level singleton.

    All fields are **required** — no Python defaults are defined.  Missing variables
    cause a ``ValidationError`` at startup with a clear message identifying which
    variable is absent.

    Attributes:
        oxigraph_url: Base URL of the Oxigraph HTTP endpoint (no trailing slash).
            Accepts both ``http://`` and ``https://`` schemes.
            Example: ``http://localhost:7878``

        data_graph_uri: Named graph URI where all instance data is stored and
            queried.  All SPARQL reads use ``FROM <uri>`` and all Turtle loads
            use ``?graph=<uri>`` via the Graph Store Protocol.
            Example: ``https://rfdb.it/graph/data``

        schema_path: Path to the SHACL schema Turtle file used by
            ``SchemaExtractor`` and ``ShaclValidator``.  Relative to the backend
            working directory inside the container.
            Example: ``schema/schema.ttl``

        vocab_path: Path to ``vocab.ttl`` loaded into Oxigraph on every startup
            when ``seed_vocab_on_startup`` is ``true``.
            Example: ``data/vocab.ttl``

        data_path: Path to ``data.ttl`` — test fixture data, seeded only when
            ``seed_test_data_on_startup`` is ``true``.
            Example: ``data/data.ttl``

        reset_data_on_startup: Drop and re-seed all instance data at startup.
            When ``true``, the named graph identified by ``data_graph_uri`` is
            cleared before any seed files are loaded.  Should be ``false`` in
            production to avoid accidental data loss.

        seed_vocab_on_startup: Load ``vocab_path`` into Oxigraph at startup.
            Should be ``true`` in all environments so that controlled vocabulary
            terms are always present.

        seed_test_data_on_startup: Load ``data_path`` at startup.  Set to
            ``true`` only in development/test environments; must be ``false``
            in production.

        read_only: Disable all mutating API operations when ``true``.
            Write and delete routes return HTTP 403 with a clear message.
            Useful for demo or presentation mode.

        cors_origins: List of allowed CORS origins.  Supplied as a JSON array
            string in the ``.env`` file or Docker Compose ``environment:`` block
            and automatically parsed by the ``parse_cors`` validator.
            Example: ``["http://localhost:5173", "http://localhost:3000"]``
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------ #
    # Oxigraph / SPARQL                                                    #
    # ------------------------------------------------------------------ #

    oxigraph_url: AnyHttpUrl
    """Base URL of the Oxigraph HTTP endpoint.  ``AnyHttpUrl`` accepts both
    ``http://`` and ``https://`` schemes, so no union type is required."""

    data_graph_uri: str
    """Named graph URI used for all SPARQL reads (``FROM <uri>``) and
    Graph Store Protocol writes (``?graph=<uri>``)."""

    # ------------------------------------------------------------------ #
    # File paths (relative to the backend working directory)              #
    # ------------------------------------------------------------------ #

    schema_path: str
    """Path to the SHACL schema Turtle file (e.g. ``schema/schema.ttl``)."""

    vocab_path: str
    """Path to the vocabulary Turtle file (e.g. ``data/vocab.ttl``)."""

    data_path: str
    """Path to the test-fixture Turtle file (e.g. ``data/data.ttl``)."""

    # ------------------------------------------------------------------ #
    # Startup behaviour                                                    #
    # ------------------------------------------------------------------ #

    reset_data_on_startup: bool
    """When ``true``, clears the named graph before seeding.  Keep ``false``
    in production to prevent accidental data loss."""

    seed_vocab_on_startup: bool
    """When ``true``, loads ``vocab_path`` into Oxigraph at every startup.
    Recommended ``true`` in all environments."""

    seed_test_data_on_startup: bool
    """When ``true``, loads ``data_path`` at startup.  Should only be
    ``true`` in development or test environments."""

    read_only: bool = False
    """When ``true``, disable write/delete API routes and allow only reads.
    Intended for demo/presentation environments."""

    # ------------------------------------------------------------------ #
    # HTTP / CORS                                                          #
    # ------------------------------------------------------------------ #

    cors_origins: list[str]
    """Allowed CORS origins.  Parsed from a JSON array string by
    :meth:`parse_cors` so it works transparently in both ``.env`` files
    and Docker Compose ``environment:`` blocks."""

    # ------------------------------------------------------------------ #
    # Logging                                                              #
    # ------------------------------------------------------------------ #

    log_file: str = "logs/app.jsonl"
    """Path to the structured JSON-lines log file.
    Parent directories are created automatically at startup.
    Default: ``logs/app.jsonl`` (relative to the backend working directory)."""

    log_level: str = "INFO"
    """Minimum log level for both the file and console handlers.
    Accepted values: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``."""

    truncate_log_on_startup: bool = False
    """When ``true``, truncate ``log_file`` on backend process startup.
    Useful in local Docker workflows where old JSON-lines logs should not
    accumulate across rebuilds/restarts."""

    truncate_log_on_fresh_container_start: bool = False
    """When ``true``, truncate ``log_file`` only on first startup of a
    freshly created container (for example after ``docker compose up --build``).
    Subsequent restarts of the same container keep appending to the file."""

    # ------------------------------------------------------------------ #
    # Validators                                                           #
    # ------------------------------------------------------------------ #

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        """Accept ``CORS_ORIGINS`` as a JSON array string or a plain Python list.

        Docker Compose and ``.env`` files both supply environment variables as
        raw strings.  This validator transparently handles either form:

        - String (from env): ``'["http://localhost:5173"]'`` → parsed via
          :func:`json.loads`.
        - List (from Python tests or programmatic instantiation): passed
          through unchanged.

        Args:
            v: Raw value coming from the environment or a direct constructor
               call.

        Returns:
            A proper Python ``list[str]`` of origin URLs.

        Raises:
            ValueError: If ``v`` is a string that cannot be parsed as JSON.
        """
        if isinstance(v, str):
            return json.loads(v)
        return v


# --------------------------------------------------------------------------- #
# Module-level singleton                                                        #
# --------------------------------------------------------------------------- #

settings = Settings()
"""Module-level singleton consumed by the rest of the application.

Import and use as::

    from config import settings

    print(settings.oxigraph_url)
"""
