"""单元测试：sources/dingtalk.py

所有测试均使用 mock，不需要真实凭证或网络访问。
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "dingtalk_sample.json"


@pytest.fixture(autouse=True)
def reset_token_cache():
    """每个测试前重置模块级 token 缓存，防止测试间状态污染。"""
    import sources.dingtalk as dt
    dt._cached_token = None
    dt._token_expiry = 0.0
    yield
    dt._cached_token = None
    dt._token_expiry = 0.0


def _make_token_response() -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"accessToken": "test_access_token", "expireIn": 7200}
    return mock_resp


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class TestAuthenticate:
    """AC #1：authenticate() 返回 True / False 并输出日志。"""

    def test_authenticate_success(self, mock_credentials):
        token_resp = _make_token_response()
        with patch("sources.dingtalk.requests.post", return_value=token_resp):
            from sources.dingtalk import authenticate
            result = authenticate()
        assert result is True

    def test_authenticate_token_cached(self, mock_credentials):
        """首次成功后第二次调用不再发送 POST 请求。"""
        token_resp = _make_token_response()
        with patch("sources.dingtalk.requests.post", return_value=token_resp) as mock_post:
            from sources.dingtalk import authenticate
            authenticate()
            authenticate()
        assert mock_post.call_count == 1

    def test_authenticate_failure(self, mock_credentials):
        with patch("sources.dingtalk.requests.post", side_effect=requests.HTTPError("401")):
            from sources.dingtalk import authenticate
            result = authenticate()
        assert result is False


class TestFetchSample:
    """AC #2：fetch_sample() 返回记录列表。"""

    def test_fetch_sample_success(self, mock_credentials):
        """使用显式 DINGTALK_SHEET_ID 凭证，只需发送 range 请求。"""
        creds_with_sheet = dict(mock_credentials)
        creds_with_sheet["DINGTALK_SHEET_ID"] = "test_sheet_id"

        token_resp = _make_token_response()
        fixture_data = _load_fixture()
        range_resp = MagicMock()
        range_resp.raise_for_status = MagicMock()
        range_resp.json.return_value = fixture_data

        with patch("sources.dingtalk.requests.post", return_value=token_resp), \
             patch("sources.dingtalk.requests.get", return_value=range_resp), \
             patch("config.credentials.get_credentials", return_value=creds_with_sheet):
            from sources.dingtalk import fetch_sample
            result = fetch_sample()

        assert isinstance(result, list)
        assert len(result) == 3
        assert "日期" in result[0]
        assert result[0]["日期"] == "2024-01-01"

    def test_fetch_sample_success_auto_sheet(self, mock_credentials):
        """未配置 DINGTALK_SHEET_ID 时，自动获取第一个 Sheet。"""
        creds_no_sheet = {k: v for k, v in mock_credentials.items() if k != "DINGTALK_SHEET_ID"}

        token_resp = _make_token_response()
        sheets_resp = MagicMock()
        sheets_resp.raise_for_status = MagicMock()
        sheets_resp.json.return_value = {"value": [{"id": "auto_sheet_id"}]}

        fixture_data = _load_fixture()
        range_resp = MagicMock()
        range_resp.raise_for_status = MagicMock()
        range_resp.json.return_value = fixture_data

        with patch("sources.dingtalk.requests.post", return_value=token_resp), \
             patch("sources.dingtalk.requests.get", side_effect=[sheets_resp, range_resp]), \
             patch("config.credentials.get_credentials", return_value=creds_no_sheet):
            from sources.dingtalk import fetch_sample
            result = fetch_sample()

        assert isinstance(result, list)
        assert len(result) == 3


class TestExtractFields:
    """AC #3：extract_fields() 返回 FieldInfo 列表。"""

    def test_extract_fields_normal(self, mock_credentials):
        fixture_data = _load_fixture()
        values = fixture_data["value"]["values"]
        headers_row = values[0]
        records = [
            {str(col): (row[i] if i < len(row) else None) for i, col in enumerate(headers_row)}
            for row in values[1:]
        ]

        from sources.dingtalk import extract_fields
        result = extract_fields(records)

        assert isinstance(result, list)
        assert len(result) == 5  # 5 列

        for field in result:
            assert set(field.keys()) == {"field_name", "data_type", "sample_value", "nullable"}

        field_names = [f["field_name"] for f in result]
        assert "日期" in field_names
        assert "营销投入" in field_names

        # 日期列是字符串，非空
        date_field = next(f for f in result if f["field_name"] == "日期")
        assert date_field["data_type"] == "string"
        assert date_field["nullable"] is False
        assert date_field["sample_value"] is not None

    def test_extract_fields_nullable_association(self, mock_credentials):
        """含"关联"的列名应被标记为 nullable。"""
        sample = [
            {"关联字段": None, "普通字段": "abc"},
            {"关联字段": None, "普通字段": "def"},
        ]
        from sources.dingtalk import extract_fields
        result = extract_fields(sample)
        assoc_field = next(f for f in result if f["field_name"] == "关联字段")
        assert assoc_field["nullable"] is True
        assert assoc_field["sample_value"] is None

    def test_extract_fields_empty_sample(self, mock_credentials):
        from sources.dingtalk import extract_fields
        result = extract_fields([])
        assert result == []
