---
name: vehicle-market-ranker
description: Refresh and reuse public annual U.S. vehicle sales data, estimate effective vehicle population with age-based survival rates for years compatible with a SKU, combine configured vehicle families without double counting, and rank market-size proxies with coverage checks.
---

# Vehicle Market Ranker

1. Read normalized fitment, family rules, source mappings, and `data/vehicle_sales_cache.csv`.
2. Refresh only explicit configured URLs when requested or stale.
3. Preserve source URL, refresh date, and annual row grain.
4. Multiply each compatible year's sales by its configured age-based survival rate, then sum the estimated surviving population.
5. Treat absent years as missing, never as zero.
6. Return cumulative sales, estimated effective population, market tier, required/available years, coverage, and decision eligibility.
