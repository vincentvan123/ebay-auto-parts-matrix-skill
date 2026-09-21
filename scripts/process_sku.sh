#!/bin/sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "Usage: scripts/process_sku.sh <SKU> [--refresh-sales]" >&2
  exit 2
fi

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sku=$1
shift

python3 "$project_dir/scripts/run_mvp.py" --sku "$sku" "$@"

if ! python3 -c 'import openpyxl' >/dev/null 2>&1; then
  echo "Data and Markdown outputs created. Install requirements.txt to generate Excel." >&2
  exit 0
fi

python3 "$project_dir/scripts/build_workbook.py" \
  "$project_dir/outputs/$sku/workbook_data.json" \
  "$project_dir/outputs/$sku/$sku-listing-plp-matrix.xlsx"
