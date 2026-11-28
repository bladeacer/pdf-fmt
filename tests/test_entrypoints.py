import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pdf_fmt.main import main
from pdf_fmt.startup import StartupCheckError
from pdf_fmt.startup import checks as startup_checks

ROOT = Path(__file__).resolve().parent.parent


def load_script(filename: str, name: str):
    """Loads a root-level entry point as a module."""
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_script(filename: str) -> None:
    """Runs a root-level entry point as a script."""
    load_script(filename, "__main__")


class TestSharedEntryPoint(unittest.TestCase):

    def test_wrappers_share_the_implementation(self):
        self.assertIs(load_script("pdf-fmt.py", "local_entry").main, main)
        self.assertIs(load_script("build.py", "build_entry").main, main)

    def test_local_script_runs_the_venv_check(self):
        with patch("pdf_fmt.main.check_not_root") as not_root, \
             patch("pdf_fmt.main.check_venv") as venv, \
             patch("pdf_fmt.config.load_config", return_value={}) as load, \
             patch("pdf_fmt.parser.execute_main_pipeline") as pipeline:
            run_script("pdf-fmt.py")
        not_root.assert_called_once_with()
        venv.assert_called_once_with()
        load.assert_called_once_with()
        pipeline.assert_called_once_with({})

    def test_console_path_skips_the_venv_check(self):
        with patch("pdf_fmt.main.check_not_root") as not_root, \
             patch("pdf_fmt.main.check_venv") as venv, \
             patch("pdf_fmt.config.load_config", return_value={}), \
             patch("pdf_fmt.parser.execute_main_pipeline") as pipeline:
            main()
        not_root.assert_called_once_with()
        venv.assert_not_called()
        pipeline.assert_called_once_with({})

    def test_compiled_entry_point_skips_the_venv_check(self):
        with patch("pdf_fmt.main.check_not_root"), \
             patch("pdf_fmt.main.check_venv") as venv, \
             patch("pdf_fmt.config.load_config", return_value={}), \
             patch("pdf_fmt.parser.execute_main_pipeline") as pipeline:
            run_script("build.py")
        venv.assert_not_called()
        pipeline.assert_called_once_with({})

    def test_startup_error_keeps_its_exit_code(self):
        with patch(
            "pdf_fmt.main.check_not_root",
            side_effect=StartupCheckError("Root rejected", 3),
        ), patch("pdf_fmt.main.check_venv") as venv, \
             redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as raised:
                main(check_environment=True)
        self.assertEqual(raised.exception.code, 3)
        self.assertIn("Root rejected", output.getvalue())
        venv.assert_not_called()

    def test_pipeline_error_uses_one_exit_code(self):
        with patch("pdf_fmt.main.check_not_root"), \
             patch("pdf_fmt.config.load_config", return_value={}), \
             patch(
                 "pdf_fmt.parser.execute_main_pipeline",
                 side_effect=StartupCheckError("", 0),
             ), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main()
        self.assertEqual(raised.exception.code, 0)

    def test_windows_admin_is_rejected(self):
        with patch.object(
            startup_checks.platform, "system", return_value="Windows"
        ), patch.object(
            startup_checks.ctypes, "windll", create=True
        ) as windll:
            windll.shell32.IsUserAnAdmin.return_value = 1
            with self.assertRaises(StartupCheckError):
                startup_checks.check_not_root()

    def test_unexpected_error_exits_one(self):
        with patch("pdf_fmt.main.check_not_root"), \
             patch("pdf_fmt.config.load_config", side_effect=RuntimeError("boom")), \
             redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as raised:
                main()
        self.assertEqual(raised.exception.code, 1)
        self.assertIn("Unknown error: boom", output.getvalue())


if __name__ == "__main__":
    unittest.main()
