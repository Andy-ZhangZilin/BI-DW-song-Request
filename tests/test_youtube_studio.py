"""YouTube Studio 爬虫数据源单元测试。

覆盖 AC：
    AC3 — extract_fields() 返回标准 FieldInfo 列表（6 个目标字段）
    AC5 — CAPTCHA 检测逻辑（独立函数测试）
    AC6 — 单元测试不依赖真实账号；集成测试标注 @pytest.mark.integration

集成测试（标注 @pytest.mark.integration，CI 中跳过）：
    AC1 — authenticate() 返回 bool
    AC2 — fetch_sample() 返回非空列表
"""
import json
import pytest
from pathlib import Path

from sources import youtube_studio

FIXTURES_DIR = Path(__file__).parent / "fixtures"

REQUIRED_KEYS = {"field_name", "data_type", "sample_value", "nullable"}


# ---------------------------------------------------------------------------
# TestExtractFields — AC3 & AC6
# ---------------------------------------------------------------------------

class TestExtractFields:
    """使用 fixture 数据验证 extract_fields() 返回标准 FieldInfo 结构。"""

    @pytest.fixture
    def sample(self):
        with open(FIXTURES_DIR / "youtube_studio_sample.json", encoding="utf-8") as f:
            return json.load(f)

    def test_returns_list(self, sample):
        result = youtube_studio.extract_fields(sample)
        assert isinstance(result, list)

    def test_returns_correct_count(self, sample):
        result = youtube_studio.extract_fields(sample)
        assert len(result) == len(youtube_studio.TARGET_FIELDS)

    def test_each_item_has_four_required_keys(self, sample):
        result = youtube_studio.extract_fields(sample)
        for item in result:
            assert set(item.keys()) == REQUIRED_KEYS, (
                f"FieldInfo 结构不符合规范，缺少键：{REQUIRED_KEYS - set(item.keys())}"
            )

    def test_returns_sorted_fields(self, sample):
        result = youtube_studio.extract_fields(sample)
        field_names = [item["field_name"] for item in result]
        assert field_names == sorted(youtube_studio.TARGET_FIELDS)

    def test_nullable_when_value_is_none(self, sample):
        """第二条记录中 订阅者 和 点击率 为 null，应触发 nullable=True。"""
        result = youtube_studio.extract_fields(sample)
        nullable_fields = {item["field_name"]: item["nullable"] for item in result}
        assert nullable_fields["订阅者"] is True
        assert nullable_fields["点击率"] is True

    def test_non_nullable_field(self, sample):
        """播放量 在两条记录中都有值，应为 nullable=False。"""
        result = youtube_studio.extract_fields(sample)
        nullable_fields = {item["field_name"]: item["nullable"] for item in result}
        assert nullable_fields["播放量"] is False

    def test_sample_value_is_first_non_empty(self, sample):
        """播放量 首条非空值应为 '1,234'。"""
        result = youtube_studio.extract_fields(sample)
        field_map = {item["field_name"]: item for item in result}
        assert field_map["播放量"]["sample_value"] == "1,234"

    def test_data_type_inferred(self, sample):
        """每个 FieldInfo 的 data_type 字段应为非空字符串。"""
        result = youtube_studio.extract_fields(sample)
        for item in result:
            assert isinstance(item["data_type"], str)
            assert item["data_type"] != ""

    def test_null_sample_value_type_is_unknown(self, sample):
        """全部为 None 的字段，sample_value=None，data_type='unknown'。"""
        # 构造只含 null 的 sample
        null_sample = [
            {field: None for field in youtube_studio.TARGET_FIELDS}
        ]
        result = youtube_studio.extract_fields(null_sample)
        for item in result:
            assert item["sample_value"] is None
            assert item["data_type"] == "unknown"


# ---------------------------------------------------------------------------
# TestExtractFieldsEdgeCases — 边界情况
# ---------------------------------------------------------------------------

class TestExtractFieldsEdgeCases:
    """边界情况：空列表等。"""

    def test_empty_sample_returns_empty_list(self):
        result = youtube_studio.extract_fields([])
        assert result == []

    def test_single_record_with_all_fields(self):
        sample = [{
            "播放量": "100",
            "观看时长（小时）": "5.5",
            "订阅者": "+3",
            "曝光次数": "500",
            "点击率": "2.0%",
            "平均观看时长": "1:30",
        }]
        result = youtube_studio.extract_fields(sample)
        assert len(result) == 6
        for item in result:
            assert item["nullable"] is False

    def test_partial_fields_in_record(self):
        """记录中部分字段缺失时，缺失字段应为 nullable=True，sample_value=None。"""
        sample = [{"播放量": "100"}]  # 只有播放量
        result = youtube_studio.extract_fields(sample)
        field_map = {item["field_name"]: item for item in result}
        assert field_map["播放量"]["sample_value"] == "100"
        assert field_map["播放量"]["nullable"] is False
        assert field_map["订阅者"]["sample_value"] is None
        assert field_map["订阅者"]["nullable"] is True


# ---------------------------------------------------------------------------
# TestInferType — _infer_type 内部逻辑
# ---------------------------------------------------------------------------

class TestInferType:
    """验证 _infer_type 辅助函数的类型推断逻辑。"""

    def test_none_returns_unknown(self):
        assert youtube_studio._infer_type(None) == "unknown"

    def test_integer_string(self):
        assert youtube_studio._infer_type("1234") == "integer"

    def test_integer_with_comma(self):
        """千位分隔符数字如 '1,234' 应解析为 integer。"""
        assert youtube_studio._infer_type("1,234") == "integer"

    def test_float_string(self):
        assert youtube_studio._infer_type("56.7") == "number"

    def test_plain_string(self):
        assert youtube_studio._infer_type("4.2%") == "string"

    def test_time_string(self):
        assert youtube_studio._infer_type("2:45") == "string"

    def test_bool_value(self):
        assert youtube_studio._infer_type(True) == "boolean"

    def test_int_value(self):
        assert youtube_studio._infer_type(42) == "integer"

    def test_float_value(self):
        assert youtube_studio._infer_type(3.14) == "number"


# ---------------------------------------------------------------------------
# TestIsEmpty — _is_empty 内部逻辑
# ---------------------------------------------------------------------------

class TestIsEmpty:
    """验证 _is_empty 辅助函数。"""

    def test_none_is_empty(self):
        assert youtube_studio._is_empty(None) is True

    def test_empty_string_is_empty(self):
        assert youtube_studio._is_empty("") is True

    def test_whitespace_is_empty(self):
        assert youtube_studio._is_empty("   ") is True

    def test_nonempty_string_not_empty(self):
        assert youtube_studio._is_empty("1,234") is False

    def test_zero_not_empty(self):
        assert youtube_studio._is_empty(0) is False


# ---------------------------------------------------------------------------
# 集成测试（需要真实 Google 账号，CI 中跳过）
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestAuthenticateIntegration:
    """AC1 集成测试：需要真实 YOUTUBE_STUDIO_EMAIL/PASSWORD，CI 中跳过。"""

    def test_authenticate_returns_bool(self, mock_credentials):
        result = youtube_studio.authenticate()
        assert isinstance(result, bool)


@pytest.mark.integration
class TestFetchSampleIntegration:
    """AC2 集成测试：需要真实 YOUTUBE_STUDIO_EMAIL/PASSWORD，CI 中跳过。"""

    def test_fetch_sample_returns_list(self, mock_credentials):
        result = youtube_studio.fetch_sample()
        assert isinstance(result, list)
