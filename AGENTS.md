# Agent Onboarding

This document explains the repository structure, common development tasks, and conventions used in **Linker CLI**.

## Project Summary
Linker CLI is an interactive command line application for analysing pages and planning migrations to Sitecore.  It can load URLs from DSM spreadsheets, extract links/embeds, cache page data and generate HTML reports.

See `README.md` for a full overview of features and usage.  The table of contents, feature list and quick start examples are useful when first exploring the tool.

## Repository Layout
- `commands/` – individual command implementations
- `data/` – DSM spreadsheet utilities
- `utils/` – core helpers such as caching and scraping
- `templates/` – HTML report template and assets
- `tests/` – pytest test suite
- `main.py` – interactive CLI entry point
- `run` – small launcher script

## Development Tips
- Create a virtual environment and install dependencies as shown in the README.
- Use the `run` helper to start the CLI.
- All code is formatted with **black**.  Run `black .` before committing.
- Tests are written with **pytest**.  Run `pytest` to verify behaviour.
- Cached page data lives in `migration_cache/`.  Reports are written to `reports/`.
- `CLIState` in `state.py` manages global variables like URL, DOMAIN and DEBUG.
- Domain definitions and the command map are located in `constants.py`.

## Contributing
1. Ensure tests pass with `pytest`.  There are currently 40 passing tests covering command behaviour and report generation logic.
2. Keep functions small and focused.  Commands delegate to helpers in `utils/` where possible.
3. Follow the existing directory structure when adding new commands or utilities.

