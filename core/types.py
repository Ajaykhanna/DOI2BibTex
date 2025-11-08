"""
Type definitions for DOI2BibTex application.

This module provides comprehensive type hints and protocols for
better type safety and IDE support throughout the application.
"""

from __future__ import annotations

from typing import (
    Any, Protocol, TypeVar,
    Callable, Awaitable, Iterator, TypedDict, Literal
)
from dataclasses import dataclass
from abc import ABC, abstractmethod
import streamlit as st


# Basic type aliases
DOI = str
CitationKey = str 
BibTeXContent = str
JSONData = dict[str, Any]
FieldName = str
FieldValue = str

# Configuration types
ThemeType = Literal["light", "gray", "dark"]
KeyPatternType = Literal["author_year", "first_author_title_year", "journal_year"]
StyleType = Literal["APA", "MLA", "Chicago", "None"]

# Processing status types
ProcessingStatus = Literal["processing", "ok", "error"]

# Generic type variable
T = TypeVar('T')


# Structured metadata types
class BibTeXFields(TypedDict, total=False):
    """Type hint for BibTeX field dictionary."""
    key: str
    title: str | None
    author: str | None
    journal: str | None
    journal_full: str | None
    journal_abbrev: str | None
    volume: str | None
    number: str | None
    pages: str | None
    year: str | None
    publisher: str | None
    doi: str | None
    abstract: str | None
    url: str | None


class EntryMetadata(TypedDict):
    """Type hint for entry metadata dictionary."""
    doi: DOI
    status: ProcessingStatus
    error: str | None
    metadata: BibTeXFields | None


class AnalyticsData(TypedDict):
    """Type hint for analytics data dictionary."""
    total_entries: int
    year_range: str
    unique_authors: int
    unique_journals: int
    doi_coverage: float
    top_authors: list[tuple[str, int]]
    top_journals: list[tuple[str, int]]
    years_hist: dict[int, int]


# Progress callback type
ProgressCallback = Callable[[int, int, DOI], None]

# HTTP response types
class HTTPResponse(TypedDict):
    """Type hint for HTTP response data."""
    status_code: int
    content: bytes
    headers: dict[str, str]


class CrossrefMessage(TypedDict, total=False):
    """Type hint for Crossref API response message."""
    DOI: str
    title: list[str]
    author: list[dict[str, Any]]
    container_title: list[str]
    short_container_title: list[str]
    published_print: dict[str, list[int]]
    volume: str
    issue: str
    page: str
    publisher: str
    abstract: str


# Protocol definitions for dependency injection
class ConfigProtocol(Protocol):
    """Protocol for configuration objects."""
    theme: ThemeType
    batch_size: int
    timeout: int
    max_retries: int
    validate_dois: bool
    remove_duplicates: bool
    fetch_abstracts: bool
    include_abstracts: bool
    use_abbrev_journal: bool
    normalize_authors: bool
    key_pattern: KeyPatternType
    field_order: list[str]
    style_preview: StyleType


class StateProtocol(Protocol):
    """Protocol for application state objects."""
    entries: list[Any]
    analytics: AnalyticsData

    @property
    def has_entries(self) -> bool: ...
    @property
    def entry_count(self) -> int: ...
    def get_cite_keys(self) -> list[CitationKey]: ...
    def get_bibtex_content(self) -> BibTeXContent: ...


class ProcessorProtocol(Protocol):
    """Protocol for DOI processor objects."""

    def parse_input(self, raw_text: str, uploaded_file: Any) -> list[DOI]: ...

    def fetch_bibtex(self, doi: DOI) -> Any: ...

    def process_batch(
        self,
        dois: list[DOI],
        progress_callback: ProgressCallback | None
    ) -> Any: ...


class LoggerProtocol(Protocol):
    """Protocol for logger objects."""
    
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None: ...


# Abstract base classes
class DOIValidatorABC(ABC):
    """Abstract base class for DOI validators."""
    
    @abstractmethod
    def is_valid(self, doi: DOI) -> bool:
        """Check if DOI is valid."""
        pass
    
    @abstractmethod
    def clean(self, raw_doi: str) -> DOI:
        """Clean and normalize DOI."""
        pass


class DataExporterABC(ABC):
    """Abstract base class for data exporters."""

    @abstractmethod
    def export(self, entries: list[Any], format_type: str) -> str:
        """Export entries to specified format."""
        pass


class CacheProviderABC(ABC):
    """Abstract base class for cache providers."""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Get cached value."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set cached value with optional TTL."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values."""
        pass


# Result types for operations
@dataclass
class ProcessingResult:
    """Result of a DOI processing operation."""
    entries: list[Any]
    successful_count: int
    failed_count: int
    failed_dois: list[DOI]
    analytics: AnalyticsData
    execution_time: float
    
    @property
    def total_count(self) -> int:
        return self.successful_count + self.failed_count
    
    @property 
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return (self.successful_count / self.total_count) * 100.0


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    cleaned_value: Any | None = None


@dataclass
class ExportResult:
    """Result of data export operation."""
    content: str
    format_type: str
    entry_count: int
    file_size: int
    warnings: list[str]


# Streamlit-specific types
StreamlitUploadedFile = Any  # st.runtime.uploaded_file_manager.UploadedFile
StreamlitContainer = Any     # st.container
StreamlitColumn = Any        # st.columns result


# Function signature types for callbacks and handlers
ErrorHandler = Callable[[Exception], None]
ProgressHandler = Callable[[float, str], None]
CompletionHandler = Callable[[ProcessingResult], None]


# Advanced type utilities
class TypeGuard:
    """Type guard utilities for runtime type checking."""
    
    @staticmethod
    def is_doi(value: Any) -> bool:
        """Check if value is a valid DOI string."""
        return isinstance(value, str) and value.startswith(('10.', 'doi:', 'DOI:', 'https://doi.org/'))
    
    @staticmethod
    def is_bibtex_entry(value: Any) -> bool:
        """Check if value looks like a BibTeX entry."""
        return isinstance(value, str) and '@' in value and '{' in value and '}' in value
    
    @staticmethod
    def is_metadata_dict(value: Any) -> bool:
        """Check if value is a metadata dictionary."""
        return (
            isinstance(value, dict) and 
            'doi' in value and 
            'status' in value
        )


# Context manager types
class TimedOperation:
    """Context manager for timing operations."""

    def __init__(self, operation_name: str, logger: LoggerProtocol | None = None):
        self.operation_name = operation_name
        self.logger = logger
        self.start_time: float | None = None
        self.end_time: float | None = None
    
    def __enter__(self) -> TimedOperation:
        import time
        self.start_time = time.perf_counter()
        if self.logger:
            self.logger.info(f"Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        import time
        self.end_time = time.perf_counter()
        duration = self.end_time - self.start_time if self.start_time else 0.0
        
        if self.logger:
            if exc_type is None:
                self.logger.info(f"Completed {self.operation_name} in {duration:.3f}s")
            else:
                self.logger.error(f"Failed {self.operation_name} after {duration:.3f}s")
    
    @property
    def duration(self) -> float | None:
        """Get operation duration if completed."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


# Factory function types
ConfigFactory = Callable[[], ConfigProtocol]
ProcessorFactory = Callable[[ConfigProtocol], ProcessorProtocol]
StateFactory = Callable[[], StateProtocol]


# API response type hints
class CrossrefAPIResponse(TypedDict):
    """Type hint for Crossref API response."""
    status: str
    message_type: str
    message_version: str
    message: CrossrefMessage


class DOIAPIResponse(TypedDict):
    """Type hint for DOI resolution response."""
    content_type: str
    content: str
    status_code: int


# Validation schemas (for future runtime validation)
BIBTEX_REQUIRED_FIELDS = {'title', 'author', 'year'}
BIBTEX_OPTIONAL_FIELDS = {
    'journal', 'volume', 'number', 'pages', 'publisher', 
    'doi', 'abstract', 'url', 'keywords', 'note'
}
ALL_BIBTEX_FIELDS = BIBTEX_REQUIRED_FIELDS | BIBTEX_OPTIONAL_FIELDS


# Type checking utilities for development
def ensure_type(value: Any, expected_type: type, name: str = "value") -> Any:
    """Ensure value is of expected type, raising TypeError if not."""
    if not isinstance(value, expected_type):
        raise TypeError(f"{name} must be {expected_type.__name__}, got {type(value).__name__}")
    return value


def ensure_doi(value: Any) -> DOI:
    """Ensure value is a valid DOI string."""
    if not TypeGuard.is_doi(value):
        raise ValueError(f"Invalid DOI format: {value}")
    return str(value)
