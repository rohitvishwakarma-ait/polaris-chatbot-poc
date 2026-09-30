# Banking Sample Dataset

A multi-source banking dataset for testing Polaris on a domain other than
Glass Bottle Manufacturing. Data is distributed across four sources exactly
like the original demo, so you can test cross-database federation.

## Data Layout

| Source | Table / Collection | Contents | Join key |
|--------|-------------------|----------|----------|
| **MySQL** | `banking.customers` | Customer master (name, KYC, risk) | `customer_id` |
| **PostgreSQL** | `banking.accounts` | Bank accounts (balance, type, status) | `customer_id`, `account_number` |
| **MongoDB** | `banking.transaction_logs` | Transaction history | `account_number` |
| **Redis** | `account:*`, `fraud_alert:*`, `session:*`, `dashboard:*` | Live balances, fraud alerts, sessions, KPIs | `account:` + account_number |
| **Google Sheets** | `branch_targets` | Monthly branch targets vs actuals | `branch` |

## Loading the Data

### 1. MySQL
```bash
mysql -u <user> -p < 01_mysql_customers.sql
```

### 2. PostgreSQL
```bash
createdb banking            # if it doesn't exist
psql -U <user> -d banking -f 02_postgres_accounts.sql
```

### 3. MongoDB
```bash
mongosh banking < 03_mongodb_transaction_logs.js
```

### 4. Redis
```bash
bash 04_redis_live_data.sh
# or for a Redis on a different port:
REDIS_PORT=6380 bash 04_redis_live_data.sh
```

### 5. Google Sheets
Unlike the other sources, Google Sheets data lives in actual spreadsheets.
Two CSV files are provided:

- `05_googlesheets_branch_targets.csv` — the **data** (one table: `branch_targets`)
- `06_googlesheets_metadata.csv` — the **metadata sheet** that maps table names to sheet IDs

Steps:
1. Create a Google Sheet and import `05_googlesheets_branch_targets.csv`
   (**File → Import → Upload**). Rename the tab to `branch_targets`.
2. Create a second Google Sheet and import `06_googlesheets_metadata.csv`.
   This is the *metadata sheet* — its header row must stay exactly
   `Table Name | Sheet ID | Owner | Notes`.
3. In the metadata sheet, replace `PASTE_DATA_SPREADSHEET_ID_HERE` in the
   `Sheet ID` column with the **ID of the data spreadsheet** from step 1
   (the string in its URL between `/d/` and `/edit`).
4. Share **both** spreadsheets with the service-account email
   (found as `client_email` in the key JSON), e.g.
   `trino-sheets-reader@trino-sheets-501013.iam.gserviceaccount.com`.
5. Give Polaris the **metadata sheet's ID** as the `gsheets.metadata-sheet-id`
   (via the Data Sources page → Google Sheets settings), then restart Trino.

Tip: you can also keep both the data and the metadata on separate tabs of a
single spreadsheet — in that case the `Sheet ID` value is that one
spreadsheet's ID, optionally with a tab/range suffix like `#branch_targets`.

## Configuring in Polaris

1. Open the **Data Sources** page (`http://localhost:8501/Data_Sources`)
2. (Optional) Remove the old GlassBottle data sources to keep context clean
3. Add each source:

| Name | Type | Host | Port | Database |
|------|------|------|------|----------|
| `bank_customers` | mysql | localhost | 3306 | banking |
| `bank_accounts` | postgresql | localhost | 5434 | banking |
| `bank_transactions` | mongodb | localhost | 27017 | banking |
| `bank_live` | redis | localhost | 6379 | (leave empty) |
| `gsheets` | google_sheets | (leave empty) | 0 | (leave empty) |

For `gsheets`, use the **Google Sheets settings** section: upload/paste the
service-account JSON and enter the metadata sheet ID (see step 5 above).

4. **Restart Trino** so it loads the new catalogs:
   ```bash
   docker restart polaris-trino
   ```
5. Click **☁️ Sync Metadata** on each source (except Redis relies on Trino introspection)

## Test Questions

### Single-source
- "Show me all customers with High risk rating" (MySQL)
- "Which accounts are Frozen?" (PostgreSQL)
- "Show me all failed transactions" (MongoDB)
- "Show me open fraud alerts" (Redis)
- "What is today's dashboard summary?" (Redis)
- "Which accounts have negative balance?" (PostgreSQL — loan accounts)
- "Show me branch deposit targets for March 2026" (Google Sheets)
- "Which branches beat their deposit target?" (Google Sheets — compare target vs actual)

### Cross-source (Trino federation)
- "Show me accounts along with their customer names" (PostgreSQL + MySQL)
- "Show me transactions with the account holder's city" (MongoDB + PostgreSQL + MySQL)
- "Show me accounts with their live balance from Redis" (PostgreSQL + Redis)
- "Which high-risk customers have active fraud alerts?" (MySQL + Redis)
- "Compare actual deposits per branch with the total account balance at that branch" (Google Sheets + PostgreSQL)

### Analytical
- "How many accounts does each customer have?"
- "What is the total balance per branch?"
- "Show me the largest transactions this month"
- "Which customers are not KYC verified?"
