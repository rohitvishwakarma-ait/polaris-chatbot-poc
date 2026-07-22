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
_OM_SERVICE_TYPE_MAP: dict[DataSourceType, str] = {
    DataSourceType.POSTGRESQL: "Postgres",
    DataSourceType.MYSQL: "Mysql",
    DataSourceType.MONGODB: "MongoDB",
    DataSourceType.REDIS: "Redis",
    DataSourceType.GOOGLE_SHEETS: "GoogleSheets",
    DataSourceType.MARIADB: "MariaDB",
    DataSourceType.SQLSERVER: "Mssql",
}


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
        """Register a database service in OpenMetadata.

        Creates the service if it doesn't exist, or updates it if it does.

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
            # Try to create the service
            response = httpx.put(
                f"{self._base_url}/api/v1/services/databaseServices",
                json=payload,
                headers=self._headers,
                timeout=15.0,
            )
            response.raise_for_status()
            logger.info(
                "Registered OpenMetadata service '%s' (type=%s)",
                datasource.name, service_type,
            )
            return True, f"Service '{datasource.name}' registered in OpenMetadata."

        except httpx.HTTPStatusError as exc:
            msg = f"OpenMetadata HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            logger.error("Failed to register OM service: %s", msg)
            return False, msg
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            msg = f"Cannot reach OpenMetadata at {self._base_url}: {exc}"
            logger.error(msg)
            return False, msg

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
                delete_resp = httpx.delete(
                    f"{self._base_url}/api/v1/services/databaseServices/{service_id}?hardDelete=true",
                    headers=self._headers,
                    timeout=10.0,
                )
                delete_resp.raise_for_status()

            return True, f"Service '{service_name}' removed from OpenMetadata."

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
        """Build connector-specific connection configuration for OM."""
        if service_type == "Postgres":
            return {
                "type": "Postgres",
                "scheme": "postgresql+psycopg2",
                "hostPort": f"{ds.host}:{ds.port}",
                "username": ds.username,
                "password": ds.password,
                "database": ds.database,
            }
        elif service_type == "Mysql":
            return {
                "type": "Mysql",
                "scheme": "mysql+pymysql",
                "hostPort": f"{ds.host}:{ds.port}",
                "username": ds.username,
                "password": ds.password,
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
                "password": ds.password,
                "database": ds.database,
            }
        else:
            # Generic fallback
            return {
                "type": service_type,
                "hostPort": f"{ds.host}:{ds.port}",
                "username": ds.username,
                "password": ds.password,
            }
