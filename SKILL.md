---
name: ebay-auto-parts-matrix
description: Estimate effective vehicle population from age-adjusted U.S. sales and generate eBay auto-parts market rankings, Core and Discovery listing matrices, required multi-model Mixed titles, PLP keyword campaigns, negative keywords, CSV files, and an Excel workbook from arbitrary SKU fitment. Use when Codex needs to process automotive compatibility data, size vehicle markets, build listing or advertising plans, or launch the bundled local Chinese web tool.
---

# eBay Auto Parts Matrix

Use the bundled deterministic pipeline. Do not invent sales, compatibility, or missing model years.

## User-facing language and privacy

- Never expose a sales source provider, source URL, or internal source key in the web UI or any user-facing Excel, CSV, Markdown, or JSON output.
- Keep source metadata only in the internal cache and refresh diagnostics.
- Prefer Chinese labels in the web UI and user-facing exports.
- Keep stable machine keys and established marketplace terms such as SKU, PLP, Listing, Core, Discovery, Mixed, Campaign, Ad Group, and Compatibility in English when they are clearer.

## Run the web tool

1. Ensure Python 3.11+ is available.
2. Install the optional Excel dependency with `python3 -m pip install -r requirements.txt` when workbook output is required.
3. Run `scripts/start_tool.sh` from this skill directory.
4. Open `http://127.0.0.1:8765`.
5. Enter one SKU, its English product keyword, and all compatible make/model/year rows.
6. Generate and inspect the ranking and listing matrix before downloading outputs.

## Run from the command line

1. Create `sku/<SKU>/input.csv` using `sku/_template/input.csv`.
2. Run `scripts/process_sku.sh <SKU>`.
3. Add `--refresh-sales` only when current public sales data must be fetched.
4. Read generated files from `outputs/<SKU>/`.

For an arbitrary CSV path, run `python3 scripts/run_mvp.py --input /path/to/input.csv`. The CSV must contain `sku`, `core_keyword`, `make`, `model`, and either a continuous `start_year`/`end_year` pair or semicolon-separated `years`.

## Apply the rules

- Treat every SKU independently. Never reuse another SKU's keyword or fitment.
- Estimate effective population only from the fitment years for the current SKU, applying configured age-based survival rates.
- Keep missing sales explicit; never treat missing values as zero.
- Require coverage, absolute effective-population, and relative-market thresholds before assigning Core; select no more than the configured number of Core listings.
- Put every compatibility row in exactly one primary Core or Discovery listing.
- When a SKU fits at least two distinct models, also create one supplemental Mixed listing covering the full fitment.
- Order Discovery and Mixed title models by descending market rank.
- Keep supplemental Mixed listings out of PLP so they do not compete with primary model-targeted campaigns.
- Keep titles within the configured 80-character limit.
- When keyword expansion is requested, fetch ranked eBay search suggestions, require operator selection, then merge novel words into titles in returned order.
- Treat suggestion order as a search-habit signal rather than official search volume, and never select an unverified product attribute.
- Review data gaps before using the output for live advertising decisions.

Read [references/methodology.md](references/methodology.md) when changing ranking, title, family, or PLP behavior. Use the narrower contracts in `skills/` when modifying one pipeline stage.
