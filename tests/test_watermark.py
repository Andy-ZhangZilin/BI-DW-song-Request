"""
tests/test_watermark.py

单元测试：bi/python_sdk/outdoor_collector/common/watermark.py
使用 mock pymysql，不依赖真实 Doris 连接。
"""
import sys
import os
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, call

# 将 outdoor_collector 根目录加入 sys.path，以便 import doris_config
_OUTDOOR_COLLECTOR_ROOT = os.path.join(
    os.path.dirname(__file__),
    "..",
    "bi",
    "python_sdk",
    "outdoor_collector",
)
sys.path.insert(0, _OUTDOOR_COLLECTOR_ROOT)

from common.watermark import (  # noqa: E402
    ensure_table,
    get_watermark,
    update_watermark,
    reset_watermark,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_mock_conn():
    """返回 (mock_conn, mock_cursor)，已配置好 context manager。"""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


# ---------------------------------------------------------------------------
# Test 1：ensure_table — CREATE TABLE IF NOT EXISTS 被执行
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_ensure_table(mock_connect):
    """ensure_table 应执行 CREATE TABLE IF NOT EXISTS。"""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_connect.return_value = mock_conn

    ensure_table()

    mock_cursor.execute.assert_called_once()
    sql_arg = mock_cursor.execute.call_args[0][0]
    assert "CREATE TABLE IF NOT EXISTS" in sql_arg.upper()
    assert "etl_watermark" in sql_arg
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2：ensure_table — 连接失败抛出 RuntimeError
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_ensure_table_connection_failure(mock_connect):
    """pymysql.connect 抛出异常时，ensure_table 应抛出 RuntimeError。"""
    mock_connect.side_effect = Exception("connection refused")

    with pytest.raises(RuntimeError, match="建表失败"):
        ensure_table()


# ---------------------------------------------------------------------------
# Test 3：get_watermark — 无记录返回 None（首次运行）
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_get_watermark_no_record(mock_connect):
    """首次运行，查无记录 → 返回 None。"""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_connect.return_value = mock_conn
    mock_cursor.fetchone.return_value = None

    result = get_watermark("triplewhale", "pixel_orders_table")

    assert result is None
    mock_cursor.execute.assert_called_once()
    sql_arg = mock_cursor.execute.call_args[0][0]
    assert "etl_watermark" in sql_arg
    mock_conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# Test 4：get_watermark — 有记录返回 dict
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_get_watermark_with_record(mock_connect):
    """有历史记录 → 返回含 last_success_time 的 dict。"""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_connect.return_value = mock_conn
    expected = {
        "source": "triplewhale",
        "table_name": "pixel_orders_table",
        "last_success_time": datetime(2026, 4, 10),
        "run_mode": "incremental",
        "updated_at": datetime(2026, 4, 10, 12, 0, 0),
    }
    mock_cursor.fetchone.return_value = expected

    result = get_watermark("triplewhale", "pixel_orders_table")

    assert result == expected
    assert result["last_success_time"] == datetime(2026, 4, 10)
    mock_conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# Test 5：get_watermark — 连接失败抛出 RuntimeError
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_get_watermark_connection_failure(mock_connect):
    """连接失败时 get_watermark 应抛出 RuntimeError。"""
    mock_connect.side_effect = Exception("timeout")

    with pytest.raises(RuntimeError, match="查询失败"):
        get_watermark("triplewhale", "pixel_orders_table")


# ---------------------------------------------------------------------------
# Test 6：update_watermark — 无历史记录，run_mode="full"
# ---------------------------------------------------------------------------

@patch("common.watermark.write_to_doris")
@patch("common.watermark.get_watermark")
def test_update_watermark_first_run(mock_get, mock_write):
    """首次运行（get_watermark 返回 None）→ run_mode 应为 "full"。"""
    mock_get.return_value = None
    success_time = datetime(2026, 4, 15, 10, 0, 0)

    update_watermark("triplewhale", "pixel_orders_table", success_time)

    mock_write.assert_called_once()
    call_kwargs = mock_write.call_args
    records = call_kwargs[1]["records"] if call_kwargs[1] else call_kwargs[0][1]
    assert records[0]["run_mode"] == "full"
    assert records[0]["last_success_time"] == success_time
    assert records[0]["source"] == "triplewhale"
    assert records[0]["table_name"] == "pixel_orders_table"


# ---------------------------------------------------------------------------
# Test 7：update_watermark — 有历史记录，run_mode="incremental"
# ---------------------------------------------------------------------------

@patch("common.watermark.write_to_doris")
@patch("common.watermark.get_watermark")
def test_update_watermark_incremental(mock_get, mock_write):
    """有历史记录（get_watermark 返回 dict）→ run_mode 应为 "incremental"。"""
    mock_get.return_value = {
        "source": "triplewhale",
        "table_name": "pixel_orders_table",
        "last_success_time": datetime(2026, 4, 10),
        "run_mode": "incremental",
        "updated_at": datetime(2026, 4, 10, 12, 0, 0),
    }
    success_time = datetime(2026, 4, 15, 10, 0, 0)

    update_watermark("triplewhale", "pixel_orders_table", success_time)

    mock_write.assert_called_once()
    call_kwargs = mock_write.call_args
    records = call_kwargs[1]["records"] if call_kwargs[1] else call_kwargs[0][1]
    assert records[0]["run_mode"] == "incremental"
    assert records[0]["last_success_time"] == success_time


# ---------------------------------------------------------------------------
# Test 8：update_watermark — write_to_doris 参数正确
# ---------------------------------------------------------------------------

@patch("common.watermark.write_to_doris")
@patch("common.watermark.get_watermark")
def test_update_watermark_write_params(mock_get, mock_write):
    """update_watermark 调用 write_to_doris 时必须传入正确的 table 和 unique_keys。"""
    mock_get.return_value = None
    success_time = datetime(2026, 4, 15)

    update_watermark("tiktok", "orders", success_time)

    _, kwargs = mock_write.call_args
    assert kwargs["table"] == "hqware.etl_watermark"
    assert kwargs["unique_keys"] == ["source", "table_name"]


# ---------------------------------------------------------------------------
# Test 9：reset_watermark — DELETE 被执行
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_reset_watermark(mock_connect):
    """reset_watermark 应执行 DELETE 语句并 commit。"""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_connect.return_value = mock_conn

    reset_watermark("triplewhale", "pixel_orders_table")

    mock_cursor.execute.assert_called_once()
    sql_arg = mock_cursor.execute.call_args[0][0]
    assert "DELETE" in sql_arg.upper()
    assert "etl_watermark" in sql_arg
    params = mock_cursor.execute.call_args[0][1]
    assert params == ("triplewhale", "pixel_orders_table")
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# Test 10：reset_watermark — 连接失败抛出 RuntimeError
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_reset_watermark_connection_failure(mock_connect):
    """连接失败时 reset_watermark 应抛出 RuntimeError。"""
    mock_connect.side_effect = Exception("connection refused")

    with pytest.raises(RuntimeError, match="重置失败"):
        reset_watermark("triplewhale", "pixel_orders_table")
