"""tests/test_triplewhale.py — TripleWhale 数据源模块单元测试

使用 mock_credentials fixture（conftest.py）确保无需真实 API Key。
所有网络请求通过 unittest.mock.patch 替换，不发起真实 HTTP 请求。
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import requests as req_lib

import sources.triplewhale as triplewhale
from sources.triplewhale import (
    authenticate,
    fetch_sample,
    extract_fields,
    fetch_data_profile,
    _infer_type,
    _fetch_table,
    _fetch_earliest_date,
    _fetch_row_count,
    _run_sql_query,
    TABLES,
    SHOP_DOMAIN,
    DEFAULT_TIMEOUT,
    RATE_LIMIT_RPM,
    MAX_ROWS_PER_REQUEST,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "triplewhale_sample.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tw_sample() -> dict:
    """加载 triplewhale fixture 数据。"""
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def orders_sample(tw_sample) -> list[dict]:
    """pixel_orders_table 的 data 列表（用于 extract_fields 逻辑测试）。"""
    return tw_sample["pixel_orders_table"]["data"]


@pytest.fixture
def joined_sample(tw_sample) -> list[dict]:
    """pixel_joined_tvf 的 data 列表。"""
    return tw_sample["pixel_joined_tvf"]["data"]


# ---------------------------------------------------------------------------
# authenticate() 测试
# ---------------------------------------------------------------------------

class TestAuthenticate:
    def test_success_http_200(self, mock_credentials):
        """HTTP 200 → 返回 True，日志含"成功"。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            result = authenticate()
        assert result is True

    def test_failure_http_400(self, mock_credentials):
        """HTTP 400 → 返回 False（summary-page 端点参数错误视为失败）。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=400, text="Bad Request")
            result = authenticate()
        assert result is False

    def test_failure_http_401(self, mock_credentials):
        """HTTP 401 → 返回 False，不抛出异常。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=401, text="Unauthorized")
            result = authenticate()
        assert result is False

    def test_failure_http_403(self, mock_credentials):
        """HTTP 403 → 返回 False。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=403, text="Forbidden")
            result = authenticate()
        assert result is False

    def test_timeout_returns_false(self, mock_credentials):
        """请求超时 → 返回 False，不抛出未处理异常。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.side_effect = req_lib.Timeout()
            result = authenticate()
        assert result is False

    def test_network_error_returns_false(self, mock_credentials):
        """网络错误（ConnectionError）→ 返回 False。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.side_effect = req_lib.ConnectionError("Network unreachable")
            result = authenticate()
        assert result is False

    def test_uses_api_key_header(self, mock_credentials):
        """请求必须使用 x-api-key header 携带 API Key（小写，HTTP/2 兼容）。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            authenticate()
        call_kwargs = mock_post.call_args[1]
        assert "x-api-key" in call_kwargs["headers"]
        assert call_kwargs["headers"]["x-api-key"] == "test_tw_key"

    def test_uses_shop_domain_in_body(self, mock_credentials):
        """请求 body 必须包含 shopDomain=piscifun.myshopify.com。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            authenticate()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["shopDomain"] == SHOP_DOMAIN

    def test_uses_timeout(self, mock_credentials):
        """请求必须设置 timeout=30。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            authenticate()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["timeout"] == DEFAULT_TIMEOUT


# ---------------------------------------------------------------------------
# fetch_sample() 测试
# ---------------------------------------------------------------------------

class TestFetchSample:
    def test_default_table_is_pixel_orders(self, mock_credentials, orders_sample):
        """table_name=None → 使用 pixel_orders_table，结果受 MAX_SAMPLE_ROWS 截断。"""
        with patch("sources.triplewhale._fetch_table") as mock_fetch:
            mock_fetch.return_value = orders_sample
            result = fetch_sample(None)
        mock_fetch.assert_called_once()
        assert mock_fetch.call_args[0][0] == "pixel_orders_table"
        assert result == orders_sample[:triplewhale.MAX_SAMPLE_ROWS]

    def test_explicit_table_name(self, mock_credentials, joined_sample):
        """显式指定 table_name → 使用该表。"""
        with patch("sources.triplewhale._fetch_table") as mock_fetch:
            mock_fetch.return_value = joined_sample
            result = fetch_sample("pixel_joined_tvf")
        mock_fetch.assert_called_once()
        assert mock_fetch.call_args[0][0] == "pixel_joined_tvf"

    def test_all_valid_tables_accepted(self, mock_credentials, orders_sample):
        """TABLES 中所有表名均可接受，不抛出异常。"""
        for table in TABLES:
            with patch("sources.triplewhale._fetch_table") as mock_fetch:
                mock_fetch.return_value = orders_sample
                fetch_sample(table)  # 不应抛出异常

    def test_invalid_table_raises_value_error(self, mock_credentials):
        """未知表名 → 抛出 ValueError，错误信息包含表名。"""
        with pytest.raises(ValueError, match="未知表名"):
            fetch_sample("nonexistent_table")

    def test_returns_list_of_dicts(self, mock_credentials, orders_sample):
        """返回值类型为 list[dict]。"""
        with patch("sources.triplewhale._fetch_table") as mock_fetch:
            mock_fetch.return_value = orders_sample
            result = fetch_sample("pixel_orders_table")
        assert isinstance(result, list)
        assert all(isinstance(r, dict) for r in result)


# ---------------------------------------------------------------------------
# extract_fields() 测试
# ---------------------------------------------------------------------------

class TestExtractFields:
    def test_returns_fieldinfo_structure(self, orders_sample):
        """返回值符合 FieldInfo 四字段结构。"""
        fields = extract_fields(orders_sample)
        assert len(fields) > 0
        for f in fields:
            assert "field_name" in f, f"缺少 field_name: {f}"
            assert "data_type" in f, f"缺少 data_type: {f}"
            assert "sample_value" in f, f"缺少 sample_value: {f}"
            assert "nullable" in f, f"缺少 nullable: {f}"
            assert isinstance(f["nullable"], bool)
            assert f["data_type"] in (
                "string", "number", "boolean", "array", "object", "null"
            ), f"未知 data_type: {f['data_type']}"

    def test_nullable_detection_null_first_record(self, orders_sample):
        """refund_amount 首条记录为 null → nullable=True。"""
        # 验证 fixture：第一条 refund_amount 为 null
        assert orders_sample[0]["refund_amount"] is None
        fields = extract_fields(orders_sample)
        refund_field = next(
            (f for f in fields if f["field_name"] == "refund_amount"), None
        )
        assert refund_field is not None
        assert refund_field["nullable"] is True

    def test_nullable_false_when_no_nulls(self, orders_sample):
        """order_id 在所有记录中非 null → nullable=False。"""
        fields = extract_fields(orders_sample)
        order_id_field = next(
            (f for f in fields if f["field_name"] == "order_id"), None
        )
        assert order_id_field is not None
        assert order_id_field["nullable"] is False

    def test_data_type_string(self, orders_sample):
        """order_id 字段类型应为 string。"""
        fields = extract_fields(orders_sample)
        field = next(f for f in fields if f["field_name"] == "order_id")
        assert field["data_type"] == "string"

    def test_data_type_number(self, orders_sample):
        """total_price 字段类型应为 number。"""
        fields = extract_fields(orders_sample)
        field = next(f for f in fields if f["field_name"] == "total_price")
        assert field["data_type"] == "number"

    def test_data_type_boolean(self, orders_sample):
        """is_first_order 字段类型应为 boolean。"""
        fields = extract_fields(orders_sample)
        field = next(f for f in fields if f["field_name"] == "is_first_order")
        assert field["data_type"] == "boolean"

    def test_data_type_array(self, orders_sample):
        """line_items 字段类型应为 array。"""
        fields = extract_fields(orders_sample)
        field = next(f for f in fields if f["field_name"] == "line_items")
        assert field["data_type"] == "array"

    def test_data_type_object(self, orders_sample):
        """metadata 字段类型应为 object。"""
        fields = extract_fields(orders_sample)
        field = next(f for f in fields if f["field_name"] == "metadata")
        assert field["data_type"] == "object"

    def test_data_type_null_for_none_first_record(self, orders_sample):
        """refund_amount 首条为 null → data_type 为 null。"""
        assert orders_sample[0]["refund_amount"] is None
        fields = extract_fields(orders_sample)
        field = next(f for f in fields if f["field_name"] == "refund_amount")
        assert field["data_type"] == "null"

    def test_empty_sample_returns_empty_list(self):
        """空样本 → 返回空列表。"""
        assert extract_fields([]) == []

    def test_fields_sorted_alphabetically(self, orders_sample):
        """返回字段列表按字段名字母序排列。"""
        fields = extract_fields(orders_sample)
        names = [f["field_name"] for f in fields]
        assert names == sorted(names)

    def test_all_fields_discovered(self, orders_sample):
        """所有出现在样本中的字段均被提取。"""
        all_keys: set[str] = set()
        for record in orders_sample:
            all_keys.update(record.keys())
        fields = extract_fields(orders_sample)
        discovered_keys = {f["field_name"] for f in fields}
        assert discovered_keys == all_keys

    def test_sample_value_from_first_record(self, orders_sample):
        """sample_value 取自第一条记录。"""
        fields = extract_fields(orders_sample)
        order_id_field = next(f for f in fields if f["field_name"] == "order_id")
        assert order_id_field["sample_value"] == orders_sample[0]["order_id"]

    def test_nullable_from_partial_null(self, orders_sample):
        """refund_amount：首条 null，第二条有值 → nullable=True。"""
        assert orders_sample[0]["refund_amount"] is None
        assert orders_sample[1]["refund_amount"] is not None
        fields = extract_fields(orders_sample)
        field = next(f for f in fields if f["field_name"] == "refund_amount")
        assert field["nullable"] is True


# ---------------------------------------------------------------------------
# _infer_type() 测试
# ---------------------------------------------------------------------------

class TestInferType:
    def test_none_returns_null(self):
        assert _infer_type(None) == "null"

    def test_bool_true_returns_boolean(self):
        assert _infer_type(True) == "boolean"

    def test_bool_false_returns_boolean(self):
        assert _infer_type(False) == "boolean"

    def test_int_returns_number(self):
        assert _infer_type(42) == "number"

    def test_float_returns_number(self):
        assert _infer_type(3.14) == "number"

    def test_str_returns_string(self):
        assert _infer_type("hello") == "string"

    def test_list_returns_array(self):
        assert _infer_type([1, 2, 3]) == "array"

    def test_dict_returns_object(self):
        assert _infer_type({"key": "val"}) == "object"

    def test_zero_returns_number(self):
        """0 是数字，不是 falsy null。"""
        assert _infer_type(0) == "number"

    def test_empty_string_returns_string(self):
        """空字符串是字符串，不是 null。"""
        assert _infer_type("") == "string"

    def test_bool_not_confused_with_number(self):
        """bool 是 int 子类，必须先判断 bool 再判断 int。"""
        assert _infer_type(True) == "boolean"
        assert _infer_type(1) == "number"


# ---------------------------------------------------------------------------
# _fetch_table() 测试
# ---------------------------------------------------------------------------

class TestFetchTable:
    def test_post_request_uses_shop_id(self, mock_credentials):
        """POST 请求 body 必须包含 shopId 字段（SQL 端点规范）。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=True,
                json=lambda: [{"order_id": "ORD-001"}],
            )
            _fetch_table("pixel_orders_table", "test_tw_key")
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["shopId"] == SHOP_DOMAIN

    def test_post_request_uses_api_key_header(self, mock_credentials):
        """POST 请求 header 必须包含 x-api-key（小写，HTTP/2 兼容）。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=True,
                json=lambda: [{"order_id": "ORD-001"}],
            )
            _fetch_table("pixel_orders_table", "test_tw_key")
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["x-api-key"] == "test_tw_key"

    def test_post_request_uses_timeout(self, mock_credentials):
        """POST 请求必须设置 timeout=30。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=True,
                json=lambda: [{"order_id": "ORD-001"}],
            )
            _fetch_table("pixel_orders_table", "test_tw_key")
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["timeout"] == DEFAULT_TIMEOUT

    def test_post_request_includes_sql_query(self, mock_credentials):
        """POST 请求 body 必须包含 query 字段，且包含表名。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=True,
                json=lambda: [{"order_id": "ORD-001"}],
            )
            _fetch_table("pixel_orders_table", "test_tw_key")
        call_kwargs = mock_post.call_args[1]
        assert "query" in call_kwargs["json"]
        assert "pixel_orders_table" in call_kwargs["json"]["query"]

    def test_post_request_includes_period(self, mock_credentials):
        """POST 请求 body 必须包含 period 字段（含 startDate/endDate）。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=True,
                json=lambda: [{"order_id": "ORD-001"}],
            )
            _fetch_table("pixel_orders_table", "test_tw_key")
        call_kwargs = mock_post.call_args[1]
        assert "period" in call_kwargs["json"]
        assert "startDate" in call_kwargs["json"]["period"]
        assert "endDate" in call_kwargs["json"]["period"]

    def test_response_list_returned_directly(self, mock_credentials):
        """响应为列表 → 直接返回该列表。"""
        expected = [{"order_id": "ORD-001", "total_price": 99.99}]
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=True,
                json=lambda: expected,
            )
            result = _fetch_table("pixel_orders_table", "test_tw_key")
        assert result == expected

    def test_empty_list_response_returned(self, mock_credentials):
        """响应为空列表（无数据）→ 返回空列表，不报错。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=True,
                json=lambda: [],
            )
            result = _fetch_table("ai_visibility_table", "test_tw_key")
        assert result == []

    def test_http_4xx_raises_runtime_error(self, mock_credentials):
        """HTTP 4xx（认证/权限错误）→ 抛出 RuntimeError。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=False, status_code=403, text="Forbidden"
            )
            with pytest.raises(RuntimeError, match="HTTP 403"):
                _fetch_table("pixel_orders_table", "test_tw_key")

    def test_http_5xx_returns_empty_list(self, mock_credentials):
        """HTTP 5xx（服务端错误，如表权限未开通）→ 返回空列表，不抛出异常。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=False, status_code=500, text="Error getting data"
            )
            result = _fetch_table("creatives_table", "test_tw_key")
        assert result == []

    def test_unknown_response_structure_raises_runtime_error(self, mock_credentials):
        """响应为 dict（非列表）→ 抛出 RuntimeError。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=True,
                json=lambda: {"unexpected_key": "value"},
            )
            with pytest.raises(RuntimeError, match="无法解析"):
                _fetch_table("pixel_orders_table", "test_tw_key")

    def test_timeout_propagates(self, mock_credentials):
        """请求超时 → 直接传播 Timeout 异常（由 fetch_sample 层处理）。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.side_effect = req_lib.Timeout()
            with pytest.raises(req_lib.Timeout):
                _fetch_table("pixel_orders_table", "test_tw_key")


# ---------------------------------------------------------------------------
# fetch_data_profile() 测试（Task 5）
# ---------------------------------------------------------------------------

class TestFetchDataProfile:
    def test_success_returns_correct_structure(self, mock_credentials):
        """AC8: 正常路径 → 返回含全部 7 个字段的字典，estimated_pull_minutes 计算正确。"""
        with (
            patch("sources.triplewhale._fetch_earliest_date", return_value="2024-01-15") as _,
            patch("sources.triplewhale._fetch_row_count", return_value=5000) as __,
        ):
            result = fetch_data_profile("pixel_orders_table")

        assert result["table_name"] == "pixel_orders_table"
        assert result["earliest_date"] == "2024-01-15"
        assert result["total_rows"] == 5000
        assert result["rate_limit_rpm"] == RATE_LIMIT_RPM
        assert result["max_rows_per_request"] == MAX_ROWS_PER_REQUEST
        assert result["date_column"] == "created_at"
        # estimated_pull_minutes = ceil(5000 / MAX_ROWS_PER_REQUEST) / RATE_LIMIT_RPM
        from math import ceil
        expected = ceil(5000 / MAX_ROWS_PER_REQUEST) / RATE_LIMIT_RPM
        assert result["estimated_pull_minutes"] == expected

    def test_no_data_returns_zero_rows_and_none(self, mock_credentials):
        """AC9: 无数据（COUNT=0）→ total_rows=0，earliest_date=None，estimated_pull_minutes=None。"""
        with (
            patch("sources.triplewhale._fetch_earliest_date", return_value=None),
            patch("sources.triplewhale._fetch_row_count", return_value=0),
        ):
            result = fetch_data_profile("creatives_table")

        assert result["total_rows"] == 0
        assert result["earliest_date"] is None
        assert result["estimated_pull_minutes"] is None

    def test_query_failure_returns_zero_rows(self, mock_credentials):
        """查询失败（_fetch_row_count 返回 None）→ total_rows=0，不传播异常。"""
        with (
            patch("sources.triplewhale._fetch_earliest_date", return_value=None),
            patch("sources.triplewhale._fetch_row_count", return_value=None),
        ):
            result = fetch_data_profile("ai_visibility_table")

        assert result["total_rows"] == 0
        assert result["estimated_pull_minutes"] is None

    def test_invalid_table_raises_value_error(self, mock_credentials):
        """未知表名 → 抛出 ValueError，不调用 SQL 查询。"""
        with pytest.raises(ValueError, match="未知表名"):
            fetch_data_profile("nonexistent_table")

    def test_contains_rate_limit_constants(self, mock_credentials):
        """返回字典必须包含 rate_limit_rpm 和 max_rows_per_request 常量值。"""
        with (
            patch("sources.triplewhale._fetch_earliest_date", return_value=None),
            patch("sources.triplewhale._fetch_row_count", return_value=0),
        ):
            result = fetch_data_profile("sessions_table")

        assert result["rate_limit_rpm"] == RATE_LIMIT_RPM
        assert result["max_rows_per_request"] == MAX_ROWS_PER_REQUEST

    def test_all_tables_accepted(self, mock_credentials):
        """TABLES 中所有表名均可接受，不抛出异常。"""
        for table in TABLES:
            with (
                patch("sources.triplewhale._fetch_earliest_date", return_value=None),
                patch("sources.triplewhale._fetch_row_count", return_value=0),
            ):
                result = fetch_data_profile(table)
            assert result["table_name"] == table


# ---------------------------------------------------------------------------
# _run_sql_query() 测试
# ---------------------------------------------------------------------------

class TestRunSqlQuery:
    def test_post_uses_sql_endpoint(self):
        """_run_sql_query 应向 SQL_URL 发送 POST 请求。"""
        from sources.triplewhale import SQL_URL
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, json=lambda: [{"total": 100}])
            _run_sql_query("SELECT COUNT(*) as total FROM pixel_orders_table", "test_key")
        assert mock_post.call_args[0][0] == SQL_URL

    def test_post_includes_query_in_payload(self):
        """payload 必须包含 query 字段。"""
        query = "SELECT MIN(created_at) as earliest FROM pixel_orders_table"
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, json=lambda: [])
            _run_sql_query(query, "test_key")
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["query"] == query

    def test_list_response_returned(self):
        """响应为列表 → 直接返回。"""
        expected = [{"earliest": "2024-01-01"}]
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, json=lambda: expected)
            result = _run_sql_query("SELECT MIN(date) as earliest FROM ads_table", "key")
        assert result == expected

    def test_dict_response_returns_empty(self):
        """响应为 dict（非列表）→ 返回空列表，不抛出异常。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, json=lambda: {"error": "unknown"})
            result = _run_sql_query("SELECT COUNT(*) as total FROM sessions_table", "key")
        assert result == []

    def test_5xx_returns_empty_list(self):
        """HTTP 5xx → 返回空列表，不抛出异常。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=False, status_code=503, text="Service Unavailable")
            result = _run_sql_query("SELECT COUNT(*) as total FROM ads_table", "key")
        assert result == []

    def test_4xx_raises_runtime_error(self):
        """HTTP 4xx → 抛出 RuntimeError。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=False, status_code=403, text="Forbidden")
            with pytest.raises(RuntimeError, match="SQL 查询失败"):
                _run_sql_query("SELECT COUNT(*) as total FROM pixel_orders_table", "key")


# ---------------------------------------------------------------------------
# _fetch_earliest_date() / _fetch_row_count() 测试
# ---------------------------------------------------------------------------

class TestFetchEarliestDate:
    def test_returns_date_string_on_success(self):
        """正常返回 → 日期字符串。"""
        with patch("sources.triplewhale._run_sql_query", return_value=[{"earliest": "2024-03-01"}]):
            result = _fetch_earliest_date("pixel_orders_table", "test_key")
        assert result == "2024-03-01"

    def test_returns_none_when_no_data(self):
        """无数据（earliest=None）→ 返回 None。"""
        with patch("sources.triplewhale._run_sql_query", return_value=[{"earliest": None}]):
            result = _fetch_earliest_date("pixel_orders_table", "test_key")
        assert result is None

    def test_returns_none_on_query_exception(self):
        """查询抛出异常 → 捕获，返回 None，不传播。"""
        with patch("sources.triplewhale._run_sql_query", side_effect=RuntimeError("error")):
            result = _fetch_earliest_date("sessions_table", "test_key")
        assert result is None

    def test_no_date_column_returns_none(self):
        """对于无日期列的表 → 直接返回 None（不发 SQL 查询）。"""
        import sources.triplewhale as tw
        original = tw._TABLE_DATE_COLUMNS.get("pixel_orders_table")
        tw._TABLE_DATE_COLUMNS["pixel_orders_table"] = None
        try:
            with patch("sources.triplewhale._run_sql_query") as mock_sql:
                result = _fetch_earliest_date("pixel_orders_table", "test_key")
            mock_sql.assert_not_called()
            assert result is None
        finally:
            tw._TABLE_DATE_COLUMNS["pixel_orders_table"] = original


class TestFetchRowCount:
    def test_returns_count_on_success(self):
        """正常返回 → 整数行数。"""
        with patch("sources.triplewhale._run_sql_query", return_value=[{"total": 12345}]):
            result = _fetch_row_count("pixel_orders_table", "test_key")
        assert result == 12345

    def test_returns_zero_on_empty_result(self):
        """空结果列表 → 返回 0。"""
        with patch("sources.triplewhale._run_sql_query", return_value=[]):
            result = _fetch_row_count("ads_table", "test_key")
        assert result == 0

    def test_returns_none_on_exception(self):
        """查询抛出异常 → 捕获，返回 None，不传播。"""
        with patch("sources.triplewhale._run_sql_query", side_effect=RuntimeError("db error")):
            result = _fetch_row_count("pixel_orders_table", "test_key")
        assert result is None
