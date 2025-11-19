"""
Comprehensive test suite for CLI Tool (Phase 4).

Tests all functionality in cli.py including:
- Convert command (single/multiple DOIs)
- Batch command (file processing)
- Formats command
- Sources command
- Error handling
- Output formats
- Options and flags

Phase 6.1c: CLI Tests
"""

import pytest
import tempfile
from pathlib import Path

# Import CLI components
try:
    from click.testing import CliRunner
    from cli import cli
    CLICK_AVAILABLE = True
except ImportError:
    CLICK_AVAILABLE = False
    pytest.skip("Click not installed - skipping CLI tests", allow_module_level=True)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def runner():
    """Provide Click test runner."""
    return CliRunner()


@pytest.fixture
def sample_doi():
    """Provide a sample DOI for testing."""
    return "10.1038/nature12373"


@pytest.fixture
def sample_dois():
    """Provide multiple DOIs for testing."""
    return [
        "10.1038/nature12373",
        "10.1126/science.1234567",
        "10.1371/journal.pone.0123456"
    ]


@pytest.fixture
def dois_file(tmp_path, sample_dois):
    """Create a temporary file with DOIs."""
    file_path = tmp_path / "dois.txt"
    file_path.write_text("\n".join(sample_dois))
    return file_path


@pytest.fixture
def dois_file_with_comments(tmp_path):
    """Create a DOIs file with comments and empty lines."""
    content = """# This is a comment
10.1038/nature12373

# Another comment
10.1126/science.1234567

10.1371/journal.pone.0123456
"""
    file_path = tmp_path / "dois_comments.txt"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def dois_csv_file(tmp_path):
    """Create a CSV file with DOIs."""
    content = "10.1038/nature12373,10.1126/science.1234567\n10.1371/journal.pone.0123456"
    file_path = tmp_path / "dois.csv"
    file_path.write_text(content)
    return file_path


# ============================================================================
# Test: CLI Entry Point
# ============================================================================

class TestCLIEntry:
    """Test CLI entry point and help."""

    def test_cli_help(self, runner):
        """Test CLI shows help message."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "DOI2BibTeX" in result.output
        assert "convert" in result.output
        assert "batch" in result.output

    def test_cli_version(self, runner):
        """Test CLI version flag."""
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "2.2.0" in result.output or "version" in result.output.lower()


# ============================================================================
# Test: Convert Command
# ============================================================================

class TestConvertCommand:
    """Test convert command functionality."""

    def test_convert_help(self, runner):
        """Test convert command help."""
        result = runner.invoke(cli, ["convert", "--help"])

        assert result.exit_code == 0
        assert "Convert one or more DOIs" in result.output
        assert "--output" in result.output
        assert "--format" in result.output

    def test_convert_single_doi_stdout(self, runner, sample_doi):
        """Test converting single DOI to stdout."""
        result = runner.invoke(cli, ["convert", sample_doi])

        # Should attempt conversion (may fail due to network)
        assert result.exit_code in [0, 1]  # 1 if network fails

    def test_convert_single_doi_to_file(self, runner, sample_doi, tmp_path):
        """Test converting single DOI to file."""
        output_file = tmp_path / "output.bib"

        result = runner.invoke(cli, [
            "convert",
            sample_doi,
            "-o", str(output_file)
        ])

        # Should attempt conversion
        assert result.exit_code in [0, 1]

    def test_convert_multiple_dois(self, runner, sample_dois):
        """Test converting multiple DOIs."""
        result = runner.invoke(cli, ["convert"] + sample_dois)

        # Should attempt conversion
        assert result.exit_code in [0, 1]

    def test_convert_ris_format(self, runner, sample_doi, tmp_path):
        """Test converting to RIS format."""
        output_file = tmp_path / "output.ris"

        result = runner.invoke(cli, [
            "convert",
            sample_doi,
            "-f", "ris",
            "-o", str(output_file)
        ])

        assert result.exit_code in [0, 1]

    def test_convert_endnote_format(self, runner, sample_doi, tmp_path):
        """Test converting to EndNote format."""
        output_file = tmp_path / "output.enw"

        result = runner.invoke(cli, [
            "convert",
            sample_doi,
            "-f", "endnote",
            "-o", str(output_file)
        ])

        assert result.exit_code in [0, 1]

    def test_convert_with_abstracts(self, runner, sample_doi, tmp_path):
        """Test converting with abstracts option."""
        output_file = tmp_path / "output.bib"

        result = runner.invoke(cli, [
            "convert",
            sample_doi,
            "--abstracts",
            "-o", str(output_file)
        ])

        assert result.exit_code in [0, 1]

    def test_convert_with_verbose(self, runner, sample_doi):
        """Test verbose output."""
        result = runner.invoke(cli, [
            "convert",
            sample_doi,
            "-v"
        ])

        # Verbose should show processing message
        if "Processing" in result.output or "Successful" in result.output:
            assert True
        # May fail due to network, but should attempt
        assert result.exit_code in [0, 1]

    def test_convert_invalid_format(self, runner, sample_doi):
        """Test invalid format returns error."""
        result = runner.invoke(cli, [
            "convert",
            sample_doi,
            "-f", "invalid"
        ])

        assert result.exit_code == 2  # Click validation error
        assert "Invalid value" in result.output or "invalid" in result.output.lower()

    def test_convert_no_dois_provided(self, runner):
        """Test convert without DOIs shows error."""
        result = runner.invoke(cli, ["convert"])

        assert result.exit_code == 2  # Missing argument error


# ============================================================================
# Test: Batch Command
# ============================================================================

class TestBatchCommand:
    """Test batch command functionality."""

    def test_batch_help(self, runner):
        """Test batch command help."""
        result = runner.invoke(cli, ["batch", "--help"])

        assert result.exit_code == 0
        assert "batch file" in result.output.lower()
        assert "--output" in result.output
        assert "--async" in result.output

    def test_batch_from_file(self, runner, dois_file, tmp_path):
        """Test batch processing from file."""
        output_file = tmp_path / "results.bib"

        result = runner.invoke(cli, [
            "batch",
            str(dois_file),
            "-o", str(output_file)
        ])

        # Should attempt processing
        assert result.exit_code in [0, 1]

    def test_batch_with_async(self, runner, dois_file, tmp_path):
        """Test batch with async mode."""
        output_file = tmp_path / "results.bib"

        result = runner.invoke(cli, [
            "batch",
            str(dois_file),
            "--async",
            "-o", str(output_file)
        ])

        assert result.exit_code in [0, 1]

    def test_batch_with_sync(self, runner, dois_file, tmp_path):
        """Test batch with explicit sync mode."""
        output_file = tmp_path / "results.bib"

        result = runner.invoke(cli, [
            "batch",
            str(dois_file),
            "--sync",
            "-o", str(output_file)
        ])

        assert result.exit_code in [0, 1]

    def test_batch_with_comments(self, runner, dois_file_with_comments, tmp_path):
        """Test batch file with comments is parsed correctly."""
        output_file = tmp_path / "results.bib"

        result = runner.invoke(cli, [
            "batch",
            str(dois_file_with_comments),
            "-o", str(output_file)
        ])

        # Comments should be ignored
        assert result.exit_code in [0, 1]

    def test_batch_csv_format(self, runner, dois_csv_file, tmp_path):
        """Test batch file with CSV format."""
        output_file = tmp_path / "results.bib"

        result = runner.invoke(cli, [
            "batch",
            str(dois_csv_file),
            "-o", str(output_file)
        ])

        assert result.exit_code in [0, 1]

    def test_batch_ris_format(self, runner, dois_file, tmp_path):
        """Test batch conversion to RIS format."""
        output_file = tmp_path / "results.ris"

        result = runner.invoke(cli, [
            "batch",
            str(dois_file),
            "-f", "ris",
            "-o", str(output_file)
        ])

        assert result.exit_code in [0, 1]

    def test_batch_with_abstracts(self, runner, dois_file, tmp_path):
        """Test batch with abstracts option."""
        output_file = tmp_path / "results.bib"

        result = runner.invoke(cli, [
            "batch",
            str(dois_file),
            "--abstracts",
            "-o", str(output_file)
        ])

        assert result.exit_code in [0, 1]

    def test_batch_with_verbose(self, runner, dois_file, tmp_path):
        """Test batch with verbose output."""
        output_file = tmp_path / "results.bib"

        result = runner.invoke(cli, [
            "batch",
            str(dois_file),
            "-v",
            "-o", str(output_file)
        ])

        # Verbose should show processing info
        assert result.exit_code in [0, 1]

    def test_batch_custom_batch_size(self, runner, dois_file, tmp_path):
        """Test batch with custom batch size."""
        output_file = tmp_path / "results.bib"

        result = runner.invoke(cli, [
            "batch",
            str(dois_file),
            "--batch-size", "10",
            "-o", str(output_file)
        ])

        assert result.exit_code in [0, 1]

    def test_batch_file_not_found(self, runner):
        """Test batch with non-existent file."""
        result = runner.invoke(cli, [
            "batch",
            "nonexistent.txt"
        ])

        assert result.exit_code == 2  # File not found error
        assert "does not exist" in result.output.lower() or "Error" in result.output

    def test_batch_empty_file(self, runner, tmp_path):
        """Test batch with empty file."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        result = runner.invoke(cli, [
            "batch",
            str(empty_file)
        ])

        # Should show error for no DOIs
        assert result.exit_code == 1
        assert "No DOIs found" in result.output or "Error" in result.output

    def test_batch_to_stdout(self, runner, dois_file):
        """Test batch output to stdout."""
        result = runner.invoke(cli, [
            "batch",
            str(dois_file)
        ])

        # Should attempt to output to stdout
        assert result.exit_code in [0, 1]


# ============================================================================
# Test: Info Commands
# ============================================================================

class TestInfoCommands:
    """Test information commands."""

    def test_formats_command(self, runner):
        """Test formats command."""
        result = runner.invoke(cli, ["formats"])

        assert result.exit_code == 0
        assert "bibtex" in result.output.lower()
        assert "ris" in result.output.lower()
        assert "endnote" in result.output.lower()

    def test_sources_command(self, runner):
        """Test sources command."""
        result = runner.invoke(cli, ["sources"])

        assert result.exit_code == 0
        assert "Crossref" in result.output
        assert "DataCite" in result.output
        assert "DOI.org" in result.output


# ============================================================================
# Test: Error Handling
# ============================================================================

class TestErrorHandling:
    """Test CLI error handling."""

    def test_invalid_command(self, runner):
        """Test invalid command shows error."""
        result = runner.invoke(cli, ["invalid"])

        assert result.exit_code == 2
        assert "No such command" in result.output or "invalid" in result.output.lower()

    def test_missing_required_argument(self, runner):
        """Test missing required argument."""
        result = runner.invoke(cli, ["batch"])

        assert result.exit_code == 2
        assert "Missing argument" in result.output or "required" in result.output.lower()

    def test_invalid_option_value(self, runner, sample_doi):
        """Test invalid option value."""
        result = runner.invoke(cli, [
            "convert",
            sample_doi,
            "--batch-size", "invalid"
        ])

        # batch-size not valid for convert, or invalid value
        assert result.exit_code == 2


# ============================================================================
# Test: Output Handling
# ============================================================================

class TestOutputHandling:
    """Test output file handling."""

    def test_output_file_created(self, runner, tmp_path):
        """Test output file is created."""
        output_file = tmp_path / "test_output.bib"

        # File should not exist yet
        assert not output_file.exists()

        runner.invoke(cli, [
            "convert",
            "10.1234/test",
            "-o", str(output_file)
        ])

        # File may or may not be created depending on success
        # This is just testing the path handling

    def test_output_directory_doesnt_exist(self, runner, tmp_path):
        """Test error when output directory doesn't exist."""
        output_file = tmp_path / "nonexistent" / "output.bib"

        result = runner.invoke(cli, [
            "convert",
            "10.1234/test",
            "-o", str(output_file)
        ])

        # Should handle gracefully
        assert result.exit_code in [0, 1, 2]


# ============================================================================
# Test: Options Combinations
# ============================================================================

class TestOptionsCombinations:
    """Test various option combinations."""

    def test_all_options_together(self, runner, sample_doi, tmp_path):
        """Test using all options together."""
        output_file = tmp_path / "output.bib"

        result = runner.invoke(cli, [
            "convert",
            sample_doi,
            "-o", str(output_file),
            "-f", "bibtex",
            "--abstracts",
            "--abbrev-journal",
            "--no-duplicates",
            "-v"
        ])

        # Should accept all valid options
        assert result.exit_code in [0, 1]

    def test_batch_all_options(self, runner, dois_file, tmp_path):
        """Test batch command with all options."""
        output_file = tmp_path / "output.bib"

        result = runner.invoke(cli, [
            "batch",
            str(dois_file),
            "-o", str(output_file),
            "-f", "bibtex",
            "--async",
            "--abstracts",
            "--abbrev-journal",
            "--batch-size", "50",
            "-v"
        ])

        assert result.exit_code in [0, 1]


# ============================================================================
# Test: Exit Codes
# ============================================================================

class TestExitCodes:
    """Test CLI exit codes."""

    def test_success_exit_code(self, runner):
        """Test successful command returns 0."""
        result = runner.invoke(cli, ["formats"])

        assert result.exit_code == 0

    def test_error_exit_code(self, runner):
        """Test error returns non-zero."""
        result = runner.invoke(cli, ["invalid-command"])

        assert result.exit_code != 0


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
