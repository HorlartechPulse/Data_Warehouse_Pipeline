-- Analytical warehouse: dimensional model
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS fact_marketing_spend;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_channel;
DROP TABLE IF EXISTS dim_region;
DROP TABLE IF EXISTS dq_results;

CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,  -- YYYYMMDD
    date TEXT NOT NULL,
    year INTEGER,
    quarter TEXT,
    month INTEGER,
    month_name TEXT,
    year_month TEXT
);

CREATE TABLE dim_region (
    region_key INTEGER PRIMARY KEY,
    region_name TEXT NOT NULL UNIQUE
);

CREATE TABLE dim_channel (
    channel_key INTEGER PRIMARY KEY,
    channel_name TEXT NOT NULL UNIQUE
);

CREATE TABLE dim_customer (
    customer_key INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL UNIQUE,
    full_name TEXT,
    email TEXT,
    region_name TEXT,
    signup_date TEXT,
    status TEXT,
    effective_from TEXT,
    is_current INTEGER DEFAULT 1
);

CREATE TABLE dim_product (
    product_key INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL UNIQUE,
    product_name TEXT,
    category TEXT,
    list_price REAL,
    cost REAL
);

CREATE TABLE fact_sales (
    sales_key INTEGER PRIMARY KEY,
    date_key INTEGER REFERENCES dim_date(date_key),
    customer_key INTEGER REFERENCES dim_customer(customer_key),
    product_key INTEGER REFERENCES dim_product(product_key),
    region_key INTEGER REFERENCES dim_region(region_key),
    channel_key INTEGER REFERENCES dim_channel(channel_key),
    order_id INTEGER,
    quantity INTEGER,
    unit_price REAL,
    line_amount REAL,
    cost_amount REAL,
    gross_profit REAL,
    order_status TEXT
);

CREATE TABLE fact_marketing_spend (
    spend_key INTEGER PRIMARY KEY,
    year_month TEXT,
    region_key INTEGER REFERENCES dim_region(region_key),
    channel_key INTEGER REFERENCES dim_channel(channel_key),
    spend_ngn REAL
);

CREATE TABLE dq_results (
    check_id INTEGER PRIMARY KEY,
    check_name TEXT,
    layer TEXT,
    status TEXT,  -- PASS / FAIL / WARN
    records_flagged INTEGER,
    details TEXT,
    checked_at TEXT
);

-- Analytics-ready mart views
DROP VIEW IF EXISTS mart_daily_sales;
CREATE VIEW mart_daily_sales AS
SELECT
    d.date,
    d.year_month,
    r.region_name,
    c.channel_name,
    p.category,
    COUNT(DISTINCT f.order_id) AS orders,
    SUM(f.quantity) AS units,
    ROUND(SUM(f.line_amount), 2) AS revenue,
    ROUND(SUM(f.gross_profit), 2) AS gross_profit
FROM fact_sales f
JOIN dim_date d ON d.date_key = f.date_key
JOIN dim_region r ON r.region_key = f.region_key
JOIN dim_channel c ON c.channel_key = f.channel_key
JOIN dim_product p ON p.product_key = f.product_key
WHERE f.order_status = 'completed'
GROUP BY d.date, d.year_month, r.region_name, c.channel_name, p.category;

DROP VIEW IF EXISTS mart_customer_ltv;
CREATE VIEW mart_customer_ltv AS
SELECT
    cu.customer_id,
    cu.full_name,
    cu.region_name,
    COUNT(DISTINCT f.order_id) AS orders,
    ROUND(SUM(f.line_amount), 2) AS lifetime_revenue,
    ROUND(SUM(f.gross_profit), 2) AS lifetime_gross_profit,
    MIN(d.date) AS first_order,
    MAX(d.date) AS last_order
FROM fact_sales f
JOIN dim_customer cu ON cu.customer_key = f.customer_key
JOIN dim_date d ON d.date_key = f.date_key
WHERE f.order_status = 'completed'
GROUP BY cu.customer_id, cu.full_name, cu.region_name;
