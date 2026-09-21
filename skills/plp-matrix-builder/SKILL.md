---
name: plp-matrix-builder
description: Build Core and Discovery eBay PLP campaign, ad-group, keyword, match-type, and negative-keyword matrices aligned to listing compatibility.
---

# PLP Matrix Builder

1. Create one campaign per listing with deterministic names.
2. Create one ad group per compatibility model.
3. Generate model, make-model, and `for` terms as Phrase match.
4. Generate each configured year term as Exact match.
5. Negate competing Core/model intents according to project rules.
6. Deduplicate keywords case-insensitively within each ad group.
7. Export PLP rows and negative-keyword rows separately.
