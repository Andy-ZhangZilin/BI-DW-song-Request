"""Awin 数据源单元测试。

覆盖 AC3 & AC7：
- AC3: extract_fields 返回标准 FieldInfo 结构（field_name/data_type/sample_value/nullable）
- AC7: extract_fields 单元测试使用 tests/fixtures/awin_sample.json；
       fetch_sample 标注 @pytest.mark.integration，不在单元测试中执行
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
    """AC3: extract_fields 从样本数据返回标准 FieldInfo 列表。"""

    @pytest.fixture
    def sample(self):
        """从 tests/fixtures/awin_sample.json 加载 3 条模拟报表记录。"""
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

    def test_field_names_cover_all_keys(self, sample):
        """返回的字段名覆盖样本中的所有 key。"""
        expected_keys = set()
        for record in sample:
            expected_keys.update(record.keys())
        result = awin.extract_fields(sample)
        result_keys = {item["field_name"] for item in result}
        assert expected_keys == result_keys

    def test_commission_nullable_true(self, sample):
        """commission 在 TXN-002 中为 null，应被识别为 nullable=True。"""
        result = awin.extract_fields(sample)
        commission_field = next(
            (f for f in result if f["field_name"] == "commission"), None
        )
        assert commission_field is not None, "commission 字段应存在"
        assert commission_field["nullable"] is True

    def test_transaction_id_nullable_false(self, sample):
        """transaction_id 在所有记录中均有值，nullable 应为 False。"""
        result = awin.extract_fields(sample)
        tx_field = next(
            (f for f in result if f["field_name"] == "transaction_id"), None
        )
        assert tx_field is not None
        assert tx_field["nullable"] is False

    def test_sample_value_is_first_non_null(self, sample):
        """commission 的 sample_value 为第一条有效值 '4.95'，而非 null。"""
        result = awin.extract_fields(sample)
        commission_field = next(f for f in result if f["field_name"] == "commission")
        assert commission_field["sample_value"] == "4.95"

    def test_data_type_string_inference(self, sample):
        """字符串类型值应推断为 'string'。"""
        result = awin.extract_fields(sample)
        # date 字段的值是 "2024-01-15"（字符串），应推断为 string
        date_field = next(f for f in result if f["field_name"] == "date")
        assert date_field["data_type"] == "string"

    def test_returns_sorted_fields(self, sample):
        """返回的字段列表按字段名字母顺序排列（便于报告阅读）。"""
        result = awin.extract_fields(sample)
        names = [item["field_name"] for item in result]
        assert names == sorted(names)


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
        sample = [{"order_id": "O-1", "amount": "50.00"}]
        result = awin.extract_fields(sample)
        assert len(result) == 2
        names = {f["field_name"] for f in result}
        assert names == {"order_id", "amount"}

    def test_all_none_values_nullable(self):
        """字段在所有记录中均为 None 时，nullable=True，sample_value=None。"""
        sample = [{"field_x": None}, {"field_x": None}]
        result = awin.extract_fields(sample)
        assert result[0]["nullable"] is True
        assert result[0]["sample_value"] is None

    def test_empty_string_treated_as_null(self):
        """空字符串 '' 视为空值，影响 nullable 判断。"""
        sample = [{"field_y": ""}, {"field_y": "有值"}]
        result = awin.extract_fields(sample)
        assert result[0]["nullable"] is True

    def test_string_encoded_number_inferred_as_number(self):
        """字符串编码的浮点数应推断为 'number'（Playwright inner_text 始终返回字符串）。"""
        sample = [{"amount": "99.00"}, {"amount": "149.50"}]
        result = awin.extract_fields(sample)
        amount_field = result[0]
        assert amount_field["data_type"] == "number"

    def test_non_numeric_string_inferred_as_string(self):
        """非数字字符串应推断为 'string'。"""
        sample = [{"status": "approved"}, {"status": "pending"}]
        result = awin.extract_fields(sample)
        status_field = result[0]
        assert status_field["data_type"] == "string"

    def test_whitespace_string_treated_as_null(self):
        """纯空白字符串视为空值，影响 nullable 判断（D3）。"""
        sample = [{"field_z": "   "}, {"field_z": "有值"}]
        result = awin.extract_fields(sample)
        assert result[0]["nullable"] is True

    def test_multiple_records_consistent_keys(self):
        """多条记录键集合不一致时，联合所有键，缺失键 nullable=True。"""
        sample = [
            {"a": "v1", "b": "v2"},
            {"a": "v3"},              # 缺少 b
        ]
        result = awin.extract_fields(sample)
        names = {f["field_name"] for f in result}
        assert names == {"a", "b"}
        b_field = next(f for f in result if f["field_name"] == "b")
        assert b_field["nullable"] is True

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
# Integration 测试（标注 @pytest.mark.integration，CI 中跳过）
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestAuthenticateIntegration:
    """AC1 集成测试：需要真实 Awin 账号，CI 中跳过。"""

    def test_authenticate_returns_bool(self, mock_credentials):
        """authenticate() 返回布尔值（True=成功，False=失败）。"""
        result = awin.authenticate()
        assert isinstance(result, bool)


@pytest.mark.integration
class TestFetchSampleIntegration:
    """AC2 集成测试：需要真实 Awin 账号，CI 中跳过。"""

    def test_fetch_sample_returns_list(self, mock_credentials):
        """fetch_sample() 返回列表（可为空）。"""
        result = awin.fetch_sample()
        assert isinstance(result, list)
