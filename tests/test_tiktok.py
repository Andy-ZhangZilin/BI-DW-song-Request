"""tests/test_tiktok.py — TikTok Shop 数据源模块单元测试

使用 mock_credentials fixture（conftest.py）确保无需真实 API Key。
所有网络请求通过 unittest.mock.patch 替换，不发起真实 HTTP 请求。
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import sources.tiktok as tiktok


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "tiktok_sample.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_order():
    """从 fixture 文件加载订单样本数据（作为通用样本 list）。"""
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["data"]["order_list"]


@pytest.fixture(autouse=True)
def reset_module_state():
    """每个测试前后重置模块级状态变量，避免测试间状态污染。"""
    tiktok._access_token = None
    tiktok._shop_cipher = None
    yield
    tiktok._access_token = None
    tiktok._shop_cipher = None


# ---------------------------------------------------------------------------
# authenticate() 测试
# ---------------------------------------------------------------------------

class TestAuthenticate:
    def test_authenticate_success(self, mock_credentials):
        """authenticate() 成功：mock _get_tiktok_auth_via_dtc 返回 token 和 cipher。"""
        with patch("sources.tiktok._get_tiktok_auth_via_dtc", return_value=("test_token", "test_cipher")):
            result = tiktok.authenticate()
        assert result is True

    def test_authenticate_sets_module_state(self, mock_credentials):
        """authenticate() 成功后，模块级变量被正确设置。"""
        with patch("sources.tiktok._get_tiktok_auth_via_dtc", return_value=("tok_abc", "cip_xyz")):
            tiktok.authenticate()
        assert tiktok._access_token == "tok_abc"
        assert tiktok._shop_cipher == "cip_xyz"

    def test_authenticate_failure_returns_false(self, mock_credentials):
        """authenticate() 失败时返回 False，不抛出异常。"""
        with patch("sources.tiktok._get_tiktok_auth_via_dtc", side_effect=RuntimeError("DTC 失败")):
            result = tiktok.authenticate()
        assert result is False

    def test_authenticate_failure_clears_state(self, mock_credentials):
        """authenticate() 失败时，模块级变量被清空为 None。"""
        tiktok._access_token = "old_token"
        tiktok._shop_cipher = "old_cipher"
        with patch("sources.tiktok._get_tiktok_auth_via_dtc", side_effect=RuntimeError("失败")):
            tiktok.authenticate()
        assert tiktok._access_token is None
        assert tiktok._shop_cipher is None

    def test_authenticate_logs_success(self, mock_credentials, caplog):
        """authenticate() 成功时日志包含 '认证 ... 成功'。"""
        import logging
        with patch("sources.tiktok._get_tiktok_auth_via_dtc", return_value=("t", "c")):
            with caplog.at_level(logging.INFO, logger="sources.tiktok"):
                tiktok.authenticate()
        assert "认证 ... 成功" in caplog.text

    def test_authenticate_logs_failure(self, mock_credentials, caplog):
        """authenticate() 失败时日志包含 '认证 ... 失败'。"""
        import logging
        with patch("sources.tiktok._get_tiktok_auth_via_dtc", side_effect=RuntimeError("err")):
            with caplog.at_level(logging.ERROR, logger="sources.tiktok"):
                tiktok.authenticate()
        assert "认证 ... 失败" in caplog.text


# ---------------------------------------------------------------------------
# fetch_sample() 测试 — 路由分发与基础行为
# ---------------------------------------------------------------------------

class TestFetchSampleRouting:
    def test_fetch_sample_requires_authenticate(self):
        """fetch_sample() 未认证时抛出 RuntimeError。"""
        with pytest.raises(RuntimeError, match="authenticate"):
            tiktok.fetch_sample("return_refund")

    def test_fetch_sample_unknown_table_raises(self, mock_credentials):
        """未知 table_name 抛出 ValueError。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        with pytest.raises(ValueError, match="未知 table_name"):
            tiktok.fetch_sample("unknown_table")

    def test_fetch_sample_ad_spend_returns_empty(self, mock_credentials):
        """ad_spend 路由直接返回空列表，不发起 HTTP 请求。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        with patch("sources.tiktok.requests.get") as mock_get, \
             patch("sources.tiktok.requests.post") as mock_post:
            result = tiktok.fetch_sample("ad_spend")
        assert result == []
        mock_get.assert_not_called()
        mock_post.assert_not_called()

    def test_fetch_sample_none_uses_default_table(self, mock_credentials, sample_order):
        """table_name=None 时使用默认表 return_refund。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": 0,
            "data": {"returns": sample_order},
        }
        with patch("sources.tiktok.requests.post", return_value=mock_resp):
            result = tiktok.fetch_sample(None)
        assert isinstance(result, list)

    def test_fetch_sample_tables_constant_has_7_entries(self):
        """TABLES 常量包含 7 个 table_name。"""
        assert len(tiktok.TABLES) == 7
        assert "ad_spend" in tiktok.TABLES
        assert "return_refund" in tiktok.TABLES
        assert "shop_product_performance" in tiktok.TABLES
        assert "affiliate_creator_orders" in tiktok.TABLES
        assert "video_performances" in tiktok.TABLES
        assert "affiliate_sample_status" in tiktok.TABLES
        assert "affiliate_campaign_performance" in tiktok.TABLES


# ---------------------------------------------------------------------------
# fetch_sample() 测试 — 各路由 POST/GET 实现
# ---------------------------------------------------------------------------

class TestFetchSampleReturnRefund:
    def test_return_refund_success(self, mock_credentials, sample_order):
        """return_refund 路由成功返回退款记录列表。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": 0,
            "data": {"returns": sample_order},
        }
        with patch("sources.tiktok.requests.post", return_value=mock_resp):
            result = tiktok.fetch_sample("return_refund")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_return_refund_empty_returns_empty_list(self, mock_credentials):
        """return_refund 接口无记录时返回空列表（不抛异常）。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": 0, "data": {"returns": []}}
        with patch("sources.tiktok.requests.post", return_value=mock_resp):
            result = tiktok.fetch_sample("return_refund")
        assert result == []

    def test_return_refund_api_error_raises(self, mock_credentials):
        """return_refund API 返回非 0 code 时抛出 RuntimeError。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": 40001, "message": "Unauthorized"}
        with patch("sources.tiktok.requests.post", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="退款查询失败"):
                tiktok.fetch_sample("return_refund")


class TestFetchSampleAffiliateCreatorOrders:
    def test_affiliate_creator_orders_success(self, mock_credentials):
        """affiliate_creator_orders 路由成功返回达人订单列表。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": 0,
            "data": {"orders": [{"order_id": "123", "status": "PAID"}]},
        }
        with patch("sources.tiktok.requests.post", return_value=mock_resp):
            result = tiktok.fetch_sample("affiliate_creator_orders")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_affiliate_creator_orders_empty_returns_empty(self, mock_credentials):
        """affiliate_creator_orders 接口无数据时返回空列表。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": 0, "data": {"orders": []}}
        with patch("sources.tiktok.requests.post", return_value=mock_resp):
            result = tiktok.fetch_sample("affiliate_creator_orders")
        assert result == []


class TestFetchSampleVideoPerformances:
    def test_video_performances_success(self, mock_credentials):
        """video_performances 路由成功返回视频表现列表。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": 0,
            "data": [{"video_id": "v001", "views": 5000, "likes": 200}],
        }
        with patch("sources.tiktok.requests.get", return_value=mock_resp):
            result = tiktok.fetch_sample("video_performances")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_video_performances_uses_get(self, mock_credentials):
        """video_performances 路由使用 GET 方法。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": 0, "data": [{"video_id": "v001"}]}
        with patch("sources.tiktok.requests.get", return_value=mock_resp) as mock_get, \
             patch("sources.tiktok.requests.post") as mock_post:
            tiktok.fetch_sample("video_performances")
        mock_get.assert_called_once()
        mock_post.assert_not_called()


class TestFetchSampleShopProductPerformance:
    def test_shop_product_performance_skips_when_no_product_id(self, mock_credentials):
        """TIKTOK_PRODUCT_ID 未配置时返回空列表，不发起请求。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        with patch("config.credentials.get_optional_config", return_value=""), \
             patch("sources.tiktok.requests.get") as mock_get:
            result = tiktok.fetch_sample("shop_product_performance")
        assert result == []
        mock_get.assert_not_called()

    def test_shop_product_performance_success(self, mock_credentials):
        """TIKTOK_PRODUCT_ID 已配置时调用 API 并返回性能数据。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": 0,
            "data": {"product_id": "p123", "revenue": "1000.00", "orders": 50},
        }
        with patch.dict("os.environ", {"TIKTOK_PRODUCT_ID": "p123"}), \
             patch("sources.tiktok.requests.get", return_value=mock_resp):
            result = tiktok.fetch_sample("shop_product_performance")
        assert isinstance(result, list)
        assert len(result) > 0


class TestFetchSampleAffiliateSampleStatus:
    def test_affiliate_sample_status_skips_when_missing_ids(self, mock_credentials):
        """路径参数未配置时返回空列表。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        with patch("config.credentials.get_optional_config", return_value=""), \
             patch("sources.tiktok.requests.get") as mock_get:
            result = tiktok.fetch_sample("affiliate_sample_status")
        assert result == []
        mock_get.assert_not_called()

    def test_affiliate_sample_status_success(self, mock_credentials):
        """所有路径参数已配置时调用 API 并返回状态数据。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": 0,
            "data": {"sample_count": 5, "delivered": 3},
        }
        env_vars = {
            "TIKTOK_CAMPAIGN_ID": "c001",
            "TIKTOK_PRODUCT_ID": "p001",
            "TIKTOK_CREATOR_TEMP_ID": "cr001",
        }
        with patch.dict("os.environ", env_vars), \
             patch("sources.tiktok.requests.get", return_value=mock_resp):
            result = tiktok.fetch_sample("affiliate_sample_status")
        assert isinstance(result, list)
        assert len(result) > 0


class TestFetchSampleAffiliateCampaignPerformance:
    def test_affiliate_campaign_performance_skips_when_missing_ids(self, mock_credentials):
        """路径参数未配置时返回空列表。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        with patch("config.credentials.get_optional_config", return_value=""), \
             patch("sources.tiktok.requests.get") as mock_get:
            result = tiktok.fetch_sample("affiliate_campaign_performance")
        assert result == []
        mock_get.assert_not_called()

    def test_affiliate_campaign_performance_success(self, mock_credentials):
        """所有路径参数已配置时调用 API 并返回表现数据。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": 0,
            "data": {"campaign_id": "c001", "gmv": "5000.00", "orders": 100},
        }
        env_vars = {"TIKTOK_CAMPAIGN_ID": "c001", "TIKTOK_PRODUCT_ID": "p001"}
        with patch.dict("os.environ", env_vars), \
             patch("sources.tiktok.requests.get", return_value=mock_resp):
            result = tiktok.fetch_sample("affiliate_campaign_performance")
        assert isinstance(result, list)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# extract_fields() 测试
# ---------------------------------------------------------------------------

class TestExtractFields:
    def test_extract_fields_returns_fieldinfo_structure(self, sample_order):
        """extract_fields() 返回正确的 FieldInfo 结构（四字段）。"""
        fields = tiktok.extract_fields(sample_order)
        assert isinstance(fields, list)
        assert len(fields) > 0
        for field in fields:
            assert "field_name" in field
            assert "data_type" in field
            assert "sample_value" in field
            assert "nullable" in field

    def test_extract_fields_data_types(self, sample_order):
        """data_type 值仅为合法类型之一。"""
        valid_types = {"string", "number", "boolean", "array", "object", "null"}
        fields = tiktok.extract_fields(sample_order)
        for field in fields:
            assert field["data_type"] in valid_types

    def test_extract_fields_nullable_when_none(self):
        """值为 None 时 nullable=True。"""
        sample = [{"order_id": "123", "buyer_message": None}]
        fields = tiktok.extract_fields(sample)
        none_field = next((f for f in fields if f["field_name"] == "buyer_message"), None)
        assert none_field is not None
        assert none_field["nullable"] is True

    def test_extract_fields_not_nullable_when_has_value(self):
        """值非 None 时 nullable=False。"""
        sample = [{"order_id": "123", "buyer_message": "hello"}]
        fields = tiktok.extract_fields(sample)
        field = next((f for f in fields if f["field_name"] == "buyer_message"), None)
        assert field is not None
        assert field["nullable"] is False

    def test_extract_fields_empty_sample(self):
        """空样本返回空列表。"""
        assert tiktok.extract_fields([]) == []

    def test_extract_fields_string_type(self, sample_order):
        """order_id 字段类型应为 string。"""
        fields = tiktok.extract_fields(sample_order)
        field = next((f for f in fields if f["field_name"] == "order_id"), None)
        assert field is not None
        assert field["data_type"] == "string"

    def test_extract_fields_number_type(self, sample_order):
        """order_status 字段类型应为 number（integer）。"""
        fields = tiktok.extract_fields(sample_order)
        field = next((f for f in fields if f["field_name"] == "order_status"), None)
        assert field is not None
        assert field["data_type"] == "number"

    def test_extract_fields_boolean_type(self, sample_order):
        """is_cod 字段类型应为 boolean。"""
        fields = tiktok.extract_fields(sample_order)
        field = next((f for f in fields if f["field_name"] == "is_cod"), None)
        assert field is not None
        assert field["data_type"] == "boolean"

    def test_extract_fields_array_type(self, sample_order):
        """skus 字段类型应为 array。"""
        fields = tiktok.extract_fields(sample_order)
        field = next((f for f in fields if f["field_name"] == "skus"), None)
        assert field is not None
        assert field["data_type"] == "array"

    def test_extract_fields_object_type(self, sample_order):
        """recipient_address 字段类型应为 object。"""
        fields = tiktok.extract_fields(sample_order)
        field = next((f for f in fields if f["field_name"] == "recipient_address"), None)
        assert field is not None
        assert field["data_type"] == "object"

    def test_extract_fields_nullable_is_bool(self, sample_order):
        """nullable 字段类型应为 bool。"""
        fields = tiktok.extract_fields(sample_order)
        for f in fields:
            assert isinstance(f["nullable"], bool)


# ---------------------------------------------------------------------------
# _sign_request() 测试
# ---------------------------------------------------------------------------

class TestSignRequest:
    def test_sign_request_deterministic(self):
        """相同输入产生相同签名（确定性）。"""
        params = {"app_key": "test_key", "timestamp": "1693468800"}
        sig1 = tiktok._sign_request("test_secret", "/test/path", params)
        sig2 = tiktok._sign_request("test_secret", "/test/path", params)
        assert sig1 == sig2

    def test_sign_request_different_secrets(self):
        """不同 secret 产生不同签名。"""
        params = {"app_key": "test_key", "timestamp": "1693468800"}
        sig1 = tiktok._sign_request("secret1", "/test/path", params)
        sig2 = tiktok._sign_request("secret2", "/test/path", params)
        assert sig1 != sig2

    def test_sign_request_different_paths(self):
        """不同路径产生不同签名。"""
        params = {"app_key": "test_key", "timestamp": "1693468800"}
        sig1 = tiktok._sign_request("secret", "/path1", params)
        sig2 = tiktok._sign_request("secret", "/path2", params)
        assert sig1 != sig2

    def test_sign_request_returns_hex_string(self):
        """签名返回十六进制字符串（小写，64 字符）。"""
        params = {"app_key": "test_key", "timestamp": "1693468800"}
        sig = tiktok._sign_request("test_secret", "/test/path", params)
        assert isinstance(sig, str)
        assert len(sig) == 64
        assert sig == sig.lower()

    def test_sign_request_different_params(self):
        """不同参数产生不同签名。"""
        sig1 = tiktok._sign_request("secret", "/path", {"a": "1"})
        sig2 = tiktok._sign_request("secret", "/path", {"a": "2"})
        assert sig1 != sig2

    def test_sign_request_sorted_params(self):
        """参数顺序不影响签名结果（字典序排列）。"""
        sig1 = tiktok._sign_request("secret", "/path", {"b": "2", "a": "1"})
        sig2 = tiktok._sign_request("secret", "/path", {"a": "1", "b": "2"})
        assert sig1 == sig2

    def test_sign_request_with_body(self):
        """带 body 参数与不带 body 签名不同。"""
        params = {"app_key": "test_key", "timestamp": "1693468800"}
        sig_no_body = tiktok._sign_request("secret", "/path", params)
        sig_with_body = tiktok._sign_request("secret", "/path", params, body={"page_size": 10})
        assert sig_no_body != sig_with_body
