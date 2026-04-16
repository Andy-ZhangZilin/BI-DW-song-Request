"""tests/test_partnerboost_collector.py

单元测试：bi/python_sdk/outdoor_collector/collectors/partnerboost_collector.py

策略：
- _transform() / _to_int() / _to_float() / _norm() 等纯函数直接测试
- collect() 使用 mock playwright + mock write_to_doris，不依赖真实网络或 Doris
- 爬虫集成测试标注 @pytest.mark.integration，单元测试模式下跳过
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# 将 collector 目录加入 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../bi/python_sdk/outdoor_collector"))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "../bi/python_sdk/outdoor_collector/collectors"),
)

import partnerboost_collector as pc


# ─────────────────────────────────────────────────────────────
# _norm()
# ─────────────────────────────────────────────────────────────

def test_norm_basic():
    assert pc._norm("Payment Status") == "payment_status"
    assert pc._norm("  Click  ") == "click"
    assert pc._norm("PARTNER") == "partner"


# ─────────────────────────────────────────────────────────────
# _to_int()
# ─────────────────────────────────────────────────────────────

def test_to_int_normal():
    assert pc._to_int("150") == 150


def test_to_int_with_comma():
    assert pc._to_int("1,234") == 1234


def test_to_int_none():
    assert pc._to_int(None) is None


def test_to_int_empty_string():
    assert pc._to_int("") is None


def test_to_int_invalid():
    assert pc._to_int("N/A") is None


def test_to_int_decimal_string():
    """Patch 3: '1,234.00' 应降级为 int(float(...)) 返回 1234"""
    assert pc._to_int("1,234.00") == 1234
    assert pc._to_int("100.0") == 100


# ─────────────────────────────────────────────────────────────
# _to_float()
# ─────────────────────────────────────────────────────────────

def test_to_float_normal():
    assert abs(pc._to_float("299.97") - 299.97) < 0.001


def test_to_float_with_dollar():
    assert abs(pc._to_float("$50.00") - 50.0) < 0.001


def test_to_float_with_comma_and_dollar():
    assert abs(pc._to_float("$1,234.56") - 1234.56) < 0.001


def test_to_float_none():
    assert pc._to_float(None) is None


def test_to_float_empty():
    assert pc._to_float("") is None


def test_to_float_invalid():
    assert pc._to_float("N/A") is None


# ─────────────────────────────────────────────────────────────
# _transform()
# ─────────────────────────────────────────────────────────────

def _sample_raw():
    return [
        {
            "Partner": "BestReviews",
            "Click": "150",
            "Sale": "3",
            "Revenue": "$299.97",
            "Commission": "$29.99",
            "Status": "Approved",
            "Channel": "Content",
            "Payment Status": "Pending",
        }
    ]


def test_transform_basic_fields():
    result = pc._transform(_sample_raw(), "2026-04-15")
    assert len(result) == 1
    r = result[0]
    assert r["collect_date"] == "2026-04-15"
    assert r["partner"] == "BestReviews"
    assert r["clicks"] == 150
    assert r["sales"] == 3
    assert abs(r["revenue"] - 299.97) < 0.01
    assert abs(r["commission"] - 29.99) < 0.01
    assert r["status"] == "Approved"
    assert r["channel"] == "Content"
    assert r["payment_status"] == "Pending"


def test_transform_empty_input():
    assert pc._transform([], "2026-04-15") == []


def test_transform_missing_numeric_fields():
    """缺失数值字段应置 None，不抛异常"""
    raw = [{"Partner": "Foo"}]
    result = pc._transform(raw, "2026-04-15")
    assert len(result) == 1
    r = result[0]
    assert r["partner"] == "Foo"
    assert r["clicks"] is None
    assert r["revenue"] is None
    assert r["commission"] is None


def test_transform_clicks_variant_column_name():
    """兼容 'Clicks'（复数）列名"""
    raw = [{"Partner": "Bar", "Clicks": "200", "Sales": "5",
            "Revenue": "100.00", "Commission": "10.00",
            "Status": "Pending", "Channel": "Email", "Payment Status": "Paid"}]
    result = pc._transform(raw, "2026-04-15")
    assert result[0]["clicks"] == 200
    assert result[0]["sales"] == 5


def test_transform_multiple_rows():
    raw = [
        {"Partner": "A", "Click": "10", "Sale": "1",
         "Revenue": "50.00", "Commission": "5.00",
         "Status": "Approved", "Channel": "Content", "Payment Status": "Pending"},
        {"Partner": "B", "Click": "20", "Sale": "2",
         "Revenue": "100.00", "Commission": "10.00",
         "Status": "Approved", "Channel": "Social", "Payment Status": "Paid"},
    ]
    result = pc._transform(raw, "2026-04-15")
    assert len(result) == 2
    assert result[0]["partner"] == "A"
    assert result[1]["partner"] == "B"


def test_transform_all_have_collect_date():
    raw = _sample_raw() * 3
    result = pc._transform(raw, "2026-01-01")
    assert all(r["collect_date"] == "2026-01-01" for r in result)


# ─────────────────────────────────────────────────────────────
# _scrape_all_rows()  — 使用 mock page
# ─────────────────────────────────────────────────────────────

def _make_cell(text: str):
    m = MagicMock()
    m.inner_text.return_value = text
    return m


def test_scrape_all_rows_no_headers():
    page = MagicMock()
    page.query_selector_all.side_effect = lambda sel: [] if "thead" in sel else []
    result = pc._scrape_all_rows(page)
    assert result == []


def test_scrape_all_rows_happy_path():
    page = MagicMock()
    headers = ["Partner", "Click", "Revenue"]
    row1_cells = ["Foo", "10", "50.00"]

    header_mocks = [_make_cell(h) for h in headers]
    row_mock = MagicMock()
    cell_mocks = [_make_cell(v) for v in row1_cells]
    row_mock.query_selector_all.return_value = cell_mocks

    def qs_all(sel):
        if "thead" in sel:
            return header_mocks
        if "tbody tr" in sel:
            return [row_mock]
        return []

    page.query_selector_all.side_effect = qs_all
    result = pc._scrape_all_rows(page)
    assert len(result) == 1
    assert result[0] == {"Partner": "Foo", "Click": "10", "Revenue": "50.00"}


# ─────────────────────────────────────────────────────────────
# collect() — mock playwright + mock write_to_doris
# ─────────────────────────────────────────────────────────────

def _build_playwright_mock(scrape_return=None):
    """构造标准 playwright mock，_scrape_all_rows 可单独 patch。"""
    mock_pw_ctx = MagicMock()
    mock_p = MagicMock()
    mock_browser = MagicMock()
    mock_page = MagicMock()

    mock_pw_ctx.__enter__ = MagicMock(return_value=mock_p)
    mock_pw_ctx.__exit__ = MagicMock(return_value=False)
    mock_p.chromium.launch.return_value = mock_browser
    mock_browser.new_page.return_value = mock_page

    # body.inner_text 无验证码
    mock_body = MagicMock()
    mock_body.inner_text.return_value = "normal page content"
    mock_page.query_selector.return_value = mock_body

    return mock_pw_ctx, mock_page


@patch("partnerboost_collector.write_to_doris", return_value=1)
@patch("partnerboost_collector.sync_playwright")
@patch("partnerboost_collector._scrape_all_rows")
@patch("partnerboost_collector._login")
def test_collect_happy_path(mock_login, mock_scrape, mock_pw, mock_write):
    mock_pw_ctx, mock_page = _build_playwright_mock()
    mock_pw.return_value = mock_pw_ctx
    mock_scrape.return_value = [
        {"Partner": "X", "Click": "10", "Sale": "1",
         "Revenue": "20.00", "Commission": "2.00",
         "Status": "Approved", "Channel": "Content", "Payment Status": "Pending"}
    ]

    env = {"PARTNERBOOST_USERNAME": "user@test.com", "PARTNERBOOST_PASSWORD": "secret"}
    with patch.dict(os.environ, env):
        written = pc.collect("2026-04-15")

    assert written == 1
    mock_write.assert_called_once()
    call_args = mock_write.call_args
    assert call_args[0][0] == pc.TABLE
    assert call_args[0][2] == pc.UNIQUE_KEYS


@patch("partnerboost_collector.write_to_doris")
@patch("partnerboost_collector.sync_playwright")
@patch("partnerboost_collector._login")
def test_collect_no_data_rows(mock_login, mock_pw, mock_write):
    """当日无数据行：wait_for_selector 超时，返回 0，不调用 write_to_doris"""
    mock_pw_ctx, mock_page = _build_playwright_mock()
    mock_pw.return_value = mock_pw_ctx
    # wait_for_selector 超时
    mock_page.wait_for_selector.side_effect = Exception("Timeout")

    env = {"PARTNERBOOST_USERNAME": "u", "PARTNERBOOST_PASSWORD": "p"}
    with patch.dict(os.environ, env):
        written = pc.collect("2026-04-15")

    assert written == 0
    mock_write.assert_not_called()


@patch("partnerboost_collector.sync_playwright", None)
def test_collect_playwright_not_installed():
    """Patch 4: playwright 未安装时应抛出 RuntimeError 而非 TypeError"""
    env = {"PARTNERBOOST_USERNAME": "u", "PARTNERBOOST_PASSWORD": "p"}
    with patch.dict(os.environ, env):
        with pytest.raises(RuntimeError, match="playwright 未安装"):
            pc.collect("2026-04-15")


@patch("partnerboost_collector.write_to_doris")
@patch("partnerboost_collector.sync_playwright")
@patch("partnerboost_collector._login")
def test_collect_captcha_during_no_data_timeout(mock_login, mock_pw, mock_write):
    """Patch 1: wait_for_selector 超时时若有验证码，应抛出 RuntimeError 而非返回 0"""
    mock_pw_ctx, mock_page = _build_playwright_mock()
    mock_pw.return_value = mock_pw_ctx
    mock_page.wait_for_selector.side_effect = Exception("Timeout")

    # 超时后页面显示验证码
    mock_body = MagicMock()
    mock_body.inner_text.return_value = "please complete captcha verification"
    mock_page.query_selector.return_value = mock_body

    env = {"PARTNERBOOST_USERNAME": "u", "PARTNERBOOST_PASSWORD": "p"}
    with patch.dict(os.environ, env):
        with pytest.raises(RuntimeError, match="验证码"):
            pc.collect("2026-04-15")
    mock_write.assert_not_called()


def test_collect_missing_credentials():
    """未配置凭证时抛出 RuntimeError"""
    env = {"PARTNERBOOST_USERNAME": "", "PARTNERBOOST_PASSWORD": ""}
    with patch.dict(os.environ, env, clear=False):
        # 确保 env 中无凭证
        os.environ.pop("PARTNERBOOST_USERNAME", None)
        os.environ.pop("PARTNERBOOST_PASSWORD", None)
        with pytest.raises(RuntimeError, match="未配置"):
            pc.collect("2026-04-15")


@patch("partnerboost_collector.sync_playwright")
@patch("partnerboost_collector._login")
def test_collect_captcha_raises(mock_login, mock_pw):
    """检测到验证码时抛出 RuntimeError"""
    mock_pw_ctx, mock_page = _build_playwright_mock()
    mock_pw.return_value = mock_pw_ctx

    mock_body = MagicMock()
    mock_body.inner_text.return_value = "please complete captcha to continue"
    mock_page.query_selector.return_value = mock_body

    env = {"PARTNERBOOST_USERNAME": "u", "PARTNERBOOST_PASSWORD": "p"}
    with patch.dict(os.environ, env):
        with pytest.raises(RuntimeError, match="验证码"):
            pc.collect("2026-04-15")


@pytest.mark.integration
def test_collect_integration_real_network():
    """集成测试：需要真实凭证和网络，标注 integration 在单元测试模式下跳过"""
    username = os.environ.get("PARTNERBOOST_USERNAME", "")
    password = os.environ.get("PARTNERBOOST_PASSWORD", "")
    if not username or not password:
        pytest.skip("未配置 PARTNERBOOST 凭证，跳过集成测试")
    written = pc.collect()
    assert isinstance(written, int)
    assert written >= 0
