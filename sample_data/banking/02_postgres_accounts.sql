-- ============================================================
-- Banking Sample Data — PostgreSQL: accounts
-- ============================================================
-- Run against your PostgreSQL server:
--   psql -U <user> -d banking -f 02_postgres_accounts.sql
-- (create the database first: CREATE DATABASE banking;)
-- ============================================================

DROP TABLE IF EXISTS accounts;
CREATE TABLE accounts (
    account_id      INTEGER PRIMARY KEY,
    account_number  VARCHAR(20) NOT NULL,
    customer_id     INTEGER NOT NULL,          -- matches MySQL customers.customer_id
    account_type    VARCHAR(20),               -- Savings, Current, FixedDeposit, Loan
    balance         NUMERIC(14,2),
    currency        VARCHAR(5),
    branch          VARCHAR(60),
    status          VARCHAR(20),               -- Active, Dormant, Frozen, Closed
    opened_date     DATE,
    interest_rate   NUMERIC(4,2)
);

INSERT INTO accounts (account_id, account_number, customer_id, account_type, balance, currency, branch, status, opened_date, interest_rate) VALUES
(5001, 'ACC0000005001', 1001, 'Savings',      152340.75,  'INR', 'Mumbai-Andheri',   'Active',  '2021-03-15', 3.50),
(5002, 'ACC0000005002', 1001, 'FixedDeposit', 500000.00,  'INR', 'Mumbai-Andheri',   'Active',  '2022-01-10', 6.75),
(5003, 'ACC0000005003', 1002, 'Savings',      89250.00,   'INR', 'Ahmedabad-CG',     'Active',  '2020-07-23', 3.50),
(5004, 'ACC0000005004', 1003, 'Current',      12500.50,   'INR', 'Delhi-CP',         'Dormant', '2023-01-12', 0.00),
(5005, 'ACC0000005005', 1004, 'Savings',      234100.25,  'INR', 'Chennai-TNagar',   'Active',  '2019-11-06', 3.50),
(5006, 'ACC0000005006', 1005, 'Loan',        -450000.00,  'INR', 'Pune-Kothrud',     'Active',  '2022-06-20', 10.50),
(5007, 'ACC0000005007', 1005, 'Savings',      5230.00,    'INR', 'Pune-Kothrud',     'Frozen',  '2022-06-20', 3.50),
(5008, 'ACC0000005008', 1007, 'Current',      678900.00,  'INR', 'Kochi-MG',         'Active',  '2021-12-02', 0.00),
(5009, 'ACC0000005009', 1008, 'Savings',      45600.00,   'INR', 'Kolkata-Park',     'Active',  '2020-02-15', 3.50),
(5010, 'ACC0000005010', 1010, 'FixedDeposit', 1000000.00, 'INR', 'Surat-Ring',       'Active',  '2018-05-26', 7.00),
(5011, 'ACC0000005011', 1011, 'Savings',      78900.50,   'INR', 'Lucknow-Hazrat',   'Active',  '2022-08-12', 3.50),
(5012, 'ACC0000005012', 1012, 'Current',      156700.00,  'INR', 'Bengaluru-MG',     'Active',  '2021-04-04', 0.00),
(5013, 'ACC0000005013', 1013, 'Savings',      3400.00,    'INR', 'Indore-Vijay',     'Dormant', '2023-11-20', 3.50),
(5014, 'ACC0000005014', 1014, 'Savings',      92300.75,   'INR', 'Nagpur-Sitabuldi', 'Active',  '2020-10-09', 3.50),
(5015, 'ACC0000005015', 1015, 'FixedDeposit', 750000.00,  'INR', 'Bhopal-MP',        'Active',  '2019-07-17', 6.75),
(5016, 'ACC0000005016', 1004, 'Current',      34500.00,   'INR', 'Chennai-TNagar',   'Active',  '2020-03-11', 0.00),
(5017, 'ACC0000005017', 1002, 'Loan',        -220000.00,  'INR', 'Ahmedabad-CG',     'Active',  '2023-02-18', 9.75),
(5018, 'ACC0000005018', 1009, 'Savings',      18700.00,   'INR', 'Jaipur-MI',        'Active',  '2024-01-22', 3.50),
(5019, 'ACC0000005019', 1016, 'Savings',      67800.00,   'INR', 'Kolkata-Park',     'Active',  '2021-09-13', 3.50),
(5020, 'ACC0000005020', 1017, 'Current',      890500.00,  'INR', 'Delhi-CP',         'Active',  '2020-12-02', 0.00),
(5021, 'ACC0000005021', 1017, 'FixedDeposit', 2000000.00, 'INR', 'Delhi-CP',         'Active',  '2021-01-15', 7.00),
(5022, 'ACC0000005022', 1018, 'Savings',      23400.00,   'INR', 'Chennai-TNagar',   'Active',  '2024-02-16', 3.50),
(5023, 'ACC0000005023', 1019, 'Savings',      112000.00,  'INR', 'Hyderabad-Banjara','Active',  '2019-04-09', 3.50),
(5024, 'ACC0000005024', 1020, 'Current',      3400000.00, 'INR', 'Mumbai-BKC',       'Active',  '2022-01-31', 0.00),
(5025, 'ACC0000005025', 1020, 'FixedDeposit', 5000000.00, 'INR', 'Mumbai-BKC',       'Active',  '2022-02-10', 7.25),
(5026, 'ACC0000005026', 1021, 'Savings',      145600.00,  'INR', 'Pune-Kothrud',     'Active',  '2021-06-23', 3.50),
(5027, 'ACC0000005027', 1022, 'Savings',      56700.00,   'INR', 'Kochi-MG',         'Active',  '2020-08-18', 3.50),
(5028, 'ACC0000005028', 1023, 'Current',      780000.00,  'INR', 'Jaipur-MI',        'Frozen',  '2023-10-06', 0.00),
(5029, 'ACC0000005029', 1024, 'Savings',      198000.00,  'INR', 'Lucknow-Hazrat',   'Active',  '2019-02-20', 3.50),
(5030, 'ACC0000005030', 1025, 'Current',      450000.00,  'INR', 'Bengaluru-MG',     'Active',  '2022-11-12', 0.00),
(5031, 'ACC0000005031', 1025, 'Loan',        -1200000.00, 'INR', 'Bengaluru-MG',     'Active',  '2023-01-05', 11.00),
(5032, 'ACC0000005032', 1026, 'Savings',      34500.00,   'INR', 'Nagpur-Sitabuldi', 'Active',  '2021-03-28', 3.50),
(5033, 'ACC0000005033', 1027, 'Savings',      12300.00,   'INR', 'Kolkata-Park',     'Dormant', '2024-03-02', 3.50),
(5034, 'ACC0000005034', 1028, 'Savings',      167800.00,  'INR', 'Pune-Kothrud',     'Active',  '2020-05-15', 3.50),
(5035, 'ACC0000005035', 1029, 'Current',      6700000.00, 'INR', 'Delhi-CP',         'Active',  '2018-09-10', 0.00),
(5036, 'ACC0000005036', 1029, 'FixedDeposit', 10000000.00,'INR', 'Delhi-CP',         'Active',  '2019-01-20', 7.50),
(5037, 'ACC0000005037', 1030, 'Savings',      45000.00,   'INR', 'Mumbai-Andheri',   'Active',  '2021-07-08', 3.50),
(5038, 'ACC0000005038', 1031, 'Savings',      234500.00,  'INR', 'Chennai-TNagar',   'Active',  '2022-04-20', 3.50),
(5039, 'ACC0000005039', 1032, 'Current',      78000.00,   'INR', 'Hyderabad-Banjara','Active',  '2023-12-23', 0.00),
(5040, 'ACC0000005040', 1033, 'Current',      560000.00,  'INR', 'Bengaluru-MG',     'Active',  '2019-10-31', 0.00),
(5041, 'ACC0000005041', 1034, 'FixedDeposit', 1500000.00, 'INR', 'Surat-Ring',       'Active',  '2020-06-12', 7.00),
(5042, 'ACC0000005042', 1035, 'Savings',      890000.00,  'INR', 'Jaipur-MI',        'Active',  '2021-11-26', 3.50),
(5043, 'ACC0000005043', 1035, 'Loan',        -750000.00,  'INR', 'Jaipur-MI',        'Active',  '2022-03-15', 10.25),
(5044, 'ACC0000005044', 1036, 'Savings',      67000.00,   'INR', 'Ahmedabad-CG',     'Active',  '2022-02-09', 3.50),
(5045, 'ACC0000005045', 1037, 'Current',      1230000.00, 'INR', 'Mumbai-BKC',       'Active',  '2024-01-06', 0.00),
(5046, 'ACC0000005046', 1038, 'Savings',      45600.00,   'INR', 'Lucknow-Hazrat',   'Active',  '2020-03-17', 3.50),
(5047, 'ACC0000005047', 1039, 'Current',      670000.00,  'INR', 'Delhi-CP',         'Active',  '2019-08-22', 0.00),
(5048, 'ACC0000005048', 1040, 'Savings',      23400.00,   'INR', 'Kolkata-Park',     'Active',  '2021-05-30', 3.50),
(5049, 'ACC0000005049', 1003, 'FixedDeposit', 300000.00,  'INR', 'Delhi-CP',         'Active',  '2023-05-10', 6.75),
(5050, 'ACC0000005050', 1006, 'Savings',      8900.00,    'INR', 'Hyderabad-Banjara','Frozen',  '2023-09-30', 3.50);
