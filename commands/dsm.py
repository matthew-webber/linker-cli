"""
Command to display DSM row data in tabular format.
"""

import pandas as pd
from constants import DOMAINS
from utils.core import debug_print
from data.dsm import get_column_value


def cmd_dsm(args, state):
    """Display the currently loaded domain row data in a tabular format.

    Shows all relevant columns from the DSM spreadsheet for the current
    domain and row that have been loaded with the 'load' command.
    """

    # Check if we have a loaded domain and row
    domain_name = state.get_variable("DOMAIN")
    row = state.get_variable("ROW")

    if not domain_name or not row:
        print("❌ No domain/row loaded. Use 'load <domain> <row>' first.")
        return

    if not state.excel_data:
        print("❌ No DSM file loaded. Use 'load' command first.")
        return

    # Find the domain configuration
    domain = next((d for d in DOMAINS if d.get("full_name") == domain_name), None)

    if not domain:
        print(f"❌ Domain '{domain_name}' not found in configuration.")
        return

    try:
        # Parse the worksheet
        df = state.excel_data.parse(
            sheet_name=domain.get("worksheet_name"),
            header=domain.get("worksheet_header_row", 4),
        )

        # Calculate the dataframe row index
        df_header_row = domain.get("worksheet_header_row", 4) + 2
        row_num = int(row)
        df_idx = row_num - df_header_row

        if df_idx < 0 or df_idx >= len(df):
            print(f"❌ Row {row_num} is out of range for domain '{domain_name}'.")
            return

        # Get the row data
        row_data = df.iloc[df_idx]

        # Prepare data for display
        display_data = []
        for col_name in df.columns:
            if pd.notna(col_name):
                col_str = str(col_name).strip()
                value = row_data[col_name]
                value_str = str(value) if pd.notna(value) else ""

                display_data.append({"Column": col_str, "Value": value_str})

        # Print header
        print("\n" + "=" * 80)
        print(f"DSM ROW DATA: {domain_name} - Row {row}")
        print("=" * 80)

        # Display as a table using pandas
        if display_data:
            display_df = pd.DataFrame(display_data)
            # Set pandas display options to show full content without truncation
            pd.set_option("display.max_colwidth", None)
            pd.set_option("display.width", None)
            pd.set_option("display.max_rows", None)
            print(display_df.to_string(index=False))
        else:
            print("No data found for this row.")

        print("=" * 80 + "\n")

    except Exception as e:
        print(f"❌ Error reading DSM data: {e}")
        debug_print(f"Exception details: {type(e).__name__}: {e}")
        if state.get_variable("DEBUG"):
            import traceback

            traceback.print_exc()
