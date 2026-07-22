"""
Data Source Manager — CRUD operations with JSON persistence.

Handles creating, reading, updating, and deleting data source configurations.
On each mutation it persists state to disk and triggers Trino catalog generation.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from datasource.models import DataSource, DataSourceType
from datasource.trino_catalog import TrinoCatalogManager

logger = logging.getLogger(__name__)

_DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_DEFAULT_FILE = "datasources.json"


class DataSourceManager:
    """Manages data source configurations with file-based persistence.

    Args:
        data_dir: Directory where datasources.json is stored.
        trino_catalog_dir: Directory where Trino .properties files are written.
    """

    def __init__(
        self,
        data_dir: str | None = None,
        trino_catalog_dir: str | None = None,
    ) -> None:
        self._data_dir = Path(data_dir or _DEFAULT_DATA_DIR)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._file_path = self._data_dir / _DEFAULT_FILE

        # Trino catalog directory (where .properties files go)
        default_catalog_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "infra", "trino", "catalog"
        )
        self._trino_mgr = TrinoCatalogManager(
            catalog_dir=trino_catalog_dir or default_catalog_dir
        )

        self._datasources: list[DataSource] = []
        self._load()

    # ------------------------------------------------------------------
    # Public CRUD API
    # ------------------------------------------------------------------

    def list_all(self) -> list[DataSource]:
        """Return all configured data sources."""
        return list(self._datasources)

    def get(self, datasource_id: str) -> Optional[DataSource]:
        """Get a data source by ID. Returns None if not found."""
        for ds in self._datasources:
            if ds.id == datasource_id:
                return ds
        return None

    def get_by_name(self, name: str) -> Optional[DataSource]:
        """Get a data source by name. Returns None if not found."""
        for ds in self._datasources:
            if ds.name.lower() == name.lower():
                return ds
        return None

    def add(self, datasource: DataSource) -> DataSource:
        """Add a new data source, persist, and generate Trino catalog.

        Raises:
            ValueError: If a data source with the same name already exists.
        """
        # Validate unique name
        existing = self.get_by_name(datasource.name)
        if existing:
            raise ValueError(
                f"A data source named '{datasource.name}' already exists."
            )

        # Validate name is a valid identifier (Trino catalog name)
        if not datasource.name or not datasource.name.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Data source name must be alphanumeric (underscores and hyphens allowed)."
            )

        datasource.status = "active"
        self._datasources.append(datasource)
        self._save()

        # Generate Trino catalog file
        try:
            self._trino_mgr.create_catalog(datasource)
            logger.info("Created Trino catalog for data source: %s", datasource.name)
        except Exception as exc:
            datasource.status = "error"
            self._save()
            logger.error("Failed to create Trino catalog for %s: %s", datasource.name, exc)

        return datasource

    def update(self, datasource_id: str, updates: dict) -> Optional[DataSource]:
        """Update a data source's properties.

        Args:
            datasource_id: ID of the data source to update.
            updates: Dict of field names to new values.

        Returns:
            The updated DataSource, or None if not found.
        """
        ds = self.get(datasource_id)
        if ds is None:
            return None

        old_name = ds.name

        for key, value in updates.items():
            if key == "type":
                value = DataSourceType(value)
            if hasattr(ds, key) and key not in ("id", "created_at"):
                setattr(ds, key, value)

        ds.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()

        # Regenerate Trino catalog
        try:
            if old_name != ds.name:
                self._trino_mgr.remove_catalog(old_name)
            self._trino_mgr.create_catalog(ds)
            ds.status = "active"
        except Exception as exc:
            ds.status = "error"
            logger.error("Failed to update Trino catalog for %s: %s", ds.name, exc)

        self._save()
        return ds

    def remove(self, datasource_id: str) -> bool:
        """Remove a data source by ID.

        Returns:
            True if removed, False if not found.
        """
        ds = self.get(datasource_id)
        if ds is None:
            return False

        self._datasources = [d for d in self._datasources if d.id != datasource_id]
        self._save()

        # Remove Trino catalog file
        try:
            self._trino_mgr.remove_catalog(ds.name)
            logger.info("Removed Trino catalog for data source: %s", ds.name)
        except Exception as exc:
            logger.error("Failed to remove Trino catalog for %s: %s", ds.name, exc)

        return True

    def test_connection(self, datasource: DataSource) -> tuple[bool, str]:
        """Test connectivity to a data source.

        Returns:
            (success: bool, message: str)
        """
        return self._trino_mgr.test_connection(datasource)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load data sources from JSON file."""
        if not self._file_path.exists():
            self._datasources = []
            return

        try:
            with open(self._file_path, "r") as f:
                data = json.load(f)
            self._datasources = [
                DataSource.from_dict(ds) for ds in data.get("datasources", [])
            ]
            logger.info("Loaded %d data source(s) from %s", len(self._datasources), self._file_path)
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error("Failed to load datasources.json: %s", exc)
            self._datasources = []

    def _save(self) -> None:
        """Persist data sources to JSON file."""
        data = {
            "datasources": [ds.to_dict() for ds in self._datasources]
        }
        self._data_dir.mkdir(parents=True, exist_ok=True)
        with open(self._file_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.debug("Saved %d data source(s) to %s", len(self._datasources), self._file_path)
