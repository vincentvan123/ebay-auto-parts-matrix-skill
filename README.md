# eBay Auto Parts Listing & PLP Advertising Matrix Agent

This repository is an installable Codex Skill and a standalone local tool for turning arbitrary SKU fitment into an estimated effective vehicle population, mutually exclusive listing matrix, mixed titles, and a PLP campaign matrix. It ships without product or SKU data.

## Install as a Codex Skill

Ask Codex to install this repository as a Skill:

```text
Install the Skill from https://github.com/vincentvan123/ebay-auto-parts-matrix-skill
```

Restart Codex after installation, then invoke `$ebay-auto-parts-matrix`. The repository root contains the required `SKILL.md` and `agents/openai.yaml` metadata.

Python 3.11+ is required. Install the Excel dependency once:

```bash
python3 -m pip install -r requirements.txt
```

## Run

### Local web tool

```bash
scripts/start_tool.sh
```

Open `http://127.0.0.1:8765`. Enter a SKU, product keyword, and fitment rows, or import a compatible CSV. The tool previews ranking and listing results and provides Excel/CSV downloads.

### Command line

```bash
# Generate Markdown, CSV/JSON, and Excel from sku/<SKU>/input.csv
scripts/process_sku.sh YOUR_SKU --refresh-sales

# Process an arbitrary compatible CSV outside the vault (data/Markdown stage)
python3 scripts/run_mvp.py --input /path/to/fitment.csv --refresh-sales
```

The command reads the SKU and product keyword from the input rows, then writes Markdown, intermediate JSON/CSV files, and a four-sheet Excel workbook to `outputs/<SKU>/`. Start a new product from `sku/_template/input.csv`.

## Project layout

- `config/`: configurable decision rules and source mappings.
- `data/`: reusable historical sales cache.
- `knowledge/`: business rules, product knowledge, and vehicle normalization.
- `skills/`: five reusable Skill contracts.
- `sku/`: SKU inputs and generated Obsidian notes.
- `scripts/`: deterministic fetch, calculation, and workbook code.
- `outputs/`: generated deliverables.
- `tool/`: local Chinese web interface and API server.

## Input contract

Every input is a CSV with `sku`, `core_keyword`, `make`, `model`, and either `start_year` plus `end_year` or an explicit semicolon-separated `years` value. A single run processes one SKU. Product type and fitment are not hardcoded.

The global source registry is reusable across every SKU. When an input contains a new model, the runner creates a deterministic public-source candidate for that model. Successful annual series enter the shared cache. Failed candidates remain explicit in the refresh report so an operator can add or replace the source mapping without changing code.

## Data integrity

Effective vehicle population is estimated as the sum of each compatible year's U.S. sales multiplied by its configured age-based survival rate. The default rates are 95% for ages 0-5, 85% for 6-10, 65% for 11-15, 40% for 16-20, and 20% for 21+.

A ranking entity is Core-eligible only when data coverage is at least 80%, estimated effective population is at least 150,000, and the entity reaches at least 10% of the largest eligible market. Core is capped at six listings. Missing years are never converted to zero. This is an operating estimate, not licensed registration/VIO data.
