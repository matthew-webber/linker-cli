import json
import re
from pathlib import Path
from datetime import datetime

from utils.core import debug_print, normalize_url

CACHE_DIR = Path("migration_cache")
CACHE_DIR.mkdir(exist_ok=True)


def _cache_page_data(state, url, data):
    domain = state.get_variable("DOMAIN")
    row = state.get_variable("ROW")
    kanban_id = state.get_variable("KANBAN_ID")
    selector = state.get_variable("SELECTOR")
    include_sidebar = state.get_variable("INCLUDE_SIDEBAR")
    url = normalize_url(url)

    if domain and row:
        cache_filename = f"page_check_{domain}-{row}.json"
    else:
        sanitized_url = re.sub(r"[^\w\-_.]", "_", url)[:50]
        cache_filename = f"page_check_{sanitized_url}.json"

    cache_file = CACHE_DIR / cache_filename

    cache_data = {
        "metadata": {
            "url": url,
            "domain": domain,
            "row": row,
            "kanban_id": kanban_id,
            "selector": selector,
            "include_sidebar": include_sidebar,
            "timestamp": datetime.now().isoformat(),
            "cache_filename": cache_filename,
        },
        "page_data": data,
    }

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        state.set_variable("CACHE_FILE", str(cache_file))
        print(f"✅ Data cached to {cache_file}")
        debug_print(f"Cache metadata: {cache_data['metadata']}")
    except Exception as e:
        debug_print(f"Error caching data to {cache_file}: {e}")
        raise


def cache_page_data(state, url, data):
    return _cache_page_data(state, url, data)


def _get_expected_metadata_structure():
    """Get the current expected metadata structure for cache validation."""
    return {
        "url": None,
        "domain": None,
        "row": None,
        "kanban_id": None,
        "selector": None,
        "include_sidebar": None,
        "timestamp": None,
        "cache_filename": None,
    }


def _is_metadata_structure_current(metadata):
    """Check if the metadata structure matches current expectations."""
    if not isinstance(metadata, dict):
        return False

    expected_keys = set(_get_expected_metadata_structure().keys())
    actual_keys = set(metadata.keys())

    # Check if all expected keys are present
    return expected_keys.issubset(actual_keys)


def _load_cached_page_data(cache_file_path):
    try:
        with open(cache_file_path, "r", encoding="utf-8") as f:
            cached_content = json.load(f)

        if (
            isinstance(cached_content, dict)
            and "metadata" in cached_content
            and "page_data" in cached_content
        ):
            return cached_content["metadata"], cached_content["page_data"]
        else:
            return {}, cached_content
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        debug_print(f"Error loading cache file {cache_file_path}: {e}")
        return {}, {}


def _is_cache_valid_for_context(state, cache_file):
    if not cache_file:
        return False, "No cache file specified"
    try:
        metadata, page_data = _load_cached_page_data(cache_file)
        if not metadata:
            return False, "Cache file contains no metadata"

        # Check if metadata structure is current
        if not _is_metadata_structure_current(metadata):
            return False, "Metadata structure is outdated"

        # Check if page_data contains meta_description and meta_robots
        if (
            not page_data
            or "meta_description" not in page_data
            or "meta_robots" not in page_data
        ):
            return False, "Cache missing meta description or robots data"

        current_url = state.get_variable("URL")
        current_domain = state.get_variable("DOMAIN")
        current_row = state.get_variable("ROW")
        current_include_sidebar = state.get_variable("INCLUDE_SIDEBAR")

        cached_url = metadata.get("url")
        cached_domain = metadata.get("domain")
        cached_row = metadata.get("row")
        cached_include_sidebar = metadata.get("include_sidebar", False)

        if current_url and cached_url:
            url_matches = normalize_url(cached_url) == normalize_url(current_url)
            if not url_matches:
                return (
                    False,
                    f"URL mismatch: cached={cached_url}, current={current_url}",
                )

        if current_domain and cached_domain and cached_domain != current_domain:
            return (
                False,
                f"Domain mismatch: cached={cached_domain}, current={current_domain}",
            )

        if current_row and cached_row and cached_row != current_row:
            return False, f"Row mismatch: cached={cached_row}, current={current_row}"

        sidebar_compatible = (not current_include_sidebar) or (
            current_include_sidebar and cached_include_sidebar
        )
        if not sidebar_compatible:
            return (
                False,
                f"Sidebar compatibility: need sidebar={current_include_sidebar}, cached sidebar={cached_include_sidebar}",
            )
        return True, "Cache is valid for current context"
    except Exception as e:
        debug_print(f"Error validating cache: {e}")
        return False, f"Error validating cache: {e}"


def _find_cache_file_for_domain_row(domain, row):
    if not domain or not row:
        return None
    cache_filename = f"page_check_{domain}-{row}.json"
    cache_file = CACHE_DIR / cache_filename
    if cache_file.exists():
        debug_print(f"Found cache file for {domain}-{row}: {cache_file}")
        return str(cache_file)
    debug_print(f"No cache file found for {domain}-{row}")
    return None


def _find_cache_file_for_url(url):
    if not url:
        return None
    url = normalize_url(url)
    for cache_file in CACHE_DIR.glob("page_check_*.json"):
        try:
            metadata, _ = _load_cached_page_data(cache_file)
            cached_url = metadata.get("url")
            if cached_url and normalize_url(cached_url) == url:
                debug_print(f"Found cache file for URL {url}: {cache_file}")
                return str(cache_file)
        except Exception as e:
            debug_print(f"Error checking cache file {cache_file}: {e}")
            continue
    debug_print(f"No cache file found for URL: {url}")
    return None


def _update_state_from_cache(state, url=None, domain=None, row=None):
    """
    Updates the state object with data from a cache file based on the provided
    URL, domain, or row. If a matching cache file is found, it loads metadata
    and page data into the state. If no matching cache file is found, it resets
    the relevant state variables.

    Args:
        state (object): The state object that holds variables and current page data.
        url (str, optional): The URL to search for a matching cache file. Defaults to None.
        domain (str, optional): The domain to search for a matching cache file. Defaults to None.
        row (str, optional): The row to search for a matching cache file. Defaults to None.

    Behavior:
        - Searches for a cache file based on the provided domain and row, or URL.
        - If a matching cache file is found:
            - Updates the `CACHE_FILE` variable in the state.
            - Loads metadata and page data from the cache file into the state.
            - Updates additional state variables (e.g., `KANBAN_ID`, `URL`, `DOMAIN`, etc.)
              based on the metadata.
        - If no matching cache file is found:
            - Resets the `CACHE_FILE` variable and clears the current page data in the state.
        - Logs debug messages and prints information about the cache loading process.

    Raises:
        Exception: If an error occurs while loading cached page data from the file.

    Note:
        This function relies on helper functions `_find_cache_file_for_domain_row`,
        `_find_cache_file_for_url`, and `_load_cached_page_data` to perform its operations.
    """

    current_cache_file = state.get_variable("CACHE_FILE")
    search_url = url or state.get_variable("URL")
    search_domain = domain or state.get_variable("DOMAIN")
    search_row = row or state.get_variable("ROW")

    found_cache_file = None
    if search_domain and search_row:
        found_cache_file = _find_cache_file_for_domain_row(search_domain, search_row)
    if not found_cache_file and search_url:
        found_cache_file = _find_cache_file_for_url(search_url)

    if current_cache_file and found_cache_file != current_cache_file:
        debug_print(
            f"Current cache file {current_cache_file} doesn't match new context, unsetting"
        )
        state.set_variable("CACHE_FILE", "")
        state.current_page_data = None

    if found_cache_file:
        state.set_variable("CACHE_FILE", found_cache_file)
        try:
            metadata, page_data = _load_cached_page_data(found_cache_file)
            if page_data:
                state.current_page_data = page_data
                if metadata:
                    if metadata.get("kanban_id"):
                        state.set_variable("KANBAN_ID", metadata["kanban_id"])
                    if metadata.get("url"):
                        state.set_variable("URL", metadata["url"])
                    if metadata.get("domain"):
                        state.set_variable("DOMAIN", metadata["domain"])
                    if metadata.get("row"):
                        state.set_variable("ROW", metadata["row"])
                    if metadata.get("selector"):
                        state.set_variable("SELECTOR", metadata["selector"])
                    if metadata.get("include_sidebar") is not None:
                        state.set_variable(
                            "INCLUDE_SIDEBAR", str(metadata["include_sidebar"]).lower()
                        )
                print(f"📋 Loaded cached data from {Path(found_cache_file).name}")
            else:
                debug_print(
                    f"Cache file {found_cache_file} exists but contains no page data"
                )
        except Exception as e:
            debug_print(f"Error loading cached page data from {found_cache_file}: {e}")
    elif not found_cache_file and current_cache_file:
        state.set_variable("CACHE_FILE", "")
        state.current_page_data = None
        debug_print("No matching cache file found, unset CACHE_FILE")
