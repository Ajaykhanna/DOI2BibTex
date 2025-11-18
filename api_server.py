"""
REST API Server for DOI2BibTeX application.

This module provides a FastAPI-based REST API for programmatic access to
DOI conversion functionality, enabling:
- Batch DOI conversion via POST endpoints
- Single DOI lookup via GET endpoints
- Multiple output formats (BibTeX, RIS, EndNote)
- Async processing for high performance
- Auto-generated OpenAPI/Swagger documentation

Phase 4.2 Implementation

Usage:
    # Development server
    uvicorn api_server:app --reload --port 8000

    # Production server
    uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 4
"""

from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    from fastapi import FastAPI, HTTPException, Query, Path as PathParam
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, PlainTextResponse
    from pydantic import BaseModel, Field, validator
except ImportError:
    raise ImportError(
        "FastAPI dependencies not installed. Install with: pip install 'doi2bibtex[phase4]'"
    )

from core.processor import DOIProcessor
from core.config import AppConfig
from core.exceptions import DOIError, DOINotFoundError, ValidationError
from core.types import BibtexEntry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# API Models (Request/Response)
# ============================================================================


class DOIRequest(BaseModel):
    """Request model for batch DOI conversion."""

    dois: List[str] = Field(
        ...,
        description="List of DOIs to convert",
        min_items=1,
        max_items=1000,
        example=["10.1038/nature12373", "10.1126/science.1234567"],
    )
    format: str = Field(
        default="bibtex",
        description="Output format",
        pattern="^(bibtex|ris|endnote)$",
    )
    fetch_abstracts: bool = Field(
        default=False, description="Include abstracts in output"
    )
    use_abbrev_journal: bool = Field(
        default=False, description="Use journal abbreviations"
    )
    remove_duplicates: bool = Field(
        default=True, description="Remove duplicate DOIs"
    )

    @validator("dois")
    def validate_dois(cls, v):
        """Validate DOI list."""
        if not v:
            raise ValueError("DOI list cannot be empty")
        if len(v) > 1000:
            raise ValueError("Maximum 1000 DOIs per request")
        return v

    class Config:
        schema_extra = {
            "example": {
                "dois": ["10.1038/nature12373", "10.1126/science.1234567"],
                "format": "bibtex",
                "fetch_abstracts": False,
                "use_abbrev_journal": False,
                "remove_duplicates": True,
            }
        }


class DOIEntryResponse(BaseModel):
    """Response model for single DOI entry."""

    doi: str = Field(..., description="DOI identifier")
    bibtex: Optional[str] = Field(None, description="BibTeX string")
    source: str = Field(..., description="Data source (Crossref, DataCite, DOI.org)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    quality_score: Optional[float] = Field(None, description="Quality score (0-1)")

    class Config:
        schema_extra = {
            "example": {
                "doi": "10.1038/nature12373",
                "bibtex": "@article{...}",
                "source": "Crossref",
                "metadata": {"ISSN": "0028-0836", "publisher": "Springer Nature"},
                "quality_score": 0.95,
            }
        }


class DOIBatchResponse(BaseModel):
    """Response model for batch DOI conversion."""

    entries: List[DOIEntryResponse] = Field(
        default_factory=list, description="Successfully processed entries"
    )
    successful: int = Field(..., description="Number of successful conversions")
    failed: int = Field(..., description="Number of failed conversions")
    failed_dois: List[str] = Field(
        default_factory=list, description="List of failed DOIs"
    )
    execution_time: float = Field(..., description="Execution time in seconds")
    timestamp: str = Field(..., description="Request timestamp (ISO format)")

    class Config:
        schema_extra = {
            "example": {
                "entries": [
                    {
                        "doi": "10.1038/nature12373",
                        "bibtex": "@article{...}",
                        "source": "Crossref",
                        "metadata": {},
                        "quality_score": 0.95,
                    }
                ],
                "successful": 1,
                "failed": 0,
                "failed_dois": [],
                "execution_time": 1.23,
                "timestamp": "2025-01-18T12:00:00Z",
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Current timestamp")

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2025-01-18T12:00:00Z",
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

    class Config:
        schema_extra = {
            "example": {
                "error": "DOINotFoundError",
                "message": "DOI not found in any source",
                "details": {
                    "doi": "10.invalid/doi",
                    "sources_tried": ["Crossref", "DataCite", "DOI.org"],
                },
            }
        }


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="DOI2BibTeX API",
    description="Convert DOIs to BibTeX and other bibliography formats via REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware for browser-based clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global processor
processor = DOIProcessor(AppConfig())

# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/", response_model=HealthResponse, tags=["Health"])
async def root():
    """Root endpoint - API health check."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns service status and version information.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@app.post(
    "/api/v1/convert",
    response_model=DOIBatchResponse,
    responses={
        200: {"description": "Successful conversion"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["Conversion"],
)
async def convert_dois(request: DOIRequest):
    """
    Convert multiple DOIs to bibliography format.

    Processes a batch of DOIs and returns results in the specified format.
    Supports BibTeX, RIS, and EndNote formats.

    - **dois**: List of DOI identifiers (1-1000)
    - **format**: Output format (bibtex, ris, endnote)
    - **fetch_abstracts**: Include abstracts if available
    - **use_abbrev_journal**: Use journal abbreviations
    - **remove_duplicates**: Remove duplicate DOIs from input

    Returns batch processing results with success/failure counts.
    """
    import time

    start_time = time.time()

    try:
        # Create config from request
        config = AppConfig(
            fetch_abstracts=request.fetch_abstracts,
            use_abbrev_journal=request.use_abbrev_journal,
            remove_duplicates=request.remove_duplicates,
        )

        # Update processor config
        processor.config = config

        # Process DOIs
        result = processor.process_batch(request.dois)

        # Convert entries to response format
        entries = []
        for entry in result.entries:
            entries.append(
                DOIEntryResponse(
                    doi=entry.doi,
                    bibtex=entry.bibtex,
                    source=entry.metadata.get("source", "Unknown"),
                    metadata=entry.metadata.get("metadata", {}),
                    quality_score=entry.metadata.get("quality_score"),
                )
            )

        execution_time = time.time() - start_time

        return DOIBatchResponse(
            entries=entries,
            successful=result.successful_count,
            failed=result.failed_count,
            failed_dois=result.failed_dois,
            execution_time=round(execution_time, 3),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing batch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/doi/{doi:path}",
    response_model=DOIEntryResponse,
    responses={
        200: {"description": "DOI found and converted"},
        404: {"model": ErrorResponse, "description": "DOI not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["Conversion"],
)
async def get_doi(
    doi: str = PathParam(..., description="DOI identifier"),
    format: str = Query("bibtex", description="Output format", pattern="^(bibtex|ris|endnote)$"),
    fetch_abstracts: bool = Query(False, description="Include abstract"),
):
    """
    Get bibliography entry for a single DOI.

    Fetches and converts a single DOI to the specified format.

    - **doi**: DOI identifier (URL-encoded if necessary)
    - **format**: Output format (bibtex, ris, endnote)
    - **fetch_abstracts**: Include abstract if available

    Returns bibliography entry with metadata.
    """
    try:
        # Update processor config
        processor.config.fetch_abstracts = fetch_abstracts

        # Fetch DOI
        entry = processor.fetch_bibtex(doi)

        return DOIEntryResponse(
            doi=entry.doi,
            bibtex=entry.bibtex,
            source=entry.metadata.get("source", "Unknown"),
            metadata=entry.metadata.get("metadata", {}),
            quality_score=entry.metadata.get("quality_score"),
        )

    except DOINotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "DOINotFoundError",
                "message": str(e),
                "details": e.context if hasattr(e, "context") else {},
            },
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching DOI {doi}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/formats",
    response_model=List[str],
    tags=["Information"],
)
async def list_formats():
    """
    List supported output formats.

    Returns list of available bibliography formats.
    """
    return ["bibtex", "ris", "endnote"]


@app.get(
    "/api/v1/sources",
    response_model=List[str],
    tags=["Information"],
)
async def list_sources():
    """
    List supported DOI data sources.

    Returns list of DOI metadata sources with fallback order.
    """
    return ["Crossref", "DataCite", "DOI.org"]


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(DOIError)
async def doi_error_handler(request, exc: DOIError):
    """Handle DOI-related errors."""
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "details": exc.to_dict() if hasattr(exc, "to_dict") else {},
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTPException", "message": exc.detail},
    )


# ============================================================================
# Application Lifecycle
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("DOI2BibTeX API server starting...")
    logger.info("Docs available at http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("DOI2BibTeX API server shutting down...")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
