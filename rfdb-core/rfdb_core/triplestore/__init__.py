"""Triplestore seam: the :class:`TripleStore` interface plus its implementations.

Construct one with :func:`build_triplestore`; never instantiate an implementation
directly outside tests, so swapping stores stays a config change.
"""

from __future__ import annotations

from typing import Protocol

from rfdb_core.triplestore.base import TripleStore
from rfdb_core.triplestore.oxigraph import OxigraphStore

__all__ = ["TripleStore", "OxigraphStore", "build_triplestore"]

# Registry of available implementations, keyed by the TRIPLESTORE setting value.
# Adding a store means adding a module and one entry here — no call site changes.
_STORES = {"oxigraph": OxigraphStore}


class StoreSettings(Protocol):
    """The slice of a service's ``Settings`` that :func:`build_triplestore` reads.

    Structural, so neither service has to import from here — both already carry
    these fields via ``rfdb_core.config.BaseServiceSettings``.
    """

    triplestore: str
    data_graph_uri: str
    oxigraph_load_timeout: float

    @property
    def oxigraph_url(self) -> object:
        """Pydantic ``AnyHttpUrl``; cast to ``str`` before use."""


def build_triplestore(settings: StoreSettings) -> TripleStore:
    """Construct the configured triplestore implementation.

    Keyed on ``settings.triplestore`` (env: ``TRIPLESTORE``). Raises on an unknown
    value rather than silently defaulting: a typo in a deployment's env should fail
    loudly at startup, not quietly point the service at the wrong store.

    ``settings`` is passed in rather than imported because each service owns its own
    ``Settings`` subclass — a shared library cannot know which one to reach for.
    """
    name = (settings.triplestore or "").strip().lower()
    try:
        store_cls = _STORES[name]
    except KeyError:
        raise ValueError(
            f"Unknown TRIPLESTORE '{settings.triplestore}'. "
            f"Available: {', '.join(sorted(_STORES))}."
        ) from None

    # Pydantic v2 AnyHttpUrl is not a plain str — cast explicitly so base_url is
    # always a regular string.
    return store_cls(
        str(settings.oxigraph_url),
        settings.data_graph_uri,
        load_timeout=settings.oxigraph_load_timeout,
    )
