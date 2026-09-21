import importlib.util
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


if __name__ == "__main__":
    unittest.main()
