# Credits

bladeacer maintains `pdf-fmt`.

## SimpleEnglish skill

The technical writing rules in this repo come from the
[SimpleEnglish skill](https://github.com/AminBlg/SimpleEnglish), version 1.3.0
(ASD-STE100 Issue 9, 2025-01-15). Upstream is MIT licensed. See
[the upstream licence](https://github.com/AminBlg/SimpleEnglish/blob/main/LICENSE).

We vendor the skill at `skills/simple-english/` so contributors need no network
access to load it. The copy holds `SKILL.md` and three reference files. It is
unmodified upstream text.

We apply two project overrides. We use British spelling, and our docs gate
rejects em dashes. The gate lives in `tools/check_docs.py` and runs through
`make docs-check`.

## Dependencies

`pyproject.toml` lists the runtime and build dependencies. `sbom.json` records
the dependency inventory.
