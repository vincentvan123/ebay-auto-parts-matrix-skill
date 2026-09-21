---
name: vehicle-market-ranker
description: Refresh and reuse public annual U.S. vehicle sales data, sum only the years compatible with a SKU, combine configured vehicle families without double counting, and rank market-size proxies with coverage checks.
---

# Vehicle Market Ranker

1. Read normalized fitment, family rules, source mappings, and `data/vehicle_sales_cache.csv`.
2. Refresh only explicit configured URLs when requested or stale.
3. Preserve source URL, refresh date, and annual row grain.
4. Sum sales only for the union of fitment years attached to each ranking entity.
5. Treat absent years as missing, never as zero.
6. Return cumulative sales, required/available years, coverage, and decision eligibility.
