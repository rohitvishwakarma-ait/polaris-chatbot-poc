#!/usr/bin/env bash
# ============================================================
# Banking Sample Data — Redis: live operational data
# ============================================================
# Real-time banking state: live account balances, fraud alerts,
# active login sessions, and dashboard KPIs.
#
# Usage:
#   bash 04_redis_live_data.sh              # uses localhost:6379
#   REDIS_PORT=6380 bash 04_redis_live_data.sh
# ============================================================

REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_CLI="redis-cli -p ${REDIS_PORT}"

echo "Loading banking live data into Redis on port ${REDIS_PORT}..."

# ---- Live account balances (updated in real-time) ----
$REDIS_CLI SET "account:ACC0000005001" '{"account_number":"ACC0000005001","balance":152340.75,"status":"Active","last_txn":"2026-08-19"}'
$REDIS_CLI SET "account:ACC0000005005" '{"account_number":"ACC0000005005","balance":234100.25,"status":"Active","last_txn":"2026-08-19"}'
$REDIS_CLI SET "account:ACC0000005006" '{"account_number":"ACC0000005006","balance":-450000.00,"status":"Active","last_txn":"2026-08-10"}'
$REDIS_CLI SET "account:ACC0000005007" '{"account_number":"ACC0000005007","balance":5230.00,"status":"Frozen","last_txn":"2026-08-05"}'
$REDIS_CLI SET "account:ACC0000005008" '{"account_number":"ACC0000005008","balance":678900.00,"status":"Active","last_txn":"2026-08-20"}'
$REDIS_CLI SET "account:ACC0000005020" '{"account_number":"ACC0000005020","balance":890500.00,"status":"Active","last_txn":"2026-08-21"}'
$REDIS_CLI SET "account:ACC0000005024" '{"account_number":"ACC0000005024","balance":3400000.00,"status":"Active","last_txn":"2026-08-21"}'
$REDIS_CLI SET "account:ACC0000005028" '{"account_number":"ACC0000005028","balance":780000.00,"status":"Frozen","last_txn":"2026-08-13"}'
$REDIS_CLI SET "account:ACC0000005035" '{"account_number":"ACC0000005035","balance":6700000.00,"status":"Active","last_txn":"2026-08-23"}'
$REDIS_CLI SET "account:ACC0000005045" '{"account_number":"ACC0000005045","balance":1230000.00,"status":"Active","last_txn":"2026-08-24"}'
$REDIS_CLI SET "account:ACC0000005050" '{"account_number":"ACC0000005050","balance":8900.00,"status":"Frozen","last_txn":"2026-08-25"}'

# ---- Fraud alerts (live monitoring) ----
$REDIS_CLI SET "fraud_alert:FA001" '{"alert_id":"FA001","account_number":"ACC0000005006","reason":"Large unusual transfer","severity":"High","amount":250000,"flagged_at":"2026-08-10T09:15:00","status":"Open"}'
$REDIS_CLI SET "fraud_alert:FA002" '{"alert_id":"FA002","account_number":"ACC0000005007","reason":"Multiple failed attempts","severity":"Medium","amount":4800,"flagged_at":"2026-08-05T14:22:00","status":"Investigating"}'
$REDIS_CLI SET "fraud_alert:FA003" '{"alert_id":"FA003","account_number":"ACC0000005008","reason":"High-value RTGS to new payee","severity":"High","amount":320000,"flagged_at":"2026-08-03T11:05:00","status":"Open"}'
$REDIS_CLI SET "fraud_alert:FA004" '{"alert_id":"FA004","account_number":"ACC0000005028","reason":"Crypto exchange transfer","severity":"High","amount":500000,"flagged_at":"2026-08-13T16:40:00","status":"Open"}'
$REDIS_CLI SET "fraud_alert:FA005" '{"alert_id":"FA005","account_number":"ACC0000005035","reason":"Suspicious large debit","severity":"High","amount":1500000,"flagged_at":"2026-08-23T10:30:00","status":"Investigating"}'
$REDIS_CLI SET "fraud_alert:FA006" '{"alert_id":"FA006","account_number":"ACC0000005050","reason":"Failed transaction spike","severity":"Low","amount":2300,"flagged_at":"2026-08-25T12:00:00","status":"Closed"}'

# ---- Active login sessions ----
$REDIS_CLI SET "session:SES9001" '{"session_id":"SES9001","customer_id":1001,"channel":"MobileApp","login_time":"2026-08-25T08:30:00","ip":"49.36.12.5","active":true}'
$REDIS_CLI SET "session:SES9002" '{"session_id":"SES9002","customer_id":1005,"channel":"NetBanking","login_time":"2026-08-25T09:10:00","ip":"103.21.58.9","active":true}'
$REDIS_CLI SET "session:SES9003" '{"session_id":"SES9003","customer_id":1008,"channel":"MobileApp","login_time":"2026-08-25T07:45:00","ip":"157.35.88.2","active":false}'
$REDIS_CLI SET "session:SES9004" '{"session_id":"SES9004","customer_id":1020,"channel":"NetBanking","login_time":"2026-08-25T10:05:00","ip":"106.51.30.1","active":true}'
$REDIS_CLI SET "session:SES9005" '{"session_id":"SES9005","customer_id":1029,"channel":"MobileApp","login_time":"2026-08-25T11:20:00","ip":"122.15.44.7","active":true}'
$REDIS_CLI SET "session:SES9006" '{"session_id":"SES9006","customer_id":1035,"channel":"NetBanking","login_time":"2026-08-25T06:50:00","ip":"117.99.12.8","active":false}'

# ---- Dashboard KPIs ----
$REDIS_CLI SET "dashboard:summary" '{"total_deposits_today":7285000,"total_withdrawals_today":6912300,"active_accounts":42,"frozen_accounts":3,"open_fraud_alerts":3,"transactions_today":50}'
$REDIS_CLI SET "dashboard:channels" '{"UPI":13,"Card":9,"NEFT":11,"RTGS":15,"IMPS":2}'
$REDIS_CLI SET "dashboard:branches" '{"Mumbai-BKC":2,"Delhi-CP":6,"Chennai-TNagar":4,"Pune-Kothrud":4,"Bengaluru-MG":4}'

echo ""
echo "Done. Loaded keys:"
$REDIS_CLI KEYS "*" | sort
