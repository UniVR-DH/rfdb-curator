"""Response models for the source digital-copy (PDF) file API.

The file node itself is written directly by ``api/files.py`` (bytes are
out-of-band), so there is no create *request* model here — uploads arrive as
multipart form data. These models describe what the API returns.
"""

from __future__ import annotations

from pydantic import BaseModel

# The digital-copy vocabulary constants that used to live here moved to
# rfdb_core.vocab — schema_extractor (in rfdb-core) needs them, and so will the
# reader service, so a service-local home would have inverted the dependency.
# Import them from there; this module keeps only the response model.


class DigitalCopy(BaseModel):
    """One staged/stored PDF copy (mirrors ``rfdbs:DigitalCopyShape``).

    Returned by ``POST /api/v1/curator/files/staged`` as the prefill for the form's
    file field; the same values later travel inside the JSON-LD payload as a
    bridge node (and are re-derived server-side at write time).

    Attributes:
        id: Full IRI of the ``schema:DigitalDocument`` node.
        fileId: Local id (last path segment of ``id``), used in file URLs.
        name: Original uploaded filename (``schema:name``).
        contentUrl: Stable backend-relative download path (``schema:contentUrl``).
        contentSize: File size in bytes (``schema:contentSize``).
        sha256: SHA-256 checksum of the content (``schema:sha256``).
        numberOfPages: Page count from pypdf, or ``None`` if unparseable.
        encodingFormat: Always ``application/pdf``.
    """

    id: str
    fileId: str
    name: str
    contentUrl: str
    contentSize: int
    sha256: str
    numberOfPages: int | None = None
    encodingFormat: str = "application/pdf"
