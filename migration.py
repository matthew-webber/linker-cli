"""
Migration logic for Linker CLI.
"""

from migrate_hierarchy import print_hierarchy, print_proposed_hierarchy
from link_mapping import launch_link_mapping


def migrate(state, url=None, debug_print=None):
    url = url or state.get_variable("URL")
    if not url:
        print("❌ No URL set. Use 'set URL <value>' first.")
        return
    while True:
        print("\nMIGRATE MENU:")
        print("(p) Page mapping - show existing & proposed hierarchy")
        print("(l) Link mapping - review links to migrate")
        print("(q) Quit migrate mode")
        choice = input("Select option > ").strip().lower()
        if choice == "p":
            print_hierarchy(url)
            proposed = state.get_variable("PROPOSED_PATH")
            if proposed:
                print_proposed_hierarchy(url, proposed)
            else:
                proposed = input(
                    "Enter Proposed URL path (e.g. foo/bar/baz) > "
                ).strip()
                if proposed:
                    state.set_variable("PROPOSED_PATH", proposed)
                    print_proposed_hierarchy(url, proposed)
                else:
                    if debug_print:
                        debug_print("No proposed URL provided.")
        elif choice == "l":
            if not state.current_page_data:
                print("❌ No page data loaded. Run 'check' first.")
            else:
                launch_link_mapping(state.current_page_data)
        elif choice == "q":
            print("Exiting migrate mode.")
            break
        else:
            print("Invalid choice, please select 'p', 'l', or 'q'.")
