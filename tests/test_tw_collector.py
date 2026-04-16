"""tw_collector 单元测试。

测试策略：
- mock pymysql.connect 避免真实 DB 连接
- mock requests.post 避免真实 API 调用
- 验证数据转换、日期范围解析、采集逻辑、错误处理
"""

import json
import os
import sys
from datetime import datetime, date
from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# 路径设置
# ---------------------------------------------------------------------------
_OUTDOOR_COLLECTOR_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "bi", "python_sdk", "outdoor_collector"
)
sys.path.insert(0, _OUTDOOR_COLLECTOR_ROOT)

from collectors.tw_collector import (
    _serialize_row,
    _transform_pixel_orders_table,
    _transform_sessions_table,
    _transform_ai_visibility_table,
    _resolve_date_range,
    collect_table,
    collect_all,
    ALL_TABLES,
    TABLE_EARLIEST_DATES,
    SOURCE,
)

# ---------------------------------------------------------------------------
# _serialize_row 测试
# ---------------------------------------------------------------------------

def test_serialize_row_arrays():
    """list 和 dict 字段应被序列化为 JSON 字符串。"""
    row = {
        "order_id": "123",
        "customer_tags": ["CartSee", "member"],
        "products_info": [{"product_id": "456", "qty": 2}],
        "discount_codes": [],
    }
    result = _serialize_row(row)

    assert result["order_id"] == "123"
    assert isinstance(result["customer_tags"], str)
    assert json.loads(result["customer_tags"]) == ["CartSee", "member"]
    assert isinstance(result["products_info"], str)
    assert json.loads(result["products_info"])[0]["product_id"] == "456"
    assert result["discount_codes"] == "[]"


def test_serialize_row_booleans():
    """bool 字段应转换为 TINYINT（1/0）。"""
    row = {
        "is_new_customer": True,
        "is_subscription_order": False,
        "is_first_order_in_subscription": False,
    }
    result = _serialize_row(row)
    assert result["is_new_customer"] == 1
    assert result["is_subscription_order"] == 0
    assert result["is_first_order_in_subscription"] == 0


def test_serialize_row_passthrough():
    """数字、字符串、None 应原样返回。"""
    row = {"gross_sales": 97.64, "channel": "smile_rewards", "cancelled_at": None}
    result = _serialize_row(row)
    assert result["gross_sales"] == 97.64
    assert result["channel"] == "smile_rewards"
    assert result["cancelled_at"] is None


# ---------------------------------------------------------------------------
# transform 函数测试
# ---------------------------------------------------------------------------

def test_transform_sessions_table():
    """sessions_table transform：is_new_visitor bool → 0/1，其他字段原样。"""
    rows = [
        {
            "session_id": "abc123",
            "event_date": "2026-04-10",
            "is_new_visitor": False,
            "session_page_views": 3,
            "channel": "google-ads",
        }
    ]
    result = _transform_sessions_table(rows)
    assert len(result) == 1
    assert result[0]["is_new_visitor"] == 0
    assert result[0]["session_id"] == "abc123"
    assert result[0]["session_page_views"] == 3


def test_transform_pixel_orders():
    """pixel_orders_table transform：数组序列化，布尔转换。"""
    rows = [
        {
            "order_id": "6511942172741",
            "customer_tags": ["CartSee", "member"],
            "products_info": [{"product_id": "789"}],
            "discount_codes": [],
            "tags": ["seel-wfd"],
            "is_new_customer": False,
            "is_subscription_order": False,
            "is_first_order_in_subscription": False,
            "gross_sales": 97.64,
        }
    ]
    result = _transform_pixel_orders_table(rows)
    assert len(result) == 1
    r = result[0]
    assert r["order_id"] == "6511942172741"
    assert isinstance(r["customer_tags"], str)
    assert json.loads(r["customer_tags"]) == ["CartSee", "member"]
    assert r["is_new_customer"] == 0
    assert r["gross_sales"] == 97.64


def test_transform_ai_visibility_empty():
    """ai_visibility_table 无数据时返回空列表。"""
    assert _transform_ai_visibility_table([]) == []


def test_transform_ai_visibility_wraps_row():
    """ai_visibility_table 有数据时将整行序列化为 data 字段。"""
    rows = [{"event_date": "2026-04-10", "score": 0.95}]
    result = _transform_ai_visibility_table(rows)
    assert len(result) == 1
    assert result[0]["event_date"] == "2026-04-10"
    data = json.loads(result[0]["data"])
    assert data["score"] == 0.95


# ---------------------------------------------------------------------------
# _resolve_date_range 测试
# ---------------------------------------------------------------------------

@patch("collectors.tw_collector.get_watermark")
def test_resolve_date_range_full_mode(mock_get_wm):
    """full 模式时，period_start = TABLE_EARLIEST_DATES[table]。"""
    start, end = _resolve_date_range("pixel_orders_table", "full", None, "2026-04-15")
    assert start == TABLE_EARLIEST_DATES["pixel_orders_table"]
    assert end == "2026-04-15"
    mock_get_wm.assert_not_called()


@patch("collectors.tw_collector.get_watermark")
def test_resolve_date_range_no_watermark(mock_get_wm):
    """incremental 模式且无水位线时，触发全量（返回最早日期）。"""
    mock_get_wm.return_value = None
    start, end = _resolve_date_range("sessions_table", "incremental", None, "2026-04-15")
    assert start == TABLE_EARLIEST_DATES["sessions_table"]
    assert end == "2026-04-15"


@patch("collectors.tw_collector.get_watermark")
def test_resolve_date_range_with_watermark(mock_get_wm):
    """incremental 模式且有水位线时，从水位线时间开始。"""
    mock_get_wm.return_value = {
        "last_success_time": datetime(2026, 4, 10),
        "run_mode": "incremental",
    }
    start, end = _resolve_date_range("pixel_orders_table", "incremental", None, "2026-04-15")
    assert start == "2026-04-10"
    assert end == "2026-04-15"


def test_resolve_date_range_explicit_start():
    """显式指定 start_date 时，不查水位线，直接使用传入值。"""
    with patch("collectors.tw_collector.get_watermark") as mock_get_wm:
        start, end = _resolve_date_range(
            "ads_table", "incremental", "2026-03-01", "2026-04-01"
        )
        assert start == "2026-03-01"
        assert end == "2026-04-01"
        mock_get_wm.assert_not_called()


# ---------------------------------------------------------------------------
# collect_table 测试（mock SDK + DB）
# ---------------------------------------------------------------------------

def _make_mock_conn():
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


@patch("collectors.tw_collector.update_watermark")
@patch("collectors.tw_collector.get_watermark")
@patch("collectors.tw_collector.write_to_doris")
@patch("collectors.tw_collector.TripleWhaleClient")
def test_collect_table_incremental(
    mock_client_cls, mock_write, mock_get_wm, mock_update_wm, monkeypatch
):
    """增量模式：从水位线时间拉取，写入后更新水位线。"""
    monkeypatch.setenv("TRIPLEWHALE_API_KEY", "test_key")
    mock_get_wm.return_value = {
        "last_success_time": datetime(2026, 4, 10),
        "run_mode": "incremental",
    }
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.execute_sql.return_value = [
        {"comment_id": "c001", "channel": "meta-analytics", "comment_text": "Good!",
         "created_at": "2026-04-11 10:00:00"}
    ]
    mock_write.return_value = 1

    result = collect_table(
        "social_media_comments_table", mode="incremental", end_date="2026-04-15"
    )

    assert result == 1
    mock_write.assert_called_once()
    # 水位线应以 end_date 更新
    mock_update_wm.assert_called_once()
    args = mock_update_wm.call_args[0]
    assert args[0] == SOURCE
    assert args[1] == "social_media_comments_table"


@patch("collectors.tw_collector.update_watermark")
@patch("collectors.tw_collector.get_watermark")
@patch("collectors.tw_collector.write_to_doris")
@patch("collectors.tw_collector.TripleWhaleClient")
def test_collect_table_full_no_watermark(
    mock_client_cls, mock_write, mock_get_wm, mock_update_wm, monkeypatch
):
    """无水位线时触发全量，period_start = TABLE_EARLIEST_DATES[table]。"""
    monkeypatch.setenv("TRIPLEWHALE_API_KEY", "test_key")
    mock_get_wm.return_value = None
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.execute_sql.return_value = [
        {"event_date": "2026-04-10", "page_id": "p001", "channel": "meta-analytics",
         "fan_adds": 10.0}
    ]
    mock_write.return_value = 1

    collect_table("social_media_pages_table", mode="incremental", end_date="2026-04-15")

    call_args = mock_client.execute_sql.call_args
    assert call_args[0][1] == TABLE_EARLIEST_DATES["social_media_pages_table"]


@patch("collectors.tw_collector.update_watermark")
@patch("collectors.tw_collector.get_watermark")
@patch("collectors.tw_collector.write_to_doris")
@patch("collectors.tw_collector.TripleWhaleClient")
def test_collect_table_no_rows(
    mock_client_cls, mock_write, mock_get_wm, mock_update_wm, monkeypatch
):
    """API 返回空数据时，write_to_doris 不被调用，返回 0。"""
    monkeypatch.setenv("TRIPLEWHALE_API_KEY", "test_key")
    mock_get_wm.return_value = {"last_success_time": datetime(2026, 4, 10)}
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.execute_sql.return_value = []

    result = collect_table("creatives_table", mode="incremental", end_date="2026-04-15")

    assert result == 0
    mock_write.assert_not_called()


# ---------------------------------------------------------------------------
# collect_all 测试
# ---------------------------------------------------------------------------

@patch("collectors.tw_collector.collect_table")
def test_collect_all_single_failure(mock_collect):
    """一张表失败不影响其他表：失败表值为 -1，其他表正常。"""
    def side_effect(table_name, **kwargs):
        if table_name == "sessions_table":
            raise RuntimeError("API 超时")
        return 5

    mock_collect.side_effect = side_effect

    results = collect_all(mode="incremental")

    assert results["sessions_table"] == -1
    for tbl in ALL_TABLES:
        if tbl != "sessions_table":
            assert results[tbl] == 5


@patch("collectors.tw_collector.collect_table")
def test_collect_all_returns_all_tables(mock_collect):
    """collect_all 应返回全部 10 张表的结果。"""
    mock_collect.return_value = 0
    results = collect_all()
    assert set(results.keys()) == set(ALL_TABLES)
    assert len(results) == 10


# ---------------------------------------------------------------------------
# API Key 缺失测试
# ---------------------------------------------------------------------------

def test_missing_api_key():
    """TRIPLEWHALE_API_KEY 未配置时，_get_client() 抛 RuntimeError。"""
    from collectors.tw_collector import _get_client
    original = os.environ.pop("TRIPLEWHALE_API_KEY", None)
    try:
        with pytest.raises(RuntimeError, match="TRIPLEWHALE_API_KEY"):
            _get_client()
    finally:
        if original is not None:
            os.environ["TRIPLEWHALE_API_KEY"] = original


def test_missing_api_key_on_collect():
    """collect_table 在 API Key 缺失时抛 RuntimeError，不执行任何 DB 操作。"""
    original = os.environ.pop("TRIPLEWHALE_API_KEY", None)
    try:
        with pytest.raises(RuntimeError, match="TRIPLEWHALE_API_KEY"):
            collect_table("ads_table")
    finally:
        if original is not None:
            os.environ["TRIPLEWHALE_API_KEY"] = original
