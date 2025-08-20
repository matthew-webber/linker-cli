import json
from commands.report import (
    _build_sitecore_nav_js,
    _format_display_url,
    _generate_consolidated_section,
)
from state import CLIState
from unittest.mock import patch

"""
Core Functionality Tests:
    Empty path handling - Returns empty string for empty input
    Single and multiple path elements - Proper IIFE generation
    Special characters - JSON escaping of quotes, newlines, etc.
    Unicode characters - Proper handling of international characters
IIFE Syntax Validation Tests:
    Valid IIFE structure - Starts with (async () => { and ends with })();
    Balanced braces/parentheses - No syntax errors from unmatched brackets
    Proper semicolon usage - Critical statements are properly terminated
    No unescaped line breaks - Ensures no literal newlines break JS syntax
JavaScript Structure Tests:
    Template completeness - All required functions and logic present
    Error handling - Try-catch blocks and proper error logging
    Debug logging - Debug levels and conditional logging
    DOM traversal logic - Query selectors and event handling
    Async/await patterns - Proper promise handling
Edge Cases:
    Deeply nested paths - Long arrays don't break the function
    Empty strings - Handles edge cases gracefully
    Path validation - Includes client-side validation logic
"""


class TestBuildSitecoreNavJs:
    """Tests for the _build_sitecore_nav_js function."""

    def test_empty_path_returns_empty_string(self):
        """Test that an empty path returns an empty string."""
        result = _build_sitecore_nav_js([])
        assert result == ""

    def test_single_path_element(self):
        """Test JavaScript generation with a single path element."""
        path = ["Sites"]
        result = _build_sitecore_nav_js(path)

        # Verify it's not empty
        assert result != ""

        # Verify it starts and ends as an IIFE
        assert result.startswith("(async () => {")
        assert result.endswith("})();")

        # Verify the path is properly JSON encoded
        expected_json = json.dumps(path)
        assert f"const path = {expected_json}" in result

    def test_multiple_path_elements(self):
        """Test JavaScript generation with multiple path elements."""
        path = ["Sites", "Enterprise", "Page Name"]
        result = _build_sitecore_nav_js(path)

        # Verify IIFE structure
        assert result.startswith("(async () => {")
        assert result.endswith("})();")

        # Verify the path array is correctly embedded
        expected_json = json.dumps(path)
        assert f"const path = {expected_json}" in result

        # Verify key JavaScript components exist
        assert "const finalName = path[path.length - 1];" in result
        assert "const expandNames = path.slice(0, -1);" in result
        assert "async function expand(" in result
        assert "async function clickNode(" in result

    def test_path_with_special_characters(self):
        """Test that paths with special characters are properly JSON escaped."""
        path = [
            "Sites",
            'Page with "quotes"',
            "Page with 'apostrophes'",
            "Page with\nnewlines",
        ]
        result = _build_sitecore_nav_js(path)

        # Verify IIFE structure
        assert result.startswith("(async () => {")
        assert result.endswith("})();")

        # Verify JSON encoding handles special characters correctly
        expected_json = json.dumps(path)
        assert f"const path = {expected_json}" in result

        # Verify no unescaped quotes break the JavaScript
        lines = result.split("\n")
        path_line = next(line for line in lines if "const path =" in line)
        assert '\\"quotes\\"' in path_line  # Should be properly escaped in JSON
        assert "'apostrophes'" in path_line

    def test_no_unescaped_line_breaks(self):
        """Test that the generated JavaScript has no unescaped line breaks that would break syntax."""
        path = ["Sites", "Multi\nLine\nPath", "Another\rCarriage\rReturn"]
        result = _build_sitecore_nav_js(path)

        # The JSON encoding should escape the newlines and carriage returns
        expected_json = json.dumps(path)
        assert f"const path = {expected_json}" in result

        # Verify that the problematic characters are escaped in the JSON
        assert "Multi\\nLine\\nPath" in result
        assert "Another\\rCarriage\\rReturn" in result

    def test_javascript_structure_completeness(self):
        """Test that all required JavaScript functions and logic are present."""
        path = ["Sites", "Test"]
        result = _build_sitecore_nav_js(path)

        # Check for required variable declarations
        assert "myDebug = 3;" in result
        assert "myDebugLevels = {" in result
        assert "DEBUG: 1," in result
        assert "INFO: 2," in result
        assert "WARN: 3," in result

        # Check for required functions
        assert "const sanitizeName = (name) =>" in result
        assert "const findNode = (name, searchRoot = document) =>" in result
        assert (
            "function waitForMatch(name, searchRoot = document, timeout = 5000)"
            in result
        )
        assert "async function expand(name, searchRoot = document)" in result
        assert "async function clickNode(name, searchRoot = document)" in result

        # Check for main execution logic
        assert "let currentSearchRoot = document;" in result
        assert "for (const name of expandNames)" in result
        assert "await clickNode(finalName, currentSearchRoot);" in result
        assert "} catch (e) {" in result
        assert "console.error(e);" in result

    def test_path_validation_logic_included(self):
        """Test that path validation logic is included in the generated JavaScript."""
        path = ["Sites", "Test"]
        result = _build_sitecore_nav_js(path)

        # Check for path validation
        assert "if (path.length === 0) {" in result
        assert "console.error('empty path');" in result
        assert "if (path.some((name) => !name || typeof name !== 'string'))" in result
        assert "console.error('invalid path', path);" in result

    def test_sanitization_logic_included(self):
        """Test that name sanitization logic is included."""
        path = ["Sites", "Test-Page_Name"]
        result = _build_sitecore_nav_js(path)

        # Check for sanitization function
        assert "name.toLowerCase().replace(/[-_]/g, ' ').trim();" in result

    def test_valid_iife_syntax(self):
        """Test that the returned JavaScript is a syntactically valid IIFE."""
        path = ["Sites", "Enterprise", "Test Page"]
        result = _build_sitecore_nav_js(path)

        # Must start with IIFE opening
        assert result.startswith("(async () => {")

        # Must end with IIFE closing and execution
        assert result.endswith("})();")

        # Should not have any unmatched braces or syntax errors
        # Count opening and closing braces to ensure they match
        opening_braces = result.count("{")
        closing_braces = result.count("}")
        assert opening_braces == closing_braces

        # Verify async arrow function syntax
        assert "(async () => {" in result

    def test_unicode_characters_handled(self):
        """Test that Unicode characters in paths are properly handled."""
        path = ["Sites", "Página con acentos", "页面中文", "🏠 Home"]
        result = _build_sitecore_nav_js(path)

        # Verify IIFE structure
        assert result.startswith("(async () => {")
        assert result.endswith("})();")

        # Verify JSON encoding (default json.dumps uses ASCII encoding)
        expected_json = json.dumps(path)  # This will escape Unicode by default
        assert f"const path = {expected_json}" in result

    def test_no_literal_newlines_in_output(self):
        """Test that the output contains no literal unescaped newlines that would break JS syntax."""
        path = ["Sites", "Test\nWith\nNewlines", "Another line"]
        result = _build_sitecore_nav_js(path)

        # Split by actual newlines in the template (which are intentional)
        lines = result.split("\n")

        # Find the line with the path declaration
        path_line = next((line for line in lines if "const path =" in line), None)
        assert path_line is not None

        # The path line should contain escaped newlines, not literal ones
        # JSON.dumps should have escaped the \n characters as \\n
        assert "Test\\nWith\\nNewlines" in path_line
        # Should not contain unescaped newlines that would break JS
        assert "\nWith\n" not in path_line

    def test_javascript_template_completeness(self):
        """Test that the JavaScript template includes all necessary DOM traversal logic."""
        path = ["Sites", "Test"]
        result = _build_sitecore_nav_js(path)

        # Verify DOM query selectors are present
        assert ".scContentTreeNode" in result
        assert "querySelectorAll" in result
        assert "querySelector" in result

        # Verify event handling
        assert "arrow.click();" in result
        assert "span.click();" in result

        # Verify async/await patterns
        assert "await waitForMatch" in result
        assert "await expand" in result
        assert "await clickNode" in result

        # Verify promise handling
        assert "new Promise" in result
        assert "setTimeout" in result

    def test_error_handling_included(self):
        """Test that proper error handling is included in the generated JavaScript."""
        path = ["Sites", "Test"]
        result = _build_sitecore_nav_js(path)

        # Check for try-catch block
        assert "try {" in result
        assert "} catch (e) {" in result
        assert "console.error(e);" in result

        # Check for specific error conditions
        assert "console.error('empty path');" in result
        assert "console.error('invalid path', path);" in result
        assert "console.warn('no span for'" in result
        assert "console.warn('no expand arrow for'" in result
        assert "reject(new Error('Timeout waiting for '" in result

    def test_debug_logging_levels(self):
        """Test that debug logging with different levels is properly configured."""
        path = ["Sites", "Test"]
        result = _build_sitecore_nav_js(path)

        # Check debug level configuration
        assert "myDebug = 3;" in result
        assert "myDebugLevels = {" in result
        assert "DEBUG: 1," in result
        assert "INFO: 2," in result
        assert "WARN: 3," in result

        # Check conditional logging
        assert "if (myDebug < myDebugLevels.INFO)" in result
        assert "if (myDebug < myDebugLevels.WARN)" in result

    def test_iife_returns_promise(self):
        """Test that the IIFE structure properly handles async execution."""
        path = ["Sites", "Test"]
        result = _build_sitecore_nav_js(path)

        # Should be an async IIFE that can handle promises
        assert result.startswith("(async () => {")
        assert result.endswith("})();")

        # Should contain async/await patterns
        await_count = result.count("await ")
        assert await_count >= 3  # At least expand calls and final clickNode

        # Should have proper async function declarations
        assert "async function expand(" in result
        assert "async function clickNode(" in result

    def test_empty_string_vs_none_input(self):
        """Test edge cases with empty strings and None-like inputs."""
        # Empty list should return empty string
        assert _build_sitecore_nav_js([]) == ""

        # List with empty strings should still generate JS (though it may fail at runtime)
        result = _build_sitecore_nav_js([""])
        assert result.startswith("(async () => {")
        assert result.endswith("})();")
        assert 'const path = [""]' in result

    def test_deeply_nested_path(self):
        """Test with a deeply nested path to ensure no issues with long arrays."""
        path = ["Sites", "Level1", "Level2", "Level3", "Level4", "Level5", "FinalPage"]
        result = _build_sitecore_nav_js(path)

        # Verify structure
        assert result.startswith("(async () => {")
        assert result.endswith("})();")

        # Verify all path elements are present in JSON
        expected_json = json.dumps(path)
        assert f"const path = {expected_json}" in result

        # Should still contain all the required functions
        assert "async function expand(" in result
        assert "async function clickNode(" in result

    def test_iife_syntax_validation_comprehensive(self):
        """Comprehensive test to ensure the IIFE has completely valid JavaScript syntax."""
        path = ["Sites", "Test Page", "Sub Page"]
        result = _build_sitecore_nav_js(path)

        # Must be a proper IIFE
        assert result.startswith("(async () => {")
        assert result.endswith("})();")

        # No unescaped newlines that would break JS string literals
        # (newlines in the template are intentional for readability)
        lines = result.split("\n")
        for i, line in enumerate(lines):
            # Check that any string literals don't contain unescaped newlines
            if "const path =" in line:
                # This line contains the JSON array - it should not have literal newlines
                assert "\n" not in line.split("const path =")[1].split(";")[0]

        # Verify balanced braces and parentheses
        assert result.count("{") == result.count("}")
        assert result.count("(") == result.count(")")
        assert result.count("[") == result.count("]")

        # Verify proper semicolon usage in key statements
        assert "myDebug = 3;" in result
        assert "return;" in result  # Early returns should have semicolons

        # Verify no syntax-breaking characters in critical areas
        critical_statements = [
            "const path = ",
            "const finalName = ",
            "const expandNames = ",
        ]

        for stmt in critical_statements:
            assert stmt in result
            # Find the line and ensure it's properly terminated
            stmt_line = next(line for line in lines if stmt in line)
            assert stmt_line.strip().endswith(";")


class TestFormatDisplayUrl:
    """Tests for the _format_display_url helper."""

    def test_truncates_and_preserves_ends(self):
        long_url = "https://example.com/" + "a" * 80 + "/file"
        formatted = _format_display_url(long_url, max_length=60)
        assert formatted.startswith("https://example.com/")
        assert formatted.endswith("/file")
        assert "..." in formatted
        assert len(formatted) <= 60


class TestGenerateConsolidatedSection:
    """Tests for consolidated section generation."""

    def test_internal_hierarchy_only_for_internal_pages(self):
        state = CLIState()
        state.set_variable("URL", "https://musckids.org/page")
        state.current_page_data = {
            "links": [
                ("Internal", "https://musckids.org/page", 200),
                ("Phone", "tel:1234567890", 0),
                ("Email", "mailto:test@example.com", 0),
            ],
            "pdfs": [("PDF", "https://musckids.org/doc.pdf", 200)],
        }

        with patch(
            "utils.sitecore.get_current_sitecore_root", return_value="Root"
        ), patch(
            "utils.sitecore.get_proposed_sitecore_root", return_value="Root"
        ), patch(
            "data.dsm.lookup_link_in_dsm",
            return_value={"proposed_hierarchy": {"segments": ["Page"], "root": "Root"}},
        ):
            html = _generate_consolidated_section(state)

        # Only the internal page link should have hierarchy information
        assert html.count("internal-hierarchy") == 1

        # All items should display their URL strings
        assert html.count('class="link-url"') == 4
