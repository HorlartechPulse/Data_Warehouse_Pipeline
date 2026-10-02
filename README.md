# Analytical Data Warehouse Pipeline

**Case study:** Build a small analytical data warehouse  
**Architecture:** Source Systems → Staging → Storage (DWH + Marts) → Presentation

## Deliverables

| Deliverable | Path |
|-------------|------|
| Raw data ingestion | `source/**` + staging load in ETL |
| ETL/ELT pipeline | `scripts/etl_pipeline.py` |
| Data quality validation | `dq_results` table + `docs/data_quality.md` |
| Dimensional modeling | `sql/02_warehouse_ddl.sql` + `docs/dimensional_model.md` |
| Analytics-ready tables | `mart_*` views + `output/*.csv` |
| Documentation & architecture | `docs/architecture.md` |

## Quick start

```bash
cd Data_Warehouse_Pipeline
python scripts/etl_pipeline.py

# Inspect
sqlite3 warehouse/analytics_dw.db "SELECT * FROM dq_results;"
sqlite3 warehouse/analytics_dw.db "SELECT * FROM mart_daily_sales LIMIT 10;"
sqlite3 warehouse/analytics_dw.db "SELECT * FROM mart_customer_ltv ORDER BY lifetime_revenue DESC LIMIT 10;"
```

## Pipeline steps

1. **Extract** — read CRM / ERP / flat-file CSVs  
2. **Stage** — land into `stg_*` with load metadata  
3. **Transform** — build dims & facts (dedupe customers, keys, gross profit)  
4. **Validate** — run DQ suite  
5. **Publish** — mart views + CSV exports for BI  

## Author

Abdulwaheed Toheeb Olanrewaju — Data Engineering Portfolio
