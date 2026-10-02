"""Small local media adapter for development/self-hosted Maharashtra Tourist Places deployments."""

from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings


ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _valid_signature(content_type: str, data: bytes) -> bool:
    signatures = {
        "image/jpeg": (b"\xff\xd8\xff",),
        "image/png": (b"\x89PNG\r\n\x1a\n",),
        "image/webp": (b"RIFF",),
    }
    if not data.startswith(signatures[content_type]):
        return False
    return content_type != "image/webp" or data[8:12] == b"WEBP"


async def store_hotel_image(hotel_id: int, file: UploadFile) -> tuple[str, str, str, int]:
    return await _store_image(f"hotels/{hotel_id}", file)


async def store_campaign_creative(hotel_id: int, campaign_id: int, file: UploadFile) -> tuple[str, str, str, int]:
    return await _store_image(f"hotels/{hotel_id}/campaigns/{campaign_id}", file)


async def store_external_campaign_creative(advertiser_id: int, campaign_id: int, file: UploadFile) -> tuple[str, str, str, int, int, int]:
    """Store a sanitized public advertising creative outside private documents."""
    return await _store_optimized_public_image(
        f"advertisers/{advertiser_id}/campaigns/{campaign_id}", file,
        minimum=(640, 360), label="Advertising creative",
    )


async def store_discovery_image(entity_type: str, entity_id: int, file: UploadFile) -> tuple[str, str, str, int, int, int]:
    """Validate, strip metadata, resize oversized sources, and encode a public WebP."""
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=422, detail="Only JPEG, PNG, and WebP images are supported")
    data = await file.read(settings.DISCOVERY_IMAGE_MAX_BYTES + 1)
    if not data:
        raise HTTPException(status_code=422, detail="Image file is empty")
    if len(data) > settings.DISCOVERY_IMAGE_MAX_BYTES:
        raise HTTPException(status_code=422, detail="Discovery image must be 8 MB or smaller")
    if not _valid_signature(content_type, data):
        raise HTTPException(status_code=422, detail="The file content does not match its image type")
    try:
        Image.MAX_IMAGE_PIXELS = settings.DISCOVERY_IMAGE_MAX_PIXELS
        with Image.open(BytesIO(data)) as source:
            source.verify()
        with Image.open(BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source)
            image.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            width, height = image.size
            if width < 640 or height < 360:
                raise HTTPException(status_code=422, detail="Discovery images must be at least 640 x 360 pixels")
            output = BytesIO()
            image.save(output, format="WEBP", quality=86, method=6)
            optimized = output.getvalue()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(status_code=422, detail="Image is corrupt or unsafe to process") from exc

    safe_type = entity_type.lower()
    if safe_type not in {"destination", "place"}:
        raise HTTPException(status_code=422, detail="Unsupported discovery media entity")
    storage_key = f"discovery/{safe_type}s/{entity_id}/{uuid4().hex}.webp"
    destination = settings.MEDIA_ROOT / Path(storage_key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(optimized)
    public_url = f"{settings.MEDIA_BASE_URL.rstrip('/')}{settings.MEDIA_URL}/{storage_key}"
    return public_url, storage_key, "image/webp", len(optimized), width, height


async def _store_optimized_public_image(folder: str, file: UploadFile, *, minimum: tuple[int, int], label: str) -> tuple[str, str, str, int, int, int]:
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=422, detail="Only JPEG, PNG, and WebP images are supported")
    data = await file.read(settings.HOTEL_IMAGE_MAX_BYTES + 1)
    if not data or len(data) > settings.HOTEL_IMAGE_MAX_BYTES:
        raise HTTPException(status_code=422, detail=f"{label} must be non-empty and 8 MB or smaller")
    if not _valid_signature(content_type, data):
        raise HTTPException(status_code=422, detail="The file content does not match its image type")
    try:
        Image.MAX_IMAGE_PIXELS = settings.DISCOVERY_IMAGE_MAX_PIXELS
        with Image.open(BytesIO(data)) as source: source.verify()
        with Image.open(BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source)
            image.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
            if image.mode not in {"RGB", "RGBA"}: image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            width, height = image.size
            if width < minimum[0] or height < minimum[1]:
                raise HTTPException(status_code=422, detail=f"{label} must be at least {minimum[0]} x {minimum[1]} pixels")
            output = BytesIO(); image.save(output, format="WEBP", quality=86, method=6); optimized = output.getvalue()
    except HTTPException: raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(status_code=422, detail="Image is corrupt or unsafe to process") from exc
    storage_key = f"{folder}/{uuid4().hex}.webp"
    destination = settings.MEDIA_ROOT / Path(storage_key); destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(optimized)
    return f"{settings.MEDIA_BASE_URL.rstrip('/')}{settings.MEDIA_URL}/{storage_key}", storage_key, "image/webp", len(optimized), width, height


async def _store_image(folder: str, file: UploadFile) -> tuple[str, str, str, int]:
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Only JPEG, PNG, and WebP images are supported")
    data = await file.read(settings.HOTEL_IMAGE_MAX_BYTES + 1)
    if not data:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Image file is empty")
    if len(data) > settings.HOTEL_IMAGE_MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Image must be 8 MB or smaller")
    if not _valid_signature(content_type, data):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="The file content does not match its image type")

    storage_key = f"{folder}/{uuid4().hex}{ALLOWED_IMAGE_TYPES[content_type]}"
    destination = settings.MEDIA_ROOT / Path(storage_key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    public_url = f"{settings.MEDIA_BASE_URL.rstrip('/')}{settings.MEDIA_URL}/{storage_key}"
    return public_url, storage_key, content_type, len(data)


def delete_stored_file(storage_key: str | None) -> None:
    if not storage_key:
        return
    target = (settings.MEDIA_ROOT / Path(storage_key)).resolve()
    media_root = settings.MEDIA_ROOT.resolve()
    if media_root not in target.parents:
        return
    target.unlink(missing_ok=True)
