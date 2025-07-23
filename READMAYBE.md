# Codebase Overview

This repository implements **Linker CLI**, a Python command-line tool for analyzing and migrating web page content.

## Key Components

### Main Application

- **`main.py`**  
  Parses CLI arguments, sets up a global `CLIState`, autoloads the latest DSM spreadsheet, and enters an interactive loop.  
  Commands are dispatched to handlers in `commands.py`.  
  Each prompt displays contextual info like current domain and row.

### State Management

- **`CLIState`**  
  Stores and manages variables:
  - `URL`, `DOMAIN`, `ROW`
  - Flags like `INCLUDE_SIDEBAR`, `DEBUG`
  - Helpers for validation, listing current state

### Command Handlers

- **`commands.py`** — Core logic for command execution  
  Examples:

  - `cmd_check`: Fetches a page, parses links/embeds via `page_extractor`, caches results
  - `cmd_load`: Loads URLs from Excel via `dsm_utils`
  - `cmd_report`: Builds HTML reports summarizing link/page data

  Additional utilities handle:

  - File caching
  - HTML report generation
  - File access

### Utilities and Helpers

- **`dsm_utils.py`**  
  Loads and queries DSM spreadsheets

- **`page_extractor.py`**  
  Uses `requests` + `BeautifulSoup` to extract:

  - Links
  - PDFs
  - Embeds
  - **_Supports optional sidebar content parsing_**

- **`lookup_utils.py`**  
  Looks up link migration targets in DSM  
  Outputs report data and navigation paths

- **`migrate_hierarchy.py`**  
  Builds proposed/current page hierarchies

- **`link_mapping.py`**  
  Curses-based UI for link migration selection

### Templates

- **`templates/report/`**  
  HTML, CSS, JS for interactive report generation via `cmd_report`

### Tests

- **`tests/test_commands.py`**  
  Pytest-based tests, mostly mock-driven  
  Validates behavior of CLI commands

## Configuration

- **`constants.py`**  
  Defines domain configurations  
  Constructs the CLI command map used in `main.py`

## High-Level Workflow

1. Launch CLI:  
   `python main.py`

2. Load page data:  
   `load <domain> <row>`

3. Analyze:  
   `check` — link/resource parsing, with caching

4. Optional:

   - `report` — generate HTML summary
   - `lookup <url>` — migration info, navigation paths

5. Reference:
   - `README.md` — command list, variable guide, file structure, advanced options (e.g. CSS selectors, caching)

## Suggestions for Further Learning

- **Dive into `commands.py`**  
  Understand how commands modify `CLIState` and connect to other modules

- **Explore `lookup_utils.py`**  
  Crucial for DSM navigation and link migration strategy

- **Study `templates/report`**  
  See how extracted data is visualized

- **Run `pytest`**  
  Watch command behavior in action  
  Consider adding tests for untested commands
