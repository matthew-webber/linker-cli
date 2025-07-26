from constants import DOMAINS


def _get_var_description(var):
    """Get description for a variable."""
    descriptions = {
        "URL": "Target URL to analyze/migrate",
        "DOMAIN": "Current spreadsheet domain",
        "ROW": "Current spreadsheet row number",
        "SELECTOR": "CSS selector for content extraction",
        "DSM_FILE": "Path to the DSM Excel file",
        "CACHE_FILE": "Last cached data file path",
        "PROPOSED_PATH": "Proposed URL path for migration (e.g. /foo/bar/baz)",
    }
    return descriptions.get(var, "User-defined variable")


def print_help_for_command(command, state):
    """Display usage information for a specific command."""
    match command:
        case "set":
            print("Usage: set <VARIABLE> <value>")
            print("Available variables:")
            for var in state.variables.keys():
                print(f"  {var}")
            return
        case "bulk_check":
            print("Usage: bulk_check [csv_filename]")
            print()
            print("Process multiple pages from a CSV file and update with link counts.")
            print(
                "The CSV should have columns: title, domain, row, existing_url, no_links, no_pdfs, no_embeds, % difficulty"
            )
            print()
            print("If no filename is provided, uses 'bulk_check_progress.csv'")
            print(
                "Only processes rows where no_links, no_pdfs, no_embeds, and % difficulty are empty."
            )
            print()
            print("The command will:")
            print("  1. Create a template CSV if it doesn't exist")
            print("  2. Load each unprocessed row from the CSV")
            print("  3. Run the check command on each URL")
            print("  4. Update the CSV with link counts and difficulty percentage")
            print("  5. Cache the page data for faster report generation")
            print()
            print("% difficulty represents the percentage of non-easy links (tel: and mailto: are easy)")
            return
        case "debug":
            print("Usage: debug [on|off]")
            print("Toggle debug output; no argument toggles the current state.")
            return
        case "sidebar":
            print("Usage: sidebar [on|off]")
            print("Toggle inclusion of sidebar content when analyzing pages.")
            return
        case "lookup":
            print("Usage: lookup <url>")
            print("Example: lookup https://medicine.musc.edu/departments/surgery")
            print("Look up where a link should point on the new site using the DSM file.")
            return
        case "load":
            print("Usage: load <domain> <row_number>")
            if state.excel_data:
                print("Available domains:")
                for i, domain in enumerate([d.get("full_name") for d in DOMAINS], 1):
                    print(f"  {i:2}. {domain}")
            return
        case "open":
            print("Usage: open <target>")
            print("Available targets:")
            print("  dsm        - Open the loaded DSM Excel file")
            print("  [page|url] - Open the current URL in browser")
            print("  report     - Open the latest report for current domain/row")
            return
        case "report":
            print("Usage: report [--force] [<domain> <row1> [row2 ...]]")
            print(
                "Generate an HTML report for the specified rows or the current context if no arguments are provided."
            )
            print("Options:")
            print("  --force, -f    Force regeneration even if report already exists and is current")
            return
        case "check":
            print("Usage: check")
            print("Analyze the current URL using the configured selector.")
            return
        case "migrate":
            print("Usage: migrate")
            print("Generate a migration hierarchy for the currently loaded URL.")
            return
        case "links":
            print("Usage: links")
            print("Analyze all links on the current page for migration mapping.")
            return
        case "show":
            print("Usage: show [variables|domains|page]")
            print("Display current variables, list available domains, or show page data.")
            return
        case "clear":
            print("Usage: clear")
            print("Clear the terminal screen.")
            return
        case "help":
            print("Usage: help [command]")
            print("Show general help or help for a specific command.")
            return


def display_domains():
    """Print the list of available domains."""
    for i, domain in enumerate([domain.get("full_name") for domain in DOMAINS], 1):
        print(f"  {i:2}. {domain}")

