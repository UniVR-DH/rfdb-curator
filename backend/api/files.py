"""Upload-first digital-copy routes: stage a PDF, download a stored one.

A digital copy is a bridge node whose fields are machine-filled. The flow
(see ``.temp/temp-upload-first-files-*.md``):

1. ``POST /api/files/staged`` — parent-agnostic. Sniffs the PDF, computes
   sha256/size/pages, stores the bytes under ``staged/File_{8hex}.pdf`` and
   returns the prefilled ``schema:DigitalDocument`` node. The form shows it as
   a read-only bridge entry — on unsaved forms too.
2. The node travels inside the normal JSON-LD payload of ``POST /api/data``
   under whatever predicate the *schema* declares (any shape with a property
   whose ``sh:node`` targets ``DigitalCopyShape`` gets the widget). The write
   path re-derives the metadata server-side and promotes the object to
   ``registered/`` on persist — see ``api/data.py``.
3. ``GET /api/files/{file_id}`` streams the bytes back (registered first,
   then staged, so pre-submit previews work).

Abandoned staged files and unreferenced registered ones are collected by
``scripts/cleanup_files.py`` — RDF is the source of truth; storage is
reconciled against it, never the other way around.

Downloads are proxied through the backend (never a direct browser→Garage
path) so Garage can stay on the internal network in production.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import uuid

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from api.data import _assert_writable_mode
from core.blank_node_handler import RFDB_BASE
from core.config import settings
from core.file_storage import (
    REGISTERED_PREFIX,
    STAGED_PREFIX,
    registered_key,
    staged_key,
)
from models.files import (
    DIGITAL_COPY_SHAPE_ID,
    SCHEMA_DIGITAL_DOCUMENT,
    SCHEMA_NAME,
    DigitalCopy,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_PDF_MAGIC = b"%PDF-"
_CHUNK = 1024 * 1024  # 1 MiB
FILE_ID_RE = re.compile(r"^File_[0-9a-f]{8}$")


def file_content_url(file_id: str) -> str:
    """Backend-relative download path stored as ``schema:contentUrl``."""
    return f"/api/files/{file_id}"


def key_file_id(key: str, prefix: str) -> str:
    """File id from an object key: ``staged/File_x.pdf`` → ``File_x``."""
    return key[len(prefix) :].removesuffix(".pdf")


def collect_file_state(storage, oxigraph, extractor) -> dict:
    """Snapshot RDF and storage state for the reconciler and the stats endpoint.

    RDF is the source of truth: ``linked`` are file ids reachable from a parent
    via any schema-declared link predicate; ``typed`` are all
    ``schema:DigitalDocument`` subjects (typed-but-unlinked = orphaned node).
    ``staged``/``registered`` are the raw object listings.

    Raises:
        StorageNotConfigured: storage credentials are absent.
    """
    linked: set[str] = set()
    for _, link_pred in extractor.find_links_to_shape(DIGITAL_COPY_SHAPE_ID):
        rows = oxigraph.query(
            f"SELECT ?file {oxigraph.from_clause()} WHERE {{ ?parent <{link_pred}> ?file . }}"
        )
        linked |= {
            r["file"][len(RFDB_BASE) :] for r in rows if (r.get("file") or "").startswith(RFDB_BASE)
        }

    rows = oxigraph.query(
        f"SELECT ?n {oxigraph.from_clause()} WHERE {{ ?n a <{SCHEMA_DIGITAL_DOCUMENT}> . }}"
    )
    typed = {r["n"][len(RFDB_BASE) :] for r in rows if (r.get("n") or "").startswith(RFDB_BASE)}

    return {
        "linked": linked,
        "typed": typed,
        "staged": storage.list(STAGED_PREFIX),
        "registered": storage.list(REGISTERED_PREFIX),
    }


def _page_count(fileobj) -> int | None:
    """PDF page count via pypdf; ``None`` for encrypted/damaged files."""
    try:
        from pypdf import PdfReader

        return len(PdfReader(fileobj).pages)
    except Exception as exc:  # pypdf raises a variety of types on bad input
        logger.warning("Could not read PDF page count: %s", exc)
        return None


def derive_metadata(spool) -> tuple[int, str, int | None]:
    """Return ``(size, sha256, pages)`` for a spooled PDF, streaming in chunks.

    Enforces ``MAX_UPLOAD_MB`` while reading so an oversize body is rejected
    without hashing it in full. Shared by the staging route and the write-path
    re-derivation in ``api/data.py`` (server is the metadata authority).

    Raises:
        HTTPException 413: size exceeds ``MAX_UPLOAD_MB`` (0 disables the cap).
    """
    max_bytes = settings.max_upload_mb * 1024 * 1024 if settings.max_upload_mb else None
    hasher = hashlib.sha256()
    size = 0
    spool.seek(0)
    while chunk := spool.read(_CHUNK):
        size += len(chunk)
        if max_bytes is not None and size > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {settings.max_upload_mb} MB upload limit",
            )
        hasher.update(chunk)
    spool.seek(0)
    pages = _page_count(spool)
    return size, hasher.hexdigest(), pages


@router.post("/files/staged", response_model=DigitalCopy)
def stage_file(request: Request, file: UploadFile) -> DigitalCopy:
    """Stage an uploaded PDF and return the prefilled digital-copy node.

    No triples are written here — the returned node is form-state only until
    the curator submits the parent entity. Unsubmitted staged files expire via
    the cleanup script.

    Raises:
        403: Read-only mode.
        413: File exceeds ``MAX_UPLOAD_MB``.
        415: Body is not a PDF.
        503: Storage not configured.
    """
    _assert_writable_mode()

    spool = file.file  # SpooledTemporaryFile — sync route, so direct access is fine
    spool.seek(0)
    if spool.read(len(_PDF_MAGIC)) != _PDF_MAGIC:
        raise HTTPException(status_code=415, detail="Only PDF files are accepted")

    size, sha256, pages = derive_metadata(spool)

    # Random 8-hex id (assign_entity_id idiom): never reused, no mint race.
    file_id = f"File_{uuid.uuid4().hex[:8]}"
    original_name = os.path.basename(file.filename or "") or f"{file_id}.pdf"

    spool.seek(0)
    # A StorageError here (endpoint down, bad creds, missing bucket) propagates
    # to the app-level handler → clean 503. See app.py.
    request.app.state.storage.put_pdf(staged_key(file_id), spool)

    return DigitalCopy(
        id=RFDB_BASE + file_id,
        fileId=file_id,
        name=original_name,
        contentUrl=file_content_url(file_id),
        contentSize=size,
        sha256=sha256,
        numberOfPages=pages,
    )


@router.get("/files/{file_id}")
def download_file(file_id: str, request: Request):
    """Stream a stored PDF as an attachment (registered first, then staged)."""
    if not FILE_ID_RE.match(file_id):
        raise HTTPException(status_code=404, detail="File not found")

    storage = request.app.state.storage
    stream = None
    # A StorageError propagates to the app-level handler (503); a genuinely
    # absent object raises FileNotFoundError, which we treat as "try the next
    # key" and finally 404.
    for key in (registered_key(file_id), staged_key(file_id)):
        try:
            stream = storage.open_stream(key)
            break
        except FileNotFoundError:
            continue
    if stream is None:
        raise HTTPException(status_code=404, detail="File not found")

    # Original filename from RDF when the node was persisted; staged files
    # (not yet submitted) fall back to the file id.
    oxigraph = request.app.state.oxigraph
    name = None
    try:
        rows = oxigraph.query(
            f"SELECT ?name {oxigraph.from_clause()} "
            f"WHERE {{ <{RFDB_BASE}{file_id}> <{SCHEMA_NAME}> ?name . }} LIMIT 1"
        )
        name = rows[0]["name"] if rows else None
    except Exception:  # store down — still serve the bytes
        pass
    name = name or f"{file_id}.pdf"

    # Strip quotes, backslashes and control characters (a crafted name with
    # \r\n would otherwise be rejected by the HTTP stack → 500).
    safe_name = "".join(c for c in name if c.isprintable() and c not in '"\\') or "download.pdf"
    return StreamingResponse(
        stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )
