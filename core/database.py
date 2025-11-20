"""
Database/Persistence Layer for DOI2BibTeX application.

This module provides SQLAlchemy-based database management for persistent
storage of DOI entries, enabling:
- Offline mode capability
- History tracking
- Reduced API calls via database caching
- Export/import functionality
- Usage analytics

Phase 4.1 Implementation
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    Text,
    Integer,
    Float,
    Boolean,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

Base = declarative_base()


class DOIEntry(Base):
    """
    Database model for DOI entries.

    Stores fetched DOI metadata and BibTeX data for offline access,
    history tracking, and reduced API calls.
    """

    __tablename__ = "doi_entries"

    # Primary key
    doi = Column(String(255), primary_key=True, index=True)

    # Bibliography data
    bibtex = Column(Text, nullable=False)
    source = Column(String(50), nullable=False)  # Crossref, DataCite, DOI.org

    # Metadata (stored as JSON string)
    metadata_json = Column(Text, nullable=True)

    # Quality metrics
    quality_score = Column(Float, nullable=True)
    has_abstract = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Access tracking
    access_count = Column(Integer, default=1)

    def __repr__(self) -> str:
        return f"<DOIEntry(doi='{self.doi}', source='{self.source}', created='{self.created_at}')>"

    @property
    def metadata(self) -> Dict[str, Any]:
        """Parse and return metadata from JSON string."""
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse metadata for DOI {self.doi}")
                return {}
        return {}

    @metadata.setter
    def metadata(self, value: Dict[str, Any]) -> None:
        """Store metadata as JSON string."""
        if value:
            self.metadata_json = json.dumps(value)
        else:
            self.metadata_json = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary for serialization."""
        return {
            "doi": self.doi,
            "bibtex": self.bibtex,
            "source": self.source,
            "metadata": self.metadata,
            "quality_score": self.quality_score,
            "has_abstract": self.has_abstract,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "access_count": self.access_count,
        }


class DOIDatabase:
    """
    Database manager for DOI entries with SQLite/PostgreSQL support.

    Provides CRUD operations, statistics, and maintenance functionality
    for persistent DOI storage.

    Example:
        >>> db = DOIDatabase("doi2bibtex.db")
        >>> db.save_entry("10.1038/nature12373", bibtex_str, {"title": "..."}, "Crossref")
        >>> entry = db.get_entry("10.1038/nature12373")
        >>> print(entry.bibtex)
    """

    def __init__(
        self,
        db_path: str | Path = "doi2bibtex.db",
        echo: bool = False,
        create_tables: bool = True,
    ):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file or PostgreSQL connection string
            echo: Enable SQL query logging
            create_tables: Automatically create tables if they don't exist
        """
        self.db_path = Path(db_path) if isinstance(db_path, str) else db_path

        # Determine if PostgreSQL or SQLite
        if str(db_path).startswith("postgresql://"):
            # PostgreSQL connection
            self.engine = create_engine(str(db_path), echo=echo)
        else:
            # SQLite connection
            connect_args = {"check_same_thread": False}
            self.engine = create_engine(
                f"sqlite:///{self.db_path}",
                echo=echo,
                connect_args=connect_args,
                poolclass=StaticPool,
            )

        # Create tables if requested
        if create_tables:
            Base.metadata.create_all(self.engine)
            logger.info(f"Database initialized at {db_path}")

        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def get_entry(self, doi: str) -> Optional[DOIEntry]:
        """
        Retrieve DOI entry from database.

        Args:
            doi: DOI identifier

        Returns:
            DOIEntry if found, None otherwise
        """
        with self.get_session() as session:
            entry = session.query(DOIEntry).filter_by(doi=doi).first()

            if entry:
                # Update access tracking
                entry.last_accessed = datetime.utcnow()
                entry.access_count += 1
                session.commit()
                session.refresh(entry)

            return entry

    def save_entry(
        self,
        doi: str,
        bibtex: str,
        metadata: Dict[str, Any],
        source: str,
        quality_score: Optional[float] = None,
        has_abstract: bool = False,
    ) -> DOIEntry:
        """
        Save or update DOI entry in database.

        Args:
            doi: DOI identifier
            bibtex: BibTeX string
            metadata: Metadata dictionary
            source: Source name (Crossref, DataCite, DOI.org)
            quality_score: Optional quality score
            has_abstract: Whether entry includes abstract

        Returns:
            Saved DOIEntry object
        """
        with self.get_session() as session:
            # Check if entry exists
            entry = session.query(DOIEntry).filter_by(doi=doi).first()

            if entry:
                # Update existing entry
                entry.bibtex = bibtex
                entry.metadata = metadata
                entry.source = source
                entry.quality_score = quality_score
                entry.has_abstract = has_abstract
                entry.updated_at = datetime.utcnow()
                logger.info(f"Updated database entry for DOI: {doi}")
            else:
                # Create new entry
                entry = DOIEntry(
                    doi=doi,
                    bibtex=bibtex,
                    source=source,
                    quality_score=quality_score,
                    has_abstract=has_abstract,
                )
                entry.metadata = metadata
                session.add(entry)
                logger.info(f"Created new database entry for DOI: {doi}")

            session.commit()
            session.refresh(entry)
            return entry

    def delete_entry(self, doi: str) -> bool:
        """
        Delete DOI entry from database.

        Args:
            doi: DOI identifier

        Returns:
            True if deleted, False if not found
        """
        with self.get_session() as session:
            entry = session.query(DOIEntry).filter_by(doi=doi).first()
            if entry:
                session.delete(entry)
                session.commit()
                logger.info(f"Deleted database entry for DOI: {doi}")
                return True
            return False

    def search_entries(
        self,
        source: Optional[str] = None,
        has_abstract: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DOIEntry]:
        """
        Search database entries with filters.

        Args:
            source: Filter by source (Crossref, DataCite, DOI.org)
            has_abstract: Filter by abstract presence
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            List of matching DOIEntry objects
        """
        with self.get_session() as session:
            query = session.query(DOIEntry)

            if source:
                query = query.filter_by(source=source)
            if has_abstract is not None:
                query = query.filter_by(has_abstract=has_abstract)

            query = query.order_by(DOIEntry.created_at.desc())
            return query.limit(limit).offset(offset).all()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with database statistics
        """
        with self.get_session() as session:
            total_entries = session.query(DOIEntry).count()

            source_counts = {}
            for source in ["Crossref", "DataCite", "DOI.org"]:
                count = session.query(DOIEntry).filter_by(source=source).count()
                source_counts[source] = count

            with_abstracts = session.query(DOIEntry).filter_by(has_abstract=True).count()

            # Get oldest and newest entries
            oldest = session.query(DOIEntry).order_by(DOIEntry.created_at.asc()).first()
            newest = session.query(DOIEntry).order_by(DOIEntry.created_at.desc()).first()

            return {
                "total_entries": total_entries,
                "by_source": source_counts,
                "with_abstracts": with_abstracts,
                "abstract_percentage": (
                    (with_abstracts / total_entries * 100) if total_entries > 0 else 0
                ),
                "oldest_entry": oldest.created_at.isoformat() if oldest else None,
                "newest_entry": newest.created_at.isoformat() if newest else None,
            }

    def clear_all(self) -> int:
        """
        Clear all entries from database.

        Returns:
            Number of entries deleted

        Warning:
            This operation cannot be undone!
        """
        with self.get_session() as session:
            count = session.query(DOIEntry).count()
            session.query(DOIEntry).delete()
            session.commit()
            logger.warning(f"Cleared {count} entries from database")
            return count

    def export_to_json(self, output_path: str | Path) -> int:
        """
        Export all database entries to JSON file.

        Args:
            output_path: Path to output JSON file

        Returns:
            Number of entries exported
        """
        output_path = Path(output_path)

        with self.get_session() as session:
            entries = session.query(DOIEntry).all()
            export_data = [entry.to_dict() for entry in entries]

            output_path.write_text(json.dumps(export_data, indent=2))
            logger.info(f"Exported {len(entries)} entries to {output_path}")

            return len(entries)

    def import_from_json(self, input_path: str | Path) -> int:
        """
        Import entries from JSON file.

        Args:
            input_path: Path to input JSON file

        Returns:
            Number of entries imported
        """
        input_path = Path(input_path)
        data = json.loads(input_path.read_text())

        count = 0
        for entry_data in data:
            self.save_entry(
                doi=entry_data["doi"],
                bibtex=entry_data["bibtex"],
                metadata=entry_data.get("metadata", {}),
                source=entry_data["source"],
                quality_score=entry_data.get("quality_score"),
                has_abstract=entry_data.get("has_abstract", False),
            )
            count += 1

        logger.info(f"Imported {count} entries from {input_path}")
        return count

    def cleanup_old_entries(self, days: int = 90) -> int:
        """
        Remove entries older than specified days that haven't been accessed.

        Args:
            days: Number of days threshold

        Returns:
            Number of entries deleted
        """
        from datetime import timedelta

        threshold = datetime.utcnow() - timedelta(days=days)

        with self.get_session() as session:
            entries = (
                session.query(DOIEntry)
                .filter(DOIEntry.last_accessed < threshold)
                .all()
            )

            count = len(entries)
            for entry in entries:
                session.delete(entry)

            session.commit()
            logger.info(f"Cleaned up {count} old entries (>{days} days)")

            return count

    def __repr__(self) -> str:
        stats = self.get_statistics()
        return f"<DOIDatabase(entries={stats['total_entries']}, path='{self.db_path}')>"
