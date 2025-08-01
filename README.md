# Linker CLI

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
- [DSM Spreadsheets](#dsm-spreadsheets)
- [Reports](#reports)
- [File Structure](#file-structure)
- [Development](#development)
- [License](#license)

## Overview
Linker CLI is an interactive command line tool for analysing web pages and planning migrations to Sitecore.  It can pull URLs from **DSM** Excel spreadsheets, extract links and embedded resources, cache results for later review and generate HTML reports.

## Features
- Load URLs and proposed paths from DSM spreadsheets
- Extract links, PDF references and Vimeo embeds
- Optional sidebar scraping
- Page data caching for quick repeat checks
- Bulk checking of many pages from a CSV
- HTML report generation with Sitecore hierarchy helpers

## Installation
```bash
# clone the repo
git clone <repository-url>
cd linker-cli

python -m venv venv    # recommended
source venv/bin/activate
pip install -r requirements.txt
```

## Quick Start
Run the CLI using the bundled helper script:
```bash
./run
```
You should see a prompt similar to:
```
🔗 Welcome to Linker CLI v2.0 - State-based Framework
💡 Type 'help' for available commands
linker_user [~ 🪟 🐞 📂] >
```

### Example workflow
Set a URL directly and analyse it:
```bash
set URL https://example.com/page
check
show page
```
Load a page from your DSM spreadsheet:
```bash
load Education 23
check
report
```

## Commands
The `help` command prints a full list.  Important ones include:

| Command            | Purpose                                                   |
|--------------------|-----------------------------------------------------------|
| `load <domain> <row>` | Load URL and proposed path from a DSM sheet            |
| `check`            | Fetch the current URL and extract links/PDFs/embeds       |
| `report`           | Generate an HTML report for the loaded page               |
| `links`            | Analyse internal links against the DSM                   |
| `bulk_check [csv]` | Process many pages listed in a CSV file                   |
| `set <VAR> <val>`  | Configure variables (URL, SELECTOR, etc.)                 |
| `show [target]`    | Display variables, domains or current page data           |
| `open <target>`    | Open the DSM file, current URL or generated report        |
| `debug [on|off]`   | Toggle verbose debugging output                           |
| `sidebar [on|off]` | Include sidebar content when analysing pages              |

## DSM Spreadsheets
DSM files are Excel spreadsheets named like `dsm-MMDD.xlsx` with one sheet per domain.  Use `load <domain> <row>` to set the current URL and proposed path.  Known domain names are defined in `constants.py`.

## Reports
`report` writes an HTML file to the `reports/` directory showing all extracted resources and a visual hierarchy comparison.  Cached page data is reused when available.

## File Structure
```
linker-cli/
├── commands/      # Individual command implementations
├── data/          # DSM utilities
├── utils/         # Helper functions (caching, scraping, sitecore tools)
├── templates/     # HTML report template and assets
├── tests/         # Pytest test suite
├── main.py        # CLI entry point
└── run            # Convenience launcher
```

## Development
- Run tests with `pytest`
- Code style is enforced via `black`

## License
See `LICENSE` file for details.
