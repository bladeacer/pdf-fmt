# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-11-28

### Added

- BCP 47 locale handling for `en-US`, `en-GB`, `zh-CN`, `zh-HK` and `zh-TW`.
- Unicode and CJK text handling, locale formatting and typography rules.
- Per-locale dictionaries and opt-in script detection in the config.
- Tests that import production modules, with PDF and CLI end-to-end coverage.
- Adacovex complexity and SBOM make targets, API docs and a docs em dash gate.
- Python 3.14 support and a CI test matrix from 3.10 to 3.14.

### Changed

- Split the image, processing, spell, formatting, core, config, startup and parser packages.
- Replaced three startup implementations with one CLI and thin wrappers.
- Hardened core counts, image subprocess cleanup, worker errors and config caching.

### Removed

- Rejected the legacy locale values `en-UK` and `none`. This is a breaking change.
- Removed the empty `actions` and `filter` packages.

### Fixed

- Kept CJK text through the default character filter and line wrapping.
- Preserved whitespace and CJK characters during tokenisation.
- Rejected Windows administrator access reliably.

[Unreleased]: https://github.com/bladeacer/pdf-fmt/compare/1.0.0...HEAD
[1.0.0]: https://github.com/bladeacer/pdf-fmt/releases/tag/1.0.0
