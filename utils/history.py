"""
Simple command history manager for people-card-cli.
Saves and loads command history from a dot file in the user's home directory.
"""

import os
import readline
from pathlib import Path
from typing import List, Optional


class CommandHistory:
    """Manages command history with persistent storage."""

    def __init__(self, history_file: Optional[str] = None):
        """Initialize history manager.

        Args:
            history_file: Path to history file. Defaults to ~/.people_card_cli_history
        """
        if history_file is None:
            history_file = os.path.expanduser("~/.people_card_cli_history")

        self.history_file = Path(history_file)
        self.max_history = 1000  # Keep last 1000 commands

        # Setup readline for arrow key navigation
        self._setup_readline()

        # Load existing history
        self.load_history()

    def _setup_readline(self):
        """Configure readline for command history navigation."""
        # Enable tab completion (though we don't use it much)
        readline.parse_and_bind("tab: complete")

        # Enable history search with up/down arrows
        readline.parse_and_bind('"\\e[A": previous-history')  # Up arrow
        readline.parse_and_bind('"\\e[B": next-history')  # Down arrow

        # Enable emacs-style editing
        readline.parse_and_bind("set editing-mode emacs")

    def load_history(self):
        """Load command history from file."""
        if not self.history_file.exists():
            return

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:  # Skip empty lines
                        readline.add_history(line)
        except (IOError, OSError) as e:
            # Silently ignore errors - history is nice-to-have
            pass

    def save_history(self):
        """Save current command history to file."""
        try:
            # Create directory if it doesn't exist
            self.history_file.parent.mkdir(parents=True, exist_ok=True)

            # Get history from readline
            history_length = readline.get_current_history_length()

            # Determine how many items to save (respect max_history)
            start_idx = max(0, history_length - self.max_history)

            with open(self.history_file, "w", encoding="utf-8") as f:
                for i in range(start_idx + 1, history_length + 1):
                    item = readline.get_history_item(i)
                    if item:
                        f.write(f"{item}\n")
        except (IOError, OSError) as e:
            # Silently ignore errors - history is nice-to-have
            pass

    def add_command(self, command: str):
        """Add a command to history.

        Args:
            command: The command string to add to history
        """
        command = command.strip()
        if not command:
            return

        # Don't add duplicate consecutive commands
        history_length = readline.get_current_history_length()
        if history_length > 0:
            last_command = readline.get_history_item(history_length)
            if last_command == command:
                return

        # Add to readline history
        readline.add_history(command)

    def get_input(self, prompt: str) -> str:
        """Get input with history support.

        Args:
            prompt: The prompt string to display

        Returns:
            The user input string
        """
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            # Re-raise these for the main loop to handle
            raise

    def clear_history(self):
        """Clear all command history."""
        readline.clear_history()
        if self.history_file.exists():
            try:
                self.history_file.unlink()
            except (IOError, OSError):
                pass

    def get_history_stats(self) -> dict:
        """Get history statistics for debugging.

        Returns:
            Dictionary with history stats
        """
        history_length = readline.get_current_history_length()
        file_exists = self.history_file.exists()
        file_size = self.history_file.stat().st_size if file_exists else 0

        return {
            "current_length": history_length,
            "file_exists": file_exists,
            "file_path": str(self.history_file),
            "file_size": file_size,
            "max_history": self.max_history,
        }


# Global history instance
_history = None


def get_history() -> CommandHistory:
    """Get the global history instance."""
    global _history
    if _history is None:
        _history = CommandHistory()
    return _history


def cleanup_history():
    """Save history on exit."""
    global _history
    if _history is not None:
        _history.save_history()
