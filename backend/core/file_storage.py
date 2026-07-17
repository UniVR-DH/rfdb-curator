"""Object-storage seam for source digital copies (PDF scans).

A thin abstraction over S3-compatible storage (Garage in this project). The
route layer never touches boto3 directly — it goes through :class:`FileStorage`
so that:

  * tests inject :class:`InMemoryStorage` (no ``moto`` dependency, no network);
  * a future backend swap (e.g. a different object store) is a single-file change.

The concrete :class:`GarageStorage` builds its boto3 client lazily on first use,
so importing this module — and starting the app or the test suite — never
requires credentials or a reachable endpoint.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import BinaryIO, NamedTuple

_CHUNK = 1024 * 1024  # 1 MiB streaming chunk

# Key prefixes for the upload-first lifecycle: uploads land in staged/ and are
# moved to registered/ when the entity that references them is persisted. The
# cleanup reconciler (scripts/cleanup_files.py) garbage-collects both.
STAGED_PREFIX = "staged/"
REGISTERED_PREFIX = "registered/"


def staged_key(file_id: str) -> str:
    """Object key for a staged (not yet submitted) file."""
    return f"{STAGED_PREFIX}{file_id}.pdf"


def registered_key(file_id: str) -> str:
    """Object key for a registered (referenced in RDF) file."""
    return f"{REGISTERED_PREFIX}{file_id}.pdf"


class ObjectInfo(NamedTuple):
    """One stored object as returned by :meth:`FileStorage.list`."""

    key: str
    size: int
    last_modified: float  # unix timestamp


class StorageError(RuntimeError):
    """Base: an object-storage operation failed.

    The seam raises a subclass (never a raw boto/botocore exception) so the API
    can answer cleanly and log the cause. The two subclasses map to the two
    failure families that need *different* operator action — see the app-level
    handler in ``app.py``.
    """


class StorageNotInitialized(StorageError):
    """Storage is reachable but not set up for use: missing/unimported
    credentials, access denied, or an absent bucket.

    Deterministic — retrying will not help; the fix is to (re)run the bootstrap
    (``scripts/garage-init.sh``).
    """


class StorageNotConfigured(StorageNotInitialized):
    """No endpoint/credentials configured at all (env vars unset)."""


class StorageUnavailable(StorageError):
    """Storage is configured but not reachable/serving right now: endpoint down,
    connection reset/timeout, or a transient service-side error.

    Often self-resolving — the fix is to ensure the service is running; the
    operation may succeed on retry.
    """


# S3 error codes that mean "set up / permissions", not "temporarily down".
# Garage returns AccessDenied for both an unimported key and a denied grant.
_NOT_INITIALIZED_CODES = frozenset(
    {
        "AccessDenied",
        "InvalidAccessKeyId",
        "SignatureDoesNotMatch",
        "NoSuchBucket",
        "AllAccessDisabled",
        "AccountProblem",
    }
)


def _storage_error(op: str, endpoint: str, exc: Exception) -> StorageError:
    """Classify a boto/botocore exception into the right StorageError family.

    Auth/bucket/credential ``ClientError`` codes → :class:`StorageNotInitialized`
    (bootstrap needed). Everything else — connection/transport errors
    (``BotoCoreError``) and non-auth service errors — → :class:`StorageUnavailable`
    (service down / transient / retryable).
    """
    from botocore.exceptions import ClientError

    msg = f"{op} failed against '{endpoint}': {exc}"
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        if code in _NOT_INITIALIZED_CODES:
            return StorageNotInitialized(msg)
    return StorageUnavailable(msg)


class FileStorage(ABC):
    """Minimal object-storage interface used by the file routes."""

    @abstractmethod
    def put_pdf(self, key: str, fileobj: BinaryIO) -> None:
        """Stream ``fileobj`` (positioned at 0) to ``key`` as ``application/pdf``."""

    @abstractmethod
    def open_stream(self, key: str) -> Iterator[bytes]:
        """Yield the object's bytes in chunks. Raise ``FileNotFoundError`` if absent."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete ``key``. A no-op if the object does not exist."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return whether ``key`` exists."""

    @abstractmethod
    def move(self, src: str, dst: str) -> None:
        """Move an object (copy + delete). Raise ``FileNotFoundError`` if absent."""

    @abstractmethod
    def list(self, prefix: str) -> list[ObjectInfo]:
        """List objects under ``prefix`` with size and last-modified timestamp."""


class GarageStorage(FileStorage):
    """S3-compatible storage backed by boto3 (Garage or any S3 service)."""

    def __init__(
        self,
        *,
        endpoint: str,
        region: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
    ) -> None:
        self._endpoint = endpoint
        self._region = region
        self._bucket = bucket
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._client = None  # built lazily so import/startup needs no endpoint

    def _s3(self):
        """Return the boto3 S3 client, building it on first use."""
        if self._client is None:
            if not (self._endpoint and self._access_key_id and self._secret_access_key):
                raise StorageNotConfigured(
                    "File storage is not configured: set S3_ENDPOINT, "
                    "S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY."
                )
            import boto3  # local import keeps boto3 off the startup import path

            self._client = boto3.client(
                "s3",
                endpoint_url=self._endpoint,
                region_name=self._region,
                aws_access_key_id=self._access_key_id,
                aws_secret_access_key=self._secret_access_key,
            )
        return self._client

    @staticmethod
    def _is_missing(exc) -> bool:
        """True when a boto ClientError means the object/bucket simply isn't there."""
        return exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NotFound")

    def _run(self, op: str, fn):
        """Run a boto call, translating any backend failure into a StorageError
        subclass (:func:`_storage_error`) so nothing boto-specific leaks past the seam.
        """
        from botocore.exceptions import BotoCoreError, ClientError

        try:
            return fn()
        except (BotoCoreError, ClientError) as exc:
            raise _storage_error(op, self._endpoint, exc) from exc

    def put_pdf(self, key: str, fileobj: BinaryIO) -> None:
        # upload_fileobj streams in parts; the whole PDF is never held in memory.
        self._run(
            "put_pdf",
            lambda: self._s3().upload_fileobj(
                fileobj, self._bucket, key, ExtraArgs={"ContentType": "application/pdf"}
            ),
        )

    def open_stream(self, key: str) -> Iterator[bytes]:
        from botocore.exceptions import ClientError

        try:
            body = self._s3().get_object(Bucket=self._bucket, Key=key)["Body"]
        except ClientError as exc:
            if self._is_missing(exc):
                raise FileNotFoundError(key) from exc
            raise _storage_error("open_stream", self._endpoint, exc) from exc
        return body.iter_chunks(_CHUNK)

    def delete(self, key: str) -> None:
        # S3 delete_object is idempotent — deleting a missing key is not an error.
        self._run("delete", lambda: self._s3().delete_object(Bucket=self._bucket, Key=key))

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._s3().head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as exc:
            if self._is_missing(exc):
                return False
            raise _storage_error("exists", self._endpoint, exc) from exc

    def move(self, src: str, dst: str) -> None:
        from botocore.exceptions import ClientError

        try:
            self._s3().copy_object(
                Bucket=self._bucket, Key=dst, CopySource={"Bucket": self._bucket, "Key": src}
            )
        except ClientError as exc:
            if self._is_missing(exc):
                raise FileNotFoundError(src) from exc
            raise _storage_error("move", self._endpoint, exc) from exc
        self._run("move.delete", lambda: self._s3().delete_object(Bucket=self._bucket, Key=src))

    def list(self, prefix: str) -> list[ObjectInfo]:
        def _list() -> list[ObjectInfo]:
            paginator = self._s3().get_paginator("list_objects_v2")
            out: list[ObjectInfo] = []
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    out.append(ObjectInfo(obj["Key"], obj["Size"], obj["LastModified"].timestamp()))
            return out

        return self._run("list", _list)


class InMemoryStorage(FileStorage):
    """Dict-backed fake for tests. Same contract as :class:`GarageStorage`.

    ``clock`` is injectable so reconciler tests can control object age without
    sleeping.
    """

    def __init__(self, clock=time.time) -> None:
        self.objects: dict[str, bytes] = {}
        self.mtimes: dict[str, float] = {}
        self._clock = clock

    def put_pdf(self, key: str, fileobj: BinaryIO) -> None:
        self.objects[key] = fileobj.read()
        self.mtimes[key] = self._clock()

    def open_stream(self, key: str) -> Iterator[bytes]:
        if key not in self.objects:
            raise FileNotFoundError(key)
        return _chunks(self.objects[key])

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)
        self.mtimes.pop(key, None)

    def exists(self, key: str) -> bool:
        return key in self.objects

    def move(self, src: str, dst: str) -> None:
        if src not in self.objects:
            raise FileNotFoundError(src)
        self.objects[dst] = self.objects.pop(src)
        self.mtimes[dst] = self.mtimes.pop(src)

    def list(self, prefix: str) -> list[ObjectInfo]:
        return [
            ObjectInfo(k, len(v), self.mtimes[k])
            for k, v in sorted(self.objects.items())
            if k.startswith(prefix)
        ]


def _chunks(data: bytes) -> Iterator[bytes]:
    for i in range(0, len(data), _CHUNK):
        yield data[i : i + _CHUNK]


def build_storage() -> FileStorage:
    """Construct the configured storage backend from application settings.

    Called once at startup (app lifespan). Returns a :class:`GarageStorage`;
    the client itself connects lazily, so this never blocks or fails on a
    missing endpoint.
    """
    from core.config import settings

    return GarageStorage(
        endpoint=settings.s3_endpoint,
        region=settings.s3_region,
        bucket=settings.s3_bucket,
        access_key_id=settings.s3_access_key_id,
        secret_access_key=settings.s3_secret_access_key,
    )
