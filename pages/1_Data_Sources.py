"""
Polaris — Data Source Configuration Page.

Allows users to add, edit, test, and remove data sources directly from
the Streamlit UI. Each data source is provisioned into Trino (catalog
properties file) and optionally into OpenMetadata.
"""

from __future__ import annotations

import os
import sys

# Ensure project root is on the path
_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_APP_DIR, ".env"))
except ImportError:
    pass

import streamlit as st

from datasource.models import DataSource, DataSourceType, DEFAULT_PORTS
from datasource.manager import DataSourceManager

st.set_page_config(page_title="Polaris — Data Sources", page_icon="🔌", layout="wide")

# ---------------------------------------------------------------------------
# Initialise manager in session state
# ---------------------------------------------------------------------------

if "ds_manager" not in st.session_state:
    st.session_state.ds_manager = DataSourceManager()


def get_manager() -> DataSourceManager:
    return st.session_state.ds_manager


# ---------------------------------------------------------------------------
# Page Header
# ---------------------------------------------------------------------------

st.title("🔌 Data Sources")
st.caption(
    "Configure your database connections here. Each data source is automatically "
    "provisioned as a Trino catalog and registered in OpenMetadata for discovery."
)

st.divider()

# ---------------------------------------------------------------------------
# Existing Data Sources
# ---------------------------------------------------------------------------

manager = get_manager()
datasources = manager.list_all()

if datasources:
    st.subheader("Configured Data Sources")

    for ds in datasources:
        with st.expander(f"{'🟢' if ds.status == 'active' else '🔴'} {ds.name} ({ds.type.value})", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.text(f"Host: {ds.host}")
                st.text(f"Port: {ds.port}")
            with col2:
                st.text(f"Database: {ds.database}")
                st.text(f"Username: {ds.username}")
            with col3:
                st.text(f"Status: {ds.status}")
                st.text(f"Created: {ds.created_at[:10]}")

            # Action buttons
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("🔄 Test Connection", key=f"test_{ds.id}"):
                    success, message = manager.test_connection(ds)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
            with btn_col2:
                if st.button("🗑️ Remove", key=f"remove_{ds.id}", type="secondary"):
                    manager.remove(ds.id)
                    st.success(f"Removed '{ds.name}'")
                    st.rerun()
            with btn_col3:
                st.caption(f"ID: {ds.id[:8]}...")

    st.divider()
else:
    st.info("No data sources configured yet. Add one below to get started.")

# ---------------------------------------------------------------------------
# Add New Data Source Form
# ---------------------------------------------------------------------------

st.subheader("Add New Data Source")

with st.form("add_datasource_form", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        ds_name = st.text_input(
            "Name *",
            placeholder="e.g., my_postgres, sales_db",
            help="Alphanumeric with underscores/hyphens. Used as the Trino catalog name.",
        )
        ds_type = st.selectbox(
            "Type *",
            options=[t.value for t in DataSourceType],
            format_func=lambda x: x.replace("_", " ").title(),
        )
        ds_host = st.text_input(
            "Host *",
            placeholder="e.g., localhost, db.example.com",
            help="For Docker services, use the container name (e.g., 'my-postgres').",
        )

    with col2:
        selected_type = DataSourceType(ds_type)
        default_port = DEFAULT_PORTS.get(selected_type, 5432)
        ds_port = st.number_input(
            "Port *",
            min_value=0,
            max_value=65535,
            value=default_port,
            help="Default port auto-fills based on type.",
        )
        ds_database = st.text_input(
            "Database / Schema",
            placeholder="e.g., mydb, public",
            help="Database name or schema depending on the connector.",
        )
        ds_username = st.text_input("Username", placeholder="e.g., admin")

    # Password on its own row for security
    ds_password = st.text_input("Password", type="password", placeholder="Enter password")

    # Extra config for advanced connectors
    with st.expander("Advanced Configuration (optional)"):
        st.caption("Additional connector-specific properties as key=value pairs, one per line.")
        extra_raw = st.text_area(
            "Extra Properties",
            placeholder="e.g.,\nredis.table-names=my_table\ngsheets.credentials-path=/path/to/creds.json",
            height=100,
        )

    submitted = st.form_submit_button("➕ Add Data Source", type="primary", use_container_width=True)

    if submitted:
        # Validate required fields
        if not ds_name:
            st.error("Name is required.")
        elif not ds_host and selected_type != DataSourceType.GOOGLE_SHEETS:
            st.error("Host is required.")
        else:
            # Parse extra config
            extra_config = {}
            if extra_raw:
                for line in extra_raw.strip().split("\n"):
                    line = line.strip()
                    if "=" in line:
                        key, value = line.split("=", 1)
                        extra_config[key.strip()] = value.strip()

            new_ds = DataSource(
                name=ds_name.strip().lower().replace(" ", "_"),
                type=selected_type,
                host=ds_host.strip(),
                port=int(ds_port),
                database=ds_database.strip(),
                username=ds_username.strip(),
                password=ds_password,
                extra_config=extra_config,
            )

            try:
                manager.add(new_ds)
                st.success(f"Data source '{new_ds.name}' added and Trino catalog generated.")

                # Attempt OpenMetadata registration
                om_url = os.environ.get("OPENMETADATA_URL")
                om_token = os.environ.get("OPENMETADATA_API_TOKEN")
                if om_url and om_token:
                    from datasource.openmetadata_sync import OpenMetadataSync
                    om_sync = OpenMetadataSync(om_url, om_token)
                    ok, msg = om_sync.register_service(new_ds)
                    if ok:
                        st.success(f"OpenMetadata: {msg}")
                    else:
                        st.warning(f"OpenMetadata sync skipped: {msg}")
                else:
                    st.info("OpenMetadata not configured — skipping metadata registration.")

                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

# ---------------------------------------------------------------------------
# Footer info
# ---------------------------------------------------------------------------

st.divider()
with st.expander("How it works"):
    st.markdown("""
    **When you add a data source:**

    1. A Trino catalog `.properties` file is generated in `infra/trino/catalog/`
    2. If OpenMetadata is configured, the service is registered there for table discovery
    3. After Trino restarts (or with dynamic catalog management), the data becomes queryable
    4. The chatbot can now answer questions about data in this source

    **Supported connectors:** PostgreSQL, MySQL, MongoDB, Redis, Google Sheets, MariaDB, SQL Server

    **Docker networking tip:** If your databases run in the same Docker Compose stack,
    use the service name as the host (e.g., `my-postgres` instead of `localhost`).
    """)
