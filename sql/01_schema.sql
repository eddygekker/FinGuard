-- FinGuard database schema (SQLite)

CREATE TABLE IF NOT EXISTS customers (
    id              INTEGER PRIMARY KEY,
    company_name    TEXT NOT NULL,
    email           TEXT NOT NULL,
    plan            TEXT NOT NULL CHECK (plan IN ('Basic', 'Pro', 'Enterprise')),
    mrr             REAL NOT NULL,
    signup_date     TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('active', 'churned')),
    churn_date      TEXT,
    industry        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     INTEGER NOT NULL,
    event_date      TEXT NOT NULL,
    logins          INTEGER NOT NULL DEFAULT 0,
    active_minutes  INTEGER NOT NULL DEFAULT 0,
    features_used   INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS support_tickets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     INTEGER NOT NULL,
    created_at      TEXT NOT NULL,
    resolved_at     TEXT,
    priority        TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high')),
    status          TEXT NOT NULL CHECK (status IN ('open', 'resolved')),
    subject         TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS billing_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     INTEGER NOT NULL,
    event_date      TEXT NOT NULL,
    event_type      TEXT NOT NULL CHECK (
        event_type IN ('payment_success', 'payment_failed', 'downgrade', 'upgrade')
    ),
    amount          REAL,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS customer_risk_scores (
    customer_id         INTEGER PRIMARY KEY,
    risk_score          REAL NOT NULL,
    risk_tier           TEXT NOT NULL CHECK (risk_tier IN ('low', 'medium', 'high')),
    usage_drop_pct      REAL NOT NULL DEFAULT 0,
    days_since_login    INTEGER NOT NULL DEFAULT 0,
    open_tickets        INTEGER NOT NULL DEFAULT 0,
    payment_failures    INTEGER NOT NULL DEFAULT 0,
    feature_adoption    REAL NOT NULL DEFAULT 0,
    computed_at         TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE INDEX IF NOT EXISTS idx_usage_customer_date ON usage_events(customer_id, event_date);
CREATE INDEX IF NOT EXISTS idx_tickets_customer_status ON support_tickets(customer_id, status);
CREATE INDEX IF NOT EXISTS idx_billing_customer_date ON billing_events(customer_id, event_date);
CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status);
