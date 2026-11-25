import unittest
from typing import Any, Dict

from pdf_fmt.core import DEFAULT_CHARS_REGEX
from pdf_fmt.formatting import clean_and_lint_text
from pdf_fmt.processing import (
    PageProcessArgs,
    _process_page_text_block,
    _to_markdown_table,
)
from pdf_fmt.spell import enforce_spelling, locale_checks

FOOTER_REGEXES = [
    r"^\s*\d+\s*$",
    r"^.*\s*[A-Za-z]+\d+\s.*$",
    r"^.*\d+S\d+[vV]\d+.*$",
    r"^.*Copyright.*$",
    r"^.*Official.*$",
    r"^.*Private.*$",
    r"^.*All rights reserved.*$",
    r"^.*(?:AY\s?)?\d{4}.*$",
    r"^.*v\d\.\d$",
    r"^Page\s\d.*$",
]


def make_args(**kwargs: Any) -> PageProcessArgs:
    config: Dict[str, Any] = {
        "filters": {
            "allowed_chars_regex": kwargs.get("allowed_chars_regex", DEFAULT_CHARS_REGEX),
            "footer_regexes": kwargs.get("footer_regexes", FOOTER_REGEXES),
        },
        "formatting": {
            "page_separator": kwargs.get("page_separator", "___"),
            "min_chars_per_line": kwargs.get("min_chars_per_line", 0),
            "max_chars_per_line": kwargs.get("max_chars_per_line", 0),
            "enforce_line_capitalization": kwargs.get("enforce_cap", False),
        },
    }
    return PageProcessArgs(
        page_num=kwargs.get("page_num", 0),
        page_text=kwargs.get("page_text", ""),
        config=config,
        allowed_chars_regex=config["filters"]["allowed_chars_regex"],
        footer_patterns=config["filters"]["footer_regexes"],
        spelling_locale=kwargs.get("spelling_locale", "en-US"),
        ignore_list=kwargs.get("ignore_list", []),
        total_pages=kwargs.get("total_pages", 1),
    )


class TestSpelling(unittest.TestCase):

    def test_enforce_spelling_uk(self):
        text = "This is a great Color, organization, filter, and connection."
        result = enforce_spelling(text, "en-UK", ["filter", "connection"])
        self.assertEqual(result, "This is a great Colour, organisation, filter, and connection.")

    def test_enforce_spelling_us(self):
        result = enforce_spelling("This is a great colour and organisation.", "en-US", [])
        self.assertEqual(result, "This is a great color and organization.")

    def test_enforce_spelling_unknown_locale(self):
        text = "This is a great colour and organization."
        self.assertEqual(enforce_spelling(text, "none", []), text)

    def test_locale_checks(self):
        config = {
            "filters": {
                "linting": {
                    "spelling": {
                        "enforce_locale": "en-UK",
                        "ignore_locale_strings": ["filter"],
                    }
                }
            }
        }
        self.assertEqual(locale_checks(config), ("en-UK", ["filter"]))
        self.assertEqual(locale_checks({}), ("en-US", []))

    def test_clean_and_lint_text(self):
        self.assertEqual(
            clean_and_lint_text("This is a great colour!", "en-US", []),
            "This is a great color!",
        )
        self.assertEqual(
            clean_and_lint_text("  中文   测试  ", "none", []),
            "中文 测试",
        )


class TestPageProcessing(unittest.TestCase):

    def test_page_separator(self):
        british = make_args(page_num=1, page_text="Content", total_pages=3, page_separator="___")
        self.assertEqual(_process_page_text_block(british)[-1], "\n\n___\n\n")

        labelled = make_args(
            page_num=1,
            page_text="Content",
            total_pages=3,
            page_separator="--- PAGE SEPARATOR ---",
        )
        self.assertEqual(_process_page_text_block(labelled)[-1], "\n\n--- Page 2 ---\n\n")

        none = make_args(page_num=1, page_text="Content", total_pages=3, page_separator="none")
        self.assertEqual(_process_page_text_block(none), ["Content"])

        last = make_args(page_num=1, page_text="Content", total_pages=2)
        self.assertEqual(_process_page_text_block(last), ["Content"])

    def test_min_chars_per_line(self):
        page_text = "Line One (Long)\nShort\nLine Three (Long)"
        separate = _process_page_text_block(make_args(page_text=page_text, min_chars_per_line=0))
        self.assertEqual(len(separate), 3)

        joined = _process_page_text_block(make_args(page_text=page_text, min_chars_per_line=20))
        self.assertEqual(joined, ["Line One (Long) Short Line Three (Long)"])

    def test_max_chars_per_line(self):
        page_text = "A very long sentence that will be split if max_chars is set to a small value."
        self.assertEqual(len(_process_page_text_block(make_args(page_text=page_text))), 1)
        wrapped = _process_page_text_block(make_args(page_text=page_text, max_chars_per_line=30))
        self.assertGreater(len(wrapped), 1)

    def test_enforce_line_capitalization(self):
        page_text = "line one starts with lower case."
        plain = make_args(page_text=page_text, max_chars_per_line=100)
        self.assertIn("line one starts with lower case.", _process_page_text_block(plain))

        capped = make_args(page_text=page_text, max_chars_per_line=100, enforce_cap=True)
        self.assertIn("Line one starts with lower case.", _process_page_text_block(capped))

    def test_footer_filtering(self):
        page_text = "Normal line.\nPage 5 out of 10.\nIT1234 - Module Code\n\n25\n\nCopyright 2024"
        self.assertEqual(_process_page_text_block(make_args(page_text=page_text)), ["Normal line."])

    def test_allowed_chars_regex(self):
        page_text = "Line 1: 100!\nLine 2: 200."
        result = _process_page_text_block(
            make_args(
                page_text=page_text,
                allowed_chars_regex=r"[a-zA-Z0-9\s]+",
                min_chars_per_line=50,
            )
        )
        self.assertEqual(result, ["Line 1 100 Line 2 200"])


class TestMarkdownTable(unittest.TestCase):

    def test_to_markdown_table(self):
        table = _to_markdown_table([["A", "B"], ["1", "2"]])
        self.assertIn("| A | B |", table)
        self.assertIn("| --- | --- |", table)
        self.assertIn("| 1 | 2 |", table)


if __name__ == "__main__":
    unittest.main()
