# Listing matrix rules

- Rank each model or configured family by age-adjusted effective vehicle population within its actual fitment years.
- A ranking entity is Core-eligible only when sales-data coverage meets `minimum_sales_coverage`.
- A Core entity must reach `minimum_effective_vehicle_population` after age-based survival adjustment.
- A Core entity must reach `minimum_relative_market_share` of the largest eligible entity.
- Select at most `max_core_listings` Core entities.
- Put every remaining fitment into a make-level Discovery listing.
- Treat Core and Discovery as the mutually exclusive primary Compatibility pools.
- If the SKU fits at least two distinct make/model combinations, add one supplemental Mixed listing covering the complete fitment.
- Order the Mixed title by descending market rank, including as many models as fit within the title limit.
- Build each Discovery mixed title from its own remaining Compatibility pool, ordering models by descending market rank.
- Put missing-sales models after ranked models in a mixed title; keep all models in Compatibility even when the title reaches 80 characters first.
- Primary Compatibility pools are mutually exclusive; the supplemental Mixed listing intentionally overlaps them.
- Missing sales data remains missing and must be called out in the decision reason.
