"""单元测试：sources/youtube_url.py

所有测试均使用 mock，不需要真实凭证或网络访问。

覆盖 AC:
- AC1: youtube_url.py 实现 ARCH2 三接口契约
- AC2: authenticate() 复用 YouTube API Key 验证逻辑
- AC3: fetch_sample() 使用写死 URL 调用 videos.list?part=statistics
- AC4: extract_fields() 返回标准 FieldInfo 列表，含 viewCount/likeCount
- AC6: 所有测试全 mock，无需真实 API Key
"""

import pytest
import requests as req_lib
from unittest.mock import patch, MagicMock

from sources import youtube_url


# ---------------------------------------------------------------------------
# authenticate() 测试
# ---------------------------------------------------------------------------


def test_authenticate_success(mock_credentials):
    """AC2: API Key 有效时 authenticate() 应返回 True。"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("sources.youtube_url.requests.get", return_value=mock_resp):
        result = youtube_url.authenticate()
    assert result is True


def test_authenticate_failure_403(mock_credentials):
    """AC2: API Key 无效（403）时 authenticate() 应返回 False。"""
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.reason = "Forbidden"
    with patch("sources.youtube_url.requests.get", return_value=mock_resp):
        result = youtube_url.authenticate()
    assert result is False


def test_authenticate_failure_network_error(mock_credentials):
    """AC2: 网络异常时 authenticate() 应返回 False。"""
    with patch("sources.youtube_url.requests.get",
               side_effect=req_lib.exceptions.ConnectionError("Connection error")):
        result = youtube_url.authenticate()
    assert result is False


def test_authenticate_uses_api_key(mock_credentials):
    """AC2: authenticate() 应传递 key 参数到 API 请求。"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("sources.youtube_url.requests.get", return_value=mock_resp) as mock_get:
        youtube_url.authenticate()
    params = mock_get.call_args.kwargs.get("params", {})
    assert "key" in params
    assert params["key"] == "test_youtube_key"


# ---------------------------------------------------------------------------
# fetch_sample() 测试
# ---------------------------------------------------------------------------


SAMPLE_RESPONSE = {
    "items": [
        {
            "kind": "youtube#video",
            "etag": "test_etag",
            "id": "1laF2zVhbcE",
            "statistics": {
                "viewCount": "919",
                "likeCount": "89",
                "favoriteCount": "0",
                "commentCount": "5",
            },
        }
    ]
}


def test_fetch_sample_returns_records(mock_credentials):
    """AC3: fetch_sample() 应返回至少一条记录。"""
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_RESPONSE
    mock_resp.raise_for_status = MagicMock()
    with patch("sources.youtube_url.requests.get", return_value=mock_resp):
        result = youtube_url.fetch_sample()
    assert isinstance(result, list)
    assert len(result) >= 1


def test_fetch_sample_uses_hardcoded_url(mock_credentials):
    """AC3: fetch_sample() 应使用写死的 video_id=1laF2zVhbcE。"""
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_RESPONSE
    mock_resp.raise_for_status = MagicMock()
    with patch("sources.youtube_url.requests.get", return_value=mock_resp) as mock_get:
        youtube_url.fetch_sample()
    params = mock_get.call_args.kwargs.get("params", {})
    assert params.get("id") == "1laF2zVhbcE"
    assert params.get("part") == "statistics"


def test_fetch_sample_raises_on_empty(mock_credentials):
    """AC3: API 返回空 items 时应抛出 RuntimeError。"""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"items": []}
    mock_resp.raise_for_status = MagicMock()
    with patch("sources.youtube_url.requests.get", return_value=mock_resp):
        with pytest.raises(RuntimeError, match=r"\[youtube_url\]"):
            youtube_url.fetch_sample()


def test_fetch_sample_raises_on_http_error(mock_credentials):
    """AC3: API 请求失败时应上抛异常。"""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = req_lib.exceptions.HTTPError("403 Forbidden")
    with patch("sources.youtube_url.requests.get", return_value=mock_resp):
        with pytest.raises(req_lib.exceptions.HTTPError):
            youtube_url.fetch_sample()


def test_fetch_sample_table_name_ignored(mock_credentials):
    """AC3: table_name 参数被忽略，调用仍正常返回。"""
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_RESPONSE
    mock_resp.raise_for_status = MagicMock()
    with patch("sources.youtube_url.requests.get", return_value=mock_resp):
        result = youtube_url.fetch_sample(table_name="anything")
    assert isinstance(result, list)
    assert len(result) >= 1


# ---------------------------------------------------------------------------
# extract_fields() 测试
# ---------------------------------------------------------------------------


def test_extract_fields_returns_list():
    """AC4: extract_fields() 应返回非空列表。"""
    fields = youtube_url.extract_fields(SAMPLE_RESPONSE["items"])
    assert isinstance(fields, list)
    assert len(fields) > 0


def test_extract_fields_empty_sample():
    """AC4: 空列表输入应返回空列表。"""
    assert youtube_url.extract_fields([]) == []


def test_extract_fields_has_required_keys():
    """AC4: 每个 FieldInfo 条目必须含 field_name / data_type / sample_value / nullable。"""
    fields = youtube_url.extract_fields(SAMPLE_RESPONSE["items"])
    for f in fields:
        assert "field_name" in f, f"缺少 field_name: {f}"
        assert "data_type" in f, f"缺少 data_type: {f}"
        assert "sample_value" in f, f"缺少 sample_value: {f}"
        assert "nullable" in f, f"缺少 nullable: {f}"


def test_extract_fields_contains_viewcount_likecount():
    """AC4: extract_fields() 应提取含 viewCount 和 likeCount 的字段。"""
    fields = youtube_url.extract_fields(SAMPLE_RESPONSE["items"])
    field_names = [f["field_name"] for f in fields]
    assert any("viewCount" in name for name in field_names), \
        f"未找到 viewCount 字段，已提取：{field_names}"
    assert any("likeCount" in name for name in field_names), \
        f"未找到 likeCount 字段，已提取：{field_names}"


def test_extract_fields_nullable_is_bool():
    """AC4: nullable 字段值必须是 bool 类型。"""
    fields = youtube_url.extract_fields(SAMPLE_RESPONSE["items"])
    for f in fields:
        assert isinstance(f["nullable"], bool), f"nullable 应为 bool: {f}"


def test_extract_fields_data_type_valid():
    """AC4: data_type 必须是有效类型字符串。"""
    valid_types = {"string", "number", "boolean", "array", "object", "null"}
    fields = youtube_url.extract_fields(SAMPLE_RESPONSE["items"])
    for f in fields:
        assert f["data_type"] in valid_types, f"无效 data_type: {f['data_type']} in {f}"
