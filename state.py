"""
State management for Linker CLI.
"""

import re
from utils.core import debug_print


class CLIState:
    """Global state manager for the CLI application."""

    def __init__(self):
        self.variables = {
            "URL": "",
            "EXISTING_URLS": [],
            "DOMAIN": "",
            "ROW": "",
            "KANBAN_ID": "",
            "SELECTOR": "#main",
            "INCLUDE_SIDEBAR": "false",
            "DSM_FILE": "",
            "CACHE_FILE": "",
            "PROPOSED_PATH": "",
            "DEBUG": "true",
            "TAXONOMY": "",
        }
        self.excel_data = None
        self.current_page_data = None

        # Variables that should be returned as booleans
        self.boolean_variables = {"INCLUDE_SIDEBAR", "DEBUG"}

        self.valid_variable_formats = {
            "URL": r"^https?://",
            "INCLUDE_SIDEBAR": r"^(true|false)$",
            "DSM_FILE": r"^[\w\-. ]+\.xlsx$",
            "CACHE_FILE": r"^[\w\-. ]+\.json$",
        }

    def set_variable(self, name, value):
        name = name.upper()
        if name in self.variables:
            old_value = self.variables[name]
            if isinstance(value, (list, dict)):
                self.variables[name] = value
            else:
                self.variables[name] = str(value) if value is not None else ""
            debug_print(
                f"❤️Variable {name} changed from '{old_value}' to '{self.variables[name]}'"
            )
            return True
        else:
            debug_print(f"💙Unknown variable: {name}")
            return False

    def get_variable(self, name):
        name = name.upper()
        value = self.variables.get(name, "")

        # Convert boolean variables to actual booleans
        if name in self.boolean_variables:
            return value.lower() in ["true", "1", "yes", "on"]

        return value

    def get_raw_variable(self, name):
        """Get the raw string value without boolean conversion."""
        name = name.upper()
        return self.variables.get(name, "")

    def list_variables(self):
        print("\n" + "=" * 50)
        print("CURRENT VARIABLES")
        print("=" * 50)
        for name, value in self.variables.items():
            status = "✅ SET" if value else "❌ UNSET"
            display_value = str(value)
            display_value = (
                display_value[:40] + "..." if len(display_value) > 40 else display_value
            )
            print(f"{name:20} = {display_value:45} [{status}]")
        print("=" * 50)

    def validate_required_vars(self, required_vars):
        missing = []
        invalid = []
        for var in required_vars:
            if not self.get_raw_variable(var):
                missing.append(var)

            if var in self.valid_variable_formats:
                if not re.match(
                    self.valid_variable_formats[var], self.get_raw_variable(var)
                ):
                    invalid.append(var)

        if missing:
            print(f"❌ Missing required variables: {', '.join(missing)}")
        if invalid:
            print(f"❌ Invalid variables: {', '.join(invalid)}")
        else:
            debug_print("All required variables are set.")

        return missing, invalid

    def reset_page_context_state(self):
        """Reset page-specific variables to their defaults."""
        self.variables["URL"] = ""
        self.variables["EXISTING_URLS"] = []
        self.variables["DOMAIN"] = ""
        self.variables["ROW"] = ""
        self.variables["KANBAN_ID"] = ""
        self.variables["PROPOSED_PATH"] = ""
        self.variables["TAXONOMY"] = ""
        debug_print("Variables reset to defaults.")
