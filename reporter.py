"""报告渲染器：负责生成 raw 字段发现报告和 validation 人工标注模板。

职责：
- write_raw_report(): 写入或追加 reports/{source}-raw.md 的接口 Section
- init_validation_report(): 仅首次创建 reports/{source}-validation.md，后续不覆盖

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


def _get_source_requirements(source_name: str) -> List[Dict]:
    """从 field_requirements.yaml 中提取指定数据源的所有需求字段。

    返回：[{"display_name": str, "report": str, "table": str | None}]
    """
    req = _load_field_requirements()
    source_fields: List[Dict] = []
    for report_name, items in req.items():
        if isinstance(items, list):
            for item in items:
                if item.get("source") == source_name:
                    display_name = item.get("display_name", "")
                    if not display_name:
                        continue
                    source_fields.append({
                        "display_name": display_name,
                        "report": report_name,
                        "table": item.get("table"),
                    })
    return source_fields


def _escape_cell(value: object) -> str:
    """将单元格值转换为安全的 Markdown 表格字符串：None 转为空串，转义竖线。"""
    if value is None:
        return ""
    return str(value).replace("\n", " ").replace("\r", "").replace("|", "\\|")


def _render_field_table(fields: List[Dict]) -> List[str]:
    """渲染字段表格行（不含表头）。"""
    lines: List[str] = []
    for field in fields:
        field_name = _escape_cell(field.get("field_name", ""))
        data_type = _escape_cell(field.get("data_type", ""))
        sample_value = _escape_cell(field.get("sample_value"))
        nullable = "是" if field.get("nullable") else "否"
        lines.append(f"| {field_name} | {data_type} | {sample_value} | {nullable} |")
    return lines


def _render_raw_report(
    source_name: str,
    fields: List[Dict],
    table_name: Optional[str],
    sample_count: int,
) -> str:
    """渲染完整 raw 报告 Markdown 内容（含报告头和需求字段区块）。

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
        "| 字段名 | 类型 | 示例值 | 可空 |",
        "|--------|------|--------|------|",
    ]
    lines += _render_field_table(fields)

    # --- 需求字段区块 ---
    lines += [
        "",
        "## 需求字段（待人工对照）",
        "",
        "| 需求字段（中文） | 报表 | 对照结果 |",
        "|----------------|------|---------|",
    ]
    source_fields = _get_source_requirements(source_name)
    if source_fields:
        for sf in source_fields:
            lines.append(f"| {sf['display_name']} | {sf['report']} | ⬜ 待确认 |")
    else:
        lines.append("| （暂无配置的需求字段） | — | — |")

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
        "| 字段名 | 类型 | 示例值 | 可空 |",
        "|--------|------|--------|------|",
    ]
    lines += _render_field_table(fields)
    lines.append("")
    return "\n".join(lines)


def _render_validation_template(source_name: str) -> str:
    """渲染 validation 报告 Markdown 模板内容。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: List[str] = [
        f"# {source_name} 字段对标结论（Validation）",
        "",
        "> 本文件由工具首次生成，后续**人工维护**，工具运行不覆盖。",
        f"> 创建时间：{now}",
        "",
        "## 字段对标结论",
        "",
        "| 需求字段（中文） | 报表 | 状态 | 说明 |",
        "|----------------|------|------|------|",
    ]

    source_fields = _get_source_requirements(source_name)
    if source_fields:
        for sf in source_fields:
            lines.append(f"| {sf['display_name']} | {sf['report']} | ⬜ 待确认 | |")
    else:
        lines.append("| （暂无配置的需求字段） | — | ⬜ 待确认 | |")

    lines += [
        "",
        "---",
        "",
        "### 标注说明",
        "",
        "- ✅ 直接可用：API 实际返回该字段，可直接使用",
        "- ⚠️ 需转换：有对应字段但需格式转换，在「说明」列填写转换逻辑",
        "- ❌ 缺失：API 无此字段，在「说明」列填写替代方案或结论",
        "- ⬜ 待确认：尚未完成对标判断",
        "",
    ]
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
        append: False（默认）= 覆盖写入完整报告（含头部和需求字段区块）；
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


def init_validation_report(source_name: str) -> None:
    """仅在文件不存在时创建 reports/{source_name}-validation.md。

    若文件已存在（人工已标注），则跳过，不覆盖。

    Args:
        source_name: 数据源名称。
    """
    _ensure_reports_dir()
    path = REPORTS_DIR / f"{source_name}-validation.md"
    if path.exists():
        logger.info(f"[reporter] {source_name} validation 报告已存在，跳过创建")
        return
    content = _render_validation_template(source_name)
    path.write_text(content, encoding="utf-8")
    logger.info(f"[reporter] {source_name} validation 报告模板已创建 {path}")
