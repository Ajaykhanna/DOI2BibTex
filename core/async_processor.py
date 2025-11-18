"""
Asynchronous DOI processing for improved performance.

This module provides async/await based DOI processing that can handle
multiple DOI requests concurrently, significantly improving performance
for large batches.
"""

from __future__ import annotations

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass

# Optional aiohttp import
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

from .config import AppConfig
from .state import BibtexEntry
from .exceptions import DOIError, NetworkError, DOINotFoundError
from .types import DOI, ProcessingResult, ProgressCallback
from .doi import clean_doi, is_valid_doi, extract_bibtex_fields
from .keys import make_key, disambiguate
from .export import order_bibtex_fields, safe_replace_key
from .logging_config import get_logger


# Configure logger
logger = get_logger("async_processor")

# Constants
# Multiple DOI resolution sources (try in order)
DOI_SOURCES = [
    ("Crossref", "https://api.crossref.org/works/{doi}/transform/application/x-bibtex"),
    ("DataCite", "https://api.datacite.org/application/x-bibtex/{doi}"),
    ("DOI.org", "https://doi.org/{doi}"),
]
DOI_BASE = "https://doi.org/"
CROSSREF_JSON = "https://api.crossref.org/works/"
APP_EMAIL = "akhanna2@ucmerced.edu"


@dataclass
class AsyncProcessingResult:
    """Result of async DOI processing operation."""
    entries: List[BibtexEntry]
    successful_count: int
    failed_count: int
    failed_dois: List[DOI]
    analytics: Dict[str, Any]
    execution_time: float
    total_requests: int
    requests_per_second: float
    
    @property
    def total_count(self) -> int:
        return self.successful_count + self.failed_count
    
    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return (self.successful_count / self.total_count) * 100.0


class AsyncDOIProcessor:
    """Asynchronous DOI processor for high-performance batch operations."""
    
    def __init__(self, config: AppConfig):
        if not AIOHTTP_AVAILABLE:
            raise ImportError(
                "aiohttp is required for async processing. "
                "Install with: pip install aiohttp"
            )

        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._used_keys: set[str] = set()  # Track citation keys to prevent duplicates
        self._key_lock: Optional[asyncio.Lock] = None  # Lock for thread-safe key generation
        self._crossref_cache: dict[str, dict] = {}  # Cache for Crossref JSON responses
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self._create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
    
    async def _create_session(self):
        """Create aiohttp session with proper configuration."""
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        headers = {
            "User-Agent": f"DOI2BibTex/3.0 (mailto:{APP_EMAIL})",
            "Accept": "application/x-bibtex, text/bibliography, application/json",
        }
        
        connector = aiohttp.TCPConnector(
            limit=self.config.concurrency * 2,  # Connection pool size
            limit_per_host=self.config.concurrency,
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
        )
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout,
            connector=connector
        )
        
        # Semaphore to limit concurrent requests
        self._semaphore = asyncio.Semaphore(self.config.concurrency)
        
        logger.info(f"Created async session with concurrency={self.config.concurrency}")
    
    async def _close_session(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
        self._semaphore = None
        logger.info("Closed async session")
    
    async def _fetch_with_retry(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        json_response: bool = False
    ) -> Tuple[Any, Optional[str]]:
        """
        Fetch URL with retry logic and rate limiting.
        
        Args:
            url: URL to fetch
            headers: Optional additional headers
            json_response: Whether to parse as JSON
            
        Returns:
            Tuple of (response_data, error_message)
        """
        if not self.session or not self._semaphore:
            raise RuntimeError("AsyncDOIProcessor not initialized. Use 'async with' context manager.")
        
        async with self._semaphore:  # Rate limiting
            for attempt in range(self.config.max_retries + 1):
                try:
                    request_headers = dict(self.session.headers)
                    if headers:
                        request_headers.update(headers)
                    
                    async with self.session.get(url, headers=request_headers) as response:
                        if response.status == 200:
                            if json_response:
                                data = await response.json()
                            else:
                                data = await response.text()
                            return data, None
                        
                        elif response.status == 404:
                            return None, "DOI not found"
                        
                        elif response.status == 429:
                            # Rate limited - exponential backoff
                            wait_time = (2 ** attempt) * 0.5
                            logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                            await asyncio.sleep(wait_time)
                            continue
                        
                        else:
                            error_msg = f"HTTP {response.status}"
                            if attempt == self.config.max_retries:
                                return None, error_msg
                            
                            # Brief wait before retry
                            await asyncio.sleep(0.5 * (attempt + 1))
                            continue
                
                except asyncio.TimeoutError:
                    error_msg = "Request timeout"
                    if attempt == self.config.max_retries:
                        return None, error_msg
                    await asyncio.sleep(1.0 * (attempt + 1))
                
                except aiohttp.ClientError as e:
                    error_msg = f"Client error: {e}"
                    if attempt == self.config.max_retries:
                        return None, error_msg
                    await asyncio.sleep(1.0 * (attempt + 1))
                
                except Exception as e:
                    error_msg = f"Unexpected error: {e}"
                    logger.error(f"Unexpected error fetching {url}: {e}")
                    return None, error_msg
        
        return None, "Max retries exceeded"

    async def _try_multiple_sources_async(self, doi: DOI) -> Tuple[Optional[str], Optional[str], dict]:
        """
        Try fetching BibTeX from multiple sources in order of preference.

        Args:
            doi: DOI string to fetch

        Returns:
            (bibtex_content, source_name, context_dict) on success or failure
        """
        source_failures = {}  # Track failures for error context

        for source_name, url_template in DOI_SOURCES:
            url = url_template.format(doi=doi)
            logger.info(f"Trying {source_name} for DOI: {doi}")

            try:
                bib_content, error = await self._fetch_with_retry(url)

                if not error and bib_content and "@" in bib_content:
                    logger.info(f"✓ Successfully fetched from {source_name}")
                    context = {
                        "source": source_name,
                        "url": url,
                        "sources_tried": list(source_failures.keys())
                    }
                    return bib_content, source_name, context
                else:
                    source_failures[source_name] = error or "No valid BibTeX"
                    logger.debug(f"✗ {source_name} failed: {source_failures[source_name]}")

            except Exception as e:
                source_failures[source_name] = str(e)
                logger.debug(f"✗ {source_name} error: {e}")
                continue

        # All sources failed - return context with all failures
        logger.warning(f"All sources failed for DOI: {doi}")
        context = {
            "sources_tried": list(DOI_SOURCES),
            "source_failures": source_failures,
            "timeout": self.config.timeout,
            "max_retries": self.config.max_retries
        }
        return None, None, context

    async def _enrich_with_crossref(self, doi: DOI, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich BibTeX fields with Crossref JSON data asynchronously."""
        try:
            # Check cache first
            if doi in self._crossref_cache:
                logger.debug(f"Using cached Crossref data for {doi}")
                message = self._crossref_cache[doi]
            else:
                crossref_url = CROSSREF_JSON + doi
                json_data, error = await self._fetch_with_retry(crossref_url, json_response=True)

                if error or not json_data or "message" not in json_data:
                    logger.warning(f"Crossref enrichment failed for {doi}: {error}")
                    return fields

                message = json_data["message"]
                # Cache the result
                self._crossref_cache[doi] = message
                logger.debug(f"Cached Crossref data for {doi}")

            # Extract abstract if requested
            if self.config.fetch_abstracts:
                abstract_jats = message.get("abstract")
                if abstract_jats:
                    import re
                    # Remove JATS XML tags
                    abstract_clean = re.sub(r"<[^>]+>", "", abstract_jats).strip()
                    fields["abstract"] = abstract_clean

            # Extract journal information
            self._extract_journal_info(message, fields)

            # Extract ISSN
            if "ISSN" in message and message["ISSN"]:
                fields["ISSN"] = message["ISSN"][0]

            # Extract URL (prefer DOI-based URL)
            fields["url"] = message.get("URL", f"http://dx.doi.org/{doi}")

            # Extract month from publication date
            published = message.get("published-print") or message.get("published-online")
            if published and "date-parts" in published and published["date-parts"]:
                date_parts = published["date-parts"][0]
                if len(date_parts) >= 2:
                    month_num = date_parts[1]
                    months = [
                        "jan", "feb", "mar", "apr", "may", "jun",
                        "jul", "aug", "sep", "oct", "nov", "dec"
                    ]
                    if 1 <= month_num <= 12:
                        fields["month"] = months[month_num - 1]

            # Extract pages if missing
            if "pages" not in fields:
                for field in ["page", "pages", "article-number"]:
                    if field in message and message[field]:
                        fields["pages"] = str(message[field])
                        break

            logger.debug(f"Successfully enriched {doi} with Crossref data")

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
    
    def _upsert_bibtex_field(self, bibtex: str, field: str, value: str) -> str:
        """Insert or update a field in BibTeX entry."""
        if not value:
            return bibtex
        
        import re
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
    
    async def fetch_bibtex_async(self, doi: DOI) -> BibtexEntry:
        """
        Fetch a single BibTeX entry asynchronously.
        
        Args:
            doi: DOI string to fetch
            
        Returns:
            BibtexEntry with metadata
            
        Raises:
            DOINotFoundError: When DOI is not found
            NetworkError: When network request fails
        """
        logger.debug(f"Fetching BibTeX for DOI: {doi}")

        metadata: Dict[str, Any] = {"doi": doi, "status": "processing"}

        # Step 1: Try fetching BibTeX from multiple sources
        bib_content, source_used, fetch_context = await self._try_multiple_sources_async(doi)

        if not bib_content:
            raise DOINotFoundError(doi, context=fetch_context)

        if "@" not in bib_content:
            raise DOIError("No BibTeX content in response", doi, context=fetch_context)

        metadata["source"] = source_used
        metadata["fetch_context"] = fetch_context
        
        # Extract and enrich BibTeX fields
        fields = extract_bibtex_fields(bib_content)
        
        # Fetch additional data from Crossref if needed
        fields = await self._enrich_with_crossref(doi, fields)
        
        # Normalize author names if requested
        if self.config.normalize_authors and "author" in fields:
            import re
            fields["author"] = re.sub(r"\s+", " ", fields["author"]).strip()
        
        # Generate and update citation key (thread-safe)
        base_key = make_key(fields, self.config.key_pattern)

        async with self._key_lock:
            citation_key = disambiguate(base_key, self._used_keys)
            self._used_keys.add(citation_key)

        old_key = fields.get("key", "")
        if old_key and old_key != citation_key:
            bib_content = safe_replace_key(bib_content, old_key, citation_key)
        fields["key"] = citation_key
        
        # Update journal information
        bib_content = self._update_journal_info(bib_content, fields)
        
        # Handle abstract inclusion
        bib_content = self._handle_abstracts(bib_content, fields)
        
        # Reorder fields
        bib_content = order_bibtex_fields(bib_content, self.config.field_order)
        
        metadata["status"] = "ok"
        metadata["metadata"] = fields
        
        logger.debug(f"Successfully processed DOI: {doi}")
        return BibtexEntry(
            key=citation_key,
            content=bib_content,
            metadata=metadata
        )
    
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
    
    async def process_batch_async(
        self, 
        dois: List[DOI], 
        progress_callback: Optional[ProgressCallback] = None
    ) -> AsyncProcessingResult:
        """
        Process a batch of DOIs asynchronously with concurrency control.
        
        Args:
            dois: List of DOI strings to process
            progress_callback: Optional callback for progress updates
            
        Returns:
            AsyncProcessingResult with entries and statistics
        """
        if not dois:
            return AsyncProcessingResult(
                entries=[],
                successful_count=0,
                failed_count=0,
                failed_dois=[],
                analytics={},
                execution_time=0.0,
                total_requests=0,
                requests_per_second=0.0
            )
        
        logger.info(f"Starting async batch processing of {len(dois)} DOIs")
        start_time = time.perf_counter()

        # Reset citation key tracking for this batch
        self._used_keys.clear()
        self._key_lock = asyncio.Lock()

        entries: List[BibtexEntry] = []
        failed_dois: List[DOI] = []
        completed_count = 0
        
        # Create semaphore for progress tracking
        progress_lock = asyncio.Lock()
        
        async def process_single_doi(doi: DOI) -> Optional[BibtexEntry]:
            """Process a single DOI with error handling and progress tracking."""
            nonlocal completed_count
            
            try:
                entry = await self.fetch_bibtex_async(doi)
                
                async with progress_lock:
                    completed_count += 1
                    if progress_callback:
                        progress_callback(completed_count, len(dois), doi)
                
                return entry
                
            except Exception as e:
                # Enhanced error logging with context
                if hasattr(e, 'to_dict'):
                    # Custom exception with structured data
                    error_data = e.to_dict()
                    logger.error(f"Failed to process DOI {doi}: {e}", extra={"error_context": error_data})
                else:
                    # Generic exception
                    logger.error(f"Failed to process DOI {doi}: {e}")

                failed_dois.append(doi)

                # Create error entry with context if available
                error_metadata = {"doi": doi, "status": "error", "error": str(e)}
                if hasattr(e, 'to_dict'):
                    error_metadata["error_details"] = e.to_dict()

                error_entry = BibtexEntry(
                    key="unknown",
                    content=f"Error: {doi} → {str(e)}",
                    metadata=error_metadata
                )
                
                async with progress_lock:
                    completed_count += 1
                    if progress_callback:
                        progress_callback(completed_count, len(dois), doi)
                
                return error_entry
        
        # Process all DOIs concurrently
        logger.info(f"Processing {len(dois)} DOIs with concurrency={self.config.concurrency}")
        tasks = [process_single_doi(doi) for doi in dois]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Filter out None results and collect entries
        entries = [entry for entry in results if entry is not None]
        
        # Remove duplicates if requested
        if self.config.remove_duplicates:
            from .dedupe import find_duplicates
            original_count = len(entries)
            duplicate_indices = find_duplicates(
                [(e.key, e.content, e.metadata) for e in entries]
            )
            
            if duplicate_indices:
                entries = [e for idx, e in enumerate(entries) if idx not in duplicate_indices]
                logger.info(f"Removed {len(duplicate_indices)} duplicates")
        
        # Calculate analytics
        from .analytics import summarize
        analytics = summarize([(e.key, e.content, e.metadata) for e in entries])
        
        # Calculate performance metrics
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        total_requests = len(dois) * (2 if self.config.fetch_abstracts else 1)  # DOI + Crossref requests
        requests_per_second = total_requests / execution_time if execution_time > 0 else 0
        
        successful_count = len([e for e in entries if not e.has_error])
        failed_count = len(failed_dois)
        
        logger.info(
            f"Async batch processing complete: {successful_count} successful, "
            f"{failed_count} failed out of {len(dois)} DOIs in {execution_time:.2f}s "
            f"({requests_per_second:.1f} req/s)"
        )
        
        return AsyncProcessingResult(
            entries=entries,
            successful_count=successful_count,
            failed_count=failed_count,
            failed_dois=failed_dois,
            analytics=analytics,
            execution_time=execution_time,
            total_requests=total_requests,
            requests_per_second=requests_per_second
        )


# Convenience function for async processing
async def process_dois_async(
    config: AppConfig, 
    dois: List[DOI], 
    progress_callback: Optional[ProgressCallback] = None
) -> AsyncProcessingResult:
    """
    Process DOIs asynchronously using context manager.
    
    Args:
        config: Application configuration
        dois: List of DOI strings
        progress_callback: Optional progress callback
        
    Returns:
        AsyncProcessingResult with processing statistics
    
    Raises:
        ImportError: If aiohttp is not installed
    """
    if not AIOHTTP_AVAILABLE:
        raise ImportError(
            "aiohttp is required for async processing. "
            "Install with: pip install aiohttp"
        )
    
    async with AsyncDOIProcessor(config) as processor:
        return await processor.process_batch_async(dois, progress_callback)


# Synchronous wrapper for async processing
def process_dois_sync(
    config: AppConfig,
    dois: List[DOI],
    progress_callback: Optional[ProgressCallback] = None
) -> AsyncProcessingResult:
    """
    Synchronous wrapper for async DOI processing.
    
    This function can be called from synchronous code and will
    handle the async event loop internally.
    
    Raises:
        ImportError: If aiohttp is not installed
    """
    if not AIOHTTP_AVAILABLE:
        raise ImportError(
            "aiohttp is required for async processing. "
            "Install with: pip install aiohttp"
        )
    try:
        # Try to use existing event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(process_dois_async(config, dois, progress_callback))
    else:
        # Event loop exists, run in thread pool
        import concurrent.futures
        
        def run_in_new_loop():
            return asyncio.run(process_dois_async(config, dois, progress_callback))
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_new_loop)
            return future.result()


# Performance comparison utility
async def compare_sync_vs_async_performance(
    config: AppConfig,
    test_dois: List[DOI],
    num_runs: int = 3
) -> Dict[str, Any]:
    """
    Compare performance between sync and async processing.
    
    Args:
        config: Application configuration
        test_dois: DOIs to test with
        num_runs: Number of runs for averaging
        
    Returns:
        Performance comparison results
    """
    from .processor import create_processor
    
    logger.info(f"Comparing sync vs async performance with {len(test_dois)} DOIs")
    
    # Sync processing times
    sync_times = []
    sync_processor = create_processor(config)
    
    for run in range(num_runs):
        start_time = time.perf_counter()
        # Mock the actual processing to avoid network calls in tests
        result = sync_processor.process_batch(test_dois[:5])  # Small subset
        sync_times.append(time.perf_counter() - start_time)
    
    # Async processing times
    async_times = []
    for run in range(num_runs):
        start_time = time.perf_counter()
        result = await process_dois_async(config, test_dois[:5])  # Small subset
        async_times.append(time.perf_counter() - start_time)
    
    avg_sync_time = sum(sync_times) / len(sync_times)
    avg_async_time = sum(async_times) / len(async_times)
    speedup = avg_sync_time / avg_async_time if avg_async_time > 0 else 1.0
    
    return {
        "sync_avg_time": avg_sync_time,
        "async_avg_time": avg_async_time,
        "speedup_ratio": speedup,
        "sync_times": sync_times,
        "async_times": async_times,
        "test_doi_count": len(test_dois),
        "concurrency": config.concurrency
    }
