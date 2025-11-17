"""
Custom exceptions and error handling for DOI2BibTex application.

This module provides specific exception types and user-friendly error handling
to replace generic error messages throughout the application.
"""

from __future__ import annotations

import streamlit as st
from typing import Optional, Any
from datetime import datetime
import logging


# Configure logger
logger = logging.getLogger(__name__)


class DOIError(Exception):
    """Base exception for DOI-related errors with enhanced context tracking."""

    def __init__(
        self,
        message: str,
        doi: Optional[str] = None,
        details: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ):
        self.message = message
        self.doi = doi
        self.details = details
        self.context = context or {}
        self.timestamp = datetime.now()
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize error to dictionary for logging and API responses.

        Returns:
            Dictionary with error details including type, message, DOI, details, context, and timestamp
        """
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "doi": self.doi,
            "details": self.details,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }

    def display_error(self) -> None:
        """Display user-friendly error message in Streamlit."""
        if self.doi:
            st.error(f"**DOI Error ({self.doi}):** {self.message}")
        else:
            st.error(f"**DOI Error:** {self.message}")

        if self.details:
            st.caption(f"Details: {self.details}")

        # Display context if in debug mode (could be controlled by config)
        if self.context and logger.isEnabledFor(logging.DEBUG):
            with st.expander("Debug Context"):
                st.json(self.context)


class InvalidDOIError(DOIError):
    """Raised when DOI format is invalid."""

    def __init__(
        self,
        doi: str,
        reason: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ):
        message = f"Invalid DOI format"
        details = reason if reason else "DOI does not match expected pattern"
        super().__init__(message, doi, details, context)


class DOINotFoundError(DOIError):
    """Raised when DOI is not found or returns 404."""

    def __init__(self, doi: str, context: Optional[dict[str, Any]] = None):
        message = "DOI not found"
        details = "The DOI may be invalid, not yet indexed, or temporarily unavailable"
        super().__init__(message, doi, details, context)


class NetworkError(DOIError):
    """Raised when network requests fail."""

    def __init__(
        self,
        message: str,
        doi: Optional[str] = None,
        status_code: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ):
        details = None
        ctx = context or {}

        if status_code:
            ctx["status_code"] = status_code
            if status_code == 429:
                details = "Too many requests - please wait and try again with smaller batches"
            elif status_code >= 500:
                details = "Server error - please try again later"
            elif status_code == 403:
                details = "Access forbidden - check DOI permissions"
            else:
                details = f"HTTP error code: {status_code}"

        super().__init__(message, doi, details, ctx)


class FileProcessingError(Exception):
    """Raised when file processing fails."""

    def __init__(
        self,
        message: str,
        filename: Optional[str] = None,
        details: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ):
        self.message = message
        self.filename = filename
        self.details = details
        self.context = context or {}
        self.timestamp = datetime.now()
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Serialize error to dictionary for logging and API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "filename": self.filename,
            "details": self.details,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }

    def display_error(self) -> None:
        """Display user-friendly error message in Streamlit."""
        if self.filename:
            st.error(f"**File Error ({self.filename}):** {self.message}")
        else:
            st.error(f"**File Error:** {self.message}")

        if self.details:
            st.caption(f"Details: {self.details}")


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ):
        self.message = message
        self.field = field
        self.context = context or {}
        self.timestamp = datetime.now()
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Serialize error to dictionary for logging and API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "field": self.field,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }

    def display_error(self) -> None:
        """Display user-friendly error message in Streamlit."""
        if self.field:
            st.error(f"**Configuration Error ({self.field}):** {self.message}")
        else:
            st.error(f"**Configuration Error:** {self.message}")


class BatchProcessingError(Exception):
    """Raised when batch processing encounters issues."""

    def __init__(
        self,
        message: str,
        processed_count: int,
        total_count: int,
        failed_dois: list[str],
        context: Optional[dict[str, Any]] = None
    ):
        self.message = message
        self.processed_count = processed_count
        self.total_count = total_count
        self.failed_dois = failed_dois
        self.context = context or {}
        self.timestamp = datetime.now()
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Serialize error to dictionary for logging and API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "processed_count": self.processed_count,
            "total_count": self.total_count,
            "failed_count": len(self.failed_dois),
            "failed_dois": self.failed_dois,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }

    def display_error(self) -> None:
        """Display user-friendly error message in Streamlit."""
        st.error(f"**Batch Processing Error:** {self.message}")

        if self.failed_dois:
            with st.expander(f"Failed DOIs ({len(self.failed_dois)})"):
                for doi in self.failed_dois:
                    st.write(f"• {doi}")


def handle_exception(func):
    """Decorator to handle exceptions and display user-friendly messages."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (DOIError, FileProcessingError, ConfigurationError, BatchProcessingError) as e:
            logger.error(f"Application error in {func.__name__}: {e}")
            e.display_error()
            return None
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            st.error(f"**Unexpected Error:** {str(e)}")
            st.caption("Please try again or contact support if the problem persists.")
            return None
    
    return wrapper


def validate_batch_size(batch_size: int) -> None:
    """Validate batch size and show warnings."""
    if not 1 <= batch_size <= 500:
        raise ConfigurationError(
            f"Batch size must be between 1 and 500", 
            field="batch_size"
        )
    
    if batch_size > 100:
        st.warning(
            f"⚠️ Large batch size ({batch_size}) may cause timeouts or rate limiting. "
            "Consider using smaller batches (≤50) for better reliability."
        )


def validate_file_upload(file) -> None:
    """Validate uploaded file."""
    if file is None:
        return
        
    # Check file size (limit to 10MB)
    if hasattr(file, 'size') and file.size > 10 * 1024 * 1024:
        raise FileProcessingError(
            "File too large",
            filename=file.name,
            details="Maximum file size is 10MB"
        )
    
    # Check file extension
    if hasattr(file, 'name'):
        allowed_extensions = ['.txt', '.csv']
        file_ext = '.' + file.name.split('.')[-1].lower()
        if file_ext not in allowed_extensions:
            raise FileProcessingError(
                "Invalid file type",
                filename=file.name,
                details=f"Allowed types: {', '.join(allowed_extensions)}"
            )


def safe_file_read(file) -> str:
    """Safely read file content with proper error handling."""
    if file is None:
        return ""
    
    try:
        # Validate file first
        validate_file_upload(file)
        
        # Try reading as UTF-8
        content = file.read()
        if isinstance(content, bytes):
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError:
                # Try with common encodings
                for encoding in ['latin1', 'cp1252', 'iso-8859-1']:
                    try:
                        return content.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                
                # Last resort: decode with error replacement
                return content.decode('utf-8', errors='replace')
        else:
            return str(content)
    
    except Exception as e:
        raise FileProcessingError(
            "Failed to read file",
            filename=getattr(file, 'name', 'unknown'),
            details=str(e)
        )


def display_batch_results(successful: int, failed: int, failed_dois: list[str]) -> None:
    """Display batch processing results with appropriate messaging."""
    total = successful + failed
    
    if failed == 0:
        st.success(f"✅ Successfully processed all {total} DOIs!")
    elif successful == 0:
        st.error(f"❌ Failed to process all {total} DOIs.")
        if failed_dois:
            with st.expander("Failed DOIs"):
                for doi in failed_dois:
                    st.write(f"• {doi}")
    else:
        st.warning(f"⚠️ Processed {successful} of {total} DOIs. {failed} failed.")
        if failed_dois:
            with st.expander(f"Failed DOIs ({failed})"):
                for doi in failed_dois:
                    st.write(f"• {doi}")
        
        # Provide actionable advice
        st.info(
            "💡 **Tips for failed DOIs:**\n"
            "- Check DOI format and validity\n" 
            "- Try processing failed DOIs individually\n"
            "- Reduce batch size if experiencing timeouts\n"
            "- Wait a moment before retrying (rate limiting)"
        )
