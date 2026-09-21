import importlib.util
import unittest
from datetime import date, timedelta
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_mvp.py"
SPEC = importlib.util.spec_from_file_location("run_mvp", SCRIPT)
MVP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MVP)


class MvpTests(unittest.TestCase):
    POPULATION_RULES = {
        "reference_year": 2026,
        "age_0_5_survival_rate": 0.95,
        "age_6_10_survival_rate": 0.85,
        "age_11_15_survival_rate": 0.65,
        "age_16_20_survival_rate": 0.40,
        "age_21_plus_survival_rate": 0.20,
        "large_absolute": 500000,
        "large_relative": 0.30,
        "medium_absolute": 150000,
        "medium_relative": 0.10,
        "small_absolute": 50000,
        "small_relative": 0.03,
    }

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

    def test_survival_rate_age_bands(self):
        expected = {2026: 0.95, 2021: 0.95, 2020: 0.85, 2016: 0.85, 2015: 0.65, 2011: 0.65, 2010: 0.40, 2006: 0.40, 2005: 0.20}
        for model_year, rate in expected.items():
            self.assertEqual(MVP.survival_rate(model_year, self.POPULATION_RULES, 2026), rate)

    def test_market_tiers(self):
        self.assertEqual(MVP.market_tier(600000, 0.20, self.POPULATION_RULES), "Large")
        self.assertEqual(MVP.market_tier(200000, 0.20, self.POPULATION_RULES), "Medium")
        self.assertEqual(MVP.market_tier(60000, 0.05, self.POPULATION_RULES), "Small")
        self.assertEqual(MVP.market_tier(20000, 0.02, self.POPULATION_RULES), "Long Tail")

    def test_generic_pipeline(self):
        rules = {
            "listing": {"minimum_sales_coverage": 0.8, "minimum_relative_market_share": 0.1, "minimum_effective_vehicle_population": 150000, "max_core_listings": 6},
            "vehicle_population": self.POPULATION_RULES,
        }
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
        self.assertEqual(ranking[0]["Estimated Effective Population"], 266500)
        self.assertEqual({row["Listing Type"] for row in listings}, {"Core", "Discovery"})
        self.assertTrue(any(row["Vehicle"] == "ExampleMake ModelOne" for row in plp))
        self.assertTrue(any(row["Negative Keyword"] == "ModelTwo" for row in negatives))

    def test_small_leader_is_not_core(self):
        rules = {
            "listing": {"minimum_sales_coverage": 0.8, "minimum_relative_market_share": 0.1, "minimum_effective_vehicle_population": 150000, "max_core_listings": 6},
            "vehicle_population": self.POPULATION_RULES,
        }
        fitment = [{"sku": "SKU200", "core_keyword": "Sample Part", "make": "ExampleMake", "model": "ModelOne", "years": [2021], "family": "", "family_display": "", "entity": "ModelOne", "source_key": "example-model-one"}]
        cache = [{"source_key": "example-model-one", "year": "2021", "us_sales": "10000"}]
        sources = [{"source_key": "example-model-one", "source_name": "Fixture", "source_url": "https://example.test/one"}]
        ranking = MVP.build_ranking("SKU200", fitment, cache, rules, sources)
        self.assertEqual(ranking[0]["Estimated Effective Population"], 9500)
        self.assertEqual(ranking[0]["Core / Discovery"], "Discovery")
        self.assertIn("population below 150,000", ranking[0]["Decision Reason"])

    def test_absolute_and_relative_core_gates_are_both_required(self):
        rules = {
            "listing": {"minimum_sales_coverage": 0.8, "minimum_relative_market_share": 0.1, "minimum_effective_vehicle_population": 150000, "max_core_listings": 6},
            "vehicle_population": self.POPULATION_RULES,
        }
        fitment = [
            {"sku": "SKU300", "core_keyword": "Sample Part", "make": "ExampleMake", "model": "Leader", "years": [2021], "family": "", "family_display": "", "entity": "Leader", "source_key": "example-leader"},
            {"sku": "SKU300", "core_keyword": "Sample Part", "make": "ExampleMake", "model": "Candidate", "years": [2021], "family": "", "family_display": "", "entity": "Candidate", "source_key": "example-candidate"},
        ]
        cache = [
            {"source_key": "example-leader", "year": "2021", "us_sales": "2000000"},
            {"source_key": "example-candidate", "year": "2021", "us_sales": "170000"},
        ]
        sources = [
            {"source_key": "example-leader", "source_name": "Fixture", "source_url": "https://example.test/leader"},
            {"source_key": "example-candidate", "source_name": "Fixture", "source_url": "https://example.test/candidate"},
        ]
        ranking = MVP.build_ranking("SKU300", fitment, cache, rules, sources)
        by_model = {row["Model / Family"]: row for row in ranking}
        self.assertEqual(by_model["Leader"]["Core / Discovery"], "Core")
        self.assertGreater(by_model["Candidate"]["Estimated Effective Population"], 150000)
        self.assertEqual(by_model["Candidate"]["Core / Discovery"], "Discovery")
        self.assertIn("relative size below 10%", by_model["Candidate"]["Decision Reason"])

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
