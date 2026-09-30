"""
Polaris — Data Source Configuration Page.

Allows users to add, edit, test, and remove data sources directly from
the Streamlit UI. Each data source is provisioned into Trino (catalog
properties file) and optionally into OpenMetadata.
"""

from __future__ import annotations

import base64
import json
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


def _remove_from_openmetadata(service_name: str) -> tuple[bool, str]:
    """Delete a data source's service (and its tables) from OpenMetadata."""
    om_url = os.environ.get("OPENMETADATA_URL")
    om_token = os.environ.get("OPENMETADATA_API_TOKEN")
    if not (om_url and om_token):
        return True, "OpenMetadata not configured — nothing to clean up."
    try:
        from datasource.openmetadata_sync import OpenMetadataSync
        om_sync = OpenMetadataSync(om_url, om_token)
        return om_sync.remove_service(service_name)
    except Exception as exc:  # noqa: BLE001
        return False, f"OpenMetadata cleanup error: {exc}"


def _extra_config_to_text(extra: dict) -> str:
    """Render an extra_config dict back into key=value lines for editing.

    Sensitive values (e.g. an embedded base64 service-account key) are omitted
    so they are never displayed in the UI. They are preserved across edits.
    """
    if not extra:
        return ""
    return "\n".join(
        f"{k}={v}" for k, v in extra.items() if k not in _SENSITIVE_EXTRA_KEYS
    )


# extra_config keys whose values are secrets and must never be shown in the UI.
_SENSITIVE_EXTRA_KEYS = {"credentials_key"}


def _parse_extra_config(raw: str) -> dict:
    """Parse key=value lines into a dict."""
    result: dict = {}
    if raw:
        for line in raw.strip().split("\n"):
            line = line.strip()
            if "=" in line:
                key, value = line.split("=", 1)
                result[key.strip()] = value.strip()
    return result


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
            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
            with btn_col1:
                if st.button("🔄 Test Connection", key=f"test_{ds.id}"):
                    success, message = manager.test_connection(ds)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
            with btn_col2:
                if st.button("☁️ Sync Metadata", key=f"sync_{ds.id}"):
                    om_url = os.environ.get("OPENMETADATA_URL")
                    om_token = os.environ.get("OPENMETADATA_API_TOKEN")
                    if om_url and om_token:
                        from datasource.openmetadata_sync import OpenMetadataSync
                        om_sync = OpenMetadataSync(om_url, om_token)
                        ok, msg = om_sync.register_service(ds)
                        if ok:
                            st.success(msg)
                        else:
                            st.warning(msg)
                    else:
                        st.warning("OpenMetadata not configured (OPENMETADATA_URL / OPENMETADATA_API_TOKEN missing).")
            with btn_col3:
                if st.button("✏️ Edit", key=f"editbtn_{ds.id}"):
                    st.session_state[f"editing_{ds.id}"] = not st.session_state.get(f"editing_{ds.id}", False)
            with btn_col4:
                if st.button("🗑️ Remove", key=f"remove_{ds.id}", type="secondary"):
                    # 1. Remove from OpenMetadata (service + tables)
                    om_ok, om_msg = _remove_from_openmetadata(ds.name)
                    # 2. Remove from Polaris (also deletes the Trino catalog file)
                    manager.remove(ds.id)
                    st.success(f"Removed '{ds.name}' (Trino catalog deleted). OpenMetadata: {om_msg}")
                    st.info("Restart Trino to fully unload the catalog: `docker restart polaris-trino`")
                    st.rerun()

            # ---- Edit form (toggled by Edit button) ----
            if st.session_state.get(f"editing_{ds.id}", False):
                st.divider()
                st.markdown("**Edit Connection**")
                with st.form(f"edit_form_{ds.id}"):
                    e1, e2 = st.columns(2)
                    with e1:
                        e_host = st.text_input("Host", value=ds.host, key=f"ehost_{ds.id}")
                        e_database = st.text_input("Database / Schema", value=ds.database, key=f"edb_{ds.id}")
                        e_username = st.text_input("Username", value=ds.username, key=f"euser_{ds.id}")
                    with e2:
                        e_port = st.number_input(
                            "Port", min_value=0, max_value=65535, value=int(ds.port), key=f"eport_{ds.id}"
                        )
                        e_password = st.text_input(
                            "Password", value=ds.password, type="password", key=f"epwd_{ds.id}"
                        )
                    if "credentials_key" in ds.extra_config:
                        st.caption(
                            "🔒 An embedded service-account key is stored for this "
                            "source and hidden here. It is kept on save; add a "
                            "`credentials_key=` line only to replace it."
                        )
                    e_extra = st.text_area(
                        "Advanced Properties (key=value per line)",
                        value=_extra_config_to_text(ds.extra_config),
                        key=f"eextra_{ds.id}",
                        height=80,
                    )
                    save = st.form_submit_button("💾 Save Changes", type="primary")
                    if save:
                        parsed_extra = _parse_extra_config(e_extra)
                        # Preserve hidden sensitive keys unless the user replaced them.
                        for _sk in _SENSITIVE_EXTRA_KEYS:
                            if _sk in ds.extra_config and _sk not in parsed_extra:
                                parsed_extra[_sk] = ds.extra_config[_sk]
                        updates = {
                            "host": e_host.strip(),
                            "port": int(e_port),
                            "database": e_database.strip(),
                            "username": e_username.strip(),
                            "password": e_password,
                            "extra_config": parsed_extra,
                        }
                        manager.update(ds.id, updates)
                        st.session_state[f"editing_{ds.id}"] = False
                        st.success(f"Updated '{ds.name}'. Restart Trino to apply: `docker restart polaris-trino`")
                        st.rerun()

    st.divider()
else:
    st.info("No data sources configured yet. Add one below to get started.")

# ---------------------------------------------------------------------------
# Add New Data Source Form
# ---------------------------------------------------------------------------

st.subheader("Add New Data Source")

def _resolve_gsheets_credentials(
    method: str, uploaded_file, pasted_json: str, credentials_path: str
) -> tuple[dict | None, str | None]:
    """Resolve Google Sheets credentials from the chosen input method.

    Returns an (extra_config_fragment, error_message) tuple. For upload/paste
    the raw JSON is validated and base64-encoded into ``credentials_key`` so it
    can be embedded directly in the catalog properties file (no server file
    access needed). For the server-path method it returns ``credentials_path``.
    """
    if method == "Server file path":
        if not credentials_path.strip():
            return None, "Provide the credentials path (inside Trino)."
        return {"credentials_path": credentials_path.strip()}, None

    # Upload or Paste -> obtain raw JSON text
    if method == "Upload JSON key":
        if uploaded_file is None:
            return None, "Upload the service-account JSON key file."
        raw = uploaded_file.getvalue().decode("utf-8", errors="replace")
    else:  # "Paste JSON"
        if not pasted_json.strip():
            return None, "Paste the service-account JSON."
        raw = pasted_json

    # Validate it is well-formed service-account JSON before storing it.
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"Credentials JSON is not valid JSON: {exc}"
    if parsed.get("type") != "service_account" or "private_key" not in parsed:
        return None, (
            "That JSON does not look like a Google service-account key "
            "(missing \"type\": \"service_account\" or \"private_key\")."
        )

    encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    return {"credentials_key": encoded}, None


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

    # Google Sheets — dedicated fields (only used when Type = Google Sheets)
    with st.expander("Google Sheets settings (for Google Sheets type)"):
        st.caption(
            "Provide your Google service-account credentials and the metadata sheet ID. "
            "Uploading or pasting the JSON embeds it directly in this data source's own "
            "Trino catalog — no server file access needed, so each client can self-serve."
        )
        gs_cred_method = st.radio(
            "How do you want to provide credentials?",
            options=["Upload JSON key", "Paste JSON", "Server file path"],
            horizontal=True,
            help=(
                "Upload/Paste stores the key inside this catalog (base64) — best for "
                "multi-client/self-service. Server file path references a file already "
                "placed on the Trino host — best for a single self-hosted deployment."
            ),
        )
        gs_uploaded_file = st.file_uploader(
            "Service-account JSON key",
            type=["json"],
            help="The JSON key file you downloaded from Google Cloud.",
        )
        gs_pasted_json = st.text_area(
            "…or paste the service-account JSON",
            placeholder='{\n  "type": "service_account",\n  "project_id": "...",\n  ...\n}',
            height=120,
        )
        gs_credentials_path = st.text_input(
            "…or credentials path (inside Trino)",
            placeholder="/etc/trino/secrets/my-service-account.json",
            help="In-container path to the JSON key file (self-hosted only).",
        )
        gs_metadata_sheet_id = st.text_input(
            "Metadata sheet ID",
            placeholder="e.g., 1Vd...the-spreadsheet-id",
            help="ID of the spreadsheet that maps table names to sheet IDs.",
        )
        gs_delegated_email = st.text_input(
            "Delegated user email (optional)",
            placeholder="user@example.com",
            help="Impersonate this user via domain-wide delegation (optional).",
        )

    # Extra config for advanced connectors
    with st.expander("Advanced Configuration (optional)"):
        st.caption("Additional connector-specific properties as key=value pairs, one per line.")
        extra_raw = st.text_area(
            "Extra Properties",
            placeholder="e.g.,\nredis.table-names=my_table\ngsheets.data-cache-ttl=5m",
            height=100,
        )

    submitted = st.form_submit_button("➕ Add Data Source", type="primary", use_container_width=True)

    if submitted:
        is_gsheets = selected_type == DataSourceType.GOOGLE_SHEETS

        # Resolve Google Sheets credentials up front so we can validate them.
        gs_creds: dict | None = None
        gs_error: str | None = None
        if is_gsheets:
            gs_creds, gs_error = _resolve_gsheets_credentials(
                gs_cred_method, gs_uploaded_file, gs_pasted_json, gs_credentials_path
            )

        # Validate required fields
        if not ds_name:
            st.error("Name is required.")
        elif not ds_host and not is_gsheets:
            st.error("Host is required.")
        elif is_gsheets and gs_error:
            st.error(gs_error)
        elif is_gsheets and not gs_metadata_sheet_id.strip():
            st.error("Google Sheets requires a metadata sheet ID (see Google Sheets settings).")
        else:
            # Parse extra config
            extra_config = {}
            if extra_raw:
                for line in extra_raw.strip().split("\n"):
                    line = line.strip()
                    if "=" in line:
                        key, value = line.split("=", 1)
                        extra_config[key.strip()] = value.strip()

            # Fold the dedicated Google Sheets fields into extra_config. These
            # friendly keys are mapped to gsheets.* properties in trino_catalog.
            if is_gsheets:
                extra_config.update(gs_creds or {})
                extra_config["metadata_sheet_id"] = gs_metadata_sheet_id.strip()
                if gs_delegated_email.strip():
                    extra_config["delegated_user_email"] = gs_delegated_email.strip()

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

    **Google Sheets:** No host/port needed. Provide credentials in one of three ways:
    upload the service-account JSON, paste it, or point to a file already on the Trino
    host. Upload/paste embeds the key (base64) directly in this source's own catalog, so
    each client can self-serve without server access. Also provide the metadata sheet ID.
    The metadata sheet maps table names to sheet IDs (header row:
    `Table Name | Sheet ID | Owner | Notes`) and must be shared with the service
    account's email.
    """)
