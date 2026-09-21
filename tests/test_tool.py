import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tool" / "server.py"
SPEC = importlib.util.spec_from_file_location("tool_server", SCRIPT)
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class ToolTests(unittest.TestCase):
    def test_validate_range_input(self):
        sku, keyword, rows, refresh = TOOL.validate_payload({
            "sku": "TEST-1", "core_keyword": "Sample Part", "refresh_sales": True,
            "fitments": [{"make": "ExampleMake", "model": "ModelOne", "start_year": "2012", "end_year": "2015", "years": ""}],
        })
        self.assertEqual((sku, keyword, refresh), ("TEST-1", "Sample Part", True))
        self.assertEqual(rows[0]["start_year"], "2012")

    def test_validate_explicit_years(self):
        _, _, rows, _ = TOOL.validate_payload({
            "sku": "TEST-2", "core_keyword": "Sensor",
            "fitments": [{"make": "ExampleMake", "model": "ModelTwo", "start_year": "", "end_year": "", "years": "2006, 2004;2006"}],
        })
        self.assertEqual(rows[0]["years"], "2004;2006")
        self.assertEqual(rows[0]["start_year"], "")

    def test_reject_path_like_sku(self):
        with self.assertRaisesRegex(ValueError, "SKU"):
            TOOL.validate_payload({"sku": "../bad", "core_keyword": "Part", "fitments": [{}]})

    def test_reject_reversed_years(self):
        with self.assertRaisesRegex(ValueError, "年份范围"):
            TOOL.validate_payload({
                "sku": "TEST-3", "core_keyword": "Part",
                "fitments": [{"make": "ExampleMake", "model": "ModelOne", "start_year": "2015", "end_year": "2010"}],
            })

    def test_result_payload_counts_mixed_separately(self):
        sku = "TEST-MIXED-SUMMARY"
        output_dir = TOOL.ROOT / "outputs" / sku
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            (output_dir / "workbook_data.json").write_text(json.dumps({
                "vehicle_ranking": [{
                    "Rank": 1, "Source": "Hidden", "Source URL": "https://example.test",
                    "source_key": "internal", "source": "hidden", "source_url": "https://example.test",
                }],
                "listing_matrix": [
                    {"Listing Type": "Core"},
                    {"Listing Type": "Discovery"},
                    {"Listing Type": "Mixed"},
                ],
                "plp_matrix": [],
            }), encoding="utf-8")
            result = TOOL.result_payload(sku)
            summary = result["summary"]
            self.assertEqual(summary["core_listings"], 1)
            self.assertEqual(summary["discovery_listings"], 1)
            self.assertEqual(summary["mixed_listings"], 1)
            self.assertNotIn("Source", result["vehicle_ranking"][0])
            self.assertNotIn("Source URL", result["vehicle_ranking"][0])
            self.assertNotIn("source_key", result["vehicle_ranking"][0])
            self.assertNotIn("source_url", result["vehicle_ranking"][0])
        finally:
            (output_dir / "workbook_data.json").unlink(missing_ok=True)
            output_dir.rmdir()

    def test_result_payload_uses_chinese_workbook_name_and_label(self):
        sku = "TEST-WORKBOOK-NAME"
        output_dir = TOOL.ROOT / "outputs" / sku
        output_dir.mkdir(parents=True, exist_ok=True)
        workbook_name = f"{sku}-Listing与PLP矩阵.xlsx"
        try:
            (output_dir / "workbook_data.json").write_text(json.dumps({
                "vehicle_ranking": [], "listing_matrix": [], "plp_matrix": [],
            }), encoding="utf-8")
            (output_dir / workbook_name).touch()
            result = TOOL.result_payload(sku)
            workbook = next(item for item in result["files"] if item["name"] == workbook_name)
            self.assertEqual(workbook["label"], "下载 Excel")
        finally:
            (output_dir / workbook_name).unlink(missing_ok=True)
            (output_dir / "workbook_data.json").unlink(missing_ok=True)
            output_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
