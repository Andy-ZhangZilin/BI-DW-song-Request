"""TikTok Shop 数据源接入模块

认证流程（通过 DTC 中间层）：
  1. 调用 DTC getAccessToken → dtc_access_token
  2. 用 dtc_access_token 调用 DTC getTiktokShopSecret → TikTok access_token + cipher
  3. 用 TikTok access_token + cipher 调用 TikTok Open API

fetch_sample(table_name) 路由表（共 8 个，7 个有效接口 + 1 个暂无）：
  shop_product_performance        → GET  /analytics/202509/shop_products/{product_id}/performance
  affiliate_creator_orders        → POST /affiliate_creator/202410/orders/search
  video_performances              → GET  /analytics/202509/shop_videos/performance
  ad_spend                        → 暂无对应 Shop API，返回空列表
  return_refund                   → POST /return_refund/202602/returns/search
  affiliate_sample_status         → GET  /affiliate_partner/202508/campaigns/{campaign_id}/
                                         products/{product_id}/creator/{creator_temp_id}/
                                         content/statistics/sample/status
  affiliate_campaign_performance  → GET  /affiliate_partner/202508/campaigns/{campaign_id}/
                                         products/{product_id}/performance
  shop_video_performance_detail   → GET  /analytics/202509/shop_videos/{video_id}/performance

含动态路径参数的接口会优先读取 .env 中的配置，未配置时按以下规则自动获取：
  TIKTOK_PRODUCT_ID      — 商品 ID（可选，未配置时从 /product/202309/products/search 自动获取）
  TIKTOK_CAMPAIGN_ID     — 联盟活动 ID（可选，未配置时从 /authorization/202405/category_assets
                            + /affiliate_partner/202405/campaigns 两步自动获取）
  TIKTOK_CREATOR_TEMP_ID — 达人临时 ID（可选，未配置时从 /affiliate_creator/202410/orders/search
                            返回的第一条订单中自动获取）
  TIKTOK_VIDEO_ID        — 视频 ID（可选，未配置时从 /analytics/202509/shop_videos/performance
                            列表中自动获取第一个有数据的视频 ID）
"""
import hashlib
import hmac
import logging
import time
from typing import Dict, List, Optional, Tuple

import requests

import config.credentials as _creds_module

logger = logging.getLogger(__name__)

# TikTok Shop Open Platform API 基础 URL
BASE_URL = "https://open-api.tiktokglobalshop.com"

# DTC 中间层 API（华青 DTC 系统，管理 TikTok 店铺 OAuth 令牌）
_DTC_ACCESS_TOKEN_URL = "https://api.dtc.huaqing.run/api/hub/token/getAccessToken"
_DTC_SHOP_SECRET_URL = "https://api.dtc.huaqing.run/api/hub/common/getTiktokShopSecret"
_DTC_APP_ID = "finance-online-v1"
_DTC_APP_SECRET = "CBW3rpFfeobg85uu"

# HTTP 超时（架构规范：30s）
REQUEST_TIMEOUT = 30

# 支持的数据表名列表（8 个路由，7 个有效接口 + 1 个暂无的广告花费）
TABLES: List[str] = [
    "shop_product_performance",
    "affiliate_creator_orders",
    "video_performances",
    "ad_spend",
    "return_refund",
    "affiliate_sample_status",
    "affiliate_campaign_performance",
    "shop_video_performance_detail",
]

# 默认表（fetch_sample(None) 时使用）
_DEFAULT_TABLE: str = "return_refund"

# 模块级状态变量（仅在同一进程运行周期内有效，不跨进程持久化）
_access_token: Optional[str] = None
_shop_cipher: Optional[str] = None
# 所有店铺列表，每项含 access_token / cipher / shop_name，authenticate() 时填充
_all_shops: List[Dict] = []
# 视频 ID 缓存列表（由 _fetch_video_performances 填充，供 shop_video_performance_detail 复用）
_cached_video_ids: List[str] = []


# ---- 私有函数 ----

def _sign_request(app_secret: str, path: str, params: dict, body: Optional[dict] = None) -> str:
    """TikTok Shop API HmacSHA256 签名算法（含 path）。

    签名步骤（与 Java TiktokReqUtil.generateTtSign 完全一致）：
    1. 将参数（不含 sign 本身）按 key 字典序升序排列，拼接 key+value
    2. 在排好序的字符串前面加 path
    3. 若有 body，追加 body 的 JSON 字符串（必须与 requests 实际发送的格式完全一致）
    4. 首尾各拼接 app_secret：app_secret + (path+params[+body]) + app_secret
    5. 用 HMAC-SHA256（密钥 = app_secret）对上述字符串签名
    6. 取十六进制摘要（小写）

    注意：body 序列化使用 json.dumps 默认格式（带空格分隔符），与
    requests.post(json=body) 实际发送的字节流保持一致，不能用紧凑格式。
    """
    import json as _json
    sorted_params = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    sign_input = path + sorted_params
    if body is not None:
        sign_input += _json.dumps(body)
    sign_str = f"{app_secret}{sign_input}{app_secret}"
    signature = hmac.new(
        app_secret.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature


def _get_dtc_token() -> str:
    """通过 DTC 接口获取 DTC access_token。

    DTC 是华青内部中间层，统一管理各平台 OAuth 令牌。

    Raises:
        RuntimeError: 当 DTC 接口返回失败或缺少 access_token 时
    """
    params = {"app_id": _DTC_APP_ID, "app_secret": _DTC_APP_SECRET}
    resp = requests.get(_DTC_ACCESS_TOKEN_URL, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    token = data.get("data", {}).get("access_token")
    if not token:
        raise RuntimeError(f"DTC getAccessToken 失败：{data}")
    return token


def _get_tiktok_auth_via_dtc(app_key: str, app_secret: str) -> Tuple[str, str, List[Dict]]:
    """通过 DTC 获取 TikTok 店铺的 access_token、cipher 及所有店铺列表。

    主店铺优先选取包含 Piscifun 名称的店铺；若无匹配则使用第一条。

    Returns:
        (access_token, cipher, all_shops) 三元组；
        all_shops 中每项包含 access_token / cipher / shop_name / id。

    Raises:
        RuntimeError: 当 DTC 接口返回失败或无店铺数据时
    """
    dtc_token = _get_dtc_token()
    params = {"tiktok_app_key": app_key, "tiktok_app_secret": app_secret}
    headers = {"X-HUB-TOKEN": dtc_token, "Content-Type": "application/json"}
    resp = requests.get(
        _DTC_SHOP_SECRET_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 200:
        raise RuntimeError(f"DTC getTiktokShopSecret 失败：{data}")
    shops = data.get("data") or []
    if not shops:
        raise RuntimeError("DTC 返回的店铺列表为空")
    # 过滤掉缺少凭证的店铺条目
    valid_shops = [s for s in shops if s.get("access_token") and s.get("cipher")]
    if not valid_shops:
        raise RuntimeError("DTC 返回的店铺列表中无有效凭证条目")
    shop = next(
        (s for s in valid_shops if "Tidewe" in (s.get("shop_name") or "")),
        valid_shops[0],
    )
    access_token = shop.get("access_token")
    cipher = shop.get("cipher")
    logger.info(f"[tiktok] 主店铺：{shop.get('shop_name')}（id={shop.get('id')}），共 {len(valid_shops)} 个店铺")
    return access_token, cipher, valid_shops


def _build_signed_params(
    app_key: str,
    app_secret: str,
    path: str,
    body: Optional[dict] = None,
    include_shop_cipher: bool = True,
) -> dict:
    """构造带签名的 query 参数字典。

    Args:
        include_shop_cipher: 是否包含 shop_cipher。Shop 类接口需要（默认 True）；
            Affiliate 类接口（affiliate_creator_orders、video_performances）不需要，传 False。

    注：时间戳使用当前时间 -60s，以兼容 TikTok 服务端 ±300s 容差。
    """
    params: dict = {
        "app_key": app_key,
        "timestamp": str(int(time.time()) - 60),
    }
    if include_shop_cipher:
        params["shop_cipher"] = _shop_cipher
    params["sign"] = _sign_request(app_secret, path, params, body)
    return params


def _api_headers() -> dict:
    """返回 TikTok API 通用请求头。"""
    return {
        "x-tts-access-token": _access_token,
        "Content-Type": "application/json",
    }


def _extract_list_from_data(data: object) -> List[Dict]:
    """从 API 响应 data 字段中提取记录列表。

    若 data 是列表，直接返回。
    若 data 是字典，尝试常见 list key（list/items/records/results/performances/data），
    否则将整个 dict 包装为 [data] 返回（单条记录场景）。
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("list", "items", "records", "results", "performances", "data"):
            val = data.get(key)
            if isinstance(val, list) and val:
                return val
        return [data]
    return []


def _fetch_category_asset_cipher(app_key: str, app_secret: str) -> Optional[str]:
    """从 /authorization/202405/category_assets 自动获取第一个 category_asset_cipher。

    Affiliate Partner 类接口（campaigns / campaign performance 等）使用 category_asset_cipher
    而非 shop_cipher。此接口无需传 cipher 参数，只需 app_key/timestamp/sign 和 access_token。

    Required scope: partner.authorization.info

    Returns:
        category_asset_cipher 字符串，或 None（接口异常/无授权资产时）
    """
    path = "/authorization/202405/category_assets"
    sign_params: dict = {
        "app_key": app_key,
        "timestamp": str(int(time.time()) - 60),
    }
    sign_params["sign"] = _sign_request(app_secret, path, sign_params)
    sign_params["access_token"] = _access_token
    try:
        resp = requests.get(
            f"{BASE_URL}{path}",
            params=sign_params,
            headers=_api_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            logger.warning(
                f"[tiktok] category_assets 查询失败：code={data.get('code')} {data.get('message')}"
            )
            return None
        assets = (data.get("data") or {}).get("category_assets", [])
        if not assets:
            logger.warning("[tiktok] category_assets 列表为空，无法获取 category_asset_cipher")
            return None
        cipher = assets[0].get("cipher")
        logger.info(f"[tiktok] 自动获取 category_asset_cipher={cipher}")
        return cipher
    except Exception as e:
        logger.warning(f"[tiktok] 自动获取 category_asset_cipher 失败：{e}")
        return None


def _fetch_first_campaign_id(
    app_key: str, app_secret: str, category_asset_cipher: str
) -> Optional[str]:
    """从 /affiliate_partner/202405/campaigns 自动获取第一个 READY 状态的 campaign_id。

    Required scope: partner.tap_campaign.read

    Returns:
        campaign_id 字符串，或 None（接口异常/无活动时）
    """
    path = "/affiliate_partner/202405/campaigns"
    sign_params: dict = {
        "app_key": app_key,
        "category_asset_cipher": category_asset_cipher,
        "timestamp": str(int(time.time()) - 60),
        "type": "MY_CAMPAIGNS",
        "page_size": "20",
    }
    sign_params["sign"] = _sign_request(app_secret, path, sign_params)
    sign_params["access_token"] = _access_token
    try:
        resp = requests.get(
            f"{BASE_URL}{path}",
            params=sign_params,
            headers=_api_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            logger.warning(
                f"[tiktok] campaigns 列表查询失败：code={data.get('code')} {data.get('message')}"
            )
            return None
        campaigns = (data.get("data") or {}).get("campaigns", [])
        if not campaigns:
            logger.warning("[tiktok] campaigns 列表为空，无法自动获取 campaign_id")
            return None
        # 优先取 READY 状态的活动，无则取第一个
        ready = next((c for c in campaigns if c.get("status") == "READY"), None)
        campaign = ready or campaigns[0]
        campaign_id = campaign.get("id")
        logger.info(
            f"[tiktok] 自动获取 campaign_id={campaign_id}（status={campaign.get('status')}）"
        )
        return campaign_id
    except Exception as e:
        logger.warning(f"[tiktok] 自动获取 campaign_id 失败：{e}")
        return None


def _fetch_first_creator_temp_id(app_key: str, app_secret: str) -> Optional[str]:
    """从达人订单列表中自动获取第一个 creator_temp_id。

    调用 /affiliate_creator/202410/orders/search，取第一条订单的 creator_temp_id 字段。
    .env 中已配置 TIKTOK_CREATOR_TEMP_ID 时优先使用配置值，不再调用此接口。

    Returns:
        creator_temp_id 字符串，或 None（接口异常/无订单时）
    """
    path = "/affiliate_creator/202410/orders/search"
    payload: dict = {}
    sign_params: dict = {
        "app_key": app_key,
        "timestamp": str(int(time.time()) - 60),
        "page_size": "1",
    }
    sign_params["sign"] = _sign_request(app_secret, path, sign_params, payload)
    sign_params["access_token"] = _access_token
    try:
        resp = requests.post(
            f"{BASE_URL}{path}",
            params=sign_params,
            json=payload,
            headers=_api_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            logger.warning(
                f"[tiktok] 达人订单查询失败（获取 creator_temp_id）："
                f"code={data.get('code')} {data.get('message')}"
            )
            return None
        orders = (data.get("data") or {}).get("orders", [])
        if not orders:
            logger.warning("[tiktok] 达人订单列表为空，无法自动获取 creator_temp_id")
            return None
        creator_temp_id = orders[0].get("creator_temp_id")
        if creator_temp_id:
            logger.info(f"[tiktok] 自动获取 creator_temp_id={creator_temp_id}")
        else:
            logger.warning("[tiktok] 达人订单首条记录中无 creator_temp_id 字段")
        return creator_temp_id
    except Exception as e:
        logger.warning(f"[tiktok] 自动获取 creator_temp_id 失败：{e}")
        return None


def _fetch_first_product_id(app_key: str, app_secret: str) -> Optional[str]:
    """从商品列表接口自动获取第一个上架商品的 ID。

    用于 affiliate_sample_status / affiliate_campaign_performance 等需要 product_id 的接口。
    .env 中已配置 TIKTOK_PRODUCT_ID 时优先使用配置值，不再调用此接口。

    Returns:
        商品 ID 字符串，或 None（接口异常/无商品时）
    """
    ids = _fetch_product_ids(app_key, app_secret, limit=1)
    return ids[0] if ids else None


def _fetch_product_ids(app_key: str, app_secret: str, limit: int = 20) -> List[str]:
    """从商品列表接口获取多个上架商品 ID。

    Returns:
        商品 ID 列表，接口异常或无商品时返回空列表。
    """
    path = "/product/202309/products/search"
    sign_params: dict = {
        "app_key": app_key,
        "shop_cipher": _shop_cipher,
        "timestamp": str(int(time.time()) - 60),
        "page_size": str(min(limit, 50)),
    }
    body: dict = {}
    sign_params["sign"] = _sign_request(app_secret, path, sign_params, body)
    sign_params["access_token"] = _access_token
    try:
        resp = requests.post(
            f"{BASE_URL}{path}",
            params=sign_params,
            json=body,
            headers=_api_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            logger.warning(f"[tiktok] 商品列表查询失败：code={data.get('code')} {data.get('message')}")
            return []
        products = (data.get("data") or {}).get("products", [])
        if not products:
            logger.warning("[tiktok] 商品列表为空，无法自动获取 product_id")
            return []
        ids = [p.get("id") for p in products if p.get("id")]
        logger.info(f"[tiktok] 获取到 {len(ids)} 个商品 ID")
        return ids
    except Exception as e:
        logger.warning(f"[tiktok] 自动获取 product_ids 失败：{e}")
        return []


def _fetch_video_ids(app_key: str, app_secret: str, limit: int = 10) -> List[str]:
    """获取 video_id 列表，供 shop_video_performance_detail 轮询使用。

    优先返回 _cached_video_ids（由 _fetch_video_performances 运行后填充），
    避免重复请求列表接口。缓存为空时主动调用列表接口获取。

    Args:
        limit: 主动调用列表接口时的 page_size，默认 10。

    Returns:
        video_id 字符串列表，接口异常或无数据时返回空列表。
    """
    if _cached_video_ids:
        logger.info(f"[tiktok] 复用缓存 video_id 列表（共 {len(_cached_video_ids)} 个）")
        return _cached_video_ids

    # 缓存为空（单独运行 shop_video_performance_detail 时），主动调用列表接口
    logger.info("[tiktok] video_id 缓存为空，主动从视频列表接口获取 ...")
    from datetime import datetime, timedelta
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=30)
    path = "/analytics/202509/shop_videos/performance"
    sign_params: dict = {
        "app_key": app_key,
        "shop_cipher": _shop_cipher,
        "timestamp": str(int(time.time()) - 60),
        "start_date_ge": start_dt.strftime("%Y-%m-%d"),
        "end_date_lt": end_dt.strftime("%Y-%m-%d"),
        "page_size": str(limit),
    }
    sign_params["sign"] = _sign_request(app_secret, path, sign_params)
    try:
        resp = requests.get(
            f"{BASE_URL}{path}",
            params=sign_params,
            headers=_api_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            logger.warning(
                f"[tiktok] 视频列表查询失败（获取 video_ids）："
                f"code={data.get('code')} {data.get('message')}"
            )
            return []
        videos = (data.get("data") or {}).get("videos", [])
        if not videos:
            logger.warning("[tiktok] 视频列表为空，无法自动获取 video_id")
            return []
        ids = [v.get("id") for v in videos if v.get("id")]
        logger.info(f"[tiktok] 从视频列表获取到 {len(ids)} 个 video_id")
        return ids
    except Exception as e:
        logger.warning(f"[tiktok] 自动获取 video_ids 失败：{e}")
        return []


# ---- 各路由私有实现 ----

def _fetch_return_refund_for_shop(
    app_key: str, app_secret: str, access_token: str, cipher: str, shop_name: str
) -> List[Dict]:
    """对单个店铺查询退款记录（供 _fetch_return_refund 内部循环调用）。"""
    path = "/return_refund/202602/returns/search"
    payload: dict = {"page_size": 20}
    # 临时替换模块变量，使 _build_signed_params 和 _api_headers 使用指定店铺凭证
    saved_token, saved_cipher = _access_token, _shop_cipher
    # 直接构建签名参数，避免依赖模块变量
    sign_params: dict = {
        "app_key": app_key,
        "shop_cipher": cipher,
        "timestamp": str(int(time.time()) - 60),
    }
    sign_params["sign"] = _sign_request(app_secret, path, sign_params, payload)
    headers = {"x-tts-access-token": access_token, "Content-Type": "application/json"}
    try:
        resp = requests.post(
            f"{BASE_URL}{path}",
            params=sign_params,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            logger.warning(
                f"[tiktok] 店铺 {shop_name} 退款查询失败：code={data.get('code')} {data.get('message')}"
            )
            return []
        resp_data = data.get("data") or {}
        # API 实际返回字段为 return_orders（兼容 returns / return_list 旧格式）
        for key in ("return_orders", "returns", "return_list"):
            records = resp_data.get(key)
            if records:
                break
        records = records or []
        if records:
            logger.info(f"[tiktok] 店铺 {shop_name} 退款 {len(records)} 条")
        return records
    except Exception as e:
        logger.warning(f"[tiktok] 店铺 {shop_name} 退款查询异常：{e}")
        return []


def _fetch_return_refund(app_key: str, app_secret: str) -> List[Dict]:
    """POST /return_refund/202602/returns/search — 退款数据（遍历所有店铺）。

    遍历 _all_shops 中的所有店铺，合并各店铺退款记录，返回第一批有数据的结果。
    若所有店铺均无退款，返回空列表。
    """
    all_avail = _all_shops if _all_shops else [{"access_token": _access_token, "cipher": _shop_cipher, "shop_name": "default"}]
    # 仅查询已授权的 Tidewe 店铺；无匹配时回退到全部店铺
    shops = [s for s in all_avail if "Tidewe" in (s.get("shop_name") or "")] or all_avail
    logger.info(f"[tiktok] 获取退款样本（共 {len(shops)} 个店铺）...")
    all_records: List[Dict] = []
    for shop in shops:
        records = _fetch_return_refund_for_shop(
            app_key, app_secret,
            shop.get("access_token", ""),
            shop.get("cipher", ""),
            shop.get("shop_name", "unknown"),
        )
        all_records.extend(records)
    if not all_records:
        logger.warning("[tiktok] 所有店铺退款查询均返回空，字段发现将跳过")
        return []
    logger.info(f"[tiktok] 获取退款样本 ... 成功（共 {len(all_records)} 条记录）")
    return all_records


def _fetch_affiliate_creator_orders(app_key: str, app_secret: str) -> List[Dict]:
    """POST /affiliate_creator/202410/orders/search — 达人订单数据。

    page_size 必须作为 query param 参与签名（不能放在 body 里），否则 TikTok 报 36009004。
    """
    path = "/affiliate_creator/202410/orders/search"
    payload: dict = {}
    # page_size 必须放 query params（参与签名），不放 body
    sign_params: dict = {
        "app_key": app_key,
        "timestamp": str(int(time.time()) - 60),
        "page_size": "10",
    }
    sign_params["sign"] = _sign_request(app_secret, path, sign_params, payload)
    params = sign_params
    logger.info("[tiktok] 获取达人订单样本 ...")
    resp = requests.post(
        f"{BASE_URL}{path}",
        params=params,
        json=payload,
        headers=_api_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(
            f"[tiktok] 达人订单查询失败，code={data.get('code')}，message={data.get('message')}"
        )
    resp_data = data.get("data") or {}
    records = resp_data.get("orders", [])
    if not records:
        logger.warning("[tiktok] 达人订单查询返回空列表，字段发现将跳过")
        return []
    logger.info(f"[tiktok] 获取达人订单样本 ... 成功（{len(records)} 条记录）")
    return records


def _fetch_video_performances(app_key: str, app_secret: str) -> List[Dict]:
    """GET /analytics/202509/shop_videos/performance — 店铺视频表现列表（卖家视角）。

    原 /analytics/202403/videos/performances 为 US-creator-only 接口，需要 creator token，
    已切换为卖家端 /analytics/202509/shop_videos/performance，需要 shop_cipher 和
    data.shop_analytics.public.read scope（与 shop_product_performance 相同）。
    """
    from datetime import datetime, timedelta
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=30)
    path = "/analytics/202509/shop_videos/performance"
    sign_params: dict = {
        "app_key": app_key,
        "shop_cipher": _shop_cipher,
        "timestamp": str(int(time.time()) - 60),
        "start_date_ge": start_dt.strftime("%Y-%m-%d"),
        "end_date_lt": end_dt.strftime("%Y-%m-%d"),
        "page_size": "10",
    }
    sign_params["sign"] = _sign_request(app_secret, path, sign_params)
    params = sign_params
    logger.info("[tiktok] 获取店铺视频表现样本 ...")
    resp = requests.get(
        f"{BASE_URL}{path}",
        params=params,
        headers=_api_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(
            f"[tiktok] 视频表现查询失败，code={data.get('code')}，message={data.get('message')}"
        )
    resp_data = data.get("data") or {}
    # 按 API 文档结构返回顶层字段：latest_available_date / next_page_token / total_count / videos
    # videos 作为 array 字段保留，不展平，体现层级关系
    if not resp_data.get("videos") and not resp_data.get("total_count"):
        logger.warning("[tiktok] 视频表现查询返回空，字段发现将跳过")
        return []
    # 缓存 video_id 列表供 shop_video_performance_detail 复用，避免重复请求列表接口
    global _cached_video_ids
    ids = [v.get("id") for v in (resp_data.get("videos") or []) if v.get("id")]
    if ids:
        _cached_video_ids = ids
        logger.info(f"[tiktok] 缓存 {len(ids)} 个 video_id 供后续接口复用")
    logger.info(f"[tiktok] 获取视频表现样本 ... 成功（total_count={resp_data.get('total_count')}）")
    return [resp_data]


def _has_rich_performance_data(resp_data: Dict) -> bool:
    """判断 shop_product_performance 返回的数据是否包含完整字段（如 sales、traffic）。

    如果 intervals 内只有 start_date/end_date 而没有 sales 等字段，
    说明该产品没有实际销售数据，字段不完整。
    """
    perf = resp_data.get("performance", {})
    intervals = perf.get("intervals", [])
    if not intervals:
        return False
    first_interval = intervals[0]
    # 有 sales 或 traffic 字段就认为数据完整
    return "sales" in first_interval or "traffic" in first_interval


def _query_product_performance(
    app_key: str, app_secret: str, product_id: str
) -> Optional[Dict]:
    """对单个产品查询 performance，返回 resp_data（data 层），失败返回 None。"""
    from datetime import datetime, timedelta
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=30)
    path = f"/analytics/202509/shop_products/{product_id}/performance"
    sign_params: dict = {
        "app_key": app_key,
        "shop_cipher": _shop_cipher,
        "timestamp": str(int(time.time()) - 60),
        "start_date_ge": start_dt.strftime("%Y-%m-%d"),
        "end_date_lt": end_dt.strftime("%Y-%m-%d"),
    }
    sign_params["sign"] = _sign_request(app_secret, path, sign_params)
    logger.info(f"[tiktok] 获取店铺商品表现（product_id={product_id}）...")
    try:
        resp = requests.get(
            f"{BASE_URL}{path}",
            params=sign_params,
            headers=_api_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            logger.warning(
                f"[tiktok] 商品表现查询失败 product_id={product_id}，"
                f"code={data.get('code')}，message={data.get('message')}"
            )
            return None
        return data.get("data") or {}
    except Exception as e:
        logger.warning(f"[tiktok] 商品表现查询异常 product_id={product_id}：{e}")
        return None


def _fetch_shop_product_performance(app_key: str, app_secret: str) -> List[Dict]:
    """GET /analytics/202509/shop_products/{product_id}/performance — 店铺商品表现。

    自动从商品列表获取多个产品 ID，逐个查询直到找到有完整字段（含 sales/traffic）的产品。
    如果所有产品都没有完整数据，则返回字段最多的那个结果（确保字段发现尽量全面）。
    """
    product_ids = _fetch_product_ids(app_key, app_secret, limit=20)
    if not product_ids:
        logger.warning("[tiktok] 无法获取 product_id 列表，shop_product_performance 跳过")
        return []

    best_result: Optional[Dict] = None
    best_field_count = 0

    for pid in product_ids:
        resp_data = _query_product_performance(app_key, app_secret, pid)
        if not resp_data or not resp_data.get("performance"):
            continue

        # 统计 intervals 内的字段数量
        intervals = resp_data.get("performance", {}).get("intervals", [])
        field_count = len(intervals[0]) if intervals else 0

        if _has_rich_performance_data(resp_data):
            logger.info(
                f"[tiktok] 找到有完整数据的产品 product_id={pid}（interval 字段数={field_count}）"
            )
            return [resp_data]

        # 记录字段最多的结果作为兜底
        if field_count > best_field_count:
            best_field_count = field_count
            best_result = resp_data

    if best_result:
        logger.warning(
            f"[tiktok] 未找到有完整 sales/traffic 数据的产品，"
            f"使用字段最多的结果（字段数={best_field_count}）"
        )
        return [best_result]

    logger.warning("[tiktok] 所有产品均无有效表现数据，shop_product_performance 跳过")
    return []


def _fetch_affiliate_sample_status(app_key: str, app_secret: str) -> List[Dict]:
    """GET /affiliate_partner/202508/campaigns/{campaign_id}/products/{product_id}/
    creator/{creator_temp_id}/content/statistics/sample/status — 获取寄样数。

    campaign_id 优先读 .env TIKTOK_CAMPAIGN_ID，未配置时自动从 campaigns 列表获取。
    product_id 优先读 .env TIKTOK_PRODUCT_ID，未配置时自动从商品列表获取。
    creator_temp_id 必须在 .env 中配置 TIKTOK_CREATOR_TEMP_ID，无法自动获取。

    此接口使用 category_asset_cipher（非 shop_cipher）。
    """
    campaign_id = _creds_module.get_optional_config("TIKTOK_CAMPAIGN_ID")
    product_id = _creds_module.get_optional_config("TIKTOK_PRODUCT_ID")
    creator_temp_id = _creds_module.get_optional_config("TIKTOK_CREATOR_TEMP_ID")

    if not product_id:
        product_id = _fetch_first_product_id(app_key, app_secret)

    if not campaign_id:
        logger.info("[tiktok] TIKTOK_CAMPAIGN_ID 未配置，尝试自动获取 ...")
        cipher = _fetch_category_asset_cipher(app_key, app_secret)
        if cipher:
            campaign_id = _fetch_first_campaign_id(app_key, app_secret, cipher)

    if not creator_temp_id:
        logger.info("[tiktok] TIKTOK_CREATOR_TEMP_ID 未配置，尝试从达人订单自动获取 ...")
        creator_temp_id = _fetch_first_creator_temp_id(app_key, app_secret)

    if not creator_temp_id:
        logger.warning("[tiktok] 无法获取 creator_temp_id，affiliate_sample_status 跳过")
        return []
    if not campaign_id or not product_id:
        logger.warning(
            "[tiktok] campaign_id/product_id 获取失败，affiliate_sample_status 跳过"
        )
        return []

    path = (
        f"/affiliate_partner/202508/campaigns/{campaign_id}"
        f"/products/{product_id}"
        f"/creator/{creator_temp_id}"
        f"/content/statistics/sample/status"
    )
    params = _build_signed_params(app_key, app_secret, path, include_shop_cipher=False)
    logger.info("[tiktok] 获取联盟寄样状态 ...")
    resp = requests.get(
        f"{BASE_URL}{path}",
        params=params,
        headers=_api_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(
            f"[tiktok] 联盟寄样状态查询失败，code={data.get('code')}，message={data.get('message')}"
        )
    resp_data = data.get("data") or {}
    records = _extract_list_from_data(resp_data)
    if not records:
        logger.warning("[tiktok] 联盟寄样状态返回空，字段发现将跳过")
        return []
    logger.info("[tiktok] 获取联盟寄样状态 ... 成功")
    return records


def _fetch_affiliate_campaign_performance(app_key: str, app_secret: str) -> List[Dict]:
    """GET /affiliate_partner/202508/campaigns/{campaign_id}/products/{product_id}/performance
    — 联盟活动履约状态。

    campaign_id 优先读 .env TIKTOK_CAMPAIGN_ID，未配置时通过 category_assets + campaigns 列表自动获取。
    product_id 优先读 .env TIKTOK_PRODUCT_ID，未配置时自动从商品列表获取。

    此接口使用 category_asset_cipher（非 shop_cipher）。
    """
    campaign_id = _creds_module.get_optional_config("TIKTOK_CAMPAIGN_ID")
    product_id = _creds_module.get_optional_config("TIKTOK_PRODUCT_ID")

    if not product_id:
        product_id = _fetch_first_product_id(app_key, app_secret)

    if not campaign_id:
        logger.info("[tiktok] TIKTOK_CAMPAIGN_ID 未配置，尝试自动获取 ...")
        cipher = _fetch_category_asset_cipher(app_key, app_secret)
        if cipher:
            campaign_id = _fetch_first_campaign_id(app_key, app_secret, cipher)

    if not campaign_id or not product_id:
        logger.warning(
            "[tiktok] campaign_id/product_id 获取失败，affiliate_campaign_performance 跳过"
        )
        return []

    path = f"/affiliate_partner/202508/campaigns/{campaign_id}/products/{product_id}/performance"
    params = _build_signed_params(app_key, app_secret, path, include_shop_cipher=False)
    logger.info("[tiktok] 获取联盟活动履约状态 ...")
    resp = requests.get(
        f"{BASE_URL}{path}",
        params=params,
        headers=_api_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(
            f"[tiktok] 联盟活动履约状态查询失败，code={data.get('code')}，message={data.get('message')}"
        )
    resp_data = data.get("data") or {}
    records = _extract_list_from_data(resp_data)
    if not records:
        logger.warning("[tiktok] 联盟活动履约状态返回空，字段发现将跳过")
        return []
    logger.info("[tiktok] 获取联盟活动履约状态 ... 成功")
    return records


def _query_video_performance_detail(
    app_key: str, app_secret: str, video_id: str
) -> Optional[Dict]:
    """对单个视频查询 performance detail，返回 resp_data（data 层），失败返回 None。"""
    from datetime import datetime, timedelta
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=30)
    path = f"/analytics/202509/shop_videos/{video_id}/performance"
    sign_params: dict = {
        "app_key": app_key,
        "shop_cipher": _shop_cipher,
        "timestamp": str(int(time.time()) - 60),
        "start_date_ge": start_dt.strftime("%Y-%m-%d"),
        "end_date_lt": end_dt.strftime("%Y-%m-%d"),
    }
    sign_params["sign"] = _sign_request(app_secret, path, sign_params)
    logger.info(f"[tiktok] 获取单视频详细表现（video_id={video_id}）...")
    try:
        resp = requests.get(
            f"{BASE_URL}{path}",
            params=sign_params,
            headers=_api_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            logger.warning(
                f"[tiktok] 视频详情查询失败 video_id={video_id}，"
                f"code={data.get('code')}，message={data.get('message')}"
            )
            return None
        return data.get("data") or {}
    except Exception as e:
        logger.warning(f"[tiktok] 视频详情查询异常 video_id={video_id}：{e}")
        return None


def _fetch_shop_video_performance_detail(app_key: str, app_secret: str) -> List[Dict]:
    """GET /analytics/202509/shop_videos/{video_id}/performance — 单视频详细表现数据。

    与 video_performances（店铺视频列表）不同，此接口针对单个视频返回更详细的
    时间维度表现数据（按日/周/月分段）。

    video_id 优先读 .env TIKTOK_VIDEO_ID（单个固定值）；未配置时从 _fetch_video_ids()
    获取多个候选 ID（优先复用 video_performances 缓存，避免重复请求），逐个尝试直到
    找到有数据的视频。

    Required scope: data.shop_analytics.public.read（与 shop_product_performance 相同）
    """
    fixed_id = _creds_module.get_optional_config("TIKTOK_VIDEO_ID")
    if fixed_id:
        resp_data = _query_video_performance_detail(app_key, app_secret, fixed_id)
        if resp_data:
            logger.info(f"[tiktok] 获取单视频详细表现 ... 成功（video_id={fixed_id}）")
            return [resp_data]
        logger.warning(f"[tiktok] TIKTOK_VIDEO_ID={fixed_id} 无数据，shop_video_performance_detail 跳过")
        return []

    logger.info("[tiktok] TIKTOK_VIDEO_ID 未配置，尝试从视频列表自动获取候选 ID ...")
    video_ids = _fetch_video_ids(app_key, app_secret, limit=10)
    if not video_ids:
        logger.warning("[tiktok] 无法获取 video_id 列表，shop_video_performance_detail 跳过")
        return []

    for vid in video_ids:
        resp_data = _query_video_performance_detail(app_key, app_secret, vid)
        if resp_data:
            logger.info(f"[tiktok] 获取单视频详细表现 ... 成功（video_id={vid}）")
            return [resp_data]

    logger.warning("[tiktok] 所有候选 video_id 均无数据，shop_video_performance_detail 跳过")
    return []


# ---- 路由分发表 ----

_ROUTE_HANDLERS = {
    "shop_product_performance": _fetch_shop_product_performance,
    "affiliate_creator_orders": _fetch_affiliate_creator_orders,
    "video_performances": _fetch_video_performances,
    "return_refund": _fetch_return_refund,
    "affiliate_sample_status": _fetch_affiliate_sample_status,
    "affiliate_campaign_performance": _fetch_affiliate_campaign_performance,
    "shop_video_performance_detail": _fetch_shop_video_performance_detail,
}


# ---- 公开接口（必须严格遵守三函数契约）----

def authenticate() -> bool:
    """验证 TikTok Shop 凭证是否有效。

    流程：
    1. 从 get_credentials() 获取 TIKTOK_APP_KEY 和 TIKTOK_APP_SECRET
    2. 通过 DTC 两步获取 TikTok access_token 和 shop_cipher
    3. 将 access_token 和 shop_cipher 存入模块级变量供 fetch_sample 使用

    Returns:
        True: 认证成功
        False: 认证失败（已记录错误日志）
    """
    global _access_token, _shop_cipher, _all_shops
    try:
        creds = _creds_module.get_credentials()
        logger.info("[tiktok] 认证 ...")
        _access_token, _shop_cipher, _all_shops = _get_tiktok_auth_via_dtc(
            creds["TIKTOK_APP_KEY"],
            creds["TIKTOK_APP_SECRET"],
        )
        logger.info("[tiktok] 认证 ... 成功")
        return True
    except Exception as e:
        logger.error(f"[tiktok] 认证 ... 失败：{e}")
        _access_token = None
        _shop_cipher = None
        _all_shops = []
        return False


def fetch_sample(table_name: Optional[str] = None) -> List[Dict]:
    """抓取 TikTok Shop 指定接口的样本数据。

    根据 table_name 路由到对应接口。table_name=None 时使用默认表（return_refund）。
    ad_spend 接口暂无对应 Shop API，直接返回空列表并记录警告。
    含动态路径参数的接口若 .env 未配置对应 ID，同样返回空列表。

    Args:
        table_name: 接口名称，见 TABLES 常量；None 时使用 _DEFAULT_TABLE。

    Returns:
        list[dict]: 原始 API 响应中的记录列表，无数据时返回空列表

    Raises:
        RuntimeError: 认证未完成或 API 调用失败
        ValueError: table_name 不在 TABLES 中
    """
    if not _access_token or not _shop_cipher:
        raise RuntimeError("[tiktok] fetch_sample 调用前必须先成功调用 authenticate()")

    table = table_name or _DEFAULT_TABLE

    if table == "ad_spend":
        logger.warning("[tiktok] 广告花费接口暂无 Shop API 支持，跳过")
        return []

    handler = _ROUTE_HANDLERS.get(table)
    if handler is None:
        raise ValueError(f"[tiktok] 未知 table_name: {table}，有效值：{TABLES}")

    creds = _creds_module.get_credentials()
    return handler(creds["TIKTOK_APP_KEY"], creds["TIKTOK_APP_SECRET"])


def extract_fields(sample: List[Dict]) -> List[Dict]:
    """从样本记录中提取字段信息（递归展开嵌套结构）。

    递归遍历嵌套 dict 和 array，使用点号分隔路径表示层级关系：
    - dict 嵌套：parent.child
    - array 嵌套：parent[].child（取第一个元素展开）

    叶子节点（string/number/boolean/null）和空 array/dict 作为最终字段输出。

    Returns:
        list[dict]: 标准 FieldInfo 格式列表，每项含 field_name/data_type/sample_value/nullable
    """
    if not sample:
        return []

    first_record = sample[0]
    fields: List[Dict] = []

    def _infer_type(value: object) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "number"
        if isinstance(value, float):
            return "number"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        return "string"

    def _truncate_sample(value: object, max_len: int = 200) -> object:
        """截断过长的 sample_value，避免报告表格过宽。"""
        s = str(value)
        if len(s) <= max_len:
            return value
        return s[:max_len] + "..."

    def _walk(obj: object, prefix: str) -> None:
        """递归遍历，将叶子字段追加到 fields 列表。"""
        if isinstance(obj, dict):
            if not obj:
                # 空 dict，作为叶子输出
                fields.append({
                    "field_name": prefix,
                    "data_type": "object",
                    "sample_value": {},
                    "nullable": False,
                })
                return
            for key, value in obj.items():
                child_path = f"{prefix}.{key}" if prefix else key
                _walk(value, child_path)
        elif isinstance(obj, list):
            if not obj:
                # 空 array，作为叶子输出
                fields.append({
                    "field_name": prefix,
                    "data_type": "array",
                    "sample_value": [],
                    "nullable": False,
                })
                return
            # 取第一个元素展开，路径加 []
            first_elem = obj[0]
            arr_path = f"{prefix}[]"
            if isinstance(first_elem, dict):
                _walk(first_elem, arr_path)
            else:
                # 基础类型数组，直接输出
                fields.append({
                    "field_name": arr_path,
                    "data_type": f"array<{_infer_type(first_elem)}>",
                    "sample_value": _truncate_sample(obj),
                    "nullable": False,
                })
        else:
            # 叶子节点（string/number/boolean/null）
            fields.append({
                "field_name": prefix,
                "data_type": _infer_type(obj),
                "sample_value": _truncate_sample(obj),
                "nullable": obj is None,
            })

    _walk(first_record, "")

    return fields
