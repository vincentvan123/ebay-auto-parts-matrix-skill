---
name: fitment-normalizer
description: Normalize SKU vehicle fitment makes, models, and explicit or ranged years before building an eBay listing matrix. Use for eBay auto-parts fitment inputs that need canonical casing, year expansion, validation, or family lookup.
---

# Fitment Normalizer

1. Read the SKU `input.csv`.
2. Normalize make/model casing with project mappings.
3. Expand start/end ranges or parse semicolon-separated explicit years.
4. Reject reversed ranges, non-four-digit years, and duplicate make/model/year rows.
5. Attach family and sales-source keys without changing compatibility model names.
6. Write normalized fitment to the SKU output and pass structured rows to the ranker.
