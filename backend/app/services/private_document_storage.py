"""Provider-neutral private document storage.

Private objects are never mounted as static content. Callers authorize the
domain record before streaming the object through an authenticated route.
"""

from __future__ import annotations

import hashlib
import logging
import re
import tempfile
import unicodedata
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol
from urllib.parse import quote
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.core.config import settings


logger = logging.getLogger(__name__)
ALLOWED_TYPES = {
    "application/pdf": (".pdf", {".pdf"}),
    "image/jpeg": (".jpg", {".jpg", ".jpeg"}),
    "image/png": (".png", {".png"}),
}
CHUNK_SIZE = 64 * 1024
SAFE_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9/_.-]{1,510}$")
SAFE_SCOPES = {"verification", "safari-traveller", "safari-confirmation"}


@dataclass(frozen=True)
class StoredPrivateDocument:
    storage_key: str
    original_name: str
    content_type: str
    size: int
    checksum_sha256: str


@dataclass(frozen=True)
class PrivateDocumentStream:
    chunks: Iterator[bytes]
    close: Callable[[], None]


class PrivateDocumentProvider(Protocol):
    def put(self, *, scope: str, source: BinaryIO, content_type: str, extension: str, size: int, checksum: str) -> str: ...
    def open(self, storage_key: str) -> PrivateDocumentStream: ...
    def delete(self, storage_key: str) -> None: ...


def _safe_storage_key(storage_key: str) -> str:
    normalized = storage_key.replace("\\", "/").strip("/")
    if not SAFE_KEY_PATTERN.fullmatch(normalized) or ".." in normalized.split("/"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Private document not found")
    if not normalized.startswith(("private/", "verification/", "safari/")):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Private document not found")
    return normalized


def _sanitize_display_name(filename: str | None, extension: str) -> str:
    normalized = unicodedata.normalize("NFKC", filename or "document").replace("\\", "/")
    basename = normalized.rsplit("/", 1)[-1].replace("\x00", "")
    basename = "".join(char for char in basename if char.isprintable() and ord(char) < 128)
    basename = re.sub(r"[^A-Za-z0-9._ -]+", "_", basename).strip(" .")
    stem = Path(basename).stem[:100].strip(" .") or "document"
    return f"{stem}{extension}"


def _detected_type(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return None


async def _validated_upload(file: UploadFile, label: str) -> tuple[BinaryIO, str, str, int, str, str]:
    declared_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if declared_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail=f"{label} documents must be PDF, JPEG, or PNG")
    buffer = tempfile.SpooledTemporaryFile(max_size=min(settings.PRIVATE_DOCUMENT_MAX_BYTES, 1024 * 1024), mode="w+b")
    digest, total, prefix = hashlib.sha256(), 0, b""
    try:
        while chunk := await file.read(CHUNK_SIZE):
            total += len(chunk)
            if total > settings.PRIVATE_DOCUMENT_MAX_BYTES:
                raise HTTPException(status_code=413, detail=f"{label} document exceeds the configured size limit")
            prefix += chunk[: max(0, 32 - len(prefix))]
            digest.update(chunk)
            buffer.write(chunk)
        if total == 0:
            raise HTTPException(status_code=422, detail=f"{label} document is empty")
        detected_type = _detected_type(prefix)
        if detected_type != declared_type:
            raise HTTPException(status_code=422, detail="Document content does not match its declared type")
        extension, allowed_extensions = ALLOWED_TYPES[detected_type]
        supplied_extension = Path((file.filename or "").replace("\\", "/")).suffix.lower()
        if supplied_extension and supplied_extension not in allowed_extensions:
            raise HTTPException(status_code=422, detail="Document filename extension does not match its content")
        safe_name = _sanitize_display_name(file.filename, extension)
        buffer.seek(0)
        return buffer, safe_name, detected_type, total, digest.hexdigest(), extension
    except Exception:
        buffer.close()
        await file.close()
        raise


class LocalPrivateDocumentProvider:
    def __init__(self, root: Path | None = None):
        self.root = (root or settings.PRIVATE_DOCUMENT_ROOT).resolve()

    def put(self, *, scope: str, source: BinaryIO, content_type: str, extension: str, size: int, checksum: str) -> str:
        del content_type, size, checksum
        key = _new_key(scope, extension)
        destination = (self.root / key).resolve()
        if self.root not in destination.parents:
            raise HTTPException(status_code=400, detail="Invalid document path")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(f"{destination.suffix}.{uuid4().hex}.upload")
        try:
            with temporary.open("xb") as output:
                while chunk := source.read(CHUNK_SIZE):
                    output.write(chunk)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return key

    def open(self, storage_key: str) -> PrivateDocumentStream:
        target = (self.root / _safe_storage_key(storage_key)).resolve()
        if self.root not in target.parents or not target.is_file():
            raise HTTPException(status_code=404, detail="Private document not found")
        handle = target.open("rb")

        def chunks() -> Iterator[bytes]:
            while chunk := handle.read(CHUNK_SIZE):
                yield chunk

        return PrivateDocumentStream(chunks(), handle.close)

    def delete(self, storage_key: str) -> None:
        target = (self.root / _safe_storage_key(storage_key)).resolve()
        if self.root not in target.parents:
            raise HTTPException(status_code=404, detail="Private document not found")
        target.unlink(missing_ok=True)


class S3PrivateDocumentProvider:
    """Private Amazon S3 adapter. A client can be injected for transport tests."""

    def __init__(self, client=None):
        if client is None:
            try:
                import boto3
                from botocore.config import Config
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("boto3 is required for S3 private document storage") from exc
            kwargs: dict[str, object] = {
                "region_name": settings.PRIVATE_DOCUMENT_S3_REGION,
                "config": Config(
                    connect_timeout=settings.PRIVATE_DOCUMENT_CONNECT_TIMEOUT_SECONDS,
                    read_timeout=settings.PRIVATE_DOCUMENT_READ_TIMEOUT_SECONDS,
                    retries={"max_attempts": 2, "mode": "standard"},
                    s3={"addressing_style": settings.PRIVATE_DOCUMENT_S3_ADDRESSING_STYLE},
                ),
            }
            if settings.PRIVATE_DOCUMENT_S3_ENDPOINT_URL:
                kwargs["endpoint_url"] = settings.PRIVATE_DOCUMENT_S3_ENDPOINT_URL
            if settings.PRIVATE_DOCUMENT_S3_ACCESS_KEY_ID:
                kwargs["aws_access_key_id"] = settings.PRIVATE_DOCUMENT_S3_ACCESS_KEY_ID
                kwargs["aws_secret_access_key"] = settings.PRIVATE_DOCUMENT_S3_SECRET_ACCESS_KEY
            client = boto3.client("s3", **kwargs)
        self.client, self.bucket = client, settings.PRIVATE_DOCUMENT_S3_BUCKET

    def put(self, *, scope: str, source: BinaryIO, content_type: str, extension: str, size: int, checksum: str) -> str:
        key = _new_key(scope, extension)
        params: dict[str, object] = {
            "Bucket": self.bucket, "Key": key, "Body": source, "ContentLength": size,
            "ContentType": content_type, "CacheControl": "private, no-store, max-age=0",
            "Metadata": {"sha256": checksum}, "ServerSideEncryption": settings.PRIVATE_DOCUMENT_S3_ENCRYPTION,
        }
        if settings.PRIVATE_DOCUMENT_S3_KMS_KEY_ID:
            params["SSEKMSKeyId"] = settings.PRIVATE_DOCUMENT_S3_KMS_KEY_ID
        try:
            self.client.put_object(**params)
        except Exception as exc:
            # A lost response can follow a successful PUT. Verify the same
            # random key and checksum before classifying the upload as failed.
            try:
                head = self.client.head_object(Bucket=self.bucket, Key=key)
                if head.get("ContentLength") == size and head.get("Metadata", {}).get("sha256") == checksum:
                    logger.info("Recovered private document upload after uncertain response", extra={"provider": "s3", "operation": "head_object", "key_fingerprint": hashlib.sha256(key.encode()).hexdigest()[:12]})
                    return key
            except Exception:
                pass
            _storage_failure("put_object", key)
            raise HTTPException(status_code=503, detail="Private document storage is temporarily unavailable") from exc
        return key

    def open(self, storage_key: str) -> PrivateDocumentStream:
        key = _safe_storage_key(storage_key)
        try:
            result = self.client.get_object(Bucket=self.bucket, Key=key)
            body = result["Body"]
            if not callable(getattr(body, "iter_chunks", None)) or not callable(getattr(body, "close", None)):
                raise ValueError("Invalid object body")
        except Exception as exc:
            _storage_failure("get_object", key)
            if _provider_error_code(exc) in {"404", "NoSuchKey", "NotFound"}:
                raise HTTPException(status_code=404, detail="Private document not found") from exc
            raise HTTPException(status_code=503, detail="Private document storage is temporarily unavailable") from exc
        return PrivateDocumentStream(body.iter_chunks(chunk_size=CHUNK_SIZE), body.close)

    def delete(self, storage_key: str) -> None:
        key = _safe_storage_key(storage_key)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            if _provider_error_code(exc) in {"404", "NoSuchKey", "NotFound"}:
                return
            _storage_failure("delete_object", key)
            raise RuntimeError("Private document deletion failed") from exc


def _storage_failure(operation: str, key: str) -> None:
    logger.warning("Private document storage operation failed", extra={"provider": "s3", "operation": operation, "key_fingerprint": hashlib.sha256(key.encode()).hexdigest()[:12]})


def _provider_error_code(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    return str(response.get("Error", {}).get("Code", "")) if isinstance(response, dict) else ""


def _new_key(scope: str, extension: str) -> str:
    if scope not in SAFE_SCOPES:
        raise ValueError("Unsupported private document scope")
    identifier = uuid4().hex
    return f"private/{scope}/{identifier[:2]}/{identifier}{extension}"


def configured_provider() -> PrivateDocumentProvider:
    if settings.PRIVATE_DOCUMENT_MODE == "local":
        return LocalPrivateDocumentProvider()
    if settings.PRIVATE_DOCUMENT_MODE == "s3":
        return S3PrivateDocumentProvider()
    raise HTTPException(status_code=503, detail="Private document storage is disabled")


async def _store(scope: str, file: UploadFile, label: str) -> StoredPrivateDocument:
    source, name, content_type, size, checksum, extension = await _validated_upload(file, label)
    try:
        key = configured_provider().put(scope=scope, source=source, content_type=content_type, extension=extension, size=size, checksum=checksum)
    finally:
        source.close()
        await file.close()
    return StoredPrivateDocument(key, name, content_type, size, checksum)


async def store_verification_document(hotel_id: int, file: UploadFile) -> StoredPrivateDocument:
    del hotel_id
    return await _store("verification", file, "Verification")


async def store_safari_document(request_id: int, scope: str, file: UploadFile) -> StoredPrivateDocument:
    del request_id
    return await _store("safari-confirmation" if scope == "confirmation" else "safari-traveller", file, "Safari")


def open_document(storage_key: str) -> PrivateDocumentStream:
    return configured_provider().open(storage_key)


def resolve_owned_reference(hotel_id: int, storage_key: str) -> PrivateDocumentStream:
    del hotel_id
    return open_document(storage_key)


def resolve_safari_reference(request_id: int, storage_key: str) -> PrivateDocumentStream:
    del request_id
    return open_document(storage_key)


def delete_document(storage_key: str | None) -> None:
    if storage_key:
        configured_provider().delete(storage_key)


def download_response(storage_key: str, *, filename: str, content_type: str) -> StreamingResponse:
    safe_name = _sanitize_display_name(filename, ALLOWED_TYPES.get(content_type, (".bin", set()))[0])

    def body() -> Iterator[bytes]:
        stream = open_document(storage_key)
        try:
            yield from stream.chunks
        finally:
            stream.close()

    disposition = f"attachment; filename=\"{safe_name}\"; filename*=UTF-8''{quote(safe_name)}"
    return StreamingResponse(body(), media_type=content_type if content_type in ALLOWED_TYPES else "application/octet-stream", headers={
        "Cache-Control": "private, no-store, max-age=0", "Pragma": "no-cache",
        "Content-Disposition": disposition, "X-Content-Type-Options": "nosniff",
    })
