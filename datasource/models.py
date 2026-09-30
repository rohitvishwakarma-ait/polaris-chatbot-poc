"""
Data source models for Polaris.

Defines the schema for configurable data sources that can be added
via the UI and provisioned into Trino + OpenMetadata.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class DataSourceType(str, enum.Enum):
    """Supported data source connector types."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    REDIS = "redis"
    GOOGLE_SHEETS = "google_sheets"
    MARIADB = "mariadb"
    SQLSERVER = "sqlserver"


# Mapping from DataSourceType to Trino connector name
TRINO_CONNECTOR_MAP: dict[DataSourceType, str] = {
    DataSourceType.POSTGRESQL: "postgresql",
    DataSourceType.MYSQL: "mysql",
    DataSourceType.MONGODB: "mongodb",
    DataSourceType.REDIS: "redis",
    DataSourceType.GOOGLE_SHEETS: "google_sheets",
    DataSourceType.MARIADB: "mariadb",
    DataSourceType.SQLSERVER: "sqlserver",
}


@dataclass
class DataSource:
    """A configured data source that will be provisioned into Trino and OpenMetadata.

    Attributes:
        id: Unique identifier (UUID string).
        name: Human-readable name (also used as Trino catalog name).
        type: The connector type.
        host: Database server hostname or IP.
        port: Database server port.
        database: Database/schema name to connect to.
        username: Connection username.
        password: Connection password (stored encrypted in production).
        extra_config: Additional connector-specific properties.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
        status: Current status (active, error, pending).
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    type: DataSourceType = DataSourceType.POSTGRESQL
    host: str = "localhost"
    port: int = 5432
    database: str = ""
    username: str = ""
    password: str = ""
    extra_config: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "password": self.password,
            "extra_config": self.extra_config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DataSource:
        """Deserialize from a dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            type=DataSourceType(data.get("type", "postgresql")),
            host=data.get("host", "localhost"),
            port=data.get("port", 5432),
            database=data.get("database", ""),
            username=data.get("username", ""),
            password=data.get("password", ""),
            extra_config=data.get("extra_config", {}),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            status=data.get("status", "pending"),
        )


# Default ports per data source type
DEFAULT_PORTS: dict[DataSourceType, int] = {
    DataSourceType.POSTGRESQL: 5432,
    DataSourceType.MYSQL: 3306,
    DataSourceType.MONGODB: 27017,
    DataSourceType.REDIS: 6379,
    DataSourceType.GOOGLE_SHEETS: 0,
    DataSourceType.MARIADB: 3306,
    DataSourceType.SQLSERVER: 1433,
}
