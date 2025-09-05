"""
Tests for configuration management module.
"""

import pytest
from unittest.mock import Mock, patch

from core.config import AppConfig, ConfigManager, get_config, update_config
from core.exceptions import ConfigurationError


class TestAppConfig:
    """Test AppConfig dataclass."""
    
    def test_default_config_creation(self):
        """Test creating config with default values."""
        config = AppConfig()
        assert config.theme == "light"
        assert config.batch_size == 50
        assert config.timeout == 10
        assert config.max_retries == 3
        assert config.validate_dois == True
    
    def test_custom_config_creation(self):
        """Test creating config with custom values."""
        config = AppConfig(
            theme="dark",
            batch_size=25,
            timeout=15,
            key_pattern="first_author_title_year"
        )
        assert config.theme == "dark"
        assert config.batch_size == 25
        assert config.timeout == 15
        assert config.key_pattern == "first_author_title_year"
    
    def test_config_validation_batch_size_too_small(self):
        """Test validation fails for batch size too small."""
        with pytest.raises(ValueError, match="Batch size must be between 1 and 500"):
            AppConfig(batch_size=0)
    
    def test_config_validation_batch_size_too_large(self):
        """Test validation fails for batch size too large."""
        with pytest.raises(ValueError, match="Batch size must be between 1 and 500"):
            AppConfig(batch_size=501)
    
    def test_config_validation_timeout_too_small(self):
        """Test validation fails for timeout too small."""
        with pytest.raises(ValueError, match="Timeout must be between 5 and 60"):
            AppConfig(timeout=4)
    
    def test_config_validation_timeout_too_large(self):
        """Test validation fails for timeout too large."""
        with pytest.raises(ValueError, match="Timeout must be between 5 and 60"):
            AppConfig(timeout=61)
    
    def test_config_validation_max_retries_invalid(self):
        """Test validation fails for invalid max retries."""
        with pytest.raises(ValueError, match="Max retries must be between 1 and 10"):
            AppConfig(max_retries=0)
    
    def test_config_validation_invalid_fields_in_order(self):
        """Test validation fails for invalid fields in field_order."""
        with pytest.raises(ValueError, match="Invalid fields in field_order"):
            AppConfig(field_order=["title", "invalid_field", "author"])
    
    def test_field_order_copy_behavior(self):
        """Test that field_order is properly copied."""
        config1 = AppConfig()
        config2 = AppConfig()
        
        # Modify one config's field order
        config1.field_order.append("new_field")  # This should fail validation
        
        # But before validation, ensure they start as separate lists
        assert config1.field_order is not config2.field_order


class TestConfigManager:
    """Test ConfigManager class."""
    
    def test_load_creates_default_if_not_exists(self, mock_streamlit_session):
        """Test that load creates default config if none exists."""
        with patch('streamlit.session_state', mock_streamlit_session):
            config = ConfigManager.load()
            assert isinstance(config, AppConfig)
            assert config.theme == "light"  # default value
    
    def test_load_returns_existing_config(self, mock_streamlit_session, sample_config):
        """Test that load returns existing config from session state."""
        mock_streamlit_session[ConfigManager.SESSION_KEY] = sample_config
        
        with patch('streamlit.session_state', mock_streamlit_session):
            config = ConfigManager.load()
            assert config is sample_config
    
    def test_save_stores_config(self, mock_streamlit_session, sample_config):
        """Test that save stores config in session state."""
        with patch('streamlit.session_state', mock_streamlit_session):
            ConfigManager.save(sample_config)
            assert mock_streamlit_session[ConfigManager.SESSION_KEY] is sample_config
    
    def test_save_validates_config(self, mock_streamlit_session):
        """Test that save validates config before storing."""
        bad_config = AppConfig(batch_size=1000)  # Invalid
        bad_config._validate = Mock(side_effect=ValueError("Invalid config"))
        
        with patch('streamlit.session_state', mock_streamlit_session):
            with patch('streamlit.error') as mock_error:
                with pytest.raises(ValueError):
                    ConfigManager.save(bad_config)
                mock_error.assert_called_once()
    
    def test_update_changes_values(self, mock_streamlit_session, sample_config):
        """Test that update changes configuration values."""
        mock_streamlit_session[ConfigManager.SESSION_KEY] = sample_config
        
        with patch('streamlit.session_state', mock_streamlit_session):
            new_config = ConfigManager.update(theme="dark", batch_size=25)
            
            assert new_config.theme == "dark"
            assert new_config.batch_size == 25
            assert new_config.timeout == sample_config.timeout  # unchanged
    
    def test_update_validates_new_config(self, mock_streamlit_session, sample_config):
        """Test that update validates the new configuration."""
        mock_streamlit_session[ConfigManager.SESSION_KEY] = sample_config
        
        with patch('streamlit.session_state', mock_streamlit_session):
            with patch('streamlit.error') as mock_error:
                # Try to update with invalid value
                result = ConfigManager.update(batch_size=1000)
                
                # Should return original config unchanged
                assert result.batch_size == sample_config.batch_size
                mock_error.assert_called_once()
    
    def test_reset_creates_default_config(self, mock_streamlit_session, sample_config):
        """Test that reset creates a new default configuration."""
        mock_streamlit_session[ConfigManager.SESSION_KEY] = sample_config
        
        with patch('streamlit.session_state', mock_streamlit_session):
            new_config = ConfigManager.reset()
            
            assert new_config.theme == "light"  # default
            assert new_config.batch_size == 50  # default
            assert mock_streamlit_session[ConfigManager.SESSION_KEY] is new_config


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_get_config(self, mock_streamlit_session):
        """Test get_config convenience function."""
        with patch('streamlit.session_state', mock_streamlit_session):
            with patch.object(ConfigManager, 'load') as mock_load:
                mock_load.return_value = AppConfig()
                
                config = get_config()
                mock_load.assert_called_once()
                assert isinstance(config, AppConfig)
    
    def test_update_config(self, mock_streamlit_session):
        """Test update_config convenience function."""  
        with patch('streamlit.session_state', mock_streamlit_session):
            with patch.object(ConfigManager, 'update') as mock_update:
                mock_update.return_value = AppConfig()
                
                config = update_config(theme="dark")
                mock_update.assert_called_once_with(theme="dark")
                assert isinstance(config, AppConfig)


@pytest.mark.integration
class TestConfigIntegration:
    """Integration tests for configuration system."""
    
    def test_full_config_lifecycle(self, mock_streamlit_session):
        """Test complete configuration lifecycle."""
        with patch('streamlit.session_state', mock_streamlit_session):
            # 1. Load initial config (should create default)
            config1 = get_config()
            assert config1.theme == "light"
            
            # 2. Update config
            config2 = update_config(theme="dark", batch_size=25)
            assert config2.theme == "dark"
            assert config2.batch_size == 25
            
            # 3. Load again (should return updated config)
            config3 = get_config()
            assert config3.theme == "dark"
            assert config3.batch_size == 25
            
            # 4. Reset config
            config4 = ConfigManager.reset()
            assert config4.theme == "light"
            assert config4.batch_size == 50
    
    def test_config_persistence_across_sessions(self):
        """Test that config persists across different session states."""
        session1 = {}
        session2 = {}
        
        # Create config in first session
        with patch('streamlit.session_state', session1):
            config1 = update_config(theme="dark")
            assert session1[ConfigManager.SESSION_KEY].theme == "dark"
        
        # Copy config to second session (simulates Streamlit behavior)
        session2[ConfigManager.SESSION_KEY] = session1[ConfigManager.SESSION_KEY]
        
        # Load config in second session
        with patch('streamlit.session_state', session2):
            config2 = get_config()
            assert config2.theme == "dark"


@pytest.mark.performance
class TestConfigPerformance:
    """Performance tests for configuration system."""
    
    def test_config_creation_performance(self, performance_timer):
        """Test config creation performance."""
        performance_timer.start()
        
        # Create many configs
        for _ in range(1000):
            AppConfig()
        
        performance_timer.stop()
        
        # Should be very fast (less than 100ms for 1000 configs)
        assert performance_timer.elapsed < 0.1
    
    def test_config_validation_performance(self, performance_timer):
        """Test config validation performance."""
        config = AppConfig()
        
        performance_timer.start()
        
        # Validate many times
        for _ in range(1000):
            config._validate()
        
        performance_timer.stop()
        
        # Should be very fast
        assert performance_timer.elapsed < 0.05
