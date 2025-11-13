"""
Configuration management for DOI2BibTex application.

This module provides type-safe configuration management with validation
and default values, replacing the scattered session state dictionary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Dict, Any
import streamlit as st


DEFAULT_FIELD_ORDER = [
    "title",
    "author",
    "journal",
    "volume",
    "number",
    "pages",
    "year",
    "publisher",
    "DOI",
    "ISSN",
    "url",
    "month",
]

ThemeType = Literal["light", "gray", "dark"]
KeyPatternType = Literal["author_year", "first_author_title_year", "journal_year"]
StyleType = Literal["APA", "MLA", "Chicago", "None"]


@dataclass
class AppConfig:
    """Application configuration with validation and type safety."""
    
    # UI Settings
    theme: ThemeType = "light"
    show_progress: bool = False
    
    # Processing Settings
    batch_size: int = 50
    remove_duplicates: bool = True
    validate_dois: bool = True
    include_quality: bool = True
    normalize_authors: bool = True
    include_abstracts: bool = False
    fetch_abstracts: bool = False
    use_abbrev_journal: bool = False
    
    # Citation Settings
    field_order: List[str] = field(default_factory=lambda: DEFAULT_FIELD_ORDER.copy())
    key_pattern: KeyPatternType = "author_year"
    style_preview: StyleType = "APA"
    
    # Network Settings
    timeout: int = 10
    max_retries: int = 3
    concurrency: int = 1
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """Validate configuration values and raise errors for invalid settings."""
        if not 1 <= self.batch_size <= 500:
            raise ValueError(f"Batch size must be between 1 and 500, got {self.batch_size}")
        
        if self.batch_size > 100:
            # This will be shown as a warning in the UI
            pass
            
        if not 5 <= self.timeout <= 60:
            raise ValueError(f"Timeout must be between 5 and 60 seconds, got {self.timeout}")
            
        if not 1 <= self.max_retries <= 10:
            raise ValueError(f"Max retries must be between 1 and 10, got {self.max_retries}")
            
        if not 1 <= self.concurrency <= 10:
            raise ValueError(f"Concurrency must be between 1 and 10, got {self.concurrency}")
            
        # Validate field order contains valid fields
        valid_fields = set(DEFAULT_FIELD_ORDER)
        invalid_fields = [f for f in self.field_order if f not in valid_fields]
        if invalid_fields:
            raise ValueError(f"Invalid fields in field_order: {invalid_fields}")


class ConfigManager:
    """Manages application configuration with Streamlit session state integration."""
    
    SESSION_KEY = "app_config"
    
    @classmethod
    def load(cls) -> AppConfig:
        """Load configuration from Streamlit session state or create default."""
        if cls.SESSION_KEY not in st.session_state:
            st.session_state[cls.SESSION_KEY] = AppConfig()
        return st.session_state[cls.SESSION_KEY]
    
    @classmethod
    def save(cls, config: AppConfig) -> None:
        """Save configuration to Streamlit session state."""
        try:
            config._validate()
            st.session_state[cls.SESSION_KEY] = config
        except ValueError as e:
            st.error(f"Configuration error: {e}")
            raise
    
    @classmethod
    def update(cls, **kwargs) -> AppConfig:
        """Update specific configuration values."""
        config = cls.load()
        
        # Create a new config with updated values
        config_dict = config.__dict__.copy()
        config_dict.update(kwargs)
        
        try:
            new_config = AppConfig(**config_dict)
            cls.save(new_config)
            return new_config
        except (ValueError, TypeError) as e:
            st.error(f"Invalid configuration update: {e}")
            return config
    
    @classmethod
    def reset(cls) -> AppConfig:
        """Reset configuration to defaults."""
        config = AppConfig()
        cls.save(config)
        return config


def get_config() -> AppConfig:
    """Convenience function to get current configuration."""
    return ConfigManager.load()


def update_config(**kwargs) -> AppConfig:
    """Convenience function to update configuration."""
    return ConfigManager.update(**kwargs)
