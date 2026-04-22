-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Market data table (time-series optimized)
CREATE TABLE IF NOT EXISTS quotes (
    time TIMESTAMPTZ NOT NULL,
    instrument_id TEXT NOT NULL,
    exchange TEXT NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION,
    bid DOUBLE PRECISION,
    ask DOUBLE PRECISION,
    metadata JSONB
);

-- Convert to hypertable for efficient time-series queries
SELECT create_hypertable('quotes', 'time', if_not_exists => TRUE);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_quotes_instrument_time ON quotes (instrument_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_quotes_exchange ON quotes (exchange, time DESC);

-- Trades table
CREATE TABLE IF NOT EXISTS trades (
    time TIMESTAMPTZ NOT NULL,
    trade_id TEXT UNIQUE NOT NULL,
    instrument_id TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    fee DOUBLE PRECISION DEFAULT 0,
    exchange TEXT,
    metadata JSONB
);

SELECT create_hypertable('trades', 'time', if_not_exists => TRUE);

-- Audit log (immutable event store)
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type TEXT NOT NULL,
    actor TEXT DEFAULT 'system',
    data JSONB NOT NULL,
    model_version TEXT,
    config_hash TEXT,
    session_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log (event_type);
CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log (session_id);

-- Positions table (current state)
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol TEXT NOT NULL UNIQUE,
    quantity DOUBLE PRECISION NOT NULL,
    avg_price DOUBLE PRECISION NOT NULL,
    current_value DOUBLE PRECISION,
    unrealized_pnl DOUBLE PRECISION
);

-- System config history
CREATE TABLE IF NOT EXISTS config_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    config JSONB NOT NULL,
    config_hash TEXT NOT NULL,
    applied_by TEXT DEFAULT 'system'
);

COMMENT ON TABLE quotes IS 'Time-series market data from all exchanges';
COMMENT ON TABLE trades IS 'Executed trades (both paper and live)';
COMMENT ON TABLE audit_log IS 'Immutable audit trail for compliance';
COMMENT ON TABLE positions IS 'Current position state (updated on fills)';
