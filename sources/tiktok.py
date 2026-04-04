"""TikTok Shop 数据源接入模块

认证流程（通过 DTC 中间层）：
  1. 调用 DTC getAccessToken → dtc_access_token
  2. 用 dtc_access_token 调用 DTC getTiktokShopSecret → TikTok access_token + cipher
  3. 用 TikTok access_token + cipher 调用 TikTok Open API
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

# 模块级状态变量（仅在同一进程运行周期内有效，不跨进程持久化）
_access_token: Optional[str] = None
_shop_cipher: Optional[str] = None


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
    if body:
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


def _get_tiktok_auth_via_dtc(app_key: str, app_secret: str) -> Tuple[str, str]:
    """通过 DTC 获取 TikTok 店铺的 access_token 和 cipher。

    返回包含 Piscifun 品牌的店铺认证信息；若无匹配则使用第一条。

    Returns:
        (access_token, cipher) 元组

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

    shops = data.get("data", [])
    if not shops:
        raise RuntimeError("DTC 返回的店铺列表为空")

    # 优先选择店铺名包含 "Piscifun" 的店铺
    shop = next(
        (s for s in shops if "Piscifun" in (s.get("shop_name") or "")),
        shops[0],
    )

    access_token = shop.get("access_token")
    cipher = shop.get("cipher")
    if not access_token or not cipher:
        raise RuntimeError(f"DTC 返回的店铺数据缺少 access_token 或 cipher：{shop}")

    logger.info(f"[tiktok] 使用店铺：{shop.get('shop_name')}（id={shop.get('id')}）")
    return access_token, cipher


# ---- 公开接口（必须严格遵守三函数契约）----

def authenticate() -> bool:
    """验证 TikTok Shop 凭证是否有效。

    流程：
    1. 从 get_credentials() 获取凭证
    2. 用 refresh_token 换取 access_token
    3. 用 access_token 获取 shop_cipher（验证可用性）
    4. 将 access_token 和 shop_cipher 存入模块级变量供 fetch_sample 使用

    Returns:
        True: 认证成功
        False: 认证失败（已记录错误日志）
    """
    global _access_token, _shop_cipher
    try:
        creds = _creds_module.get_credentials()
        logger.info("[tiktok] 认证 ...")

        _access_token, _shop_cipher = _get_tiktok_auth_via_dtc(
            creds["TIKTOK_APP_KEY"],
            creds["TIKTOK_APP_SECRET"],
        )

        logger.info("[tiktok] 认证 ... 成功")
        return True

    except Exception as e:
        logger.error(f"[tiktok] 认证 ... 失败：{e}")
        _access_token = None
        _shop_cipher = None
        return False


def fetch_sample(table_name: Optional[str] = None) -> List[Dict]:
    """抓取 TikTok Shop 退款样本数据（用于验证 API 连通性和字段发现）。

    调用 /return_refund/202602/returns/search，返回退款记录。

    注意：
    - /affiliate_creator/202410/orders/search（达人订单数据）需要达人级别 token，
      不支持 DTC 提供的店铺 token，因此改用退款端点验证连通性。
    - 退款端点需要 shop_cipher 在 query params 中，且签名必须包含请求 body。
    - 若当前店铺无退款历史，返回空列表（字段发现将跳过，但认证/连通性验证仍通过）。

    table_name 参数忽略（TikTok 只使用一个样本端点）。

    Returns:
        list[dict]: 原始 API 响应中的退款记录列表，无数据时返回空列表

    Raises:
        RuntimeError: 认证未完成或 API 调用失败
    """
    if not _access_token or not _shop_cipher:
        raise RuntimeError("[tiktok] fetch_sample 调用前必须先成功调用 authenticate()")

    creds = _creds_module.get_credentials()
    app_key = creds["TIKTOK_APP_KEY"]
    app_secret = creds["TIKTOK_APP_SECRET"]

    path = "/return_refund/202602/returns/search"
    payload: dict = {"page_size": 20}

    # return_refund 端点需要 shop_cipher 在 query params 中
    params: dict = {
        "app_key": app_key,
        "shop_cipher": _shop_cipher,
        "timestamp": str(int(time.time()) - 60),
    }
    # 签名必须包含 body（使用 json.dumps 默认格式，与 requests 发送格式一致）
    params["sign"] = _sign_request(app_secret, path, params, payload)

    logger.info("[tiktok] 获取退款样本 ...")
    resp = requests.post(
        f"{BASE_URL}{path}",
        params=params,
        json=payload,
        headers={"x-tts-access-token": _access_token, "Content-Type": "application/json"},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(
            f"[tiktok] 退款查询失败，code={data.get('code')}，message={data.get('message')}"
        )

    resp_data = data.get("data") or {}
    records = resp_data.get("returns") or resp_data.get("return_list", [])
    if not records:
        logger.warning("[tiktok] 退款查询返回空列表（当前店铺无退款历史），字段发现将跳过")
        return []

    logger.info(f"[tiktok] 获取退款样本 ... 成功（{len(records)} 条记录）")
    return records


def extract_fields(sample: List[Dict]) -> List[Dict]:
    """从订单样本中提取字段信息。

    从第一条订单记录中提取所有顶层字段，推断数据类型（string/number/boolean/array/object/null）。
    嵌套结构（如 recipient_address、skus）作为整体字段返回，不展开内层键。

    Returns:
        list[dict]: 标准 FieldInfo 格式列表，每项含 field_name/data_type/sample_value/nullable
    """
    if not sample:
        return []

    first_record = sample[0]
    fields: List[Dict] = []

    def _infer_type(value) -> str:
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

    for key, value in first_record.items():
        fields.append({
            "field_name": key,
            "data_type": _infer_type(value),
            "sample_value": value,
            "nullable": value is None,
        })

    return fields
