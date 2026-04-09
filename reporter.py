"""报告渲染器：负责生成 raw 字段发现报告和聚合结论文档。

职责：
- write_raw_report(): 写入或追加 reports/{source}-raw.md 的接口 Section
- write_aggregate_report(): 生成 reports/all-sources-aggregate.md 聚合结论文档

不处理凭证，不调用 source 模块，不包含调度逻辑（调度由 validate.py 负责）。

多接口数据源（tiktok、triplewhale）通过 append=True 参数在同一文件内追加 Section，
第一个接口传 append=False（覆盖写入，含报告头），后续接口传 append=True（追加新 Section）。
"""

from datetime import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# --- 路径常量 ---
REPORTS_DIR = Path("reports")
REQUIREMENTS_PATH = Path("config") / "field_requirements.yaml"


# ---------------------------------------------------------------------------
# 私有辅助函数
# ---------------------------------------------------------------------------

def _ensure_reports_dir() -> None:
    """确保 reports/ 目录存在，不存在则自动创建。"""
    REPORTS_DIR.mkdir(exist_ok=True)


def _load_field_requirements() -> dict:
    """加载字段需求配置，返回完整 dict。文件不存在时返回空 dict。"""
    if not REQUIREMENTS_PATH.exists():
        return {}
    with open(REQUIREMENTS_PATH, encoding="utf-8") as f:
        try:
            return yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            logger.warning(f"[reporter] 解析 field_requirements.yaml 失败：{exc}")
            return {}



def _escape_cell(value: object) -> str:
    """将单元格值转换为安全的 Markdown 表格字符串：None 转为空串，转义竖线。"""
    if value is None:
        return ""
    return str(value).replace("\n", " ").replace("\r", "").replace("|", "\\|")


def _has_source_label(fields: List[Dict]) -> bool:
    """检查是否有任何字段包含 source_label 信息。"""
    return any(field.get("source_label") for field in fields)


def _render_field_table_header(has_source: bool) -> List[str]:
    """渲染字段表格表头。"""
    if has_source:
        return [
            "| 字段名 | 类型 | 示例值 | 可空 | 来源 |",
            "|--------|------|--------|------|------|",
        ]
    return [
        "| 字段名 | 类型 | 示例值 | 可空 |",
        "|--------|------|--------|------|",
    ]


def _render_field_table(fields: List[Dict]) -> List[str]:
    """渲染字段表格行（不含表头）。"""
    has_source = _has_source_label(fields)
    lines: List[str] = []
    for field in fields:
        field_name = _escape_cell(field.get("field_name", ""))
        data_type = _escape_cell(field.get("data_type", ""))
        sample_value = _escape_cell(field.get("sample_value"))
        nullable = "是" if field.get("nullable") else "否"
        if has_source:
            source_label = _escape_cell(field.get("source_label", ""))
            lines.append(f"| {field_name} | {data_type} | {sample_value} | {nullable} | {source_label} |")
        else:
            lines.append(f"| {field_name} | {data_type} | {sample_value} | {nullable} |")
    return lines


def _render_raw_report(
    source_name: str,
    fields: List[Dict],
    table_name: Optional[str],
    sample_count: int,
) -> str:
    """渲染完整 raw 报告 Markdown 内容。

    用于第一次写入（覆盖模式）。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    table_display = table_name if table_name else "N/A"

    # --- 报告头部 ---
    lines: List[str] = [
        f"# {source_name} 字段验证报告（Raw）",
        "",
        f"**生成时间：** {now}",
        "",
    ]

    # --- 接口 Section ---
    lines += [
        f"## 接口：{table_display}",
        "",
        f"**样本记录数：** {sample_count}",
        "",
    ]
    lines += _render_field_table_header(_has_source_label(fields))
    lines += _render_field_table(fields)

    lines.append("")  # 文件末尾空行
    return "\n".join(lines)


def _render_raw_section(
    fields: List[Dict],
    table_name: str,
    sample_count: int,
) -> str:
    """渲染单个接口的追加 Section Markdown 内容（不含报告头和需求字段区块）。

    用于多接口数据源追加写入（append 模式）。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: List[str] = [
        "",
        "---",
        "",
        f"## 接口：{table_name}",
        "",
        f"**生成时间：** {now}",
        "",
        f"**样本记录数：** {sample_count}",
        "",
    ]
    lines += _render_field_table_header(_has_source_label(fields))
    lines += _render_field_table(fields)
    lines.append("")
    return "\n".join(lines)



# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def write_raw_report(
    source_name: str,
    fields: List[Dict],
    table_name: Optional[str],
    sample_count: int,
    append: bool = False,
) -> None:
    """写入 reports/{source_name}-raw.md。

    Args:
        source_name: 数据源名称，与 sources/ 目录下模块名对应（不含 .py）。
        fields: FieldInfo 列表，每项含 field_name / data_type / sample_value / nullable。
        table_name: 数据表名（接口名），非多表数据源传 None。
        sample_count: 本次抓取的样本记录数。
        append: False（默认）= 覆盖写入完整报告；
                True = 追加新接口 Section（不含头部，用于多接口数据源的后续调用）。
    """
    _ensure_reports_dir()
    path = REPORTS_DIR / f"{source_name}-raw.md"
    if append:
        effective_table = table_name or "N/A"
        section = _render_raw_section(fields, effective_table, sample_count)
        with open(path, "a", encoding="utf-8") as f:
            f.write(section)
        logger.info(f"[reporter] {source_name}/{effective_table} section 已追加到 {path}")
    else:
        content = _render_raw_report(source_name, fields, table_name, sample_count)
        path.write_text(content, encoding="utf-8")
        logger.info(f"[reporter] {source_name} raw 报告已写入 {path}")


def write_triplewhale_data_profile(profiles: List[Dict]) -> None:
    """将 TripleWhale 数据概况区块追加写入 reports/triplewhale-raw.md。

    在 write_raw_report 所有表 Section 之后调用，追加"数据概况"Markdown 表格。
    若文件不存在则创建。

    Args:
        profiles: fetch_data_profile() 返回的字典列表，每项含：
            table_name, date_column, earliest_date, total_rows,
            rate_limit_rpm, max_rows_per_request, estimated_pull_minutes
    """
    _ensure_reports_dir()
    path = REPORTS_DIR / "triplewhale-raw.md"

    lines: List[str] = [
        "",
        "---",
        "",
        "## 数据概况（TripleWhale 专属）",
        "",
        "| 表名 | 日期列 | 最早数据日期 | 总行数 | Rate Limit (RPM) | 每次最大行数 | 全量拉取预估时长 |",
        "|------|--------|-------------|--------|-----------------|------------|----------------|",
    ]

    for profile in profiles:
        table_name = _escape_cell(profile.get("table_name", ""))
        date_column = _escape_cell(profile.get("date_column")) or "-"
        earliest_date = _escape_cell(profile.get("earliest_date")) or "-"
        total_rows = _escape_cell(profile.get("total_rows", 0))
        rate_limit = _escape_cell(profile.get("rate_limit_rpm", ""))
        max_rows = _escape_cell(profile.get("max_rows_per_request", ""))
        est_minutes = profile.get("estimated_pull_minutes")
        est_str = f"{est_minutes:.2f} min" if est_minutes is not None else "-"
        lines.append(
            f"| {table_name} | {date_column} | {earliest_date} | "
            f"{total_rows} | {rate_limit} | {max_rows} | {est_str} |"
        )

    lines.append("")
    content = "\n".join(lines)
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"[reporter] triplewhale 数据概况已追加到 {path}")


def write_aggregate_report(source_results: Dict[str, Dict]) -> None:
    """生成 reports/all-sources-aggregate.md 聚合结论文档。

    文档结构：
    - Part 1：数据源采集结论汇总（每个数据源的运行状态）
    - Part 2：各数据源实际字段清单（供 AI 分析引用）
    - Part 3：11 张报表字段映射模板（待 AI 填充）
    - Part 4：AI 分析提示语

    每次 --all 运行覆盖更新。

    Args:
        source_results: 各数据源运行结果，格式：
            {
                "triplewhale": {
                    "status": "已生成",
                    "error": None,
                    "fields": {"pixel_orders_table": [...], "pixel_joined_tvf": [...]},
                },
                "social_media": {
                    "status": "未实现",
                    "error": "NotImplementedError: ...",
                    "fields": {},
                },
            }
            fields 中每个列表项为 FieldInfo dict（field_name / data_type / sample_value / nullable）。
    """
    _ensure_reports_dir()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: List[str] = [
        "# 数据源聚合结论文档",
        "",
        f"**生成时间：** {now}",
        "",
    ]

    # === Part 1：数据源采集结论汇总 ===
    lines += _render_aggregate_part1(source_results)

    # === Part 2：各数据源实际字段清单 ===
    lines += _render_aggregate_part2(source_results)

    # === Part 3：11 张报表字段映射模板 ===
    lines += _render_aggregate_part3()

    # === Part 4：AI 分析提示语 ===
    lines += _render_aggregate_prompt()

    path = REPORTS_DIR / "all-sources-aggregate.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"[reporter] 聚合结论文档已写入 {path}")


# ---------------------------------------------------------------------------
# 聚合文档 — 私有渲染函数
# ---------------------------------------------------------------------------

def _render_aggregate_part1(source_results: Dict[str, Dict]) -> List[str]:
    """Part 1：数据源采集结论汇总表。"""
    lines: List[str] = [
        "---",
        "",
        "## Part 1：数据源采集结论汇总",
        "",
        "| 数据来源 | 接口/表 | 采集状态 | 字段数 | 说明 |",
        "|---------|--------|---------|-------|------|",
    ]
    for source_name, result in source_results.items():
        status = _escape_cell(result.get("status", "未知"))
        error = _escape_cell(result.get("error")) or ""
        fields_dict = result.get("fields", {})
        if fields_dict:
            for table_name, field_list in fields_dict.items():
                table_display = _escape_cell(table_name) if table_name else "—"
                count = len(field_list)
                lines.append(f"| {source_name} | {table_display} | {status} | {count} | {error} |")
        else:
            lines.append(f"| {source_name} | — | {status} | 0 | {error} |")
    lines.append("")
    return lines


def _render_aggregate_part2(source_results: Dict[str, Dict]) -> List[str]:
    """Part 2：各数据源实际字段清单（供 AI 分析引用的真实字段数据）。"""
    lines: List[str] = [
        "---",
        "",
        "## Part 2：各数据源实际字段清单",
        "",
        "> 以下为各数据源实际返回的字段列表，AI 分析时必须引用这些真实字段，不可虚构。",
        "",
    ]
    for source_name, result in source_results.items():
        fields_dict = result.get("fields", {})
        if not fields_dict:
            lines += [f"### {source_name}", "", f"采集状态：{result.get('status', '未知')}（无字段数据）", ""]
            continue
        for table_name, field_list in fields_dict.items():
            table_display = table_name if table_name else "默认"
            lines += [
                f"### {source_name} / {table_display}",
                "",
                "| 字段名 | 类型 | 示例值 |",
                "|--------|------|--------|",
            ]
            for field in field_list:
                fname = _escape_cell(field.get("field_name", ""))
                dtype = _escape_cell(field.get("data_type", ""))
                sample = _escape_cell(field.get("sample_value"))
                lines.append(f"| {fname} | {dtype} | {sample} |")
            lines.append("")
    return lines


def _render_aggregate_part3() -> List[str]:
    """Part 3：11 张报表字段映射模板（待 AI 填充）。"""
    req = _load_field_requirements()
    reports = req.get("reports", [])
    if not reports:
        return ["## Part 3：报表字段映射分析", "", "（未找到报表定义配置）", ""]

    lines: List[str] = [
        "---",
        "",
        "## Part 3：报表字段映射分析",
        "",
        "> 以下 11 张报表的字段映射待 AI 根据 Part 2 的真实字段数据进行分析填充。",
        "",
    ]
    for i, report in enumerate(reports, 1):
        name = report.get("report_name", f"报表{i}")
        dashboard = report.get("dashboard", "")
        deadline = report.get("deadline", "")
        launch = report.get("launch_date", "")
        notes = report.get("notes", "")
        fields = report.get("fields") or []

        lines += [
            f"### 报表 {i}：{name}",
            "",
        ]
        if dashboard:
            lines.append(f"- **所属报表：** {dashboard}")
        if deadline:
            lines.append(f"- **需求时间：** {deadline}")
        if launch:
            lines.append(f"- **上线时间：** {launch}")
        if notes:
            lines.append(f"- **备注：** {notes}")
        lines += [
            "",
            "| 报表字段 | 来源数据源 | 来源字段（真实） | 映射状态 | 备注 |",
            "|---------|----------|---------------|---------|------|",
        ]
        for field_name in fields:
            lines.append(f"| {_escape_cell(field_name)} | | | 待分析 | |")
        lines.append("")
    return lines


def _render_aggregate_prompt() -> List[str]:
    """Part 4：AI 分析提示语。"""
    return [
        "---",
        "",
        "## Part 4：AI 分析提示语",
        "",
        "请根据以下要求对本文档进行分析：",
        "",
        "### 任务",
        "",
        "对照 Part 2 中各数据源的**真实字段清单**，逐一分析 Part 3 中 11 张报表的每个字段，",
        "判断该字段是否可以从现有数据源中获取，并填写字段映射关系。",
        "",
        "### 规则",
        "",
        "1. **来源字段必须真实**：只能引用 Part 2 中实际存在的字段名，不可虚构或假设字段存在",
        "2. **映射状态**使用以下标记：",
        "   - `可映射`：数据源中存在直接对应的字段",
        "   - `需转换`：数据源中有相关字段但需要格式转换或计算（在备注中说明转换逻辑）",
        "   - `缺失`：当前所有数据源中均无法获取该字段（在备注中说明建议的补充方案）",
        "   - `待人工确认`：存在疑似对应字段但无法确定（在备注中说明原因）",
        "3. **一个报表字段可能来自多个数据源**：如果多个数据源都能提供，列出主要来源并在备注中注明备选来源",
        '4. **注意数据源的采集状态**：Part 1 中标注为"失败"/"未实现"/"跳过"的数据源暂无字段数据，',
        '   若报表字段预期来自这些数据源，映射状态填"待人工确认"并在备注中说明原因',
        "",
        "### 输出格式",
        "",
        "直接在 Part 3 的表格中填写 `来源数据源`、`来源字段（真实）`、`映射状态`、`备注` 四列，",
        "保持 Markdown 表格格式不变。",
        "",
    ]
