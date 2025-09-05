"""
Tests for application state management module.
"""

import pytest
from unittest.mock import Mock, patch

from core.state import BibtexEntry, AppState, StateManager, get_state
from tests.conftest import generate_bibtex_entries, assert_citation_key_valid


class TestBibtexEntry:
    """Test BibtexEntry dataclass."""
    
    def test_entry_creation(self):
        """Test creating a BibTeX entry."""
        entry = BibtexEntry(
            key="test2023",
            content="@article{test2023, title={Test}}",
            metadata={"doi": "10.1234/test", "status": "ok"}
        )
        
        assert entry.key == "test2023"
        assert "@article" in entry.content
        assert entry.metadata["status"] == "ok"
    
    def test_doi_property(self, sample_bibtex_entry):
        """Test DOI property extraction."""
        assert sample_bibtex_entry.doi == "10.1234/test"
        
        # Test entry without DOI
        entry_no_doi = BibtexEntry("key", "content", {"status": "ok"})
        assert entry_no_doi.doi is None
    
    def test_title_property(self, sample_bibtex_entry):
        """Test title property extraction."""
        assert sample_bibtex_entry.title == "Test Article"
        
        # Test entry without title
        entry_no_title = BibtexEntry("key", "content", {"status": "ok", "metadata": {}})
        assert entry_no_title.title is None
    
    def test_year_property(self, sample_bibtex_entry):
        """Test year property extraction and conversion."""
        assert sample_bibtex_entry.year == 2023
        
        # Test entry with string year
        entry_str_year = BibtexEntry(
            "key", "content", 
            {"status": "ok", "metadata": {"year": "2022"}}
        )
        assert entry_str_year.year == 2022
        
        # Test entry with invalid year
        entry_bad_year = BibtexEntry(
            "key", "content",
            {"status": "ok", "metadata": {"year": "invalid"}}
        )
        assert entry_bad_year.year is None
    
    def test_has_error_property(self, sample_bibtex_entry, sample_error_entry):
        """Test error status detection."""
        assert not sample_bibtex_entry.has_error
        assert sample_error_entry.has_error
    
    def test_error_message_property(self, sample_bibtex_entry, sample_error_entry):
        """Test error message extraction."""
        assert sample_bibtex_entry.error_message is None
        assert sample_error_entry.error_message == "DOI not found"


class TestAppState:
    """Test AppState dataclass."""
    
    def test_state_creation(self, sample_bibtex_entry):
        """Test creating application state."""
        state = AppState(
            entries=[sample_bibtex_entry],
            analytics={"total": 1}
        )
        
        assert len(state.entries) == 1
        assert state.analytics["total"] == 1
    
    def test_has_entries_property(self, sample_app_state):
        """Test has_entries property."""
        assert sample_app_state.has_entries
        
        empty_state = AppState(entries=[], analytics={})
        assert not empty_state.has_entries
    
    def test_entry_count_property(self, sample_app_state):
        """Test entry_count property."""
        assert sample_app_state.entry_count == 1
    
    def test_successful_entries_property(self, sample_bibtex_entry, sample_error_entry):
        """Test successful_entries filtering."""
        state = AppState(
            entries=[sample_bibtex_entry, sample_error_entry],
            analytics={}
        )
        
        successful = state.successful_entries
        assert len(successful) == 1
        assert successful[0] is sample_bibtex_entry
    
    def test_failed_entries_property(self, sample_bibtex_entry, sample_error_entry):
        """Test failed_entries filtering."""
        state = AppState(
            entries=[sample_bibtex_entry, sample_error_entry],
            analytics={}
        )
        
        failed = state.failed_entries
        assert len(failed) == 1
        assert failed[0] is sample_error_entry
    
    def test_success_rate_calculation(self, sample_bibtex_entry, sample_error_entry):
        """Test success rate calculation."""
        # 100% success
        state_all_good = AppState(entries=[sample_bibtex_entry], analytics={})
        assert state_all_good.success_rate == 100.0
        
        # 50% success
        state_mixed = AppState(
            entries=[sample_bibtex_entry, sample_error_entry],
            analytics={}
        )
        assert state_mixed.success_rate == 50.0
        
        # 0% success (empty)
        state_empty = AppState(entries=[], analytics={})
        assert state_empty.success_rate == 0.0
    
    def test_get_cite_keys(self, sample_bibtex_entry):
        """Test citation key extraction."""
        state = AppState(entries=[sample_bibtex_entry], analytics={})
        keys = state.get_cite_keys()
        
        assert len(keys) == 1
        assert keys[0] == "smith2023"
        assert_citation_key_valid(keys[0])
    
    def test_get_bibtex_content(self, sample_bibtex_entry, sample_error_entry):
        """Test BibTeX content extraction (successful entries only)."""
        state = AppState(
            entries=[sample_bibtex_entry, sample_error_entry],
            analytics={}
        )
        
        content = state.get_bibtex_content()
        assert "@article{smith2023" in content
        assert "Error:" not in content  # Error entries excluded
    
    def test_update_entry_key(self, sample_bibtex_entry):
        """Test updating citation key."""
        state = AppState(entries=[sample_bibtex_entry], analytics={})
        
        # Update existing key
        success = state.update_entry_key("smith2023", "newkey2023")
        assert success
        assert state.entries[0].key == "newkey2023"
        assert "newkey2023" in state.entries[0].content
        
        # Try to update non-existent key
        failure = state.update_entry_key("nonexistent", "whatever")
        assert not failure


class TestStateManager:
    """Test StateManager class."""
    
    def test_load_empty_state(self, mock_streamlit_session):
        """Test loading state when session is empty."""
        with patch('streamlit.session_state', mock_streamlit_session):
            state = StateManager.load()
            assert isinstance(state, AppState)
            assert len(state.entries) == 0
            assert state.analytics == {}
    
    def test_load_existing_state(self, mock_streamlit_session, sample_bibtex_entry):
        """Test loading existing state from session."""
        # Set up session with existing data
        mock_streamlit_session[StateManager.ENTRIES_KEY] = [
            (sample_bibtex_entry.key, sample_bibtex_entry.content, sample_bibtex_entry.metadata)
        ]
        mock_streamlit_session[StateManager.ANALYTICS_KEY] = {"total": 1}
        
        with patch('streamlit.session_state', mock_streamlit_session):
            state = StateManager.load()
            
            assert len(state.entries) == 1
            assert state.entries[0].key == sample_bibtex_entry.key
            assert state.analytics["total"] == 1
    
    def test_load_legacy_format_migration(self, mock_streamlit_session, sample_bibtex_entry):
        """Test migration from legacy session state format."""
        # Set up legacy format
        mock_streamlit_session["entries"] = [
            (sample_bibtex_entry.key, sample_bibtex_entry.content, sample_bibtex_entry.metadata)
        ]
        mock_streamlit_session["analytics"] = {"total": 1}
        
        with patch('streamlit.session_state', mock_streamlit_session):
            state = StateManager.load()
            
            assert len(state.entries) == 1
            assert state.entries[0].key == sample_bibtex_entry.key
    
    def test_save_state(self, mock_streamlit_session, sample_app_state):
        """Test saving state to session."""
        with patch('streamlit.session_state', mock_streamlit_session):
            StateManager.save(sample_app_state)
            
            assert StateManager.ENTRIES_KEY in mock_streamlit_session
            assert StateManager.ANALYTICS_KEY in mock_streamlit_session
            
            # Check legacy keys for backward compatibility
            assert "entries" in mock_streamlit_session
            assert "analytics" in mock_streamlit_session
    
    def test_add_entries(self, mock_streamlit_session, sample_bibtex_entry):
        """Test adding new entries to state."""
        with patch('streamlit.session_state', mock_streamlit_session):
            # Add first entry
            new_entries = [sample_bibtex_entry]
            state = StateManager.add_entries(new_entries)
            
            assert len(state.entries) == 1
            assert state.entries[0].key == sample_bibtex_entry.key
            
            # Add another entry
            additional_entry = BibtexEntry("key2", "content2", {"doi": "10.2"})
            state2 = StateManager.add_entries([additional_entry])
            
            assert len(state2.entries) == 2
    
    def test_clear_entries(self, mock_streamlit_session, sample_app_state):
        """Test clearing all entries."""
        # Set up state with entries
        mock_streamlit_session[StateManager.ENTRIES_KEY] = [("key", "content", {})]
        mock_streamlit_session[StateManager.ANALYTICS_KEY] = {"total": 1}
        
        with patch('streamlit.session_state', mock_streamlit_session):
            state = StateManager.clear_entries()
            
            assert len(state.entries) == 0
            assert state.analytics == {}
    
    def test_update_analytics(self, mock_streamlit_session):
        """Test updating analytics data."""
        with patch('streamlit.session_state', mock_streamlit_session):
            new_analytics = {"total": 5, "years": [2020, 2021]}
            state = StateManager.update_analytics(new_analytics)
            
            assert state.analytics == new_analytics
    
    def test_update_entry_keys(self, mock_streamlit_session):
        """Test updating multiple entry keys."""
        # Create entries with original keys
        entries = generate_bibtex_entries(3)
        
        with patch('streamlit.session_state', mock_streamlit_session):
            StateManager.add_entries(entries)
            
            # Update keys
            key_mapping = {
                "test2020": "new2020",
                "test2021": "new2021" 
            }
            updated_state = StateManager.update_entry_keys(key_mapping)
            
            # Check keys were updated
            keys = updated_state.get_cite_keys()
            assert "new2020" in keys
            assert "new2021" in keys
            assert "test2022" in keys  # Unchanged


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_get_state(self, mock_streamlit_session):
        """Test get_state convenience function."""
        with patch('streamlit.session_state', mock_streamlit_session):
            with patch.object(StateManager, 'load') as mock_load:
                mock_load.return_value = AppState([], {})
                
                state = get_state()
                mock_load.assert_called_once()
                assert isinstance(state, AppState)


@pytest.mark.integration 
class TestStateIntegration:
    """Integration tests for state management."""
    
    def test_full_state_lifecycle(self, mock_streamlit_session):
        """Test complete state management lifecycle."""
        entries = generate_bibtex_entries(3)
        
        with patch('streamlit.session_state', mock_streamlit_session):
            # 1. Start with empty state
            state1 = get_state()
            assert state1.entry_count == 0
            
            # 2. Add entries
            state2 = StateManager.add_entries(entries)
            assert state2.entry_count == 3
            
            # 3. Update analytics
            analytics = {"total": 3, "success_rate": 100.0}
            state3 = StateManager.update_analytics(analytics)
            assert state3.analytics["total"] == 3
            
            # 4. Update keys
            key_mapping = {"test2020": "updated2020"}
            state4 = StateManager.update_entry_keys(key_mapping)
            keys = state4.get_cite_keys()
            assert "updated2020" in keys
            
            # 5. Clear all
            state5 = StateManager.clear_entries()
            assert state5.entry_count == 0
    
    def test_state_persistence_across_operations(self, mock_streamlit_session):
        """Test that state persists across multiple operations."""
        with patch('streamlit.session_state', mock_streamlit_session):
            # Add entries
            entries = generate_bibtex_entries(2)
            StateManager.add_entries(entries)
            
            # Load state in separate operation
            state = get_state()
            assert state.entry_count == 2
            
            # Update analytics
            StateManager.update_analytics({"processed": 2})
            
            # Load again
            state2 = get_state()
            assert state2.entry_count == 2
            assert state2.analytics["processed"] == 2


@pytest.mark.performance
class TestStatePerformance:
    """Performance tests for state management."""
    
    def test_large_state_operations(self, mock_streamlit_session, performance_timer):
        """Test performance with large number of entries."""
        with patch('streamlit.session_state', mock_streamlit_session):
            # Create many entries
            large_entry_set = generate_bibtex_entries(100)
            
            performance_timer.start()
            
            # Add all entries
            state = StateManager.add_entries(large_entry_set)
            
            # Perform state operations
            keys = state.get_cite_keys()
            content = state.get_bibtex_content()
            successful = state.successful_entries
            
            performance_timer.stop()
            
            # Should handle 100 entries quickly
            assert len(keys) == 100
            assert len(successful) == 100
            assert performance_timer.elapsed < 1.0  # Less than 1 second
    
    def test_key_update_performance(self, mock_streamlit_session, performance_timer):
        """Test performance of key updates."""
        with patch('streamlit.session_state', mock_streamlit_session):
            entries = generate_bibtex_entries(50)
            StateManager.add_entries(entries)
            
            # Create key mapping for all entries
            key_mapping = {f"test{2020+i}": f"updated{2020+i}" for i in range(50)}
            
            performance_timer.start()
            StateManager.update_entry_keys(key_mapping)
            performance_timer.stop()
            
            # Should update 50 keys quickly
            assert performance_timer.elapsed < 0.5  # Less than 0.5 seconds
