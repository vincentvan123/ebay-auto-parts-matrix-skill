#!/usr/bin/env python3
"""Build the four-sheet deliverable with portable openpyxl."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo


HIDDEN_FIELDS = {"source_key", "source", "source_url", "Source", "Source URL"}
HEADER_LABELS = {
    "Rank": "排名", "Make": "品牌", "Model / Family": "车型 / 家族",
    "Fitment Years": "适配年份", "US Historical Sales": "适配年份美国历史销量",
    "Estimated Effective Population": "估算有效保有量",
    "Population Reference Year": "保有量估算基准年", "Market Tier": "市场等级",
    "Relative Market Size": "相对市场规模", "Coverage": "销量数据覆盖率",
    "Required Years": "所需年份数", "Available Years": "已有年份数",
    "Data Status": "数据状态", "Core / Discovery": "分组", "Decision Reason": "判定原因",
    "Listing Type": "Listing 类型", "Vehicle": "车型", "Vehicle Family": "车型家族",
    "Title": "标题", "Compatibility Scope": "Compatibility 范围",
    "Campaign Type": "Campaign 类型", "Keyword": "关键词", "Match Type": "匹配方式",
    "Campaign Role": "Campaign 角色", "Negative Keyword": "否定关键词", "Reason": "原因",
}
NUMBER_FORMATS = {
    "US Historical Sales": "#,##0", "Estimated Effective Population": "#,##0",
    "Relative Market Size": "0.0%", "Coverage": "0.0%",
}
WORKBOOK_FONT = "Arial Unicode MS"
SHEETS = [
    ("车型市场排名", "vehicle_ranking", "VehicleRankingTable"),
    ("Listing 矩阵", "listing_matrix", "ListingMatrixTable"),
    ("PLP 广告矩阵", "plp_matrix", "PLPMatrixTable"),
    ("否定关键词", "negative_keywords", "NegativeKeywordsTable"),
]


def build_sheet(workbook: Workbook, name: str, rows: list[dict], table_name: str) -> None:
    sheet = workbook.create_sheet(name)
    sheet.freeze_panes = "A2"
    sheet.sheet_view.showGridLines = False
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.print_title_rows = "1:1"
    if not rows:
        sheet.append(["暂无数据"])
        return

    headers = [header for header in rows[0] if header not in HIDDEN_FIELDS]
    sheet.append([HEADER_LABELS.get(header, header) for header in headers])
    for row in rows:
        sheet.append([row.get(header) for header in headers])

    header_fill = PatternFill("solid", fgColor="243447")
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = Font(name=WORKBOOK_FONT, bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name=WORKBOOK_FONT, size=10, color="17212B")
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    for index, header in enumerate(headers, 1):
        longest = max(len(str(HEADER_LABELS.get(header, header))), *(len(str(row.get(header, ""))) for row in rows))
        sheet.column_dimensions[get_column_letter(index)].width = min(max(longest + 2, 10), 60)
        if header in NUMBER_FORMATS:
            for cell in sheet[get_column_letter(index)][1:]:
                cell.number_format = NUMBER_FORMATS[header]

    end = f"{get_column_letter(len(headers))}{len(rows) + 1}"
    table = Table(displayName=table_name, ref=f"A1:{end}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    sheet.add_table(table)
    sheet.auto_filter.ref = f"A1:{end}"


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: build_workbook.py <workbook_data.json> <output.xlsx>")
    input_path, output_path = map(Path, sys.argv[1:])
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    workbook = Workbook()
    workbook.remove(workbook.active)
    for sheet_name, key, table_name in SHEETS:
        build_sheet(workbook, sheet_name, payload.get(key, []), table_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    print(json.dumps({"outputPath": str(output_path), "sheets": len(SHEETS)}))


if __name__ == "__main__":
    main()
