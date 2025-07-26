import os
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# ensure commands module is importable from repo root
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

from commands import core as commands
from commands import clear
from commands import help as help_cmd
from commands import debug as debug_cmd
from commands import sidebar as sidebar_cmd
from commands import load as load_cmd
from commands import report as report_cmd


@pytest.fixture
def mock_state():
    state = MagicMock()
    state.get_variable = MagicMock(return_value=None)
    state.set_variable = MagicMock()
    return state


@pytest.fixture
def cli_state():
    from state import CLIState
    return CLIState()


# ----- cmd_sidebar tests -----

def test_cmd_sidebar_toggle_on(mock_state, capsys):
    mock_state.get_variable.return_value = False
    sidebar_cmd.cmd_sidebar([], mock_state)
    mock_state.set_variable.assert_called_once_with("INCLUDE_SIDEBAR", "true")
    assert "Sidebar inclusion: ON" in capsys.readouterr().out


def test_cmd_sidebar_set_off(mock_state, capsys):
    mock_state.get_variable.return_value = True
    sidebar_cmd.cmd_sidebar(["off"], mock_state)
    mock_state.set_variable.assert_called_once_with("INCLUDE_SIDEBAR", "false")
    assert "Sidebar inclusion: OFF" in capsys.readouterr().out


# ----- cmd_open tests -----

def test_cmd_open_dsm_success(tmp_path, monkeypatch, mock_state, capsys):
    dsm = tmp_path / "test.xlsx"
    dsm.touch()
    mock_state.get_variable.return_value = str(dsm)
    opener = MagicMock()
    monkeypatch.setattr(commands, "_open_file_in_default_app", opener)
    commands.cmd_open(["dsm"], mock_state)
    opener.assert_called_once_with(Path(dsm))
    assert f"Opening DSM file: {dsm}" in capsys.readouterr().out


def test_cmd_open_page_success(monkeypatch, mock_state, capsys):
    url = "http://example.com"
    mock_state.get_variable.return_value = url
    opener = MagicMock()
    monkeypatch.setattr(commands, "_open_url_in_browser", opener)
    commands.cmd_open(["page"], mock_state)
    opener.assert_called_once_with(url)
    assert "Opening URL in browser" in capsys.readouterr().out


def test_cmd_open_report_not_found(monkeypatch, mock_state, capsys):
    mock_state.get_variable.side_effect = lambda var: {"DOMAIN": "Example", "ROW": "1"}.get(var, "")
    opener = MagicMock()
    monkeypatch.setattr(commands, "_open_file_in_default_app", opener)
    commands.cmd_open(["report"], mock_state)
    opener.assert_not_called()
    out = capsys.readouterr().out
    assert "Report not found" in out
    assert "Generate a report first" in out


# ----- cmd_clear test -----

def test_cmd_clear(monkeypatch):
    call = MagicMock()
    monkeypatch.setattr(os, "system", call)
    monkeypatch.setattr(os, "name", "posix", raising=False)
    clear.cmd_clear([])
    call.assert_called_once_with("clear")


# ----- cmd_bulk_check tests -----

def test_cmd_bulk_check_creates_template(tmp_path, monkeypatch, cli_state, capsys):
    csv = tmp_path / "bulk.csv"
    create = MagicMock()
    monkeypatch.setattr(commands, "_create_bulk_check_template", create)
    commands.cmd_bulk_check([str(csv)], cli_state)
    create.assert_called_once_with(csv)
    out = capsys.readouterr().out
    assert "Creating template CSV" in out


def test_cmd_bulk_check_all_done(tmp_path, monkeypatch, cli_state, capsys):
    csv = tmp_path / "bulk.csv"
    csv.touch()
    loader = MagicMock(return_value=[])
    monkeypatch.setattr(commands, "_load_bulk_check_csv", loader)
    commands.cmd_bulk_check([str(csv)], cli_state)
    loader.assert_called_once_with(csv)
    assert "already been processed" in capsys.readouterr().out


# ----- cmd_check tests -----

def test_cmd_check_uses_cached_data(monkeypatch, cli_state, capsys):
    cli_state.set_variable("URL", "http://example.com")
    cli_state.set_variable("SELECTOR", "#main")
    cli_state.set_variable("INCLUDE_SIDEBAR", "false")
    cli_state.current_page_data = {"links": [], "pdfs": [], "embeds": []}
    cli_state.set_variable("CACHE_FILE", "cache.json")
    monkeypatch.setattr(commands, "_is_cache_valid_for_context", lambda s, c: (True, ""))
    gen = MagicMock()
    monkeypatch.setattr(report_cmd, "_generate_summary_report", gen)
    cache = MagicMock()
    monkeypatch.setattr(commands, "_cache_page_data", cache)
    commands.cmd_check([], cli_state)
    gen.assert_called_once_with(False, cli_state.current_page_data)
    cache.assert_not_called()
    assert "Using cached data" in capsys.readouterr().out


# ----- cmd_debug tests -----

def test_cmd_debug_toggle_on(monkeypatch, mock_state, capsys):
    mock_state.get_variable.return_value = False
    monkeypatch.setattr(commands, "sync_debug_with_state", MagicMock())
    debug_cmd.cmd_debug([], mock_state)
    mock_state.set_variable.assert_called_once_with("DEBUG", "true")
    assert "Debug mode: ON" in capsys.readouterr().out


def test_cmd_debug_set_off(monkeypatch, mock_state, capsys):
    mock_state.get_variable.return_value = True
    monkeypatch.setattr(commands, "sync_debug_with_state", MagicMock())
    debug_cmd.cmd_debug(["off"], mock_state)
    mock_state.set_variable.assert_called_once_with("DEBUG", "false")
    assert "Debug mode: OFF" in capsys.readouterr().out


# ----- cmd_help test -----

def test_cmd_help_output(cli_state, capsys):
    help_cmd.cmd_help([], cli_state)
    assert "COMMAND REFERENCE" in capsys.readouterr().out


# ----- cmd_links test -----

def test_cmd_links(monkeypatch, cli_state):
    func = MagicMock()
    import lookup_utils
    monkeypatch.setattr(lookup_utils, "analyze_page_links_for_migration", func)
    commands.cmd_links([], cli_state)
    func.assert_called_once_with(cli_state)


# ----- cmd_lookup test -----

def test_cmd_lookup_success(monkeypatch, cli_state, capsys):
    cli_state.excel_data = "sheet"
    lookup = MagicMock(return_value={})
    display = MagicMock()
    import lookup_utils
    monkeypatch.setattr(lookup_utils, "lookup_link_in_dsm", lookup)
    monkeypatch.setattr(lookup_utils, "display_link_lookup_result", display)
    commands.cmd_lookup(["http://example.com"], cli_state)
    lookup.assert_called_once_with("http://example.com", "sheet", cli_state)
    display.assert_called_once_with(lookup.return_value)


# ----- cmd_load test -----

def test_cmd_load_success(monkeypatch, cli_state, capsys):
    cli_state.excel_data = MagicMock()
    cli_state.excel_data.parse.return_value = "df"
    monkeypatch.setattr(load_cmd, "get_existing_url", lambda df, row: "http://page")
    monkeypatch.setattr(load_cmd, "get_proposed_url", lambda df, row: "/new")
    monkeypatch.setattr(load_cmd, "_update_cache_file_state", MagicMock())
    monkeypatch.setattr(load_cmd, "count_http", lambda url: 0)
    load_cmd.cmd_load(["Enterprise", "5"], cli_state)
    assert cli_state.get_variable("URL") == "http://page"
    assert "Loaded URL" in capsys.readouterr().out


# ----- cmd_migrate test -----

def test_cmd_migrate_calls_migrate(monkeypatch, cli_state):
    cli_state.set_variable("URL", "http://example.com")
    func = MagicMock()
    monkeypatch.setattr(commands, "migrate", func)
    commands.cmd_migrate([], cli_state)
    func.assert_called_once_with(cli_state, url="http://example.com")


# ----- cmd_report test -----

def test_cmd_report_multiple_rows(monkeypatch, cli_state):
    load = MagicMock()
    gen = MagicMock(return_value="file.html")
    opener = MagicMock()
    monkeypatch.setattr(report_cmd, "cmd_load", load)
    monkeypatch.setattr(report_cmd, "_generate_report", gen)
    monkeypatch.setattr(commands, "_open_file_in_default_app", opener)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    report_cmd.cmd_report(["Enterprise", "1", "2"], cli_state)
    assert load.call_count == 2
    assert gen.call_count == 2
    opener.assert_not_called()


# ----- cmd_set test -----

def test_cmd_set_url(monkeypatch, mock_state, capsys):
    mock_state.set_variable.return_value = True
    updater = MagicMock()
    monkeypatch.setattr(commands, "_update_cache_file_state", updater)
    commands.cmd_set(["URL", "http://example.com"], mock_state)
    mock_state.set_variable.assert_called_once_with("URL", "http://example.com")
    updater.assert_called_once_with(mock_state, url="http://example.com")
    assert "URL => http://example.com" in capsys.readouterr().out


# ----- cmd_show tests -----

def test_cmd_show_variables(mock_state):
    commands.cmd_show([], mock_state)
    mock_state.list_variables.assert_called_once()


def test_cmd_show_page_no_data(cli_state, capsys):
    commands.cmd_show(["page"], cli_state)
    assert "No page data loaded" in capsys.readouterr().out
