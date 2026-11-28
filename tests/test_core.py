import re
import unittest

from pdf_fmt.core import (
    NBSP,
    apply_regex_enclosure,
    compile_footer_patterns,
    contains_cjk,
    enforce_capitalization,
    format_indented_line,
    is_ft_factory,
    ln_cont_factory,
    post_process_content,
    preserve_case,
    replace_successive_spaces,
    split_fmt_line,
    tokenize_text,
)


class TestCoreFunctions(unittest.TestCase):

    def test_compile_footer_patterns_skips_invalid_regex(self):
        patterns = [r"page \d+", r"\d+/\d+", r"[0-9]+", r"("]
        self.assertEqual(len(compile_footer_patterns(patterns)), 3)

    def test_apply_regex_enclosure(self):
        text = "The quick brown fox jumps over the lazy dog."
        self.assertEqual(
            apply_regex_enclosure(text, r"fox|dog", "**"),
            "The quick brown **fox** jumps over the lazy **dog**.",
        )
        self.assertEqual(apply_regex_enclosure(text, "", "**"), text)
        self.assertEqual(apply_regex_enclosure(text, "(", "**"), text)

    def test_enforce_capitalization(self):
        self.assertEqual(enforce_capitalization(" already Capitalized"), " Already Capitalized")
        self.assertEqual(enforce_capitalization("hello world"), "Hello world")
        self.assertEqual(enforce_capitalization("  hello world"), "  Hello world")
        self.assertEqual(enforce_capitalization(" Already Capitalized"), " Already Capitalized")
        self.assertEqual(enforce_capitalization("1. hello world"), "1. hello world")
        self.assertEqual(enforce_capitalization("https://example.com"), "https://example.com")
        self.assertEqual(enforce_capitalization(""), "")

    def test_replace_successive_spaces(self):
        text = "  This   has  many \t spaces \n in it. "
        self.assertEqual(replace_successive_spaces(text), "This has many spaces in it.")
        self.assertEqual(replace_successive_spaces("  中文   测试  "), "中文 测试")

    def test_preserve_case(self):
        self.assertEqual(preserve_case("COLOR", "colour"), "COLOUR")
        self.assertEqual(preserve_case("Color", "colour"), "Colour")
        self.assertEqual(preserve_case("ResNet", "resnet"), "Resnet")
        self.assertEqual(preserve_case("cOlOr", "colour"), "colour")
        self.assertEqual(preserve_case("中文", "中文"), "中文")
        self.assertEqual(preserve_case("", "colour"), "colour")

    def test_split_fmt_line_wrapping_and_capitalization(self):
        line = "this is a very long sentence that needs to be broken into multiple lines at a sensible break point."
        pieces = split_fmt_line(line, 50, True)
        self.assertEqual(len(pieces), 3)
        self.assertTrue(pieces[0].startswith("This"))
        self.assertEqual(split_fmt_line("中文测试", 0, False), ["中文测试"])

    def test_cjk_wrapping_keeps_punctuation(self):
        text = "这是第一段中文文本，接着是第二段文本。"
        pieces = split_fmt_line(text, 12, False, "zh-CN")
        self.assertEqual("".join(pieces), text)
        self.assertTrue(all(len(piece) <= 12 for piece in pieces))
        self.assertFalse(any(piece.startswith("。") for piece in pieces))

    def test_locale_aware_case(self):
        self.assertEqual(preserve_case("中文", "中文", "zh-CN"), "中文")
        self.assertEqual(enforce_capitalization("中文", "zh-CN"), "中文")
        self.assertEqual(preserve_case("COLOR", "colour", "en-US"), "COLOUR")

    def test_contains_cjk(self):
        self.assertTrue(contains_cjk("中文 test"))
        self.assertFalse(contains_cjk("plain ASCII"))

    def test_tokenize_text_keeps_cjk_and_whitespace(self):
        self.assertEqual(
            tokenize_text("中文 with\u00A0spaces"),
            ["中文", " ", "with", "\u00A0", "spaces"],
        )

    def test_ln_cont_factory(self):
        restricted = ln_cont_factory(re.compile(r"[a-zA-Z\s]+"))
        self.assertEqual(restricted("123. Hello-world! 456. "), "Hello world")

        unicode_filter = ln_cont_factory(re.compile(r"[\w\s]+"))
        self.assertEqual(unicode_filter("中文 test!"), "中文 test")

    def test_format_indented_line(self):
        self.assertEqual(format_indented_line(" first item"), "- first item")
        self.assertEqual(format_indented_line("  second item"), "  second item")
        self.assertEqual(format_indented_line(f"{NBSP}third item"), "- third item")
        self.assertEqual(format_indented_line("- listed"), "- listed")

    def test_is_ft_factory(self):
        patterns = [r"^\s*\d+\s*$", r"^.*Copyright.*$"]
        is_footer = is_ft_factory(compile_footer_patterns(patterns))
        self.assertTrue(is_footer(" 5 "))
        self.assertTrue(is_footer("Copyright 2024"))
        self.assertFalse(is_footer("Normal line."))
        self.assertFalse(is_footer("   "))

    def test_post_process_content(self):
        lines = ["Line one [1, 2, 3]", "Line two: TODO", "Line three."]
        config = {
            "formatting": {
                "regex_enclosures": [
                    {"pattern": r"\[.*?\]", "wrapper": "`"},
                    {"pattern": r"TODO", "wrapper": "!"},
                    {"pattern": r"one", "wrapper": "*"},
                ]
            }
        }
        self.assertEqual(
            post_process_content(lines, config),
            "Line *one* `[1, 2, 3]`\nLine two: !TODO!\nLine three.",
        )
        self.assertEqual(post_process_content(["中文测试"], {"formatting": {}}), "中文测试")


if __name__ == "__main__":
    unittest.main()
