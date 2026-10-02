# Data Quality Validation

| Check | Layer | Rule |
|-------|-------|------|
| STG_customers_null_id | Staging | customer_id must be present |
| STG_orders_bad_dates | Staging | order_date ISO length 10 |
| WARN_STG_customer_dupes | Staging | warn on duplicate customer_id in extract |
| DWH_fact_orphans_customer | Warehouse | fact rows must match dim_customer |
| DWH_fact_orphans_product | Warehouse | fact rows must match dim_product |
| DWH_negative_amounts | Warehouse | no negative qty/amount |
| DWH_completed_revenue_positive | Warehouse | completed revenue sum > 0 |

Results stored in `dq_results` after each pipeline run.
