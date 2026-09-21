# Listing matrix rules

- Rank each model or configured family by cumulative U.S. sales within its actual fitment years.
- A ranking entity is Core-eligible only when sales-data coverage meets `minimum_sales_coverage`.
- A Core entity must reach `minimum_relative_market_share` of the largest eligible entity.
- Select at most `max_core_listings` Core entities.
- Put every remaining fitment into a make-level Discovery listing.
- Build each Discovery mixed title from its own remaining Compatibility pool, ordering models by descending market rank.
- Put missing-sales models after ranked models in a mixed title; keep all models in Compatibility even when the title reaches 80 characters first.
- Compatibility pools are mutually exclusive: a model belongs to one primary listing only.
- Missing sales data remains missing and must be called out in the decision reason.
