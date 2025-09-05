"""
Tests for DOI processing module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from core.processor import DOIProcessor, create_processor, ProcessingResult
from core.state import BibtexEntry
from core.exceptions import DOIError, NetworkError, DOINotFoundError


class TestDOIProcessor:
    """Test DOIProcessor class."""
    
    def test_processor_creation(self, sample_config):
        """Test creating DOI processor."""
        processor = DOIProcessor(sample_config)
        assert processor.config is sample_config
        assert processor.config.batch_size == sample_config.batch_size
    
    def test_parse_input_text_only(self, processor_with_mocks):
        """Test parsing DOIs from text input only."""
        text_input = "10.1038/nature12373\n10.1126/science.1234567,10.1145/3292500.3330701"
        
        dois = processor_with_mocks.parse_input(text_input, None)
        
        assert len(dois) == 3
        assert "10.1038/nature12373" in dois
        assert "10.1126/science.1234567" in dois
        assert "10.1145/3292500.3330701" in dois
    
    def test_parse_input_file_only(self, processor_with_mocks, mock_uploaded_file):
        """Test parsing DOIs from uploaded file only."""
        with patch('core.processor.safe_file_read') as mock_read:
            mock_read.return_value = "10.1038/nature12373\n10.1126/science.1234567"
            
            dois = processor_with_mocks.parse_input("", mock_uploaded_file)
            
            assert len(dois) == 2
            assert "10.1038/nature12373" in dois
            mock_read.assert_called_once_with(mock_uploaded_file)
    
    def test_parse_input_combined(self, processor_with_mocks, mock_uploaded_file):
        """Test parsing DOIs from both text and file."""
        text_input = "10.1038/nature12373"
        
        with patch('core.processor.safe_file_read') as mock_read:
            mock_read.return_value = "10.1126/science.1234567"
            
            dois = processor_with_mocks.parse_input(text_input, mock_uploaded_file)
            
            assert len(dois) == 2
            assert "10.1038/nature12373" in dois
            assert "10.1126/science.1234567" in dois
    
    def test_parse_input_with_validation_enabled(self, sample_config):
        """Test parsing with DOI validation enabled."""
        sample_config.validate_dois = True
        processor = DOIProcessor(sample_config)
        
        text_input = "10.1038/nature12373\ninvalid.doi\n10.1126/science.1234567"
        
        with patch('core.processor.is_valid_doi') as mock_valid:
            mock_valid.side_effect = lambda doi: doi.startswith('10.')
            
            dois = processor.parse_input(text_input, None)
            
            # Only valid DOIs should be returned
            assert len(dois) == 2
            assert "invalid.doi" not in dois
    
    def test_parse_input_validation_disabled(self, sample_config):
        """Test parsing with DOI validation disabled."""
        sample_config.validate_dois = False
        processor = DOIProcessor(sample_config)
        
        text_input = "10.1038/nature12373\ninvalid.doi"
        
        dois = processor.parse_input(text_input, None)
        
        # All DOIs should be returned, even invalid ones
        assert len(dois) == 2
        assert "invalid.doi" in dois
    
    def test_fetch_bibtex_success(self, processor_with_mocks, mock_http_response):
        """Test successful BibTeX fetching."""
        doi = "10.1234/test"
        
        # Mock the HTTP request
        with patch('core.processor.get_with_retry') as mock_get:
            mock_get.return_value = (mock_http_response, None)
            
            with patch('core.processor.extract_bibtex_fields') as mock_extract:
                mock_extract.return_value = {
                    "title": "Test Article",
                    "author": "Test Author",
                    "year": "2023"
                }
                
                with patch('core.processor.make_key') as mock_key:
                    mock_key.return_value = "test2023"
                    
                    entry = processor_with_mocks.fetch_bibtex(doi)
                    
                    assert isinstance(entry, BibtexEntry)
                    assert entry.key == "test2023"
                    assert "@article" in entry.content
                    assert entry.metadata["status"] == "ok"
                    assert entry.metadata["doi"] == doi
    
    def test_fetch_bibtex_network_error(self, processor_with_mocks):
        """Test BibTeX fetching with network error."""
        doi = "10.1234/test"
        
        with patch('core.processor.get_with_retry') as mock_get:
            mock_get.return_value = (None, "Connection timeout")
            
            with pytest.raises(NetworkError):
                processor_with_mocks.fetch_bibtex(doi)
    
    def test_fetch_bibtex_404_error(self, processor_with_mocks):
        """Test BibTeX fetching with 404 error."""
        doi = "10.9999/nonexistent"
        mock_response = Mock()
        mock_response.status_code = 404
        
        with patch('core.processor.get_with_retry') as mock_get:
            mock_get.return_value = (mock_response, None)
            
            with pytest.raises(DOINotFoundError):
                processor_with_mocks.fetch_bibtex(doi)
    
    def test_fetch_bibtex_with_crossref_enrichment(self, sample_config, mock_crossref_response):
        """Test BibTeX fetching with Crossref data enrichment."""
        sample_config.fetch_abstracts = True
        sample_config.use_abbrev_journal = True
        processor = DOIProcessor(sample_config)
        
        doi = "10.1234/test"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"@article{test, title={Test}}"
        
        with patch('core.processor.get_with_retry') as mock_get:
            mock_get.return_value = (mock_response, None)
            
            with patch('core.processor.get_json_with_retry') as mock_json:
                mock_json.return_value = (mock_crossref_response, None)
                
                with patch('core.processor.extract_bibtex_fields') as mock_extract:
                    mock_extract.return_value = {"title": "Test", "author": "Test Author"}
                    
                    with patch('core.processor.make_key') as mock_key:
                        mock_key.return_value = "test2023"
                        
                        entry = processor.fetch_bibtex(doi)
                        
                        # Should have made both HTTP and JSON requests
                        mock_get.assert_called_once()
                        mock_json.assert_called_once()
    
    def test_process_batch_success(self, processor_with_mocks, sample_dois):
        """Test successful batch processing."""
        # Mock fetch_bibtex to return successful entries
        mock_entries = []
        for i, doi in enumerate(sample_dois):
            entry = BibtexEntry(
                key=f"test{i}",
                content=f"@article{{test{i}, title={{Test {i}}}}}",
                metadata={"doi": doi, "status": "ok"}
            )
            mock_entries.append(entry)
        
        processor_with_mocks.fetch_bibtex = Mock(side_effect=mock_entries)
        
        with patch('core.processor.summarize') as mock_summarize:
            mock_summarize.return_value = {"total": 3}
            
            result = processor_with_mocks.process_batch(sample_dois)
            
            assert isinstance(result, ProcessingResult)
            assert result.successful_count == 3
            assert result.failed_count == 0
            assert len(result.entries) == 3
            assert result.analytics["total"] == 3
    
    def test_process_batch_with_failures(self, processor_with_mocks, sample_dois):
        """Test batch processing with some failures."""
        def mock_fetch(doi):
            if doi == sample_dois[1]:  # Second DOI fails
                raise NetworkError("Network timeout", doi)
            return BibtexEntry(
                key=f"success_{doi.replace('.', '_')}",
                content=f"@article{{success, title={{Success for {doi}}}}}",
                metadata={"doi": doi, "status": "ok"}
            )
        
        processor_with_mocks.fetch_bibtex = Mock(side_effect=mock_fetch)
        
        with patch('core.processor.summarize') as mock_summarize:
            mock_summarize.return_value = {"total": 2}
            
            result = processor_with_mocks.process_batch(sample_dois)
            
            assert result.successful_count == 2
            assert result.failed_count == 1
            assert len(result.failed_dois) == 1
            assert sample_dois[1] in result.failed_dois
    
    def test_process_batch_with_progress_callback(self, processor_with_mocks, sample_dois):
        """Test batch processing with progress callback."""
        processor_with_mocks.fetch_bibtex = Mock(return_value=BibtexEntry(
            "key", "content", {"doi": "test", "status": "ok"}
        ))
        
        progress_calls = []
        def progress_callback(current, total, doi):
            progress_calls.append((current, total, doi))
        
        with patch('core.processor.summarize') as mock_summarize:
            mock_summarize.return_value = {}
            
            processor_with_mocks.process_batch(sample_dois, progress_callback)
            
            assert len(progress_calls) == len(sample_dois)
            assert progress_calls[0] == (1, 3, sample_dois[0])
            assert progress_calls[-1] == (3, 3, sample_dois[-1])
    
    def test_process_batch_empty_list(self, processor_with_mocks):
        """Test batch processing with empty DOI list."""
        result = processor_with_mocks.process_batch([])
        
        assert result.successful_count == 0
        assert result.failed_count == 0
        assert len(result.entries) == 0
        assert result.analytics == {}
    
    def test_process_batch_duplicate_removal(self, sample_config, sample_dois):
        """Test batch processing with duplicate removal."""
        sample_config.remove_duplicates = True
        processor = DOIProcessor(sample_config)
        
        # Mock successful fetches
        processor.fetch_bibtex = Mock(return_value=BibtexEntry(
            "duplicate", "content", {"doi": "test", "status": "ok"}
        ))
        
        with patch('core.processor.find_duplicates') as mock_duplicates:
            mock_duplicates.return_value = [1]  # Second entry is duplicate
            
            with patch('core.processor.summarize') as mock_summarize:
                mock_summarize.return_value = {}
                
                result = processor.process_batch(sample_dois)
                
                # Should have removed 1 duplicate
                mock_duplicates.assert_called_once()
                assert len(result.entries) == 2  # 3 - 1 duplicate
    
    def test_upsert_bibtex_field_new_field(self, processor_with_mocks):
        """Test inserting new field into BibTeX entry."""
        bibtex = "@article{test2023,\n  title = {Test Title}\n}"
        
        result = processor_with_mocks._upsert_bibtex_field(bibtex, "author", "Test Author")
        
        assert "author = {Test Author}" in result
        assert "title = {Test Title}" in result
    
    def test_upsert_bibtex_field_update_existing(self, processor_with_mocks):
        """Test updating existing field in BibTeX entry."""
        bibtex = "@article{test2023,\n  title = {Old Title},\n  author = {Old Author}\n}"
        
        result = processor_with_mocks._upsert_bibtex_field(bibtex, "title", "New Title")
        
        assert "title = {New Title}" in result
        assert "Old Title" not in result
        assert "author = {Old Author}" in result
    
    def test_upsert_bibtex_field_empty_value(self, processor_with_mocks):
        """Test upserting with empty value (should do nothing)."""
        bibtex = "@article{test2023,\n  title = {Test Title}\n}"
        
        result = processor_with_mocks._upsert_bibtex_field(bibtex, "author", "")
        
        assert result == bibtex  # Should be unchanged


class TestCreateProcessor:
    """Test processor factory function."""
    
    def test_create_processor(self, sample_config):
        """Test creating processor with factory function."""
        processor = create_processor(sample_config)
        
        assert isinstance(processor, DOIProcessor)
        assert processor.config is sample_config


@pytest.mark.integration
class TestProcessorIntegration:
    """Integration tests for DOI processor."""
    
    def test_full_processing_workflow(self, sample_config, sample_dois):
        """Test complete DOI processing workflow."""
        processor = create_processor(sample_config)
        
        # Mock all external dependencies
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"@article{test, title={Mock Test}}"
        
        with patch('core.processor.get_with_retry') as mock_get:
            mock_get.return_value = (mock_response, None)
            
            with patch('core.processor.extract_bibtex_fields') as mock_extract:
                mock_extract.return_value = {
                    "title": "Mock Test",
                    "author": "Mock Author",
                    "year": "2023"
                }
                
                with patch('core.processor.make_key') as mock_key:
                    mock_key.return_value = "mocktest2023"
                    
                    with patch('core.processor.summarize') as mock_summarize:
                        mock_summarize.return_value = {"total": len(sample_dois)}
                        
                        # Process the batch
                        result = processor.process_batch(sample_dois)
                        
                        assert result.successful_count == len(sample_dois)
                        assert result.failed_count == 0
                        assert len(result.entries) == len(sample_dois)
    
    def test_error_handling_integration(self, sample_config):
        """Test error handling in processing workflow."""
        processor = create_processor(sample_config)
        
        # Mix of valid and invalid DOIs
        mixed_dois = ["10.1038/valid", "invalid.doi", "10.1126/valid2"]
        
        def mock_fetch(doi):
            if "invalid" in doi:
                raise DOIError("Invalid DOI", doi)
            return BibtexEntry("valid", "content", {"doi": doi, "status": "ok"})
        
        processor.fetch_bibtex = Mock(side_effect=mock_fetch)
        
        with patch('core.processor.summarize') as mock_summarize:
            mock_summarize.return_value = {}
            
            result = processor.process_batch(mixed_dois)
            
            assert result.successful_count == 2
            assert result.failed_count == 1
            assert "invalid.doi" in result.failed_dois


@pytest.mark.performance
class TestProcessorPerformance:
    """Performance tests for DOI processor."""
    
    def test_batch_processing_performance(self, sample_config, performance_timer):
        """Test performance of batch processing."""
        processor = create_processor(sample_config)
        
        # Create many DOIs
        many_dois = [f"10.1234/test{i}" for i in range(100)]
        
        # Mock fast processing
        processor.fetch_bibtex = Mock(return_value=BibtexEntry(
            "fast", "content", {"doi": "test", "status": "ok"}
        ))
        
        with patch('core.processor.summarize') as mock_summarize:
            mock_summarize.return_value = {}
            
            performance_timer.start()
            result = processor.process_batch(many_dois)
            performance_timer.stop()
            
            # Should process 100 DOIs quickly (mocked, but tests overhead)
            assert result.successful_count == 100
            assert performance_timer.elapsed < 2.0  # Less than 2 seconds
    
    def test_input_parsing_performance(self, sample_config, performance_timer):
        """Test performance of input parsing."""
        processor = create_processor(sample_config)
        
        # Create large text input
        large_input = "\n".join(f"10.1234/test{i}" for i in range(1000))
        
        performance_timer.start()
        dois = processor.parse_input(large_input, None)
        performance_timer.stop()
        
        assert len(dois) == 1000
        assert performance_timer.elapsed < 0.1  # Very fast parsing
