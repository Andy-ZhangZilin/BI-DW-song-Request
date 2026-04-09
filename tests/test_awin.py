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

# Performance Over Time 全部 10 个字段
ALL_10_FIELDS = {
    "impressions", "clicks", "totalNo", "totalValue", "totalComm",
    "conversionRate", "aov", "cpa", "cpc", "roi",
}


# ---------------------------------------------------------------------------
# TestExtractFields — AC3 & AC7：使用 fixture 数据验证 FieldInfo 结构
# ---------------------------------------------------------------------------

class TestExtractFields:
    """AC3: extract_fields 从样本数据返回标准 FieldInfo 列表。"""

    @pytest.fixture
    def sample(self):
        """从 tests/fixtures/awin_sample.json 加载数据。"""
        with open(FIXTURES_DIR / "awin_sample.json", encoding="utf-8") as f:
            return json.load(f)

    def test_returns_list(self, sample):
        result = awin.extract_fields(sample)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_each_item_has_four_required_keys(self, sample):
        result = awin.extract_fields(sample)
        for item in result:
            assert "field_name" in item
            assert "data_type" in item
            assert "sample_value" in item
            assert "nullable" in item

    def test_field_names_cover_all_10_fields(self, sample):
        """返回的字段名覆盖全部 10 个 Performance Over Time 字段。"""
        result = awin.extract_fields(sample)
        result_keys = {item["field_name"] for item in result}
        assert result_keys == ALL_10_FIELDS

    def test_exactly_10_fields_returned(self, sample):
        result = awin.extract_fields(sample)
        assert len(result) == 10

    def test_clicks_nullable_false(self, sample):
        result = awin.extract_fields(sample)
        field = next(f for f in result if f["field_name"] == "clicks")
        assert field["nullable"] is False

    def test_integer_type_for_clicks(self, sample):
        result = awin.extract_fields(sample)
        field = next(f for f in result if f["field_name"] == "clicks")
        assert field["data_type"] == "integer"

    def test_number_type_for_totalvalue(self, sample):
        result = awin.extract_fields(sample)
        field = next(f for f in result if f["field_name"] == "totalValue")
        assert field["data_type"] == "number"

    def test_number_type_for_conversionrate(self, sample):
        result = awin.extract_fields(sample)
        field = next(f for f in result if f["field_name"] == "conversionRate")
        assert field["data_type"] == "number"

    def test_aov_nullable_true(self, sample):
        """aov 在第二条记录中为 null（totalNo=0 无法计算），nullable 应为 True。"""
        result = awin.extract_fields(sample)
        field = next(f for f in result if f["field_name"] == "aov")
        assert field["nullable"] is True

    def test_roi_nullable_true(self, sample):
        """roi 在第二条记录中为 null（totalComm=0 无法计算），nullable 应为 True。"""
        result = awin.extract_fields(sample)
        field = next(f for f in result if f["field_name"] == "roi")
        assert field["nullable"] is True

    def test_returns_sorted_fields(self, sample):
        result = awin.extract_fields(sample)
        names = [item["field_name"] for item in result]
        assert names == sorted(names)

    def test_sample_value_clicks(self, sample):
        result = awin.extract_fields(sample)
        field = next(f for f in result if f["field_name"] == "clicks")
        assert field["sample_value"] == 76


# ---------------------------------------------------------------------------
# TestEnrichRecord — 计算字段验证
# ---------------------------------------------------------------------------

class TestEnrichRecord:
    """验证 _enrich_record 正确计算 5 个派生字段。"""

    def test_normal_record(self):
        rec = {
            "impressions": 100, "clicks": 50,
            "totalNo": 10, "totalValue": 500.0, "totalComm": 50.0,
            "publisherId": 999, "region": "US",  # 多余字段应被过滤
        }
        result = awin._enrich_record(rec)
        assert result["conversionRate"] == 0.2     # 10/50
        assert result["aov"] == 50.0               # 500/10
        assert result["cpa"] == 5.0                # 50/10
        assert result["cpc"] == 1.0                # 50/50
        assert result["roi"] == 10.0               # 500/50
        assert "publisherId" not in result
        assert "region" not in result

    def test_zero_clicks(self):
        rec = {"impressions": 0, "clicks": 0, "totalNo": 0, "totalValue": 0.0, "totalComm": 0.0}
        result = awin._enrich_record(rec)
        assert result["conversionRate"] is None
        assert result["cpc"] is None

    def test_zero_transactions(self):
        rec = {"impressions": 0, "clicks": 10, "totalNo": 0, "totalValue": 0.0, "totalComm": 0.0}
        result = awin._enrich_record(rec)
        assert result["aov"] is None
        assert result["cpa"] is None

    def test_zero_commission(self):
        rec = {"impressions": 0, "clicks": 10, "totalNo": 5, "totalValue": 100.0, "totalComm": 0.0}
        result = awin._enrich_record(rec)
        assert result["roi"] is None


# ---------------------------------------------------------------------------
# TestExtractFieldsEdgeCases — 边界情况
# ---------------------------------------------------------------------------

class TestExtractFieldsEdgeCases:

    def test_empty_sample_returns_empty_list(self):
        result = awin.extract_fields([])
        assert result == []

    def test_single_record(self):
        sample = [{"clicks": 10, "totalNo": 5}]
        result = awin.extract_fields(sample)
        assert len(result) == 2

    def test_all_none_values_nullable(self):
        sample = [{"field_x": None}, {"field_x": None}]
        result = awin.extract_fields(sample)
        assert result[0]["nullable"] is True

    def test_native_float_type_inferred(self):
        sample = [{"price": 9.99}]
        result = awin.extract_fields(sample)
        assert result[0]["data_type"] == "number"


# ---------------------------------------------------------------------------
# TestSafeDiv
# ---------------------------------------------------------------------------

class TestSafeDiv:

    def test_normal_division(self):
        assert awin._safe_div(10, 3) == 3.3333

    def test_zero_denominator_returns_none(self):
        assert awin._safe_div(10, 0) is None

    def test_both_zero_returns_none(self):
        assert awin._safe_div(0, 0) is None


# ---------------------------------------------------------------------------
# Integration 测试（标注 @pytest.mark.integration，CI 中跳过）
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestAuthenticateIntegration:

    def test_authenticate_returns_bool(self, mock_credentials):
        result = awin.authenticate()
        assert isinstance(result, bool)


@pytest.mark.integration
class TestFetchSampleIntegration:

    def test_fetch_sample_returns_list(self, mock_credentials):
        result = awin.fetch_sample()
        assert isinstance(result, list)
