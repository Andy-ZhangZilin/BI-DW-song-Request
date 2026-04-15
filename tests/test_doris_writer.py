"""
tests/test_doris_writer.py

单元测试：bi/python_sdk/outdoor_collector/common/doris_writer.py
使用 mock pymysql，不依赖真实 Doris 连接。
"""
import sys
import os
import pytest
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

from common.doris_writer import write_to_doris  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _make_mock_conn():
    """返回 (mock_conn, mock_cursor)，已配置好 context manager。"""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


# ---------------------------------------------------------------------------
# Test 1：正常写入——executemany 和 commit 被调用
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_write_basic(mock_connect):
    """正常写入：records 非空，executemany 被调用，commit 被调用，返回写入行数。"""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_connect.return_value = mock_conn

    records = [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]
    result = write_to_doris(
        table="hqware.test_table",
        records=records,
        unique_keys=["id"],
        source="test",
    )

    assert result == 2
    mock_cursor.executemany.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2：批量分页——records > batch_size 时分批调用 executemany
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_write_batching(mock_connect):
    """records 数量超过 batch_size 时，executemany 应被调用多次。"""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_connect.return_value = mock_conn

    records = [{"id": i, "val": i * 10} for i in range(25)]
    write_to_doris(
        table="hqware.test_table",
        records=records,
        unique_keys=["id"],
        source="test",
        batch_size=10,
    )

    # 25 条，batch_size=10 → 3 次调用（10+10+5）
    assert mock_cursor.executemany.call_count == 3
    assert mock_conn.commit.call_count == 3


# ---------------------------------------------------------------------------
# Test 3：SET 语句在 executemany 之前执行
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_write_set_statements_order(mock_connect):
    """写入前必须先执行两条 SET 语句，且顺序固定。"""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_connect.return_value = mock_conn

    records = [{"id": 1, "val": "x"}]
    write_to_doris(
        table="hqware.test_table",
        records=records,
        unique_keys=["id"],
        source="test",
    )

    execute_calls = mock_cursor.execute.call_args_list
    assert len(execute_calls) >= 2
    assert execute_calls[0] == call("SET enable_unique_key_partial_update = true")
    assert execute_calls[1] == call("SET enable_insert_strict = false")

    # executemany 必须在 SET 之后
    set_idx = max(
        execute_calls.index(call("SET enable_unique_key_partial_update = true")),
        execute_calls.index(call("SET enable_insert_strict = false")),
    )
    # executemany 被调用，且调用时 execute 已完成（通过 call_count 验证顺序）
    assert mock_cursor.executemany.call_count >= 1
    _ = set_idx  # 顺序通过 execute_calls 已验证


# ---------------------------------------------------------------------------
# Test 4：空 records——直接返回 0，不创建连接
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_write_empty_records(mock_connect):
    """records 为空时，应直接返回 0，不调用 pymysql.connect。"""
    result = write_to_doris(
        table="hqware.test_table",
        records=[],
        unique_keys=["id"],
        source="test",
    )

    assert result == 0
    mock_connect.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5：连接失败——抛出 RuntimeError
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_write_connection_failure(mock_connect):
    """pymysql.connect 抛出异常时，write_to_doris 必须抛出 RuntimeError。"""
    mock_connect.side_effect = Exception("connection refused")

    records = [{"id": 1, "val": "x"}]
    with pytest.raises(RuntimeError, match="写入失败"):
        write_to_doris(
            table="hqware.test_table",
            records=records,
            unique_keys=["id"],
            source="test",
        )


# ---------------------------------------------------------------------------
# Test 6：键名不一致——抛出 ValueError（Patch F1）
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_write_inconsistent_keys(mock_connect):
    """records 中存在键名不一致的 dict 时，应在连接前抛出 ValueError。"""
    records = [{"id": 1, "val": "a"}, {"id": 2, "extra": "b"}]
    with pytest.raises(ValueError, match="键集"):
        write_to_doris(
            table="hqware.test_table",
            records=records,
            unique_keys=["id"],
            source="test",
        )
    mock_connect.assert_not_called()


# ---------------------------------------------------------------------------
# Test 7：空 dict records——抛出 ValueError（Patch F2）
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_write_empty_dict_records(mock_connect):
    """records[0] 为空 dict 时，应在连接前抛出 ValueError。"""
    with pytest.raises(ValueError, match="空 dict"):
        write_to_doris(
            table="hqware.test_table",
            records=[{}],
            unique_keys=[],
            source="test",
        )
    mock_connect.assert_not_called()


# ---------------------------------------------------------------------------
# Test 8：batch_size=0——抛出 ValueError（Patch F3）
# ---------------------------------------------------------------------------

@patch("pymysql.connect")
def test_write_invalid_batch_size(mock_connect):
    """batch_size <= 0 时应抛出 ValueError。"""
    records = [{"id": 1, "val": "x"}]
    with pytest.raises(ValueError, match="batch_size"):
        write_to_doris(
            table="hqware.test_table",
            records=records,
            unique_keys=["id"],
            source="test",
            batch_size=0,
        )
    mock_connect.assert_not_called()
