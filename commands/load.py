from data.dsm import (
    get_latest_dsm_file,
    load_spreadsheet,
    get_existing_urls,
    get_proposed_url,
    get_column_value,
)
from constants import DOMAINS
from utils.core import debug_print
from utils.cache import _update_state_from_cache
from utils.validation import validation_wrapper


def _extract_url_and_proposed_path(state, domain, row_num):
    """Load URLs and proposed path for a domain/row and update state.

    Parameters
    ----------
    state : object
        Current CLI state object containing the loaded spreadsheet and variables.
    domain : dict
        Domain configuration dictionary from :data:`DOMAINS`.
    row_num : int
        Row number in the spreadsheet to load.

    Returns
    -------
    tuple[list[str] | None, str | None]
        ``(urls, proposed_path)`` if URLs were found, otherwise ``(None, None)``.
    """

    if not state.excel_data:
        dsm_file = get_latest_dsm_file()
        if not dsm_file:
            raise RuntimeError(
                "No DSM file found. Set DSM_FILE manually or place a dsm-*.xlsx file in the directory."
            )
        state.excel_data = load_spreadsheet(dsm_file)
        state.set_variable("DSM_FILE", dsm_file)

    df_header_row = domain.get("worksheet_header_row", 4) + 2
    existing_url_header = domain.get("existing_url_col_name", "EXISTING URL")
    proposed_url_header = domain.get("proposed_url_col_name", "PROPOSED URL")

    df = state.excel_data.parse(
        sheet_name=domain.get("worksheet_name"),
        header=domain.get("worksheet_header_row", 4),
    )

    urls = get_existing_urls(df, row_num - df_header_row, col_name=existing_url_header)
    proposed = get_proposed_url(
        df, row_num - df_header_row, col_name=proposed_url_header
    )

    taxonomy = ""
    taxonomy_cols = [
        c for c in df.columns if isinstance(c, str) and "taxonomy" in c.lower().strip()
    ]
    if taxonomy_cols:
        debug_print(f"Found taxonomy column: {taxonomy_cols[0]}")
        taxonomy = get_column_value(df, row_num - df_header_row, taxonomy_cols[0])

    # sort the taxonomy values alphabetically and join with commas
    if taxonomy:
        taxonomy = ", ".join(sorted(map(str.strip, taxonomy.split(","))))

    if not urls:
        return None, None

    state.set_variable("URL", urls[0])
    state.set_variable("EXISTING_URLS", urls)
    state.set_variable("PROPOSED_PATH", proposed)
    state.set_variable("DOMAIN", domain.get("full_name", "Domain Placeholder"))
    state.set_variable("ROW", str(row_num))
    state.set_variable("TAXONOMY", taxonomy)

    _update_state_from_cache(
        state, url=urls[0], domain=domain.get("full_name"), row=str(row_num)
    )

    return urls, proposed


@validation_wrapper
def cmd_load(args, state, *, validated=None):
    """Load page information from the DSM spreadsheet.

    The command resolves ``<domain> <row>`` to an existing URL and proposed
    path, updating the relevant state variables. Cached data is loaded when
    available to avoid re-fetching page content.
    """
    state.reset_page_context_state()

    if validated:
        domain, row_num = validated
    else:
        return
    try:
        urls, _ = _extract_url_and_proposed_path(state, domain, row_num)
        if not urls:
            print(f"❌ Could not find URL for {domain.get('full_name')} row {row_num}")
            return

        primary = urls[0]
        print(f"✅ Loaded URL: {primary[:60]}{'...' if len(primary) > 60 else ''}")
        if len(urls) > 1:
            print("⚠️  WARNING: Multiple existing URLs detected for this row.")

    except RuntimeError as e:
        print(f"❌ {e}")
    except Exception as e:
        print(f"❌ Error loading from spreadsheet: {e}")
        debug_print(f"Full error: {e}")
