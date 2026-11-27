import unittest

from pdf_fmt.spell import enforce_spelling, locale_checks
from pdf_fmt.spell.english import apply_curated_map
from pdf_fmt.spell.locale import (
    auto_apply_categories,
    auto_locale,
    detect_script,
    normalize_locale,
)


class TestLocaleValidation(unittest.TestCase):

    def test_normalize_locale(self):
        self.assertEqual(normalize_locale("EN-us"), "en-US")
        self.assertEqual(normalize_locale(" zh-hk "), "zh-HK")
        self.assertEqual(normalize_locale("off"), "off")

    def test_legacy_values_are_rejected(self):
        for value in ("en-UK", "none"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_locale(value)

    def test_unsupported_values_are_rejected(self):
        with self.assertRaises(ValueError):
            normalize_locale("fr-FR")

    def test_script_detection(self):
        self.assertEqual(detect_script("简体中文"), "hans")
        self.assertEqual(detect_script("繁體中文"), "hant")
        self.assertEqual(detect_script("简体繁體"), "mixed")
        self.assertEqual(detect_script("plain text"), "latin")

    def test_auto_locale(self):
        self.assertEqual(auto_locale("off", "简体中文", True), "zh-CN")
        self.assertEqual(auto_locale("en-US", "繁體中文", True), "zh-TW")
        self.assertEqual(auto_locale("off", "简体中文", False), "off")

    def test_auto_apply_categories(self):
        config = {"filters": {"linting": {"auto_apply": {"grammar": True}}}}
        self.assertEqual(
            auto_apply_categories(config),
            {"variant": True, "grammar": True, "style": False},
        )


class TestCuratedSpelling(unittest.TestCase):

    def test_curated_map(self):
        self.assertEqual(apply_curated_map("localization", "en-GB"), "localisation")
        self.assertEqual(apply_curated_map("localisation", "en-US"), "localization")

    def test_curated_map_fills_upstream_gap(self):
        self.assertEqual(
            enforce_spelling("Localization and localization.", "en-GB", []),
            "Localisation and localisation.",
        )

    def test_locale_checks_uses_per_locale_dictionary(self):
        config = {
            "filters": {
                "linting": {
                    "spelling": {
                        "enforce_locale": "en-GB",
                        "ignore_locale_strings": {
                            "en-GB": ["localization"],
                            "en-US": [],
                        },
                    }
                }
            }
        }
        self.assertEqual(locale_checks(config), ("en-GB", ["localization"]))


if __name__ == "__main__":
    unittest.main()
