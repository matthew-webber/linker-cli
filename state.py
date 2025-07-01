"""
State management for Linker CLI.
"""


class CLIState:
    """Global state manager for the CLI application."""

    def __init__(self):
        self.variables = {
            "URL": "",
            "DOMAIN": "",
            "ROW": "",
            "SELECTOR": "#main",
            "DSM_FILE": "",
            "CACHE_FILE": "",
            "PROPOSED_PATH": "",
        }
        self.excel_data = None
        self.current_page_data = None

    def set_variable(self, name, value, debug_print=None):
        name = name.upper()
        if name in self.variables:
            old_value = self.variables[name]
            self.variables[name] = str(value) if value is not None else ""
            if debug_print:
                debug_print(
                    f"Variable {name} changed from '{old_value}' to '{self.variables[name]}'"
                )
            return True
        else:
            if debug_print:
                debug_print(f"Unknown variable: {name}")
            return False

    def get_variable(self, name):
        name = name.upper()
        return self.variables.get(name, "")

    def list_variables(self):
        print("\n" + "=" * 50)
        print("CURRENT VARIABLES")
        print("=" * 50)
        for name, value in self.variables.items():
            status = "✅ SET" if value else "❌ UNSET"
            display_value = value[:40] + "..." if len(value) > 40 else value
            print(f"{name:12} = {display_value:40} [{status}]")
        print("=" * 50)

    def validate_required_vars(self, required_vars):
        missing = []
        for var in required_vars:
            if not self.get_variable(var):
                missing.append(var)
        return missing
