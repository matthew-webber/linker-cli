import pytest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from commands import *


@pytest.fixture
def mock_state():
    """Fixture to create a mock state object."""
    state = MagicMock()
    state.list_variables = MagicMock()
    state.excel_data = None
    state.current_page_data = None
    return state


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


def test_cmd_check(mock_state):
    """Test the cmd_check function."""
    cmd_check(["arg1", "arg2"], mock_state)
    mock_state.list_variables.assert_called_once()


def test_cmd_clear(mock_state):
    """Test the cmd_clear function."""
    cmd_clear([], mock_state)
    mock_state.list_variables.assert_called_once()


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
    _get_var_description("var_name", mock_state)
    mock_state.list_variables.assert_called_once()


def test__get_var_description(mock_state):
    """Test the _get_var_description function."""
    _get_var_description("var_name", mock_state)
    mock_state.list_variables.assert_called_once()
