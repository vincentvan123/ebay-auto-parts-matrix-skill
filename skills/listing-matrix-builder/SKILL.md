---
name: listing-matrix-builder
description: Convert ranked eBay auto-parts fitment entities into mutually exclusive primary Core and make-grouped Discovery pools plus a required full-fitment Mixed listing whenever a SKU supports at least two distinct vehicle models.
---

# Listing Matrix Builder

1. Read configured maximum Core count, relative threshold, and minimum sales coverage.
2. Select only eligible entities that meet the relative threshold, capped at the configured maximum.
3. Create one Core listing per selected model or family.
4. Group all remaining compatibility models into make-level Discovery listings.
5. Order models in each Discovery mixed title by descending market rank, with missing-sales models last.
6. Assert that every normalized make/model/year belongs to exactly one primary Core or Discovery listing.
7. When fitment contains at least two distinct models, add one supplemental Mixed listing covering all fitment and order its title by descending market rank.
8. Pass only primary listings to PLP generation; retain Mixed in listing outputs.
