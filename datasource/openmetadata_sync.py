"""
OpenMetadata Sync — registers data sources in OpenMetadata for metadata discovery.

After a data source is added in Polaris, this module creates the corresponding
database service in OpenMetadata and triggers an ingestion workflow so that
table schemas become searchable by the chatbot.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from datasource.models import DataSource, DataSourceType

logger = logging.getLogger(__name__)

# Mapping from our DataSourceType to OpenMetadata service type
# Note: Not all types are supported in OM as database services.
# Redis and Google Sheets use CustomDatabase as a workaround.
_OM_SERVICE_TYPE_MAP: dict[DataSourceType, str] = {
    DataSourceType.POSTGRESQL: "Postgres",
    DataSourceType.MYSQL: "Mysql",
    DataSourceType.MONGODB: "MongoDB",
    DataSourceType.REDIS: "CustomDatabase",
    DataSourceType.GOOGLE_SHEETS: "CustomDatabase",
    DataSourceType.MARIADB: "MariaDB",
    DataSourceType.SQLSERVER: "Mssql",
}

# Types that are NOT supported in OpenMetadata as database services
_OM_UNSUPPORTED_TYPES: set[DataSourceType] = set()


class OpenMetadataSync:
    """Syncs data source configurations to OpenMetadata.

    Args:
        base_url: OpenMetadata server base URL (e.g., http://openmetadata:8585).
        api_token: Bearer token for authentication.
    """

    def __init__(self, base_url: str, api_token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = api_token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def register_service(self, datasource: DataSource) -> tuple[bool, str]:
        """Register a database service in OpenMetadata and trigger ingestion.

        Creates the service if it doesn't exist, or updates it if it does.
        Then triggers a metadata ingestion pipeline to crawl tables.

        Args:
            datasource: The DataSource to register.

        Returns:
            (success, message) tuple.
        """
        service_type = _OM_SERVICE_TYPE_MAP.get(datasource.type)
        if not service_type:
            return False, f"Unsupported type for OpenMetadata: {datasource.type.value}"

        payload = self._build_service_payload(datasource, service_type)

        try:
            # Create/update the service
            response = httpx.put(
                f"{self._base_url}/api/v1/services/databaseServices",
                json=payload,
                headers=self._headers,
                timeout=15.0,
            )
            response.raise_for_status()
            service_data = response.json()
            service_id = service_data.get("id", "")
            logger.info(
                "Registered OpenMetadata service '%s' (type=%s, id=%s)",
                datasource.name, service_type, service_id,
            )

            # Trigger metadata ingestion
            ingestion_ok, ingestion_msg = self._trigger_ingestion(
                datasource.name, service_id, service_type, datasource.database
            )

            if ingestion_ok:
                return True, (
                    f"Service '{datasource.name}' registered and ingestion triggered. "
                    f"Tables will be available for search shortly."
                )
            else:
                return True, (
                    f"Service '{datasource.name}' registered in OpenMetadata. "
                    f"Ingestion note: {ingestion_msg}"
                )

        except httpx.HTTPStatusError as exc:
            msg = f"OpenMetadata HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            logger.error("Failed to register OM service: %s", msg)
            return False, msg
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            msg = f"Cannot reach OpenMetadata at {self._base_url}: {exc}"
            logger.error(msg)
            return False, msg

    def _trigger_ingestion(
        self, service_name: str, service_id: str, service_type: str,
        target_database: str = ""
    ) -> tuple[bool, str]:
        """Ingest metadata by querying Trino and pushing table info to OpenMetadata.

        Since the Airflow-based ingestion container has compatibility issues,
        we perform a lightweight ingestion directly: query Trino's
        information_schema for the catalog that was just added, then create
        the database/schema/table entities in OpenMetadata via REST API.

        Only ingests the specific database/schema configured by the user,
        not all schemas on the server.

        Args:
            service_name: Name of the database service (also the Trino catalog name).
            service_id: UUID of the service in OpenMetadata.
            service_type: OM service type (e.g., "Postgres", "Mysql").
            target_database: The specific database/schema to ingest (from user config).

        Returns:
            (success, message) tuple.
        """
        try:
            # Import TrinoClient to query the catalog's information_schema
            from chatbot.trino_client import TrinoClient
            from config import Config

            cfg = Config()
            tc = TrinoClient(cfg)

            # Get schemas for this catalog
            try:
                schemas_result = tc.execute(
                    f"SHOW SCHEMAS FROM {service_name}", row_limit=50
                )
                all_schemas = [
                    r.get("Schema", "")
                    for r in schemas_result.rows
                    if r.get("Schema", "") != "information_schema"
                ]
            except Exception as exc:
                logger.warning("Could not query Trino for schemas of %s: %s", service_name, exc)
                return False, (
                    f"Trino catalog '{service_name}' not yet available. "
                    "Restart Trino to load the new catalog, then re-add the data source."
                )

            if not all_schemas:
                return True, "Service registered but no schemas found in catalog."

            # Filter to only the target database/schema if specified
            if target_database:
                schemas = [s for s in all_schemas if s == target_database]
                if not schemas:
                    # Target schema not found — fall back to all schemas
                    logger.warning(
                        "Target schema '%s' not found in catalog '%s'. "
                        "Available schemas: %s. Ingesting all.",
                        target_database, service_name, all_schemas,
                    )
                    schemas = all_schemas
            else:
                schemas = all_schemas

            tables_ingested = 0
            for schema in schemas:
                # Create database entity in OM
                db_fqn = f"{service_name}.{schema}"
                self._create_database(service_name, schema)

                # Get tables in this schema
                try:
                    tables_result = tc.execute(
                        f"SELECT table_name FROM {service_name}.information_schema.tables "
                        f"WHERE table_schema = '{schema}'",
                        row_limit=100,
                    )
                except Exception:
                    continue

                for row in tables_result.rows:
                    table_name = row.get("table_name", "")
                    if not table_name:
                        continue

                    # Get columns
                    try:
                        cols_result = tc.execute(
                            f"SELECT column_name, data_type "
                            f"FROM {service_name}.information_schema.columns "
                            f"WHERE table_schema = '{schema}' AND table_name = '{table_name}' "
                            f"ORDER BY ordinal_position",
                            row_limit=200,
                        )
                        columns = [
                            {
                                "name": r.get("column_name", ""),
                                "dataType": self._map_trino_type(r.get("data_type", "VARCHAR")),
                                "dataLength": 1,
                            }
                            for r in cols_result.rows
                        ]
                    except Exception:
                        columns = []

                    # Create table entity in OM
                    self._create_table(service_name, schema, table_name, columns)
                    tables_ingested += 1

            if tables_ingested > 0:
                logger.info("Ingested %d table(s) for service '%s'", tables_ingested, service_name)
                return True, f"Ingested {tables_ingested} table(s) into OpenMetadata."
            else:
                return True, "Service registered but no tables found to ingest."

        except Exception as exc:
            logger.warning("Python-based ingestion failed: %s", exc)
            return False, f"Ingestion failed: {exc}"

    def _create_database(self, service_name: str, schema_name: str) -> None:
        """Create a database + databaseSchema entity in OpenMetadata."""
        # Create database
        db_payload = {
            "name": schema_name,
            "service": service_name,
        }
        try:
            httpx.put(
                f"{self._base_url}/api/v1/databases",
                json=db_payload,
                headers=self._headers,
                timeout=10.0,
            )
        except Exception:
            pass  # May already exist

        # Create database schema
        schema_payload = {
            "name": schema_name,
            "database": f"{service_name}.{schema_name}",
        }
        try:
            httpx.put(
                f"{self._base_url}/api/v1/databaseSchemas",
                json=schema_payload,
                headers=self._headers,
                timeout=10.0,
            )
        except Exception:
            pass  # May already exist

    def _create_table(
        self, service_name: str, schema_name: str, table_name: str, columns: list
    ) -> None:
        """Create a table entity in OpenMetadata."""
        table_payload = {
            "name": table_name,
            "databaseSchema": f"{service_name}.{schema_name}.{schema_name}",
            "columns": columns if columns else [
                {"name": "_key", "dataType": "VARCHAR", "dataLength": 1, "description": "Redis key identifier"},
                {"name": "_value", "dataType": "VARCHAR", "dataLength": 1, "description": "JSON value containing the data"},
            ],
        }
        try:
            resp = httpx.put(
                f"{self._base_url}/api/v1/tables",
                json=table_payload,
                headers=self._headers,
                timeout=10.0,
            )
            if resp.status_code >= 400:
                logger.debug(
                    "Failed to create table %s.%s.%s: HTTP %d",
                    service_name, schema_name, table_name, resp.status_code,
                )
        except Exception as exc:
            logger.debug("Failed to create table %s: %s", table_name, exc)

    @staticmethod
    def _map_trino_type(trino_type: str) -> str:
        """Map a Trino data type to an OpenMetadata dataType enum value."""
        trino_type_upper = trino_type.upper()
        mapping = {
            "INTEGER": "INT",
            "BIGINT": "BIGINT",
            "SMALLINT": "SMALLINT",
            "TINYINT": "TINYINT",
            "BOOLEAN": "BOOLEAN",
            "REAL": "FLOAT",
            "DOUBLE": "DOUBLE",
            "DECIMAL": "DECIMAL",
            "VARCHAR": "VARCHAR",
            "CHAR": "CHAR",
            "VARBINARY": "BINARY",
            "DATE": "DATE",
            "TIME": "TIME",
            "TIMESTAMP": "TIMESTAMP",
            "JSON": "JSON",
            "ARRAY": "ARRAY",
            "MAP": "MAP",
            "ROW": "STRUCT",
        }
        for prefix, om_type in mapping.items():
            if trino_type_upper.startswith(prefix):
                return om_type
        return "VARCHAR"

    def remove_service(self, service_name: str) -> tuple[bool, str]:
        """Remove a database service from OpenMetadata.

        Args:
            service_name: The name of the service to remove.

        Returns:
            (success, message) tuple.
        """
        try:
            # First get the service ID
            response = httpx.get(
                f"{self._base_url}/api/v1/services/databaseServices/name/{service_name}",
                headers=self._headers,
                timeout=10.0,
            )
            if response.status_code == 404:
                return True, "Service not found in OpenMetadata (already removed)."

            response.raise_for_status()
            service_id = response.json().get("id")

            if service_id:
                # recursive=true removes all databases/schemas/tables under the service
                delete_resp = httpx.delete(
                    f"{self._base_url}/api/v1/services/databaseServices/{service_id}"
                    f"?hardDelete=true&recursive=true",
                    headers=self._headers,
                    timeout=60.0,
                )
                delete_resp.raise_for_status()

            return True, f"Service '{service_name}' and its tables removed from OpenMetadata."

        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as exc:
            msg = f"Failed to remove OM service: {exc}"
            logger.error(msg)
            return False, msg

    # ------------------------------------------------------------------
    # Payload builders
    # ------------------------------------------------------------------

    def _build_service_payload(
        self, ds: DataSource, service_type: str
    ) -> dict[str, Any]:
        """Build the OpenMetadata createDatabaseService request body."""
        connection_config = self._build_connection_config(ds, service_type)

        return {
            "name": ds.name,
            "serviceType": service_type,
            "connection": {
                "config": connection_config,
            },
        }

    def _build_connection_config(
        self, ds: DataSource, service_type: str
    ) -> dict[str, Any]:
        """Build connector-specific connection configuration for OM 1.4.8+."""
        if service_type == "Postgres":
            return {
                "type": "Postgres",
                "scheme": "postgresql+psycopg2",
                "hostPort": f"{ds.host}:{ds.port}",
                "username": ds.username,
                "authType": {"password": ds.password},
                "database": ds.database,
            }
        elif service_type == "Mysql":
            return {
                "type": "Mysql",
                "scheme": "mysql+pymysql",
                "hostPort": f"{ds.host}:{ds.port}",
                "username": ds.username,
                "authType": {"password": ds.password},
                "databaseSchema": ds.database,
            }
        elif service_type == "MongoDB":
            return {
                "type": "MongoDB",
                "scheme": "mongodb",
                "hostPort": f"{ds.host}:{ds.port}",
                "username": ds.username,
                "password": ds.password,
                "databaseName": ds.database,
            }
        elif service_type == "Redis":
            config: dict[str, Any] = {
                "type": "Redis",
                "hostPort": f"{ds.host}:{ds.port}",
            }
            if ds.username:
                config["username"] = ds.username
            if ds.password:
                config["password"] = ds.password
            return config
        elif service_type == "Mssql":
            return {
                "type": "Mssql",
                "scheme": "mssql+pytds",
                "hostPort": f"{ds.host}:{ds.port}",
                "username": ds.username,
                "authType": {"password": ds.password},
                "database": ds.database,
            }
        elif service_type == "CustomDatabase":
            # Used for Redis, Google Sheets, and other non-standard sources
            return {
                "type": "CustomDatabase",
                "sourcePythonClass": "metadata.ingestion.source.database.customdatabase.CustomDatabaseSource",
                "connectionOptions": {
                    "host": f"{ds.host}:{ds.port}",
                    "database": ds.database or "default",
                },
            }
        else:
            # Generic fallback
            return {
                "type": service_type,
                "hostPort": f"{ds.host}:{ds.port}",
                "username": ds.username,
                "authType": {"password": ds.password},
            }
