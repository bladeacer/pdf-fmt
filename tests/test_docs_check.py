import unittest

from tools.check_docs import doc_files, em_dash_lines


class TestDocsCheck(unittest.TestCase):

    def test_em_dash_lines(self):
        self.assertEqual(em_dash_lines(["plain text", "bad \u2014 here", "also \u2014 bad"]), [2, 3])
        self.assertEqual(em_dash_lines(["hyphen - here", "en dash \u2013 here"]), [])

    def test_docs_in_scope(self):
        names = {path.name for path in doc_files()}
        self.assertIn("README.md", names)
        self.assertIn("plan.md", names)
        self.assertNotIn("SKILL.md", names)


if __name__ == "__main__":
    unittest.main()
