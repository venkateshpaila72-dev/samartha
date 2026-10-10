"""Unit tests for deterministic crop matching logic."""

import unittest
from app.services.crop_profile_service import CropProfileService


class TestCropMatchingUnit(unittest.TestCase):
    def test_exact_crop_match(self):
        match = CropProfileService.match_crop_profile(
            crop_name="Paddy (Rice)",
            crop_form="Threshed Raw Paddy Grain",
            storage_type="Warehouse / Hermetic Bag / Traditional Bin",
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.matched_profile.crop_id, "paddy_grain_ambient")
        self.assertEqual(match.match_confidence, "high")
        self.assertEqual(match.matched_profile.recommended_temperature_min_c, 15.0)
        self.assertEqual(match.matched_profile.recommended_crop_moisture_percent, 13.0)

    def test_fuzzy_crop_name_match(self):
        # User enters 'rice' or 'corn'
        match_rice = CropProfileService.match_crop_profile(crop_name="rice")
        self.assertIsNotNone(match_rice)
        self.assertEqual(match_rice.matched_profile.crop_id, "paddy_grain_ambient")

        match_corn = CropProfileService.match_crop_profile(crop_name="corn")
        self.assertIsNotNone(match_corn)
        self.assertEqual(match_corn.matched_profile.crop_id, "maize_grain_ambient")

    def test_vegetable_profile_match(self):
        match_onion = CropProfileService.match_crop_profile(crop_name="Onion")
        self.assertIsNotNone(match_onion)
        self.assertEqual(match_onion.matched_profile.crop_id, "onion_bulb_ambient_ventilated")
        self.assertEqual(match_onion.matched_profile.recommended_temperature_max_c, 30.0)
        self.assertEqual(match_onion.matched_profile.recommended_relative_humidity_max_percent, 72.0)


if __name__ == "__main__":
    unittest.main()
