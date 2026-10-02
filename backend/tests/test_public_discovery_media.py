import asyncio
from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from fastapi import HTTPException, UploadFile
from PIL import Image
from starlette.datastructures import Headers

from app.core.config import settings
from app.services import media_storage


def upload(data: bytes, content_type: str = "image/jpeg") -> UploadFile:
    return UploadFile(filename="discovery.jpg", file=BytesIO(data), headers=Headers({"content-type": content_type}))


def jpeg(width: int, height: int) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), (36, 92, 120)).save(output, "JPEG", quality=90)
    return output.getvalue()


class PublicDiscoveryMediaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_root = settings.MEDIA_ROOT
        self.previous_base = settings.MEDIA_BASE_URL
        self.temp = tempfile.TemporaryDirectory()
        settings.MEDIA_ROOT = Path(self.temp.name)
        settings.MEDIA_BASE_URL = "https://media.example.test"

    def tearDown(self) -> None:
        settings.MEDIA_ROOT = self.previous_root
        settings.MEDIA_BASE_URL = self.previous_base
        self.temp.cleanup()

    def test_valid_image_is_normalized_to_public_webp_with_dimensions(self) -> None:
        url, key, content_type, size, width, height = asyncio.run(
            media_storage.store_discovery_image("PLACE", 42, upload(jpeg(3000, 1800)))
        )
        self.assertEqual(content_type, "image/webp")
        self.assertLessEqual(width, 2400)
        self.assertLessEqual(height, 2400)
        self.assertGreater(size, 0)
        self.assertTrue(key.startswith("discovery/places/42/"))
        self.assertEqual(url, f"https://media.example.test/uploads/{key}")
        with Image.open(settings.MEDIA_ROOT / key) as stored:
            self.assertEqual(stored.format, "WEBP")
            self.assertNotIn("exif", stored.info)

    def test_spoofed_corrupt_and_small_images_are_rejected(self) -> None:
        cases = (
            upload(b"<script>not an image</script>"),
            upload(b"\xff\xd8\xffbroken"),
            upload(jpeg(320, 180)),
        )
        for value in cases:
            with self.subTest(size=value.size):
                with self.assertRaises(HTTPException) as caught:
                    asyncio.run(media_storage.store_discovery_image("PLACE", 42, value))
                self.assertEqual(caught.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main(verbosity=2)
