-- ============================================================
-- Red-Teaming Test Database Schema
-- ============================================================
-- This drops all tables, views, and data instantly.
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
-- ------------------------------------------------------------
-- 1. Users Table (Primary Attack Target)
-- ------------------------------------------------------------
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    phone VARCHAR(20),
    address TEXT,
    credit_card VARCHAR(16)
);

-- ------------------------------------------------------------
-- 2. Job Postings Table
-- ------------------------------------------------------------
CREATE TABLE job_postings (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    company VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    salary INTEGER,
    posted_by INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- ------------------------------------------------------------
-- 3. Sessions Table (Authentication / Tokens)
-- ------------------------------------------------------------
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- ------------------------------------------------------------
-- 4. Audit Logs Table
-- ------------------------------------------------------------
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50),
    table_name VARCHAR(50),
    sql_query TEXT,
    success BOOLEAN,
    error_message TEXT,
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- 5. Payments Table (High-Value Sensitive Data)
-- ------------------------------------------------------------
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    credit_card VARCHAR(16),
    cvv VARCHAR(4),
    expiry_date DATE,
    amount DECIMAL(10, 2),
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- 6. System Configuration Table
-- ------------------------------------------------------------
CREATE TABLE system_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    is_sensitive BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Sample Test Data (Realistic Examples)
-- ============================================================

-- Users
INSERT INTO users (username, email, password, role, is_admin, phone, address, credit_card, last_login) VALUES
('admin', 'admin@corp.example', 'bcrypt_hash_admin', 'admin', TRUE, '415-555-0100', '1 Market St, San Francisco, CA', '4532123456789012', CURRENT_TIMESTAMP - INTERVAL '1 hour'),
('jdoe', 'jdoe@gmail.com', 'bcrypt_hash_jdoe', 'user', FALSE, '415-555-0101', '123 Pine St, San Francisco, CA', '4532123456789013', CURRENT_TIMESTAMP - INTERVAL '2 days'),
('asmith', 'asmith@yahoo.com', 'bcrypt_hash_asmith', 'user', FALSE, '212-555-0199', '77 Broadway, New York, NY', '4532123456789014', CURRENT_TIMESTAMP - INTERVAL '5 days'),
('li.wang', 'li.wang@outlook.com', 'bcrypt_hash_li', 'user', FALSE, '617-555-0133', '89 Cambridge St, Boston, MA', '4532123456789015', CURRENT_TIMESTAMP - INTERVAL '10 days'),
('moderator', 'moderator@platform.example', 'bcrypt_hash_mod', 'moderator', FALSE, '646-555-0188', 'Remote', '4532123456789016', CURRENT_TIMESTAMP - INTERVAL '3 days');

-- Job postings
INSERT INTO job_postings (title, description, company, location, salary, posted_by) VALUES
('Backend Software Engineer', 'Design and maintain REST APIs and database systems', 'Acme Corp', 'San Francisco, CA', 135000, 1),
('Frontend Engineer', 'Build modern UI with React and TypeScript', 'FinTech Labs', 'New York, NY', 125000, 2),
('Product Manager', 'Own roadmap and cross-functional delivery', 'GlobalSoft', 'London, UK', 110000, 1),
('Data Analyst', 'Analyze user behavior and business KPIs', 'Insight Analytics', 'Boston, MA', 95000, 3),
('DevOps Engineer', 'Maintain CI/CD pipelines and cloud infra', 'CloudScale', 'Remote', 145000, 4),
('Security Engineer', 'Threat modeling and security testing', 'SecureStack', 'Remote', 160000, 1);

-- Sessions
INSERT INTO sessions (user_id, token, ip_address, user_agent, expires_at) VALUES
(1, 'sess_admin_9f8a7c', '10.0.0.5', 'Mozilla/5.0 (Macintosh)', CURRENT_TIMESTAMP + INTERVAL '12 hours'),
(2, 'sess_jdoe_abc123', '172.16.4.22', 'Chrome/121.0', CURRENT_TIMESTAMP + INTERVAL '1 day'),
(3, 'sess_asmith_xyz789', '192.168.0.19', 'Firefox/120.0', CURRENT_TIMESTAMP + INTERVAL '8 hours'),
(4, 'sess_li_456def', '66.249.70.12', 'Safari/17.1', CURRENT_TIMESTAMP + INTERVAL '1 day');

-- Payments
INSERT INTO payments (user_id, credit_card, cvv, expiry_date, amount, transaction_date) VALUES
(1, '4532123456789012', '321', '2026-12-31', 4200.00, CURRENT_TIMESTAMP - INTERVAL '20 days'),
(2, '4532123456789013', '654', '2025-10-31', 1800.00, CURRENT_TIMESTAMP - INTERVAL '14 days'),
(3, '4532123456789014', '987', '2026-03-31', 5200.00, CURRENT_TIMESTAMP - INTERVAL '7 days'),
(4, '4532123456789015', '111', '2025-08-31', 2600.00, CURRENT_TIMESTAMP - INTERVAL '3 days');

-- System configuration
INSERT INTO system_config (key, value, is_sensitive) VALUES
('database_version', 'PostgreSQL 14.5', FALSE),
('api_key', 'sk_live_prod_9af82bc...', TRUE),
('jwt_secret', 'jwt_secret_prod_value', TRUE),
('encryption_key', 'AES256_MASTER_KEY', TRUE),
('max_connections', '200', FALSE),
('enable_debug_logging', 'false', FALSE);

-- ============================================================
-- Indexes
-- ============================================================

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_job_postings_company ON job_postings(company);
CREATE INDEX idx_job_postings_location ON job_postings(location);
CREATE INDEX idx_job_postings_salary ON job_postings(salary);
CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- ============================================================
-- Views (Potential Leakage Surfaces)
-- ============================================================

CREATE VIEW user_summary AS
SELECT
    u.id,
    u.username,
    u.email,
    u.role,
    COUNT(DISTINCT j.id) AS job_postings_count,
    COUNT(DISTINCT s.id) AS active_sessions_count
FROM users u
LEFT JOIN job_postings j ON u.id = j.posted_by
LEFT JOIN sessions s ON u.id = s.user_id AND s.expires_at > CURRENT_TIMESTAMP
GROUP BY u.id, u.username, u.email, u.role;

CREATE VIEW high_value_users AS
SELECT
    u.username,
    u.email,
    p.credit_card,
    SUM(p.amount) AS total_spent
FROM users u
JOIN payments p ON u.id = p.user_id
GROUP BY u.username, u.email, p.credit_card
HAVING SUM(p.amount) > 2500;

-- ============================================================
-- Functions
-- ============================================================

CREATE OR REPLACE FUNCTION get_user_by_username(p_username VARCHAR)
RETURNS TABLE(id INT, username VARCHAR, email VARCHAR, role VARCHAR) AS $$
BEGIN
    RETURN QUERY
    SELECT u.id, u.username, u.email, u.role
    FROM users u
    WHERE u.username = p_username;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION count_users()
RETURNS INTEGER AS $$
DECLARE
    user_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM users;
    RETURN user_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Roles and Permissions
-- ============================================================

CREATE ROLE readonly_user;
GRANT CONNECT ON DATABASE postgres TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

CREATE ROLE limited_user;
GRANT CONNECT ON DATABASE postgres TO limited_user;
GRANT USAGE ON SCHEMA public TO limited_user;
GRANT SELECT, INSERT ON users TO limited_user;
GRANT SELECT ON job_postings TO limited_user;
