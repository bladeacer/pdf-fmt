import unittest
from datetime import date

from pdf_fmt.formatting import add_cjk_spacing, clean_and_lint_text, fix_spacing
from pdf_fmt.formatting.locale_format import (
    format_locale_currency,
    format_locale_date,
    format_locale_number,
)
from pdf_fmt.formatting.typography import apply_typography
from pdf_fmt.spell import enforce_spelling


class TestSpacing(unittest.TestCase):

    def test_fix_spacing_is_unicode_aware(self):
        self.assertEqual(fix_spacing("helloWorld"), "hello World")
        self.assertEqual(fix_spacing(" naïveÉlan"), " naïve Élan")
        self.assertEqual(fix_spacing("中文ABC"), "中文ABC")

    def test_add_cjk_spacing(self):
        self.assertEqual(add_cjk_spacing("使用Python3处理文本"), "使用 Python3 处理文本")
        self.assertEqual(add_cjk_spacing("纯中文文本"), "纯中文文本")

    def test_clean_and_lint_text_for_zh(self):
        self.assertEqual(
            clean_and_lint_text("  使用Python3  处理文本  ", "zh-CN", []),
            "使用 Python3 处理文本",
        )


class TestTypography(unittest.TestCase):

    def test_quotes_and_ellipsis(self):
        self.assertEqual(
            apply_typography('He said "hi" ...', "en-US"),
            'He said \u201chi\u201d \u2026',
        )
        self.assertEqual(apply_typography('"hi"', "en-GB"), "\u2018hi\u2019")

    def test_dashes_are_locale_scoped(self):
        self.assertEqual(apply_typography("one--two", "en-US"), "one\u2013two")
        self.assertEqual(apply_typography("one--two", "zh-CN"), "one--two")


class TestLocaleFormatting(unittest.TestCase):

    def test_babel_hooks(self):
        self.assertEqual(format_locale_date(date(2026, 11, 27), "en-US"), "Nov 27, 2026")
        self.assertEqual(format_locale_number(1234.5, "de-DE"), "1.234,5")
        self.assertIn("$", format_locale_currency(12.5, "USD", "en-US"))


class TestSpellWhitespace(unittest.TestCase):

    def test_whitespace_and_unicode_words_survive(self):
        text = "  colour\torganisation\n中文  "
        self.assertEqual(enforce_spelling(text, "en-US", []), "  color\torganization\n中文  ")


if __name__ == "__main__":
    unittest.main()
