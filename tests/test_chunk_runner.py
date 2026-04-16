"""
tests/test_chunk_runner.py

单元测试：bi/python_sdk/outdoor_collector/common/chunk_runner.py
使用 mock pymysql / mock 内部函数，不依赖真实 Doris 连接。
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

from common.chunk_runner import (  # noqa: E402
    ensure_chunk_table,
    _generate_chunks,
    _get_done_chunks,
    _set_chunk_status,
    chunked_fetch,
    CHUNK_STATUS_TABLE,
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
# Test 1：ensure_chunk_table — CREATE TABLE IF NOT EXISTS 被执行
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_ensure_chunk_table(mock_connect):
    """ensure_chunk_table 应执行 CREATE TABLE IF NOT EXISTS。"""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_connect.return_value = mock_conn

    ensure_chunk_table()

    mock_cursor.execute.assert_called_once()
    sql_arg = mock_cursor.execute.call_args[0][0]
    assert "CREATE TABLE IF NOT EXISTS" in sql_arg.upper()
    assert "etl_chunk_status" in sql_arg
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2：ensure_chunk_table — 连接失败抛出 RuntimeError
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_ensure_chunk_table_connection_failure(mock_connect):
    """pymysql.connect 抛出异常时，ensure_chunk_table 应抛出 RuntimeError。"""
    mock_connect.side_effect = Exception("connection refused")

    with pytest.raises(RuntimeError, match="建表失败"):
        ensure_chunk_table()


# ---------------------------------------------------------------------------
# Test 3：_generate_chunks — 整除情况（30天/30天 → 1片）
# ---------------------------------------------------------------------------

def test_generate_chunks_even():
    """整除情况：[2026-01-01, 2026-01-31) 按 30 天 → 1 片。"""
    start = datetime(2026, 1, 1)
    end = datetime(2026, 1, 31)
    chunks = _generate_chunks(start, end, 30)

    assert len(chunks) == 1
    assert chunks[0][0] == start
    assert chunks[0][1] == end


# ---------------------------------------------------------------------------
# Test 4：_generate_chunks — 余数情况（50天/30天 → 2片）
# ---------------------------------------------------------------------------

def test_generate_chunks_remainder():
    """余数情况：50 天按 30 天分片 → 2 片，最后 1 片 20 天。"""
    from datetime import timedelta
    start = datetime(2026, 1, 1)
    end = start + timedelta(days=50)
    chunks = _generate_chunks(start, end, 30)

    assert len(chunks) == 2
    assert chunks[0] == (start, start + timedelta(days=30))
    assert chunks[1] == (start + timedelta(days=30), end)


# ---------------------------------------------------------------------------
# Test 5：_generate_chunks — start >= end 返回空列表
# ---------------------------------------------------------------------------

def test_generate_chunks_empty():
    """start >= end 时返回空列表。"""
    start = datetime(2026, 1, 10)
    end = datetime(2026, 1, 1)
    assert _generate_chunks(start, end, 30) == []

    # start == end 也返回空
    assert _generate_chunks(start, start, 30) == []


# ---------------------------------------------------------------------------
# Test 6：chunked_fetch — done 分片被跳过（不调用 fetch_fn）
# ---------------------------------------------------------------------------

@patch("common.chunk_runner._set_chunk_status")
@patch("common.chunk_runner._get_done_chunks")
@patch("common.chunk_runner.ensure_chunk_table")
def test_chunked_fetch_skips_done(mock_ensure, mock_get_done, mock_set_status):
    """done 分片不应调用 fetch_fn。"""
    from datetime import timedelta
    start = datetime(2026, 1, 1)
    end = datetime(2026, 3, 2)  # 60 天 → 2 片（30天各一片）

    # 第一片已经 done
    chunk1_start = start
    chunk1_end = start + timedelta(days=30)
    mock_get_done.return_value = {(chunk1_start, chunk1_end)}

    fetch_fn = MagicMock()

    chunked_fetch("triplewhale", "sessions_table", fetch_fn, start, end, chunk_days=30, workers=1)

    # fetch_fn 只被调用 1 次（第二片）
    assert fetch_fn.call_count == 1
    called_args = fetch_fn.call_args[0]
    assert called_args[0] == chunk1_end  # 第二片起始


# ---------------------------------------------------------------------------
# Test 7：chunked_fetch — 全部成功时所有分片标记 done
# ---------------------------------------------------------------------------

@patch("common.chunk_runner._set_chunk_status")
@patch("common.chunk_runner._get_done_chunks")
@patch("common.chunk_runner.ensure_chunk_table")
def test_chunked_fetch_all_success(mock_ensure, mock_get_done, mock_set_status):
    """全部 fetch_fn 成功 → 所有分片标记 done，无异常。"""
    from datetime import timedelta
    start = datetime(2026, 1, 1)
    end = start + timedelta(days=30)

    mock_get_done.return_value = set()
    fetch_fn = MagicMock()  # 不抛出异常

    chunked_fetch("triplewhale", "sessions_table", fetch_fn, start, end, chunk_days=30, workers=1)

    fetch_fn.assert_called_once_with(start, end)

    # _set_chunk_status 应先 pending 后 done
    status_calls = [c[0][4] for c in mock_set_status.call_args_list]
    assert "pending" in status_calls
    assert "done" in status_calls
    assert "failed" not in status_calls


# ---------------------------------------------------------------------------
# Test 8：chunked_fetch — fetch_fn 异常时分片标记 failed，不中断其他分片
# ---------------------------------------------------------------------------

@patch("common.chunk_runner._set_chunk_status")
@patch("common.chunk_runner._get_done_chunks")
@patch("common.chunk_runner.ensure_chunk_table")
def test_chunked_fetch_partial_failure(mock_ensure, mock_get_done, mock_set_status):
    """1 片失败 → 标记 failed，其余继续执行，最终抛 RuntimeError。"""
    from datetime import timedelta
    start = datetime(2026, 1, 1)
    end = start + timedelta(days=60)  # 2 片

    mock_get_done.return_value = set()

    call_count = [0]

    def fetch_fn(cs, ce):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("API timeout")
        # 第二次调用成功

    with pytest.raises(RuntimeError, match="1 个分片失败"):
        chunked_fetch("triplewhale", "sessions_table", fetch_fn, start, end, chunk_days=30, workers=2)

    assert call_count[0] == 2  # 两片都被尝试执行
    status_calls = [c[0][4] for c in mock_set_status.call_args_list]
    assert "failed" in status_calls
    assert "done" in status_calls


# ---------------------------------------------------------------------------
# Test 9：chunked_fetch — workers 参数控制并发数
# ---------------------------------------------------------------------------

@patch("common.chunk_runner.ThreadPoolExecutor")
@patch("common.chunk_runner._set_chunk_status")
@patch("common.chunk_runner._get_done_chunks")
@patch("common.chunk_runner.ensure_chunk_table")
def test_chunked_fetch_workers(mock_ensure, mock_get_done, mock_set_status, mock_executor_cls):
    """chunked_fetch 应将 workers 参数传给 ThreadPoolExecutor。"""
    from datetime import timedelta
    start = datetime(2026, 1, 1)
    end = start + timedelta(days=30)

    mock_get_done.return_value = set()

    # 配置 mock executor 正常完成
    mock_executor = MagicMock()
    mock_executor.__enter__ = lambda s: mock_executor
    mock_executor.__exit__ = MagicMock(return_value=False)
    mock_executor_cls.return_value = mock_executor

    # submit 返回 mock future
    mock_future = MagicMock()
    mock_future.result.return_value = (start, end, True, "")
    mock_executor.submit.return_value = mock_future

    # as_completed 直接 yield mock_future
    with patch("common.chunk_runner.as_completed", return_value=[mock_future]):
        fetch_fn = MagicMock()
        chunked_fetch(
            "triplewhale", "sessions_table", fetch_fn,
            start, end, chunk_days=30, workers=8
        )

    mock_executor_cls.assert_called_once_with(max_workers=8)
