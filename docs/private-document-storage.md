# Private document storage

## Scope and data minimization

Maharashtra Tourist Places stores private files only where an existing operational workflow requires them:

- hotel partners may provide business registration evidence during paid hotel verification;
- a Safari may request a traveller document only when its server-managed `traveller_requirements` configuration explicitly requires that document type;
- Maharashtra Tourist Places operations may attach the official Safari ticket or permit when that Safari requires a confirmation document.

Ordinary hotel bookings do not collect Aadhaar or other identity copies. Public discovery imagery and advertising creative remain in the public media system. Payment receipts are generated from authoritative transaction records and are not copied into object storage.

## Architecture

`PrivateDocumentProvider` is the storage boundary. Local development uses a private, unmounted filesystem root. Production uses the Amazon S3 adapter through Boto3. Domain services authorize the hotel, verification, Safari request, traveller, and document record before invoking storage. Browser clients never receive S3 credentials, bucket names, object keys, or permanent URLs; authorized downloads are streamed by the API.

Uploads are read in 64 KiB chunks into a bounded spooled file. The default maximum is 10 MiB and the configurable hard ceiling is 20 MiB. Supported content is PDF, JPEG, and PNG. Maharashtra Tourist Places validates magic bytes, declared MIME type, and filename extension; HTML, SVG, archives, executables, empty files, and mismatches are rejected. Display filenames are normalized and sanitized. Object keys contain random identifiers only.

Every S3 PUT requests SSE-S3 (`AES256`) or configured SSE-KMS, sets `private, no-store` caching, and omits public ACLs. Downloads use `Content-Disposition: attachment`, `Cache-Control: private, no-store`, and `X-Content-Type-Options: nosniff`.

## Privacy and access

- Partner download: only the partner who owns the related hotel.
- Customer Safari download: only the customer who owns the Safari request.
- Admin download: only the existing explicit Admin permission boundary.
- Storage keys alone never authorize access.
- Upload and download events use the immutable audit log without recording content, identity numbers, object keys, or credentials.

Hotel replacement creates a new random object and records checksum/uploader/time metadata. The previous object is added to the deletion queue after the database points at the new object. Safari replacement follows the same rule per traveller/document type. The existing worker retries failed deletions. `PRIVATE_DOCUMENT_REPLACEMENT_RETENTION_DAYS` controls the delay; this is an operational control, not a legal-retention assertion.

## Amazon S3 configuration

Use a dedicated bucket in the configured region. Enable all four S3 Block Public Access controls, disable ACLs with bucket-owner-enforced Object Ownership, require TLS, and enable bucket versioning only if the approved retention policy accounts for noncurrent versions. S3 encrypts new objects by default; Maharashtra Tourist Places additionally sends an explicit SSE-S3 or SSE-KMS request. References: [S3 Block Public Access](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html), [S3 security best practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html), and [default bucket encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-bucket-encryption.html).

Prefer an attached workload role. If an S3-compatible provider requires static credentials, inject them only through the server secret manager. The application principal needs only these actions on `arn:aws:s3:::<bucket>/private/*`:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
    "Resource": "arn:aws:s3:::<bucket>/private/*"
  }]
}
```

Do not grant bucket creation/deletion, ACL, policy, website, or unrestricted account administration. SSE-KMS additionally requires the minimum encrypt/decrypt/data-key permissions on the selected KMS key.

## Required environment

Set `PRIVATE_DOCUMENT_MODE=s3`, bucket, region, addressing style, encryption mode, bounded timeouts, upload limit, deletion retry settings, and replacement-retention delay. `PRIVATE_DOCUMENT_S3_ENDPOINT_URL` is optional and must be HTTPS. `PRIVATE_DOCUMENT_S3_ACCESS_KEY_ID` and `PRIVATE_DOCUMENT_S3_SECRET_ACCESS_KEY` are optional as a pair; omit both when using workload identity. SSE-KMS requires a key ID. Production startup rejects local/disabled storage and incomplete or unsafe S3 configuration.

## Malware scanning launch gate

No malware scanner exists in the current infrastructure. Maharashtra Tourist Places does not claim that uploads are scanned. Documents remain private, are forced to download rather than render inline, and are restricted to validated types, but production use with real KYC/traveller evidence requires an approved malware-scanning/quarantine control. The retention owner must also approve document-type-specific retention periods before collecting real documents.

## Validation and rollback

In a non-production account, upload only a synthetic PDF/JPEG/PNG, verify authorized download and cross-tenant denial, replace it, run the worker, verify the retired object is deleted, and confirm bucket access logs/CloudTrail without logging content. Verify oversize, spoofed MIME, HTML/SVG, traversal names, unavailable storage, and deletion retry behavior. Never test with real KYC.

For rollback, stop uploads first, retain the database metadata and bucket, deploy the previous application with private-document routes disabled, and do not delete the bucket or objects. Forward-fix the adapter or configuration, then resume. A database downgrade removes reconciliation metadata and must not be used as an object-deletion mechanism.
