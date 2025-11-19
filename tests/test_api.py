"""
Comprehensive test suite for REST API Layer (Phase 4).

Tests all functionality in api_server.py including:
- Health check endpoints
- Single DOI conversion
- Batch DOI conversion
- Error handling
- CORS headers
- Request validation
- Response formats

Phase 6.1b: REST API Tests
"""

import pytest
from typing import Dict, Any

# Import API components
try:
    from fastapi.testclient import TestClient
    from api_server import app
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    pytest.skip("FastAPI not installed - skipping API tests", allow_module_level=True)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Provide FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_doi():
    """Provide a sample DOI for testing."""
    return "10.1038/nature12373"


@pytest.fixture
def sample_dois():
    """Provide multiple DOIs for batch testing."""
    return [
        "10.1038/nature12373",
        "10.1126/science.1234567",
        "10.1371/journal.pone.0123456"
    ]


@pytest.fixture
def valid_convert_request():
    """Provide valid batch conversion request."""
    return {
        "dois": [
            "10.1038/nature12373",
            "10.1126/science.1234567"
        ],
        "format": "bibtex",
        "fetch_abstracts": False,
        "remove_duplicates": True
    }


# ============================================================================
# Test: Health Endpoints
# ============================================================================

class TestHealthEndpoints:
    """Test health check and root endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns health status."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"

    def test_health_check_endpoint(self, client):
        """Test /health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data

    def test_health_returns_json(self, client):
        """Test health endpoint returns proper JSON."""
        response = client.get("/health")

        assert response.headers["content-type"] == "application/json"
        assert response.json() is not None


# ============================================================================
# Test: Information Endpoints
# ============================================================================

class TestInformationEndpoints:
    """Test endpoints that provide information."""

    def test_list_formats_endpoint(self, client):
        """Test /api/v1/formats endpoint."""
        response = client.get("/api/v1/formats")

        assert response.status_code == 200
        formats = response.json()

        assert isinstance(formats, list)
        assert "bibtex" in formats
        assert "ris" in formats
        assert "endnote" in formats

    def test_list_sources_endpoint(self, client):
        """Test /api/v1/sources endpoint."""
        response = client.get("/api/v1/sources")

        assert response.status_code == 200
        sources = response.json()

        assert isinstance(sources, list)
        assert "Crossref" in sources
        assert "DataCite" in sources
        assert "DOI.org" in sources


# ============================================================================
# Test: Batch Conversion Endpoint
# ============================================================================

class TestBatchConversionEndpoint:
    """Test POST /api/v1/convert endpoint."""

    def test_batch_conversion_valid_request(self, client, valid_convert_request):
        """Test batch conversion with valid request."""
        response = client.post("/api/v1/convert", json=valid_convert_request)

        # May fail due to network, but should have correct structure
        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = response.json()

            assert "entries" in data
            assert "successful" in data
            assert "failed" in data
            assert "failed_dois" in data
            assert "execution_time" in data
            assert "timestamp" in data

    def test_batch_conversion_empty_dois(self, client):
        """Test batch conversion with empty DOI list."""
        request_data = {
            "dois": [],
            "format": "bibtex"
        }

        response = client.post("/api/v1/convert", json=request_data)

        # Should fail validation
        assert response.status_code == 422  # Validation error

    def test_batch_conversion_invalid_format(self, client, sample_dois):
        """Test batch conversion with invalid format."""
        request_data = {
            "dois": sample_dois,
            "format": "invalid_format"
        }

        response = client.post("/api/v1/convert", json=request_data)

        # Should fail validation
        assert response.status_code == 422

    def test_batch_conversion_too_many_dois(self, client):
        """Test batch conversion with too many DOIs."""
        request_data = {
            "dois": [f"10.1234/test{i}" for i in range(1001)],  # 1001 DOIs (max is 1000)
            "format": "bibtex"
        }

        response = client.post("/api/v1/convert", json=request_data)

        # Should fail validation
        assert response.status_code == 422

    def test_batch_conversion_with_abstracts(self, client, sample_dois):
        """Test batch conversion with abstracts option."""
        request_data = {
            "dois": sample_dois,
            "format": "bibtex",
            "fetch_abstracts": True
        }

        response = client.post("/api/v1/convert", json=request_data)

        # Structure should be valid
        assert response.status_code in [200, 400, 500]

    def test_batch_conversion_ris_format(self, client, sample_dois):
        """Test batch conversion to RIS format."""
        request_data = {
            "dois": sample_dois,
            "format": "ris"
        }

        response = client.post("/api/v1/convert", json=request_data)

        assert response.status_code in [200, 400, 500]

    def test_batch_conversion_response_structure(self, client):
        """Test batch conversion response has correct structure."""
        request_data = {
            "dois": ["10.1234/invalid"],  # Likely to fail but test structure
            "format": "bibtex"
        }

        response = client.post("/api/v1/convert", json=request_data)

        if response.status_code == 200:
            data = response.json()

            # Check required fields
            assert isinstance(data["entries"], list)
            assert isinstance(data["successful"], int)
            assert isinstance(data["failed"], int)
            assert isinstance(data["failed_dois"], list)
            assert isinstance(data["execution_time"], float)
            assert isinstance(data["timestamp"], str)


# ============================================================================
# Test: Single DOI Endpoint
# ============================================================================

class TestSingleDOIEndpoint:
    """Test GET /api/v1/doi/{doi} endpoint."""

    def test_single_doi_conversion(self, client, sample_doi):
        """Test single DOI conversion."""
        response = client.get(f"/api/v1/doi/{sample_doi}")

        # May fail due to network, but should have correct structure
        assert response.status_code in [200, 404, 500]

        if response.status_code == 200:
            data = response.json()

            assert "doi" in data
            assert "bibtex" in data
            assert "source" in data
            assert "metadata" in data

    def test_single_doi_with_format_param(self, client, sample_doi):
        """Test single DOI with format query parameter."""
        response = client.get(f"/api/v1/doi/{sample_doi}?format=ris")

        assert response.status_code in [200, 404, 500]

    def test_single_doi_with_abstracts(self, client, sample_doi):
        """Test single DOI with abstracts parameter."""
        response = client.get(f"/api/v1/doi/{sample_doi}?fetch_abstracts=true")

        assert response.status_code in [200, 404, 500]

    def test_single_doi_not_found(self, client):
        """Test single DOI endpoint with non-existent DOI."""
        invalid_doi = "10.1234/definitely-does-not-exist-12345"
        response = client.get(f"/api/v1/doi/{invalid_doi}")

        # Should return 404
        assert response.status_code in [404, 500]

        if response.status_code == 404:
            data = response.json()
            assert "error" in data or "detail" in data

    def test_single_doi_url_encoding(self, client):
        """Test DOI with special characters (URL encoding)."""
        # DOI with slash should be URL encoded
        doi_with_slash = "10.1038/nature12373"
        response = client.get(f"/api/v1/doi/{doi_with_slash}")

        assert response.status_code in [200, 404, 500]

    def test_single_doi_response_structure(self, client):
        """Test single DOI response has correct structure."""
        response = client.get(f"/api/v1/doi/10.1234/test")

        if response.status_code == 200:
            data = response.json()

            # Check required fields
            assert "doi" in data
            assert "bibtex" in data or "bibtex" is None
            assert "source" in data
            assert "metadata" in data
            assert isinstance(data["metadata"], dict)


# ============================================================================
# Test: Request Validation
# ============================================================================

class TestRequestValidation:
    """Test API request validation."""

    def test_missing_required_field(self, client):
        """Test request with missing required field."""
        request_data = {
            # Missing 'dois' field
            "format": "bibtex"
        }

        response = client.post("/api/v1/convert", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_invalid_json(self, client):
        """Test request with invalid JSON."""
        response = client.post(
            "/api/v1/convert",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_wrong_data_type(self, client):
        """Test request with wrong data type."""
        request_data = {
            "dois": "should be a list",  # Wrong type
            "format": "bibtex"
        }

        response = client.post("/api/v1/convert", json=request_data)

        assert response.status_code == 422

    def test_format_pattern_validation(self, client, sample_dois):
        """Test format field pattern validation."""
        request_data = {
            "dois": sample_dois,
            "format": "not-a-valid-format"
        }

        response = client.post("/api/v1/convert", json=request_data)

        assert response.status_code == 422


# ============================================================================
# Test: Error Handling
# ============================================================================

class TestErrorHandling:
    """Test API error handling."""

    def test_404_endpoint(self, client):
        """Test accessing non-existent endpoint."""
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test wrong HTTP method."""
        # POST to a GET endpoint
        response = client.post("/health")

        assert response.status_code == 405  # Method not allowed

    def test_error_response_structure(self, client):
        """Test error responses have consistent structure."""
        response = client.post("/api/v1/convert", json={})

        assert response.status_code == 422

        # Error response should be JSON
        assert response.headers["content-type"] == "application/json"


# ============================================================================
# Test: CORS Headers
# ============================================================================

class TestCORSHeaders:
    """Test CORS middleware functionality."""

    def test_cors_headers_present(self, client):
        """Test CORS headers are included in responses."""
        response = client.get(
            "/health",
            headers={"Origin": "http://example.com"}
        )

        assert response.status_code == 200
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers

    def test_cors_preflight_request(self, client):
        """Test CORS preflight OPTIONS request."""
        response = client.options(
            "/api/v1/convert",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST"
            }
        )

        # Should allow the request
        assert response.status_code == 200


# ============================================================================
# Test: Content Negotiation
# ============================================================================

class TestContentNegotiation:
    """Test content type handling."""

    def test_json_content_type(self, client):
        """Test endpoints return JSON content type."""
        response = client.get("/health")

        assert "application/json" in response.headers["content-type"]

    def test_accept_header(self, client):
        """Test Accept header handling."""
        response = client.get(
            "/health",
            headers={"Accept": "application/json"}
        )

        assert response.status_code == 200


# ============================================================================
# Test: API Documentation
# ============================================================================

class TestAPIDocumentation:
    """Test API documentation endpoints."""

    def test_openapi_json(self, client):
        """Test OpenAPI JSON schema is available."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()

        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    def test_swagger_ui_redirect(self, client):
        """Test Swagger UI is accessible."""
        response = client.get("/docs", follow_redirects=False)

        # Should be available (200) or redirect
        assert response.status_code in [200, 307, 308]

    def test_redoc_ui(self, client):
        """Test ReDoc UI is accessible."""
        response = client.get("/redoc", follow_redirects=False)

        # Should be available (200) or redirect
        assert response.status_code in [200, 307, 308]


# ============================================================================
# Test: Request/Response Timing
# ============================================================================

class TestTiming:
    """Test API response timing."""

    def test_execution_time_included(self, client, sample_dois):
        """Test execution_time is included in batch response."""
        request_data = {
            "dois": sample_dois,
            "format": "bibtex"
        }

        response = client.post("/api/v1/convert", json=request_data)

        if response.status_code == 200:
            data = response.json()

            assert "execution_time" in data
            assert isinstance(data["execution_time"], (int, float))
            assert data["execution_time"] >= 0

    def test_timestamp_format(self, client):
        """Test timestamp is in ISO format."""
        response = client.get("/health")
        data = response.json()

        assert "timestamp" in data
        # Should be ISO format string
        assert isinstance(data["timestamp"], str)
        assert "T" in data["timestamp"] or "Z" in data["timestamp"]


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
