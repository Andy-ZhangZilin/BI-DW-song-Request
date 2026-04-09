"""Awin 数据源单元测试。

覆盖 AC3 & AC7：
- AC3: extract_fields 返回标准 FieldInfo 结构（field_name/data_type/sample_value/nullable）
- AC7: extract_fields 单元测试使用 tests/fixtures/awin_sample.json；
       authenticate 和 fetch_sample 标注 @pytest.mark.integration，不在单元测试中执行
"""
import json
import pytest
from pathlib import Path

import sources.awin as awin

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# TestExtractFields — AC3 & AC7：使用 fixture 数据验证 FieldInfo 结构
# ---------------------------------------------------------------------------

class TestExtractFields:
    """AC3: extract_fields 从 Publisher Performance API 样本数据返回标准 FieldInfo 列表。"""

    @pytest.fixture
    def sample(self):
        """从 tests/fixtures/awin_sample.json 加载模拟 Publisher Performance API 记录。"""
        with open(FIXTURES_DIR / "awin_sample.json", encoding="utf-8") as f:
            return json.load(f)

    def test_returns_list(self, sample):
        """返回值为非空列表。"""
        result = awin.extract_fields(sample)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_each_item_has_four_required_keys(self, sample):
        """每条 FieldInfo 包含 field_name / data_type / sample_value / nullable 四字段（ARCH2）。"""
        result = awin.extract_fields(sample)
        for item in result:
            assert "field_name" in item, f"缺少 field_name：{item}"
            assert "data_type" in item, f"缺少 data_type：{item}"
            assert "sample_value" in item, f"缺少 sample_value：{item}"
            assert "nullable" in item, f"缺少 nullable：{item}"

    def test_field_name_is_string(self, sample):
        """field_name 必须是字符串。"""
        result = awin.extract_fields(sample)
        for item in result:
            assert isinstance(item["field_name"], str)

    def test_data_type_is_string(self, sample):
        """data_type 必须是字符串。"""
        result = awin.extract_fields(sample)
        for item in result:
            assert isinstance(item["data_type"], str)

    def test_nullable_is_bool(self, sample):
        """nullable 必须是布尔值。"""
        result = awin.extract_fields(sample)
        for item in result:
            assert isinstance(item["nullable"], bool), f"nullable 应为 bool：{item}"

    def test_field_names_cover_target_fields(self, sample):
        """返回的字段名覆盖全部 5 个目标字段。"""
        result = awin.extract_fields(sample)
        result_keys = {item["field_name"] for item in result}
        assert result_keys == {"impressions", "clicks", "totalNo", "totalValue", "totalComm"}

    def test_only_5_fields_returned(self, sample):
        """只返回 5 个目标字段，无多余字段。"""
        result = awin.extract_fields(sample)
        assert len(result) == 5

    def test_clicks_nullable_false(self, sample):
        """clicks 在所有记录中均有值，nullable 应为 False。"""
        result = awin.extract_fields(sample)
        clicks_field = next(
            (f for f in result if f["field_name"] == "clicks"), None
        )
        assert clicks_field is not None
        assert clicks_field["nullable"] is False

    def test_integer_type_inferred_for_clicks(self, sample):
        """clicks 为整数类型，应推断为 'integer'。"""
        result = awin.extract_fields(sample)
        clicks_field = next(f for f in result if f["field_name"] == "clicks")
        assert clicks_field["data_type"] == "integer"

    def test_number_type_inferred_for_totalvalue(self, sample):
        """totalValue 为浮点数类型，应推断为 'number'。"""
        result = awin.extract_fields(sample)
        tv_field = next(f for f in result if f["field_name"] == "totalValue")
        assert tv_field["data_type"] == "number"

    def test_integer_type_inferred_for_impressions(self, sample):
        """impressions 为整数类型，应推断为 'integer'。"""
        result = awin.extract_fields(sample)
        field = next(f for f in result if f["field_name"] == "impressions")
        assert field["data_type"] == "integer"

    def test_returns_sorted_fields(self, sample):
        """返回的字段列表按字段名字母顺序排列（便于报告阅读）。"""
        result = awin.extract_fields(sample)
        names = [item["field_name"] for item in result]
        assert names == sorted(names)

    def test_sample_value_is_first_non_null(self, sample):
        """clicks 应为第一条记录的值 76。"""
        result = awin.extract_fields(sample)
        clicks_field = next(f for f in result if f["field_name"] == "clicks")
        assert clicks_field["sample_value"] == 76


# ---------------------------------------------------------------------------
# TestExtractFieldsEdgeCases — 边界情况
# ---------------------------------------------------------------------------

class TestExtractFieldsEdgeCases:
    """边界情况：空列表、全 None 值等。"""

    def test_empty_sample_returns_empty_list(self):
        """AC3（边界）：空输入返回空列表，不报错。"""
        result = awin.extract_fields([])
        assert result == []

    def test_single_record(self):
        """单条记录也能正常提取字段。"""
        sample = [{"clicks": 10, "totalNo": 5}]
        result = awin.extract_fields(sample)
        assert len(result) == 2
        names = {f["field_name"] for f in result}
        assert names == {"clicks", "totalNo"}

    def test_all_none_values_nullable(self):
        """字段在所有记录中均为 None 时，nullable=True，sample_value=None。"""
        sample = [{"field_x": None}, {"field_x": None}]
        result = awin.extract_fields(sample)
        assert result[0]["nullable"] is True
        assert result[0]["sample_value"] is None

    def test_native_int_type_inferred(self):
        """原生 int 值推断为 'integer'。"""
        sample = [{"count": 5, "name": "foo"}]
        result = awin.extract_fields(sample)
        count_field = next(f for f in result if f["field_name"] == "count")
        assert count_field["data_type"] == "integer"

    def test_native_float_type_inferred(self):
        """原生 float 值推断为 'number'。"""
        sample = [{"price": 9.99}]
        result = awin.extract_fields(sample)
        assert result[0]["data_type"] == "number"

    def test_bool_type_inferred(self):
        """布尔值推断为 'boolean'。"""
        sample = [{"active": True}]
        result = awin.extract_fields(sample)
        assert result[0]["data_type"] == "boolean"


# ---------------------------------------------------------------------------
# TestTargetFields — 验证 TARGET_FIELDS 常量
# ---------------------------------------------------------------------------

class TestTargetFields:
    """验证 TARGET_FIELDS 常量定义正确。"""

    def test_target_fields_has_5_entries(self):
        assert len(awin.TARGET_FIELDS) == 5

    def test_target_fields_content(self):
        assert awin.TARGET_FIELDS == {"impressions", "clicks", "totalNo", "totalValue", "totalComm"}


# ---------------------------------------------------------------------------
# Integration 测试（标注 @pytest.mark.integration，CI 中跳过）
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestAuthenticateIntegration:
    """AC1 集成测试：需要真实 Awin API Token，CI 中跳过。"""

    def test_authenticate_returns_bool(self, mock_credentials):
        """authenticate() 返回布尔值（True=成功，False=失败）。"""
        result = awin.authenticate()
        assert isinstance(result, bool)


@pytest.mark.integration
class TestFetchSampleIntegration:
    """AC2 集成测试：需要真实 Awin API Token，CI 中跳过。"""

    def test_fetch_sample_returns_list(self, mock_credentials):
        """fetch_sample() 返回列表（可为空）。"""
        result = awin.fetch_sample()
        assert isinstance(result, list)
