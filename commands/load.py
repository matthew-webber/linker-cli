from data.dsm import (
    count_http,
    get_latest_dsm_file,
    load_spreadsheet,
    get_existing_url,
    get_proposed_url,
)
from constants import DOMAINS
from utils.core import debug_print
from commands.common import print_help_for_command
from utils.cache import _update_state_from_cache


def cmd_load(args, state):
    """Handle the 'load' command for loading URLs from spreadsheet."""
    state.reset_page_context_state()

    if not args or len(args) < 2:
        return print_help_for_command("load", state)

    if not state.excel_data:
        dsm_file = get_latest_dsm_file()
        if not dsm_file:
            print("❌ No DSM file found. Set DSM_FILE manually.")
            return
        state.excel_data = load_spreadsheet(dsm_file)
        state.set_variable("DSM_FILE", dsm_file)

    user_domain = " ".join(args[:-1])
    row_arg = args[-1]

    debug_print("Executing cmd_load with args:", args)

    domain = next(
        (d for d in DOMAINS if d.get("full_name", "").lower() == user_domain.lower()),
        None,
    )

    df_header_row = domain.get("worksheet_header_row", 4) if domain else 4
    df_header_row = df_header_row + 2
    existing_url_header = domain.get("existing_url_col_name", "EXISTING URL")
    proposed_url_header = domain.get("proposed_url_col_name", "PROPOSED URL")

    try:
        row_num = int(row_arg)
    except ValueError:
        print("❌ Row number must be an integer")
        return

    if not domain:
        print(f"❌ Domain '{user_domain}' not found.")
        print("Available domains:")
        for i, domain in enumerate([d.get("full_name") for d in DOMAINS], 1):
            print(f"  {i:2}. {domain}")
        return

    try:
        df = state.excel_data.parse(
            sheet_name=domain.get("worksheet_name"),
            header=domain.get("worksheet_header_row", 4),
        )
        url = get_existing_url(
            df, row_num - df_header_row, col_name=existing_url_header
        )
        proposed = get_proposed_url(
            df, row_num - df_header_row, col_name=proposed_url_header
        )

        if not url:
            print(f"❌ Could not find URL for {domain} row {row_num}")
            return

        state.set_variable("URL", url)
        state.set_variable("PROPOSED_PATH", proposed)
        state.set_variable("DOMAIN", domain.get("full_name", "Domain Placeholder"))
        state.set_variable("ROW", str(row_num))

        _update_state_from_cache(
            state, url=url, domain=domain.get("full_name"), row=str(row_num)
        )

        warn = count_http(url) > 1
        print(f"✅ Loaded URL: {url[:60]}{'...' if len(url) > 60 else ''}")
        if warn:
            print("⚠️  WARNING: Multiple URLs detected in this cell.")

    except Exception as e:
        print(f"❌ Error loading from spreadsheet: {e}")
        debug_print(f"Full error: {e}")
