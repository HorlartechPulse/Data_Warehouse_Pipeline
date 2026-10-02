# Architecture — Small Analytical Data Warehouse

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────────────┐     ┌──────────────────┐
│   SOURCE SYSTEMS    │     │     STAGING      │     │   STORAGE (DWH)         │     │  PRESENTATION    │
│                     │     │                  │     │                         │     │                  │
│  CRM (customers)    │────▶│  stg_customers   │────▶│  dim_customer           │────▶│  mart_daily_sales│
│  ERP (orders/lines) │────▶│  stg_orders      │────▶│  dim_product            │────▶│  mart_customer_  │
│  ERP (products)     │────▶│  stg_order_lines │────▶│  dim_date / region /    │     │    ltv           │
│  Flat files (spend) │────▶│  stg_products    │────▶│    channel              │────▶│  BI / SQL / CSV  │
│                     │     │  stg_marketing_  │────▶│  fact_sales             │     │                  │
│                     │     │    spend         │     │  fact_marketing_spend   │     │                  │
│                     │     │  + DQ checks     │     │  dq_results             │     │                  │
└─────────────────────┘     └──────────────────┘     └─────────────────────────┘     └──────────────────┘
         Extract                    Load / validate           Transform + model              Consume
```

## Pattern

**ELT-leaning batch pipeline:** land raw files into staging (extract/load), then transform inside the warehouse engine (SQL) into dimensional tables and marts.

## Tech (portfolio implementation)

| Layer | Implementation |
|-------|----------------|
| Sources | CSV extracts under `source/` |
| Orchestration | `scripts/etl_pipeline.py` |
| Engine | SQLite file `warehouse/analytics_dw.db` (swap for PostgreSQL in prod) |
| DQ | SQL checks → `dq_results` |
| Marts | SQL views + CSV export in `output/` |
