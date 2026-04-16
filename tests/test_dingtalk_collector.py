"""单元测试：dingtalk_collector

覆盖：
  - _sanitize_record 转换逻辑
  - collect 正常路径（mock SDK + mock write_to_doris）
  - 单表失败不中断其他表
  - dry-run 模式
"""

import sys
import os
from datetime import datetime
from unittest.mock import MagicMock, patch, call

import pytest

# 注入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../bi/python_sdk/outdoor_collector"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../bi/python_sdk/outdoor_collector/collectors"))

import dingtalk_collector as dc


# ---------------------------------------------------------------------------
# 3.1  _sanitize_record 转换规则
# ---------------------------------------------------------------------------

class TestSanitizeRecord:
    def test_linked_record_to_none(self):
        raw = {"_record_id": "r1", "产品SKU": {"linkedRecordIds": ["abc", "def"]}}
        result = dc._sanitize_record(raw)
        assert result["record_id"] == "r1"
        assert result["产品SKU"] is None

    def test_attachment_to_url(self):
        raw = {
            "_record_id": "r2",
            "合同": [{"url": "https://example.com/file.pdf", "name": "合同.pdf"}],
        }
        result = dc._sanitize_record(raw)
        assert result["合同"] == "https://example.com/file.pdf"

    def test_attachment_resource_url_fallback(self):
        raw = {
            "_record_id": "r3",
            "图片": [{"resourceUrl": "https://cdn.example.com/img.jpg"}],
        }
        result = dc._sanitize_record(raw)
        assert result["图片"] == "https://cdn.example.com/img.jpg"

    def test_list_without_url_or_resource_url_not_attachment(self):
        """list 元素无 url / resourceUrl 时，不视为附件，保持原值"""
        raw = {
            "_record_id": "r4",
            "附件": [{"name": "file.txt"}],
        }
        result = dc._sanitize_record(raw)
        # 不满足附件识别条件（无 url/resourceUrl），保持原 list
        assert result["附件"] == [{"name": "file.txt"}]

    def test_ms_timestamp_to_datetime(self):
        # 2024-01-15 00:00:00 UTC → 毫秒时间戳
        ms = 1705276800000
        raw = {"_record_id": "r5", "*实际发布日期": ms}
        result = dc._sanitize_record(raw)
        dt = result["*实际发布日期"]
        assert isinstance(dt, datetime)
        assert dt.tzinfo is None          # 无时区
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15

    def test_plain_field_unchanged(self):
        raw = {"_record_id": "r6", "姓名": "张三", "年龄": 25, "备注": None}
        result = dc._sanitize_record(raw)
        assert result["record_id"] == "r6"
        assert result["姓名"] == "张三"
        assert result["年龄"] == 25
        assert result["备注"] is None

    def test_record_id_renamed(self):
        raw = {"_record_id": "rec_abc123", "字段A": "value"}
        result = dc._sanitize_record(raw)
        assert "record_id" in result
        assert "_record_id" not in result
        assert result["record_id"] == "rec_abc123"

    def test_small_integer_not_converted(self):
        """小整数（< 1e12）不应被转换为 datetime"""
        raw = {"_record_id": "r7", "数量": 999}
        result = dc._sanitize_record(raw)
        assert result["数量"] == 999

    def test_list_without_url_not_treated_as_attachment(self):
        """list 元素不含 url/resourceUrl 时不按附件处理"""
        raw = {"_record_id": "r8", "标签": ["tag1", "tag2"]}
        result = dc._sanitize_record(raw)
        assert result["标签"] == ["tag1", "tag2"]


# ---------------------------------------------------------------------------
# 3.2  collect 正常路径
# ---------------------------------------------------------------------------

_FAKE_ENV = {
    "DINGTALK_APP_KEY": "ak",
    "DINGTALK_APP_SECRET": "as",
    "DINGTALK_OPERATOR_ID": "oid",
}

_FAKE_RECORDS = [
    {"_record_id": "r1", "名称": "Alice", "时间戳": 1705276800000},
    {"_record_id": "r2", "名称": "Bob",   "时间戳": 1705363200000},
]


class TestCollectHappyPath:
    @patch("dingtalk_collector.update_watermark")
    @patch("dingtalk_collector.write_to_doris", return_value=2)
    @patch("dingtalk_collector.DingTalkClient")
    def test_collect_single_table(self, MockClient, mock_write, mock_wm):
        mock_instance = MockClient.return_value
        mock_instance.fetch_bitable_records.return_value = list(_FAKE_RECORDS)

        with patch.dict(os.environ, _FAKE_ENV):
            results = dc.collect(tables=["kol_tidwe_红人信息汇总"])

        assert results["kol_tidwe_红人信息汇总"] == 2
        mock_write.assert_called_once()
        call_kwargs = mock_write.call_args
        assert call_kwargs.kwargs["unique_keys"] == ["record_id"]
        assert call_kwargs.kwargs["source"] == "dingtalk_collector"
        mock_wm.assert_called_once()

    @patch("dingtalk_collector.update_watermark")
    @patch("dingtalk_collector.write_to_doris", return_value=5)
    @patch("dingtalk_collector.DingTalkClient")
    def test_collect_all_tables(self, MockClient, mock_write, mock_wm):
        mock_instance = MockClient.return_value
        mock_instance.fetch_bitable_records.return_value = list(_FAKE_RECORDS)

        with patch.dict(os.environ, _FAKE_ENV):
            results = dc.collect()

        assert len(results) == len(dc.TABLE_CONFIG)
        assert all(v == 5 for v in results.values())
        assert mock_write.call_count == len(dc.TABLE_CONFIG)

    @patch("dingtalk_collector.update_watermark")
    @patch("dingtalk_collector.write_to_doris")
    @patch("dingtalk_collector.DingTalkClient")
    def test_collected_at_injected(self, MockClient, mock_write, mock_wm):
        """每条记录必须包含 collected_at 字段"""
        mock_instance = MockClient.return_value
        mock_instance.fetch_bitable_records.return_value = [{"_record_id": "r1", "字段": "v"}]
        mock_write.return_value = 1

        with patch.dict(os.environ, _FAKE_ENV):
            dc.collect(tables=["kol_tidwe_红人信息汇总"])

        written_records = mock_write.call_args.kwargs["records"]
        assert all("collected_at" in r for r in written_records)
        assert all(isinstance(r["collected_at"], datetime) for r in written_records)

    @patch("dingtalk_collector.update_watermark")
    @patch("dingtalk_collector.write_to_doris")
    @patch("dingtalk_collector.DingTalkClient")
    def test_record_id_in_written_records(self, MockClient, mock_write, mock_wm):
        """写入数据中必须包含 record_id 字段"""
        mock_instance = MockClient.return_value
        mock_instance.fetch_bitable_records.return_value = [{"_record_id": "abc", "字段": "v"}]
        mock_write.return_value = 1

        with patch.dict(os.environ, _FAKE_ENV):
            dc.collect(tables=["kol_tidwe_红人信息汇总"])

        written_records = mock_write.call_args.kwargs["records"]
        assert all("record_id" in r for r in written_records)
        assert written_records[0]["record_id"] == "abc"


# ---------------------------------------------------------------------------
# 3.3  单表失败不中断其他表
# ---------------------------------------------------------------------------

class TestCollectFailureIsolation:
    @patch("dingtalk_collector.update_watermark")
    @patch("dingtalk_collector.write_to_doris", return_value=3)
    @patch("dingtalk_collector.DingTalkClient")
    def test_one_table_fails_others_continue(self, MockClient, mock_write, mock_wm):
        mock_instance = MockClient.return_value

        def fake_fetch(base_id, sheet_name, include_record_id=False):
            # 第一个 base_id 抛异常
            if base_id == "Gl6Pm2Db8D332mAgCnk7N0AaJxLq0Ee4" and sheet_name == "红人信息汇总":
                raise RuntimeError("API 超时")
            return [{"_record_id": "r1", "字段": "v"}]

        mock_instance.fetch_bitable_records.side_effect = fake_fetch

        with patch.dict(os.environ, _FAKE_ENV):
            results = dc.collect(tables=["kol_tidwe_红人信息汇总", "kol_tidwe_寄样记录"])

        assert results["kol_tidwe_红人信息汇总"] == -1
        assert results["kol_tidwe_寄样记录"] == 3

    @patch("dingtalk_collector.update_watermark")
    @patch("dingtalk_collector.write_to_doris", return_value=1)
    @patch("dingtalk_collector.DingTalkClient")
    def test_watermark_not_updated_on_failure(self, MockClient, mock_write, mock_wm):
        """采集失败时不应更新水位线"""
        mock_instance = MockClient.return_value
        mock_instance.fetch_bitable_records.side_effect = RuntimeError("网络错误")

        with patch.dict(os.environ, _FAKE_ENV):
            results = dc.collect(tables=["kol_tidwe_红人信息汇总"])

        assert results["kol_tidwe_红人信息汇总"] == -1
        mock_wm.assert_not_called()


# ---------------------------------------------------------------------------
# 3.4  dry-run 模式
# ---------------------------------------------------------------------------

class TestDryRun:
    @patch("dingtalk_collector.update_watermark")
    @patch("dingtalk_collector.write_to_doris")
    @patch("dingtalk_collector.DingTalkClient")
    def test_dry_run_skips_write(self, MockClient, mock_write, mock_wm):
        mock_instance = MockClient.return_value
        mock_instance.fetch_bitable_records.return_value = [
            {"_record_id": "r1", "字段": "v"},
            {"_record_id": "r2", "字段": "w"},
        ]

        with patch.dict(os.environ, _FAKE_ENV):
            results = dc.collect(tables=["kol_tidwe_红人信息汇总"], dry_run=True)

        mock_write.assert_not_called()
        assert results["kol_tidwe_红人信息汇总"] == 2

    @patch("dingtalk_collector.update_watermark")
    @patch("dingtalk_collector.write_to_doris")
    @patch("dingtalk_collector.DingTalkClient")
    def test_dry_run_skips_watermark(self, MockClient, mock_write, mock_wm):
        mock_instance = MockClient.return_value
        mock_instance.fetch_bitable_records.return_value = [{"_record_id": "r1", "字段": "v"}]

        with patch.dict(os.environ, _FAKE_ENV):
            dc.collect(tables=["kol_tidwe_红人信息汇总"], dry_run=True)

        mock_wm.assert_not_called()


# ---------------------------------------------------------------------------
# 集成测试标注（不在 CI 单元测试中运行）
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestCollectIntegration:
    def test_real_api_call(self):
        """集成测试：需真实钉钉凭证和 Doris 连接"""
        results = dc.collect(tables=["kol_tidwe_内容上线"], dry_run=True)
        assert "kol_tidwe_内容上线" in results
        assert results["kol_tidwe_内容上线"] >= 0
