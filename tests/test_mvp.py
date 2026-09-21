import importlib.util
import unittest
from datetime import date, timedelta
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_mvp.py"
SPEC = importlib.util.spec_from_file_location("run_mvp", SCRIPT)
MVP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MVP)


class MvpTests(unittest.TestCase):
    def test_non_contiguous_years(self):
        self.assertEqual(MVP.format_years([2004, 2006]), "2004, 2006")

    def test_contiguous_years(self):
        self.assertEqual(MVP.format_years([2005, 2006, 2007]), "2005-2007")

    def test_title_limit(self):
        title = MVP.build_title("Sample Part", "ExampleMake", ["ModelOne", "ModelTwo", "ModelThree"], list(range(2010, 2024)), 80)
        self.assertLessEqual(len(title), 80)
        self.assertIn("for ExampleMake", title)

    def test_family_title_can_omit_ambiguous_years(self):
        title = MVP.build_title("Sample Part", "ExampleMake", ["ModelOne", "ModelTwo"], [], 80)
        self.assertEqual(title, "Sample Part for ExampleMake ModelOne ModelTwo")

    def test_parse_current_table(self):
        page = "<table><tr><th>Year</th><th>Units</th></tr><tr><td>2005</td><td>168,811</td></tr><tr><td>2006</td><td>178,351</td></tr></table>"
        self.assertEqual(MVP.parse_annual_sales(page), {2005: 168811, 2006: 178351})

    def test_monthly_table_is_not_treated_as_annual(self):
        page = (
            "<table><tr><th>Year</th><th>Jan</th><th>Feb</th></tr>"
            "<tr><td>2005</td><td>5,566</td><td>6,000</td></tr>"
            "<tr><td>2006</td><td>7,654</td><td>8,000</td></tr></table>"
            "<table><tr><th>Year</th><th>Sales Units</th></tr>"
            "<tr><td>2005</td><td>107,155</td></tr>"
            "<tr><td>2006</td><td>106,971</td></tr></table>"
        )
        self.assertEqual(MVP.parse_annual_sales(page), {2005: 107155, 2006: 106971})

    def test_unknown_source_candidate(self):
        fitment = [{"source_key": "examplemake-modelone", "make": "ExampleMake", "entity": "ModelOne"}]
        sources = MVP.add_candidate_sources([], fitment)
        self.assertEqual(sources[0]["source_url"], "https://www.goodcarbadcar.net/examplemake-modelone-sales-figures/")

    def test_new_source_refreshes_even_when_other_cache_exists(self):
        sources = [{"source_key": "example-model-one"}, {"source_key": "example-model-two"}]
        cache = [{"source_key": "example-model-one", "last_updated": date.today().isoformat()}]
        pending = MVP.sources_needing_refresh(sources, cache, 365)
        self.assertEqual([row["source_key"] for row in pending], ["example-model-two"])

    def test_stale_source_refreshes(self):
        sources = [{"source_key": "example-model-one"}]
        cache = [{"source_key": "example-model-one", "last_updated": (date.today() - timedelta(days=366)).isoformat()}]
        self.assertEqual(MVP.sources_needing_refresh(sources, cache, 365), sources)

    def test_generic_pipeline(self):
        rules = {"listing": {"minimum_sales_coverage": 0.8, "minimum_relative_market_share": 0.1, "max_core_listings": 6}}
        fitment = [
            {"sku": "SKU100", "core_keyword": "Sample Part", "make": "ExampleMake", "model": "ModelOne", "years": [2012, 2013], "family": "", "family_display": "", "entity": "ModelOne", "source_key": "example-model-one"},
            {"sku": "SKU100", "core_keyword": "Sample Part", "make": "ExampleMake", "model": "ModelTwo", "years": [2012, 2013], "family": "", "family_display": "", "entity": "ModelTwo", "source_key": "example-model-two"},
        ]
        cache = [
            {"source_key": "example-model-one", "year": "2012", "us_sales": "200000"},
            {"source_key": "example-model-one", "year": "2013", "us_sales": "210000"},
            {"source_key": "example-model-two", "year": "2012", "us_sales": "5000"},
            {"source_key": "example-model-two", "year": "2013", "us_sales": "6000"},
        ]
        sources = [
            {"source_key": "example-model-one", "source_name": "Fixture", "source_url": "https://example.test/one"},
            {"source_key": "example-model-two", "source_name": "Fixture", "source_url": "https://example.test/two"},
        ]
        ranking = MVP.build_ranking("SKU100", fitment, cache, rules, sources)
        listings = MVP.build_listings("SKU100", "Sample Part", ranking, 80)
        plp, negatives = MVP.build_plp("SKU100", "Sample Part", listings, True, "Phrase")
        self.assertEqual([row["Model / Family"] for row in ranking if row["Core / Discovery"] == "Core"], ["ModelOne"])
        self.assertEqual({row["Listing Type"] for row in listings}, {"Core", "Discovery"})
        self.assertTrue(any(row["Vehicle"] == "ExampleMake ModelOne" for row in plp))
        self.assertTrue(any(row["Negative Keyword"] == "ModelTwo" for row in negatives))

    def test_discovery_mixed_title_follows_market_rank(self):
        ranking = [
            {"Core / Discovery": "Core", "Make": "ExampleMake", "Model / Family": "ModelOne", "fitment_rows": [{"make": "ExampleMake", "model": "ModelOne", "years": [2012]}]},
            {"Core / Discovery": "Discovery", "Make": "ExampleMake", "Model / Family": "ModelTwo", "fitment_rows": [{"make": "ExampleMake", "model": "ModelTwo", "years": [2012]}]},
            {"Core / Discovery": "Discovery", "Make": "ExampleMake", "Model / Family": "ModelThree", "fitment_rows": [{"make": "ExampleMake", "model": "ModelThree", "years": [2012]}]},
            {"Core / Discovery": "Discovery", "Make": "ExampleMake", "Model / Family": "ModelFour", "fitment_rows": [{"make": "ExampleMake", "model": "ModelFour", "years": [2012]}]},
        ]
        listings = MVP.build_listings("SKU100", "Sample Part", ranking, 80)
        discovery = next(row for row in listings if row["Listing Type"] == "Discovery")
        self.assertEqual(discovery["Title"], "Sample Part for ExampleMake ModelTwo ModelThree ModelFour")
        self.assertNotIn("ModelOne", discovery["Title"])


if __name__ == "__main__":
    unittest.main()
