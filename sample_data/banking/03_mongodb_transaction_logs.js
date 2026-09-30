// ============================================================
// Banking Sample Data — MongoDB: transaction_logs
// ============================================================
// Run against your MongoDB server:
//   mongosh banking < 03_mongodb_transaction_logs.js
// ============================================================

db = db.getSiblingDB("banking");
db.transaction_logs.drop();

db.transaction_logs.insertMany([
  { txn_id: "TXN100001", account_number: "ACC0000005001", type: "Debit",  amount: 2500.00,  channel: "UPI",  merchant: "Amazon",         txn_date: "2026-08-01", status: "Success" },
  { txn_id: "TXN100002", account_number: "ACC0000005001", type: "Credit", amount: 45000.00, channel: "NEFT", merchant: "Salary Credit",  txn_date: "2026-08-01", status: "Success" },
  { txn_id: "TXN100003", account_number: "ACC0000005003", type: "Debit",  amount: 1200.00,  channel: "Card", merchant: "BigBazaar",      txn_date: "2026-08-02", status: "Success" },
  { txn_id: "TXN100004", account_number: "ACC0000005005", type: "Debit",  amount: 89000.00, channel: "RTGS", merchant: "Property Pay",   txn_date: "2026-08-02", status: "Success" },
  { txn_id: "TXN100005", account_number: "ACC0000005006", type: "Credit", amount: 15000.00, channel: "UPI",  merchant: "Loan EMI",       txn_date: "2026-08-03", status: "Success" },
  { txn_id: "TXN100006", account_number: "ACC0000005008", type: "Debit",  amount: 320000.00,channel: "RTGS", merchant: "Vendor Payment", txn_date: "2026-08-03", status: "Pending" },
  { txn_id: "TXN100007", account_number: "ACC0000005009", type: "Debit",  amount: 500.00,   channel: "UPI",  merchant: "Swiggy",         txn_date: "2026-08-04", status: "Success" },
  { txn_id: "TXN100008", account_number: "ACC0000005005", type: "Credit", amount: 12000.00, channel: "IMPS", merchant: "Refund",         txn_date: "2026-08-04", status: "Success" },
  { txn_id: "TXN100009", account_number: "ACC0000005012", type: "Debit",  amount: 75000.00, channel: "NEFT", merchant: "Supplier",       txn_date: "2026-08-05", status: "Success" },
  { txn_id: "TXN100010", account_number: "ACC0000005007", type: "Debit",  amount: 4800.00,  channel: "Card", merchant: "Flipkart",       txn_date: "2026-08-05", status: "Failed" },
  { txn_id: "TXN100011", account_number: "ACC0000005001", type: "Debit",  amount: 999.00,   channel: "UPI",  merchant: "Netflix",        txn_date: "2026-08-06", status: "Success" },
  { txn_id: "TXN100012", account_number: "ACC0000005014", type: "Credit", amount: 30000.00, channel: "NEFT", merchant: "Salary Credit",  txn_date: "2026-08-06", status: "Success" },
  { txn_id: "TXN100013", account_number: "ACC0000005011", type: "Debit",  amount: 2100.00,  channel: "Card", merchant: "Reliance",       txn_date: "2026-08-07", status: "Success" },
  { txn_id: "TXN100014", account_number: "ACC0000005008", type: "Debit",  amount: 150000.00,channel: "RTGS", merchant: "Vendor Payment", txn_date: "2026-08-07", status: "Success" },
  { txn_id: "TXN100015", account_number: "ACC0000005005", type: "Debit",  amount: 60000.00, channel: "Card", merchant: "Jewellery",      txn_date: "2026-08-08", status: "Success" },
  { txn_id: "TXN100016", account_number: "ACC0000005012", type: "Credit", amount: 200000.00,channel: "RTGS", merchant: "Client Payment", txn_date: "2026-08-08", status: "Success" },
  { txn_id: "TXN100017", account_number: "ACC0000005003", type: "Debit",  amount: 750.00,   channel: "UPI",  merchant: "Zomato",         txn_date: "2026-08-09", status: "Success" },
  { txn_id: "TXN100018", account_number: "ACC0000005015", type: "Credit", amount: 50000.00, channel: "NEFT", merchant: "FD Interest",    txn_date: "2026-08-09", status: "Success" },
  { txn_id: "TXN100019", account_number: "ACC0000005006", type: "Debit",  amount: 250000.00,channel: "RTGS", merchant: "Suspicious",     txn_date: "2026-08-10", status: "Success" },
  { txn_id: "TXN100020", account_number: "ACC0000005018", type: "Debit",  amount: 1500.00,  channel: "UPI",  merchant: "Uber",           txn_date: "2026-08-10", status: "Success" },
  { txn_id: "TXN100021", account_number: "ACC0000005020", type: "Debit",  amount: 450000.00,channel: "RTGS", merchant: "Aircraft Parts", txn_date: "2026-08-11", status: "Success" },
  { txn_id: "TXN100022", account_number: "ACC0000005024", type: "Credit", amount: 1200000.00,channel:"RTGS", merchant: "Investment Ret", txn_date: "2026-08-11", status: "Success" },
  { txn_id: "TXN100023", account_number: "ACC0000005024", type: "Debit",  amount: 890000.00,channel: "RTGS", merchant: "Stock Purchase", txn_date: "2026-08-12", status: "Success" },
  { txn_id: "TXN100024", account_number: "ACC0000005026", type: "Debit",  amount: 3400.00,  channel: "Card", merchant: "Croma",          txn_date: "2026-08-12", status: "Success" },
  { txn_id: "TXN100025", account_number: "ACC0000005029", type: "Credit", amount: 25000.00, channel: "NEFT", merchant: "Clinic Income",  txn_date: "2026-08-13", status: "Success" },
  { txn_id: "TXN100026", account_number: "ACC0000005028", type: "Debit",  amount: 500000.00,channel: "RTGS", merchant: "Crypto Exchange",txn_date: "2026-08-13", status: "Success" },
  { txn_id: "TXN100027", account_number: "ACC0000005030", type: "Debit",  amount: 120000.00,channel: "NEFT", merchant: "Office Rent",    txn_date: "2026-08-14", status: "Success" },
  { txn_id: "TXN100028", account_number: "ACC0000005031", type: "Credit", amount: 40000.00, channel: "UPI",  merchant: "Loan EMI",       txn_date: "2026-08-14", status: "Success" },
  { txn_id: "TXN100029", account_number: "ACC0000005035", type: "Debit",  amount: 2500000.00,channel:"RTGS", merchant: "Film Budget",    txn_date: "2026-08-15", status: "Success" },
  { txn_id: "TXN100030", account_number: "ACC0000005035", type: "Credit", amount: 5000000.00,channel:"RTGS", merchant: "Distributor",    txn_date: "2026-08-15", status: "Success" },
  { txn_id: "TXN100031", account_number: "ACC0000005038", type: "Debit",  amount: 8900.00,  channel: "Card", merchant: "Apple Store",    txn_date: "2026-08-16", status: "Success" },
  { txn_id: "TXN100032", account_number: "ACC0000005040", type: "Debit",  amount: 67000.00, channel: "NEFT", merchant: "Food Supplier",  txn_date: "2026-08-16", status: "Success" },
  { txn_id: "TXN100033", account_number: "ACC0000005042", type: "Credit", amount: 150000.00,channel: "IMPS", merchant: "Gold Sale",      txn_date: "2026-08-17", status: "Success" },
  { txn_id: "TXN100034", account_number: "ACC0000005043", type: "Credit", amount: 60000.00, channel: "UPI",  merchant: "Loan EMI",       txn_date: "2026-08-17", status: "Success" },
  { txn_id: "TXN100035", account_number: "ACC0000005045", type: "Debit",  amount: 340000.00,channel: "RTGS", merchant: "Stock Trade",    txn_date: "2026-08-18", status: "Pending" },
  { txn_id: "TXN100036", account_number: "ACC0000005047", type: "Debit",  amount: 230000.00,channel: "RTGS", merchant: "Import Duty",    txn_date: "2026-08-18", status: "Success" },
  { txn_id: "TXN100037", account_number: "ACC0000005001", type: "Debit",  amount: 1800.00,  channel: "UPI",  merchant: "BookMyShow",     txn_date: "2026-08-19", status: "Success" },
  { txn_id: "TXN100038", account_number: "ACC0000005005", type: "Debit",  amount: 5600.00,  channel: "Card", merchant: "Myntra",         txn_date: "2026-08-19", status: "Success" },
  { txn_id: "TXN100039", account_number: "ACC0000005008", type: "Credit", amount: 500000.00,channel: "RTGS", merchant: "Project Payment",txn_date: "2026-08-20", status: "Success" },
  { txn_id: "TXN100040", account_number: "ACC0000005012", type: "Debit",  amount: 34000.00, channel: "NEFT", merchant: "Cloud Services", txn_date: "2026-08-20", status: "Success" },
  { txn_id: "TXN100041", account_number: "ACC0000005020", type: "Debit",  amount: 12000.00, channel: "Card", merchant: "Hotel Taj",      txn_date: "2026-08-21", status: "Success" },
  { txn_id: "TXN100042", account_number: "ACC0000005024", type: "Debit",  amount: 78000.00, channel: "UPI",  merchant: "Car Service",    txn_date: "2026-08-21", status: "Success" },
  { txn_id: "TXN100043", account_number: "ACC0000005026", type: "Credit", amount: 21000.00, channel: "NEFT", merchant: "Freelance Pay",  txn_date: "2026-08-22", status: "Success" },
  { txn_id: "TXN100044", account_number: "ACC0000005030", type: "Debit",  amount: 250000.00,channel: "RTGS", merchant: "Equipment",      txn_date: "2026-08-22", status: "Success" },
  { txn_id: "TXN100045", account_number: "ACC0000005035", type: "Debit",  amount: 1500000.00,channel:"RTGS", merchant: "Suspicious",     txn_date: "2026-08-23", status: "Success" },
  { txn_id: "TXN100046", account_number: "ACC0000005038", type: "Credit", amount: 45000.00, channel: "NEFT", merchant: "Salary Credit",  txn_date: "2026-08-23", status: "Success" },
  { txn_id: "TXN100047", account_number: "ACC0000005042", type: "Debit",  amount: 12000.00, channel: "Card", merchant: "Tanishq",        txn_date: "2026-08-24", status: "Success" },
  { txn_id: "TXN100048", account_number: "ACC0000005045", type: "Debit",  amount: 560000.00,channel: "RTGS", merchant: "Stock Trade",    txn_date: "2026-08-24", status: "Success" },
  { txn_id: "TXN100049", account_number: "ACC0000005047", type: "Credit", amount: 340000.00,channel: "RTGS", merchant: "Export Revenue", txn_date: "2026-08-25", status: "Success" },
  { txn_id: "TXN100050", account_number: "ACC0000005050", type: "Debit",  amount: 2300.00,  channel: "UPI",  merchant: "Grocery",        txn_date: "2026-08-25", status: "Failed" }
]);

print("Inserted " + db.transaction_logs.countDocuments() + " transaction logs");
