import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# ensure commands module is importable from repo root
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

import commands


@pytest.fixture
def mock_state():
    state = MagicMock()
    state.get_variable = MagicMock(return_value=None)
    state.set_variable = MagicMock()
    return state


# ----- cmd_sidebar tests -----

def test_cmd_sidebar_toggle_on(mock_state, capsys):
    mock_state.get_variable.return_value = False
    commands.cmd_sidebar([], mock_state)
    mock_state.set_variable.assert_called_once_with("INCLUDE_SIDEBAR", "true")
    assert "Sidebar inclusion: ON" in capsys.readouterr().out


def test_cmd_sidebar_set_off(mock_state, capsys):
    mock_state.get_variable.return_value = True
    commands.cmd_sidebar(["off"], mock_state)
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
    commands.cmd_clear([])
    call.assert_called_once_with("clear")
