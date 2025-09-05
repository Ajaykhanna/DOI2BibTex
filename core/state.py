"""
Application state management for DOI2BibTex.

This module provides type-safe state management for bibliography entries
and analytics, replacing direct session state manipulation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional
import streamlit as st


@dataclass
class BibtexEntry:
    """Represents a single BibTeX entry with metadata."""
    key: str
    content: str
    metadata: Dict[str, Any]
    
    @property
    def doi(self) -> Optional[str]:
        """Extract DOI from metadata."""
        return self.metadata.get("doi")
    
    @property
    def title(self) -> Optional[str]:
        """Extract title from metadata."""
        return self.metadata.get("title")
    
    @property
    def year(self) -> Optional[int]:
        """Extract publication year from metadata."""
        year_str = self.metadata.get("year")
        if year_str:
            try:
                return int(year_str)
            except (ValueError, TypeError):
                pass
        return None
    
    @property
    def has_error(self) -> bool:
        """Check if entry has an error status."""
        return self.metadata.get("status") == "error"
    
    @property
    def error_message(self) -> Optional[str]:
        """Get error message if entry has error status."""
        if self.has_error:
            return self.metadata.get("error")
        return None


@dataclass 
class AppState:
    """Application state container."""
    entries: List[BibtexEntry]
    analytics: Dict[str, Any]
    
    @property
    def has_entries(self) -> bool:
        """Check if there are any entries."""
        return len(self.entries) > 0
    
    @property
    def entry_count(self) -> int:
        """Get total number of entries."""
        return len(self.entries)
    
    @property
    def successful_entries(self) -> List[BibtexEntry]:
        """Get entries that were successfully processed."""
        return [entry for entry in self.entries if not entry.has_error]
    
    @property
    def failed_entries(self) -> List[BibtexEntry]:
        """Get entries that failed to process."""
        return [entry for entry in self.entries if entry.has_error]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if not self.entries:
            return 0.0
        return (len(self.successful_entries) / len(self.entries)) * 100
    
    def get_cite_keys(self) -> List[str]:
        """Get list of citation keys from all entries."""
        return [entry.key for entry in self.entries]
    
    def get_bibtex_content(self) -> str:
        """Get combined BibTeX content from all successful entries."""
        successful = self.successful_entries
        return "\n\n".join(entry.content for entry in successful)
    
    def update_entry_key(self, old_key: str, new_key: str) -> bool:
        """Update citation key for an entry."""
        from core.export import safe_replace_key
        
        for entry in self.entries:
            if entry.key == old_key:
                entry.key = new_key
                entry.content = safe_replace_key(entry.content, old_key, new_key)
                entry.metadata["key"] = new_key
                return True
        return False


class StateManager:
    """Manages application state with Streamlit session state integration."""
    
    ENTRIES_KEY = "app_entries"
    ANALYTICS_KEY = "app_analytics"
    
    @classmethod
    def load(cls) -> AppState:
        """Load application state from Streamlit session state."""
        # Load entries (convert from legacy format if needed)
        if cls.ENTRIES_KEY in st.session_state:
            raw_entries = st.session_state[cls.ENTRIES_KEY]
        elif "entries" in st.session_state:
            # Legacy format migration
            raw_entries = st.session_state["entries"]
        else:
            raw_entries = []
        
        # Convert to BibtexEntry objects
        entries = []
        for item in raw_entries:
            if isinstance(item, tuple) and len(item) == 3:
                key, content, metadata = item
                entries.append(BibtexEntry(key=key, content=content, metadata=metadata))
            elif isinstance(item, BibtexEntry):
                entries.append(item)
        
        # Load analytics
        if cls.ANALYTICS_KEY in st.session_state:
            analytics = st.session_state[cls.ANALYTICS_KEY]
        elif "analytics" in st.session_state:
            # Legacy format migration
            analytics = st.session_state["analytics"]
        else:
            analytics = {}
            
        return AppState(entries=entries, analytics=analytics)
    
    @classmethod
    def save(cls, state: AppState) -> None:
        """Save application state to Streamlit session state."""
        # Convert entries back to tuple format for compatibility
        entry_tuples = [(e.key, e.content, e.metadata) for e in state.entries]
        
        st.session_state[cls.ENTRIES_KEY] = entry_tuples
        st.session_state[cls.ANALYTICS_KEY] = state.analytics
        
        # Also update legacy keys for backward compatibility
        st.session_state["entries"] = entry_tuples
        st.session_state["analytics"] = state.analytics
    
    @classmethod
    def add_entries(cls, new_entries: List[BibtexEntry]) -> AppState:
        """Add new entries to the application state."""
        state = cls.load()
        state.entries.extend(new_entries)
        cls.save(state)
        return state
    
    @classmethod
    def clear_entries(cls) -> AppState:
        """Clear all entries from application state."""
        state = cls.load()
        state.entries = []
        state.analytics = {}
        cls.save(state)
        return state
    
    @classmethod
    def update_analytics(cls, analytics: Dict[str, Any]) -> AppState:
        """Update analytics data."""
        state = cls.load()
        state.analytics = analytics
        cls.save(state)
        return state
    
    @classmethod
    def update_entry_keys(cls, key_mapping: Dict[str, str]) -> AppState:
        """Update multiple entry keys at once."""
        state = cls.load()
        
        for old_key, new_key in key_mapping.items():
            state.update_entry_key(old_key, new_key)
        
        cls.save(state)
        return state


def get_state() -> AppState:
    """Convenience function to get current application state."""
    return StateManager.load()


def save_state(state: AppState) -> None:
    """Convenience function to save application state."""
    StateManager.save(state)
