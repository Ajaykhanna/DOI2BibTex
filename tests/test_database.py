"""
Comprehensive test suite for Database Layer (Phase 4).

Tests all functionality in core/database.py including:
- CRUD operations
- Search and filter
- Statistics and analytics
- Export/import
- Cleanup utilities
- Error handling
- Edge cases

Phase 6.1a: Database Layer Tests
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

# Import database components
try:
    from core.database import DOIDatabase, DOIEntry, Base
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    pytest.skip("SQLAlchemy not installed - skipping database tests", allow_module_level=True)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    """Provide temporary database path for testing."""
    db_path = tmp_path / "test_doi2bibtex.db"
    yield db_path
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def db(temp_db_path):
    """Provide fresh DOIDatabase instance for each test."""
    database = DOIDatabase(temp_db_path, echo=False, create_tables=True)
    yield database
    # Cleanup happens via temp_db_path fixture


@pytest.fixture
def sample_entry_data() -> Dict[str, Any]:
    """Provide sample DOI entry data."""
    return {
        "doi": "10.1038/nature12373",
        "bibtex": "@article{Nature2013,\n  title={Example Paper},\n  author={Smith, John},\n  year={2013}\n}",
        "metadata": {
            "title": "Example Paper",
            "author": "Smith, John",
            "year": "2013",
            "ISSN": "0028-0836",
            "publisher": "Nature Publishing Group"
        },
        "source": "Crossref",
        "quality_score": 0.95,
        "has_abstract": True
    }


@pytest.fixture
def multiple_entries_data():
    """Provide multiple sample entries for batch testing."""
    return [
        {
            "doi": "10.1038/nature12373",
            "bibtex": "@article{Nature2013, title={Paper 1}}",
            "metadata": {"title": "Paper 1"},
            "source": "Crossref",
            "quality_score": 0.95,
            "has_abstract": True
        },
        {
            "doi": "10.1126/science.1234567",
            "bibtex": "@article{Science2014, title={Paper 2}}",
            "metadata": {"title": "Paper 2"},
            "source": "Crossref",
            "quality_score": 0.88,
            "has_abstract": False
        },
        {
            "doi": "10.1371/journal.pone.0123456",
            "bibtex": "@article{PLOS2015, title={Paper 3}}",
            "metadata": {"title": "Paper 3"},
            "source": "DataCite",
            "quality_score": 0.72,
            "has_abstract": True
        },
        {
            "doi": "10.5281/zenodo.123456",
            "bibtex": "@article{Zenodo2016, title={Paper 4}}",
            "metadata": {"title": "Paper 4"},
            "source": "DataCite",
            "quality_score": 0.65,
            "has_abstract": False
        },
        {
            "doi": "10.1000/xyz123",
            "bibtex": "@article{DOI2017, title={Paper 5}}",
            "metadata": {"title": "Paper 5"},
            "source": "DOI.org",
            "quality_score": 0.50,
            "has_abstract": True
        }
    ]


# ============================================================================
# Test: Database Initialization
# ============================================================================

class TestDatabaseInitialization:
    """Test database initialization and setup."""

    def test_database_creation(self, temp_db_path):
        """Test database file is created."""
        db = DOIDatabase(temp_db_path)
        assert temp_db_path.exists()
        assert db.db_path == temp_db_path

    def test_table_creation(self, db):
        """Test database tables are created correctly."""
        # Check that we can query the table (would fail if not created)
        with db.get_session() as session:
            count = session.query(DOIEntry).count()
            assert count == 0

    def test_multiple_db_instances(self, temp_db_path):
        """Test multiple database instances can coexist."""
        db1 = DOIDatabase(temp_db_path)
        db2 = DOIDatabase(temp_db_path)

        # Both should work with same database
        assert db1.db_path == db2.db_path


# ============================================================================
# Test: CRUD Operations
# ============================================================================

class TestCRUDOperations:
    """Test Create, Read, Update, Delete operations."""

    def test_save_entry(self, db, sample_entry_data):
        """Test saving a new DOI entry."""
        entry = db.save_entry(**sample_entry_data)

        assert entry.doi == sample_entry_data["doi"]
        assert entry.bibtex == sample_entry_data["bibtex"]
        assert entry.source == sample_entry_data["source"]
        assert entry.quality_score == sample_entry_data["quality_score"]
        assert entry.has_abstract == sample_entry_data["has_abstract"]
        assert entry.metadata == sample_entry_data["metadata"]
        assert entry.created_at is not None
        assert entry.access_count == 1

    def test_get_entry(self, db, sample_entry_data):
        """Test retrieving a DOI entry."""
        # Save entry first
        db.save_entry(**sample_entry_data)

        # Retrieve it
        entry = db.get_entry(sample_entry_data["doi"])

        assert entry is not None
        assert entry.doi == sample_entry_data["doi"]
        assert entry.bibtex == sample_entry_data["bibtex"]

    def test_get_nonexistent_entry(self, db):
        """Test retrieving non-existent entry returns None."""
        entry = db.get_entry("10.1234/nonexistent")
        assert entry is None

    def test_update_entry(self, db, sample_entry_data):
        """Test updating an existing entry."""
        # Save initial entry
        db.save_entry(**sample_entry_data)

        # Update with new data
        new_bibtex = "@article{Updated, title={Updated Title}}"
        updated_entry = db.save_entry(
            doi=sample_entry_data["doi"],
            bibtex=new_bibtex,
            metadata={"title": "Updated"},
            source="DataCite",
            quality_score=0.80,
            has_abstract=False
        )

        assert updated_entry.bibtex == new_bibtex
        assert updated_entry.source == "DataCite"
        assert updated_entry.quality_score == 0.80
        assert updated_entry.has_abstract == False
        assert updated_entry.updated_at > updated_entry.created_at

    def test_delete_entry(self, db, sample_entry_data):
        """Test deleting an entry."""
        # Save entry
        db.save_entry(**sample_entry_data)

        # Verify it exists
        assert db.get_entry(sample_entry_data["doi"]) is not None

        # Delete it
        result = db.delete_entry(sample_entry_data["doi"])
        assert result is True

        # Verify it's gone
        assert db.get_entry(sample_entry_data["doi"]) is None

    def test_delete_nonexistent_entry(self, db):
        """Test deleting non-existent entry returns False."""
        result = db.delete_entry("10.1234/nonexistent")
        assert result is False

    def test_access_count_increment(self, db, sample_entry_data):
        """Test access count increments on each retrieval."""
        # Save entry
        db.save_entry(**sample_entry_data)

        # Access it multiple times
        for i in range(1, 6):
            entry = db.get_entry(sample_entry_data["doi"])
            # First access was on save (count=1), so this is +1 each time
            assert entry.access_count == i + 1

    def test_last_accessed_updates(self, db, sample_entry_data):
        """Test last_accessed timestamp updates on retrieval."""
        # Save entry
        db.save_entry(**sample_entry_data)

        # Get initial timestamp
        entry1 = db.get_entry(sample_entry_data["doi"])
        first_access = entry1.last_accessed

        # Wait a tiny bit and access again
        import time
        time.sleep(0.01)

        entry2 = db.get_entry(sample_entry_data["doi"])
        second_access = entry2.last_accessed

        assert second_access > first_access


# ============================================================================
# Test: Search and Filter
# ============================================================================

class TestSearchAndFilter:
    """Test search and filter functionality."""

    def test_search_all_entries(self, db, multiple_entries_data):
        """Test retrieving all entries without filters."""
        # Save multiple entries
        for entry_data in multiple_entries_data:
            db.save_entry(**entry_data)

        # Search without filters
        entries = db.search_entries(limit=100)

        assert len(entries) == len(multiple_entries_data)

    def test_search_by_source(self, db, multiple_entries_data):
        """Test filtering by source."""
        # Save entries
        for entry_data in multiple_entries_data:
            db.save_entry(**entry_data)

        # Search for Crossref entries
        crossref_entries = db.search_entries(source="Crossref")
        assert len(crossref_entries) == 2
        assert all(e.source == "Crossref" for e in crossref_entries)

        # Search for DataCite entries
        datacite_entries = db.search_entries(source="DataCite")
        assert len(datacite_entries) == 2
        assert all(e.source == "DataCite" for e in datacite_entries)

    def test_search_by_abstract(self, db, multiple_entries_data):
        """Test filtering by abstract presence."""
        # Save entries
        for entry_data in multiple_entries_data:
            db.save_entry(**entry_data)

        # Search for entries with abstracts
        with_abstracts = db.search_entries(has_abstract=True)
        assert len(with_abstracts) == 3
        assert all(e.has_abstract for e in with_abstracts)

        # Search for entries without abstracts
        without_abstracts = db.search_entries(has_abstract=False)
        assert len(without_abstracts) == 2
        assert all(not e.has_abstract for e in without_abstracts)

    def test_search_combined_filters(self, db, multiple_entries_data):
        """Test combining multiple filters."""
        # Save entries
        for entry_data in multiple_entries_data:
            db.save_entry(**entry_data)

        # Search for Crossref entries with abstracts
        results = db.search_entries(source="Crossref", has_abstract=True)
        assert len(results) == 1
        assert results[0].source == "Crossref"
        assert results[0].has_abstract is True

    def test_search_with_limit(self, db, multiple_entries_data):
        """Test limit parameter."""
        # Save entries
        for entry_data in multiple_entries_data:
            db.save_entry(**entry_data)

        # Search with limit
        results = db.search_entries(limit=3)
        assert len(results) == 3

    def test_search_with_offset(self, db, multiple_entries_data):
        """Test offset parameter for pagination."""
        # Save entries
        for entry_data in multiple_entries_data:
            db.save_entry(**entry_data)

        # Get first page
        page1 = db.search_entries(limit=2, offset=0)
        # Get second page
        page2 = db.search_entries(limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].doi != page2[0].doi

    def test_search_returns_newest_first(self, db, multiple_entries_data):
        """Test entries are ordered by creation date (newest first)."""
        # Save entries
        for entry_data in multiple_entries_data:
            db.save_entry(**entry_data)

        results = db.search_entries()

        # Verify descending order
        for i in range(len(results) - 1):
            assert results[i].created_at >= results[i + 1].created_at


# ============================================================================
# Test: Statistics
# ============================================================================

class TestStatistics:
    """Test database statistics functionality."""

    def test_empty_database_stats(self, db):
        """Test statistics on empty database."""
        stats = db.get_statistics()

        assert stats["total_entries"] == 0
        assert stats["by_source"]["Crossref"] == 0
        assert stats["by_source"]["DataCite"] == 0
        assert stats["by_source"]["DOI.org"] == 0
        assert stats["with_abstracts"] == 0
        assert stats["abstract_percentage"] == 0
        assert stats["oldest_entry"] is None
        assert stats["newest_entry"] is None

    def test_statistics_with_data(self, db, multiple_entries_data):
        """Test statistics with populated database."""
        # Save entries
        for entry_data in multiple_entries_data:
            db.save_entry(**entry_data)

        stats = db.get_statistics()

        assert stats["total_entries"] == 5
        assert stats["by_source"]["Crossref"] == 2
        assert stats["by_source"]["DataCite"] == 2
        assert stats["by_source"]["DOI.org"] == 1
        assert stats["with_abstracts"] == 3
        assert stats["abstract_percentage"] == 60.0
        assert stats["oldest_entry"] is not None
        assert stats["newest_entry"] is not None


# ============================================================================
# Test: Export/Import
# ============================================================================

class TestExportImport:
    """Test JSON export and import functionality."""

    def test_export_to_json(self, db, multiple_entries_data, tmp_path):
        """Test exporting database to JSON."""
        # Save entries
        for entry_data in multiple_entries_data:
            db.save_entry(**entry_data)

        # Export to file
        export_path = tmp_path / "export.json"
        count = db.export_to_json(export_path)

        assert count == len(multiple_entries_data)
        assert export_path.exists()

        # Verify JSON content
        with open(export_path) as f:
            data = json.load(f)

        assert len(data) == len(multiple_entries_data)
        assert all("doi" in entry for entry in data)
        assert all("bibtex" in entry for entry in data)

    def test_import_from_json(self, db, tmp_path):
        """Test importing database from JSON."""
        # Create export file
        export_data = [
            {
                "doi": "10.1038/nature12373",
                "bibtex": "@article{Test, title={Test}}",
                "metadata": {"title": "Test"},
                "source": "Crossref",
                "quality_score": 0.9,
                "has_abstract": True
            },
            {
                "doi": "10.1126/science.123",
                "bibtex": "@article{Test2, title={Test2}}",
                "metadata": {"title": "Test2"},
                "source": "DataCite",
                "quality_score": 0.8,
                "has_abstract": False
            }
        ]

        import_path = tmp_path / "import.json"
        import_path.write_text(json.dumps(export_data))

        # Import
        count = db.import_from_json(import_path)

        assert count == 2
        assert db.get_entry("10.1038/nature12373") is not None
        assert db.get_entry("10.1126/science.123") is not None

    def test_export_import_roundtrip(self, db, multiple_entries_data, tmp_path):
        """Test export then import preserves data."""
        # Save original entries
        for entry_data in multiple_entries_data:
            db.save_entry(**entry_data)

        # Export
        export_path = tmp_path / "roundtrip.json"
        db.export_to_json(export_path)

        # Clear database
        db.clear_all()
        assert db.get_statistics()["total_entries"] == 0

        # Import
        db.import_from_json(export_path)

        # Verify all entries restored
        assert db.get_statistics()["total_entries"] == len(multiple_entries_data)
        for entry_data in multiple_entries_data:
            entry = db.get_entry(entry_data["doi"])
            assert entry is not None
            assert entry.source == entry_data["source"]


# ============================================================================
# Test: Cleanup
# ============================================================================

class TestCleanup:
    """Test database cleanup functionality."""

    def test_cleanup_old_entries(self, db, sample_entry_data):
        """Test cleaning up old, unused entries."""
        # Save an entry
        db.save_entry(**sample_entry_data)

        # Manually set last_accessed to old date
        with db.get_session() as session:
            entry = session.query(DOIEntry).filter_by(doi=sample_entry_data["doi"]).first()
            entry.last_accessed = datetime.utcnow() - timedelta(days=100)
            session.commit()

        # Cleanup entries older than 90 days
        removed = db.cleanup_old_entries(days=90)

        assert removed == 1
        assert db.get_entry(sample_entry_data["doi"]) is None

    def test_cleanup_preserves_recent(self, db, sample_entry_data):
        """Test cleanup preserves recently accessed entries."""
        # Save an entry
        db.save_entry(**sample_entry_data)

        # Access it (updates last_accessed)
        db.get_entry(sample_entry_data["doi"])

        # Try to cleanup (should preserve it)
        removed = db.cleanup_old_entries(days=90)

        assert removed == 0
        assert db.get_entry(sample_entry_data["doi"]) is not None

    def test_clear_all(self, db, multiple_entries_data):
        """Test clearing all database entries."""
        # Save multiple entries
        for entry_data in multiple_entries_data:
            db.save_entry(**entry_data)

        # Verify entries exist
        assert db.get_statistics()["total_entries"] == len(multiple_entries_data)

        # Clear all
        count = db.clear_all()

        assert count == len(multiple_entries_data)
        assert db.get_statistics()["total_entries"] == 0


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_metadata(self, db):
        """Test saving entry with empty metadata."""
        entry = db.save_entry(
            doi="10.1234/test",
            bibtex="@article{Test, title={Test}}",
            metadata={},
            source="Crossref"
        )

        assert entry.metadata == {}

    def test_none_metadata(self, db):
        """Test saving entry with None metadata."""
        entry = db.save_entry(
            doi="10.1234/test",
            bibtex="@article{Test, title={Test}}",
            metadata=None,
            source="Crossref"
        )

        # Should handle None gracefully
        assert entry.metadata_json is None or entry.metadata == {}

    def test_very_long_bibtex(self, db):
        """Test saving entry with very long BibTeX."""
        long_bibtex = "@article{Test, title={" + "x" * 10000 + "}}"

        entry = db.save_entry(
            doi="10.1234/test",
            bibtex=long_bibtex,
            metadata={"title": "Test"},
            source="Crossref"
        )

        assert len(entry.bibtex) > 10000

    def test_special_characters_in_doi(self, db):
        """Test DOI with special characters."""
        special_doi = "10.1234/test-123_abc(2024)"

        entry = db.save_entry(
            doi=special_doi,
            bibtex="@article{Test, title={Test}}",
            metadata={},
            source="Crossref"
        )

        retrieved = db.get_entry(special_doi)
        assert retrieved is not None
        assert retrieved.doi == special_doi

    def test_unicode_in_metadata(self, db):
        """Test Unicode characters in metadata."""
        unicode_metadata = {
            "title": "Tëst Pàper with Ûnicode",
            "author": "José García-López"
        }

        entry = db.save_entry(
            doi="10.1234/test",
            bibtex="@article{Test, title={Test}}",
            metadata=unicode_metadata,
            source="Crossref"
        )

        retrieved = db.get_entry("10.1234/test")
        assert retrieved.metadata["title"] == unicode_metadata["title"]
        assert retrieved.metadata["author"] == unicode_metadata["author"]

    def test_to_dict_serialization(self, db, sample_entry_data):
        """Test entry.to_dict() serialization."""
        entry = db.save_entry(**sample_entry_data)

        entry_dict = entry.to_dict()

        assert isinstance(entry_dict, dict)
        assert entry_dict["doi"] == sample_entry_data["doi"]
        assert entry_dict["source"] == sample_entry_data["source"]
        assert isinstance(entry_dict["created_at"], str)  # ISO format string
        assert isinstance(entry_dict["metadata"], dict)

    def test_repr_string(self, db, sample_entry_data):
        """Test entry __repr__ method."""
        entry = db.save_entry(**sample_entry_data)

        repr_str = repr(entry)

        assert "DOIEntry" in repr_str
        assert sample_entry_data["doi"] in repr_str
        assert sample_entry_data["source"] in repr_str


# ============================================================================
# Test: Database Representation
# ============================================================================

class TestDatabaseRepresentation:
    """Test database __repr__ and metadata."""

    def test_database_repr(self, db, multiple_entries_data):
        """Test DOIDatabase __repr__ method."""
        # Add some entries
        for entry_data in multiple_entries_data[:3]:
            db.save_entry(**entry_data)

        repr_str = repr(db)

        assert "DOIDatabase" in repr_str
        assert "entries=3" in repr_str
        assert str(db.db_path) in repr_str


# ============================================================================
# Test: Concurrent Access (Thread Safety)
# ============================================================================

class TestConcurrentAccess:
    """Test thread-safe database operations."""

    def test_concurrent_writes(self, db):
        """Test multiple threads can write simultaneously."""
        import threading

        def save_entry(doi_num):
            db.save_entry(
                doi=f"10.1234/test{doi_num}",
                bibtex=f"@article{{Test{doi_num}, title={{Test}}}}",
                metadata={},
                source="Crossref"
            )

        # Create 10 threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=save_entry, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify all entries saved
        stats = db.get_statistics()
        assert stats["total_entries"] == 10

    def test_concurrent_reads(self, db, sample_entry_data):
        """Test multiple threads can read simultaneously."""
        import threading

        # Save an entry first
        db.save_entry(**sample_entry_data)

        results = []

        def read_entry():
            entry = db.get_entry(sample_entry_data["doi"])
            results.append(entry is not None)

        # Create 10 reader threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=read_entry)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All should have succeeded
        assert all(results)
        assert len(results) == 10


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
