"""
Command-Line Interface for DOI2BibTeX application.

This module provides a Click-based CLI for DOI conversion, enabling:
- Single DOI conversion
- Batch file processing
- Multiple output formats
- Async/sync processing modes
- Pipeline-friendly design

Phase 4.3 Implementation

Usage:
    # Convert single DOI
    python cli.py convert 10.1038/nature12373

    # Convert with output file
    python cli.py convert 10.1038/nature12373 -o output.bib

    # Batch process file
    python cli.py batch dois.txt -o results.bib

    # Use async mode for large batches
    python cli.py batch dois.txt --async -o results.bib

    # Different output format
    python cli.py convert 10.1038/nature12373 -f ris -o output.ris
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

try:
    import click
except ImportError:
    print("Click not installed. Install with: pip install 'doi2bibtex[phase4]'")
    sys.exit(1)

from core.processor import DOIProcessor
from core.config import AppConfig
from core.export import export_to_ris, export_to_endnote
from core.exceptions import DOIError


# ============================================================================
# CLI Group
# ============================================================================


@click.group()
@click.version_option(version="2.2.0", prog_name="doi2bibtex")
@click.pass_context
def cli(ctx):
    """
    DOI2BibTeX - Convert DOIs to bibliography formats.

    Enterprise-grade DOI to BibTeX converter with multi-source fallback,
    advanced caching, and professional error handling.

    Examples:

        \b
        # Convert single DOI to BibTeX
        $ doi2bibtex convert 10.1038/nature12373

        \b
        # Convert with output file
        $ doi2bibtex convert 10.1038/nature12373 -o output.bib

        \b
        # Batch process file
        $ doi2bibtex batch dois.txt -o results.bib

        \b
        # Use async mode for better performance
        $ doi2bibtex batch dois.txt --async -o results.bib

        \b
        # Convert to RIS format
        $ doi2bibtex convert 10.1038/nature12373 -f ris -o output.ris
    """
    ctx.ensure_object(dict)


# ============================================================================
# Convert Command (Single/Multiple DOIs)
# ============================================================================


@cli.command()
@click.argument("dois", nargs=-1, required=True)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, writable=True),
    help="Output file path. If not specified, prints to stdout.",
)
@click.option(
    "-f",
    "--format",
    type=click.Choice(["bibtex", "ris", "endnote"], case_sensitive=False),
    default="bibtex",
    help="Output format (default: bibtex)",
)
@click.option(
    "--async/--sync",
    "use_async",
    default=False,
    help="Use async processing for better performance (requires aiohttp)",
)
@click.option(
    "--abstracts/--no-abstracts",
    "fetch_abstracts",
    default=False,
    help="Include abstracts in output",
)
@click.option(
    "--abbrev-journal/--full-journal",
    "use_abbrev_journal",
    default=False,
    help="Use journal abbreviations",
)
@click.option(
    "--no-duplicates/--allow-duplicates",
    "remove_duplicates",
    default=True,
    help="Remove duplicate DOIs",
)
@click.option(
    "-v", "--verbose", is_flag=True, help="Enable verbose output"
)
def convert(
    dois: tuple,
    output: Optional[str],
    format: str,
    use_async: bool,
    fetch_abstracts: bool,
    use_abbrev_journal: bool,
    remove_duplicates: bool,
    verbose: bool,
):
    """
    Convert one or more DOIs to bibliography format.

    DOIS: One or more DOI identifiers to convert.

    Examples:

        \b
        # Single DOI
        $ doi2bibtex convert 10.1038/nature12373

        \b
        # Multiple DOIs
        $ doi2bibtex convert 10.1038/nature12373 10.1126/science.1234567

        \b
        # With output file
        $ doi2bibtex convert 10.1038/nature12373 -o output.bib

        \b
        # RIS format
        $ doi2bibtex convert 10.1038/nature12373 -f ris -o output.ris
    """
    try:
        # Create configuration
        config = AppConfig(
            fetch_abstracts=fetch_abstracts,
            use_abbrev_journal=use_abbrev_journal,
            remove_duplicates=remove_duplicates,
        )

        # Initialize processor
        processor = DOIProcessor(config)

        # Convert DOIs list
        doi_list = list(dois)

        if verbose:
            click.echo(f"Processing {len(doi_list)} DOI(s)...")

        # Process DOIs
        if use_async and len(doi_list) > 1:
            # Use async processing for multiple DOIs
            try:
                import asyncio
                from core.async_processor import process_dois_async

                result = asyncio.run(process_dois_async(config, doi_list))
            except ImportError:
                click.echo(
                    "Warning: aiohttp not installed. Falling back to sync processing.",
                    err=True,
                )
                result = processor.process_batch(doi_list)
        else:
            # Sync processing
            result = processor.process_batch(doi_list)

        if verbose:
            click.echo(
                f"✓ Successful: {result.successful_count}, "
                f"✗ Failed: {result.failed_count}"
            )

        # Convert to requested format
        if format.lower() == "bibtex":
            output_text = "\n\n".join(entry.bibtex for entry in result.entries if entry.bibtex)
        elif format.lower() == "ris":
            output_text = export_to_ris(result.entries)
        elif format.lower() == "endnote":
            output_text = export_to_endnote(result.entries)
        else:
            raise click.BadParameter(f"Unknown format: {format}")

        # Output results
        if output:
            output_path = Path(output)
            output_path.write_text(output_text, encoding="utf-8")
            click.echo(f"✓ Results written to {output_path}")
        else:
            click.echo(output_text)

        # Report failures
        if result.failed_count > 0:
            click.echo(
                f"\n⚠ Warning: {result.failed_count} DOI(s) failed:", err=True
            )
            for doi in result.failed_dois:
                click.echo(f"  - {doi}", err=True)
            sys.exit(1)

    except DOIError as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


# ============================================================================
# Batch Command (File Processing)
# ============================================================================


@cli.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, writable=True),
    help="Output file path. If not specified, prints to stdout.",
)
@click.option(
    "-f",
    "--format",
    type=click.Choice(["bibtex", "ris", "endnote"], case_sensitive=False),
    default="bibtex",
    help="Output format (default: bibtex)",
)
@click.option(
    "--async/--sync",
    "use_async",
    default=False,
    help="Use async processing for better performance",
)
@click.option(
    "--abstracts/--no-abstracts",
    "fetch_abstracts",
    default=False,
    help="Include abstracts in output",
)
@click.option(
    "--abbrev-journal/--full-journal",
    "use_abbrev_journal",
    default=False,
    help="Use journal abbreviations",
)
@click.option(
    "--batch-size",
    type=click.IntRange(1, 500),
    default=50,
    help="Batch processing size (default: 50)",
)
@click.option(
    "-v", "--verbose", is_flag=True, help="Enable verbose output"
)
def batch(
    file: str,
    output: Optional[str],
    format: str,
    use_async: bool,
    fetch_abstracts: bool,
    use_abbrev_journal: bool,
    batch_size: int,
    verbose: bool,
):
    """
    Process a batch file of DOIs.

    FILE: Path to text file containing one DOI per line.

    Supports .txt and .csv files with DOIs. Comments (lines starting with #)
    and empty lines are ignored.

    Examples:

        \b
        # Basic batch processing
        $ doi2bibtex batch dois.txt -o results.bib

        \b
        # With async mode for better performance
        $ doi2bibtex batch dois.txt --async -o results.bib

        \b
        # Custom batch size
        $ doi2bibtex batch dois.txt --batch-size 100 -o results.bib

        \b
        # RIS format
        $ doi2bibtex batch dois.txt -f ris -o results.ris
    """
    try:
        # Read DOIs from file
        file_path = Path(file)
        content = file_path.read_text(encoding="utf-8")

        # Parse DOIs (ignore comments and empty lines)
        dois = []
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                # Handle CSV files
                if "," in line:
                    dois.extend(doi.strip() for doi in line.split(",") if doi.strip())
                else:
                    dois.append(line)

        if not dois:
            click.echo("✗ Error: No DOIs found in file", err=True)
            sys.exit(1)

        if verbose:
            click.echo(f"Found {len(dois)} DOI(s) in {file_path}")

        # Create configuration
        config = AppConfig(
            fetch_abstracts=fetch_abstracts,
            use_abbrev_journal=use_abbrev_journal,
            batch_size=batch_size,
            remove_duplicates=True,
        )

        # Process batch
        if use_async:
            try:
                import asyncio
                from core.async_processor import process_dois_async

                if verbose:
                    click.echo("Using async processing...")

                result = asyncio.run(process_dois_async(config, dois))
            except ImportError:
                click.echo(
                    "Warning: aiohttp not installed. Falling back to sync processing.",
                    err=True,
                )
                processor = DOIProcessor(config)
                result = processor.process_batch(dois)
        else:
            if verbose:
                click.echo("Using sync processing...")
            processor = DOIProcessor(config)
            result = processor.process_batch(dois)

        if verbose:
            click.echo(
                f"✓ Successful: {result.successful_count}, "
                f"✗ Failed: {result.failed_count}"
            )
            click.echo(f"Execution time: {result.execution_time:.2f}s")

        # Convert to requested format
        if format.lower() == "bibtex":
            output_text = "\n\n".join(entry.bibtex for entry in result.entries if entry.bibtex)
        elif format.lower() == "ris":
            output_text = export_to_ris(result.entries)
        elif format.lower() == "endnote":
            output_text = export_to_endnote(result.entries)
        else:
            raise click.BadParameter(f"Unknown format: {format}")

        # Output results
        if output:
            output_path = Path(output)
            output_path.write_text(output_text, encoding="utf-8")
            click.echo(f"✓ Results written to {output_path}")
        else:
            click.echo(output_text)

        # Report failures
        if result.failed_count > 0:
            click.echo(
                f"\n⚠ Warning: {result.failed_count} DOI(s) failed:", err=True
            )
            if verbose:
                for doi in result.failed_dois:
                    click.echo(f"  - {doi}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


# ============================================================================
# Info Commands
# ============================================================================


@cli.command()
def formats():
    """List supported output formats."""
    click.echo("Supported output formats:")
    click.echo("  • bibtex  - LaTeX/academic standard (.bib)")
    click.echo("  • ris     - Reference manager import (.ris)")
    click.echo("  • endnote - EndNote library format (.enw)")


@cli.command()
def sources():
    """List DOI data sources."""
    click.echo("DOI data sources (in fallback order):")
    click.echo("  1. Crossref  - Primary source with rich metadata")
    click.echo("  2. DataCite  - Fallback for research data DOIs")
    click.echo("  3. DOI.org   - Final fallback via DOI resolver")


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Main entry point for CLI."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        click.echo("\n✗ Interrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"\n✗ Fatal error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
