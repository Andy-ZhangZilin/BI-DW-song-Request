"""
tests/test_field_requirements.py

验证 config/field_requirements.yaml 可正确加载且符合预期数据结构。
适配新结构：顶层 reports 列表，每项含 report_name / fields 等。
"""
import yaml
from pathlib import Path

YAML_PATH = Path(__file__).parent.parent / "config/field_requirements.yaml"


def _load() -> dict:
    """辅助函数：读取并解析 YAML 文件。"""
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    assert data is not None, "field_requirements.yaml 不应为空文件"
    return data


# ---------------------------------------------------------------------------
# AC1 — YAML 结构合法
# ---------------------------------------------------------------------------

def test_yaml_loads_successfully():
    """YAML 文件可正常加载，返回非空字典。"""
    data = _load()
    assert isinstance(data, dict), "yaml.safe_load 应返回 dict"
    assert "reports" in data, "顶层应包含 reports 键"


def test_reports_is_list():
    """reports 值应为列表。"""
    data = _load()
    assert isinstance(data["reports"], list)
    assert len(data["reports"]) > 0


def test_has_11_reports():
    """应定义 11 张报表。"""
    data = _load()
    assert len(data["reports"]) == 11, f"应有 11 张报表，实际 {len(data['reports'])} 张"


def test_each_report_has_required_keys():
    """每张报表必须含 report_name 和 fields。"""
    data = _load()
    for i, report in enumerate(data["reports"]):
        assert "report_name" in report, f"报表 {i} 缺少 report_name"
        assert "fields" in report, f"报表 {i} ({report.get('report_name', '?')}) 缺少 fields"
        assert isinstance(report["fields"], list), \
            f"报表 {report['report_name']} 的 fields 应为列表"
        assert len(report["fields"]) > 0, \
            f"报表 {report['report_name']} 的 fields 不应为空"


# ---------------------------------------------------------------------------
# 具体报表验证
# ---------------------------------------------------------------------------

def test_profit_table_exists():
    """利润表应存在且字段数 >= 9。"""
    data = _load()
    profit = [r for r in data["reports"] if r["report_name"] == "利润表"]
    assert len(profit) == 1, "应有且仅有一张利润表"
    assert len(profit[0]["fields"]) >= 9


def test_marketing_table_exists():
    """营销表现表应存在且字段数 >= 11。"""
    data = _load()
    marketing = [r for r in data["reports"] if r["report_name"] == "营销表现表"]
    assert len(marketing) == 1
    assert len(marketing[0]["fields"]) >= 11


def test_report_names_unique():
    """报表名称应唯一。"""
    data = _load()
    names = [r["report_name"] for r in data["reports"]]
    assert len(names) == len(set(names)), f"存在重复报表名称：{names}"


def test_fields_are_strings():
    """所有字段名应为字符串。"""
    data = _load()
    for report in data["reports"]:
        for field in report["fields"]:
            assert isinstance(field, str), \
                f"报表 {report['report_name']} 的字段 {field} 应为字符串"


# ---------------------------------------------------------------------------
# AC2 — 热更新验证
# ---------------------------------------------------------------------------

def test_yaml_structure_supports_hot_update():
    """YAML 结构支持热更新：新增报表只需编辑 YAML，无需修改 Python 代码。"""
    data = _load()
    assert isinstance(data["reports"], list), "reports 应为列表结构以支持新增"
    for report in data["reports"]:
        assert isinstance(report, dict)
        assert isinstance(report.get("fields", []), list)
