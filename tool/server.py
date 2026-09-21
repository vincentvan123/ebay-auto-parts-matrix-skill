#!/usr/bin/env python3
"""Local web UI for the listing and PLP matrix pipeline."""

from __future__ import annotations

import csv
import json
import mimetypes
import os
import re
import subprocess
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
WEB = Path(__file__).resolve().parent / "web"
IMPORT_TEMPLATE = ROOT / "sku" / "_template" / "input.csv"
PROCESS_LOCK = threading.Lock()
SKU_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
DOWNLOAD_FILES = {
    "vehicle_ranking.csv",
    "listing_matrix.csv",
    "plp_matrix.csv",
    "negative_keywords.csv",
    "workbook_data.json",
}
WORKBOOK_SUFFIX = "Listing与PLP矩阵.xlsx"
DOWNLOAD_LABELS = {
    "vehicle_ranking.csv": "车型市场排名 CSV",
    "listing_matrix.csv": "Listing 矩阵 CSV",
    "plp_matrix.csv": "PLP 广告矩阵 CSV",
    "negative_keywords.csv": "否定关键词 CSV",
    "workbook_data.json": "结果数据 JSON",
}
PUBLIC_HIDDEN_FIELDS = {"source_key", "source", "source_url", "Source", "Source URL"}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def attachment_header(filename: str) -> str:
    ascii_name = filename.encode("ascii", "ignore").decode("ascii").replace('"', "")
    if not ascii_name:
        ascii_name = f"download{Path(filename).suffix}"
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


def fetch_keyword_suggestions(keyword: str) -> list[str]:
    keyword = keyword.strip()
    if not keyword or len(keyword) > 80:
        raise ValueError("请先输入不超过 80 个字符的产品核心关键词")
    result = subprocess.run([
        "curl", "--fail", "--location", "--silent", "--show-error", "--max-time", "20",
        "--get", "--data-urlencode", f"kwd={keyword}", "--data", "sId=0", "--data", "fmt=json",
        "https://autosug.ebay.com/autosug",
    ], check=True, capture_output=True, text=True, timeout=25)
    match = re.search(r"_do\((\{.*\})\)\s*$", result.stdout, re.S)
    if not match:
        raise RuntimeError("暂时无法读取搜索词建议")
    suggestions = json.loads(match.group(1)).get("res", {}).get("sug", [])
    unique = []
    for suggestion in suggestions:
        clean = re.sub(r"\s+", " ", str(suggestion)).strip()
        if clean and clean.casefold() not in {item.casefold() for item in unique}:
            unique.append(clean)
    return unique[:10]


def validate_payload(payload: dict) -> tuple[str, str, list[dict], bool]:
    sku = str(payload.get("sku", "")).strip()
    keyword = str(payload.get("core_keyword", "")).strip()
    refresh = bool(payload.get("refresh_sales", False))
    fitments = payload.get("fitments")
    expansions = payload.get("keyword_expansions", [])
    if not SKU_PATTERN.fullmatch(sku):
        raise ValueError("SKU 只能包含字母、数字、点、下划线和连字符，最长 64 位")
    if not keyword or len(keyword) > 80:
        raise ValueError("产品核心关键词不能为空，且不能超过 80 个字符")
    if not isinstance(fitments, list) or not 1 <= len(fitments) <= 500:
        raise ValueError("至少需要 1 条适配数据，单次最多 500 条")
    if not isinstance(expansions, list) or len(expansions) > 10:
        raise ValueError("标题扩展词格式错误，最多选择 10 个")
    cleaned_expansions = []
    for expansion in expansions:
        clean = re.sub(r"\s+", " ", str(expansion)).strip()
        if not clean or len(clean) > 80 or ";" in clean:
            raise ValueError("每个标题扩展词必须为 1-80 个字符，且不能包含分号")
        if clean.casefold() not in {item.casefold() for item in cleaned_expansions}:
            cleaned_expansions.append(clean)
    expansion_text = ";".join(cleaned_expansions)

    normalized = []
    for index, row in enumerate(fitments, 1):
        if not isinstance(row, dict):
            raise ValueError(f"第 {index} 条适配数据格式错误")
        make = str(row.get("make", "")).strip()
        model = str(row.get("model", "")).strip()
        explicit = str(row.get("years", "")).strip().replace(",", ";")
        start = str(row.get("start_year", "")).strip()
        end = str(row.get("end_year", "")).strip()
        if not make or not model:
            raise ValueError(f"第 {index} 条适配必须填写品牌和车型")
        if len(make) > 50 or len(model) > 80:
            raise ValueError(f"第 {index} 条品牌或车型名称过长")
        if explicit:
            parts = [part.strip() for part in explicit.split(";") if part.strip()]
            if not parts or any(not part.isdigit() or not 1900 <= int(part) <= 2100 for part in parts):
                raise ValueError(f"第 {index} 条指定年份格式错误，请使用 2012;2014;2015")
            explicit = ";".join(str(year) for year in sorted({int(part) for part in parts}))
            start = end = ""
        else:
            if not start.isdigit() or not end.isdigit():
                raise ValueError(f"第 {index} 条需要填写起止年份，或填写指定年份")
            start_year, end_year = int(start), int(end)
            if not 1900 <= start_year <= end_year <= 2100:
                raise ValueError(f"第 {index} 条年份范围无效")
        normalized.append({
            "sku": sku,
            "core_keyword": keyword,
            "make": make,
            "model": model,
            "start_year": start,
            "end_year": end,
            "years": explicit,
            "keyword_expansions": expansion_text,
        })
    return sku, keyword, normalized, refresh


def write_input(sku: str, rows: list[dict]) -> Path:
    sku_dir = ROOT / "sku" / sku
    sku_dir.mkdir(parents=True, exist_ok=True)
    output = sku_dir / "input.csv"
    temporary = sku_dir / "input.csv.tmp"
    fields = ["sku", "core_keyword", "keyword_expansions", "make", "model", "start_year", "end_year", "years"]
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, output)
    return output


def load_input(sku: str) -> dict:
    if not SKU_PATTERN.fullmatch(sku):
        raise ValueError("SKU 格式无效")
    path = ROOT / "sku" / sku / "input.csv"
    if not path.exists():
        raise FileNotFoundError("未找到该 SKU")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("SKU 输入为空")
    return {
        "sku": sku,
        "core_keyword": rows[0]["core_keyword"],
        "keyword_expansions": [item for item in rows[0].get("keyword_expansions", "").split(";") if item],
        "fitments": [{key: row.get(key, "") for key in ["make", "model", "start_year", "end_year", "years"]} for row in rows],
    }


def result_payload(sku: str) -> dict:
    if not SKU_PATTERN.fullmatch(sku):
        raise ValueError("SKU 格式无效")
    output_dir = ROOT / "outputs" / sku
    data_path = output_dir / "workbook_data.json"
    if not data_path.exists():
        raise FileNotFoundError("该 SKU 尚未生成结果")
    data = read_json(data_path)
    ranking = [
        {key: value for key, value in row.items() if key not in PUBLIC_HIDDEN_FIELDS}
        for row in data.get("vehicle_ranking", [])
    ]
    listings = data.get("listing_matrix", [])
    workbook_name = f"{sku}-{WORKBOOK_SUFFIX}"
    files = [name for name in sorted(DOWNLOAD_FILES | {workbook_name}) if (output_dir / name).exists()]
    return {
        "sku": sku,
        "summary": {
            "ranking_entities": len(ranking),
            "core_listings": sum(row.get("Listing Type") == "Core" for row in listings),
            "discovery_listings": sum(row.get("Listing Type") == "Discovery" for row in listings),
            "mixed_listings": sum(row.get("Listing Type") == "Mixed" for row in listings),
            "plp_keywords": len(data.get("plp_matrix", [])),
            "data_gaps": sum(row.get("Data Status") != "Complete" for row in ranking),
        },
        "vehicle_ranking": ranking,
        "listing_matrix": listings,
        "files": [{
            "name": name,
            "label": "下载 Excel" if name == workbook_name else DOWNLOAD_LABELS.get(name, name),
            "url": f"/download/{sku}/{name}",
        } for name in files],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "ListingMatrixTool/1.0"

    def log_message(self, format_string, *args):
        print(f"[{self.log_date_time_string()}] {format_string % args}")

    def send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path, attachment=False, download_name: str | None = None):
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if attachment:
            self.send_header("Content-Disposition", attachment_header(download_name or path.name))
        else:
            self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/download/input-template.csv":
            self.send_file(IMPORT_TEMPLATE, attachment=True, download_name="eBay汽配导入模板.csv")
            return
        if parsed.path == "/api/keyword-suggestions":
            try:
                keyword = parse_qs(parsed.query).get("keyword", [""])[0]
                self.send_json({"keyword": keyword, "suggestions": fetch_keyword_suggestions(keyword)})
            except ValueError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except Exception:
                self.send_json({"error": "搜索词建议暂时不可用，请稍后重试"}, HTTPStatus.BAD_GATEWAY)
            return
        if parsed.path == "/api/input":
            try:
                sku = parse_qs(parsed.query).get("sku", [""])[0]
                self.send_json(load_input(sku))
            except FileNotFoundError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/results":
            try:
                sku = parse_qs(parsed.query).get("sku", [""])[0]
                self.send_json(result_payload(sku))
            except FileNotFoundError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if parsed.path.startswith("/download/"):
            parts = [unquote(part) for part in parsed.path.split("/") if part]
            if len(parts) != 3 or not SKU_PATTERN.fullmatch(parts[1]):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            sku, filename = parts[1], parts[2]
            allowed = DOWNLOAD_FILES | {f"{sku}-{WORKBOOK_SUFFIX}"}
            if filename not in allowed or Path(filename).name != filename:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_file(ROOT / "outputs" / sku / filename, attachment=True)
            return

        relative = "index.html" if parsed.path in {"", "/"} else parsed.path.lstrip("/")
        target = (WEB / relative).resolve()
        if WEB.resolve() not in target.parents and target != WEB.resolve():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_file(target)

    def do_POST(self):
        if urlparse(self.path).path != "/api/process":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 2_000_000:
                raise ValueError("请求内容为空或过大")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            sku, _, rows, refresh = validate_payload(payload)
            if not PROCESS_LOCK.acquire(blocking=False):
                self.send_json({"error": "已有任务正在处理，请稍后再试"}, HTTPStatus.CONFLICT)
                return
            try:
                write_input(sku, rows)
                command = [str(ROOT / "scripts" / "process_sku.sh"), sku]
                if refresh:
                    command.append("--refresh-sales")
                result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=420)
                if result.returncode != 0:
                    detail = (result.stderr or result.stdout).strip().splitlines()
                    raise RuntimeError(detail[-1] if detail else "处理失败")
                response = result_payload(sku)
                response["message"] = "处理完成"
                self.send_json(response)
            finally:
                PROCESS_LOCK.release()
        except json.JSONDecodeError:
            self.send_json({"error": "请求不是有效 JSON"}, HTTPStatus.BAD_REQUEST)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except subprocess.TimeoutExpired:
            self.send_json({"error": "处理超时，请检查网络或销量来源"}, HTTPStatus.GATEWAY_TIMEOUT)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Listing Matrix Tool: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
