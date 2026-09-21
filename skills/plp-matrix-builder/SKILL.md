---
name: plp-matrix-builder
description: Build Core and Discovery eBay PLP campaign, ad-group, keyword, match-type, and negative-keyword matrices aligned to listing compatibility.
---

# PLP Matrix Builder

1. Create one campaign per primary Core or Discovery listing with deterministic names; skip supplemental Mixed listings.
2. Create one ad group per compatibility model.
3. Generate model-product and make-model-product terms as Phrase match; never add the standalone word `for` to PLP keywords.
4. Generate each configured year term as Exact match.
5. Negate competing Core/model intents according to project rules.
6. Deduplicate keywords case-insensitively within each ad group.
7. Export PLP rows and negative-keyword rows separately.
