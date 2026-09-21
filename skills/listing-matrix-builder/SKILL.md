---
name: listing-matrix-builder
description: Convert ranked eBay auto-parts fitment entities into a limited Core and make-grouped Discovery listing matrix with mutually exclusive compatibility pools.
---

# Listing Matrix Builder

1. Read configured maximum Core count, relative threshold, and minimum sales coverage.
2. Select only eligible entities that meet the relative threshold, capped at the configured maximum.
3. Create one Core listing per selected model or family.
4. Group all remaining compatibility models into make-level Discovery listings.
5. Order models in each Discovery mixed title by descending market rank, with missing-sales models last.
6. Assert that every normalized make/model/year belongs to exactly one listing.
7. Pass listings to the title and PLP builders.
