import io
import unittest

from PIL import Image
from audit_umred_images import classify_duplicates, inspect_bytes, request_url


def encoded(size=(1280, 960), quality=85):
    image = Image.new("RGB", size, "#587932")
    output = io.BytesIO()
    image.save(output, format="WEBP", quality=quality)
    return output.getvalue()


class ImageAuditTests(unittest.TestCase):
    def test_actual_dimensions_decode_hash_and_thumbnail_rules(self):
        good = inspect_bytes(encoded())
        self.assertEqual(("WEBP", 1280, 960, "GOOD"), (good["format"], good["width"], good["height"], good["quality_status"]))
        self.assertEqual(64, len(good["checksum"]))
        small = inspect_bytes(encoded((320, 240)))
        self.assertEqual(("LOW_QUALITY", "THUMBNAIL_ONLY", False), (small["quality_status"], small["recommended_role"], small["processing_dimension_minimum_met"]))

    def test_corrupt_data_is_preserved_as_unusable_metadata(self):
        result = inspect_bytes(b"not an image")
        self.assertEqual((False, "UNUSABLE", "NOT_RECOMMENDED"), (result["decoding_succeeds"], result["quality_status"], result["recommended_role"]))

    def test_exact_duplicate_across_groups_does_not_resolve_ownership(self):
        a = dict(inspect_bytes(encoded()), family_id="lake", group="Lake", entity_resolution_status="ENTITY_RESOLUTION_REQUIRED")
        b = dict(a, family_id="park", group="Park")
        pairs = classify_duplicates([a, b])
        self.assertEqual("EXACT_DUPLICATE", pairs[0]["classification"])
        self.assertIsNone(pairs[0]["preferred_technical_candidate"])
        self.assertEqual(("Lake", "Park"), (a["group"], b["group"]))
        self.assertEqual("ENTITY_RESOLUTION_REQUIRED", b["entity_resolution_status"])

    def test_perceptual_similarity_is_candidate_only(self):
        a = dict(inspect_bytes(encoded(quality=70)), family_id="a")
        b = dict(inspect_bytes(encoded(quality=95)), family_id="b")
        self.assertNotEqual(a["checksum"], b["checksum"])
        self.assertEqual("LIKELY_VISUAL_DUPLICATE", classify_duplicates([a, b])[0]["classification"])

    def test_url_encoding_preserves_zero_width_character_and_restricts_source(self):
        raw = "https://maharashtratouristplaces.in/wp-content/uploads/lake\u200b.webp"
        self.assertEqual(request_url(raw), request_url(raw.replace("\u200b", "%E2%80%8B")))
        with self.assertRaises(ValueError):
            request_url("https://other.example/image.webp")


if __name__ == "__main__":
    unittest.main()
