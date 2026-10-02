-- Staging tables (raw landing, minimal typing)
DROP TABLE IF EXISTS stg_customers;
DROP TABLE IF EXISTS stg_products;
DROP TABLE IF EXISTS stg_orders;
DROP TABLE IF EXISTS stg_order_lines;
DROP TABLE IF EXISTS stg_marketing_spend;

CREATE TABLE stg_customers (
    customer_id TEXT,
    full_name TEXT,
    email TEXT,
    region TEXT,
    signup_date TEXT,
    status TEXT,
    _loaded_at TEXT,
    _source_file TEXT
);

CREATE TABLE stg_products (
    product_id TEXT,
    product_name TEXT,
    category TEXT,
    list_price TEXT,
    cost TEXT,
    _loaded_at TEXT,
    _source_file TEXT
);

CREATE TABLE stg_orders (
    order_id TEXT,
    customer_id TEXT,
    order_date TEXT,
    channel TEXT,
    status TEXT,
    currency TEXT,
    _loaded_at TEXT,
    _source_file TEXT
);

CREATE TABLE stg_order_lines (
    order_id TEXT,
    product_id TEXT,
    quantity TEXT,
    unit_price TEXT,
    line_amount TEXT,
    _loaded_at TEXT,
    _source_file TEXT
);

CREATE TABLE stg_marketing_spend (
    month TEXT,
    region TEXT,
    channel TEXT,
    spend_ngn TEXT,
    _loaded_at TEXT,
    _source_file TEXT
);
