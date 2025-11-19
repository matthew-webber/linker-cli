#!/usr/bin/env python3
"""
Stand-alone script to check T1-T6 columns in DSM for domain-row entries.

This script reads a text file with lines formatted as "Domain - Row | ..." and
checks if any of the T1-T6 columns contain text in the corresponding DSM row.
If text is found, it prepends the column name (e.g., "T2 | ") to the line.
If no text is found in any T columns, it prepends "T??? | ".

Usage:
    python check_t_columns.py [input_file] [output_file]

Default input: foo.txt
Default output: bar.txt
"""

import sys
import re
import glob
import os
import warnings
import pandas as pd
from pathlib import Path

# Suppress openpyxl warnings about unsupported extensions
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


# Domain configuration (copied from constants.py)
DOMAINS = [
    {
        "full_name": "Enterprise",
        "worksheet_name": "Enterprise",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "Adult Health",
        "worksheet_name": "Adult Health",
        "worksheet_header_row": 2,
    },
    {
        "full_name": "Education",
        "worksheet_name": "Education",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "Research",
        "worksheet_name": "Research",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "Hollings Cancer",
        "worksheet_name": "Hollings Cancer",
        "aliases": ["Hollings Cancer Center", "HCC", "Hollings"],
        "worksheet_header_row": 3,
    },
    {
        "full_name": "Childrens Health",
        "worksheet_name": "Childrens Health",
        "aliases": ["Children's Health", "Kids", "Children's"],
        "worksheet_header_row": 3,
    },
    {
        "full_name": "CDM",
        "worksheet_name": "CDM",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "MUSC Giving",
        "worksheet_name": "MUSC Giving",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "CGS",
        "worksheet_name": "CGS",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "CHP",
        "worksheet_name": "CHP",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "COM",
        "worksheet_name": "COM",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "CON",
        "worksheet_name": "CON",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "COP",
        "worksheet_name": "COP",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "News Releases",
        "worksheet_name": "News Releases",
        "worksheet_header_row": 0,
    },
    {
        "full_name": "Progress Notes",
        "worksheet_name": "ProgressNotes",
        "aliases": ["ProgressNotes"],
        "worksheet_header_row": 0,
    },
]


def get_latest_dsm_file():
    """Find the most recent DSM spreadsheet file."""
    pattern = "dsm-*.xlsx"
    files = glob.glob(pattern)

    if not files:
        print(f"❌ No DSM files found matching pattern '{pattern}'")
        return None

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
            except ValueError:
                continue

    if latest:
        print(f"📊 Using DSM file: {latest}")
    else:
        print(f"❌ No valid DSM files found")

    return latest


def normalize_domain_name(domain_text):
    """
    Normalize domain name to match DOMAINS configuration.
    Handles variations like "Children's Health" -> "Childrens Health"
    """
    domain_text = domain_text.strip()

    # First try exact match
    for domain in DOMAINS:
        if domain["full_name"].lower() == domain_text.lower():
            return domain
        # Check aliases
        if "aliases" in domain:
            for alias in domain["aliases"]:
                if alias.lower() == domain_text.lower():
                    return domain

    return None


def parse_line(line):
    """
    Parse a line from the input file.
    Expected format: "Domain - Row | Additional text"
    or "Domain Row | Additional text" (without dash)

    Returns: (domain_name, row_number, original_line) or (None, None, original_line)
    """
    line = line.strip()
    if not line:
        return None, None, line

    # Try pattern with dash: "Domain - Row | ..."
    match = re.match(r"^([^-|]+?)\s*-\s*(\d+)\s*\|(.*)$", line)
    if match:
        domain = match.group(1).strip()
        row = match.group(2).strip()
        rest = match.group(3).strip()
        return domain, row, line

    # Try pattern without dash: "Domain Row | ..."
    match = re.match(r"^([A-Z][^|]+?)\s+(\d+)\s*\|(.*)$", line)
    if match:
        domain = match.group(1).strip()
        row = match.group(2).strip()
        rest = match.group(3).strip()
        return domain, row, line

    return None, None, line


def check_t_columns(domain_config, row_number, excel_data):
    """
    Check if T1-T6 columns have any text for the given row.

    Returns: list of column names that have text (e.g., ["T1", "T3"])
    """
    try:
        df = excel_data.parse(
            sheet_name=domain_config["worksheet_name"],
            header=domain_config.get("worksheet_header_row", 3),
        )

        # Calculate the dataframe row index
        df_header_row = domain_config.get("worksheet_header_row", 3) + 2
        row_num = int(row_number)
        df_idx = row_num - df_header_row

        if df_idx < 0 or df_idx >= len(df):
            print(
                f"  ⚠️  Row {row_num} is out of range for domain '{domain_config['full_name']}'"
            )
            return []

        # Get the row data
        row_data = df.iloc[df_idx]

        # Check T1-T9 columns
        found_columns = []
        for t_num in range(1, 10):
            col_name = f"T{t_num}"

            # Find the column (case-insensitive)
            matching_col = None
            for col in df.columns:
                if isinstance(col, str) and col.strip().upper() == col_name:
                    matching_col = col
                    break

            if matching_col is not None:
                value = row_data[matching_col]
                if pd.notna(value) and str(value).strip():
                    found_columns.append(col_name)

        return found_columns

    except Exception as e:
        print(f"  ❌ Error checking row {row_number}: {e}")
        return []


def process_file(input_file, output_file):
    """Process the input file and write results to output file."""

    # Load DSM file
    dsm_file = get_latest_dsm_file()
    if not dsm_file:
        print("Cannot proceed without a DSM file.")
        return

    print(f"📖 Loading Excel file: {dsm_file}")
    try:
        excel_data = pd.ExcelFile(dsm_file)
    except Exception as e:
        print(f"❌ Error loading Excel file: {e}")
        return

    # Read input file
    print(f"📄 Reading input file: {input_file}")
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Error reading input file: {e}")
        return

    print(f"Processing {len(lines)} lines...")

    # Process each line
    output_lines = []
    processed_count = 0
    skipped_count = 0

    for i, line in enumerate(lines, 1):
        domain_text, row_number, original_line = parse_line(line)

        if domain_text is None or row_number is None:
            # Keep line as-is if we can't parse it
            output_lines.append(
                original_line + "\n"
                if not original_line.endswith("\n")
                else original_line
            )
            skipped_count += 1
            continue

        # Normalize domain name
        domain_config = normalize_domain_name(domain_text)

        if domain_config is None:
            print(f"  Line {i}: Unknown domain '{domain_text}' - skipping")
            output_lines.append(
                original_line + "\n"
                if not original_line.endswith("\n")
                else original_line
            )
            skipped_count += 1
            continue

        # Check T columns
        t_columns = check_t_columns(domain_config, row_number, excel_data)

        # Prepare new line
        if t_columns:
            # Join multiple T columns with commas if more than one
            t_label = ", ".join(t_columns)
            new_line = f"{t_label} | {original_line}"
            print(
                f"  ✔️ Line {i}: {domain_config['full_name']} - {row_number} -> Found: {t_label}"
            )
        else:
            new_line = f"T??? | {original_line}"
            print(
                f"  ⭕️ Line {i}: {domain_config['full_name']} - {row_number} -> No T columns found"
            )

        output_lines.append(
            new_line + "\n" if not new_line.endswith("\n") else new_line
        )
        processed_count += 1

    # Write output file
    print(f"\n📝 Writing output file: {output_file}")
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.writelines(output_lines)
    except Exception as e:
        print(f"❌ Error writing output file: {e}")
        return

    print(f"\n✅ Done!")
    print(f"   Processed: {processed_count} lines")
    print(f"   Skipped: {skipped_count} lines")
    print(f"   Output written to: {output_file}")

    excel_data.close()


def main():
    """Main entry point."""
    # Parse command-line arguments
    input_file = sys.argv[1] if len(sys.argv) > 1 else "foo.txt"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "bar.txt"

    print("=" * 80)
    print("DSM T-Column Checker")
    print("=" * 80)
    print(f"Input file:  {input_file}")
    print(f"Output file: {output_file}")
    print("=" * 80)
    print()

    if not os.path.exists(input_file):
        print(f"❌ Input file '{input_file}' not found!")
        sys.exit(1)

    process_file(input_file, output_file)


if __name__ == "__main__":
    main()
