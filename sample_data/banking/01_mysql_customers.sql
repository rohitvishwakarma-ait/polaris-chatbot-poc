-- ============================================================
-- Banking Sample Data — MySQL: customers
-- ============================================================
-- Run against your MySQL server:
--   mysql -u <user> -p < 01_mysql_customers.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS banking;
USE banking;

DROP TABLE IF EXISTS customers;
CREATE TABLE customers (
    customer_id     INT PRIMARY KEY,
    full_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(120),
    phone           VARCHAR(20),
    city            VARCHAR(60),
    kyc_status      VARCHAR(20),   -- Verified, Pending, Rejected
    customer_since  DATE,
    risk_rating     VARCHAR(10),   -- Low, Medium, High
    occupation      VARCHAR(60),
    annual_income   INT
);

INSERT INTO customers (customer_id, full_name, email, phone, city, kyc_status, customer_since, risk_rating, occupation, annual_income) VALUES
(1001, 'Aarav Sharma',     'aarav.sharma@example.com',   '9812345001', 'Mumbai',    'Verified', '2021-03-14', 'Low',    'Software Engineer', 1800000),
(1002, 'Diya Patel',       'diya.patel@example.com',     '9812345002', 'Ahmedabad', 'Verified', '2020-07-22', 'Low',    'Doctor',            2400000),
(1003, 'Rohan Verma',      'rohan.verma@example.com',    '9812345003', 'Delhi',     'Pending',  '2023-01-10', 'Medium', 'Business Owner',    3200000),
(1004, 'Ananya Iyer',      'ananya.iyer@example.com',    '9812345004', 'Chennai',   'Verified', '2019-11-05', 'Low',    'Professor',         1500000),
(1005, 'Kabir Singh',      'kabir.singh@example.com',    '9812345005', 'Pune',      'Verified', '2022-06-18', 'High',   'Trader',            5000000),
(1006, 'Isha Reddy',       'isha.reddy@example.com',     '9812345006', 'Hyderabad', 'Rejected', '2023-09-30', 'High',   'Consultant',        2800000),
(1007, 'Vivaan Nair',      'vivaan.nair@example.com',    '9812345007', 'Kochi',     'Verified', '2021-12-01', 'Low',    'Architect',         1900000),
(1008, 'Myra Gupta',       'myra.gupta@example.com',     '9812345008', 'Kolkata',   'Verified', '2020-02-14', 'Medium', 'Entrepreneur',      4200000),
(1009, 'Arjun Mehta',      'arjun.mehta@example.com',    '9812345009', 'Jaipur',    'Pending',  '2024-01-20', 'Medium', 'Lawyer',            2200000),
(1010, 'Saanvi Joshi',     'saanvi.joshi@example.com',   '9812345010', 'Surat',     'Verified', '2018-05-25', 'Low',    'Accountant',        1300000),
(1011, 'Reyansh Kapoor',   'reyansh.kapoor@example.com', '9812345011', 'Lucknow',   'Verified', '2022-08-11', 'Low',    'Teacher',           900000),
(1012, 'Aisha Khan',       'aisha.khan@example.com',     '9812345012', 'Bengaluru', 'Verified', '2021-04-03', 'Medium', 'Product Manager',   2600000),
(1013, 'Kian Desai',       'kian.desai@example.com',     '9812345013', 'Indore',    'Pending',  '2023-11-19', 'High',   'Real Estate',       3800000),
(1014, 'Zara Ali',         'zara.ali@example.com',       '9812345014', 'Nagpur',    'Verified', '2020-10-08', 'Low',    'Nurse',             800000),
(1015, 'Advait Rao',       'advait.rao@example.com',     '9812345015', 'Bhopal',    'Verified', '2019-07-16', 'Low',    'Civil Engineer',    1600000),
(1016, 'Anika Bose',       'anika.bose@example.com',     '9812345016', 'Kolkata',   'Verified', '2021-09-12', 'Medium', 'Designer',          1400000),
(1017, 'Vihaan Chauhan',   'vihaan.chauhan@example.com', '9812345017', 'Delhi',     'Verified', '2020-12-01', 'Low',    'Pilot',             3500000),
(1018, 'Navya Menon',      'navya.menon@example.com',    '9812345018', 'Chennai',   'Pending',  '2024-02-15', 'Medium', 'Journalist',        1100000),
(1019, 'Ayaan Sheikh',     'ayaan.sheikh@example.com',   '9812345019', 'Hyderabad', 'Verified', '2019-04-08', 'Low',    'Pharmacist',        1250000),
(1020, 'Kiara Malhotra',   'kiara.malhotra@example.com', '9812345020', 'Mumbai',    'Verified', '2022-01-30', 'High',   'Investor',          6500000),
(1021, 'Shaurya Bhat',     'shaurya.bhat@example.com',   '9812345021', 'Pune',      'Verified', '2021-06-22', 'Low',    'Data Scientist',    2100000),
(1022, 'Anaya Pillai',     'anaya.pillai@example.com',   '9812345022', 'Kochi',     'Verified', '2020-08-17', 'Medium', 'HR Manager',        1350000),
(1023, 'Dhruv Saxena',     'dhruv.saxena@example.com',   '9812345023', 'Jaipur',    'Rejected', '2023-10-05', 'High',   'Crypto Trader',     4800000),
(1024, 'Riya Agarwal',     'riya.agarwal@example.com',   '9812345024', 'Lucknow',   'Verified', '2019-02-19', 'Low',    'Dentist',           2000000),
(1025, 'Aryan Choudhary',  'aryan.choudhary@example.com','9812345025', 'Bengaluru', 'Verified', '2022-11-11', 'Medium', 'Startup Founder',   3600000),
(1026, 'Tara Nanda',       'tara.nanda@example.com',     '9812345026', 'Nagpur',    'Verified', '2021-03-27', 'Low',    'Physiotherapist',   950000),
(1027, 'Ishaan Ghosh',     'ishaan.ghosh@example.com',   '9812345027', 'Kolkata',   'Pending',  '2024-03-01', 'Medium', 'Chef',              1050000),
(1028, 'Mira Kulkarni',    'mira.kulkarni@example.com',  '9812345028', 'Pune',      'Verified', '2020-05-14', 'Low',    'Marketing Lead',    1700000),
(1029, 'Veer Malhotra',    'veer.malhotra@example.com',  '9812345029', 'Delhi',     'Verified', '2018-09-09', 'High',   'Film Producer',     7200000),
(1030, 'Sara Fernandes',   'sara.fernandes@example.com', '9812345030', 'Mumbai',    'Verified', '2021-07-07', 'Low',    'Air Hostess',       1150000),
(1031, 'Kabir Anand',      'kabir.anand@example.com',    '9812345031', 'Chennai',   'Verified', '2022-04-19', 'Medium', 'Banker',            2300000),
(1032, 'Ela Deshpande',    'ela.deshpande@example.com',  '9812345032', 'Hyderabad', 'Pending',  '2023-12-22', 'Medium', 'Interior Designer', 1450000),
(1033, 'Rudra Shetty',     'rudra.shetty@example.com',   '9812345033', 'Bengaluru', 'Verified', '2019-10-30', 'Low',    'Restaurant Owner',  2900000),
(1034, 'Aadhya Rao',       'aadhya.rao@example.com',     '9812345034', 'Surat',     'Verified', '2020-06-11', 'Low',    'Textile Merchant',  3100000),
(1035, 'Yuvan Kapoor',     'yuvan.kapoor@example.com',   '9812345035', 'Jaipur',    'Verified', '2021-11-25', 'High',   'Jeweller',          5500000),
(1036, 'Pari Trivedi',     'pari.trivedi@example.com',   '9812345036', 'Ahmedabad', 'Verified', '2022-02-08', 'Low',    'School Principal',  1250000),
(1037, 'Neel Bajaj',       'neel.bajaj@example.com',     '9812345037', 'Mumbai',    'Pending',  '2024-01-05', 'Medium', 'Stock Broker',      4100000),
(1038, 'Siya Kaur',        'siya.kaur@example.com',      '9812345038', 'Lucknow',   'Verified', '2020-03-16', 'Low',    'Veterinarian',      1350000),
(1039, 'Ehan Qureshi',     'ehan.qureshi@example.com',   '9812345039', 'Delhi',     'Verified', '2019-08-21', 'Medium', 'Import Exporter',   3900000),
(1040, 'Aarohi Sinha',     'aarohi.sinha@example.com',   '9812345040', 'Kolkata',   'Verified', '2021-05-29', 'Low',    'Graphic Artist',    980000);
