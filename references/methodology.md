# Matrix Methodology

## Input

Process one SKU per run. Each fitment row supplies a make, model, and either a continuous year range or explicit years. Normalize casing without changing the compatibility meaning.

## Vehicle ranking

Estimate effective vehicle population as `sum(compatible-year U.S. sales x survival rate for that model-year age)`. Default survival rates are 95% for ages 0-5, 85% for 6-10, 65% for 11-15, 40% for 16-20, and 20% for 21+. Combine configured vehicle families once so trim-like models do not double count a shared sales series. Record source, coverage, reference year, and missing years.

Classify markets as Large at 500,000 estimated vehicles or 30% of the leader, Medium at 150,000 or 10%, Small at 50,000 or 3%, and Long Tail below both Small thresholds. Treat the classification as an operating estimate rather than licensed registration/VIO data.

## Listing matrix

Select Core entities only when they meet all three gates: minimum data coverage, minimum absolute effective population, and minimum relative size versus the largest eligible entity. Apply the configured maximum after those gates. Assign one listing to each Core model or family and group all remaining compatibility by make into Discovery listings. These two primary pools must be mutually exclusive and collectively complete.

For every SKU with at least two distinct compatible models, add one supplemental Mixed listing whose Compatibility covers the full fitment. Order models in Discovery and Mixed titles by market rank. Omit a combined year suffix when members have different year ranges. Keep the full compatibility scope in the output even when the title length limit omits lower-ranked models.

Use eBay search suggestions as an ordered search-habit signal when the operator requests keyword expansion. Require the operator to approve suggestions before title use because suggestions may contain unverified product attributes. Merge only novel words, preserve suggestion order, keep the core keyword first, and omit lower-priority expansion words before exceeding the 80-character title limit.

## PLP matrix

Build deterministic campaigns for primary Core and Discovery listings with model-specific ad groups. Do not create PLP campaigns for supplemental Mixed listings. Generate model-product and make-model-product terms as Phrase match, without the standalone word `for`. Generate each configured year-make-model-product term as Exact match, then add negatives that isolate competing model intent. Deduplicate keywords case-insensitively.

## Review

Before operational use, review partial or missing sales coverage, title length, compatibility completeness, duplicate assignment, and workbook generation. The tool creates planning artifacts and does not publish eBay listings or campaigns.
