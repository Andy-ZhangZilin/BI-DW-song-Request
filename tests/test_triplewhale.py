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
    _infer_type,
    _fetch_table,
    TABLES,
    SHOP_DOMAIN,
    DEFAULT_TIMEOUT,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "triplewhale_sample.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tw_sample() -> dict:
    """加载 triplewhale fixture 数据（完整响应结构）。"""
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def orders_sample(tw_sample) -> list[dict]:
    """pixel_orders_table 的 data 列表。"""
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
        """table_name=None → 使用 pixel_orders_table。"""
        with patch("sources.triplewhale._fetch_table") as mock_fetch:
            mock_fetch.return_value = orders_sample
            result = fetch_sample(None)
        mock_fetch.assert_called_once()
        assert mock_fetch.call_args[0][0] == "pixel_orders_table"
        assert result == orders_sample

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
    def test_post_request_uses_shop_field(self, mock_credentials):
        """POST 请求 body 必须包含 shop 字段（attribution 端点规范）。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=True,
                json=lambda: {"ordersWithJourneys": [{"order_id": "ORD-001"}]},
            )
            _fetch_table("pixel_orders_table", "test_tw_key")
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["shop"] == SHOP_DOMAIN

    def test_post_request_uses_api_key_header(self, mock_credentials):
        """POST 请求 header 必须包含 x-api-key（小写，HTTP/2 兼容）。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=True,
                json=lambda: {"ordersWithJourneys": [{"order_id": "ORD-001"}]},
            )
            _fetch_table("pixel_orders_table", "test_tw_key")
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["x-api-key"] == "test_tw_key"

    def test_post_request_uses_timeout(self, mock_credentials):
        """POST 请求必须设置 timeout=30。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=True,
                json=lambda: {"ordersWithJourneys": [{"order_id": "ORD-001"}]},
            )
            _fetch_table("pixel_orders_table", "test_tw_key")
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["timeout"] == DEFAULT_TIMEOUT

    def test_response_orders_with_journeys_extracted(self, mock_credentials):
        """响应 {"ordersWithJourneys": [...]} → 返回该列表。"""
        expected = [{"order_id": "ORD-001", "total_price": 99.99}]
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=True,
                json=lambda: {"ordersWithJourneys": expected, "count": 1},
            )
            result = _fetch_table("pixel_orders_table", "test_tw_key")
        assert result == expected

    def test_http_error_raises_runtime_error(self, mock_credentials):
        """HTTP 非 2xx → 抛出 RuntimeError。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=False, status_code=500, text="Internal Server Error"
            )
            with pytest.raises(RuntimeError, match="HTTP 500"):
                _fetch_table("pixel_orders_table", "test_tw_key")

    def test_unknown_response_structure_raises_runtime_error(self, mock_credentials):
        """响应结构无法解析 → 抛出 RuntimeError。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=True,
                json=lambda: {"unknown_key": "unexpected"},
            )
            with pytest.raises(RuntimeError, match="无法解析"):
                _fetch_table("pixel_orders_table", "test_tw_key")

    def test_timeout_propagates(self, mock_credentials):
        """请求超时 → 直接传播 Timeout 异常（由 fetch_sample 层处理）。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.side_effect = req_lib.Timeout()
            with pytest.raises(req_lib.Timeout):
                _fetch_table("pixel_orders_table", "test_tw_key")

    def test_post_request_includes_date_range(self, mock_credentials):
        """POST 请求 body 必须包含 startDate 和 endDate 字段。"""
        with patch("sources.triplewhale.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                ok=True,
                json=lambda: {"ordersWithJourneys": [{"order_id": "ORD-001"}]},
            )
            _fetch_table("pixel_orders_table", "test_tw_key")
        call_kwargs = mock_post.call_args[1]
        assert "startDate" in call_kwargs["json"]
        assert "endDate" in call_kwargs["json"]
