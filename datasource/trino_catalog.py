"""
Trino Catalog Manager — generates .properties files for Trino connectors.

Each data source added in Polaris gets a corresponding Trino catalog
properties file written to the catalog directory. When Trino is configured
with `catalog.management=dynamic`, these catalogs can also be registered
at runtime via the REST API.
"""

from __future__ import annotations

import logging
import os
import socket
from pathlib import Path
from typing import Any

from datasource.models import DataSource, DataSourceType, TRINO_CONNECTOR_MAP

logger = logging.getLogger(__name__)


class TrinoCatalogManager:
    """Generates and manages Trino catalog .properties files.

    Args:
        catalog_dir: Filesystem path where .properties files are written.
    """

    def __init__(self, catalog_dir: str) -> None:
        self._catalog_dir = Path(catalog_dir)
        self._catalog_dir.mkdir(parents=True, exist_ok=True)

    def create_catalog(self, datasource: DataSource) -> str:
        """Generate a Trino catalog .properties file for the given data source.

        Args:
            datasource: The DataSource object to generate a catalog for.

        Returns:
            The path to the generated .properties file.
        """
        properties = self._build_properties(datasource)
        file_path = self._catalog_dir / f"{datasource.name}.properties"

        with open(file_path, "w") as f:
            for key, value in properties.items():
                f.write(f"{key}={value}\n")

        logger.info("Generated Trino catalog file: %s", file_path)
        return str(file_path)

    def remove_catalog(self, catalog_name: str) -> bool:
        """Remove a Trino catalog .properties file.

        Args:
            catalog_name: The name of the catalog (data source name).

        Returns:
            True if the file was removed, False if it didn't exist.
        """
        file_path = self._catalog_dir / f"{catalog_name}.properties"
        if file_path.exists():
            file_path.unlink()
            logger.info("Removed Trino catalog file: %s", file_path)
            return True
        return False

    def list_catalogs(self) -> list[str]:
        """List all catalog .properties files in the catalog directory.

        Returns:
            List of catalog names (without .properties extension).
        """
        return [
            f.stem
            for f in self._catalog_dir.glob("*.properties")
        ]

    def test_connection(self, datasource: DataSource) -> tuple[bool, str]:
        """Basic connectivity test — checks if the host:port is reachable.

        Args:
            datasource: The DataSource to test.

        Returns:
            (success, message) tuple.
        """
        if datasource.type == DataSourceType.GOOGLE_SHEETS:
            # Google Sheets doesn't have a host to test
            return True, "Google Sheets connector configured (no host test needed)."

        try:
            sock = socket.create_connection(
                (datasource.host, datasource.port), timeout=5
            )
            sock.close()
            return True, f"Successfully connected to {datasource.host}:{datasource.port}"
        except (socket.timeout, socket.error, OSError) as exc:
            return False, f"Cannot reach {datasource.host}:{datasource.port} — {exc}"

    # ------------------------------------------------------------------
    # Properties builders per connector type
    # ------------------------------------------------------------------

    def _build_properties(self, ds: DataSource) -> dict[str, str]:
        """Build the Trino connector properties dict based on data source type."""
        connector = TRINO_CONNECTOR_MAP.get(ds.type)
        if not connector:
            raise ValueError(f"Unsupported data source type: {ds.type}")

        builder = {
            DataSourceType.POSTGRESQL: self._postgres_props,
            DataSourceType.MYSQL: self._mysql_props,
            DataSourceType.MONGODB: self._mongodb_props,
            DataSourceType.REDIS: self._redis_props,
            DataSourceType.GOOGLE_SHEETS: self._gsheets_props,
            DataSourceType.MARIADB: self._mariadb_props,
            DataSourceType.SQLSERVER: self._sqlserver_props,
        }.get(ds.type)

        if builder is None:
            raise ValueError(f"No property builder for type: {ds.type}")

        return builder(ds)

    def _postgres_props(self, ds: DataSource) -> dict[str, str]:
        props = {
            "connector.name": "postgresql",
            "connection-url": f"jdbc:postgresql://{ds.host}:{ds.port}/{ds.database}",
            "connection-user": ds.username,
            "connection-password": ds.password,
        }
        props.update(ds.extra_config)
        return props

    def _mysql_props(self, ds: DataSource) -> dict[str, str]:
        props = {
            "connector.name": "mysql",
            "connection-url": f"jdbc:mysql://{ds.host}:{ds.port}/{ds.database}",
            "connection-user": ds.username,
            "connection-password": ds.password,
        }
        props.update(ds.extra_config)
        return props

    def _mongodb_props(self, ds: DataSource) -> dict[str, str]:
        props = {
            "connector.name": "mongodb",
            "mongodb.connection-url": f"mongodb://{ds.username}:{ds.password}@{ds.host}:{ds.port}/",
            "mongodb.schema-collection": ds.extra_config.get("schema_collection", "_schema"),
        }
        if ds.database:
            props["mongodb.connection-url"] = (
                f"mongodb://{ds.username}:{ds.password}@{ds.host}:{ds.port}/{ds.database}"
            )
        extra = {k: v for k, v in ds.extra_config.items() if k != "schema_collection"}
        props.update(extra)
        return props

    def _redis_props(self, ds: DataSource) -> dict[str, str]:
        props = {
            "connector.name": "redis",
            "redis.table-names": ds.extra_config.get("table_names", ""),
            "redis.nodes": f"{ds.host}:{ds.port}",
        }
        if ds.password:
            props["redis.password"] = ds.password
        if ds.database:
            props["redis.database-index"] = ds.database
        extra = {k: v for k, v in ds.extra_config.items() if k != "table_names"}
        props.update(extra)
        return props

    def _gsheets_props(self, ds: DataSource) -> dict[str, str]:
        props = {
            "connector.name": "google_sheets",
            "gsheets.credentials-path": ds.extra_config.get("credentials_path", ""),
            "gsheets.metadata-sheet-id": ds.extra_config.get("metadata_sheet_id", ""),
        }
        extra = {
            k: v for k, v in ds.extra_config.items()
            if k not in ("credentials_path", "metadata_sheet_id")
        }
        props.update(extra)
        return props

    def _mariadb_props(self, ds: DataSource) -> dict[str, str]:
        props = {
            "connector.name": "mariadb",
            "connection-url": f"jdbc:mariadb://{ds.host}:{ds.port}/{ds.database}",
            "connection-user": ds.username,
            "connection-password": ds.password,
        }
        props.update(ds.extra_config)
        return props

    def _sqlserver_props(self, ds: DataSource) -> dict[str, str]:
        props = {
            "connector.name": "sqlserver",
            "connection-url": f"jdbc:sqlserver://{ds.host}:{ds.port};database={ds.database}",
            "connection-user": ds.username,
            "connection-password": ds.password,
        }
        props.update(ds.extra_config)
        return props
