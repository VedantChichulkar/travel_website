import asyncio
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.core.config import settings
from app.database import SessionLocal
from app.models.private_document import PrivateDocumentDeletionJob, PrivateDocumentDeletionStatus
from app.services import private_document_lifecycle_service, private_document_storage


def upload(name: str, content_type: str, data: bytes) -> UploadFile:
    return UploadFile(filename=name, file=BytesIO(data), headers=Headers({"content-type": content_type}))


class FakeBody:
    def __init__(self, data: bytes): self.data, self.closed = data, False
    def iter_chunks(self, chunk_size: int):
        for offset in range(0, len(self.data), chunk_size): yield self.data[offset:offset + chunk_size]
    def close(self): self.closed = True


class FakeS3:
    def __init__(self): self.puts = []; self.deletes = []; self.body = FakeBody(b"%PDF-1.4 stored")
    def put_object(self, **kwargs): self.puts.append(kwargs); return {"ETag": "test"}
    def get_object(self, **kwargs): return {"Body": self.body}
    def head_object(self, **kwargs): return {"ContentLength": 8, "Metadata": {"sha256": "a" * 64}}
    def delete_object(self, **kwargs): self.deletes.append(kwargs); return {}


class ProviderError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class PrivateDocumentStorageTests(unittest.TestCase):
    def setUp(self):
        self.values = {name: getattr(settings, name) for name in (
            "PRIVATE_DOCUMENT_MODE", "PRIVATE_DOCUMENT_ROOT", "PRIVATE_DOCUMENT_MAX_BYTES",
            "PRIVATE_DOCUMENT_S3_BUCKET", "PRIVATE_DOCUMENT_S3_ENCRYPTION", "PRIVATE_DOCUMENT_S3_KMS_KEY_ID",
        )}

    def tearDown(self):
        for name, value in self.values.items(): setattr(settings, name, value)

    def test_valid_files_are_bounded_hashed_and_use_opaque_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            settings.PRIVATE_DOCUMENT_MODE = "local"; settings.PRIVATE_DOCUMENT_ROOT = Path(directory)
            cases = (
                ("license.pdf", "application/pdf", b"%PDF-1.4 safe"),
                ("photo.jpeg", "image/jpeg", b"\xff\xd8\xffsafe"),
                ("scan.png", "image/png", b"\x89PNG\r\n\x1a\nsafe"),
            )
            for name, content_type, data in cases:
                with self.subTest(name=name):
                    stored = asyncio.run(private_document_storage.store_verification_document(42, upload(name, content_type, data)))
                    self.assertRegex(stored.storage_key, r"^private/verification/[0-9a-f]{2}/[0-9a-f]{32}\.(pdf|jpg|png)$")
                    self.assertNotIn(name.rsplit(".", 1)[0], stored.storage_key)
                    self.assertEqual(len(stored.checksum_sha256), 64)
                    self.assertTrue((Path(directory) / stored.storage_key).is_file())

    def test_rejects_empty_oversized_spoofed_and_unsupported_content(self):
        settings.PRIVATE_DOCUMENT_MODE = "local"
        with tempfile.TemporaryDirectory() as directory:
            settings.PRIVATE_DOCUMENT_ROOT = Path(directory); settings.PRIVATE_DOCUMENT_MAX_BYTES = 12
            bad = (
                upload("empty.pdf", "application/pdf", b""),
                upload("large.pdf", "application/pdf", b"%PDF-" + b"x" * 20),
                upload("spoofed.pdf", "application/pdf", b"<html>unsafe</html>"),
                upload("mismatch.jpg", "application/pdf", b"%PDF-1.4"),
                upload("script.svg", "image/svg+xml", b"<svg/>"),
            )
            for candidate in bad:
                with self.subTest(filename=candidate.filename), self.assertRaises(HTTPException):
                    asyncio.run(private_document_storage.store_verification_document(1, candidate))

    def test_malicious_filename_is_only_safe_display_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            settings.PRIVATE_DOCUMENT_MODE = "local"; settings.PRIVATE_DOCUMENT_ROOT = Path(directory); settings.PRIVATE_DOCUMENT_MAX_BYTES = 1024
            stored = asyncio.run(private_document_storage.store_verification_document(1, upload("../../evil\x00name.pdf", "application/pdf", b"%PDF-1.4")))
            self.assertEqual(stored.original_name, "evilname.pdf")
            self.assertNotIn("evil", stored.storage_key)

    def test_s3_adapter_forces_encryption_private_cache_and_supports_stream_delete(self):
        fake = FakeS3(); settings.PRIVATE_DOCUMENT_S3_BUCKET = "private-bucket"; settings.PRIVATE_DOCUMENT_S3_ENCRYPTION = "AES256"; settings.PRIVATE_DOCUMENT_S3_KMS_KEY_ID = ""
        provider = private_document_storage.S3PrivateDocumentProvider(fake)
        key = provider.put(scope="verification", source=BytesIO(b"%PDF-1.4"), content_type="application/pdf", extension=".pdf", size=8, checksum="a" * 64)
        sent = fake.puts[0]
        self.assertEqual(sent["Bucket"], "private-bucket"); self.assertEqual(sent["ServerSideEncryption"], "AES256")
        self.assertEqual(sent["CacheControl"], "private, no-store, max-age=0"); self.assertNotIn("ACL", sent)
        stream = provider.open(key); self.assertEqual(b"".join(stream.chunks), b"%PDF-1.4 stored"); stream.close(); self.assertTrue(fake.body.closed)
        provider.delete(key); self.assertEqual(fake.deletes[0]["Key"], key)

    def test_s3_upload_recovers_a_lost_success_response_by_checksum(self):
        fake = FakeS3(); settings.PRIVATE_DOCUMENT_S3_BUCKET = "private-bucket"
        fake.put_object = lambda **kwargs: (_ for _ in ()).throw(TimeoutError())
        provider = private_document_storage.S3PrivateDocumentProvider(fake)
        key = provider.put(scope="verification", source=BytesIO(b"%PDF-1.4"), content_type="application/pdf", extension=".pdf", size=8, checksum="a" * 64)
        self.assertTrue(key.startswith("private/verification/"))

    def test_storage_failures_missing_object_and_invalid_body_are_safe(self):
        settings.PRIVATE_DOCUMENT_S3_BUCKET = "private-bucket"
        key = "private/verification/aa/" + "b" * 32 + ".pdf"

        unavailable = FakeS3()
        unavailable.put_object = lambda **kwargs: (_ for _ in ()).throw(TimeoutError())
        unavailable.head_object = lambda **kwargs: (_ for _ in ()).throw(ProviderError("NotFound"))
        provider = private_document_storage.S3PrivateDocumentProvider(unavailable)
        with self.assertRaises(HTTPException) as upload_error:
            provider.put(scope="verification", source=BytesIO(b"%PDF-1.4"), content_type="application/pdf", extension=".pdf", size=8, checksum="a" * 64)
        self.assertEqual(upload_error.exception.status_code, 503)

        missing = FakeS3()
        missing.get_object = lambda **kwargs: (_ for _ in ()).throw(ProviderError("NoSuchKey"))
        with self.assertRaises(HTTPException) as missing_error:
            private_document_storage.S3PrivateDocumentProvider(missing).open(key)
        self.assertEqual(missing_error.exception.status_code, 404)

        malformed = FakeS3()
        malformed.get_object = lambda **kwargs: {"Body": object()}
        with self.assertRaises(HTTPException) as malformed_error:
            private_document_storage.S3PrivateDocumentProvider(malformed).open(key)
        self.assertEqual(malformed_error.exception.status_code, 503)

        unavailable.delete_object = lambda **kwargs: (_ for _ in ()).throw(TimeoutError())
        with self.assertRaises(RuntimeError):
            provider.delete(key)

        with self.assertRaises(HTTPException) as traversal_error:
            provider.open("private/verification/../../secret.pdf")
        self.assertEqual(traversal_error.exception.status_code, 404)

    def test_download_response_is_attachment_no_store_and_nosniff(self):
        with tempfile.TemporaryDirectory() as directory:
            settings.PRIVATE_DOCUMENT_MODE = "local"; settings.PRIVATE_DOCUMENT_ROOT = Path(directory); settings.PRIVATE_DOCUMENT_MAX_BYTES = 1024
            stored = asyncio.run(private_document_storage.store_verification_document(1, upload("proof.pdf", "application/pdf", b"%PDF-1.4")))
            response = private_document_storage.download_response(stored.storage_key, filename=stored.original_name, content_type=stored.content_type)
            self.assertEqual(response.headers["cache-control"], "private, no-store, max-age=0")
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")
            self.assertTrue(response.headers["content-disposition"].startswith("attachment;"))


class PrivateDocumentLifecycleTests(unittest.TestCase):
    def setUp(self): self.db = SessionLocal()
    def tearDown(self): self.db.rollback(); self.db.close()

    def test_delete_failure_is_observable_and_retried(self):
        key = f"private/verification/aa/{uuid.uuid4().hex}.pdf"
        now = datetime.now(timezone.utc)
        job = private_document_lifecycle_service.enqueue(self.db, key, reason="test replacement", now=now)
        self.db.commit()
        with patch.object(private_document_storage, "delete_document", side_effect=RuntimeError("provider unavailable")):
            self.assertEqual(private_document_lifecycle_service.run_due(self.db, now=now + timedelta(seconds=1)), 0)
        self.db.refresh(job); self.assertEqual(job.status, PrivateDocumentDeletionStatus.FAILED); self.assertEqual(job.attempts, 1); self.assertNotIn("provider unavailable", job.last_error or "")
        job.next_retry_at = now - timedelta(seconds=1); self.db.commit()
        with patch.object(private_document_storage, "delete_document") as deletion:
            self.assertEqual(private_document_lifecycle_service.run_due(self.db, now=now), 1)
        self.db.refresh(job); self.assertEqual(job.status, PrivateDocumentDeletionStatus.COMPLETED); deletion.assert_called_once_with(key)
        self.db.delete(job); self.db.commit()


if __name__ == "__main__": unittest.main()
