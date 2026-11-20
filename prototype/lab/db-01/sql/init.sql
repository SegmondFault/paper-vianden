-- VulnCastle - Intentionally Vulnerable Database (Educational Purpose Only)

CREATE DATABASE IF NOT EXISTS acme_corp;
USE acme_corp;

-- Customer data (sensitive information disclosure target)
CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    credit_card VARCHAR(20),
    ssn VARCHAR(11),
    address TEXT
);

INSERT INTO customers (name, email, phone, credit_card, ssn, address) VALUES
('John Smith', 'john.smith@example.com', '555-0101', '4111-1111-1111-1111', '123-45-6789', '123 Main St, Springfield'),
('Jane Doe', 'jane.doe@example.com', '555-0102', '4222-2222-2222-2222', '987-65-4321', '456 Oak Ave, Shelbyville'),
('Bob Wilson', 'bob.wilson@example.com', '555-0103', '4333-3333-3333-3333', '456-78-9012', '789 Pine Rd, Capital City'),
('Alice Brown', 'alice.brown@example.com', '555-0104', '4444-4444-4444-4444', '321-54-9876', '321 Elm St, Ogdenville'),
('Charlie Davis', 'charlie.d@example.com', '555-0105', '4555-5555-5555-5555', '654-32-1098', '654 Maple Dr, North Haverbrook');

-- Internal credentials table (lateral movement target)
CREATE TABLE service_accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    service_name VARCHAR(50),
    username VARCHAR(50),
    password VARCHAR(100),
    host VARCHAR(100),
    notes TEXT
);

INSERT INTO service_accounts (service_name, username, password, host, notes) VALUES
('Samba FileShare', 'sysadmin', 'FileShare#2024', 'file-01.internal', 'Public/backups writable; confidential share read-only'),
('Redis Cache', '', '', 'admin-01.internal:6379', 'No authentication required'),
('Backup SSH', 'backup', 'backup', 'vpn-gw-01.internal', 'Used for automated backups'),
('Admin Panel', 'administrator', 'Admin!Panel99', 'admin-01.internal:8080', 'Web admin interface');

-- Weak permissions: allow remote root login
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY 'S3cretDB!2024' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON *.* TO 'app_user'@'%' IDENTIFIED BY 'S3cretDB!2024';
FLUSH PRIVILEGES;
