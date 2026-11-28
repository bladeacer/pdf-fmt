# API

The packages below are importable from `pdf_fmt`. Private helpers are omitted.

| Package | Main exports | Purpose |
| --- | --- | --- |
| `pdf_fmt.config` | `load_config`, `find_config_file`, `clear_config_cache` | Find and load YAML config with mtime caching. |
| `pdf_fmt.core` | `post_process_content`, `split_fmt_line`, `tokenize_text`, `ln_cont_factory` | Filter, wrap, tokenise and join extracted text. |
| `pdf_fmt.conversion` | `convert_to_pdf`, `find_conversion_tool` | Convert supported files to PDF. |
| `pdf_fmt.formatting` | `clean_and_lint_text`, `replace_unicode_chars`, `add_cjk_spacing` | Clean text and apply locale formatting. |
| `pdf_fmt.image` | `extract_images_from_pdf`, `post_process_images` | Extract, convert and dedupe images. |
| `pdf_fmt.parser` | `execute_main_pipeline` | Coordinate conversion, extraction and post-actions. |
| `pdf_fmt.processing` | `extract_text_from_pdf`, `perform_post_actions` | Read PDF pages and write the output. |
| `pdf_fmt.spell` | `locale_checks`, `enforce_spelling`, `normalize_locale` | Validate BCP 47 tags and convert spelling variants. |
| `pdf_fmt.startup` | `setup_cli`, `check_venv`, `check_not_root` | Parse arguments and check the runtime. |
| `pdf_fmt.main` | `main` | Run the shared CLI entry point. |

## CLI

Run `pdf-fmt [FILE]`, or omit `FILE` to read from standard input.
`pdf-fmt --version` prints the package version and exits.
The CLI runs `pdf_fmt.main.main` after the local script checks the environment.
