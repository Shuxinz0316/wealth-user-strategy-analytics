PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS campaign_observations;
DROP TABLE IF EXISTS experiment_assignments;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    registered_at TEXT NOT NULL,
    acquisition_channel TEXT NOT NULL,
    age_group TEXT NOT NULL,
    city_tier TEXT NOT NULL,
    risk_profile TEXT NOT NULL CHECK (risk_profile IN ('cautious', 'balanced', 'aggressive')),
    initial_cash_balance REAL NOT NULL CHECK (initial_cash_balance >= 0),
    marketing_consent INTEGER NOT NULL CHECK (marketing_consent IN (0, 1))
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    product_type TEXT NOT NULL,
    risk_level INTEGER NOT NULL,
    expected_return REAL NOT NULL,
    minimum_investment REAL NOT NULL
);

CREATE TABLE events (
    event_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    event_time TEXT NOT NULL,
    event_type TEXT NOT NULL,
    channel TEXT,
    product_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE transactions (
    transaction_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    transaction_time TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('buy', 'redeem')),
    amount REAL NOT NULL CHECK (amount > 0),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE experiment_assignments (
    user_id INTEGER PRIMARY KEY,
    experiment_name TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    experiment_group TEXT NOT NULL,
    delivered INTEGER NOT NULL CHECK (delivered IN (0, 1)),
    clicked_7d INTEGER NOT NULL CHECK (clicked_7d IN (0, 1)),
    purchased_30d INTEGER NOT NULL CHECK (purchased_30d IN (0, 1)),
    purchase_amount_30d REAL NOT NULL CHECK (purchase_amount_30d >= 0),
    redeemed_30d INTEGER NOT NULL CHECK (redeemed_30d IN (0, 1)),
    redeemed_amount_30d REAL NOT NULL CHECK (
        redeemed_amount_30d >= 0 AND redeemed_amount_30d <= purchase_amount_30d
    ),
    retained_30d INTEGER NOT NULL CHECK (retained_30d IN (0, 1)),
    retained_90d INTEGER NOT NULL CHECK (retained_90d IN (0, 1)),
    retained_aum_90d REAL NOT NULL CHECK (retained_aum_90d >= 0),
    complaint_30d INTEGER NOT NULL CHECK (complaint_30d IN (0, 1)),
    recommended_product_id INTEGER,
    suitability_passed INTEGER NOT NULL CHECK (suitability_passed IN (0, 1)),
    campaign_cost REAL NOT NULL CHECK (campaign_cost >= 0),
    pre_90d_visits INTEGER NOT NULL,
    pre_90d_trades INTEGER NOT NULL,
    days_since_last_visit INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (recommended_product_id) REFERENCES products(product_id)
);

CREATE TABLE campaign_observations (
    user_id INTEGER NOT NULL,
    month TEXT NOT NULL,
    pilot_group INTEGER NOT NULL,
    post_period INTEGER NOT NULL,
    active_30d INTEGER NOT NULL,
    net_inflow REAL NOT NULL,
    PRIMARY KEY (user_id, month),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX idx_events_user_time ON events(user_id, event_time);
CREATE INDEX idx_events_type_time ON events(event_type, event_time);
CREATE INDEX idx_transactions_user_time ON transactions(user_id, transaction_time);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
