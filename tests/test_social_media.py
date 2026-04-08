"""sources/social_media.py 单元测试及集成测试。

覆盖 AC：
- AC3 & AC6: extract_fields 返回标准 FieldInfo 结构，使用 tests/fixtures/social_media_sample.json
- AC1 & AC2: authenticate() 和 fetch_sample() 标注 @pytest.mark.integration，CI 中跳过
"""

import json
import pytest
from pathlib import Path

import sources.social_media as social_media

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# TestExtractFields — AC3 & AC6：使用 fixture 数据验证 FieldInfo 结构
# ---------------------------------------------------------------------------

class TestExtractFields:
    """AC3 & AC6：extract_fields 从样本数据返回标准 FieldInfo 列表。"""

    @pytest.fixture
    def sample(self):
        """从 tests/fixtures/social_media_sample.json 加载 2 条模拟帖子记录。"""
        with open(FIXTURES_DIR / "social_media_sample.json", encoding="utf-8") as f:
            return json.load(f)

    def test_returns_list(self, sample):
        """返回值为非空列表。"""
        result = social_media.extract_fields(sample)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_each_item_has_four_required_keys(self, sample):
        """每条 FieldInfo 包含 field_name / data_type / sample_value / nullable 四字段（ARCH2）。"""
        result = social_media.extract_fields(sample)
        for item in result:
            assert "field_name" in item, f"缺少 field_name：{item}"
            assert "data_type" in item, f"缺少 data_type：{item}"
            assert "sample_value" in item, f"缺少 sample_value：{item}"
            assert "nullable" in item, f"缺少 nullable：{item}"

    def test_returns_seven_fields(self, sample):
        """返回恰好 7 个字段（TARGET_FIELDS 固定映射）。"""
        result = social_media.extract_fields(sample)
        assert len(result) == 7

    def test_field_name_is_string(self, sample):
        """field_name 必须是字符串。"""
        result = social_media.extract_fields(sample)
        for item in result:
            assert isinstance(item["field_name"], str)

    def test_data_type_is_string(self, sample):
        """data_type 必须是字符串。"""
        result = social_media.extract_fields(sample)
        for item in result:
            assert isinstance(item["data_type"], str)

    def test_nullable_is_bool(self, sample):
        """nullable 必须是布尔值。"""
        result = social_media.extract_fields(sample)
        for item in result:
            assert isinstance(item["nullable"], bool), f"nullable 应为 bool：{item}"

    def test_nullable_when_value_is_none(self, sample):
        """获赞数和心情数 在第二条记录中为 null，应被识别为 nullable=True。"""
        result = social_media.extract_fields(sample)
        likes_field = next(
            (f for f in result if f["field_name"] == "获赞数和心情数"), None
        )
        assert likes_field is not None, "获赞数和心情数 字段应存在"
        assert likes_field["nullable"] is True

    def test_non_null_field_nullable_false(self, sample):
        """发布日期 在所有记录中均有值，nullable 应为 False。"""
        result = social_media.extract_fields(sample)
        date_field = next(
            (f for f in result if f["field_name"] == "发布日期"), None
        )
        assert date_field is not None
        assert date_field["nullable"] is False

    def test_sample_value_is_first_non_null(self, sample):
        """获赞数和心情数 的 sample_value 应为第一条记录的有效值 '89'，而非 null。"""
        result = social_media.extract_fields(sample)
        likes_field = next(f for f in result if f["field_name"] == "获赞数和心情数")
        assert likes_field["sample_value"] == "89"

    def test_returns_sorted_fields(self, sample):
        """返回的字段列表按字段名 sorted 顺序排列（与 TARGET_FIELDS sorted 一致）。"""
        result = social_media.extract_fields(sample)
        names = [item["field_name"] for item in result]
        assert names == sorted(names)

    def test_field_names_match_target_fields(self, sample):
        """返回的字段名集合与 TARGET_FIELDS 完全一致。"""
        result = social_media.extract_fields(sample)
        result_names = {item["field_name"] for item in result}
        assert result_names == set(social_media.TARGET_FIELDS)


# ---------------------------------------------------------------------------
# TestExtractFieldsEdgeCases — 边界情况
# ---------------------------------------------------------------------------

class TestExtractFieldsEdgeCases:
    """边界情况：空列表、全 None 值等。"""

    def test_empty_sample_returns_empty_list(self):
        """空输入返回空列表，不报错。"""
        result = social_media.extract_fields([])
        assert result == []

    def test_all_none_values_nullable(self):
        """字段在所有记录中均为 None 时，nullable=True，sample_value=None。"""
        sample = [
            {"标题": None, "发布日期": None, "状态": None,
             "覆盖人数": None, "获赞数和心情数": None, "评论数": None, "分享次数": None},
            {"标题": None, "发布日期": None, "状态": None,
             "覆盖人数": None, "获赞数和心情数": None, "评论数": None, "分享次数": None},
        ]
        result = social_media.extract_fields(sample)
        for field in result:
            assert field["nullable"] is True
            assert field["sample_value"] is None

    def test_single_record_returns_seven_fields(self):
        """单条记录也能正常提取 7 个字段。"""
        sample = [{
            "标题": "测试帖子",
            "发布日期": "4月1日 12:00",
            "状态": "已发布",
            "覆盖人数": "100",
            "获赞数和心情数": "5",
            "评论数": "1",
            "分享次数": "0",
        }]
        result = social_media.extract_fields(sample)
        assert len(result) == 7

    def test_missing_field_treated_as_null(self):
        """记录中缺少某字段时，等同于 None，nullable=True。"""
        # 第二条记录缺少"分享次数"键
        sample = [
            {"标题": "A", "发布日期": "d1", "状态": "s1",
             "覆盖人数": "100", "获赞数和心情数": "10", "评论数": "1", "分享次数": "2"},
            {"标题": "B", "发布日期": "d2", "状态": "s2",
             "覆盖人数": "200", "获赞数和心情数": "20", "评论数": "3"},
        ]
        result = social_media.extract_fields(sample)
        share_field = next(f for f in result if f["field_name"] == "分享次数")
        assert share_field["nullable"] is True


# ---------------------------------------------------------------------------
# Integration 测试（标注 @pytest.mark.integration，CI 中跳过）
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestAuthenticateIntegration:
    """AC1 集成测试：需要真实 Facebook 账号，CI 中跳过。"""

    def test_authenticate_returns_bool(self, mock_credentials):
        """authenticate() 返回布尔值（True=成功，False=失败）。"""
        result = social_media.authenticate()
        assert isinstance(result, bool)


@pytest.mark.integration
class TestFetchSampleIntegration:
    """AC2 集成测试：需要真实 Facebook 账号，CI 中跳过。"""

    def test_fetch_sample_returns_list(self, mock_credentials):
        """fetch_sample() 返回列表（可为空）。"""
        result = social_media.fetch_sample()
        assert isinstance(result, list)
