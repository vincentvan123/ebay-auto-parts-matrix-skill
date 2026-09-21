---
name: ebay-title-generator
description: Generate eBay auto-parts listing titles of at most 80 characters from product keywords, vehicle makes, models or families, and fitment years, using `for` before vehicle brands.
---

# eBay Title Generator

1. Lead with the core product keyword.
2. Add `for`, make, and model or family member names.
3. Add a compact year range when it fits.
4. Remove optional models from the right until the configured limit is met.
5. Fail rather than truncate a required keyword or split a model name.
