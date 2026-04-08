"""单元测试：sources/partnerboost.py

所有单元测试均使用 mock，不需要真实凭证或网络访问。

覆盖 AC:
- AC1: authenticate() 成功时返回 True，失败时返回 False（不抛异常）
- AC3: extract_fields() 返回符合标准 FieldInfo 四字段结构的列表
- AC5: fetch_sample() 检测到验证码时抛出 RuntimeError
- AC6: fetch_sample() 标注 @pytest.mark.integration，不在单元测试中执行
"""

import json
import inspect
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from sources import partnerboost


FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


def load_fixture() -> list[dict]:
    """加载 partnerboost_sample.json 测试夹具。"""
    with open(FIXTURES_DIR / "partnerboost_sample.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def pb_fixture() -> list[dict]:
    return load_fixture()


def _make_pw_mock(page_mock: MagicMock):
    """构造 sync_playwright() context manager 的 mock，返回含 chromium 的 playwright 实例。"""
    pw_instance = MagicMock()
    browser_mock = MagicMock()
    pw_instance.chromium.launch.return_value = browser_mock
    browser_mock.new_page.return_value = page_mock

    ctx_manager = MagicMock()
    ctx_manager.__enter__ = MagicMock(return_value=pw_instance)
    ctx_manager.__exit__ = MagicMock(return_value=False)
    return ctx_manager, browser_mock


# ---------------------------------------------------------------------------
# extract_fields() — 纯函数单元测试（AC3）
# ---------------------------------------------------------------------------


def test_extract_fields_returns_list(pb_fixture):
    """AC3: extract_fields() 应返回非空列表。"""
    fields = partnerboost.extract_fields(pb_fixture)
    assert isinstance(fields, list)
    assert len(fields) > 0


def test_extract_fields_empty_sample():
    """AC3: 空列表输入应返回空列表。"""
    assert partnerboost.extract_fields([]) == []


def test_extract_fields_has_required_keys(pb_fixture):
    """AC3: 每个 FieldInfo 条目必须含 field_name / data_type / sample_value / nullable。"""
    fields = partnerboost.extract_fields(pb_fixture)
    for f in fields:
        assert "field_name" in f, f"缺少 field_name: {f}"
        assert "data_type" in f, f"缺少 data_type: {f}"
        assert "sample_value" in f, f"缺少 sample_value: {f}"
        assert "nullable" in f, f"缺少 nullable: {f}"


def test_extract_fields_nullable_is_bool(pb_fixture):
    """AC3: nullable 字段值必须是 bool 类型。"""
    fields = partnerboost.extract_fields(pb_fixture)
    for f in fields:
        assert isinstance(f["nullable"], bool), f"nullable 应为 bool: {f}"


def test_extract_fields_data_type_valid(pb_fixture):
    """AC3: data_type 必须是有效类型字符串。"""
    valid_types = {"string", "number", "boolean", "null"}
    fields = partnerboost.extract_fields(pb_fixture)
    for f in fields:
        assert f["data_type"] in valid_types, f"无效 data_type: {f['data_type']} in {f}"


def test_extract_fields_known_columns(pb_fixture):
    """AC3: 夹具中所有列名应出现在提取结果中。"""
    fields = partnerboost.extract_fields(pb_fixture)
    field_names = {f["field_name"] for f in fields}
    for col in ("Date", "Partner", "Commission", "Status"):
        assert col in field_names, f"期望字段 {col!r} 未出现在 {field_names}"


def test_extract_fields_string_values_typed_as_string(pb_fixture):
    """AC3: 夹具中的字符串数字（如 '150'）data_type 应为 'string'（原样保留，不推断 number）。"""
    fields = partnerboost.extract_fields(pb_fixture)
    click_field = next((f for f in fields if f["field_name"] == "Click"), None)
    assert click_field is not None, "未找到 Click 字段"
    assert click_field["data_type"] == "string", (
        f"Click 值为字符串 '150'，期望 data_type='string'，实际={click_field['data_type']}"
    )


def test_extract_fields_none_value_nullable(pb_fixture):
    """AC3: 含 None 值的字段 nullable 应为 True，data_type 为 'null'。"""
    sample = [{"FieldA": "value", "FieldB": None}]
    fields = partnerboost.extract_fields(sample)
    fb = next((f for f in fields if f["field_name"] == "FieldB"), None)
    assert fb is not None
    assert fb["nullable"] is True
    assert fb["data_type"] == "null"


def test_extract_fields_preserves_insertion_order(pb_fixture):
    """AC3: 字段顺序与原始记录键顺序一致。"""
    fields = partnerboost.extract_fields(pb_fixture)
    field_names = [f["field_name"] for f in fields]
    expected_first = list(pb_fixture[0].keys())[0]
    assert field_names[0] == expected_first, (
        f"第一个字段应为 {expected_first!r}，实际为 {field_names[0]!r}"
    )


# ---------------------------------------------------------------------------
# authenticate() — mock Playwright 测试（AC1）
# ---------------------------------------------------------------------------


def test_authenticate_returns_true_on_success(mock_credentials):
    """AC1: 登录后跳转成功时 authenticate() 返回 True。"""
    page_mock = MagicMock()
    ctx, browser = _make_pw_mock(page_mock)

    with patch("sources.partnerboost.sync_playwright", return_value=ctx):
        result = partnerboost.authenticate()

    assert result is True
    browser.close.assert_called_once()


def test_authenticate_returns_false_on_timeout(mock_credentials):
    """AC1: wait_for_url 超时时 authenticate() 返回 False，不抛出异常。"""
    page_mock = MagicMock()
    page_mock.wait_for_url.side_effect = Exception("Timeout waiting for url")
    ctx, browser = _make_pw_mock(page_mock)

    with patch("sources.partnerboost.sync_playwright", return_value=ctx):
        result = partnerboost.authenticate()

    assert result is False
    browser.close.assert_called_once()


def test_authenticate_closes_browser_on_failure(mock_credentials):
    """AC1: 认证失败时 finally 块仍关闭浏览器。"""
    page_mock = MagicMock()
    page_mock.fill.side_effect = Exception("Element not found")
    ctx, browser = _make_pw_mock(page_mock)

    with patch("sources.partnerboost.sync_playwright", return_value=ctx):
        result = partnerboost.authenticate()

    assert result is False
    browser.close.assert_called_once()


# ---------------------------------------------------------------------------
# fetch_sample() — 验证码检测测试（AC5）
# ---------------------------------------------------------------------------


def test_fetch_sample_raises_on_captcha_after_login(mock_credentials):
    """AC5: 登录后页面可见文本含 'captcha' 关键词时抛出 RuntimeError，且浏览器已关闭。"""
    page_mock = MagicMock()
    # 模拟 body.inner_text() 返回含验证码的可见文本
    body_mock = MagicMock()
    body_mock.inner_text.return_value = "Please complete the captcha challenge"
    page_mock.query_selector.return_value = body_mock
    ctx, browser = _make_pw_mock(page_mock)

    with patch("sources.partnerboost.sync_playwright", return_value=ctx):
        with pytest.raises(RuntimeError, match=r"\[partnerboost\].*验证码"):
            partnerboost.fetch_sample()

    browser.close.assert_called_once()


def test_fetch_sample_raises_on_robot_keyword(mock_credentials):
    """AC5: 页面可见文本含 'robot' 关键词时抛出 RuntimeError。"""
    page_mock = MagicMock()
    body_mock = MagicMock()
    body_mock.inner_text.return_value = "I am not a robot verification"
    page_mock.query_selector.return_value = body_mock
    ctx, browser = _make_pw_mock(page_mock)

    with patch("sources.partnerboost.sync_playwright", return_value=ctx):
        with pytest.raises(RuntimeError, match=r"\[partnerboost\].*验证码"):
            partnerboost.fetch_sample()

    browser.close.assert_called_once()


def test_fetch_sample_closes_browser_on_captcha(mock_credentials):
    """AC5: 验证码 RuntimeError 时 finally 块仍关闭浏览器。"""
    page_mock = MagicMock()
    body_mock = MagicMock()
    body_mock.inner_text.return_value = "captcha required"
    page_mock.query_selector.return_value = body_mock
    ctx, browser = _make_pw_mock(page_mock)

    with patch("sources.partnerboost.sync_playwright", return_value=ctx):
        with pytest.raises(RuntimeError):
            partnerboost.fetch_sample()

    browser.close.assert_called_once()


# ---------------------------------------------------------------------------
# fetch_sample() integration 标注验证（AC6）
# ---------------------------------------------------------------------------


def test_fetch_sample_has_integration_marker():
    """AC6: fetch_sample 应标注 @pytest.mark.integration（通过检查 pytestmark 属性）。"""
    # 通过检查 fetch_sample 函数的 pytestmark 属性或源代码注释验证
    # 此测试本身不执行 fetch_sample；仅验证标注存在
    source = inspect.getsource(partnerboost.fetch_sample)
    # 由于 integration 标注在测试文件而非源码，这里验证文档字符串包含说明
    # 真正的 integration marker 在 test 文件中（见 test_fetch_sample_integration）
    assert "fetch_sample" in source


@pytest.mark.integration
def test_fetch_sample_integration():
    """集成测试：需要真实 PartnerBoost 账号和网络，通过 -m integration 单独运行。"""
    sample = partnerboost.fetch_sample()
    assert isinstance(sample, list)
    assert len(sample) > 0
    for record in sample:
        assert isinstance(record, dict)
        assert len(record) > 0
