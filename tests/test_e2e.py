import io
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import yaml
from PIL import Image

from pdf_fmt.config import (
    CONFIG_FILENAME,
    clear_config_cache,
    find_config_file,
    load_config,
)
from pdf_fmt.conversion import convert_to_pdf
from pdf_fmt.core import DEFAULT_CHARS_REGEX, DEFAULT_CONVERT_FORMATS
from pdf_fmt.image import _discard_similar_images, _extract_and_format_images
from pdf_fmt.parser import execute_main_pipeline
from pdf_fmt.processing import extract_text_from_pdf
from tests.fixtures.pdf_builder import build_pdf

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'pdf-fmt.py'
BINARY = ROOT / 'build' / 'pdf-fmt'
PAGES = [
    ['Hello World from page one.', 'Colour and organisation.', 'Copyright 2024'],
    ['Second page text.'],
    ['Third page text.'],
]


def write_pdf(root: Path, pages: list[list[str]] | None = None, **kwargs: Any) -> Path:
    """Writes a fixture PDF with the shared or caller-supplied pages."""
    path = root / 'sample.pdf'
    path.write_bytes(build_pdf(pages or PAGES, **kwargs))
    return path


def base_config(root: Path, image: bool = False, locale: str = 'en-GB') -> Dict[str, Any]:
    """Returns a config that enables file output and disables clipboard writes."""
    actions: Dict[str, Any] = {'copy': False, 'write_file': str(root / 'out.md')}
    if image:
        actions['image_dir'] = str(root / 'images')
    return {
        'filters': {
            'allowed_chars_regex': DEFAULT_CHARS_REGEX,
            'footer_regexes': [r'^.*Copyright.*$'],
            'linting': {
                'spelling': {
                    'enforce_locale': locale,
                    'ignore_locale_strings': {'en-GB': [], 'en-US': []},
                }
            },
        },
        'conversion': {'supported_formats': DEFAULT_CONVERT_FORMATS},
        'processing': {'cores': 1},
        'formatting': {
            'min_chars_per_line': 0,
            'max_chars_per_line': 0,
            'page_separator': '___',
            'enforce_line_capitalization': False,
            'extract_table': {},
        },
        'actions': actions,
    }


def write_config(root: Path, config: Dict[str, Any]) -> None:
    """Writes a config file that the CLI discovers through the current directory."""
    (root / CONFIG_FILENAME).write_text(
        yaml.safe_dump(config, sort_keys=False), encoding='utf-8'
    )


def cli_environment() -> Dict[str, str]:
    """Returns an environment that skips the venv check."""
    env = dict(os.environ)
    env['PDF_FMT_CI_BUILD'] = '1'
    env.pop('PDF_FMT_CONFIG_PATH', None)
    return env


class TestCliE2E(unittest.TestCase):

    @unittest.skipIf(hasattr(os, 'geteuid') and os.geteuid() == 0, 'root is rejected')
    def test_cli_extracts_table_and_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = write_pdf(root, table=True)
            write_config(root, base_config(root))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(pdf)],
                cwd=root, env=cli_environment(), capture_output=True,
                text=True, timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for expected in (
                'Hello World from page one.',
                'Colour and organisation.',
                '| Name | Value |',
                '___',
                'Second page text.',
                'SUCCESS: Extracted content written to',
            ):
                self.assertIn(expected, result.stdout)
            self.assertNotIn('Copyright 2024', result.stdout)
            written = (root / 'out.md').read_text(encoding='utf-8')
            self.assertIn('| Name | Value |', written)
            self.assertIn('Second page text.', written)

    @unittest.skipIf(hasattr(os, 'geteuid') and os.geteuid() == 0, 'root is rejected')
    def test_cli_version_and_error_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_config(root, base_config(root))
            version = subprocess.run(
                [sys.executable, str(SCRIPT), '--version'],
                cwd=root, env=cli_environment(), capture_output=True,
                text=True, timeout=60,
            )
            self.assertEqual(version.returncode, 0)
            self.assertIn('pdf-fmt 1.0.0', version.stdout)

            missing = subprocess.run(
                [sys.executable, str(SCRIPT), str(root / 'absent.pdf')],
                cwd=root, env=cli_environment(), capture_output=True,
                text=True, timeout=60,
            )
            self.assertEqual(missing.returncode, 1)
            self.assertIn('Input file not found', missing.stdout)

            legacy = base_config(root)
            legacy['filters']['linting']['spelling']['enforce_locale'] = 'en-UK'
            write_config(root, legacy)
            rejected = subprocess.run(
                [sys.executable, str(SCRIPT), str(write_pdf(root))],
                cwd=root, env=cli_environment(), capture_output=True,
                text=True, timeout=60,
            )
            self.assertEqual(rejected.returncode, 1)
            self.assertIn('Legacy locale', rejected.stdout)


    @unittest.skipIf(hasattr(os, 'geteuid') and os.geteuid() == 0, 'root is rejected')
    def test_cli_cjk_locale_converts_and_spaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pages = [['这是一个测试 with Python3.'], ['第二页文本。'], ['第三页。']]
            pdf = write_pdf(root, pages=pages)
            write_config(root, base_config(root, locale='zh-TW'))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(pdf)],
                cwd=root, env=cli_environment(), capture_output=True,
                text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('這是一個測試', result.stdout)
            self.assertIn('測試 with Python3', result.stdout)

    @unittest.skipIf(hasattr(os, 'geteuid') and os.geteuid() == 0, 'root is rejected')
    def test_cli_en_us_spelling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = write_pdf(root)
            settings = base_config(root, locale='en-US')
            write_config(root, settings)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(pdf)],
                cwd=root, env=cli_environment(), capture_output=True,
                text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('Color and organization.', result.stdout)

    @unittest.skipIf(hasattr(os, 'geteuid') and os.geteuid() == 0, 'root is rejected')
    def test_cli_malformed_pdf_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / 'broken.pdf'
            pdf.write_bytes(b'not a PDF at all')
            write_config(root, base_config(root))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(pdf)],
                cwd=root, env=cli_environment(), capture_output=True,
                text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn('Extraction failed', result.stdout)

    def test_no_config_uses_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = write_pdf(root)
            output = io.StringIO()
            with patch('pdf_fmt.config.find_config_file', return_value=None):
                with patch('pdf_fmt.processing.post_actions.copy_content') as copy:
                    with redirect_stdout(output):
                        settings = load_config()
                        with patch.object(sys, 'argv', ['pdf-fmt', str(pdf)]):
                            execute_main_pipeline(settings)
            text = output.getvalue()
            self.assertIn('Configuration file', text)
            self.assertIn('Hello World from page one.', text)
            copy.assert_called_once()


class TestPipelineE2E(unittest.TestCase):

    def test_pipeline_with_images_and_post_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = write_pdf(root, image=True)
            settings = base_config(root, image=True)
            output = io.StringIO()
            with patch.object(sys, 'argv', ['pdf-fmt', str(pdf)]):
                with redirect_stdout(output):
                    execute_main_pipeline(settings)

            written = (root / 'out.md').read_text(encoding='utf-8')
            self.assertIn('Hello World from page one.', written)
            self.assertIn('Second page text.', written)
            images = list((root / 'images').glob('*.png'))
            self.assertEqual(len(images), 1)
            with Image.open(images[0]) as image:
                self.assertEqual(image.format, 'PNG')

    def test_off_locale_preserves_spelling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = write_pdf(root)
            settings = base_config(root, locale='off')
            with patch.object(sys, 'argv', ['pdf-fmt', str(pdf)]):
                with redirect_stdout(io.StringIO()):
                    execute_main_pipeline(settings)
            written = (root / 'out.md').read_text(encoding='utf-8')
            self.assertIn('Colour and organisation.', written)

    def test_auto_detect_script_converts_traditional(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pages = [['這是一個測試'], ['第二頁文本'], ['第三頁']]
            pdf = write_pdf(root, pages=pages)
            settings = base_config(root, locale='zh-CN')
            spelling = settings['filters']['linting']['spelling']
            spelling['auto_detect_script'] = True
            with patch.object(sys, 'argv', ['pdf-fmt', str(pdf)]):
                with redirect_stdout(io.StringIO()):
                    execute_main_pipeline(settings)
            written = (root / 'out.md').read_text(encoding='utf-8')
            self.assertIn('这是一个测试', written)

    def test_min_chars_joins_short_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = write_pdf(root, pages=[['Short one', 'Short two', 'Short three'], ['Next page.'], ['Last page.']])
            settings = base_config(root, locale='off')
            settings['formatting']['min_chars_per_line'] = 20
            with patch.object(sys, 'argv', ['pdf-fmt', str(pdf)]):
                with redirect_stdout(io.StringIO()):
                    execute_main_pipeline(settings)
            written = (root / 'out.md').read_text(encoding='utf-8')
            self.assertIn('Short one Short two Short three', written)

    def test_labelled_page_separator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = write_pdf(root)
            settings = base_config(root, locale='off')
            settings['formatting']['page_separator'] = '--- PAGE SEPARATOR ---'
            with patch.object(sys, 'argv', ['pdf-fmt', str(pdf)]):
                with redirect_stdout(io.StringIO()):
                    execute_main_pipeline(settings)
            written = (root / 'out.md').read_text(encoding='utf-8')
            self.assertIn('--- Page 2 ---', written)

    def test_extract_text_from_real_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = write_pdf(root, table=True)
            settings = base_config(root)
            content, error = extract_text_from_pdf(
                str(pdf), settings, DEFAULT_CHARS_REGEX,
                settings['filters']['footer_regexes'], 'en-GB', [],
            )
            self.assertIsNone(error)
            self.assertIn('| Name | Value |', content)
            self.assertIn('___', content)


@unittest.skipIf(platform.system() == 'Windows', 'POSIX executable fixture')
class TestConversionE2E(unittest.TestCase):

    def test_convert_then_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_pdf = write_pdf(root)
            tool = root / 'soffice'
            tool.write_text(
                '#!/usr/bin/env python3\n'
                'import shutil, sys\n'
                "if '--version' in sys.argv:\n"
                "    print('fake 1.0')\n"
                '    raise SystemExit(0)\n'
                f'shutil.copyfile({str(source_pdf)!r}, '
                'sys.argv[-1] + "/input.pdf")\n',
                encoding='utf-8',
            )
            tool.chmod(0o755)

            document = root / 'input.docx'
            document.write_bytes(b'not really a docx')

            env = dict(os.environ)
            env['PATH'] = f'{root}{os.pathsep}{env.get("PATH", "")}'
            with patch('pdf_fmt.conversion._TOOL_CACHE', None):
                with patch.dict(os.environ, env):
                    pdf_path, converted = convert_to_pdf(
                        str(document), DEFAULT_CONVERT_FORMATS
                    )

            self.assertTrue(converted)
            self.assertIsNotNone(pdf_path)
            content, error = extract_text_from_pdf(
                str(pdf_path), base_config(root), DEFAULT_CHARS_REGEX, [], 'off', []
            )
            self.assertIsNone(error)
            self.assertIn('Hello World from page one.', content)


class TestImageE2E(unittest.TestCase):

    def test_extract_convert_and_dedupe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = write_pdf(root, image=True)
            images_dir = root / 'images'
            with redirect_stdout(io.StringIO()):
                _extract_and_format_images(str(pdf), str(images_dir), ['png'], 2000, 1)

            converted = list(images_dir.glob('*.png'))
            self.assertEqual(len(converted), 1)
            with Image.open(converted[0]) as image:
                self.assertEqual(image.format, 'PNG')

            duplicate = images_dir / 'duplicate.png'
            shutil.copyfile(converted[0], duplicate)
            with redirect_stdout(io.StringIO()):
                _discard_similar_images(str(images_dir), 95)
            self.assertEqual(len(list(images_dir.glob('*.png'))), 1)


class TestConfigE2E(unittest.TestCase):

    def test_config_file_discovery_and_mtime_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / CONFIG_FILENAME
            first = base_config(root)
            first['processing']['cores'] = 2
            path.write_text(yaml.safe_dump(first), encoding='utf-8')

            env = dict(os.environ)
            env['PDF_FMT_CONFIG_PATH'] = str(path)
            self.addCleanup(clear_config_cache)
            clear_config_cache()
            with patch.dict(os.environ, env):
                self.assertEqual(find_config_file(), str(path))
                self.assertEqual(load_config()['processing']['cores'], 2)

                second = base_config(root)
                second['processing']['cores'] = 3
                path.write_text(yaml.safe_dump(second), encoding='utf-8')
                future = time.time() + 10
                os.utime(path, (future, future))
                self.assertEqual(load_config()['processing']['cores'], 3)


@unittest.skipUnless(BINARY.exists(), 'compiled binary not built')
class TestCompiledBinaryE2E(unittest.TestCase):

    def test_version(self):
        result = subprocess.run(
            [str(BINARY), '--version'],
            cwd=ROOT, env=cli_environment(), capture_output=True,
            text=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r'pdf-fmt \d+\.\d+\.\d+')

    def test_extracts_cjk_and_table_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pages = [
                ['这是一个测试 with Python3.', 'Colour and organisation.'],
                ['第二页文本。'],
                ['第三页。'],
            ]
            pdf = write_pdf(root, pages=pages, table=True)
            write_config(root, base_config(root, locale='zh-TW'))
            env = cli_environment()
            env['PDF_FMT_CONFIG_PATH'] = str(root / CONFIG_FILENAME)
            result = subprocess.run(
                [str(BINARY), str(pdf)],
                cwd=root, env=env, capture_output=True,
                text=True, timeout=120,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('SUCCESS: Extracted content written to', result.stdout)
            written = (root / 'out.md').read_text(encoding='utf-8')
            self.assertIn('這是一個測試 with Python3.', written)
            self.assertIn('| Name | Value |', written)
            self.assertIn('___', written)


if __name__ == '__main__':
    unittest.main()
