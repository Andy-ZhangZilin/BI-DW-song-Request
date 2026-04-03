"""
tests/test_field_requirements.py

验证 config/field_requirements.yaml 可正确加载且符合预期数据结构。
测试覆盖 Story 1.3 的全部验收标准（AC1~AC4）。

运行方式（在项目根目录执行）：
    pytest tests/test_field_requirements.py -v
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
    assert len(data) > 0, "配置文件不应为空"


def test_required_report_groups_exist():
    """profit_table 和 marketing_table 两个分组必须存在（AC1）。"""
    data = _load()
    assert "profit_table" in data, "缺少 profit_table 分组"
    assert "marketing_table" in data, "缺少 marketing_table 分组"


def test_each_entry_has_required_fields():
    """每条记录必须含 display_name 和 source；table 为可选字段（AC1）。"""
    data = _load()
    for group_name, entries in data.items():
        assert entries is not None, f"{group_name} 的值不应为 None（空分组需写 []）"
        assert isinstance(entries, list), f"{group_name} 的值应为列表"
        for entry in entries:
            assert "display_name" in entry, (
                f"{group_name} 中存在缺少 display_name 的条目：{entry}"
            )
            assert "source" in entry, (
                f"{group_name} 中存在缺少 source 的条目：{entry}"
            )
            # table 是可选字段：存在时可以为 str 或 None


# ---------------------------------------------------------------------------
# AC4 — 初始内容完整
# ---------------------------------------------------------------------------

def test_profit_table_has_minimum_entries():
    """profit_table 至少 3 条条目（AC4）。"""
    data = _load()
    assert len(data["profit_table"]) >= 3, (
        f"profit_table 应至少 3 条，实际 {len(data['profit_table'])} 条"
    )


def test_profit_table_covers_multiple_sources():
    """profit_table 应覆盖 triplewhale 和 tiktok 两个数据源（AC4）。"""
    data = _load()
    sources = {entry["source"] for entry in data["profit_table"]}
    assert "triplewhale" in sources, "profit_table 应包含 triplewhale 数据源"
    assert "tiktok" in sources, "profit_table 应包含 tiktok 数据源"


# ---------------------------------------------------------------------------
# AC3 — 非 SQL 数据源 table 字段可选
# ---------------------------------------------------------------------------

def test_non_sql_source_table_optional():
    """非 SQL 数据源（youtube）的 table 字段为 None 或缺省，加载不报错（AC3）。"""
    data = _load()
    youtube_entries = [
        entry
        for entries in data.values()
        for entry in entries
        if entry.get("source") == "youtube"
    ]
    assert len(youtube_entries) > 0, "配置中应包含至少一条 youtube 数据源条目"
    for entry in youtube_entries:
        table_value = entry.get("table")
        assert table_value is None or isinstance(table_value, str), (
            f"youtube 条目的 table 应为 None 或 str，实际为：{type(table_value)}"
        )


def test_null_table_entries_load_without_error():
    """含 table: null 的条目使用 yaml.safe_load 加载后不抛异常（AC3）。"""
    data = _load()
    # 收集所有 table 为 None 的条目
    null_table_entries = [
        entry
        for entries in data.values()
        for entry in entries
        if entry.get("table") is None
    ]
    # 只要加载成功、条目结构完整即可
    for entry in null_table_entries:
        assert "display_name" in entry
        assert "source" in entry


# ---------------------------------------------------------------------------
# AC2 — 热更新验证（结构层面）
# ---------------------------------------------------------------------------

def test_yaml_structure_supports_hot_update():
    """
    YAML 顶层为字典、值为列表结构，天然支持热更新：
    新增条目只需编辑 YAML，无需修改 Python 代码（AC2）。
    """
    data = _load()
    for group_name, entries in data.items():
        assert entries is not None, f"{group_name} 的值不应为 None（空分组需写 []）"
        assert isinstance(entries, list), (
            f"{group_name} 的值应为列表，以支持任意新增条目"
        )
        for entry in entries:
            assert isinstance(entry, dict), (
                f"{group_name} 中的条目应为字典，实际为：{type(entry)}"
            )
