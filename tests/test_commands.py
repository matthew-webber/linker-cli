import os
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# ensure commands module is importable from repo root
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from commands import core as commands
from commands import clear
from commands import common as debug_cmd
from commands import sidebar as sidebar_cmd
from commands import load as load_cmd
from commands import report as report_cmd
from commands import bulk as bulk_cmd
from commands import check as check_cmd
from utils import core as utils
from utils import cache as cache_utils
from utils import validation as validation_utils


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
    mock_state.get_variable.side_effect = lambda var: {
        "DOMAIN": "Example",
        "ROW": "1",
    }.get(var, "")
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
    monkeypatch.setattr(bulk_cmd, "_create_bulk_check_template", create)
    bulk_cmd.cmd_bulk_check([str(csv)], cli_state)
    create.assert_called_once_with(csv)
    out = capsys.readouterr().out
    assert "Creating template Excel file" in out


def test_cmd_bulk_check_all_done(tmp_path, monkeypatch, cli_state, capsys):
    csv = tmp_path / "bulk.csv"
    csv.touch()
    loader = MagicMock(return_value=[])
    monkeypatch.setattr(bulk_cmd, "_load_bulk_check_xlsx", loader)
    bulk_cmd.cmd_bulk_check([str(csv)], cli_state)
    loader.assert_called_once_with(csv)
    assert "already been processed" in capsys.readouterr().out


# ----- cmd_check tests -----

# ----- cmd_debug tests -----


def test_cmd_debug_toggle_on(monkeypatch, mock_state, capsys):
    mock_state.get_variable.return_value = False
    monkeypatch.setattr(utils, "sync_debug_with_state", MagicMock())
    debug_cmd.cmd_debug([], mock_state)
    mock_state.set_variable.assert_called_once_with("DEBUG", "true")
    assert "Debug mode: ON" in capsys.readouterr().out


def test_cmd_debug_set_off(monkeypatch, mock_state, capsys):
    mock_state.get_variable.return_value = True
    monkeypatch.setattr(utils, "sync_debug_with_state", MagicMock())
    debug_cmd.cmd_debug(["off"], mock_state)
    mock_state.set_variable.assert_called_once_with("DEBUG", "false")
    assert "Debug mode: OFF" in capsys.readouterr().out


# ----- cmd_help test -----


def test_cmd_help_output(cli_state, capsys):
    debug_cmd.cmd_help([], cli_state)
    assert "COMMAND REFERENCE" in capsys.readouterr().out


# ----- cmd_links test -----


def test_cmd_links(monkeypatch, cli_state):
    func = MagicMock()

    monkeypatch.setattr(
        utils,
        "output_internal_links_analysis_detail",
        func,
    )
    commands.cmd_links([], cli_state)
    func.assert_called_once_with(cli_state)


# ----- cmd_load test -----


def test_cmd_load_success(monkeypatch, cli_state, capsys):
    cli_state.excel_data = MagicMock()
    cli_state.excel_data.parse.return_value = "df"
    monkeypatch.setattr(
        load_cmd,
        "get_existing_urls",
        lambda df, row, col_name: ["http://page", "http://two"],
    )
    monkeypatch.setattr(load_cmd, "get_proposed_url", lambda df, row, col_name: "/new")
    monkeypatch.setattr(load_cmd, "_update_state_from_cache", MagicMock())
    load_cmd.cmd_load(["Enterprise", "5"], cli_state)
    assert cli_state.get_variable("URL") == "http://page"
    assert cli_state.get_variable("EXISTING_URLS") == [
        "http://page",
        "http://two",
    ]
    assert "Loaded URL" in capsys.readouterr().out


def test_cmd_load_invalid_args(monkeypatch, cli_state, capsys):
    """Ensure validation wrapper prevents execution with bad args."""
    cli_state.excel_data = MagicMock()
    monkeypatch.setattr(load_cmd, "get_existing_urls", MagicMock())
    monkeypatch.setattr(load_cmd, "get_proposed_url", MagicMock())
    load_cmd.cmd_load(["Enterprise", "bad"], cli_state)
    out = capsys.readouterr().out
    assert "Row number must be an integer" in out
    assert cli_state.get_variable("URL") == ""


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
    monkeypatch.setattr(commands, "_update_state_from_cache", updater)
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


# ----- _generate_consolidated_section tests -----


def test_generate_consolidated_section_no_page_data(mock_state):
    """Test that function returns appropriate message when no page data is available."""
    mock_state.current_page_data = None
    result = report_cmd._generate_consolidated_section(mock_state)
    assert result == "<p>No page data available.</p>"


def test_generate_consolidated_section_basic_structure(mock_state):
    """Test the basic HTML structure generation with minimal data."""
    mock_state.current_page_data = {"links": []}  # Non-empty dict
    mock_state.get_variable.side_effect = lambda var: {
        "URL": "https://example.com/test",
        "DOMAIN": "Example Domain",
        "ROW": "42",
        "PROPOSED_PATH": "",
    }.get(var, "")

    result = report_cmd._generate_consolidated_section(mock_state)

    # Check for basic structure elements
    assert '<div class="consolidated-section">' in result
    assert "<h3>📍 Source Information</h3>" in result
    assert "https://example.com/test" in result
    assert "Example Domain 42" in result
    assert "<h3>🏗️ Directory Structure</h3>" in result
    assert "<h3>🔗 Found Links & Resources</h3>" in result
    assert "<em>No links or resources found.</em>" in result


def test_generate_consolidated_section_with_meta_description(mock_state):
    """Test meta description handling - both present and truncated."""
    mock_state.current_page_data = {
        "meta_description": "This is a test meta description"
    }
    mock_state.get_variable.side_effect = lambda var: {
        "URL": "https://example.com",
        "DOMAIN": "Test",
        "ROW": "1",
        "PROPOSED_PATH": "",
    }.get(var, "")

    result = report_cmd._generate_consolidated_section(mock_state)
    assert "This is a test meta description" in result
    assert "copy-btn" in result


def test_generate_consolidated_section_long_meta_description(mock_state):
    """Test meta description truncation for long descriptions."""
    long_desc = "A" * 250  # Longer than 200 chars
    mock_state.current_page_data = {"meta_description": long_desc}
    mock_state.get_variable.side_effect = lambda var: {
        "URL": "https://example.com",
        "DOMAIN": "Test",
        "ROW": "1",
        "PROPOSED_PATH": "",
    }.get(var, "")

    result = report_cmd._generate_consolidated_section(mock_state)
    assert long_desc[:200] + "..." in result


def test_generate_consolidated_section_no_meta_description(mock_state):
    """Test handling when meta description is not available."""
    mock_state.current_page_data = {"links": []}  # Non-empty dict
    mock_state.get_variable.side_effect = lambda var: {
        "URL": "https://example.com",
        "DOMAIN": "Test",
        "ROW": "1",
        "PROPOSED_PATH": "",
    }.get(var, "")

    result = report_cmd._generate_consolidated_section(mock_state)
    assert "<em>Not available</em>" in result


def test_generate_consolidated_section_meta_robots(mock_state):
    """Test meta robots directives styling."""
    mock_state.current_page_data = {"meta_robots": "noindex, nofollow"}
    mock_state.get_variable.side_effect = lambda var: {
        "URL": "https://example.com",
        "DOMAIN": "Test",
        "ROW": "1",
        "PROPOSED_PATH": "",
    }.get(var, "")

    result = report_cmd._generate_consolidated_section(mock_state)
    # Should have red styling for both noindex and nofollow
    assert 'style="color: red; font-weight: bold;">noindex</span>' in result
    assert 'style="color: red; font-weight: bold;">nofollow</span>' in result


def test_generate_consolidated_section_with_proposed_path(mock_state):
    """Test proposed path handling and segment parsing."""
    mock_state.current_page_data = {"links": []}  # Non-empty dict
    mock_state.get_variable.side_effect = lambda var: {
        "URL": "https://example.com/dept/surgery",
        "DOMAIN": "Test",
        "ROW": "1",
        "PROPOSED_PATH": "/redesign/medical/surgery",
    }.get(var, "")

    result = report_cmd._generate_consolidated_section(mock_state)
    assert "redesign" in result
    assert "medical" in result
    assert "surgery" in result


def test_generate_consolidated_section_content_hub_hack(mock_state):
    """Test the Content Hub path hack that removes sitecore/content/Content Hub."""
    mock_state.current_page_data = {"links": []}  # Non-empty dict
    mock_state.get_variable.side_effect = lambda var: {
        "URL": "https://example.com",
        "DOMAIN": "Test",
        "ROW": "1",
        "PROPOSED_PATH": "/sitecore/content/Content Hub/test/path",
    }.get(var, "")

    result = report_cmd._generate_consolidated_section(mock_state)
    # Should have removed the first three segments
    assert "test" in result
    assert "path" in result


def test_generate_consolidated_section_with_links(mock_state):
    """Test link processing with different types and statuses."""
    mock_state.current_page_data = {
        "links": [
            ("External Link", "https://external.com", 200),
            ("Broken Link", "https://broken.com", 404),
            ("Unchecked Link", "https://unchecked.com", 0),
        ],
        "pdfs": [("PDF Document", "https://example.com/doc.pdf", 200)],
    }
    mock_state.get_variable.side_effect = lambda var: {
        "URL": "https://example.com",
        "DOMAIN": "Test",
        "ROW": "1",
        "PROPOSED_PATH": "",
    }.get(var, "")
    mock_state.excel_data = None

    result = report_cmd._generate_consolidated_section(mock_state)

    # Check for status indicators
    assert "🟢" in result  # 200 status
    assert "🔴" in result  # 404 status
    assert "⚪" in result  # 0 status

    # Check for link types
    assert "[Link]" in result
    assert "[Pdf]" in result

    # Check for link text
    assert "External Link" in result
    assert "PDF Document" in result


def test_generate_consolidated_section_contact_links(mock_state):
    """Test special handling for tel: and mailto: links."""
    mock_state.current_page_data = {
        "links": [
            ("Call Us", "tel:+18005551234", 200),
            ("Email Us", "mailto:test@example.com", 200),
        ]
    }
    mock_state.get_variable.side_effect = lambda var: {
        "URL": "https://example.com",
        "DOMAIN": "Test",
        "ROW": "1",
        "PROPOSED_PATH": "",
    }.get(var, "")
    mock_state.excel_data = None

    result = report_cmd._generate_consolidated_section(mock_state)

    # Should have anchor copy buttons for contact links
    assert "copy-anchor-btn" in result
    assert "copyAnchorToClipboard" in result


def test_generate_consolidated_section_exception_handling(mock_state, monkeypatch):
    """Test that exceptions in sitecore utilities are handled gracefully."""

    def mock_get_current_root(url):
        raise Exception("Test exception")

    monkeypatch.setattr(
        "utils.sitecore.get_current_sitecore_root", mock_get_current_root
    )

    mock_state.current_page_data = {"links": []}  # Non-empty dict
    mock_state.get_variable.side_effect = lambda var: {
        "URL": "https://example.com",
        "DOMAIN": "Test",
        "ROW": "1",
        "PROPOSED_PATH": "",
    }.get(var, "")

    result = report_cmd._generate_consolidated_section(mock_state)

    # Should still generate HTML with fallback values
    assert '<div class="consolidated-section">' in result
    assert "Sites" in result  # fallback root


def test_generate_consolidated_section_sidebar_items(mock_state):
    """Test processing of sidebar links, PDFs, and embeds."""
    mock_state.current_page_data = {
        "sidebar_links": [("Sidebar Link", "https://sidebar.com", 200)],
        "sidebar_pdfs": [("Sidebar PDF", "https://example.com/sidebar.pdf", 200)],
        "embeds": [("Main Embed", "https://embed.com", 200)],
        "sidebar_embeds": [("Sidebar Embed", "https://sidebar-embed.com", 200)],
    }
    mock_state.get_variable.side_effect = lambda var: {
        "URL": "https://example.com",
        "DOMAIN": "Test",
        "ROW": "1",
        "PROPOSED_PATH": "",
    }.get(var, "")
    mock_state.excel_data = None

    result = report_cmd._generate_consolidated_section(mock_state)

    # Check for different item types
    assert "[Sidebar Link]" in result
    assert "[Sidebar Pdf]" in result
    assert "[Embed]" in result
    assert "[Sidebar Embed]" in result


# ----- validation utils tests -----


def test_validate_load_args_success():
    domain, row = validation_utils.validate_load_args(["Enterprise", "10"])
    assert domain.get("full_name") == "Enterprise"
    assert row == 10


def test_validate_load_args_invalid_row():
    with pytest.raises(ValueError, match="Row number must be an integer"):
        validation_utils.validate_load_args(["Enterprise", "bad"])


def test_validate_load_args_unknown_domain():
    with pytest.raises(ValueError, match="Domain 'Unknown'"):
        validation_utils.validate_load_args(["Unknown", "1"])


def test_validate_load_args_missing_args():
    with pytest.raises(ValueError, match="Expected: load <domain> <row>"):
        validation_utils.validate_load_args([])
