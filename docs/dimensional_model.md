# Dimensional Model

## Bus matrix

| Fact | Date | Customer | Product | Region | Channel |
|------|------|----------|---------|--------|---------|
| fact_sales | ✓ | ✓ | ✓ | ✓ | ✓ |
| fact_marketing_spend | year_month | | | ✓ | ✓ |

## Facts

**fact_sales** (grain: order line)  
Measures: quantity, unit_price, line_amount, cost_amount, gross_profit  

**fact_marketing_spend** (grain: month × region × channel)  
Measures: spend_ngn  

## Dimensions

- **dim_date** — calendar attributes from order dates  
- **dim_customer** — deduplicated customer master (SCD0/type-1 style current row)  
- **dim_product** — product catalog  
- **dim_region** / **dim_channel** — conformed dimensions  

## Marts

- `mart_daily_sales` — revenue & profit by date, region, channel, category  
- `mart_customer_ltv` — customer lifetime revenue and order counts  
