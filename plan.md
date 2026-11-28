# pdf-fmt: localisation / spellcheck investigation and technical-debt plan

Date: 2026-11-25. Version target: 1.0.0 (major bump from 0.8.3 for the BCP 47 hard break).
Repo state: `da6957c` ("Release version 0.8.3"), shallow clone (1 commit).
No source code was changed as part of this investigation. The working tree contains only
`plan.md` plus tool metadata (`.headroom/`, `.lccst/`); incidental changes from running
tests/tools were reverted.

**Scope (confirmed):** target locales are `en-US`, `en-GB`, `zh-CN`, `zh-HK` and `zh-TW`.
Support is shown in a small README table with `Yes` / `Partial` / `No` statuses. The code is
to be modularised. Two make targets use the sibling binary `../adacovex/bin/adacovex`
directly for complexity and SBOM work. This repo has no `alire.toml` or `alr`. All open
questions from the earlier draft have now been answered; the decisions are recorded in
section 10.

## 1. What was inspected

- `lccst` v4.8.0: `init`, `tooling`, `compliance`, `audit`, `test --dry-run`, `lint --dry-run`.
- Direct read of all source files, `pyproject.toml`, `uv.lock`, `requirements.txt`,
  `pdf-fmt.yaml`, `Makefile`, `README.md`, `.github/workflows/release.yml`, and both test files.
- Baseline test run: `uv run python -m unittest discover -sv tests` → 19 tests, all pass.
- `../adacovex` (v1.75.0 binary at `bin/adacovex`, alias `bin/covex`; `just` 1.59.0):
  `adacovex --help`, `help complexity`, `help sbom`, `justfile`, `tools/taskkit/build.py`,
  `docs/usage/sbom.md`, `README.md`; dry-runs of `complexity` and `sbom` with all output
  directed to `/tmp` (nothing written into this repo).
- PyPI metadata / upstream docs for candidate libraries, retrieved 2026-11-25.

### lccst findings

| Check | Result |
| --- | --- |
| Project type | Python, `uv`, `hatchling`; tests via `make test` → `python -m unittest discover -sv tests` |
| `make` targets | clean, compile, help, install, release, requirements, run, run-compiled, setup, sync, test |
| `compliance` | unit tests: yes (2 files); docstrings: yes (12 files); API docs: no; changelog: no |
| `audit` | no staged/unstaged changes; only untracked `.headroom/` and `.lccst/` tool metadata |
| `lint --dry-run` | command is `uv run ruff check`, but **ruff is not declared anywhere**; running it fails (`Failed to spawn: ruff`) |
| `test --dry-run` | command is `make test`; works |

### adacovex findings (relevant to the new make targets)

- `complexity` **does scan Python**. Baseline run against this repo:
  - without filters it fails because Markdown dominates (README.md 13% > 10% gate);
  - with `--excludes=md,rst` and skipping `.venv`, `.headroom`, `.lccst`, it still fails:
    `pdf_fmt/image/__init__.py` (14%) and `pdf_fmt/processing/__init__.py` (14%) exceed the
    10% LOC-dominance gate. This is direct evidence for the requested modularisation.
  - Every Python file reported `cx=0`, so for Python this behaves as a per-file LOC
    dominance gate rather than a true cyclomatic-complexity score. Treat it as a
    "keep modules small" gate, not proof that functions are simple.
- `sbom` works on this Python project despite the absence of an Alire manifest: it generated
  a 24-component SBOM from `requirements.txt`, GitHub Actions and system tools. Caveats:
  root PURL is `pkg:alire/pdf-fmt` with `proof_level Stone` and DO-178C/ISO 26262/IEC 62304
  properties (meaningless for this CLI); dependency versions are blank because
  `requirements.txt` is generated with versions stripped. Use it as a dependency inventory,
  not as a compliance artifact.
- The sibling project builds its own binary with `just build` there (docs-venv plus
  `alr build`, so that step needs `just` and Alire's `alr` **inside `../adacovex`**). This
  project only consumes `../adacovex/bin/adacovex`; it needs neither `just` nor `alr` nor an
  `alire.toml`. Refreshing the binary is an optional contributor convenience.

## 2. Technical debt (ranked)

### T1. Tests test copies, not the product (highest priority)

- [x] T1: make tests import production modules instead of pasted copies

`tests/test_core.py` and `tests/test_parser.py` paste stand-alone copies of production
functions ("Pasted for Standalone Testing", "Simulated/Real Logic, FIXED") instead of
importing `pdf_fmt.*`. Consequences:

- All 19 tests can pass while the shipped code differs. Concrete drift already visible:
  - `pdf_fmt/core/__init__.py:147-154` `ln_cont_factory` lacks the `.strip()` the test copy has.
  - `pdf_fmt/core/__init__.py:157-168` `format_indented_line` contains
    `normalized_line = line.replace("\n", "\n\n")`, which discards the preceding NBSP
    normalisation and is absent from both test copies.
  - `pdf_fmt/core/__init__.py:68-81` `preserve_case` has `mixed_upper` logic not present in the
    test copies; test copies are labelled "FIXED".
  - `tests/test_parser.py` uses mocked spelling functions and a different
    `_process_page_text_block` signature and page-separator logic than
    `pdf_fmt/processing/__init__.py:125-202`.
- No tests at all for `spell`, `formatting`, `config`, `conversion`, `image`, `startup`, CLI
  parsing, or an end-to-end PDF extraction.
- `lccst compliance` reports "unit tests: true" on this basis, so the metric is misleading
  until tests import real modules.

### T2. Locale/spell subsystem is narrow, stale and fragile

- [x] T2: replace the narrow breame spelling path with the BCP 47 stack

- `pdf_fmt/spell/__init__.py:12-65` supports exactly `EN-US` and `EN-UK` via `breame`
  0.1.2, released 2021-10-04, with no release since. `README.md:99-106` documents known
  inaccuracies (e.g. `localization` is not converted to `localisation`). Verified:
  `localization` is absent from breame's spelling constants while `organisation` is present.
- `pdf-fmt.yaml:44-49` already carries `ignore_locale_strings` as a workaround for bad
  upstream mappings; this is a config-level patch for a data-quality problem.
- `EN-UK` is non-standard (BCP 47: `en-GB`), and `none` is used as a sentinel in config/docs
  but only handled by falling through in `enforce_spelling`. No tag normalisation or
  validation exists (`locale_checks` only checks `isinstance(str)`).
- Import failure handling is broken: on `ImportError` it prints `BREAME_ERROR` but keeps
  going, so `get_american_spelling` / `get_british_spelling` would be undefined → `NameError`.
- `except (ValueError, Exception)` is equivalent to bare `except Exception` and swallows
  all errors, hiding data/programming faults.
- Tokenisation is whitespace-based (`text.split()`), dropping original whitespace;
  `NON_ALPHA_PATTERN = [^a-zA-Z]` strips punctuation and all non-ASCII letters before
  lookup; `word.replace(clean_word, ..., 1)` can corrupt hyphenated/apostrophised words.

### T3. ASCII-only pipeline blocks Chinese entirely

- [x] T3: make the text pipeline Unicode and CJK aware

- `pdf_fmt/core/__init__.py:7` `NON_ALPHA_PATTERN` and
  `pdf_fmt/core/__init__.py:5` `DEFAULT_CHARS_REGEX` are explicitly ASCII. **All Han
  characters would be deleted** by the default filter, so no Chinese backend could work
  until this is fixed.
- `pdf_fmt/formatting/__init__.py:7-9` `fix_spacing` uses `[a-z0-9][A-Z]`, ASCII-only.
- `pdf_fmt/formatting/__init__.py:12-83` replaces Unicode with LaTeX-style escapes
  (`\cdot`, `\alpha`, …); with the ASCII filter these become stray backslashes.
- `pdf_fmt/core/__init__.py:68-81` `preserve_case` is Latin/Title-case centric; Chinese has
  no case, so this must become a no-op for zh locales.
- `pdf_fmt/core/__init__.py:84-109` line wrapping uses `str.rfind(' ')`, which cannot break
  Chinese text (no spaces between words). Need grapheme/word segmentation or
  character-width-based wrapping for CJK.
- `pdf_fmt/core/__init__.py:45-60` `enforce_capitalization` is meaningless for Chinese.

### T4. Three divergent entry points

- [x] T4: collapse the entry points into one implementation with thin wrappers

`pdf-fmt.py`, `pdf_fmt/main.py`, `build.py` and `pdf_fmt/startup/__init__.py:110-163` contain
near-duplicate startup/error-handling logic. Differences are real: `build.py` (used by the
Nuitka release workflow) skips `check_venv()`, and one exception path uses `e.exit_code`
instead of `1`. `pyproject.toml:22` points the console script at `pdf_fmt.main:main`, the
installer points users at `pdf-fmt.py`, CI+Nuitka use `build.py`. One implementation with
thin wrappers removes the drift.

### T5. Empty/dead modules, docs and conventions drift

- [x] T5: remove dead modules and update stale docs and conventions

- `pdf_fmt/actions/__init__.py` and `pdf_fmt/filter/__init__.py` are empty; no imports.
- `pdf_fmt/processing/__init__.py:266` reads `formatting.extract_table`, but that key is
  not present in `pdf-fmt.yaml`; README calls table extraction "experimental" and says a
  config entry will be added.
- `README.md:99` says custom locale mappings are "being added" but no such option exists.
- `README.md:322-324` points to `scripts/compile.sh`, which does not exist; `README.md:418`
  points to `scripts/dev.sh`, which does not exist. `README.md:28-29` says the script
  installer does not work on main.
- No `AGENTS.md`, no API docs, no changelog (`lccst compliance`).
- Code comments are verbose/narrative in places while README style is concise; decision:
  use the concise technical style in README **and** in code comments.
- `pyproject.toml:9` allows Python `<3.14`, but CI builds with 3.12 and local `uv` selected
  3.13; local system Python is 3.14. Decision: add 3.14 support (section 10).

### T6. Runtime robustness (lower priority, relevant to any new backend)

- [x] T6: harden workers, timeouts and config caching

- `pdf_fmt/parser/__init__.py:16` `os.cpu_count() - 1` assumes `os.cpu_count()` is not None.
- `pdf_fmt/parser/__init__.py:54-65` starts an image-extraction subprocess with a 120 s
  join, terminates on timeout, but never reaps it.
- `pdf_fmt/processing/__init__.py:234-247` falls back to sequential on any pool exception,
  which can mask real bugs in the backend.
- The spelling engine is invoked once per page inside a multiprocessing pool
  (`pdf_fmt/processing/__init__.py:285-299`); decision: one lazily-created backend per worker.
- `pdf_fmt/config/__init__.py:8-10,15-16` caches path and mtime globally and never
  invalidates the path cache; harmless for a one-shot CLI, but awkward for tests.

### T7. Monolithic modules (now measured)

- [x] T7: split the modules that exceed the 10% LOC gate

`adacovex complexity` reports `pdf_fmt/image/__init__.py` and `pdf_fmt/processing/__init__.py`
at 14% of codebase LOC each, above the 10% gate; README alone is 13% when Markdown is not
excluded. Splitting those two modules is the concrete first modularisation step and lets the
gate stay at 10% without weakening it.

## 3. Current locale flow and target locales

`pdf-fmt.yaml` → `config.load_config()` → `parser.execute_main_pipeline()` →
`locale_checks()` returns `(locale_string, ignore_list)` → passed to each page block →
`formatting.clean_and_lint_text()` → **only if** locale lowercased is `en-us`/`en-uk`,
call `spell.enforce_spelling()` → `breame.spelling.get_american_spelling()` /
`get_british_spelling()` → case-preserving word replacement → generic ASCII
spacing/formatting. Dates, numbers, punctuation, quotes and grammar are not locale-aware.

Target state:

| Tag | Meaning | What "localisation" means here |
| --- | --- | --- |
| `en-US` / `en-GB` | American / British English | Spelling-variant conversion, typo/grammar linting, locale formatting and typography |
| `zh-CN` | Simplified Chinese (mainland) | Simplified script/region conversion, CJK–Latin spacing, CJK-aware wrapping, locale formatting |
| `zh-TW` | Traditional Chinese (Taiwan) | Taiwan Traditional forms + same formatting; no word-level spellcheck |
| `zh-HK` | Traditional Chinese (Hong Kong) | Hong Kong Traditional forms/vocabulary + same formatting; no word-level spellcheck |

"Formatting" now explicitly includes **Babel-style locale formatting** (dates, numbers,
currencies) and **typography rules** (quotes, dashes, ellipses) as well as CJK–Latin spacing.
It does not include translation of text content.

Chinese "spellcheck" is not the same problem as English: there are no spaces between words,
so correction normally needs segmentation plus a language model. Pure-Python libraries can
do conversion and spacing well but not reliable word-level correction. This is documented
honestly rather than over-promised.

## 4. Candidate libraries (PyPI state on 2026-11-25)

### English / general

| Library | Version / last release | Pure Python? | What it gives | What it does not give |
| --- | --- | --- | --- | --- |
| `breame` (current) | 0.1.2 / 2021 | Yes | ~1700 en-GB↔en-US spelling pairs, Apache-2.0 | Stale, known wrong mappings, no grammar, no other languages |
| `pyspellchecker` | 0.9.1 / 2026-10 | **Yes** | Bundled dictionaries for 12 languages; edit-distance suggestions | No grammar, no en-GB/en-US split, no Chinese, OpenSubtitles-derived dictionaries |
| `symspellpy` | 6.10.2 / 2026-11 | **Yes** | Fast fuzzy typo correction | Needs a dictionary source per language; no grammar/dialect rules |
| `codespell` | 2.4.3 / 2026-07 | **Yes** | Large typo dictionary; `dictionary_en-GB_to_en-US.txt` (~12.5 KB) | Source-code oriented, GB→US only, no grammar, CLI/file API; CC BY-SA 3.0-derived data |
| `harper-py` (unofficial Harper bindings) | 0.2.0 / 2026-10 | **No**, Rust abi3 wheel (~10 MB) | In-process English grammar + spelling + style, dialect settings, user dictionary, rule toggles, ~0.2 s cold start, no Java/network, Apache-2.0; wheels for CI targets incl. 3.14 via abi3 | English only; unofficial single-maintainer binding; must pass Nuitka smoke test; import name `harper` collides with unrelated PyPI `harper` |
| `harper-cli` (third-party binary wrapper) | 2.13.0 / 2026-10 | No | Official Harper CLI binary; useful as reference/testing tool | External process, English only |
| `language-tool-python` | 3.4.0 / 2026-05 | Wrapper only | Mature multilingual grammar/style/spell checking, en-US/en-GB variants | Java ≥17 + ~259 MB first-run download + JVM server; public API sends text to a third party; **deferred** |
| `pyLanguagetool` | 0.11.0 / 2025-03 | Yes (client) | Small client for an existing LanguageTool JSON API | Requires an external server |
| `pyenchant` / `hunspell` / `pynuspell` | 3.3.0 / 2018 / 2021 | No | Mature dictionaries in many languages | Native C/C++ libs + dictionaries per platform; no grammar; Nuitka packaging risk |
| `Babel` | 2.19.0 / 2026-11 | **Yes** | Locale-aware dates, numbers, currencies, plural rules | Not a spellchecker |
| `langcodes` | 3.5.1 / 2025-12 | **Yes** | BCP 47 tag parsing/normalisation | Not a spellchecker |
| Typography libs (`typogrify` 2.1.0, `python-typograf` 0.2.0, `richtypo` 0.2.3) | mixed | Mostly Yes | Quote/dash/ellipsis conventions | Web-oriented or stale; need evaluation against our text pipeline |

### Chinese

| Library | Version / last release | Pure Python? | What it gives | Caveats |
| --- | --- | --- | --- | --- |
| `zhconv` | 1.4.3 / 2021 | **Yes** | Maximal-match conversion using MediaWiki tables; supports `zh-cn`, `zh-tw`, `zh-hk`, `zh-sg`, `zh-hans`, `zh-hant`, exactly our target tags | Stale release; validate HK/TW fidelity with a corpus (decision: zhconv + corpus) |
| `opencc` | 1.4.2 / 2026-08 | No (C++ wheels, incl. cp314) | High-quality OpenCC conversion incl. `s2hk`, `s2twp`, `tw2sp` | Native extension; allowed only if Nuitka smoke test passes; fallback if zhconv corpus fails |
| `opencc-python-reimplemented` | 0.1.7 / 2023-02 | **Yes** | Pure-Python port using OpenCC dictionaries; import name `opencc` | Stale; name collides with native `opencc`; pick one |
| `pangu` | 6.1.0 / 2026-10 | **Yes** | Inserts spaces between CJK and Latin/digits/symbols | Opinionated; opt-in per locale; don't apply inside code/math spans |
| `jieba` | 0.42.1 / 2020-01 | **Yes** | Chinese word segmentation; enables CJK-aware wrapping | Stale but stable heuristic |
| `uniseg` | 0.10.1 / 2026-01 | **Yes** | Unicode grapheme/word segmentation | General-purpose, no Chinese dictionaries |
| `pypinyin` | 0.55.0 / 2025-07 | **Yes** | Han → pinyin | Not a spellchecker |
| `pycorrector` | 1.1.4 / 2026-07 | No in practice | Real Chinese text correction | Pulls `transformers`, `datasets`, `numpy`, `pandas`, `pyahocorasick` + models; out of scope |
| `LanguageTool` (`zh`) | 6.6 rules table | No (Java) | 1863 XML rules + 1 Java rule for Chinese grammar | **No Chinese spellcheck**, no zh-HK/zh-TW variants, activity 0; deferred with all LT work |
| Harper | 2.13.0 | No (Rust) | None | **English only** |

## 5. Evaluation and recommendation

### LanguageTool: deferred

Best grammar coverage for English and many European languages; Chinese has many XML rules
but no spellcheck and no regional variants. Java ≥17, a 259 MB first-run download and a JVM
server per worker conflict with a single-file offline Nuitka release; the public API ships
user text to a third party. Decision: **do not implement LT until all other plan.md features
are in**. When it is revisited, support both a user-supplied local/remote server and the
public API, configured by the user, never silently downloaded at runtime.

### Harper: English quality upgrade, native wheel allowed

`harper-py` gives in-process grammar + spelling + style, explicit British/American dialects,
user dictionaries and rule toggles, Apache-2.0, no Java/network, wheels for every current CI
target (abi3 covers 3.14). It is a young unofficial binding (0.2.0) and a native extension;
decision: pin it, smoke-test Nuitka standalone on Windows x64 / Linux x64 / macOS arm64, and
use it when the build passes. It does nothing for Chinese.

### Chinese: conversion and spacing, no spellcheck claim

- Normalise tags with `langcodes`; use `zhconv` as the default converter and validate
  HK/TW output against sample text. Keep native `opencc` as a tested fallback if fidelity
  is insufficient.
- Support explicit locale conversion plus an **opt-in auto-detect mode** for mixed-script
  documents; a document may contain both Simplified and Traditional text.
- Use `pangu` for CJK/Latin spacing, `uniseg`/`jieba` for Unicode-aware wrapping.
- Document **no word-level Chinese spellcheck**; `pycorrector` and similar model-heavy tools
  are out of scope.
- Babel/typography work applies to all locales as configured formatting, not translation.

### Overall stack

Default pure-Python path: curated en mapping, `zhconv` + `pangu`, `Babel`/`langcodes`, and a
vetted typography helper. Optional native upgrades (Harper for English, OpenCC for zh) are
allowed when Nuitka smoke tests pass. LanguageTool is deferred to a later phase. Backend
import failures must be explicit errors, never silent fallback-and-continue.

## 6. Proposed README change (minimal)

One short "Supported languages" subsection with a single table and a one-line note. No README
restructure, no per-library prose. Statuses use `Yes` / `Partial` / `No` and describe the
target state after implementation:

| Locale | Recognised | Spelling / variant | Formatting | Linting |
| --- | --- | --- | --- | --- |
| `en-US` | Yes | Yes (US) | Yes | Partial (Harper optional) |
| `en-GB` | Yes | Yes (UK) | Yes | Partial (Harper optional) |
| `zh-CN` | Yes | Partial (Simplified conversion; no word spellcheck) | Yes | No |
| `zh-HK` | Yes | Partial (HK Traditional conversion; no word spellcheck) | Yes | No |
| `zh-TW` | Yes | Partial (TW Traditional conversion; no word spellcheck) | Yes | No |

Note under the table: `Partial` means variant/script conversion, not word-level spellcheck;
Chinese linting/grammar is not provided. Replace the stale "Inaccurate locale
enforcement"/"working on custom mappings" paragraph rather than adding to it.

Also add/update `AGENTS.md` as the repo's concise technical-style guide; the same concise
technical style applies to code comments. Invoke the `lccst` MCP server / skill whenever it
is available and relevant (project conventions, compliance checks, test/lint gates).

## 7. Modularisation plan (driven by the complexity gate)

No code is written yet; this is the intended split.

- [x] Modularity: `pdf_fmt/image/` splits extraction (`extract_images_from_pdf`),
  post-processing/format conversion (`post_process_images`, `_process_single_image`, SVG
  wrapper), and similarity dedupe (`_calculate_dhash`, `_discard_similar_images`).
- [x] Modularity: `pdf_fmt/processing/` splits PDF/table extraction, page-block processing,
  Markdown table conversion, and post-actions (clipboard/file).
- [ ] Modularity: `pdf_fmt/core/` keeps small text/line/regex helpers and gains Unicode-aware
  tokenisation and CJK wrapping modules. Formatting and typography helpers stay separate.
- [x] Modularity: `pdf_fmt/spell/` gains one backend interface plus backend modules for the
  English curated map, optional Harper, the Chinese `zhconv`/`pangu` converter, and script
  detection. `locale_checks` becomes BCP 47 tag normalisation and validation, with a hard
  break on legacy values.
- [x] Modularity: `pdf_fmt/formatting/` gains locale-aware date/number formatting (Babel) and
  typography rules, kept separate from text cleanup.
- [ ] Modularity: `pdf_fmt/config/`, `pdf_fmt/startup/` and `pdf_fmt/parser/` slim down. The
  three entry points collapse into one implementation with thin wrappers.
- [x] Modularity: remove the two empty packages (`actions/`, `filter/`).
- [x] Modularity: keep every Python module under the adacovex 10% LOC gate, with tests that
  import the real modules and comments in the concise README style.

## 8. Configuration decisions

- **Tags:** hard break to BCP 47 (`en-US`, `en-GB`, `zh-CN`, `zh-HK`, `zh-TW`); reject
  `en-UK` and `none` rather than aliasing them. This is a major semver bump from 0.8.3.
- **Off switch:** explicit `off` value, validated.
- **Auto-apply:** new config listing which suggestion categories may be applied
  (`variant`/spelling by default; grammar/style off by default), user-configurable.
- **Script detection:** explicit locale always applies; an opt-in `auto_detect_script`
  setting handles mixed-script documents.
- **Ignore/override list:** `ignore_locale_strings` becomes per-locale user dictionaries and
  doubles as the curated mapping override for known breame inaccuracies.

## 9. Two new Makefile targets (description only, no code written)

Both use the existing sibling binary at `../adacovex/bin/adacovex` directly; no `alire.toml`
or `alr` belongs in this project. An optional separate helper may run `just build` inside
`../adacovex` to refresh the binary; the gates themselves must not depend on it.

- [x] 1. **Complexity / LOC gate:** invoke
   `adacovex complexity --target=. --excludes=md,rst` plus `--skip-path` for `.venv`,
   `.headroom`, `.lccst`, `build`, `sbom.json` and other generated files. Print per-file LOC and gate
   status; non-zero exit fails `make`. Keep the 10% threshold. Baseline currently fails on
   `image` and `processing`; section 7 is the fix. Document that `cx=0` for Python means
   this is a size gate, not proof of low cyclomatic complexity.
- [x] 2. **SBOM:** invoke `adacovex sbom --target=. --format=cyclonedx-json --out=sbom.json`.
   Keep **only `sbom.json`** in the repo; do not keep the Markdown SBOM. The generated
   AD/Alire compliance fields are not meaningful here and dependency versions are blank
   until `requirements.txt` carries pins; generate, don't hand-edit. Optionally set
   `SOURCE_DATE_EPOCH` from git for deterministic output.

Multiprocessing workers must not invoke adacovex.

## 10. Decisions (all open questions answered)

1. **Formatting scope:** text-only conversion/spacing **plus** Babel locale formatting
   **plus** typography rules.
2. **zh engine:** `zhconv` as default, validated with a corpus; native `opencc` only as a
   fallback if fidelity is insufficient.
3. **Mixed script:** explicit locale conversion plus opt-in auto-detection.
4. **Chinese spellcheck:** document as unsupported; no model-heavy correction.
5. **Native wheels:** allowed when Nuitka smoke tests pass on all release targets.
6. **Binary/platform budget:** keep the current CI matrix (Windows x64, Linux x64, macOS
   arm64); musl/aarch64 may build from source best-effort, no guarantees.
7. **LanguageTool:** low priority. Local server and public API setups are the user's
   effort; do not implement until all other plan.md features are in.
8. **Config migration:** hard break, major semver bump.
9. **Licensing:** attribute third-party data in-repo (LICENSES/NOTICE), prefer permissive
   sources.
10. **Worker design:** one lazily-created backend per multiprocessing worker.
11. **SBOM artifact:** keep only `sbom.json`.
12. **LOC gate:** keep 10%.
13. **Docs/conventions:** README table uses `Yes`/`Partial`/`No`; create/update `AGENTS.md`;
    use the concise README technical style in code comments; invoke `lccst` MCP/skill when
    available and relevant.
14. **Python versions:** add 3.14 and align `requires-python`, CI and README.

Implementation details still to settle during phases 2–5 (not blocking): which typography
helper wins evaluation, the exact default auto-apply category list, and the zhconv corpus
acceptance threshold.

## 11. Phased implementation sequence

- [x] 1. Tests-first + conventions: import real modules, fix known drift, add Unicode/CJK
   fixtures and a small PDF end-to-end; add `ruff` to a dev group; update `AGENTS.md`; vendor
   the STE skill and add the em dash gate; use `lccst` MCP/skill where available.
   - [x] 1a. Expand end-to-end coverage over the CLI, pipeline, conversion, images, locales
      and config with real multi-page PDFs that carry a table, an image and CJK text.
- [x] 2. Unicode foundation: replace ASCII filters/patterns, add CJK-aware wrapping and
   spacing, make capitalisation/case-preservation locale-aware; add Babel formatting and
   typography hooks.
- [x] 3. Modularise source (section 7) and land the two adacovex make targets; get the 10%
   gate green and generate `sbom.json`.
- [x] 4. Config hard break with major semver bump: BCP 47 tags, `off`, `auto_detect_script`,
   `auto_apply` categories, per-locale dictionaries.
- [x] 5. Pure-Python engines: curated en map, `zhconv` + corpus validation, `pangu`, typography
   helper, optional `pyspellchecker`. The in-repo CJK spacing hook replaces `pangu`.
- [ ] 6. Optional native upgrades: pin and Nuitka-smoke-test `harper-py` (English) and `opencc`
   (zh fallback only if needed) on the three CI targets. LanguageTool stays deferred. An
   import-level CI smoke job runs; wheels stay unpinned until standalone builds pass.
- [ ] 7. Docs/release: minimal README table (section 6), changelog, API docs, `AGENTS.md`,
   Python 3.14 matrix; re-run `lccst compliance` and the complexity gate.

## 12. Sources consulted

- Local: all files listed in section 1; lccst v4.8.0 outputs; adacovex v1.75.0 CLI outputs;
  `/tmp/pdf-fmt-sbom.md` (generated during investigation, not committed).
- PyPI JSON API (metadata/release dates): breame, pyspellchecker, symspellpy, codespell,
  harper-py, harper-cli, language-tool-python, pyLanguagetool, pyenchant, Babel, langcodes,
  zhconv, opencc, opencc-python-reimplemented, pangu, jieba, uniseg, pypinyin, pycorrector,
  typogrify, python-typograf, richtypo, and others.
- Upstream docs: `Automattic/harper`, `Maksim-Burtsev/harper-py`,
  `jxmorris12/language_tool_python`, `cdpierse/breame`, `codespell-project/codespell`,
  LanguageTool `dev.languagetool.org/languages` (Chinese: 1863 XML rules, no spellcheck),
  and `../adacovex` README / `docs/usage/sbom.md` / justfile.
- All external facts above are as of 2026-11-25 and should be re-checked before pinning
  versions.

## 13. Post 1.0 backlog (through v1.5.0)

This list came from an older plan written by a previous model. That text was low quality,
and the changes probably did not land. Check every item against the code before work starts.
Work through the list up to v1.5.0. Use minor semver bumps sparingly.

### 13.1 Extraction and formatting

- [ ] Improve table output. It is still wonky or broken.
- [ ] Continue the Unicode to non-Unicode mappings.
- [ ] Fix `max_chars_per_line`. Move extra characters to the next line instead of discarding
  them.
- [ ] Let users define `us_to_uk_mapping` and `uk_to_us_mapping`. These override breame when
  the definitions conflict.
- [ ] Test compiler flags and compile locally. Check whether any modules must be included
  explicitly.
- [ ] Enforce at least one line separator after Markdown blockquotes, where each line starts
  with `>`. Let users set the number of line breaks before each separator.
- [ ] Update the config schema with defensive checks. Only YAML syntax is checked today.
- [ ] Extract and embed. Test that it works as expected and add defensive checks.
- [ ] Confirm the definitions and behaviour of these config values:
  - [ ] `cores`: report time spent in multiprocessing and add a `quiet: true` option.
  - [ ] `ignore_locale_strings`
  - [ ] `enforce_locale`
- [ ] Allow a Markdown heading (`# `, `##`, and so on) after each separator and on the first
  line of the document.
- [ ] Fix unknown terms getting lowercased.
- [ ] Skip image extraction when the path is invalid or the schema value is false. Add a test.
- [ ] Group content under the same heading. Do not add a separator when the first line of two
  pages is the same. Keep the existing separator and line-break behaviour for other chunks.
- [ ] Add a file metadata option for ctime, filename and file size. Keep the options simple.
- [ ] Always join lines that hold links or HTML tags.
- [ ] Stop a line separator from appearing after the last line.
- [ ] Make `min_chars_per_line` and `max_chars_per_line` smarter. Avoid splitting words.

### 13.2 Documentation and conversions

- [ ] Document default options outside the sample YAML file. Give each value a no-op value.
  Put the material in a separate documentation directory and try another documentation
  framework.
- [ ] Optionally keep the temporary converted PDF after conversion.
- [ ] Add maximum and minimum characters per slide, paragraph and line. Check minimum and
  maximum lines per slide.
- [ ] Add a configurable prefix for each line, such as two or four spaces for visual indent.
- [ ] Replace a space before a single `s` with an apostrophe, for example `enterprise s` to
  `enterprise's`. Make this customisable and abstract it to other symbols such as `:`.
- [ ] Enforce at least a given spacing on both sides of target regex strings, for example
  `A->B` to `A -> B`. Enable this by default for brackets.

### 13.3 Text quality, line breaks and linting

*Improving the quality of extracted text by controlling line breaks, paragraph structure,
and enforcing general linting rules.*

- [ ] Smart Line Joining: restore smart capitalization during line joining and make the
  default line and paragraph handling less opinionated.
- [ ] List Joining: join ordered and unordered list items to avoid excessive line breaks.
- [ ] Global Replace: add a config option for a regex that replaces all occurrences of one
  string with another. Run it before the rest of the text processing.
- [ ] Prefix/Suffix Control: add a regex option that prefixes or suffixes a line when it
  starts with a given pattern.
- [ ] Title Case Enforcement: add a linting rule that changes all caps in headings to title
  case.
- [ ] General Linting: add more linting rules for text quality.
- [ ] Remove the hyphen from target word prefixes and let users configure this.

### 13.4 Scaling and document boundaries

*Scaling the tool for multiple documents, with fine-grained control over document
boundaries and image and footer handling.*

- [ ] Batch Processing: process multiple documents with dynamic, configurable output file
  names.
- [ ] Interactive Config: add a CLI flag or config option for interactive review. Do not
  overwrite existing values without approval.
- [ ] Output Path Control: ask for the output path, allow a default directory, and add tab
  completion for paths.
- [ ] Smart Footers: detect footers with structural heuristics, not only user regexes.
- [ ] Image Handling: replace unrecognised images with placeholders or exclude images that
  dominate the page in text-only mode.
- [ ] Line Break Control: set the line break count before and after page separators.
- [ ] List Preservation: keep ordered list numbering across page breaks until a double line
  break appears.
- [ ] Enclosure Handling: treat `[a][b]` as one block instead of two independent matches.
- [ ] Omit Short Lines: drop lines or sections below a given character count.
- [ ] Remove by Start Regex: remove a whole paragraph when it starts with a given regex, for
  example citation or summary boilerplate.

### 13.5 Validation and code handling

- [ ] Configuration Validation: validate the structure of user config files.
- [ ] Citation Enforcement: enforce citation formats such as APA and MLA. Integrate with
  Zotero when its binary is present.
- [ ] Code Block Detection: detect Python code blocks with AST or text parsing and enclose
  them with correct formatting and auto-indentation.
- [ ] Code Protection: enclose a line in a code block when it starts with `#` to avoid
  Markdown parsing problems.
