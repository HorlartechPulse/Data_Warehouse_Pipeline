#!/usr/bin/env python3
"""
Data Warehouse ETL/ELT Pipeline
Layers: Source → Staging → Warehouse (dims/facts) → Marts → DQ
"""
from __future__ import annotations

import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path("/tmp/analytics_dw.db")
WAREHOUSE_COPY = ROOT / "warehouse" / "analytics_dw.db"
LOG = ROOT / "logs" / f"etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


def log(msg: str):
    line = f"{datetime.now().isoformat(timespec='seconds')} | {msg}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def run_sql_file(conn, path: Path):
    conn.executescript(path.read_text())
    conn.commit()


def load_csv_to_staging(conn, csv_path: Path, table: str):
    """Extract: land raw CSV into staging with metadata columns."""
    loaded_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        rows = list(reader)
    if not rows:
        log(f"WARN empty file {csv_path}")
        return 0
    # staging tables include _loaded_at, _source_file
    placeholders = ",".join(["?"] * (len(cols) + 2))
    col_list = ",".join(cols + ["_loaded_at", "_source_file"])
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
    data = [tuple(r.get(c) for c in cols) + (loaded_at, csv_path.name) for r in rows]
    conn.execute(f"DELETE FROM {table}")
    conn.executemany(sql, data)
    conn.commit()
    log(f"STAGED {table}: {len(data)} rows from {csv_path.name}")
    return len(data)


def dq_check(conn, name, layer, sql_count, detail_ok="OK"):
    cur = conn.execute(sql_count)
    n = cur.fetchone()[0]
    status = "PASS" if n == 0 else "FAIL"
    if name.startswith("WARN_") and n > 0:
        status = "WARN"
    conn.execute(
        "INSERT INTO dq_results(check_name, layer, status, records_flagged, details, checked_at) VALUES (?,?,?,?,?,?)",
        (name, layer, status, n, detail_ok if n == 0 else f"{n} records", datetime.utcnow().isoformat()),
    )
    conn.commit()
    log(f"DQ [{status}] {name}: {n}")
    return status, n


def transform_load(conn):
    """Transform staging → dimensional warehouse."""
    # dim_date from order dates
    conn.execute("DELETE FROM dim_date")
    conn.execute("""
        INSERT INTO dim_date(date_key, date, year, quarter, month, month_name, year_month)
        SELECT DISTINCT
            CAST(strftime('%Y%m%d', order_date) AS INTEGER),
            order_date,
            CAST(strftime('%Y', order_date) AS INTEGER),
            'Q' || ((CAST(strftime('%m', order_date) AS INTEGER)-1)/3 + 1),
            CAST(strftime('%m', order_date) AS INTEGER),
            CASE strftime('%m', order_date)
                WHEN '01' THEN 'January' WHEN '02' THEN 'February' WHEN '03' THEN 'March'
                WHEN '04' THEN 'April' WHEN '05' THEN 'May' WHEN '06' THEN 'June'
                WHEN '07' THEN 'July' WHEN '08' THEN 'August' WHEN '09' THEN 'September'
                WHEN '10' THEN 'October' WHEN '11' THEN 'November' ELSE 'December' END,
            strftime('%Y-%m', order_date)
        FROM stg_orders
        WHERE order_date IS NOT NULL AND length(order_date)=10
    """)

    # regions
    conn.execute("DELETE FROM dim_region")
    conn.execute("""
        INSERT INTO dim_region(region_key, region_name)
        SELECT ROW_NUMBER() OVER (ORDER BY region), region FROM (
            SELECT DISTINCT TRIM(region) AS region FROM stg_customers
            WHERE region IS NOT NULL AND TRIM(region) != '' AND TRIM(region) != 'Unknown'
            UNION
            SELECT DISTINCT TRIM(region) FROM stg_marketing_spend WHERE region IS NOT NULL
        )
    """)

    # channels
    conn.execute("DELETE FROM dim_channel")
    conn.execute("""
        INSERT INTO dim_channel(channel_key, channel_name)
        SELECT ROW_NUMBER() OVER (ORDER BY channel), channel FROM (
            SELECT DISTINCT LOWER(TRIM(channel)) AS channel FROM stg_orders
            WHERE channel IS NOT NULL
            UNION
            SELECT DISTINCT LOWER(TRIM(channel)) FROM stg_marketing_spend WHERE channel IS NOT NULL
        )
    """)

    # products
    conn.execute("DELETE FROM dim_product")
    conn.execute("""
        INSERT INTO dim_product(product_key, product_id, product_name, category, list_price, cost)
        SELECT ROW_NUMBER() OVER (ORDER BY CAST(product_id AS INTEGER)),
               CAST(product_id AS INTEGER), product_name, category,
               CAST(list_price AS REAL), CAST(cost AS REAL)
        FROM (
            SELECT product_id, product_name, category, list_price, cost,
                   ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY product_id) AS rn
            FROM stg_products
            WHERE product_id IS NOT NULL AND TRIM(product_id) != ''
        ) WHERE rn = 1
    """)

    # customers — dedupe by customer_id, drop bad ids
    conn.execute("DELETE FROM dim_customer")
    conn.execute("""
        INSERT INTO dim_customer(customer_key, customer_id, full_name, email, region_name, signup_date, status, effective_from, is_current)
        SELECT ROW_NUMBER() OVER (ORDER BY cid),
               cid, full_name, email, region, signup_date, status,
               datetime('now'), 1
        FROM (
            SELECT CAST(customer_id AS INTEGER) AS cid,
                   full_name, email, TRIM(region) AS region, signup_date, status,
                   ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY signup_date DESC) AS rn
            FROM stg_customers
            WHERE customer_id IS NOT NULL AND TRIM(customer_id) != ''
              AND CAST(customer_id AS INTEGER) > 0
        ) WHERE rn = 1
    """)

    # fact_sales
    conn.execute("DELETE FROM fact_sales")
    conn.execute("""
        INSERT INTO fact_sales(
            sales_key, date_key, customer_key, product_key, region_key, channel_key,
            order_id, quantity, unit_price, line_amount, cost_amount, gross_profit, order_status
        )
        SELECT
            ROW_NUMBER() OVER (ORDER BY o.order_id, l.product_id),
            CAST(strftime('%Y%m%d', o.order_date) AS INTEGER),
            cu.customer_key,
            p.product_key,
            r.region_key,
            ch.channel_key,
            CAST(o.order_id AS INTEGER),
            CAST(l.quantity AS INTEGER),
            CAST(l.unit_price AS REAL),
            CAST(l.line_amount AS REAL),
            ROUND(CAST(l.quantity AS INTEGER) * p.cost, 2),
            ROUND(CAST(l.line_amount AS REAL) - CAST(l.quantity AS INTEGER) * p.cost, 2),
            o.status
        FROM stg_order_lines l
        JOIN stg_orders o ON o.order_id = l.order_id
        JOIN dim_customer cu ON cu.customer_id = CAST(o.customer_id AS INTEGER)
        JOIN dim_product p ON p.product_id = CAST(l.product_id AS INTEGER)
        JOIN dim_region r ON r.region_name = cu.region_name
        JOIN dim_channel ch ON ch.channel_name = LOWER(TRIM(o.channel))
        WHERE o.order_date IS NOT NULL AND length(o.order_date)=10
    """)

    # marketing fact
    conn.execute("DELETE FROM fact_marketing_spend")
    conn.execute("""
        INSERT INTO fact_marketing_spend(spend_key, year_month, region_key, channel_key, spend_ngn)
        SELECT ROW_NUMBER() OVER (ORDER BY month, region, channel),
               month, r.region_key, ch.channel_key, CAST(spend_ngn AS REAL)
        FROM stg_marketing_spend s
        JOIN dim_region r ON r.region_name = TRIM(s.region)
        JOIN dim_channel ch ON ch.channel_name = LOWER(TRIM(s.channel))
    """)
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM fact_sales").fetchone()[0]
    log(f"LOADED fact_sales: {n} rows")


def run_dq(conn):
    conn.execute("DELETE FROM dq_results")
    checks = [
        ("STG_customers_null_id", "staging",
         "SELECT COUNT(*) FROM stg_customers WHERE customer_id IS NULL OR TRIM(customer_id)=''"),
        ("STG_orders_bad_dates", "staging",
         "SELECT COUNT(*) FROM stg_orders WHERE order_date IS NULL OR length(order_date)!=10"),
        ("WARN_STG_customer_dupes", "staging",
         "SELECT COUNT(*) FROM (SELECT customer_id FROM stg_customers GROUP BY customer_id HAVING COUNT(*)>1)"),
        ("DWH_fact_orphans_customer", "warehouse",
         "SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_customer c ON c.customer_key=f.customer_key WHERE c.customer_key IS NULL"),
        ("DWH_fact_orphans_product", "warehouse",
         "SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_product p ON p.product_key=f.product_key WHERE p.product_key IS NULL"),
        ("DWH_negative_amounts", "warehouse",
         "SELECT COUNT(*) FROM fact_sales WHERE line_amount < 0 OR quantity < 0"),
        ("DWH_completed_revenue_positive", "warehouse",
         "SELECT CASE WHEN COALESCE(SUM(line_amount),0) > 0 THEN 0 ELSE 1 END FROM fact_sales WHERE order_status='completed'"),
    ]
    results = []
    for name, layer, sql in checks:
        results.append(dq_check(conn, name, layer, sql))
    return results


def export_marts(conn):
    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    for view, file in [
        ("mart_daily_sales", "mart_daily_sales.csv"),
        ("mart_customer_ltv", "mart_customer_ltv.csv"),
    ]:
        cur = conn.execute(f"SELECT * FROM {view}")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        path = out / file
        with path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
        log(f"EXPORTED {view} → {file} ({len(rows)} rows)")


def main():
    log("=== ETL START ===")
    conn = connect()
    run_sql_file(conn, ROOT / "sql" / "01_staging_ddl.sql")
    run_sql_file(conn, ROOT / "sql" / "02_warehouse_ddl.sql")

    # Extract → Stage
    load_csv_to_staging(conn, ROOT/"source/crm/customers.csv", "stg_customers")
    load_csv_to_staging(conn, ROOT/"source/erp/products.csv", "stg_products")
    load_csv_to_staging(conn, ROOT/"source/erp/orders.csv", "stg_orders")
    load_csv_to_staging(conn, ROOT/"source/erp/order_lines.csv", "stg_order_lines")
    load_csv_to_staging(conn, ROOT/"source/files/marketing_spend.csv", "stg_marketing_spend")

    # Transform → Load DWH
    transform_load(conn)

    # Data quality
    run_dq(conn)

    # Analytics-ready exports
    export_marts(conn)

    # Summary
    for t in ["dim_customer","dim_product","dim_date","fact_sales","fact_marketing_spend"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        log(f"COUNT {t}={n}")
    log("=== ETL COMPLETE ===")
    conn.close()
    import shutil
    WAREHOUSE_COPY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(DB, WAREHOUSE_COPY)
    log(f"Copied DB to {WAREHOUSE_COPY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
