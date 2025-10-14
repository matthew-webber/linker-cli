"""
History management commands for people-card-cli.
"""

from utils.history import get_history


def cmd_history(args, state):
    """Handle history-related commands."""
    if not args:
        # Show recent history
        _show_recent_history()
    elif args[0] == "clear":
        _clear_history()
    elif args[0] == "stats":
        _show_history_stats()
    else:
        print("❌ Unknown history command")
        print("💡 Usage: history [clear|stats]")


def _show_recent_history():
    """Show recent command history."""
    import readline

    history_length = readline.get_current_history_length()
    if history_length == 0:
        print("📜 No command history found")
        return

    # Show last 10 commands
    start_idx = max(1, history_length - 9)
    print("📜 Recent command history:")
    for i in range(start_idx, history_length + 1):
        item = readline.get_history_item(i)
        if item:
            print(f"  {i:3d}: {item}")


def _clear_history():
    """Clear command history."""
    history = get_history()
    history.clear_history()
    print("🗑️  Command history cleared")


def _show_history_stats():
    """Show history statistics."""
    history = get_history()
    stats = history.get_history_stats()

    print("📊 History Statistics:")
    print(f"  Current session commands: {stats['current_length']}")
    print(f"  History file: {stats['file_path']}")
    print(f"  File exists: {stats['file_exists']}")
    if stats["file_exists"]:
        print(f"  File size: {stats['file_size']} bytes")
    print(f"  Max history size: {stats['max_history']} commands")
