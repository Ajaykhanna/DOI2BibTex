"""
Pytest configuration and fixtures for DOI2BibTex tests.

This module provides shared fixtures and test configuration
for the entire test suite.
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock

# Import modules to test
from core.config import AppConfig, ConfigManager
from core.state import BibtexEntry, AppState, StateManager  
from core.processor import DOIProcessor
from core.logging_config import setup_preset_logging


@pytest.fixture
def sample_config():
    """Provide a sample configuration for testing."""
    return AppConfig(
        theme="light",
        batch_size=10,
        timeout=5,
        max_retries=2,
        validate_dois=True,
        key_pattern="author_year"
    )


@pytest.fixture
def sample_bibtex_entry():
    """Provide a sample BibTeX entry for testing."""
    return BibtexEntry(
        key="smith2023", 
        content="""@article{smith2023,
  title = {Test Article},
  author = {Smith, John and Doe, Jane},
  journal = {Test Journal},
  volume = {1},
  number = {2},
  pages = {10--20},
  year = {2023},
  doi = {10.1234/test}
}""",
        metadata={
            "doi": "10.1234/test",
            "status": "ok",
            "metadata": {
                "key": "smith2023",
                "title": "Test Article",
                "author": "Smith, John and Doe, Jane", 
                "journal": "Test Journal",
                "volume": "1",
                "number": "2", 
                "pages": "10--20",
                "year": "2023",
                "doi": "10.1234/test"
            }
        }
    )


@pytest.fixture
def sample_error_entry():
    """Provide a sample error entry for testing."""
    return BibtexEntry(
        key="unknown",
        content="Error: 10.9999/invalid → DOI not found",
        metadata={
            "doi": "10.9999/invalid",
            "status": "error",
            "error": "DOI not found"
        }
    )


@pytest.fixture
def sample_app_state(sample_bibtex_entry):
    """Provide a sample application state for testing."""
    return AppState(
        entries=[sample_bibtex_entry],
        analytics={
            "total_entries": 1,
            "year_range": "2023–2023",
            "unique_authors": 2,
            "unique_journals": 1,
            "doi_coverage": 100.0
        }
    )


@pytest.fixture
def mock_streamlit_session():
    """Provide a mock Streamlit session state."""
    return {}


@pytest.fixture
def temp_log_dir():
    """Provide a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_dois():
    """Provide sample DOIs for testing."""
    return [
        "10.1038/nature12373",
        "10.1126/science.1234567",
        "10.1145/3292500.3330701"
    ]


@pytest.fixture
def sample_invalid_dois():
    """Provide sample invalid DOIs for testing."""
    return [
        "invalid.doi",
        "10.9999/nonexistent", 
        "",
        "not-a-doi-at-all"
    ]


@pytest.fixture
def mock_http_response():
    """Provide a mock HTTP response."""
    mock = Mock()
    mock.status_code = 200
    mock.content = b"""@article{test2023,
  title = {Mock Article},
  author = {Test, Author},
  journal = {Mock Journal},
  year = {2023},
  doi = {10.1234/mock}
}"""
    mock.headers = {"Content-Type": "application/x-bibtex"}
    return mock


@pytest.fixture
def mock_crossref_response():
    """Provide a mock Crossref JSON response."""
    return {
        "status": "ok",
        "message": {
            "DOI": "10.1234/test",
            "title": ["Test Article Title"],
            "author": [
                {"given": "John", "family": "Smith"},
                {"given": "Jane", "family": "Doe"}
            ],
            "container-title": ["Test Journal Full Name"],
            "short-container-title": ["Test J."],
            "volume": "1",
            "issue": "2",
            "page": "10-20",
            "published-print": {"date-parts": [[2023]]},
            "abstract": "<p>This is a test abstract with <em>formatting</em>.</p>"
        }
    }


@pytest.fixture
def processor_with_mocks(sample_config):
    """Provide a DOI processor with mocked dependencies."""
    processor = DOIProcessor(sample_config)
    
    # Mock HTTP requests
    processor._make_request = Mock()
    processor._make_json_request = Mock()
    
    return processor


@pytest.fixture
def sample_file_content():
    """Provide sample file content for testing."""
    return """10.1038/nature12373
10.1126/science.1234567
10.1145/3292500.3330701"""


@pytest.fixture
def mock_uploaded_file(sample_file_content):
    """Provide a mock uploaded file."""
    mock_file = Mock()
    mock_file.read.return_value = sample_file_content.encode('utf-8')
    mock_file.name = "test_dois.txt"
    mock_file.size = len(sample_file_content)
    return mock_file


@pytest.fixture
def capture_logs(temp_log_dir):
    """Fixture to capture log output for testing."""
    log_file = temp_log_dir / "test.log"
    logger = setup_preset_logging("testing")
    
    # Add file handler for testing
    import logging
    file_handler = logging.FileHandler(str(log_file))
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    yield log_file, logger
    
    # Clean up
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            logger.removeHandler(handler)


@pytest.fixture
def performance_timer():
    """Fixture to measure test performance."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.perf_counter()
        
        def stop(self):
            self.end_time = time.perf_counter()
        
        @property 
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# Test data generators
def generate_bibtex_entries(count: int) -> List[BibtexEntry]:
    """Generate multiple BibTeX entries for testing."""
    entries = []
    for i in range(count):
        entry = BibtexEntry(
            key=f"test{2020 + i}",
            content=f"""@article{{test{2020 + i},
  title = {{Test Article {i + 1}}},
  author = {{Author{i + 1}, First}},
  journal = {{Test Journal}},
  year = {{{2020 + i}}},
  doi = {{10.1234/test{i}}}
}}""",
            metadata={
                "doi": f"10.1234/test{i}",
                "status": "ok",
                "metadata": {
                    "key": f"test{2020 + i}",
                    "title": f"Test Article {i + 1}",
                    "author": f"Author{i + 1}, First",
                    "journal": "Test Journal",
                    "year": str(2020 + i),
                    "doi": f"10.1234/test{i}"
                }
            }
        )
        entries.append(entry)
    return entries


# Pytest markers for test categorization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")  
    config.addinivalue_line("markers", "slow: Slow tests that may take time")
    config.addinivalue_line("markers", "network: Tests requiring network access")
    config.addinivalue_line("markers", "performance: Performance benchmarking tests")


# Custom assertions
def assert_bibtex_valid(content: str):
    """Assert that content is valid BibTeX."""
    assert "@" in content, "BibTeX must contain @ symbol"
    assert "{" in content, "BibTeX must contain opening brace"
    assert "}" in content, "BibTeX must contain closing brace"


def assert_doi_valid(doi: str):
    """Assert that DOI is valid format."""
    assert doi.startswith("10."), f"DOI must start with '10.', got: {doi}"
    assert "/" in doi, f"DOI must contain '/', got: {doi}"


def assert_citation_key_valid(key: str):
    """Assert that citation key is valid format."""
    assert key.isidentifier() or key.replace("-", "_").isidentifier(), \
        f"Citation key must be identifier-like, got: {key}"
    assert len(key) > 0, "Citation key cannot be empty"
