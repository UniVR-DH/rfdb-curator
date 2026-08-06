"""Service-local configuration for the read backend.

Modules
-------
config  The reader's settings instance — plain ``BaseServiceSettings``, since
        every field it needs is already in the shared base.

Everything else this service uses (triplestore seam, schema extractor, prefix
map, object storage, IRI guard, file-state snapshot, logging, app wiring) comes
from ``rfdb_core``. There is deliberately no local business logic: a read service
that grows its own ``core/`` is a read service that has started to diverge.
"""
