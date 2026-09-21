# Listing Matrix Orchestrator

## Scope

Process any single-SKU auto-parts fitment input through the standard listing and PLP matrix workflow. Never supply one SKU's rules, keywords, fitment, or sales to another SKU.

## Workflow

1. Read `config/rules.toml`, `config/vehicle_family.csv`, and the requested SKU input.
2. Invoke the Fitment Normalizer contract.
3. Reuse fresh rows from `data/vehicle_sales_cache.csv`; refresh only missing or stale source keys.
4. Invoke the Vehicle Market Ranker contract and retain coverage and source metadata.
5. Invoke the Listing Matrix Builder contract. Keep compatibility pools mutually exclusive.
6. Invoke the eBay Title Generator and PLP Matrix Builder contracts.
7. Generate SKU Markdown, CSV/JSON intermediates, and the four-sheet Excel workbook.
8. Validate title length, compatibility completeness, Core limit, missing-data disclosure, workbook errors, and rendered sheets.

## Guardrails

- Never infer one SKU's keyword, fitment, family, or ranking from another SKU.
- Never turn missing annual sales into zero or an estimate.
- Do not allow a source below the configured coverage threshold into Core.
- Series-level family sales may be counted once only.
- Do not put a combined year range in a family or Discovery title when members have different year scopes.
- Order Discovery mixed-title models by market rank and never by alphabetic convenience.
- Keep all titles at or below 80 characters and use `for` before vehicle makes.
- Do not publish listings or campaigns; this MVP produces planning artifacts only.
