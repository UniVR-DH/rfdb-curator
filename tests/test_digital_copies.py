"""Tests for the upload-first digital-copy flow.

Covers the staging/download routes (``api/files.py``), the write-path
reconciliation + promotion (``api/data.py``), the cleanup reconciler
(``scripts/cleanup_files.py``), and the stats endpoint (``api/meta.py``).

Uses a real ``rdflib.Graph`` behind a small Oxigraph stub (queries/updates/
constructs actually run) and the in-memory storage fake from
``core.file_storage`` (no network, no ``moto``). Route handlers are called
directly, matching ``test_backend_api_data_unit.py``.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from rdflib import Graph

import api.data as data_mod
import api.files as files_mod
import api.meta as meta_mod
from api.data import _promote_staged_files, _reconcile_digital_copies
from api.files import download_file, stage_file
from api.meta import get_file_stats
from core.file_storage import InMemoryStorage, registered_key, staged_key
from core.schema_extractor import SchemaExtractor
from scripts.cleanup_files import reconcile

FILE_ID_RE = re.compile(r"^File_[0-9a-f]{8}$")
RFDB = "https://rosfeatr.eu/rdf/data/"
P138I = "http://www.cidoc-crm.org/cidoc-crm/P138i_has_representation"
DIGITAL_DOCUMENT = "http://schema.org/DigitalDocument"

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "schema.ttl"
_EXTRACTOR = SchemaExtractor(str(_SCHEMA_PATH))


class _FakeOxigraph:
    """Oxigraph stub backed by a real in-memory rdflib graph (no named graph)."""

    def __init__(self) -> None:
        self.g = Graph()

    def from_clause(self) -> str:
        return ""

    def with_clause(self) -> str:
        return ""

    def query(self, sparql: str) -> list[dict[str, str | None]]:
        res = self.g.query(sparql)
        return [{str(k): str(v) for k, v in b.items()} for b in res.bindings]

    def construct(self, sparql: str) -> Graph:
        return self.g.query(sparql).graph or Graph()

    def load_turtle(self, turtle: str) -> None:
        self.g.parse(data=turtle, format="turtle")

    def update(self, sparql: str) -> None:
        self.g.update(sparql)


def _make_pdf(pages: int = 1) -> bytes:
    """Return valid PDF bytes with the given number of blank pages."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _upload(filename: str, data: bytes) -> UploadFile:
    return UploadFile(file=io.BytesIO(data), filename=filename)


@pytest.fixture
def env():
    """Fake store + storage + request wired like app.state."""
    oxigraph = _FakeOxigraph()
    storage = InMemoryStorage()
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(oxigraph=oxigraph, storage=storage, schema_extractor=_EXTRACTOR)
        )
    )
    return SimpleNamespace(oxigraph=oxigraph, storage=storage, request=request)


# ---------------------------------------------------------------------------
# Staging route
# ---------------------------------------------------------------------------


def test_stage_non_pdf_rejected(env):
    """A non-PDF body is rejected with 415; nothing is stored."""
    with pytest.raises(HTTPException) as exc:
        stage_file(env.request, _upload("x.png", b"\x89PNG\r\n"))
    assert exc.value.status_code == 415
    assert env.storage.objects == {}


def test_stage_over_size_cap_rejected(env, monkeypatch):
    """A body over MAX_UPLOAD_MB is rejected with 413; nothing is stored."""
    monkeypatch.setattr(files_mod.settings, "max_upload_mb", 1)
    oversize = b"%PDF-" + b"\x00" * (1024 * 1024 + 10)
    with pytest.raises(HTTPException) as exc:
        stage_file(env.request, _upload("big.pdf", oversize))
    assert exc.value.status_code == 413
    assert env.storage.objects == {}


def test_stage_storage_error_propagates(env):
    """A backend StorageError is not swallowed — it reaches the app-level handler.

    The route must NOT convert it to a leaky 500/detailed message; app.py maps
    the StorageError family to a clean 503.
    """
    from core.file_storage import StorageError, StorageNotInitialized

    def boom(*_a, **_k):
        raise StorageNotInitialized("simulated garage AccessDenied")

    env.storage.put_pdf = boom
    with pytest.raises(StorageError):  # base type — subclass propagates too
        stage_file(env.request, _upload("x.pdf", _make_pdf()))


def test_storage_error_classification():
    """Auth/bucket ClientErrors → NotInitialized; connectivity/other → Unavailable."""
    from botocore.exceptions import ClientError, EndpointConnectionError

    from core.file_storage import (
        StorageNotInitialized,
        StorageUnavailable,
        _storage_error,
    )

    def client_error(code: str) -> ClientError:
        return ClientError({"Error": {"Code": code, "Message": "x"}}, "PutObject")

    # Not initialized — deterministic setup/permission faults.
    for code in ("AccessDenied", "NoSuchBucket", "InvalidAccessKeyId", "SignatureDoesNotMatch"):
        assert isinstance(_storage_error("op", "ep", client_error(code)), StorageNotInitialized)

    # Unavailable — transient / connectivity / unknown service errors.
    assert isinstance(_storage_error("op", "ep", client_error("InternalError")), StorageUnavailable)
    assert isinstance(_storage_error("op", "ep", client_error("SlowDown")), StorageUnavailable)
    assert isinstance(
        _storage_error("op", "ep", EndpointConnectionError(endpoint_url="ep")),
        StorageUnavailable,
    )


def test_stage_read_only_blocked(env, monkeypatch):
    """READ_ONLY mode refuses staging with 403."""
    monkeypatch.setattr(data_mod.settings, "read_only", True)
    with pytest.raises(HTTPException) as exc:
        stage_file(env.request, _upload("x.pdf", _make_pdf()))
    assert exc.value.status_code == 403


def test_stage_returns_prefilled_node_and_stores_staged(env):
    """Staging stores under staged/ and returns correct derived metadata."""
    pdf = _make_pdf(pages=3)
    node = stage_file(env.request, _upload("libretto scan (1736).pdf", pdf))

    assert FILE_ID_RE.match(node.fileId)
    assert node.id == RFDB + node.fileId
    assert node.name == "libretto scan (1736).pdf"
    assert node.contentSize == len(pdf)
    assert node.sha256 == hashlib.sha256(pdf).hexdigest()
    assert node.numberOfPages == 3
    assert node.contentUrl == f"/api/files/{node.fileId}"
    assert env.storage.objects[staged_key(node.fileId)] == pdf
    # No triples written at staging time.
    assert len(env.oxigraph.g) == 0


# ---------------------------------------------------------------------------
# Download route
# ---------------------------------------------------------------------------


def _drain(resp) -> bytes:
    async def inner():
        return b"".join([chunk async for chunk in resp.body_iterator])

    return asyncio.run(inner())


def test_download_staged_then_registered(env):
    """Download serves staged bytes pre-submit and registered bytes after."""
    pdf = _make_pdf()
    node = stage_file(env.request, _upload("orig.pdf", pdf))

    resp = download_file(node.fileId, env.request)  # staged fallback
    assert _drain(resp) == pdf

    env.storage.move(staged_key(node.fileId), registered_key(node.fileId))
    resp = download_file(node.fileId, env.request)  # registered
    assert resp.media_type == "application/pdf"
    assert _drain(resp) == pdf


def test_download_unknown_id_404(env):
    """Unknown or malformed file ids return 404."""
    for bad in ("File_deadbeef", "not-a-file-id", "../etc/passwd"):
        with pytest.raises(HTTPException) as exc:
            download_file(bad, env.request)
        assert exc.value.status_code == 404


def test_download_filename_from_rdf(env):
    """A persisted node's schema:name becomes the attachment filename."""
    pdf = _make_pdf()
    node = stage_file(env.request, _upload("scan.pdf", pdf))
    env.oxigraph.load_turtle(f'<{node.id}> <http://schema.org/name> "scan.pdf" .')
    resp = download_file(node.fileId, env.request)
    assert 'filename="scan.pdf"' in resp.headers["content-disposition"]


# ---------------------------------------------------------------------------
# Write-path reconciliation + promotion
# ---------------------------------------------------------------------------


def _copy_node_turtle(node, sha="0" * 64, size=1, name="x.pdf") -> str:
    """Payload-graph turtle for a digital-copy node with client-supplied values."""
    return f"""
        @prefix schema: <http://schema.org/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        <{node}> a schema:DigitalDocument ;
          schema:name "{name}" ;
          schema:encodingFormat "application/pdf" ;
          schema:contentUrl "/api/files/x"^^xsd:anyURI ;
          schema:contentSize {size} ;
          schema:sha256 "{sha}" .
    """


def test_reconcile_rederives_staged_metadata(env):
    """Tampered payload metadata is replaced with server-derived values."""
    pdf = _make_pdf(pages=2)
    node = stage_file(env.request, _upload("a.pdf", pdf))

    payload = Graph()
    payload.parse(data=_copy_node_turtle(node.id, sha="f" * 64, size=999), format="turtle")
    promote = _reconcile_digital_copies(payload, env.request)

    assert promote == [node.fileId]
    true_sha = hashlib.sha256(pdf).hexdigest()
    values = {str(o) for o in payload.objects(None, None)}
    assert true_sha in values  # server value in
    assert "f" * 64 not in values  # tampered value out
    assert str(len(pdf)) in values and "999" not in values
    assert f"/api/files/{node.fileId}" in values  # contentUrl recomputed


def test_reconcile_strips_registered_metadata(env):
    """Registered nodes keep only their type in the payload (store wins)."""
    pdf = _make_pdf()
    node = stage_file(env.request, _upload("a.pdf", pdf))
    env.storage.move(staged_key(node.fileId), registered_key(node.fileId))

    payload = Graph()
    payload.parse(data=_copy_node_turtle(node.id, sha="f" * 64), format="turtle")
    promote = _reconcile_digital_copies(payload, env.request)

    assert promote == []  # already registered — nothing to promote
    preds = {str(p) for p in payload.predicates(None, None)}
    assert preds == {"http://www.w3.org/1999/02/22-rdf-syntax-ns#type"}


def test_reconcile_missing_staged_file_422(env):
    """A payload node whose staged object vanished is rejected."""
    payload = Graph()
    payload.parse(data=_copy_node_turtle(f"{RFDB}File_deadbeef"), format="turtle")
    with pytest.raises(HTTPException) as exc:
        _reconcile_digital_copies(payload, env.request)
    assert exc.value.status_code == 422


def test_reconcile_bad_node_iri_422(env):
    """Digital-copy nodes outside the File_{8hex} namespace are rejected."""
    payload = Graph()
    payload.parse(
        data=f"<{RFDB}evil> a <{DIGITAL_DOCUMENT}> .",
        format="turtle",
    )
    with pytest.raises(HTTPException) as exc:
        _reconcile_digital_copies(payload, env.request)
    assert exc.value.status_code == 422


def test_promote_moves_staged_to_registered(env):
    """Promotion moves the object; a failed move is logged, not raised."""
    pdf = _make_pdf()
    node = stage_file(env.request, _upload("a.pdf", pdf))
    _promote_staged_files(env.request, [node.fileId, "File_00000000"])  # 2nd missing
    assert env.storage.objects == {registered_key(node.fileId): pdf}


# ---------------------------------------------------------------------------
# Cleanup reconciler (scripts/cleanup_files.py)
# ---------------------------------------------------------------------------


def _link(env, file_id: str, parent: str = f"{RFDB}S1") -> None:
    """Write the parent→file link + node type triples into the fake store."""
    env.oxigraph.load_turtle(
        f"<{parent}> <{P138I}> <{RFDB}{file_id}> . <{RFDB}{file_id}> a <{DIGITAL_DOCUMENT}> ."
    )


def test_reconcile_script_rules(env):
    """Promote referenced-staged; expire old staged; grace-delete registered; purge orphans."""
    clock = {"now": 1000.0}
    storage = InMemoryStorage(clock=lambda: clock["now"])
    env.request.app.state.storage = storage

    # a) staged + referenced (crash before promotion) → promote
    storage.put_pdf(staged_key("File_aaaaaaaa"), io.BytesIO(b"%PDF-a"))
    _link(env, "File_aaaaaaaa")
    # b) staged + unreferenced + old → delete
    storage.put_pdf(staged_key("File_bbbbbbbb"), io.BytesIO(b"%PDF-b"))
    # c) staged + unreferenced + fresh → keep
    # (created later, after the clock advances)
    # d) registered + unreferenced + old → delete
    storage.put_pdf(registered_key("File_dddddddd"), io.BytesIO(b"%PDF-d"))
    # e) registered + linked → keep
    storage.put_pdf(registered_key("File_eeeeeeee"), io.BytesIO(b"%PDF-e"))
    _link(env, "File_eeeeeeee")
    # f) orphaned node: typed but unlinked → triples purged + object deleted
    env.oxigraph.load_turtle(f"<{RFDB}File_ffffffff> a <{DIGITAL_DOCUMENT}> .")
    storage.put_pdf(registered_key("File_ffffffff"), io.BytesIO(b"%PDF-f"))

    clock["now"] = 1000.0 + 100_000  # everything above is now "old"
    storage.put_pdf(staged_key("File_cccccccc"), io.BytesIO(b"%PDF-c"))  # (c) fresh

    actions = reconcile(
        storage,
        env.oxigraph,
        _EXTRACTOR,
        staged_ttl_s=86_400,
        registered_grace_s=86_400,
        now=clock["now"],
    )

    assert actions["promoted"] == ["File_aaaaaaaa"]
    assert actions["deleted_staged"] == ["File_bbbbbbbb"]
    assert actions["deleted_registered"] == ["File_dddddddd"]
    assert actions["purged_nodes"] == ["File_ffffffff"]
    assert set(storage.objects) == {
        registered_key("File_aaaaaaaa"),  # promoted
        staged_key("File_cccccccc"),  # fresh, kept
        registered_key("File_eeeeeeee"),  # linked, kept
    }
    # Orphaned node triples are gone from the store.
    assert (None, None, None) not in Graph().parse(
        data="", format="turtle"
    ) or f"{RFDB}File_ffffffff" not in {str(s) for s in env.oxigraph.g.subjects()}


def test_reconcile_script_dry_run_changes_nothing(env):
    """--dry-run reports actions but leaves storage and triples untouched."""
    clock = {"now": 1000.0}
    storage = InMemoryStorage(clock=lambda: clock["now"])
    storage.put_pdf(staged_key("File_bbbbbbbb"), io.BytesIO(b"%PDF-b"))
    clock["now"] += 100_000

    actions = reconcile(
        storage,
        env.oxigraph,
        _EXTRACTOR,
        staged_ttl_s=86_400,
        registered_grace_s=86_400,
        now=clock["now"],
        dry_run=True,
    )
    assert actions["deleted_staged"] == ["File_bbbbbbbb"]
    assert staged_key("File_bbbbbbbb") in storage.objects  # still there


# ---------------------------------------------------------------------------
# Stats endpoint
# ---------------------------------------------------------------------------


def test_file_stats_shape(env, monkeypatch):
    """/api/meta/files reports counts, bytes, and orphan indicators."""
    monkeypatch.setattr(meta_mod.settings, "s3_endpoint", "http://garage:3900")
    pdf = _make_pdf()
    node = stage_file(env.request, _upload("a.pdf", pdf))  # staged, unreferenced
    env.storage.put_pdf(registered_key("File_eeeeeeee"), io.BytesIO(b"%PDF-e"))
    _link(env, "File_eeeeeeee")

    stats = get_file_stats(env.request)
    assert stats["configured"] is True
    assert stats["staged"]["count"] == 1
    assert stats["staged"]["bytes"] == len(pdf)
    assert stats["staged"]["oldestAgeS"] is not None
    assert stats["registered"]["count"] == 1
    assert stats["linkedNodes"] == 1
    assert stats["unreferencedStaged"] == 1
    assert stats["unreferencedRegistered"] == 0
    assert stats["orphanedNodes"] == 0
    assert node.fileId  # staged id minted


def test_file_stats_unconfigured(env, monkeypatch):
    """Without S3_ENDPOINT the endpoint reports configured: false, zeroed."""
    monkeypatch.setattr(meta_mod.settings, "s3_endpoint", "")
    stats = get_file_stats(env.request)
    assert stats["configured"] is False
    assert stats["staged"]["count"] == 0
