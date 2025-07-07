import pytest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from commands import *


@pytest.fixture
def mock_cache_page_data(monkeypatch):
    """Prevent saving to file."""
    monkeypatch.setattr("commands.cache_page_data", MagicMock())


@pytest.fixture
def mock_state():
    """Fixture to create a mock state object."""
    state = MagicMock()
    state.list_variables = MagicMock()
    state.validate_required_vars = MagicMock(return_value=([], []))

    state.excel_data = None
    state.current_page_data = None

    return state


@pytest.fixture
def mock_spinner(monkeypatch):
    spinner = MagicMock(spec=["start", "stop"])
    monkeypatch.setattr("commands.Spinner", lambda x: spinner)
    return spinner


def test_cmd_show_variables(mock_state):
    """Test showing variables."""
    cmd_show(["variables"], mock_state)
    mock_state.list_variables.assert_called_once()


def test_cmd_show_domains_no_dsm(mock_state):
    """Test showing domains when no DSM file is loaded."""
    mock_state.excel_data = None
    cmd_show(["domains"], mock_state)
    mock_state.list_variables.assert_not_called()


def test_cmd_show_domains_with_dsm(mock_state):
    """Test showing domains when DSM file is loaded."""
    mock_state.excel_data = MagicMock()
    cmd_show(["domains"], mock_state)
    mock_state.list_variables.assert_not_called()


def test_cmd_show_page_no_data(mock_state):
    """Test showing page data when no page data is loaded."""
    mock_state.current_page_data = None
    cmd_show(["page"], mock_state)
    mock_state.list_variables.assert_not_called()


def test_cmd_show_page_with_data(mock_state):
    """Test showing page data when page data is loaded."""
    mock_state.current_page_data = {"key": "value"}
    cmd_show(["page"], mock_state)
    mock_state.list_variables.assert_not_called()


def test_cmd_show_invalid_target(mock_state):
    """Test showing an invalid target."""
    cmd_show(["invalid"], mock_state)
    mock_state.list_variables.assert_not_called()


def test_cmd_show_no_args(mock_state):
    """Test showing variables when no arguments are provided."""
    cmd_show([], mock_state)
    mock_state.list_variables.assert_called_once()


def test_display_domains(mock_state):
    """Test displaying domains."""
    mock_state.excel_data = MagicMock()
    mock_state.excel_data.sheet_names = ["Sheet1", "Sheet2"]
    cmd_show(["domains"], mock_state)
    # Assuming display_domains is called within cmd_show
    # This would need to be adjusted based on actual implementation
    assert mock_state.list_variables.call_count == 1


def test_display_domains(capsys):
    """Test the display_domains function with mocked DOMAINS."""
    mocked_domains = [
        {"full_name": "Mock Domain 1"},
        {"full_name": "Mock Domain 2"},
        {"full_name": "Mock Domain 3"},
    ]

    # Patch the DOMAINS constant in the commands module
    with patch("commands.DOMAINS", mocked_domains):
        display_domains()

    # Capture the printed output
    captured = capsys.readouterr()

    # Define the expected output
    expected_output = (
        "   1. Mock Domain 1\n" "   2. Mock Domain 2\n" "   3. Mock Domain 3\n"
    )

    # Assert that the output matches the expected output
    assert captured.out == expected_output


def test_cmd_check_missing_required_vars(mock_state, capsys, mock_spinner):
    mock_state.get_variable.return_value = None
    mock_state.validate_required_vars.return_value = (["URL", "SELECTOR"], [])

    cmd_check([], mock_state)
    captured = capsys.readouterr()

    # Spinner should not have been called
    mock_spinner.start.assert_not_called()


def test_cmd_check_given_data_retrieval_error(mock_state, capsys, mock_spinner):
    mock_state.get_variable.return_value = "http://example.com"
    mock_state.get_variable.side_effect = lambda x: (
        "invalid_selector" if x == "SELECTOR" else "false"
    )

    with patch(
        "commands.retrieve_page_data",
        side_effect=Exception("Data retrieval error test"),
    ):
        cmd_check([], mock_state)

    captured = capsys.readouterr()

    # error thrown + spinner started and stopped + current_page_data not set
    assert "Data retrieval error test" in captured.out
    mock_spinner.start.assert_called_once()
    mock_spinner.stop.assert_called_once()
    assert mock_state.current_page_data is None


def test_cmd_check_valid_data_retrieval(
    monkeypatch, mock_state, capsys, mock_spinner, mock_cache_page_data
):
    mock_state.get_variable.return_value = "http://example.com"
    mock_state.get_variable.side_effect = lambda x: (
        "#main" if x == "SELECTOR" else "false"
    )

    # monkeypatch.setattr("commands.retrieve_page_data", lambda *args, **kwargs: {})

    with patch("commands.retrieve_page_data", return_value={"key": "value"}):
        cmd_check([], mock_state)

    captured = capsys.readouterr()

    # Spinner should have started and stopped
    mock_spinner.start.assert_called_once()
    mock_spinner.stop.assert_called_once()
    assert "💡 Use 'show page' to see detailed results" in captured.out
    assert mock_state.current_page_data == {"key": "value"}


def test_cmd_debug(mock_state):
    """Test the cmd_debug function."""
    cmd_debug([], mock_state)
    mock_state.list_variables.assert_called_once()


def test_cmd_help(mock_state):
    """Test the cmd_help function."""
    cmd_help([], mock_state)
    mock_state.list_variables.assert_called_once()


def test_cmd_links(mock_state):
    """Test the cmd_links function."""
    cmd_links([], mock_state)
    mock_state.list_variables.assert_called_once()


def test_cmd_lookup(mock_state):
    """Test the cmd_lookup function."""
    cmd_lookup(["var_name"], mock_state)
    mock_state.list_variables.assert_called_once()


def test_cmd_load(mock_state):
    """Test the cmd_load function."""
    cmd_load(["file.xlsx"], mock_state)
    mock_state.list_variables.assert_called_once()


def test_cmd_migrate(mock_state):
    """Test the cmd_migrate function."""
    cmd_migrate(["source", "target"], mock_state)
    mock_state.list_variables.assert_called_once()


def test_cmd_set_incomplete_args(mock_state):
    """Test the cmd_set function with incomplete arguments."""
    cmd_set("", mock_state)
    print_help_for_command.assert_called_once()


def test__get_var_description(mock_state):
    """Test the _get_var_description function."""
    _get_var_description("var_name", mock_state)
    mock_state.list_variables.assert_called_once()


def test_cmd_report_no_args_no_data(mock_state, mock_spinner, capsys):
    """Test cmd_report with no args and no current page data."""
    mock_state.current_page_data = None
    mock_state.get_variable.return_value = None
    mock_state.validate_required_vars.return_value = (["URL", "SELECTOR"], [])

    cmd_report([], mock_state)
    captured = capsys.readouterr()

    assert "Running 'check' to gather page data..." in captured.out
    assert "Failed to gather page data. Cannot generate report." in captured.out


def test_cmd_report_with_data(mock_state, mock_cache_page_data, monkeypatch, capsys):
    """Test cmd_report with existing page data."""
    mock_state.current_page_data = {"key": "value", "links": [], "pdfs": []}
    mock_state.get_variable.side_effect = lambda x: {
        "DOMAIN": "Enterprise",
        "ROW": "90",
        "URL": "http://example.com",
        "PROPOSED_PATH": "/test/path"
    }.get(x, "")

    # Mock file writing
    mock_open = MagicMock()
    mock_file = MagicMock()
    mock_open.return_value.__enter__ = MagicMock(return_value=mock_file)
    mock_open.return_value.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr("builtins.open", mock_open)

    cmd_report([], mock_state)
    captured = capsys.readouterr()

    assert "Generating report: enterprise_90.html" in captured.out
    assert "Report saved to: enterprise_90.html" in captured.out
    mock_open.assert_called_once_with("enterprise_90.html", 'w', encoding='utf-8')


def test_cmd_report_file_write_error(mock_state, mock_cache_page_data, monkeypatch, capsys):
    """Test cmd_report when file writing fails."""
    mock_state.current_page_data = {"key": "value", "links": [], "pdfs": []}
    mock_state.get_variable.side_effect = lambda x: {
        "DOMAIN": "Enterprise",
        "ROW": "90",
        "URL": "http://example.com",
        "PROPOSED_PATH": "/test/path"
    }.get(x, "")

    # Mock file writing to raise an exception
    def mock_open_side_effect(*args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open_side_effect)

    cmd_report([], mock_state)
    captured = capsys.readouterr()

    assert "Failed to save report: Permission denied" in captured.out
