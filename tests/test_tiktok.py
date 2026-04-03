"""tests/test_tiktok.py — TikTok Shop 数据源模块单元测试

使用 mock_credentials fixture（conftest.py）确保无需真实 API Key。
所有网络请求通过 unittest.mock.patch 替换，不发起真实 HTTP 请求。
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sources.tiktok as tiktok


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "tiktok_sample.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_order():
    """从 fixture 文件加载订单样本数据"""
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
        """authenticate() 成功：mock _refresh_access_token 和 _get_shop_cipher"""
        with patch("sources.tiktok._refresh_access_token", return_value="test_token"), \
             patch("sources.tiktok._get_shop_cipher", return_value="test_cipher"):
            result = tiktok.authenticate()
        assert result is True

    def test_authenticate_sets_module_state(self, mock_credentials):
        """authenticate() 成功后，模块级变量被正确设置。"""
        with patch("sources.tiktok._refresh_access_token", return_value="tok_abc"), \
             patch("sources.tiktok._get_shop_cipher", return_value="cip_xyz"):
            tiktok.authenticate()
        assert tiktok._access_token == "tok_abc"
        assert tiktok._shop_cipher == "cip_xyz"

    def test_authenticate_failure_returns_false(self, mock_credentials):
        """authenticate() 失败时返回 False，不抛出异常"""
        with patch("sources.tiktok._refresh_access_token", side_effect=RuntimeError("Token 无效")):
            result = tiktok.authenticate()
        assert result is False

    def test_authenticate_failure_clears_state(self, mock_credentials):
        """authenticate() 失败时，模块级变量被清空为 None。"""
        tiktok._access_token = "old_token"
        tiktok._shop_cipher = "old_cipher"
        with patch("sources.tiktok._refresh_access_token", side_effect=RuntimeError("失败")):
            tiktok.authenticate()
        assert tiktok._access_token is None
        assert tiktok._shop_cipher is None

    def test_authenticate_shop_cipher_failure_returns_false(self, mock_credentials):
        """_get_shop_cipher 失败时返回 False。"""
        with patch("sources.tiktok._refresh_access_token", return_value="token"), \
             patch("sources.tiktok._get_shop_cipher", side_effect=RuntimeError("shop cipher 获取失败")):
            result = tiktok.authenticate()
        assert result is False


# ---------------------------------------------------------------------------
# fetch_sample() 测试
# ---------------------------------------------------------------------------

class TestFetchSample:
    def test_fetch_sample_requires_authenticate(self):
        """fetch_sample() 未认证时抛出 RuntimeError。"""
        with pytest.raises(RuntimeError, match="authenticate"):
            tiktok.fetch_sample()

    def test_fetch_sample_success(self, mock_credentials, sample_order):
        """fetch_sample() 成功时返回订单列表。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"order_list": sample_order},
        }
        with patch("sources.tiktok.requests.post", return_value=mock_response):
            result = tiktok.fetch_sample()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_fetch_sample_api_error_raises(self, mock_credentials):
        """fetch_sample() API 返回非 0 code 时抛出 RuntimeError。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 40001,
            "message": "Unauthorized",
        }
        with patch("sources.tiktok.requests.post", return_value=mock_response):
            with pytest.raises(RuntimeError, match="订单查询失败"):
                tiktok.fetch_sample()

    def test_fetch_sample_empty_orders_raises(self, mock_credentials):
        """fetch_sample() 返回空订单列表时抛出 RuntimeError。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"order_list": []},
        }
        with patch("sources.tiktok.requests.post", return_value=mock_response):
            with pytest.raises(RuntimeError, match="空列表"):
                tiktok.fetch_sample()

    def test_fetch_sample_ignores_table_name(self, mock_credentials, sample_order):
        """table_name 参数被忽略（TikTok 只有一个端点）。"""
        tiktok._access_token = "test_token"
        tiktok._shop_cipher = "test_cipher"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"order_list": sample_order},
        }
        with patch("sources.tiktok.requests.post", return_value=mock_response):
            result = tiktok.fetch_sample("some_table_name")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# extract_fields() 测试
# ---------------------------------------------------------------------------

class TestExtractFields:
    def test_extract_fields_returns_fieldinfo_structure(self, sample_order):
        """extract_fields() 返回正确的 FieldInfo 结构（四字段）"""
        fields = tiktok.extract_fields(sample_order)
        assert isinstance(fields, list)
        assert len(fields) > 0
        for field in fields:
            assert "field_name" in field
            assert "data_type" in field
            assert "sample_value" in field
            assert "nullable" in field

    def test_extract_fields_data_types(self, sample_order):
        """data_type 值仅为合法类型之一"""
        valid_types = {"string", "number", "boolean", "array", "object", "null"}
        fields = tiktok.extract_fields(sample_order)
        for field in fields:
            assert field["data_type"] in valid_types

    def test_extract_fields_nullable_when_none(self):
        """值为 None 时 nullable=True"""
        sample = [{"order_id": "123", "buyer_message": None}]
        fields = tiktok.extract_fields(sample)
        none_field = next((f for f in fields if f["field_name"] == "buyer_message"), None)
        assert none_field is not None
        assert none_field["nullable"] is True

    def test_extract_fields_not_nullable_when_has_value(self):
        """值非 None 时 nullable=False"""
        sample = [{"order_id": "123", "buyer_message": "hello"}]
        fields = tiktok.extract_fields(sample)
        field = next((f for f in fields if f["field_name"] == "buyer_message"), None)
        assert field is not None
        assert field["nullable"] is False

    def test_extract_fields_empty_sample(self):
        """空样本返回空列表"""
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
        """相同输入产生相同签名（确定性）"""
        params = {"app_key": "test_key", "timestamp": "1693468800"}
        sig1 = tiktok._sign_request("test_secret", params)
        sig2 = tiktok._sign_request("test_secret", params)
        assert sig1 == sig2

    def test_sign_request_different_secrets(self):
        """不同 secret 产生不同签名"""
        params = {"app_key": "test_key", "timestamp": "1693468800"}
        sig1 = tiktok._sign_request("secret1", params)
        sig2 = tiktok._sign_request("secret2", params)
        assert sig1 != sig2

    def test_sign_request_returns_hex_string(self):
        """签名返回十六进制字符串（小写，64 字符）。"""
        params = {"app_key": "test_key", "timestamp": "1693468800"}
        sig = tiktok._sign_request("test_secret", params)
        assert isinstance(sig, str)
        assert len(sig) == 64
        assert sig == sig.lower()

    def test_sign_request_different_params(self):
        """不同参数产生不同签名。"""
        sig1 = tiktok._sign_request("secret", {"a": "1"})
        sig2 = tiktok._sign_request("secret", {"a": "2"})
        assert sig1 != sig2

    def test_sign_request_sorted_params(self):
        """参数顺序不影响签名结果（字典序排列）。"""
        sig1 = tiktok._sign_request("secret", {"b": "2", "a": "1"})
        sig2 = tiktok._sign_request("secret", {"a": "1", "b": "2"})
        assert sig1 == sig2
