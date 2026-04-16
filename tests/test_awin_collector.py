"""单元测试：awin_collector

测试覆盖：
    - _transform()  字段映射和类型转换（Task 2.1）
    - collect()     首次运行 → 全量（Task 2.2）
    - collect()     增量运行 → 回溯 N 天（Task 2.3）
    - collect()     API 返回空列表 → 更新水位线（Task 2.4）
    - collect()     API Token 无效 → RuntimeError（Task 2.5）
"""

import os
import sys
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# sys.path：让 pytest（从 outdoor-data-validator/ 根目录运行）能找到 awin_collector
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bi", "python_sdk", "outdoor_collector"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bi", "python_sdk", "outdoor_collector", "collectors"))

import awin_collector as ac


# ---------------------------------------------------------------------------
# 公共 fixture
# ---------------------------------------------------------------------------

VALID_ENV = {
    "AWIN_API_TOKEN": "test_token_xyz",
    "AWIN_ADVERTISER_ID": "89509",
}

SAMPLE_RAW_RECORD = {
    "id": 12345678,
    "advertiserId": 89509,
    "publisherId": 123,
    "publisherName": "Publisher XYZ",
    "commissionStatus": "approved",
    "commissionAmount": {"amount": "5.00", "currency": "USD"},
    "saleAmount": {"amount": "50.00", "currency": "USD"},
    "clickRef": "ref123",
    "transactionDate": "2026-04-01T10:00:00",
    "validationDate": "2026-04-08T10:00:00",
    "type": "sale",
    "commissionGroupId": 1,
    "commissionGroupName": "Default Group",
}


# ---------------------------------------------------------------------------
# Task 2.1：_transform() 字段映射和类型转换
# ---------------------------------------------------------------------------

class TestTransform:
    def test_basic_mapping(self):
        """正常记录：所有字段均正确映射。"""
        result = ac._transform([SAMPLE_RAW_RECORD])
        assert len(result) == 1
        r = result[0]

        assert r["transaction_id"] == 12345678
        assert r["publisher_id"] == 123
        assert r["publisher_name"] == "Publisher XYZ"
        assert r["commission_status"] == "approved"
        assert abs(r["commission_amount"] - 5.0) < 1e-6
        assert abs(r["sale_amount"] - 50.0) < 1e-6
        assert r["click_ref"] == "ref123"
        assert r["transaction_date"] == "2026-04-01T10:00:00"
        assert r["validation_date"] == "2026-04-08T10:00:00"
        assert r["transaction_type"] == "sale"
        assert r["commission_group_id"] == 1
        assert r["commission_group_name"] == "Default Group"

    def test_empty_input(self):
        """空列表返回空列表。"""
        assert ac._transform([]) == []

    def test_null_amount_fields(self):
        """commissionAmount / saleAmount 为 None 时，转换后为 None。"""
        rec = {**SAMPLE_RAW_RECORD, "commissionAmount": None, "saleAmount": None}
        result = ac._transform([rec])
        assert result[0]["commission_amount"] is None
        assert result[0]["sale_amount"] is None

    def test_missing_nested_amount(self):
        """commissionAmount 为空 dict 时，amount 字段为 None。"""
        rec = {**SAMPLE_RAW_RECORD, "commissionAmount": {}, "saleAmount": {}}
        result = ac._transform([rec])
        assert result[0]["commission_amount"] is None
        assert result[0]["sale_amount"] is None

    def test_pending_transaction_null_validation_date(self):
        """pending 状态的交易，validationDate 为 None 时保持 None。"""
        rec = {**SAMPLE_RAW_RECORD, "commissionStatus": "pending", "validationDate": None}
        result = ac._transform([rec])
        assert result[0]["validation_date"] is None
        assert result[0]["commission_status"] == "pending"

    def test_multiple_records(self):
        """多条记录均正确转换。"""
        rec2 = {**SAMPLE_RAW_RECORD, "id": 99999, "publisherId": 456}
        result = ac._transform([SAMPLE_RAW_RECORD, rec2])
        assert len(result) == 2
        assert result[1]["transaction_id"] == 99999
        assert result[1]["publisher_id"] == 456

    def test_keys_match_doris_columns(self):
        """转换结果键集合必须包含所有 Doris 列。"""
        expected_keys = {
            "transaction_id", "publisher_id", "publisher_name",
            "commission_status", "commission_amount", "sale_amount",
            "click_ref", "transaction_date", "validation_date",
            "transaction_type", "commission_group_id", "commission_group_name",
        }
        result = ac._transform([SAMPLE_RAW_RECORD])
        assert set(result[0].keys()) == expected_keys


class TestToFloat:
    def test_string_number(self):
        assert abs(ac._to_float("5.00") - 5.0) < 1e-6

    def test_none(self):
        assert ac._to_float(None) is None

    def test_number_with_comma(self):
        assert abs(ac._to_float("1,234.56") - 1234.56) < 1e-6

    def test_invalid_string(self):
        assert ac._to_float("n/a") is None

    def test_int_value(self):
        assert abs(ac._to_float(10) - 10.0) < 1e-6


# ---------------------------------------------------------------------------
# Task 2.2：collect() 首次运行 → 全量
# ---------------------------------------------------------------------------

class TestCollectFirstRun:
    @patch("awin_collector.get_watermark", return_value=None)
    @patch("awin_collector.update_watermark")
    @patch("awin_collector.write_to_doris", return_value=1)
    @patch("awin_collector._fetch_transactions", return_value=[SAMPLE_RAW_RECORD])
    def test_full_mode_uses_earliest_date(
        self, mock_fetch, mock_write, mock_update_wm, mock_get_wm
    ):
        """水位线为 None 时，start_date 使用 AWIN_EARLIEST_DATE（默认 2024-01-01）。"""
        with patch.dict(os.environ, VALID_ENV):
            written = ac.collect()

        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args[0]
        # call_args = (token, advertiser_id, start_date, end_date)
        assert call_args[2] == "2024-01-01"
        assert written == 1

    @patch("awin_collector.get_watermark", return_value=None)
    @patch("awin_collector.update_watermark")
    @patch("awin_collector.write_to_doris", return_value=3)
    @patch("awin_collector._fetch_transactions", return_value=[SAMPLE_RAW_RECORD])
    def test_custom_earliest_date_from_env(
        self, mock_fetch, mock_write, mock_update_wm, mock_get_wm
    ):
        """AWIN_EARLIEST_DATE 环境变量可覆盖默认起始日期。"""
        env = {**VALID_ENV, "AWIN_EARLIEST_DATE": "2023-01-01"}
        with patch.dict(os.environ, env):
            ac.collect()

        call_args = mock_fetch.call_args[0]
        assert call_args[2] == "2023-01-01"

    @patch("awin_collector.get_watermark", return_value=None)
    @patch("awin_collector.update_watermark")
    @patch("awin_collector.write_to_doris", return_value=1)
    @patch("awin_collector._fetch_transactions", return_value=[SAMPLE_RAW_RECORD])
    def test_watermark_updated_after_write(
        self, mock_fetch, mock_write, mock_update_wm, mock_get_wm
    ):
        """写入成功后必须调用 update_watermark。"""
        with patch.dict(os.environ, VALID_ENV):
            ac.collect()
        mock_update_wm.assert_called_once()

    @patch("awin_collector.reset_watermark")
    @patch("awin_collector.get_watermark", return_value=None)
    @patch("awin_collector.update_watermark")
    @patch("awin_collector.write_to_doris", return_value=1)
    @patch("awin_collector._fetch_transactions", return_value=[SAMPLE_RAW_RECORD])
    def test_mode_full_resets_watermark(
        self, mock_fetch, mock_write, mock_update_wm, mock_get_wm, mock_reset
    ):
        """--mode full 时先调用 reset_watermark。"""
        with patch.dict(os.environ, VALID_ENV):
            ac.collect(mode="full")
        mock_reset.assert_called_once_with(ac.SOURCE, "transactions")


# ---------------------------------------------------------------------------
# Task 2.3：collect() 增量运行 → 回溯 N 天
# ---------------------------------------------------------------------------

class TestCollectIncremental:
    def _make_wm(self, dt: datetime) -> dict:
        return {
            "source": "awin_collector",
            "table_name": "transactions",
            "last_success_time": dt,
            "run_mode": "incremental",
            "updated_at": dt,
        }

    @patch("awin_collector.get_watermark")
    @patch("awin_collector.update_watermark")
    @patch("awin_collector.write_to_doris", return_value=2)
    @patch("awin_collector._fetch_transactions", return_value=[SAMPLE_RAW_RECORD])
    def test_incremental_start_date_is_watermark_minus_lookback(
        self, mock_fetch, mock_write, mock_update_wm, mock_get_wm
    ):
        """增量模式：start_date = 水位线日期 - lookback_days。"""
        wm_dt = datetime(2026, 4, 10, 12, 0, 0)
        mock_get_wm.return_value = self._make_wm(wm_dt)

        with patch.dict(os.environ, VALID_ENV):
            ac.collect(lookback_days=30)

        call_args = mock_fetch.call_args[0]
        expected_start = str(wm_dt.date() - timedelta(days=30))
        assert call_args[2] == expected_start  # start_date = 2026-03-11

    @patch("awin_collector.get_watermark")
    @patch("awin_collector.update_watermark")
    @patch("awin_collector.write_to_doris", return_value=2)
    @patch("awin_collector._fetch_transactions", return_value=[SAMPLE_RAW_RECORD])
    def test_incremental_reads_lookback_from_env(
        self, mock_fetch, mock_write, mock_update_wm, mock_get_wm
    ):
        """AWIN_LOOKBACK_DAYS 环境变量控制回溯窗口。"""
        wm_dt = datetime(2026, 4, 10)
        mock_get_wm.return_value = self._make_wm(wm_dt)

        env = {**VALID_ENV, "AWIN_LOOKBACK_DAYS": "7"}
        with patch.dict(os.environ, env):
            ac.collect()

        call_args = mock_fetch.call_args[0]
        expected_start = str(wm_dt.date() - timedelta(days=7))
        assert call_args[2] == expected_start  # start_date = 2026-04-03

    @patch("awin_collector.get_watermark")
    @patch("awin_collector.update_watermark")
    @patch("awin_collector.write_to_doris", return_value=5)
    @patch("awin_collector._fetch_transactions", return_value=[SAMPLE_RAW_RECORD])
    def test_incremental_watermark_updated(
        self, mock_fetch, mock_write, mock_update_wm, mock_get_wm
    ):
        """增量写入后水位线必须更新。"""
        mock_get_wm.return_value = self._make_wm(datetime(2026, 4, 1))
        with patch.dict(os.environ, VALID_ENV):
            ac.collect(lookback_days=30)
        mock_update_wm.assert_called_once()


# ---------------------------------------------------------------------------
# Task 2.4：API 返回空列表 → 更新水位线，写入 0 行
# ---------------------------------------------------------------------------

class TestCollectNoData:
    @patch("awin_collector.get_watermark", return_value=None)
    @patch("awin_collector.update_watermark")
    @patch("awin_collector._fetch_transactions", return_value=[])
    def test_empty_response_returns_zero(self, mock_fetch, mock_update_wm, mock_get_wm):
        """API 返回空列表时，written = 0，正常退出。"""
        with patch.dict(os.environ, VALID_ENV):
            written = ac.collect()
        assert written == 0

    @patch("awin_collector.get_watermark", return_value=None)
    @patch("awin_collector.update_watermark")
    @patch("awin_collector._fetch_transactions", return_value=[])
    def test_empty_response_still_updates_watermark(
        self, mock_fetch, mock_update_wm, mock_get_wm
    ):
        """即使无数据，水位线仍要更新（避免下次重跑全量）。"""
        with patch.dict(os.environ, VALID_ENV):
            ac.collect()
        mock_update_wm.assert_called_once()

    @patch("awin_collector.get_watermark", return_value=None)
    @patch("awin_collector.update_watermark")
    @patch("awin_collector.write_to_doris")
    @patch("awin_collector._fetch_transactions", return_value=[])
    def test_empty_response_does_not_call_write_to_doris(
        self, mock_fetch, mock_write, mock_update_wm, mock_get_wm
    ):
        """无数据时不调用 write_to_doris。"""
        with patch.dict(os.environ, VALID_ENV):
            ac.collect()
        mock_write.assert_not_called()


# ---------------------------------------------------------------------------
# Task 2.5：API Token 无效 → RuntimeError
# ---------------------------------------------------------------------------

class TestCollectInvalidToken:
    @patch("awin_collector.get_watermark", return_value=None)
    @patch(
        "awin_collector._fetch_transactions",
        side_effect=RuntimeError("[awin_collector] API Token 无效（HTTP 401）"),
    )
    def test_invalid_token_raises_runtime_error(self, mock_fetch, mock_get_wm):
        """API Token 无效时，collect() 向上传播 RuntimeError。"""
        with patch.dict(os.environ, VALID_ENV):
            with pytest.raises(RuntimeError, match="API Token 无效"):
                ac.collect()

    def test_missing_credentials_raises_runtime_error(self):
        """未配置环境变量时，collect() 抛出 RuntimeError。"""
        env_without_creds = {k: v for k, v in os.environ.items()
                             if k not in ("AWIN_API_TOKEN", "AWIN_ADVERTISER_ID")}
        with patch.dict(os.environ, env_without_creds, clear=True):
            with pytest.raises(RuntimeError, match="未配置 AWIN_API_TOKEN"):
                ac.collect()

    @patch("awin_collector.get_watermark", return_value=None)
    @patch("awin_collector.update_watermark")
    @patch(
        "awin_collector._fetch_transactions",
        side_effect=RuntimeError("[awin_collector] API Token 无效（HTTP 401）"),
    )
    def test_invalid_token_does_not_update_watermark(
        self, mock_fetch, mock_update_wm, mock_get_wm
    ):
        """API 失败时，水位线不应被更新。"""
        with patch.dict(os.environ, VALID_ENV):
            with pytest.raises(RuntimeError):
                ac.collect()
        mock_update_wm.assert_not_called()
