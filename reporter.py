"""报告渲染器：负责生成 raw 字段发现报告和 validation 人工标注模板。

职责：
- write_raw_report(): 每次运行完全覆盖 reports/{source}-raw.md
- init_validation_report(): 仅首次创建 reports/{source}-validation.md，后续不覆盖

不处理凭证，不调用 source 模块，不包含调度逻辑（调度由 validate.py 负责）。
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
    return str(value).replace("|", "\\|")


def _render_raw_report(
    source_name: str,
    fields: List[Dict],
    table_name: Optional[str],
    sample_count: int,
) -> str:
    """渲染 raw 报告 Markdown 内容。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    table_display = table_name if table_name else "N/A"

    # --- 报告头部 ---
    lines: List[str] = [
        f"# {source_name} 字段验证报告（Raw）",
        "",
        f"**生成时间：** {now}",
        f"**数据表：** {table_display}",
        f"**样本记录数：** {sample_count}",
        "",
        "## 实际返回字段",
        "",
        "| 字段名 | 类型 | 示例值 | 可空 |",
        "|--------|------|--------|------|",
    ]

    # --- 字段表格行 ---
    for field in fields:
        field_name = _escape_cell(field.get("field_name", ""))
        data_type = _escape_cell(field.get("data_type", ""))
        sample_value = _escape_cell(field.get("sample_value"))
        nullable = "是" if field.get("nullable") else "否"
        lines.append(f"| {field_name} | {data_type} | {sample_value} | {nullable} |")

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
) -> None:
    """生成（或覆盖）reports/{source_name}-raw.md。

    Args:
        source_name: 数据源名称，与 sources/ 目录下模块名对应（不含 .py）。
        fields: FieldInfo 列表，每项含 field_name / data_type / sample_value / nullable。
        table_name: 数据表名（SQL 数据源），非 SQL 数据源传 None。
        sample_count: 本次抓取的样本记录数。
    """
    _ensure_reports_dir()
    content = _render_raw_report(source_name, fields, table_name, sample_count)
    path = REPORTS_DIR / f"{source_name}-raw.md"
    path.write_text(content, encoding="utf-8")
    logger.info(f"[reporter] {source_name} raw 报告已写入 {path}")


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
