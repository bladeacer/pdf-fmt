import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import yaml

from pdf_fmt.config import CONFIG_FILENAME, clear_config_cache, load_config
from pdf_fmt.core import DEFAULT_CHARS_REGEX
from pdf_fmt.parser import _get_validated_cores, _run_image_pipeline
from pdf_fmt.parser import images as image_pipeline_module
from pdf_fmt.processing import PageProcessArgs, _run_processing_pool
from pdf_fmt.processing import pool as pool_module
from pdf_fmt.spell import _english_backend, enforce_spelling


def page_args(text: str) -> PageProcessArgs:
    """Builds a page block that needs two cores to enter the pool."""
    return PageProcessArgs(
        page_num=0,
        page_text=text,
        config={"formatting": {}},
        allowed_chars_regex=DEFAULT_CHARS_REGEX,
        footer_patterns=[],
        spelling_locale="off",
        ignore_list=[],
        total_pages=2,
    )


class TestCoreValidation(unittest.TestCase):

    @patch("pdf_fmt.parser.os.cpu_count", return_value=None)
    def test_missing_cpu_count_uses_one_core(self, _count):
        self.assertEqual(_get_validated_cores({}), 1)

    @patch("pdf_fmt.parser.os.cpu_count", return_value=8)
    def test_configured_and_fallback_core_counts(self, _count):
        self.assertEqual(_get_validated_cores({"processing": {"cores": 4}}), 4)
        self.assertEqual(_get_validated_cores({"processing": {"cores": 0}}), 7)
        self.assertEqual(_get_validated_cores({"processing": {"cores": "bad"}}), 7)


class TestImageProcessReaping(unittest.TestCase):

    def _run(self, alive_results, expected_joins, killed):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            actions = {"image_dir": str(root / "images")}
            process = MagicMock()
            process.is_alive.side_effect = alive_results
            with patch.object(
                image_pipeline_module.multiprocessing, "Process", return_value=process
            ), patch.object(
                image_pipeline_module, "_discard_similar_images"
            ) as discard, redirect_stdout(io.StringIO()) as output:
                _run_image_pipeline(str(root / "sample.pdf"), actions, 1)
            process.start.assert_called_once_with()
            self.assertEqual(process.join.call_args_list, expected_joins)
            process.terminate.assert_called_once_with()
            if killed:
                process.kill.assert_called_once_with()
            else:
                process.kill.assert_not_called()
            discard.assert_called_once()
            self.assertIn("timed out", output.getvalue())

    def test_timed_out_process_is_reaped(self):
        self._run(
            [True, False],
            [call(timeout=120), call(timeout=30)],
            killed=False,
        )

    def test_unstoppable_process_is_killed(self):
        self._run(
            [True, True, False],
            [call(timeout=120), call(timeout=30), call(timeout=30)],
            killed=True,
        )


class TestPoolErrors(unittest.TestCase):

    def test_start_failure_falls_back_to_sequential(self):
        blocks = [page_args("Alpha."), page_args("Beta.")]
        with patch.object(
            pool_module.multiprocessing, "Pool", side_effect=OSError("no spawn")
        ), redirect_stdout(io.StringIO()) as output:
            result = _run_processing_pool(blocks, 2)
        self.assertEqual(result, ["Alpha.", "Beta."])
        self.assertIn("Falling back to sequential", output.getvalue())

    def test_worker_error_is_not_masked(self):
        fake_pool = MagicMock()
        fake_pool.__enter__.return_value = fake_pool
        fake_pool.map.side_effect = ValueError("backend bug")
        blocks = [page_args("Alpha."), page_args("Beta.")]
        with patch.object(
            pool_module.multiprocessing, "Pool", return_value=fake_pool
        ), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "backend bug"):
                _run_processing_pool(blocks, 2)


class TestLazyEnglishBackend(unittest.TestCase):

    def setUp(self):
        _english_backend.cache_clear()
        self.addCleanup(_english_backend.cache_clear)

    def test_backend_is_loaded_once_per_process(self):
        enforce_spelling("color", "en-GB", [])
        enforce_spelling("colour", "en-US", [])
        info = _english_backend.cache_info()
        self.assertEqual(info.misses, 1)
        self.assertEqual(info.hits, 1)

    def test_missing_backend_raises_an_explicit_error(self):
        with patch.dict(sys.modules, {"breame.spelling": None}):
            with self.assertRaisesRegex(RuntimeError, "breame"):
                enforce_spelling("colour", "en-GB", [])


class TestConfigCache(unittest.TestCase):

    def test_path_and_mtime_changes_reload_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_dir = root / "first"
            second_dir = root / "second"
            first_dir.mkdir()
            second_dir.mkdir()

            def write_config(directory: Path, cores: int) -> Path:
                path = directory / CONFIG_FILENAME
                path.write_text(
                    yaml.safe_dump({"processing": {"cores": cores}}),
                    encoding="utf-8",
                )
                return path

            first = write_config(first_dir, 2)
            second = write_config(second_dir, 3)
            self.addCleanup(clear_config_cache)
            clear_config_cache()

            with patch.dict(os.environ, {"PDF_FMT_CONFIG_PATH": str(first)}), \
                 redirect_stdout(io.StringIO()):
                self.assertEqual(load_config()["processing"]["cores"], 2)
            with patch.dict(os.environ, {"PDF_FMT_CONFIG_PATH": str(second)}), \
                 redirect_stdout(io.StringIO()):
                self.assertEqual(load_config()["processing"]["cores"], 3)

                updated = {"processing": {"cores": 4}}
                second.write_text(yaml.safe_dump(updated), encoding="utf-8")
                future = os.path.getmtime(second) + 10
                os.utime(second, (future, future))
                self.assertEqual(load_config()["processing"]["cores"], 4)

                clear_config_cache()
                self.assertEqual(load_config()["processing"]["cores"], 4)


if __name__ == "__main__":
    unittest.main()
