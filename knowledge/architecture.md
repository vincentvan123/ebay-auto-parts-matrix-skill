# MVP architecture

```text
sku/<SKU>/input.csv
        |
        v
Fitment Normalizer ---- config/vehicle_family.csv
        |
        v
Vehicle Market Ranker -- data/vehicle_sales_cache.csv
        |
        v
Listing Matrix Builder -- config/rules.toml
        |                         |
        v                         v
eBay Title Generator       PLP Matrix Builder
        |                         |
        +------------+------------+
                     v
          Markdown + JSON + CSV + Excel
```

The orchestrator is `scripts/run_mvp.py`. It accepts any SKU/product/fitment input matching the contract. Skill folders define stable inputs, outputs, and guardrails; the orchestrator owns shared parsing and validation so business rules have one implementation.

## Unknown-product flow

1. Add or point to a CSV for the new SKU.
2. The runner derives product keyword and fitment from that file.
3. Known vehicle/year sales come from the shared cache.
4. New vehicle entities receive a deterministic source candidate; successful fetches extend the shared cache.
5. Unresolved sources are reported as missing coverage and stay out of Core until verified.
6. The same ranking, listing, title, compatibility, and PLP builders run without SKU-specific code.

## Data contracts

### Normalized fitment

`sku`, `core_keyword`, `make`, `model`, `years[]`, optional `family`, and `source_key`.

### Sales cache

One row per `source_key`, calendar year, and U.S. sales value. Each row also stores source name, URL, and refresh date.

### Vehicle ranking

One row per model or configured family with fitment scope, cumulative sales, age-adjusted effective population, market tier, source, data coverage, rank, assigned role, and decision reason.

### Listing matrix

One row per Core or make-level Discovery listing. Compatibility scopes are generated from normalized rows and are asserted to be mutually exclusive.

### PLP matrix

One row per campaign, ad group, listing, vehicle, keyword, and match type. Negative keywords are a separate relation keyed by campaign.
