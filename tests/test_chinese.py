import unittest
from pathlib import Path

from pdf_fmt.formatting import clean_and_lint_text
from pdf_fmt.spell.chinese import convert_chinese

CORPUS = Path(__file__).parent / 'fixtures' / 'zh_corpus.tsv'


class TestChineseConversion(unittest.TestCase):

    def test_corpus(self):
        for line in CORPUS.read_text(encoding='utf-8').splitlines():
            locale, source, expected = line.split('\t')
            with self.subTest(locale=locale, source=source):
                self.assertEqual(convert_chinese(source, locale), expected)

    def test_non_chinese_locale_is_unchanged(self):
        self.assertEqual(convert_chinese('这个文件', 'en-GB'), '这个文件')

    def test_clean_and_lint_text_converts(self):
        self.assertEqual(clean_and_lint_text('这个文件', 'zh-TW', []), '這個文件')


if __name__ == '__main__':
    unittest.main()
