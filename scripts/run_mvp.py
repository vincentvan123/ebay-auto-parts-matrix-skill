#!/usr/bin/env python3
"""Run the fitment -> ranking -> listing -> PLP MVP with stdlib only."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import subprocess
import sys
import tomllib
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
DATA = ROOT / "data"
PUBLIC_HIDDEN_FIELDS = {
    "source_key", "source", "source_url", "members", "fitment_rows", "eligible", "Source", "Source URL"
}
OUTPUT_LABELS = {
    "Rank": "排名",
    "Make": "品牌",
    "Model": "车型",
    "Model / Family": "车型 / 家族",
    "Fitment Years": "适配年份",
    "US Historical Sales": "适配年份美国历史销量",
    "Estimated Effective Population": "估算有效保有量",
    "Population Reference Year": "保有量估算基准年",
    "Market Tier": "市场等级",
    "Relative Market Size": "相对市场规模",
    "Coverage": "销量数据覆盖率",
    "Required Years": "所需年份数",
    "Available Years": "已有年份数",
    "Data Status": "数据状态",
    "Core / Discovery": "分组",
    "Decision Reason": "判定原因",
    "Listing Type": "Listing 类型",
    "Vehicle": "车型",
    "Vehicle Family": "车型家族",
    "Title": "标题",
    "Compatibility Scope": "Compatibility 范围",
    "Campaign Type": "Campaign 类型",
    "Keyword": "关键词",
    "Match Type": "匹配方式",
    "Campaign Role": "Campaign 角色",
    "Negative Keyword": "否定关键词",
    "Reason": "原因",
    "Years": "年份",
    "Family": "家族",
}

CANONICAL_MODELS: dict[str, str] = {}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str], labels: dict[str, str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([(labels or {}).get(field, field) for field in fields])
        writer.writerows([[row.get(field, "") for field in fields] for row in rows])


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def canonical_model(model: str) -> str:
    clean = clean_text(model)
    return CANONICAL_MODELS.get(clean.casefold(), clean)


def parse_years(row: dict[str, str]) -> list[int]:
    if row.get("years", "").strip():
        years = sorted({int(x.strip()) for x in row["years"].split(";") if x.strip()})
    else:
        start, end = int(row["start_year"]), int(row["end_year"])
        if start > end:
            raise ValueError(f"Reversed year range for {row['make']} {row['model']}: {start}-{end}")
        years = list(range(start, end + 1))
    if not years or any(y < 1900 or y > 2100 for y in years):
        raise ValueError(f"Invalid fitment years for {row['make']} {row['model']}")
    return years


def parse_annual_sales(page: str) -> dict[int, int]:
    for table in re.findall(r"<table\b[^>]*>.*?</table>", page, flags=re.I | re.S):
        table_rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", table, flags=re.I | re.S)
        if not table_rows:
            continue
        headers = [clean_text(x).casefold() for x in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", table_rows[0], flags=re.I | re.S)]
        if len(headers) < 2 or headers[0] != "year" or headers[1] not in {"units", "sales", "sales units", "sold"}:
            continue
        annual: dict[int, int] = {}
        for tr in table_rows[1:]:
            cells = [clean_text(x) for x in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, flags=re.I | re.S)]
            if len(cells) < 2:
                continue
            match = re.fullmatch(r"(19|20)\d{2}(?:\s*\([^)]*\))?", cells[0])
            units = re.fullmatch(r"[\d,]+", cells[1])
            if match and units:
                year = int(cells[0][:4])
                annual[year] = int(cells[1].replace(",", ""))
        if len(annual) >= 2:
            return annual

    # Legacy pages expose the same first (U.S.) annual series in chart JSON.
    for match in re.finditer(r"render_data:\s*(\{.*?\})\s*,\s*\n", page, flags=re.S):
        try:
            obj = json.loads(match.group(1))
            options = obj["options"]
            years = options["xaxis"]["categories"]
            values = options["series"][0]["data"]
            annual = {int(y): int(v) for y, v in zip(years, values) if re.fullmatch(r"\d{4}", str(y))}
            if len(annual) >= 2:
                return annual
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    raise ValueError("No annual U.S. sales series found")


def fetch_source(source: dict[str, str], user_agent: str) -> tuple[dict[str, str], dict[int, int] | None, str | None]:
    try:
        # macOS system Python may not inherit the same trusted CA bundle as curl.
        # Use curl without a shell so the configured URL remains the only target.
        result = subprocess.run(
            ["curl", "--fail", "--location", "--silent", "--show-error", "--max-time", "35",
             "--user-agent", user_agent, source["source_url"]],
            check=True, capture_output=True,
        )
        page = result.stdout.decode("utf-8", errors="replace")
        return source, parse_annual_sales(page), None
    except Exception as exc:  # Store the bounded source-specific failure in the report.
        return source, None, f"{type(exc).__name__}: {exc}"


def refresh_cache(sources: list[dict[str, str]], user_agent: str, cache_path: Path, report_path: Path) -> None:
    existing = read_csv(cache_path) if cache_path.exists() else []
    by_source = defaultdict(list)
    for row in existing:
        by_source[row["source_key"]].append(row)

    report = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(fetch_source, source, user_agent) for source in sources]
        for future in as_completed(futures):
            source, annual, error = future.result()
            key = source["source_key"]
            if annual:
                by_source[key] = [{
                    "source_key": key,
                    "make": source["make"],
                    "model_or_family": source["market_entity"],
                    "year": year,
                    "us_sales": units,
                    "source": source["source_name"],
                    "source_url": source["source_url"],
                    "last_updated": date.today().isoformat(),
                } for year, units in sorted(annual.items())]
            report.append({
                "source_key": key,
                "status": "updated" if annual else "error",
                "rows": len(annual or {}),
                "error": error or "",
                "source_url": source["source_url"],
            })

    flat = [row for key in sorted(by_source) for row in by_source[key]]
    write_csv(cache_path, flat, ["source_key", "make", "model_or_family", "year", "us_sales", "source", "source_url", "last_updated"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(sorted(report, key=lambda x: x["source_key"]), indent=2), encoding="utf-8")


def sources_needing_refresh(sources: list[dict[str, str]], cache_rows: list[dict[str, str]], max_age_days: int, force: bool = False) -> list[dict[str, str]]:
    if force:
        return sources
    latest = {}
    for row in cache_rows:
        try:
            updated = date.fromisoformat(row["last_updated"])
        except (KeyError, ValueError):
            continue
        key = row["source_key"]
        latest[key] = max(updated, latest.get(key, updated))
    cutoff = date.today() - timedelta(days=max_age_days)
    return [source for source in sources if source["source_key"] not in latest or latest[source["source_key"]] < cutoff]


def survival_rate(model_year: int, population_rules: dict, reference_year: int | None = None) -> float:
    reference = reference_year or int(population_rules.get("reference_year", 0)) or date.today().year
    age = max(0, reference - model_year)
    if age <= 5:
        return population_rules["age_0_5_survival_rate"]
    if age <= 10:
        return population_rules["age_6_10_survival_rate"]
    if age <= 15:
        return population_rules["age_11_15_survival_rate"]
    if age <= 20:
        return population_rules["age_16_20_survival_rate"]
    return population_rules["age_21_plus_survival_rate"]


def market_tier(effective_population: int | None, relative_size: float, population_rules: dict) -> str:
    if effective_population is None:
        return "Unknown"
    if effective_population >= population_rules["large_absolute"] or relative_size >= population_rules["large_relative"]:
        return "Large"
    if effective_population >= population_rules["medium_absolute"] or relative_size >= population_rules["medium_relative"]:
        return "Medium"
    if effective_population >= population_rules["small_absolute"] or relative_size >= population_rules["small_relative"]:
        return "Small"
    return "Long Tail"


def format_years(years: list[int]) -> str:
    years = sorted(set(years))
    groups = []
    start = previous = years[0]
    for year in years[1:] + [None]:
        if year is not None and year == previous + 1:
            previous = year
            continue
        groups.append(str(start) if start == previous else f"{start}-{previous}")
        if year is not None:
            start = previous = year
    return ", ".join(groups)


def slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Z0-9]+", "-", value.upper())).strip("-")


def build_title(keyword: str, make: str, models: list[str], years: list[int], limit: int, discovery: bool = False) -> str:
    chosen = list(models)
    suffix = format_years(years) if years else ""
    while chosen:
        vehicle = " ".join(chosen)
        title = " ".join(part for part in [keyword, "for", make, vehicle, suffix] if part).strip()
        if len(title) <= limit:
            return title
        chosen.pop()
    fallback = " ".join(part for part in [keyword, "for", make, "Multiple Models" if discovery else models[0], suffix] if part)
    if len(fallback) > limit:
        raise ValueError(f"Cannot generate title within {limit} characters: {fallback}")
    return fallback


def build_mixed_title(keyword: str, rows: list[dict], limit: int) -> str:
    vehicles = []
    seen = set()
    for row in rows:
        key = (row["make"].casefold(), row["model"].casefold())
        if key not in seen:
            vehicles.append((row["make"], row["model"]))
            seen.add(key)
    if len(vehicles) < 2:
        raise ValueError("A mixed title requires at least two distinct vehicle models")

    one_make = len({make.casefold() for make, _ in vehicles}) == 1
    for count in range(len(vehicles), 1, -1):
        selected = vehicles[:count]
        if one_make:
            vehicle_text = f"{selected[0][0]} " + " ".join(model for _, model in selected)
        else:
            vehicle_text = " ".join(f"{make} {model}" for make, model in selected)
        title = f"{keyword} for {vehicle_text}"
        if len(title) <= limit:
            return title
    raise ValueError(f"Cannot fit two vehicle models in a mixed title within {limit} characters")


def normalize_fitment(sku: str, rows: list[dict[str, str]], families: list[dict[str, str]], sources: list[dict[str, str]]) -> list[dict]:
    family_map = {(r["make"].casefold(), r["model"].casefold()): r for r in families}
    source_map = {(r["make"].casefold(), r["market_entity"].casefold()): r["source_key"] for r in sources}
    normalized, seen = [], set()
    for row in rows:
        if row["sku"] != sku:
            continue
        make = clean_text(row["make"]).title()
        model = canonical_model(row["model"])
        years = parse_years(row)
        family = family_map.get((make.casefold(), model.casefold()))
        entity = family["family"] if family else model
        source_key = family["source_key"] if family else source_map.get((make.casefold(), model.casefold()), slug(f"{make}-{model}").lower())
        for year in years:
            key = (make.casefold(), model.casefold(), year)
            if key in seen:
                raise ValueError(f"Duplicate compatibility: {year} {make} {model}")
            seen.add(key)
        normalized.append({
            "sku": sku, "core_keyword": row["core_keyword"].strip(), "make": make,
            "model": model, "years": years, "family": family["family"] if family else "",
            "family_display": family["family_display"] if family else "",
            "entity": entity, "source_key": source_key,
        })
    if not normalized:
        raise ValueError(f"No fitment found for {sku}")
    return normalized


def add_candidate_sources(sources: list[dict[str, str]], fitment: list[dict]) -> list[dict[str, str]]:
    """Add safe, deterministic source candidates for previously unseen entities.

    A candidate is only trusted after the normal parser extracts an annual series.
    Failed pages are retained in the refresh report, never converted to zero sales.
    """
    augmented = list(sources)
    known = {row["source_key"] for row in sources}
    entities = {}
    for row in fitment:
        entities[row["source_key"]] = (row["make"], row["entity"])
    for source_key, (make, entity) in sorted(entities.items()):
        if source_key in known:
            continue
        url_slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", f"{make} {entity}".casefold())).strip("-")
        augmented.append({
            "source_key": source_key,
            "make": make,
            "market_entity": entity,
            "source_name": "GoodCarBadCar",
            "source_url": f"https://www.goodcarbadcar.net/{url_slug}-sales-figures/",
        })
    return augmented


def build_ranking(sku: str, fitment: list[dict], cache_rows: list[dict[str, str]], rules: dict, sources: list[dict[str, str]]) -> list[dict]:
    sales = defaultdict(dict)
    for row in cache_rows:
        sales[row["source_key"]][int(row["year"])] = int(row["us_sales"])
    source_by_key = {r["source_key"]: r for r in sources}
    grouped = defaultdict(list)
    for row in fitment:
        grouped[(row["make"], row["entity"], row["source_key"])].append(row)

    ranking = []
    min_coverage = rules["listing"]["minimum_sales_coverage"]
    population_rules = rules["vehicle_population"]
    reference_year = int(population_rules.get("reference_year", 0)) or date.today().year
    for (make, entity, source_key), members in grouped.items():
        required = sorted({year for member in members for year in member["years"]})
        available = [year for year in required if year in sales[source_key]]
        coverage = len(available) / len(required)
        total = sum(sales[source_key][year] for year in available) if available else None
        effective_population = round(sum(
            sales[source_key][year] * survival_rate(year, population_rules, reference_year)
            for year in available
        )) if available else None
        source = source_by_key.get(source_key, {})
        ranking.append({
            "SKU": sku, "Rank": None, "Make": make, "Model / Family": entity,
            "Fitment Years": format_years(required), "US Historical Sales": total,
            "Estimated Effective Population": effective_population,
            "Population Reference Year": reference_year,
            "Market Tier": "Unknown", "Relative Market Size": 0.0,
            "Source": source.get("source_name", "Missing"), "Source URL": source.get("source_url", ""),
            "Core / Discovery": "Discovery", "Coverage": coverage,
            "Required Years": len(required), "Available Years": len(available),
            "Data Status": "Complete" if coverage == 1 else ("Partial" if available else "Missing"),
            "Decision Reason": "", "source_key": source_key,
            "members": [m["model"] for m in members], "fitment_rows": members,
            "eligible": coverage >= min_coverage and total is not None,
        })

    ranking.sort(key=lambda r: (r["Estimated Effective Population"] is None, -(r["Estimated Effective Population"] or 0), r["Make"], r["Model / Family"]))
    for index, row in enumerate(ranking, 1):
        row["Rank"] = index
    eligible = [r for r in ranking if r["eligible"]]
    max_population = max((r["Estimated Effective Population"] for r in eligible), default=0)
    threshold = rules["listing"]["minimum_relative_market_share"]
    minimum_population = rules["listing"]["minimum_effective_vehicle_population"]
    max_core = rules["listing"]["max_core_listings"]
    for row in ranking:
        population = row["Estimated Effective Population"]
        relative = population / max_population if population is not None and max_population else 0.0
        row["Relative Market Size"] = relative
        row["Market Tier"] = market_tier(population, relative, population_rules)
    core = [
        r for r in eligible
        if r["Estimated Effective Population"] >= minimum_population
        and r["Relative Market Size"] >= threshold
    ][:max_core]
    core_keys = {r["source_key"] for r in core}
    for row in ranking:
        if row["source_key"] in core_keys:
            row["Core / Discovery"] = "Core"
            row["Decision Reason"] = (
                f"Core; estimated population {row['Estimated Effective Population']:,}, "
                f"{row['Relative Market Size']:.1%} of largest market"
            )
        elif not row["eligible"]:
            row["Decision Reason"] = f"Discovery pending data; coverage {row['Coverage']:.0%} below {min_coverage:.0%}"
        else:
            reasons = []
            if row["Estimated Effective Population"] < minimum_population:
                reasons.append(f"population below {minimum_population:,}")
            if row["Relative Market Size"] < threshold:
                reasons.append(f"relative size below {threshold:.0%}")
            if not reasons:
                reasons.append(f"outside top {max_core} Core cap")
            row["Decision Reason"] = "Discovery; " + "; ".join(reasons)
    return ranking


def compatibility_scope(rows: list[dict]) -> str:
    return "; ".join(f"{format_years(row['years'])} {row['make']} {row['model']}" for row in sorted(rows, key=lambda r: (r["make"], r["model"])))


def build_listings(sku: str, keyword: str, ranking: list[dict], title_limit: int) -> list[dict]:
    listings, assigned = [], set()
    core = [r for r in ranking if r["Core / Discovery"] == "Core"]
    for rank_row in core:
        rows = rank_row["fitment_rows"]
        years = sorted({y for row in rows for y in row["years"]})
        models = [row["model"] for row in rows]
        title_years = years if len({tuple(row["years"]) for row in rows}) == 1 else []
        listing_id = f"{sku}-L{len(listings)+1:02d}"
        title = build_title(keyword, rank_row["Make"], models, title_years, title_limit)
        listings.append({
            "SKU": sku, "Listing ID": listing_id, "Listing Type": "Core",
            "Vehicle": rank_row["Model / Family"], "Vehicle Family": rank_row["Model / Family"] if len(rows) > 1 else "",
            "Title": title, "Compatibility Scope": compatibility_scope(rows), "fitment_rows": rows,
        })
        assigned.update((r["make"], r["model"], y) for r in rows for y in r["years"])

    remaining = defaultdict(list)
    for rank_row in ranking:
        if rank_row["Core / Discovery"] != "Core":
            # `ranking` is already ordered by descending market size, with
            # missing-data entities last. Preserve that order for mixed titles.
            remaining[rank_row["Make"]].append(rank_row)
    for make in sorted(remaining):
        rows = [fitment_row for rank_row in remaining[make] for fitment_row in rank_row["fitment_rows"]]
        years = sorted({y for row in rows for y in row["years"]})
        models = [r["model"] for r in rows]
        listing_id = f"{sku}-L{len(listings)+1:02d}"
        listings.append({
            "SKU": sku, "Listing ID": listing_id, "Listing Type": "Discovery",
            "Vehicle": f"{make} Discovery", "Vehicle Family": "",
            "Title": build_title(keyword, make, models, [], title_limit, discovery=True),
            "Compatibility Scope": compatibility_scope(rows), "fitment_rows": rows,
        })
        assigned.update((r["make"], r["model"], y) for r in rows for y in r["years"])

    expected = {(r["make"], r["model"], y) for rank_row in ranking for r in rank_row["fitment_rows"] for y in r["years"]}
    if assigned != expected:
        raise AssertionError("Compatibility assignment is not exhaustive and mutually exclusive")

    mixed_rows = [fitment_row for rank_row in ranking for fitment_row in rank_row["fitment_rows"]]
    distinct_models = {(row["make"].casefold(), row["model"].casefold()) for row in mixed_rows}
    if len(distinct_models) >= 2:
        makes = {row["make"].casefold() for row in mixed_rows}
        listing_id = f"{sku}-L{len(listings)+1:02d}"
        listings.append({
            "SKU": sku, "Listing ID": listing_id, "Listing Type": "Mixed",
            "Vehicle": f"{mixed_rows[0]['make']} Mixed" if len(makes) == 1 else "Multi-Make Mixed",
            "Vehicle Family": "",
            "Title": build_mixed_title(keyword, mixed_rows, title_limit),
            "Compatibility Scope": compatibility_scope(mixed_rows), "fitment_rows": mixed_rows,
        })
    return listings


def build_plp(
    sku: str,
    keyword: str,
    listings: list[dict],
    include_years: bool,
    phrase_match_type: str,
    year_match_type: str,
) -> tuple[list[dict], list[dict]]:
    plp, negatives = [], []
    core_models = {r["model"] for listing in listings if listing["Listing Type"] == "Core" for r in listing["fitment_rows"]}
    all_models = {r["model"] for listing in listings for r in listing["fitment_rows"]}
    for listing in listings:
        if listing["Listing Type"] == "Mixed":
            continue
        campaign = f"{sku}-{slug(listing['Vehicle'].replace(' Discovery', ''))}-{listing['Listing Type'].upper()}"
        own_models = {r["model"] for r in listing["fitment_rows"]}
        for row in listing["fitment_rows"]:
            ad_group = row["model"]
            terms = [
                (f"{row['model']} {keyword}", phrase_match_type),
                (f"{row['make']} {row['model']} {keyword}", phrase_match_type),
            ]
            if include_years:
                terms.extend(
                    (f"{year} {row['make']} {row['model']} {keyword}", year_match_type)
                    for year in row["years"]
                )
            seen = set()
            for term, match_type in terms:
                folded = term.casefold()
                if folded in seen:
                    continue
                seen.add(folded)
                plp.append({
                    "SKU": sku, "Campaign": campaign, "Campaign Type": listing["Listing Type"].upper(),
                    "Ad Group": ad_group, "Listing": listing["Listing ID"],
                    "Vehicle": f"{row['make']} {row['model']}", "Keyword": term, "Match Type": match_type,
                    "Campaign Role": "Conversion" if listing["Listing Type"] == "Core" else "Testing",
                })
        negative_models = (all_models - own_models) if listing["Listing Type"] == "Core" else core_models
        for model in sorted(negative_models, key=str.casefold):
            negatives.append({
                "Campaign": campaign, "Negative Keyword": model,
                "Reason": "Keep other vehicle intent out of Core" if listing["Listing Type"] == "Core" else "Route Core vehicle intent to its dedicated listing",
            })
    return plp, negatives


def public_row(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in PUBLIC_HIDDEN_FIELDS}


def markdown_table(rows: list[dict], fields: list[str], labels: dict[str, str] | None = None) -> str:
    def value(row, field):
        val = row.get(field, "")
        if isinstance(val, float):
            return f"{val:.1%}"
        if isinstance(val, int) and field in {"US Historical Sales", "Estimated Effective Population"}:
            return f"{val:,}"
        return str(val if val is not None else "N/A").replace("|", "\\|")
    headers = [(labels or {}).get(field, field) for field in fields]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    lines.extend("| " + " | ".join(value(row, f) for f in fields) + " |" for row in rows)
    return "\n".join(lines)


def write_outputs(sku: str, ranking: list[dict], listings: list[dict], plp: list[dict], negatives: list[dict], fitment: list[dict]) -> Path:
    out = ROOT / "outputs" / sku
    out.mkdir(parents=True, exist_ok=True)
    public_ranking = [public_row(r) for r in ranking]
    public_listings = [public_row(r) for r in listings]
    payload = {"vehicle_ranking": public_ranking, "listing_matrix": public_listings, "plp_matrix": plp, "negative_keywords": negatives}
    (out / "workbook_data.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(out / "vehicle_ranking.csv", public_ranking, list(public_ranking[0]), OUTPUT_LABELS)
    write_csv(out / "listing_matrix.csv", public_listings, list(public_listings[0]), OUTPUT_LABELS)
    write_csv(out / "plp_matrix.csv", plp, list(plp[0]) if plp else ["SKU", "Campaign", "Campaign Type", "Ad Group", "Listing", "Vehicle", "Keyword", "Match Type", "Campaign Role"], OUTPUT_LABELS)
    write_csv(out / "negative_keywords.csv", negatives, list(negatives[0]) if negatives else ["Campaign", "Negative Keyword", "Reason"], OUTPUT_LABELS)

    sku_dir = ROOT / "sku" / sku
    sku_dir.mkdir(parents=True, exist_ok=True)
    ranking_fields = ["Rank", "Make", "Model / Family", "Fitment Years", "US Historical Sales", "Estimated Effective Population", "Market Tier", "Relative Market Size", "Coverage", "Data Status", "Core / Discovery", "Decision Reason"]
    (sku_dir / "fitment.md").write_text("# 标准化适配\n\n" + markdown_table([
        {"Make": r["make"], "Model": r["model"], "Years": format_years(r["years"]), "Family": r["family"] or "-"}
        for r in fitment
    ], ["Make", "Model", "Years", "Family"], OUTPUT_LABELS) + "\n", encoding="utf-8")
    (sku_dir / "vehicle-ranking.md").write_text("# 车型市场排名\n\n" + markdown_table(public_ranking, ranking_fields, OUTPUT_LABELS) + "\n", encoding="utf-8")
    (sku_dir / "listing-matrix.md").write_text("# Listing 矩阵\n\n" + markdown_table(public_listings, ["Listing ID", "Listing Type", "Vehicle", "Title", "Compatibility Scope"], OUTPUT_LABELS) + "\n", encoding="utf-8")
    (sku_dir / "plp-matrix.md").write_text(
        "# PLP 广告矩阵\n\n" + markdown_table(plp, ["Campaign", "Campaign Type", "Ad Group", "Listing", "Vehicle", "Keyword", "Match Type"], OUTPUT_LABELS) +
        "\n\n行数：" + str(len(plp)) + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sku", help="SKU whose conventional input is sku/<SKU>/input.csv")
    parser.add_argument("--input", type=Path, help="Arbitrary fitment CSV matching the project input contract")
    parser.add_argument("--refresh-sales", action="store_true")
    args = parser.parse_args()
    if not args.sku and not args.input:
        parser.error("provide --sku or --input")
    rules = tomllib.loads((CONFIG / "rules.toml").read_text(encoding="utf-8"))
    sources = read_csv(CONFIG / "sales_sources.csv")
    families = read_csv(CONFIG / "vehicle_family.csv")
    input_path = args.input.resolve() if args.input else ROOT / "sku" / args.sku / "input.csv"
    input_rows = read_csv(input_path)
    input_skus = sorted({row["sku"].strip() for row in input_rows if row.get("sku", "").strip()})
    if args.sku:
        sku = args.sku
        if sku not in input_skus:
            raise ValueError(f"SKU {sku} is not present in {input_path}")
    elif len(input_skus) == 1:
        sku = input_skus[0]
    else:
        raise ValueError(f"Input must contain exactly one SKU when --sku is omitted; found {input_skus}")
    fitment = normalize_fitment(sku, input_rows, families, sources)
    sources = add_candidate_sources(sources, fitment)
    needed_source_keys = {row["source_key"] for row in fitment}
    active_sources = [row for row in sources if row["source_key"] in needed_source_keys]
    cache_path = DATA / "vehicle_sales_cache.csv"
    report_path = ROOT / "outputs" / sku / "sales_refresh_report.json"
    cache_rows = read_csv(cache_path) if cache_path.exists() else []
    refresh_sources = sources_needing_refresh(
        active_sources, cache_rows, rules["sales"]["cache_max_age_days"], force=args.refresh_sales,
    )
    if refresh_sources:
        refresh_cache(refresh_sources, rules["sales"]["user_agent"], cache_path, report_path)
    if not cache_path.exists():
        raise FileNotFoundError("Sales cache does not exist; run with --refresh-sales")
    ranking = build_ranking(sku, fitment, read_csv(cache_path), rules, active_sources)
    keyword = fitment[0]["core_keyword"]
    if any(row["core_keyword"] != keyword for row in fitment):
        raise ValueError("All rows for one SKU must use the same core_keyword")
    listings = build_listings(sku, keyword, ranking, rules["title"]["max_characters"])
    plp, negatives = build_plp(
        sku,
        keyword,
        listings,
        rules["plp"]["include_year_keywords"],
        rules["plp"]["phrase_match_type"],
        rules["plp"]["year_match_type"],
    )
    out = write_outputs(sku, ranking, listings, plp, negatives, fitment)
    print(json.dumps({
        "sku": sku, "input": str(input_path), "ranking_entities": len(ranking), "core_listings": sum(x["Listing Type"] == "Core" for x in listings),
        "discovery_listings": sum(x["Listing Type"] == "Discovery" for x in listings),
        "mixed_listings": sum(x["Listing Type"] == "Mixed" for x in listings), "plp_rows": len(plp),
        "missing_or_partial_entities": sum(x["Data Status"] != "Complete" for x in ranking), "output": str(out),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
