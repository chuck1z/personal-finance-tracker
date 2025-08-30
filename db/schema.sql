-- backend/src/db/schema.sql
-- Bank OCR Database Schema
-- PostgreSQL Database Schema for Bank Statement OCR System

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables if they exist (for clean installation)
DROP TABLE IF EXISTS processing_logs CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS bank_statements CASCADE;
DROP TABLE IF EXISTS transaction_categories CASCADE;
DROP TABLE IF EXISTS banks CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- =============================================
-- Users Table
-- =============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index on email for faster lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- =============================================
-- Banks Table
-- =============================================
CREATE TABLE banks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    code VARCHAR(50) UNIQUE,
    date_format VARCHAR(50),
    statement_patterns JSONB,
    config_json JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index on bank code
CREATE INDEX idx_banks_code ON banks(code);
CREATE INDEX idx_banks_active ON banks(is_active);

-- =============================================
-- Transaction Categories Table (Self-referential)
-- =============================================
CREATE TABLE transaction_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    parent_id UUID REFERENCES transaction_categories(id) ON DELETE CASCADE,
    keywords JSONB,
    rules_json JSONB,
    color VARCHAR(7),
    icon VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for categories
CREATE INDEX idx_categories_parent ON transaction_categories(parent_id);
CREATE INDEX idx_categories_name ON transaction_categories(name);

-- =============================================
-- Bank Statements Table
-- =============================================
CREATE TABLE bank_statements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- File information
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    file_size INTEGER,
    file_type VARCHAR(50),
    
    -- Account information
    account_number VARCHAR(50),
    account_holder_name VARCHAR(255),
    bank_name VARCHAR(255),
    statement_period_start DATE,
    statement_period_end DATE,
    
    -- Balance information
    opening_balance DECIMAL(12, 2),
    closing_balance DECIMAL(12, 2),
    total_credits DECIMAL(12, 2),
    total_debits DECIMAL(12, 2),
    
    -- Metadata
    raw_text TEXT,
    account_info_json JSONB,
    processing_status VARCHAR(50) DEFAULT 'pending',
    processing_error TEXT,
    
    -- Timestamps
    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT check_processing_status CHECK (
        processing_status IN ('pending', 'processing', 'completed', 'failed')
    )
);

-- Create indexes for bank_statements
CREATE INDEX idx_user_statements ON bank_statements(user_id);
CREATE INDEX idx_processing_status ON bank_statements(processing_status);
CREATE INDEX idx_statement_period ON bank_statements(statement_period_start, statement_period_end);
CREATE INDEX idx_account_number ON bank_statements(account_number);
CREATE INDEX idx_uploaded_at ON bank_statements(uploaded_at DESC);

-- =============================================
-- Transactions Table
-- =============================================
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    statement_id UUID NOT NULL REFERENCES bank_statements(id) ON DELETE CASCADE,
    
    -- Transaction details
    transaction_date DATE,
    posting_date DATE,
    description TEXT,
    reference_number VARCHAR(100),
    
    -- Amount information
    amount DECIMAL(12, 2) NOT NULL,
    transaction_type VARCHAR(20),
    balance DECIMAL(12, 2),
    
    -- Categorization
    category VARCHAR(100),
    subcategory VARCHAR(100),
    merchant_name VARCHAR(255),
    
    -- Additional metadata
    raw_text TEXT,
    metadata_json JSONB,
    confidence_score FLOAT,
    
    -- Flags
    is_pending BOOLEAN DEFAULT FALSE,
    is_flagged BOOLEAN DEFAULT FALSE,
    flag_reason VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT check_transaction_type CHECK (
        transaction_type IN ('credit', 'debit')
    ),
    CONSTRAINT check_confidence_score CHECK (
        confidence_score >= 0 AND confidence_score <= 1
    )
);

-- Create indexes for transactions
CREATE INDEX idx_transaction_date ON transactions(transaction_date);
CREATE INDEX idx_amount ON transactions(amount);
CREATE INDEX idx_category ON transactions(category);
CREATE INDEX idx_statement_date ON transactions(statement_id, transaction_date);
CREATE INDEX idx_transaction_type ON transactions(transaction_type);
CREATE INDEX idx_merchant_name ON transactions(merchant_name);
CREATE INDEX idx_flagged_transactions ON transactions(is_flagged) WHERE is_flagged = TRUE;

-- =============================================
-- Processing Logs Table
-- =============================================
CREATE TABLE processing_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    statement_id UUID REFERENCES bank_statements(id) ON DELETE CASCADE,
    
    -- Log details
    action VARCHAR(100),
    status VARCHAR(50),
    message TEXT,
    details_json JSONB,
    
    -- Performance metrics
    processing_time_ms INTEGER,
    pages_processed INTEGER,
    transactions_found INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT check_status CHECK (
        status IN ('success', 'failed', 'warning', 'info')
    )
);

-- Create indexes for processing_logs
CREATE INDEX idx_logs_statement ON processing_logs(statement_id);
CREATE INDEX idx_logs_action ON processing_logs(action);
CREATE INDEX idx_logs_status ON processing_logs(status);
CREATE INDEX idx_logs_created ON processing_logs(created_at DESC);

-- =============================================
-- Create update trigger for updated_at columns
-- =============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;$$ language 'plpgsql';

-- Apply trigger to all tables with updated_at column
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_banks_updated_at BEFORE UPDATE ON banks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_categories_updated_at BEFORE UPDATE ON transaction_categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_statements_updated_at BEFORE UPDATE ON bank_statements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- Create Views for Common Queries
-- =============================================

-- View for statement summary
CREATE VIEW statement_summary AS
SELECT 
    bs.id,
    bs.user_id,
    u.username,
    bs.bank_name,
    bs.account_number,
    bs.statement_period_start,
    bs.statement_period_end,
    bs.opening_balance,
    bs.closing_balance,
    bs.total_credits,
    bs.total_debits,
    bs.processing_status,
    COUNT(t.id) as transaction_count,
    bs.uploaded_at,
    bs.processed_at
FROM bank_statements bs
JOIN users u ON bs.user_id = u.id
LEFT JOIN transactions t ON bs.id = t.statement_id
GROUP BY bs.id, u.username;

-- View for transaction analysis
CREATE VIEW transaction_analysis AS
SELECT 
    t.id,
    t.statement_id,
    bs.user_id,
    t.transaction_date,
    t.description,
    t.amount,
    t.transaction_type,
    t.category,
    t.subcategory,
    t.merchant_name,
    tc.color as category_color,
    tc.icon as category

LEFT JOIN transaction_categories tc ON t.category = tc.name;

-- View for monthly spending summary
CREATE VIEW monthly_spending_summary AS
SELECT 
    bs.user_id,
    DATE_TRUNC('month', t.transaction_date) as month,
    t.category,
    t.transaction_type,
    COUNT(*) as transaction_count,
    SUM(CASE WHEN t.transaction_type = 'debit' THEN t.amount ELSE 0 END) as total_debits,
    SUM(CASE WHEN t.transaction_type = 'credit' THEN t.amount ELSE 0 END) as total_credits,
    AVG(t.amount) as avg_transaction_amount
FROM transactions t
JOIN bank_statements bs ON t.statement_id = bs.id
WHERE t.transaction_date IS NOT NULL
GROUP BY bs.user_id, DATE_TRUNC('month', t.transaction_date), t.category, t.transaction_type;

-- =============================================
-- Functions for Data Analysis
-- =============================================

-- Function to calculate balance consistency
CREATE OR REPLACE FUNCTION check_balance_consistency(statement_id UUID)
RETURNS TABLE(
    is_consistent BOOLEAN,
    calculated_closing DECIMAL(12, 2),
    stated_closing DECIMAL(12, 2),
    difference DECIMAL(12, 2)
) AS $$DECLARE
    opening DECIMAL(12, 2);
    closing DECIMAL(12, 2);
    total_credits DECIMAL(12, 2);
    total_debits DECIMAL(12, 2);
    calculated DECIMAL(12, 2);
BEGIN
    -- Get statement balances
    SELECT opening_balance, closing_balance
    INTO opening, closing
    FROM bank_statements
    WHERE id = statement_id;
    
    -- Calculate totals from transactions
    SELECT 
        COALESCE(SUM(CASE WHEN transaction_type = 'credit' THEN amount ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN transaction_type = 'debit' THEN amount ELSE 0 END), 0)
    INTO total_credits, total_debits
    FROM transactions
    WHERE transactions.statement_id = check_balance_consistency.statement_id;
    
    -- Calculate expected closing balance
    calculated := COALESCE(opening, 0) + total_credits - total_debits;
    
    RETURN QUERY
    SELECT 
        ABS(calculated - COALESCE(closing, 0)) < 0.01,
        calculated,
        closing,
        calculated - COALESCE(closing, 0);
END;$$ LANGUAGE plpgsql;

-- Function to categorize uncategorized transactions
CREATE OR REPLACE FUNCTION auto_categorize_transaction(transaction_id UUID)
RETURNS VARCHAR AS $$DECLARE
    trans_desc TEXT;
    matched_category VARCHAR(100);
BEGIN
    -- Get transaction description
    SELECT LOWER(description) INTO trans_desc
    FROM transactions
    WHERE id = transaction_id;
    
    -- Try to match with category keywords
    SELECT tc.name INTO matched_category
    FROM transaction_categories tc
    WHERE tc.keywords IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM jsonb_array_elements_text(tc.keywords) AS keyword
        WHERE trans_desc LIKE '%' || LOWER(keyword) || '%'
    )
    LIMIT 1;
    
    -- Update transaction if category found
    IF matched_category IS NOT NULL THEN
        UPDATE transactions
        SET category = matched_category,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = transaction_id;
    END IF;
    
    RETURN matched_category;
END;$$ LANGUAGE plpgsql;

-- =============================================
-- Security: Row Level Security (RLS) Policies
-- =============================================

-- Enable RLS on sensitive tables
ALTER TABLE bank_statements ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- Create policies for bank_statements
CREATE POLICY user_statements_policy ON bank_statements
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::UUID);

-- Create policies for transactions
CREATE POLICY user_transactions_policy ON transactions
    FOR ALL
    USING (
        statement_id IN (
            SELECT id FROM bank_statements 
            WHERE user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- =============================================
-- Seed Data
-- =============================================

-- Insert default banks
INSERT INTO banks (name, code, date_format, statement_patterns, config_json, is_active) VALUES
('Bank of America', 'BOA', 'MM/DD/YYYY', 
 '{"account_number": "Account Number:?\\s*(\\d+)", "balance": "Balance:?\\s*\\$?([\\d,]+\\.?\\d*)", "transaction": "(\\d{2}/\\d{2}/\\d{4})\\s+(.*?)\\s+\\$?([\\d,]+\\.?\\d*)"}',
 '{"requires_ocr": true, "supported_formats": ["pdf", "jpg", "png"]}', true),

('Chase Bank', 'CHASE', 'MM/DD/YYYY',
 '{"account_number": "Account:?\\s*(\\d+)", "balance": "Balance:?\\s*\\$?([\\d,]+\\.?\\d*)", "transaction": "(\\d{2}/\\d{2}/\\d{4})\\s+(.*?)\\s+\\$?([\\d,]+\\.?\\d*)"}',
 '{"requires_ocr": true, "supported_formats": ["pdf", "jpg", "png"]}', true),

('Wells Fargo', 'WF', 'MM/DD/YYYY',
 '{"account_number": "Account\\s*#?:?\\s*(\\d+)", "balance": "Balance:?\\s*\\$?([\\d,]+\\.?\\d*)", "transaction": "(\\d{2}/\\d{2}/\\d{4})\\s+(.*?)\\s+\\$?([\\d,]+\\.?\\d*)"}',
 '{"requires_ocr": true, "supported_formats": ["pdf", "jpg", "png"]}', true);

-- Insert default transaction categories
INSERT INTO transaction_categories (name, parent_id, keywords, color, icon) VALUES
('Income', NULL, '["salary", "payroll", "income", "deposit", "transfer in"]', '#28a745', '💰'),
('Food & Dining', NULL, '["restaurant", "food", "dining", "cafe", "coffee"]', '#ffc107', '🍔'),
('Transportation', NULL, '["gas", "fuel", "uber", "lyft", "parking", "transit"]', '#17a2b8', '🚗'),
('Shopping', NULL, '["amazon", "walmart", "target", "store", "shop"]', '#e83e8c', '🛍️'),
('Bills & Utilities', NULL, '["utility", "electric", "water", "internet", "phone"]', '#dc3545', '📱'),
('Entertainment', NULL, '["netflix", "spotify", "movie", "game", "entertainment"]', '#6f42c1', '🎬'),
('Healthcare', NULL, '["pharmacy", "doctor", "hospital", "medical", "health"]', '#20c997', '🏥'),
('Transfer', NULL, '["transfer", "withdrawal", "deposit", "atm"]', '#6c757d', '🔄');

-- =============================================
-- Maintenance Scripts
-- =============================================

-- Script to clean up old processing logs
CREATE OR REPLACE FUNCTION cleanup_old_logs()
RETURNS INTEGER AS $$DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM processing_logs
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '90 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;$$ LANGUAGE plpgsql;

-- Script to archive old statements
CREATE OR REPLACE FUNCTION archive_old_statements()
RETURNS INTEGER AS $$DECLARE
    archived_count INTEGER;
BEGIN
    -- Mark statements older than 1 year as archived
    UPDATE bank_statements
    SET processing_status = 'archived'
    WHERE statement_period_end < CURRENT_DATE - INTERVAL '1 year'
    AND processing_status != 'archived';
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    RETURN archived_count;
END;$$ LANGUAGE plpgsql;

-- =============================================
-- Grant Permissions (adjust based on your user setup)
-- =============================================

-- Create roles
CREATE ROLE bank_ocr_app;
CREATE ROLE bank_ocr_admin;
CREATE ROLE bank_ocr_readonly;

-- Grant permissions to app role
GRANT CONNECT ON DATABASE bank_ocr_db TO bank_ocr_app;
GRANT USAGE ON SCHEMA public TO bank_ocr_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bank_ocr_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bank_ocr_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO bank_ocr_app;

-- Grant permissions to admin role
GRANT ALL PRIVILEGES ON DATABASE bank_ocr_db TO bank_ocr_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bank_ocr_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bank_ocr_admin;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO bank_ocr_admin;

-- Grant permissions to readonly role
GRANT CONNECT ON DATABASE bank_ocr_db TO bank_ocr_readonly;
GRANT USAGE ON SCHEMA public TO bank_ocr_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bank_ocr_readonly;

-- =============================================
-- Performance Optimization Statistics
-- =============================================

-- Update table statistics for query optimization
ANALYZE users;
ANALYZE banks;
ANALYZE transaction_categories;
ANALYZE bank_statements;
ANALYZE transactions;
ANALYZE processing_logs;

-- =============================================
-- Database Health Check Queries
-- =============================================

-- Check table sizes
CREATE VIEW table_sizes AS
SELECT
    schemaname AS schema,
    tablename AS table,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
CREATE VIEW index_usage AS
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Database connection info
CREATE VIEW connection_stats AS
SELECT
    datname AS database,
    numbackends AS active_connections,
    xact_commit AS transactions_committed,
    xact_rollback AS transactions_rolled_back,
    blks_read AS blocks_read,
    blks_hit AS blocks_hit,
    tup_returned AS tuples_returned,
    tup_fetched AS tuples_fetched,
    tup_inserted AS tuples_inserted,
    tup_updated AS tuples_updated,
    tup_deleted AS tuples_deleted
FROM pg_stat_database
WHERE datname = current_database();