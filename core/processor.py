"""
DOI processing service for DOI2BibTex application.

This module separates business logic from UI concerns and provides
a clean service interface for DOI processing operations.
"""

from __future__ import annotations

import re
import time
import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from .config import AppConfig
from .state import BibtexEntry
from .exceptions import (
    DOIError, InvalidDOIError, DOINotFoundError, NetworkError, 
    BatchProcessingError, handle_exception, safe_file_read
)
from .http import get_with_retry, polite_headers, get_json_with_retry
from .doi import clean_doi, is_valid_doi, extract_bibtex_fields
from .keys import make_key, disambiguate
from .export import order_bibtex_fields, safe_replace_key
from .dedupe import find_duplicates
from .analytics import summarize


# Configure logger
logger = logging.getLogger(__name__)

# Constants
# Multiple DOI resolution sources (try in order)
DOI_SOURCES = [
    ("Crossref", "https://api.crossref.org/works/{doi}/transform/application/x-bibtex"),
    ("DataCite", "https://api.datacite.org/application/x-bibtex/{doi}"),
    ("DOI.org", "https://doi.org/{doi}"),
]
CROSSREF_JSON = "https://api.crossref.org/works/"
APP_EMAIL = "akhanna2@ucmerced.edu"


@dataclass
class ProcessingResult:
    """Result of DOI processing operation."""
    entries: List[BibtexEntry]
    successful_count: int
    failed_count: int
    failed_dois: List[str]
    analytics: Dict[str, Any]
    
    @property
    def total_count(self) -> int:
        return self.successful_count + self.failed_count
    
    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return (self.successful_count / self.total_count) * 100


class DOIProcessor:
    """Service class for processing DOIs into BibTeX entries."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        
    @handle_exception
    def parse_input(self, raw_text: str, uploaded_file=None) -> List[str]:
        """
        Parse raw input and optional uploaded file to extract DOIs.
        
        Args:
            raw_text: Raw text containing DOIs
            uploaded_file: Optional file upload
            
        Returns:
            List of cleaned and validated DOI strings
            
        Raises:
            InvalidDOIError: When DOI validation fails
            FileProcessingError: When file processing fails
        """
        items: List[str] = []
        
        # Process raw text input
        if raw_text:
            parts = re.split(r"[\s,]+", raw_text.strip())
            items.extend([p for p in parts if p])
        
        # Process uploaded file
        if uploaded_file is not None:
            try:
                text = safe_file_read(uploaded_file)
                parts = re.split(r"[\s,]+", text.strip())
                items.extend([p for p in parts if p])
            except Exception as e:
                logger.error(f"File processing error: {e}")
                raise
        
        # Clean DOIs
        cleaned = [clean_doi(x) for x in items]
        
        # Validate DOIs if requested
        if self.config.validate_dois:
            validated = []
            for doi in cleaned:
                if is_valid_doi(doi):
                    validated.append(doi)
                else:
                    logger.warning(f"Invalid DOI filtered out: {doi}")
            cleaned = validated
        
        if not cleaned:
            logger.info("No valid DOIs found in input")
        else:
            logger.info(f"Extracted {len(cleaned)} valid DOIs")
        
        return cleaned
    
    @handle_exception
    def fetch_bibtex(self, doi: str) -> BibtexEntry:
        """
        Fetch a single BibTeX entry for a DOI.
        
        Args:
            doi: DOI string to fetch
            
        Returns:
            BibtexEntry with metadata
            
        Raises:
            DOINotFoundError: When DOI is not found
            NetworkError: When network request fails
        """
        logger.info(f"Fetching BibTeX for DOI: {doi}")

        metadata: Dict[str, Any] = {"doi": doi, "status": "processing"}

        # Step 1: Try multiple sources for BibTeX
        bib_content, source_used = self._try_multiple_sources(doi)

        if not bib_content:
            raise DOINotFoundError(doi)

        metadata["source"] = source_used
        logger.info(f"Using BibTeX from {source_used}")

        # Step 2: Extract BibTeX fields
        fields = extract_bibtex_fields(bib_content)

        # Step 3: Get Crossref data for enrichment (pages, ISSN, url, month, abstracts)
        crossref_message = None
        needs_crossref = (
            self.config.fetch_abstracts or
            self.config.use_abbrev_journal or
            "pages" not in fields
        )

        if needs_crossref:
            try:
                json_data, error = get_json_with_retry(
                    CROSSREF_JSON + doi,
                    polite_headers(APP_EMAIL),
                    timeout=self.config.timeout,
                    max_retries=self.config.max_retries
                )

                if json_data and not error and "message" in json_data:
                    crossref_message = json_data["message"]

                    # Extract abstract if requested
                    if self.config.fetch_abstracts:
                        abstract_jats = crossref_message.get("abstract")
                        if abstract_jats:
                            abstract_clean = re.sub(r"<[^>]+>", "", abstract_jats).strip()
                            fields["abstract"] = abstract_clean

                    # Extract journal information
                    self._extract_journal_info(crossref_message, fields)

            except Exception as e:
                logger.warning(f"Crossref data fetch error for {doi}: {e}")

        # Step 4: Add missing pages from Crossref if needed
        if "pages" not in fields:
            pages = self._extract_pages_from_crossref_json(doi)
            if pages:
                bib_content = self._add_pages_to_bibtex(bib_content, pages)
                fields["pages"] = pages

        # Step 5: Enrich with additional fields (ISSN, url, month)
        fields = self._enrich_with_additional_fields(doi, fields, crossref_message)
        
        # Normalize author names if requested
        if self.config.normalize_authors and "author" in fields:
            fields["author"] = re.sub(r"\s+", " ", fields["author"]).strip()
        
        # Generate and update citation key
        base_key = make_key(fields, self.config.key_pattern)
        citation_key = disambiguate(base_key, set())  # TODO: Pass existing keys
        
        old_key = fields.get("key", "")
        if old_key and old_key != citation_key:
            bib_content = safe_replace_key(bib_content, old_key, citation_key)
        fields["key"] = citation_key
        
        # Update journal information
        bib_content = self._update_journal_info(bib_content, fields)
        
        # Handle abstract inclusion
        bib_content = self._handle_abstracts(bib_content, fields)
        
        # Reorder fields
        bib_content = order_bibtex_fields(
            bib_content, 
            self.config.field_order
        )
        
        metadata["status"] = "ok"
        metadata["metadata"] = fields
        
        logger.info(f"Successfully processed DOI: {doi}")
        return BibtexEntry(
            key=citation_key,
            content=bib_content,
            metadata=metadata
        )

    def _try_multiple_sources(self, doi: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Try fetching BibTeX from multiple sources in order of preference.

        Args:
            doi: DOI string to fetch

        Returns:
            (bibtex_content, source_name) on success, (None, None) if all fail
        """
        for source_name, url_template in DOI_SOURCES:
            url = url_template.format(doi=doi)
            logger.info(f"Trying {source_name} for DOI: {doi}")

            try:
                resp, err = get_with_retry(
                    url,
                    polite_headers(APP_EMAIL),
                    timeout=self.config.timeout,
                    max_retries=self.config.max_retries
                )

                if resp and resp.status_code == 200:
                    bibtex = resp.content.decode("utf-8", errors="replace")
                    if "@" in bibtex:  # Valid BibTeX marker
                        logger.info(f"✓ Successfully fetched from {source_name}")
                        return bibtex, source_name
                    else:
                        logger.warning(f"✗ {source_name} returned invalid BibTeX")
                else:
                    status = resp.status_code if resp else "no response"
                    logger.warning(f"✗ {source_name} failed: {err or f'HTTP {status}'}")

            except Exception as e:
                logger.warning(f"✗ {source_name} error: {e}")
                continue

        return None, None

    def _extract_pages_from_crossref_json(self, doi: str) -> Optional[str]:
        """
        Extract page numbers from Crossref JSON API if missing from BibTeX.

        Args:
            doi: DOI string

        Returns:
            Page number string or None
        """
        try:
            json_data, error = get_json_with_retry(
                CROSSREF_JSON + doi,
                polite_headers(APP_EMAIL),
                timeout=self.config.timeout,
                max_retries=self.config.max_retries
            )

            if error or not json_data:
                return None

            message = json_data.get('message', {})

            # Try different field names for pages
            for field in ['page', 'pages', 'article-number']:
                if field in message and message[field]:
                    logger.info(f"Extracted pages from Crossref: {message[field]}")
                    return str(message[field])

        except Exception as e:
            logger.warning(f"Error extracting pages from Crossref: {e}")

        return None

    def _add_pages_to_bibtex(self, bib_content: str, pages: str) -> str:
        """
        Add pages field to BibTeX entry if not present.

        Args:
            bib_content: BibTeX content
            pages: Page number string

        Returns:
            Updated BibTeX content
        """
        # Check if pages already exist
        if re.search(r'\bpages\s*=', bib_content, re.IGNORECASE):
            return bib_content

        # Add pages field before closing brace
        if bib_content.strip().endswith('}'):
            bib_content = bib_content.strip()[:-1]
            bib_content += f",\n  pages = {{{pages}}}\n}}"

        return bib_content

    def _enrich_with_additional_fields(
        self,
        doi: str,
        fields: Dict[str, Any],
        crossref_message: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enrich BibTeX fields with ISSN, url, and month from Crossref data.

        Args:
            doi: DOI string
            fields: Current fields dictionary
            crossref_message: Optional Crossref message data

        Returns:
            Enriched fields dictionary
        """
        if not crossref_message:
            # Minimal enrichment with just URL
            if 'url' not in fields:
                fields['url'] = f"http://dx.doi.org/{doi}"
            return fields

        # Extract ISSN
        if 'ISSN' in crossref_message and crossref_message['ISSN']:
            issn_list = crossref_message['ISSN']
            if isinstance(issn_list, list) and issn_list:
                fields['ISSN'] = issn_list[0]

        # Extract URL
        if 'URL' in crossref_message:
            fields['url'] = crossref_message['URL']
        else:
            fields['url'] = f"http://dx.doi.org/{doi}"

        # Extract month from publication date
        published = crossref_message.get('published-print') or crossref_message.get('published-online')
        if published and 'date-parts' in published:
            date_parts = published['date-parts'][0]
            if len(date_parts) >= 2 and date_parts[1]:
                month_num = date_parts[1]
                months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                         'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                if 1 <= month_num <= 12:
                    fields['month'] = months[month_num - 1]

        return fields

    def _enrich_with_crossref(self, doi: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich BibTeX fields with Crossref JSON data."""
        try:
            json_data, error = get_json_with_retry(
                CROSSREF_JSON + doi,
                polite_headers(APP_EMAIL),
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
            
            if error or not json_data or "message" not in json_data:
                logger.warning(f"Crossref enrichment failed for {doi}: {error}")
                return fields
            
            message = json_data["message"]
            
            # Extract abstract if requested
            if self.config.fetch_abstracts:
                abstract_jats = message.get("abstract")
                if abstract_jats:
                    # Remove JATS XML tags
                    abstract_clean = re.sub(r"<[^>]+>", "", abstract_jats).strip()
                    fields["abstract"] = abstract_clean
            
            # Extract journal information
            self._extract_journal_info(message, fields)
            
        except Exception as e:
            logger.warning(f"Crossref enrichment error for {doi}: {e}")
        
        return fields
    
    def _extract_journal_info(self, crossref_message: Dict[str, Any], fields: Dict[str, Any]) -> None:
        """Extract journal information from Crossref message."""
        # Full journal title
        container_title = crossref_message.get("container-title")
        if isinstance(container_title, list) and container_title:
            fields["journal_full"] = container_title[0]
        elif isinstance(container_title, str):
            fields["journal_full"] = container_title
        
        # Abbreviated journal title
        short_title = crossref_message.get("short-container-title")
        if isinstance(short_title, list) and short_title:
            fields["journal_abbrev"] = short_title[0]
        elif isinstance(short_title, str):
            fields["journal_abbrev"] = short_title
    
    def _update_journal_info(self, bib_content: str, fields: Dict[str, Any]) -> str:
        """Update journal information in BibTeX content."""
        if self.config.use_abbrev_journal and fields.get("journal_abbrev"):
            fields["journal"] = fields["journal_abbrev"]
            bib_content = self._upsert_bibtex_field(
                bib_content, "journal", fields["journal_abbrev"]
            )
        elif fields.get("journal_full"):
            fields.setdefault("journal", fields["journal_full"])
            bib_content = self._upsert_bibtex_field(
                bib_content, "journal", fields["journal"]
            )
        
        return bib_content
    
    def _handle_abstracts(self, bib_content: str, fields: Dict[str, Any]) -> str:
        """Handle abstract inclusion in BibTeX content."""
        if not self.config.include_abstracts:
            fields.pop("abstract", None)
        elif self.config.include_abstracts and fields.get("abstract"):
            bib_content = self._upsert_bibtex_field(
                bib_content, "abstract", fields["abstract"]
            )
        
        return bib_content
    
    def _upsert_bibtex_field(self, bibtex: str, field: str, value: str) -> str:
        """Insert or update a field in BibTeX entry."""
        if not value:
            return bibtex
        
        pattern = re.compile(
            rf"(^\s*{re.escape(field)}\s*=\s*\{{)(.*?)(\}}\s*,?)",
            re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )
        
        def replace_func(match):
            return match.group(1) + value + match.group(3)
        
        new_content, substitutions = pattern.subn(replace_func, bibtex)
        if substitutions > 0:
            return new_content
        
        # Field doesn't exist, add it before closing brace
        closing_pattern = re.compile(r"\n\}$", re.MULTILINE)
        return closing_pattern.sub(
            lambda m: f",\n  {field} = {{{value}}}\n}}", 
            bibtex.strip(), 
            count=1
        )
    
    @handle_exception
    def process_batch(self, dois: List[str], progress_callback=None) -> ProcessingResult:
        """
        Process a batch of DOIs.
        
        Args:
            dois: List of DOI strings to process
            progress_callback: Optional callback for progress updates
            
        Returns:
            ProcessingResult with entries and statistics
            
        Raises:
            BatchProcessingError: When batch processing encounters issues
        """
        if not dois:
            return ProcessingResult(
                entries=[],
                successful_count=0,
                failed_count=0,
                failed_dois=[],
                analytics={}
            )
        
        logger.info(f"Processing batch of {len(dois)} DOIs")
        
        entries: List[BibtexEntry] = []
        failed_dois: List[str] = []
        
        total = len(dois)
        for i, doi in enumerate(dois, 1):
            try:
                entry = self.fetch_bibtex(doi)
                entries.append(entry)
                
                # Update progress
                if progress_callback:
                    progress_callback(i, total, doi)
                
                # Rate limiting delay if show_progress is enabled
                if self.config.show_progress:
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Failed to process DOI {doi}: {e}")
                failed_dois.append(doi)
                
                # Create error entry
                error_entry = BibtexEntry(
                    key="unknown",
                    content=f"Error: {doi} → {str(e)}",
                    metadata={"doi": doi, "status": "error", "error": str(e)}
                )
                entries.append(error_entry)
                
                # Update progress
                if progress_callback:
                    progress_callback(i, total, doi)
        
        # Remove duplicates if requested
        if self.config.remove_duplicates:
            original_count = len(entries)
            duplicate_indices = find_duplicates(
                [(e.key, e.content, e.metadata) for e in entries]
            )
            
            if duplicate_indices:
                entries = [e for idx, e in enumerate(entries) if idx not in duplicate_indices]
                logger.info(f"Removed {len(duplicate_indices)} duplicates")
        
        # Calculate analytics
        analytics = summarize([(e.key, e.content, e.metadata) for e in entries])
        
        successful_count = len([e for e in entries if not e.has_error])
        failed_count = len(failed_dois)
        
        logger.info(
            f"Batch processing complete: {successful_count} successful, "
            f"{failed_count} failed out of {total} DOIs"
        )
        
        return ProcessingResult(
            entries=entries,
            successful_count=successful_count,
            failed_count=failed_count,
            failed_dois=failed_dois,
            analytics=analytics
        )


def create_processor(config: AppConfig) -> DOIProcessor:
    """Factory function to create DOI processor with configuration."""
    return DOIProcessor(config)
