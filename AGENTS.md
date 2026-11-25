# AGENTS.md

Conventions for contributors and coding agents in `pdf-fmt`. Use the same concise technical
style in the README, this file, docstrings and code comments. Write comments only where the
reason is not obvious from the code; never restate the code or mark it with `FIX`/`NOTE`.

## Layout

| Path | Scope |
| --- | --- |
| `pdf_fmt/core/` | Text, line and regex helpers |
| `pdf_fmt/spell/` | Locale checks and spelling backends |
| `pdf_fmt/formatting/` | Cleanup, Unicode mapping, locale formatting, typography |
| `pdf_fmt/parser/` | Pipeline coordination |
| `pdf_fmt/processing/` | PDF extraction, page blocks, tables, post-actions |
| `pdf_fmt/image/` | Image extraction, conversion, deduplication |
| `pdf_fmt/config/`, `pdf_fmt/startup/` | Config loading, CLI and startup checks |
| `build.py`, `pdf-fmt.py`, `pdf_fmt/main.py` | Entry points; to be collapsed into one |
| `tests/` | `unittest` suite importing real modules |
| `plan.md` | Work plan and version target |

Keep modules small: the adacovex gate fails any Python file above 10% of codebase LOC.

## Commands

- `make test` — `python -m unittest discover -sv tests`
- `uv run ruff check` — lint gate; keep the selected rules green
- `make run ARGS='...'` — run the script entry point
- `make compile`, `make run-compiled` — Nuitka build and binary check
- `make setup`, `make sync`, `make requirements` — environment and pinned export
- Complexity and SBOM gates use `../adacovex/bin/adacovex` directly. No `alire.toml` or `alr`
  in this repo. Only `sbom.json` is kept; the 10% LOC gate stays.
- When the `lccst` MCP server or skill is available, use `lccst init`, `tooling`,
  `compliance`, `audit`, `test` and `lint` instead of guessing conventions or gate commands.

## Code rules

- Target Python 3.10–3.14; add 3.14 to CI and the README as part of the version work.
- Keep type hints; let Ruff sort imports. One-sentence docstrings on public exports.
- Tests import production modules. Never paste copies of implementation code into tests.
- Add CJK/Unicode fixtures for text changes; ASCII-only filters are a known defect.
- Locales are BCP 47 tags: `en-US`, `en-GB`, `zh-CN`, `zh-HK`, `zh-TW`. `off` disables
  locale handling. Legacy `en-UK` and `none` are a hard break with a major release.

## Commit messages

Use Conventional Commits: `<type>(<scope>): <description>`. Keep the subject at most 72
characters, start with a verb, end without a full stop, and use British English. Link an
issue at the end of the body with `Closes #123` when one exists.

| Type | Use for |
| --- | --- |
| `feat` | New user-visible behaviour |
| `fix` | Defect repair |
| `docs` | Documentation only |
| `refactor` | Code change without behaviour change |
| `test` | Test-only change |
| `perf` | Measured improvement |
| `build` | Build, manifest, dependency or Makefile change |
| `ci` | Workflow changes |
| `tools` | Lint and gate tooling, including the adacovex targets |
| `chore` | No product change, such as adding a scope row |

| Scope | Covers |
| --- | --- |
| `core` | `pdf_fmt/core/` |
| `spell` | `pdf_fmt/spell/` |
| `formatting` | `pdf_fmt/formatting/` |
| `parse` | `pdf_fmt/parser/` |
| `process` | `pdf_fmt/processing/` |
| `image` | `pdf_fmt/image/` |
| `config` | `pdf_fmt/config/`, `pdf-fmt.yaml` |
| `cli` | Entry points and `pdf_fmt/startup/` |
| `tests` | `tests/` |
| `tools` | Lint/gate tooling and scripts |
| `docs` | `README.md`, `AGENTS.md`, `plan.md`, changelogs |
| `build` | `Makefile`, `pyproject.toml`, `build.py`, dependencies |
| `ci` | `.github/workflows/` |

Never invent a scope: add its row above first in a `chore:` commit. One component per commit;
split work that touches more than one component. Explain why a change was needed, not what
the diff shows.

After finishing a change, suggest the commit message in a fenced block and do not run the
commit unless asked. State why the scope fits, name the version in `plan.md` the change
belongs to, and say whether the change needs a MAJOR version. For one atomic change, suggest
one message. For several components or intents, list commits in dependency order and give
one shell one-liner that stages and commits each in turn with its own `git add` paths,
chaining the `git commit -m "$(cat <<'EOF' ... EOF)"` steps with `&&` so a failure stops the
chain. Never run that one-liner unless asked.
