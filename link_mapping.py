# link_mapping.py
import curses


def launch_link_mapping(page_data):
    """
    Full-screen TUI to list and select links/PDFs for migration.
    page_data: dict with 'links' and 'pdfs' lists of (text, href, status).
    """
    items = page_data.get("links", []) + page_data.get("pdfs", [])

    def _curses_main(stdscr):
        curses.curs_set(0)
        selected = [False] * len(items)
        pos = 0

        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            stdscr.addstr(
                0,
                0,
                "Link Mapping Checklist Mode\n\nCommands: ↑/↓ or k/j to move, space to toggle, q to quit",
                curses.A_BOLD,
            )
            for idx, (text, href, status) in enumerate(items):
                marker = "[x]" if selected[idx] else "[ ]"
                disp = text if len(text) <= w - 10 else text[: w - 13] + "..."
                line = f"{marker} {disp}"
                if idx == pos:
                    stdscr.attron(curses.A_REVERSE)
                    stdscr.addstr(idx + 1, 0, line)
                    stdscr.attroff(curses.A_REVERSE)
                else:
                    stdscr.addstr(idx + 1, 0, line)
            key = stdscr.getch()
            if key in (curses.KEY_UP, ord("k")):
                pos = (pos - 1) % len(items)
            elif key in (curses.KEY_DOWN, ord("j")):
                pos = (pos + 1) % len(items)
            elif key == ord(" "):
                selected[pos] = not selected[pos]
            elif key in (ord("q"), 27):  # 'q' or ESC
                break

        # On exit, show a simple summary
        stdscr.erase()
        stdscr.addstr(0, 0, "Selected links/PDFs:")
        row = 1
        for idx, sel in enumerate(selected):
            if sel:
                text, href, _ = items[idx]
                stdscr.addstr(row, 0, f"- {text[:w-5]} → {href}")
                row += 1
        stdscr.addstr(row + 1, 0, "Press any key to return.")
        stdscr.getch()

    curses.wrapper(_curses_main)
