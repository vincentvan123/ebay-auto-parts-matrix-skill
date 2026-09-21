# eBay 汽配 Listing 与 PLP 矩阵 Skill

这是一个可安装的 Codex Skill，也可以作为本地网页工具独立运行。它能根据任意 SKU 的适配数据估算有效车型保有量，生成车型市场排名、Core/Discovery Listing、必需的多车型 Mixed 标题，以及 PLP 广告矩阵。本仓库不包含任何真实产品或 SKU 数据。

## 安装为 Codex Skill

让 Codex 从 GitHub 安装：

```text
安装这个 Skill：https://github.com/vincentvan123/ebay-auto-parts-matrix-skill
```

安装后重启 Codex，再调用 `$ebay-auto-parts-matrix`。仓库根目录中的 `SKILL.md` 和 `agents/openai.yaml` 是 Skill 所需的元数据。

需要 Python 3.11 或更高版本。首次使用 Excel 导出功能前安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

## 使用方法

### 本地网页工具

```bash
scripts/start_tool.sh
```

打开 `http://127.0.0.1:8765`，输入 SKU、英文产品核心关键词和适配车型，也可以导入符合格式的 CSV。网页会显示车型排名与 Listing 结果，并提供 Excel、CSV 和 JSON 下载。

### 命令行

```bash
# 根据 sku/<SKU>/input.csv 生成 Markdown、CSV、JSON 和 Excel
scripts/process_sku.sh YOUR_SKU --refresh-sales

# 处理项目目录外的兼容 CSV（数据与 Markdown 阶段）
python3 scripts/run_mvp.py --input /path/to/fitment.csv --refresh-sales
```

结果写入 `outputs/<SKU>/`，Excel 文件名为 `<SKU>-Listing与PLP矩阵.xlsx`。新产品可以从 `sku/_template/input.csv` 开始。

## 项目结构

- `config/`：可配置的判定规则与内部数据源映射
- `data/`：可复用的历史销量内部缓存
- `knowledge/`：业务规则、产品知识和车型标准化知识
- `skills/`：五个可复用的 Skill 子流程
- `sku/`：SKU 输入与生成的 Obsidian 笔记
- `scripts/`：确定性的抓取、计算和 Excel 生成脚本
- `outputs/`：生成结果
- `tool/`：本地中文网页与 API 服务

## 输入规范

输入 CSV 必须包含 `sku`、`core_keyword`、`make`、`model`，并填写连续的 `start_year` 与 `end_year`，或者用分号分隔的 `years`。每次只处理一个 SKU，产品类型和适配车型都没有硬编码。

公共数据的来源名称、网站和内部 source key 不会出现在网页或面向用户的 Excel、CSV、Markdown、JSON 导出中。相关元数据只保留在内部缓存和刷新诊断中。导出标签优先使用中文；JSON 字段名、CSV 文件名以及 SKU、PLP、Listing、Core、Discovery、Mixed、Campaign、Ad Group、Compatibility 等稳定机器字段或行业术语保留英文。

## 市场规模规则

估算有效保有量等于适配年份的美国历史销量乘以对应车龄存活率后求和。默认存活率：0-5 年 95%，6-10 年 85%，11-15 年 65%，16-20 年 40%，21 年以上 20%。

车型实体只有同时满足以下条件才可进入 Core：数据覆盖率至少 80%，估算有效保有量至少 150,000，并达到最大合格市场的 10%。Core 最多六个 Listing。缺失年份不会按零处理。这是运营估算，不是授权的车辆登记量或 VIO 数据。

只要一个 SKU 适配至少两个不同车型，就会额外生成一个 Mixed Listing。标题按市场排名从高到低排列车型，Compatibility 覆盖该 SKU 的全部适配。Core 与 Discovery 仍是互斥的主要分组；补充的 Mixed Listing 不进入 PLP，以避免关键词内部竞争。
