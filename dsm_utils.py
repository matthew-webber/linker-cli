"""
DSM/Spreadsheet utilities for Linker CLI.
"""

import os
import re
import glob
import pandas as pd
from pathlib import Path

from utils import debug_print

# HEADER_ROW = 3  # zero-based index where actual header resides
# ROW_OFFSET = HEADER_ROW + 2  # number of rows before data starts
DSM_DIR = Path(".")


def get_latest_dsm_file():
    pattern = str(DSM_DIR / "dsm-*.xlsx")
    files = glob.glob(pattern)
    debug_print(f"Searching for DSM files with pattern: {pattern}")
    debug_print(f"Found files: {files}")
    latest = None
    latest_date = None
    for f in files:
        basename = os.path.basename(f)
        m = re.match(r"dsm-(\d{4})\.xlsx", basename)
        if m:
            dt = m.group(1)
            try:
                month = int(dt[:2])
                day = int(dt[2:])
                date = (month, day)
                if latest_date is None or date > latest_date:
                    latest_date = date
                    latest = f
                    debug_print(f"New latest DSM candidate: {f} (date {date})")
            except ValueError:
                debug_print(f"Skipping invalid DSM filename: {basename}")
                continue
    debug_print(f"Selected latest DSM file: {latest}")
    return latest


def load_spreadsheet(path):
    debug_print(f"Loading spreadsheet: {path}")
    return pd.ExcelFile(path)


def get_column_value(sheet_df, excel_row, column_name):
    df_idx = excel_row
    target_col = next(
        (
            c
            for c in sheet_df.columns
            if isinstance(c, str) and c.strip().upper() == column_name.upper()
        ),
        None,
    )
    if not target_col:
        debug_print(f"Column '{column_name}' not found in sheet")
        return ""
    try:
        row = sheet_df.iloc[df_idx]
        value = row[target_col]
        return str(value) if pd.notna(value) else ""
    except IndexError:
        debug_print(f"Row index {df_idx} out of range")
        return ""
    except Exception as e:
        debug_print(f"Error retrieving {column_name}: {e}")
        return ""


def get_existing_url(sheet_df, excel_row):
    return get_column_value(sheet_df, excel_row, "EXISTING URL")


def get_proposed_url(sheet_df, excel_row):
    return get_column_value(sheet_df, excel_row, "PROPOSED URL")


def get_row_data(sheet_df, excel_row, columns=None):
    debug_print(f"Extracting row data from Excel row {excel_row}")
    if columns is None:
        columns = ["EXISTING URL", "PROPOSED URL"]
    result = {}
    for col in columns:
        result[col.upper()] = get_column_value(sheet_df, excel_row, col)
    debug_print(f"Extracted row data: {result}")
    return result


def count_http(url):
    cnt = url.count("http")
    debug_print(f"Counted {cnt} occurrences of 'http' in URL")
    return cnt
