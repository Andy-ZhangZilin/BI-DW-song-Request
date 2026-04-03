"""单元测试：sources/youtube.py

所有测试均使用 mock，不需要真实凭证或网络访问。

覆盖 AC:
- AC1: authenticate() 成功时返回 True，日志输出 [youtube] 认证 ... 成功
- AC5: authenticate() 失败（403/401/网络异常）时返回 False，日志输出错误信息
- AC2: fetch_sample() 返回至少一条记录
- AC3/AC6: extract_fields() 返回标准 FieldInfo 列表，所有测试不需要真实 API Key
"""

import json
import pytest
import requests as req_lib
from pathlib import Path
from unittest.mock import patch, MagicMock

from sources import youtube


FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def youtube_fixture():
    """加载 youtube_sample.json fixture 文件，返回 items 列表。"""
    with open(FIXTURES_DIR / "youtube_sample.json", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# authenticate() 测试
# ---------------------------------------------------------------------------


def test_authenticate_success(mock_credentials):
    """AC1: API Key 有效时 authenticate() 应返回 True。"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("sources.youtube.requests.get", return_value=mock_resp):
        result = youtube.authenticate()
    assert result is True


def test_authenticate_failure_403(mock_credentials):
    """AC5: API Key 无效（403 Forbidden）时 authenticate() 应返回 False。"""
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.reason = "Forbidden"
    with patch("sources.youtube.requests.get", return_value=mock_resp):
        result = youtube.authenticate()
    assert result is False


def test_authenticate_failure_401(mock_credentials):
    """AC5: 未授权（401）时 authenticate() 应返回 False。"""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.reason = "Unauthorized"
    with patch("sources.youtube.requests.get", return_value=mock_resp):
        result = youtube.authenticate()
    assert result is False


def test_authenticate_failure_network_error(mock_credentials):
    """AC5: 网络异常时 authenticate() 应捕获异常并返回 False。"""
    with patch("sources.youtube.requests.get",
               side_effect=req_lib.exceptions.ConnectionError("Connection error")):
        result = youtube.authenticate()
    assert result is False


def test_authenticate_uses_api_key(mock_credentials):
    """AC1: authenticate() 应传递 key 参数到 API 请求。"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("sources.youtube.requests.get", return_value=mock_resp) as mock_get:
        youtube.authenticate()
    call_kwargs = mock_get.call_args
    params = call_kwargs[1].get("params") or call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {}
    if not params:
        params = call_kwargs.kwargs.get("params", {})
    assert "key" in params
    assert params["key"] == "test_youtube_key"


# ---------------------------------------------------------------------------
# fetch_sample() 测试
# ---------------------------------------------------------------------------


def test_fetch_sample_returns_records(mock_credentials, youtube_fixture):
    """AC2: fetch_sample() 应返回至少一条记录。"""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"items": youtube_fixture}
    mock_resp.raise_for_status = MagicMock()
    with patch("sources.youtube.requests.get", return_value=mock_resp):
        result = youtube.fetch_sample()
    assert isinstance(result, list)
    assert len(result) >= 1


def test_fetch_sample_table_name_ignored(mock_credentials, youtube_fixture):
    """AC2: table_name 参数（非 SQL 数据源）被忽略，调用仍正常返回。"""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"items": youtube_fixture}
    mock_resp.raise_for_status = MagicMock()
    with patch("sources.youtube.requests.get", return_value=mock_resp):
        result = youtube.fetch_sample(table_name=None)
    assert isinstance(result, list)
    assert len(result) >= 1


def test_fetch_sample_raises_on_empty_response(mock_credentials):
    """AC2: API 返回空 items 时 fetch_sample() 应抛出 RuntimeError。"""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"items": []}
    mock_resp.raise_for_status = MagicMock()
    with patch("sources.youtube.requests.get", return_value=mock_resp):
        with pytest.raises(RuntimeError, match=r"\[youtube\]"):
            youtube.fetch_sample()


# ---------------------------------------------------------------------------
# extract_fields() 测试
# ---------------------------------------------------------------------------


def test_extract_fields_returns_list(youtube_fixture):
    """AC3: extract_fields() 应返回非空列表。"""
    fields = youtube.extract_fields(youtube_fixture)
    assert isinstance(fields, list)
    assert len(fields) > 0


def test_extract_fields_empty_sample():
    """AC3: 空列表输入应返回空列表。"""
    assert youtube.extract_fields([]) == []


def test_extract_fields_has_required_keys(youtube_fixture):
    """AC3: 每个 FieldInfo 条目必须含 field_name / data_type / sample_value / nullable。"""
    fields = youtube.extract_fields(youtube_fixture)
    for f in fields:
        assert "field_name" in f, f"缺少 field_name: {f}"
        assert "data_type" in f, f"缺少 data_type: {f}"
        assert "sample_value" in f, f"缺少 sample_value: {f}"
        assert "nullable" in f, f"缺少 nullable: {f}"


def test_extract_fields_nullable_is_bool(youtube_fixture):
    """AC3: nullable 字段值必须是 bool 类型。"""
    fields = youtube.extract_fields(youtube_fixture)
    for f in fields:
        assert isinstance(f["nullable"], bool), f"nullable 应为 bool: {f}"


def test_extract_fields_data_type_valid(youtube_fixture):
    """AC3: data_type 必须是有效类型字符串。"""
    valid_types = {"string", "number", "boolean", "array", "object", "null"}
    fields = youtube.extract_fields(youtube_fixture)
    for f in fields:
        assert f["data_type"] in valid_types, f"无效 data_type: {f['data_type']} in {f}"


def test_extract_fields_contains_statistics_fields(youtube_fixture):
    """AC3: extract_fields() 应提取 statistics 下的字段（扁平化后含 statistics.xxx）。"""
    fields = youtube.extract_fields(youtube_fixture)
    field_names = [f["field_name"] for f in fields]
    assert any("viewCount" in name for name in field_names), \
        f"未找到包含 viewCount 的字段，已提取：{field_names}"


def test_extract_fields_contains_snippet_fields(youtube_fixture):
    """AC3: extract_fields() 应提取 snippet 下的字段（扁平化后含 snippet.xxx）。"""
    fields = youtube.extract_fields(youtube_fixture)
    field_names = [f["field_name"] for f in fields]
    assert any("title" in name for name in field_names), \
        f"未找到包含 title 的字段，已提取：{field_names}"


def test_extract_fields_nested_localized_flattened(youtube_fixture):
    """AC3: 双层嵌套（snippet.localized.*）应被递归扁平化提取。"""
    fields = youtube.extract_fields(youtube_fixture)
    field_names = [f["field_name"] for f in fields]
    # snippet.localized.title 应被展开
    assert any("localized" in name for name in field_names), \
        f"未找到 localized 字段，已提取：{field_names}"


def test_extract_fields_none_value_is_null_type(youtube_fixture):
    """AC3: 值为 None 的字段 data_type 应为 'null'，nullable 应为 True。"""
    sample = [{"field_a": "value", "field_b": None}]
    fields = youtube.extract_fields(sample)
    null_fields = [f for f in fields if f["field_name"] == "field_b"]
    assert len(null_fields) == 1
    assert null_fields[0]["data_type"] == "null"
    assert null_fields[0]["nullable"] is True


def test_extract_fields_string_number_in_statistics(youtube_fixture):
    """AC3: statistics 中数字以字符串形式返回（如 '1400000000'），data_type 应为 string。"""
    fields = youtube.extract_fields(youtube_fixture)
    view_count_fields = [f for f in fields if "viewCount" in f["field_name"]]
    assert len(view_count_fields) >= 1
    # YouTube API 将统计数值以字符串形式返回
    assert view_count_fields[0]["data_type"] == "string"
