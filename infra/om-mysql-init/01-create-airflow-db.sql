-- Create the Airflow database used by the OpenMetadata Ingestion container
CREATE DATABASE IF NOT EXISTS airflow_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON airflow_db.* TO 'openmetadata'@'%';
FLUSH PRIVILEGES;
