"""TikTok Shop 数据采集落库单元测试（Story 7.2）。

所有外部依赖（TikTokClient、write_to_doris、水位线）均通过 mock 隔离，
测试不需要真实的 TikTok 凭证或 Doris 连接。
"""

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest

# 将 outdoor_collector/ 根加入路径
sys.path.insert(0, "bi/python_sdk/outdoor_collector")
sys.path.insert(0, "bi/python_sdk/outdoor_collector/collectors")

import tiktok_collector as tc


# ---------------------------------------------------------------------------
# 工具 fixture
# ---------------------------------------------------------------------------

FAKE_ENV = {"TIKTOK_APP_KEY": "test_key", "TIKTOK_APP_SECRET": "test_secret"}


def _make_client_mock():
    """返回已认证的 TikTokClient mock。"""
    mock = MagicMock()
    mock.access_token = "fake_token"
    mock.shop_cipher  = "fake_cipher"
    return mock


# ---------------------------------------------------------------------------
# 测试：正常路径（6 个路由全部写入成功）
# ---------------------------------------------------------------------------

@patch.dict(os.environ, FAKE_ENV)
@patch("tiktok_collector.TikTokClient")
@patch("tiktok_collector.get_watermark", return_value=None)
@patch("tiktok_collector.update_watermark")
@patch("tiktok_collector.write_to_doris", return_value=10)
def test_collect_all_routes_happy_path(mock_write, mock_upd, mock_get_wm, mock_cls):
    """collect() 正常路径：6 个路由均成功写入 Doris（AC1-4）。"""
    mock_cls.return_value = _make_client_mock()

    fake_records = {
        "return_refund":               [{"return_id": "r1", "order_id": "o1"}],
        "affiliate_creator_orders":    [{"order_id": "o2"}],
        "video_performances":          [{"video_id": "v1", "collect_date": "2026-01-01"}],
        "shop_product_performance":    [{"product_id": "p1", "collect_date": "2026-01-01"}],
        "affiliate_campaign_performance": [{"campaign_id": "c1", "product_id": "p1", "collect_date": "2026-01-01"}],
        "affiliate_sample_status":     [{"campaign_id": "c1", "product_id": "p1", "creator_temp_id": "t1", "collect_date": "2026-01-01"}],
    }

    with patch.object(tc, "_collect_return_refund",            return_value=fake_records["return_refund"]), \
         patch.object(tc, "_collect_affiliate_creator_orders", return_value=fake_records["affiliate_creator_orders"]), \
         patch.object(tc, "_collect_video_performances",       return_value=fake_records["video_performances"]), \
         patch.object(tc, "_collect_shop_product_performance", return_value=fake_records["shop_product_performance"]), \
         patch.object(tc, "_collect_affiliate_campaign_performance", return_value=fake_records["affiliate_campaign_performance"]), \
         patch.object(tc, "_collect_affiliate_sample_status",  return_value=fake_records["affiliate_sample_status"]):
        results = tc.collect(mode="incremental")

    assert set(results.keys()) == set(tc.ROUTES.keys())
    assert all(v == 10 for v in results.values()), f"期望每路由写入 10 行，实际：{results}"
    assert mock_write.call_count == 6
    assert mock_upd.call_count == 6


# ---------------------------------------------------------------------------
# 测试：单路由失败不影响其他路由
# ---------------------------------------------------------------------------

@patch.dict(os.environ, FAKE_ENV)
@patch("tiktok_collector.TikTokClient")
@patch("tiktok_collector.get_watermark", return_value=None)
@patch("tiktok_collector.update_watermark")
@patch("tiktok_collector.write_to_doris", return_value=5)
def test_single_route_failure_does_not_propagate(mock_write, mock_upd, mock_get_wm, mock_cls):
    """单路由失败不传染（AC7）：return_refund 抛异常，其余 5 个正常写入。"""
    mock_cls.return_value = _make_client_mock()

    with patch.object(tc, "_collect_return_refund",            side_effect=RuntimeError("API error")), \
         patch.object(tc, "_collect_affiliate_creator_orders", return_value=[{"order_id": "o1"}]), \
         patch.object(tc, "_collect_video_performances",       return_value=[{"video_id": "v1", "collect_date": "2026-01-01"}]), \
         patch.object(tc, "_collect_shop_product_performance", return_value=[{"product_id": "p1", "collect_date": "2026-01-01"}]), \
         patch.object(tc, "_collect_affiliate_campaign_performance", return_value=[{"campaign_id": "c1", "product_id": "p1", "collect_date": "2026-01-01"}]), \
         patch.object(tc, "_collect_affiliate_sample_status",  return_value=[{"campaign_id": "c1", "product_id": "p1", "creator_temp_id": "t1", "collect_date": "2026-01-01"}]):
        results = tc.collect(mode="incremental")

    assert results["return_refund"] == 0, "失败路由应返回 0"
    assert results["affiliate_creator_orders"] == 5, "正常路由应正常写入"
    assert mock_write.call_count == 5, "仅 5 个路由写入"


# ---------------------------------------------------------------------------
# 测试：空数据跳过写入
# ---------------------------------------------------------------------------

@patch.dict(os.environ, FAKE_ENV)
@patch("tiktok_collector.TikTokClient")
@patch("tiktok_collector.get_watermark", return_value=None)
@patch("tiktok_collector.update_watermark")
@patch("tiktok_collector.write_to_doris")
def test_empty_data_skips_write(mock_write, mock_upd, mock_get_wm, mock_cls):
    """所有路由返回空列表时，不写入 Doris，结果均为 0（AC8）。"""
    mock_cls.return_value = _make_client_mock()

    with patch.object(tc, "_collect_return_refund",            return_value=[]), \
         patch.object(tc, "_collect_affiliate_creator_orders", return_value=[]), \
         patch.object(tc, "_collect_video_performances",       return_value=[]), \
         patch.object(tc, "_collect_shop_product_performance", return_value=[]), \
         patch.object(tc, "_collect_affiliate_campaign_performance", return_value=[]), \
         patch.object(tc, "_collect_affiliate_sample_status",  return_value=[]):
        results = tc.collect(mode="incremental")

    mock_write.assert_not_called()
    mock_upd.assert_not_called()
    assert all(v == 0 for v in results.values())


# ---------------------------------------------------------------------------
# 测试：--mode full 触发 reset_watermark
# ---------------------------------------------------------------------------

@patch.dict(os.environ, FAKE_ENV)
@patch("tiktok_collector.TikTokClient")
@patch("tiktok_collector.get_watermark", return_value=None)
@patch("tiktok_collector.update_watermark")
@patch("tiktok_collector.reset_watermark")
@patch("tiktok_collector.write_to_doris", return_value=1)
def test_full_mode_resets_watermarks(mock_write, mock_reset, mock_upd, mock_get_wm, mock_cls):
    """--mode full 为每个路由调用 reset_watermark（AC6）。"""
    mock_cls.return_value = _make_client_mock()

    with patch.object(tc, "_collect_return_refund",            return_value=[{"return_id": "r1"}]), \
         patch.object(tc, "_collect_affiliate_creator_orders", return_value=[{"order_id": "o1"}]), \
         patch.object(tc, "_collect_video_performances",       return_value=[{"video_id": "v1", "collect_date": "2026-01-01"}]), \
         patch.object(tc, "_collect_shop_product_performance", return_value=[{"product_id": "p1", "collect_date": "2026-01-01"}]), \
         patch.object(tc, "_collect_affiliate_campaign_performance", return_value=[{"campaign_id": "c1", "product_id": "p1", "collect_date": "2026-01-01"}]), \
         patch.object(tc, "_collect_affiliate_sample_status",  return_value=[{"campaign_id": "c1", "product_id": "p1", "creator_temp_id": "t1", "collect_date": "2026-01-01"}]):
        tc.collect(mode="full")

    # 6 个路由各重置一次
    assert mock_reset.call_count == 6


# ---------------------------------------------------------------------------
# 测试：dry_run 不写入
# ---------------------------------------------------------------------------

@patch.dict(os.environ, FAKE_ENV)
@patch("tiktok_collector.TikTokClient")
@patch("tiktok_collector.get_watermark", return_value=None)
@patch("tiktok_collector.update_watermark")
@patch("tiktok_collector.write_to_doris")
def test_dry_run_skips_write(mock_write, mock_upd, mock_get_wm, mock_cls):
    """dry_run=True 时不调用 write_to_doris，返回 0。"""
    mock_cls.return_value = _make_client_mock()

    with patch.object(tc, "_collect_return_refund",            return_value=[{"return_id": "r1"}]), \
         patch.object(tc, "_collect_affiliate_creator_orders", return_value=[{"order_id": "o1"}]), \
         patch.object(tc, "_collect_video_performances",       return_value=[{"video_id": "v1", "collect_date": "2026-01-01"}]), \
         patch.object(tc, "_collect_shop_product_performance", return_value=[{"product_id": "p1", "collect_date": "2026-01-01"}]), \
         patch.object(tc, "_collect_affiliate_campaign_performance", return_value=[{"campaign_id": "c1", "product_id": "p1", "collect_date": "2026-01-01"}]), \
         patch.object(tc, "_collect_affiliate_sample_status",  return_value=[{"campaign_id": "c1", "product_id": "p1", "creator_temp_id": "t1", "collect_date": "2026-01-01"}]):
        results = tc.collect(mode="incremental", dry_run=True)

    mock_write.assert_not_called()
    assert all(v == 0 for v in results.values())


# ---------------------------------------------------------------------------
# 测试：_check_code 抛 RuntimeError
# ---------------------------------------------------------------------------

def test_check_code_raises_on_nonzero():
    """_check_code 在 code != 0 时抛出 RuntimeError（AC1 防御）。"""
    with pytest.raises(RuntimeError, match="code=10000"):
        tc._check_code({"code": 10000, "message": "Invalid params"}, "/test/path")


def test_check_code_passes_on_zero():
    """_check_code 在 code=0 时不抛异常。"""
    tc._check_code({"code": 0, "data": {}}, "/test/path")  # 无异常


# ---------------------------------------------------------------------------
# 测试：凭证缺失抛异常
# ---------------------------------------------------------------------------

@patch.dict(os.environ, {}, clear=True)
def test_missing_credentials_raises():
    """未配置凭证时 _get_client() 抛 RuntimeError（AC1 防御）。"""
    with pytest.raises(RuntimeError, match="TIKTOK_APP_KEY"):
        tc._get_client()


# ---------------------------------------------------------------------------
# 测试：增量模式归因窗口 3 天
# ---------------------------------------------------------------------------

def test_get_time_range_order_attribution_window():
    """订单类路由增量模式：start_ts = 水位线时间 - 3 天（AC3）。"""
    wm_time = datetime(2026, 4, 10, 12, 0, 0)
    mock_wm = {"last_success_time": wm_time}
    cfg = {"table": "hqware.ods_tiktok_return_refund", "route_type": "order"}

    with patch("tiktok_collector.get_watermark", return_value=mock_wm):
        start_ts, end_ts = tc._get_time_range(cfg, mode="incremental", start_date_arg=None)

    # 实现将日期字符串 "2026-04-07" 转回 timestamp，截断到当天 00:00:00
    expected_start = datetime(2026, 4, 7, 0, 0, 0)  # 10 - 3 = 7，截断到当天起始
    assert start_ts == int(expected_start.timestamp()), (
        f"归因窗口应回溯 3 天，期望 start_ts={int(expected_start.timestamp())}，实际={start_ts}"
    )
    assert end_ts > start_ts


# ---------------------------------------------------------------------------
# 测试：无效路由参数
# ---------------------------------------------------------------------------

@patch.dict(os.environ, FAKE_ENV)
def test_invalid_route_raises():
    """指定无效路由时抛 ValueError。"""
    with pytest.raises(ValueError, match="未知路由"):
        tc.collect(route="nonexistent_route")


# ---------------------------------------------------------------------------
# 测试：D1 修复 — _fetch_creator_temp_id 传入过滤条件
# ---------------------------------------------------------------------------

def test_fetch_creator_temp_id_passes_filters():
    """_fetch_creator_temp_id 将 campaign_id/product_id 注入请求 body（D1 修复）。"""
    mock_client = _make_client_mock()
    mock_client.post.return_value = {
        "code": 0,
        "data": {"orders": [{"creator_temp_id": "cid_001"}]},
    }
    result = tc._fetch_creator_temp_id(mock_client, campaign_id="camp_1", product_id="prod_2")
    assert result == "cid_001"
    body = mock_client.post.call_args.kwargs.get("body", {})
    assert body.get("campaign_id") == "camp_1", "body 应包含 campaign_id 过滤条件"
    assert body.get("product_id") == "prod_2", "body 应包含 product_id 过滤条件"


# ---------------------------------------------------------------------------
# 测试：D2 修复 — collect_date = end_date - 1（数据所属日期）
# ---------------------------------------------------------------------------

def test_video_performances_collect_date_is_data_date():
    """collect_date 应为 end_date - 1 而非 end_date（D2 修复）。"""
    mock_client = _make_client_mock()
    mock_client.get.return_value = {
        "code": 0,
        "data": {"videos": [{"video_id": "v1"}]},
    }
    records = tc._collect_video_performances(mock_client, "2026-04-01", "2026-04-16")
    assert records[0]["collect_date"] == "2026-04-15", (
        "collect_date 应为 end_date - 1（2026-04-15），不是采集运行日 2026-04-16"
    )
