import importlib.util
import unittest

from pdf_fmt.spell.harper import load_harper
from pdf_fmt.spell.native_zh import load_opencc


class TestOptionalBackends(unittest.TestCase):

    @unittest.skipIf(importlib.util.find_spec('harper') is not None, 'Harper installed')
    def test_harper_reports_missing_wheel(self):
        with self.assertRaises(RuntimeError):
            load_harper()

    @unittest.skipIf(importlib.util.find_spec('opencc') is not None, 'OpenCC installed')
    def test_opencc_reports_missing_wheel(self):
        with self.assertRaises(RuntimeError):
            load_opencc()


if __name__ == '__main__':
    unittest.main()
