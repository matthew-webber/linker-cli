## Current Issues
1. commands.py is too large (1600+ lines) and handles too many responsibilities
2. Some utility functions are scattered across files
3. Missing clear separation between core business logic and CLI interface
4. Some modules have unclear naming

## Suggested Restructure

### 1. Split commands.py into focused modules:

```
commands/
├── __init__.py
├── analysis.py      # cmd_check, cmd_links, _generate_summary_report
├── data.py          # cmd_load, cmd_set, cmd_show  
├── migration.py     # cmd_migrate, migration-related functions
├── reporting.py     # cmd_report, HTML generation (merge with commands/report.py)
├── bulk.py          # Already exists - keep as is
├── cache.py         # Already exists - keep as is
├── core.py          # Already exists - keep as is
└── common.py        # Already exists - keep as is
```

### 2. Create focused utility directories:

```
utils/
├── __init__.py
├── url.py           # normalize_url, URL validation functions
├── excel.py         # Move DSM-specific functions from dsm_utils.py
├── html.py          # HTML generation utilities from commands.py
└── debug.py         # debug_print, sync_debug_with_state

analysis/
├── __init__.py
├── page_extractor.py    # Keep existing
├── link_analyzer.py     # Link analysis logic from lookup_utils.py
└── hierarchy.py         # Rename migrate_hierarchy.py and move here

data/
├── __init__.py
├── dsm.py              # Rename dsm_utils.py
├── cache.py            # Cache data structures and validation
└── state.py            # Keep existing state.py
```

### 3. Specific function moves:

**From commands.py to `commands/analysis.py`:**
- `cmd_check()`
- `cmd_links()`
- `_generate_summary_report()`
- `_calculate_difficulty_percentage()`

**From commands.py to `commands/reporting.py`:**
- `cmd_report()`
- `_generate_report()`
- `_generate_html_report()`
- `_generate_consolidated_section()`
- `_sync_report_static_assets()`

**From commands.py to `utils/html.py`:**
- `_get_copy_value()`
- `_is_internal_link()`
- HTML generation helper functions

**From lookup_utils.py to `analysis/link_analyzer.py`:**
- `lookup_link_in_dsm()`
- `output_internal_links_analysis_detail()`

~~**From dsm_utils.py to `data/dsm.py`:**~~
~~- All existing functions (just rename the file)~~

### 4. Create new focused modules:

**`analysis/migration_planner.py`:**
```python
# Move from migration.py and migrate_hierarchy.py
def plan_migration(state, url=None):
    """High-level migration planning"""

def generate_hierarchy_comparison(existing_url, proposed_path):
    """Generate side-by-side hierarchy comparison"""
```

**`utils/validation.py`:**
```python
# Extract validation logic scattered across files
def validate_url(url):
def validate_excel_data(data):
def validate_cache_compatibility(state, cache_file):
```

### 5. Keep at root level:
- main.py (entry point)
- constants.py (configuration)
- spinner.py (simple utility)
- link_mapping.py (specialized UI component)

### 6. Update imports in `__init__.py` files:

**`utils/__init__.py`:**
```python
from .debug import debug_print, sync_debug_with_state
from .url import normalize_url
from .validation import validate_url, validate_excel_data
```

**`analysis/__init__.py`:**
```python
from .page_extractor import retrieve_page_data, display_page_data
from .link_analyzer import lookup_link_in_dsm
from .hierarchy import format_hierarchy, get_sitecore_root
```

This structure would:
- Make individual files more focused and maintainable
- Improve code discoverability
- Separate CLI concerns from business logic
- Group related functionality logically
- Make testing easier with smaller, focused modules
