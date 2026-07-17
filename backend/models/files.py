"""Response models for the source digital-copy (PDF) file API.

The file node itself is written directly by ``api/files.py`` (bytes are
out-of-band), so there is no create *request* model here — uploads arrive as
multipart form data. These models describe what the API returns.
"""

from __future__ import annotations

from pydantic import BaseModel

# Vocabulary the digital-copy machinery owns: the anchor shape and the
# schema.org terms written for each file node. How a node links to a parent
# (predicate + parent class) is resolved from the schema at runtime — never
# hardcoded. Lives here (not api/files.py) so api/data.py can import it
# without an import cycle.
DIGITAL_COPY_SHAPE_ID = "https://rosfeatr.eu/rdf/schema/DigitalCopyShape"
SCHEMA_NS = "http://schema.org/"
SCHEMA_DIGITAL_DOCUMENT = SCHEMA_NS + "DigitalDocument"
SCHEMA_NAME = SCHEMA_NS + "name"
SCHEMA_ENCODING_FORMAT = SCHEMA_NS + "encodingFormat"
SCHEMA_CONTENT_URL = SCHEMA_NS + "contentUrl"
SCHEMA_CONTENT_SIZE = SCHEMA_NS + "contentSize"
SCHEMA_SHA256 = SCHEMA_NS + "sha256"
SCHEMA_NUMBER_OF_PAGES = SCHEMA_NS + "numberOfPages"

# Server-derived metadata terms: replaced (staged) or stripped (registered)
# by the write path in api/data.py — the payload's values are UI prefill only.
SCHEMA_DERIVED_TERMS = (
    SCHEMA_ENCODING_FORMAT,
    SCHEMA_CONTENT_URL,
    SCHEMA_CONTENT_SIZE,
    SCHEMA_SHA256,
    SCHEMA_NUMBER_OF_PAGES,
)


class DigitalCopy(BaseModel):
    """One staged/stored PDF copy (mirrors ``rfdbs:DigitalCopyShape``).

    Returned by ``POST /api/files/staged`` as the prefill for the form's
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
