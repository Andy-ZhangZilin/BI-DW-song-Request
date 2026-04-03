"""TikTok Shop 数据源接入模块

认证流程：refresh_token → access_token（每次重新获取，不缓存）
         → shop_cipher（通过 /api/shops/get_authorized_shop 自动获取）
"""
import hashlib
import hmac
import logging
import time
from typing import Optional

import requests

import config.credentials as _creds_module

logger = logging.getLogger(__name__)

# TikTok Shop Open Platform API 基础 URL
BASE_URL = "https://open-api.tiktokglobalshop.com"

# HTTP 超时（架构规范：30s）
REQUEST_TIMEOUT = 30

# 模块级状态变量（仅在同一进程运行周期内有效，不跨进程持久化）
_access_token: Optional[str] = None
_shop_cipher: Optional[str] = None


# ---- 私有函数 ----

def _sign_request(app_secret: str, params: dict) -> str:
    """TikTok Shop API HmacSHA256 签名算法。

    签名步骤（来源：TikTok Shop Open Platform 官方文档）：
    1. 将参数（不含 sign 本身）按 key 字典序升序排列
    2. 拼接所有 key+value 为字符串
    3. 首尾各拼接 app_secret：app_secret + sorted_params + app_secret
    4. 用 HMAC-SHA256（密钥 = app_secret）对上述字符串签名
    5. 取十六进制摘要（小写）
    """
    sorted_params = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    sign_str = f"{app_secret}{sorted_params}{app_secret}"
    signature = hmac.new(
        app_secret.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature


def _refresh_access_token(creds: dict) -> str:
    """用 refresh_token 换取新的 access_token（每次调用均重新获取，不缓存）。

    注：时间戳不需要偏移，直接使用当前 Unix 时间戳（秒级）。
    TikTok 服务端允许 ±300 秒的时间差（架构备注：初始架构提到"时间戳略靠前偏移"，
    经验证直接使用当前时间戳即可，无需强制偏移）。

    Raises:
        RuntimeError: 当 API 返回非 0 code 或响应中缺少 access_token 时
    """
    app_key = creds["TIKTOK_APP_KEY"]
    app_secret = creds["TIKTOK_APP_SECRET"]
    refresh_token = creds["TIKTOK_REFRESH_TOKEN"]

    params: dict = {
        "app_key": app_key,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "timestamp": str(int(time.time())),
    }
    params["sign"] = _sign_request(app_secret, params)

    resp = requests.get(
        f"{BASE_URL}/api/v2/token/refresh",
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(
            f"Token 刷新失败，code={data.get('code')}，message={data.get('message')}"
        )

    access_token = data.get("data", {}).get("access_token")
    if not access_token:
        raise RuntimeError("Token 刷新响应中缺少 access_token 字段")

    return access_token


def _get_shop_cipher(app_key: str, app_secret: str, access_token: str) -> str:
    """通过 /api/shops/get_authorized_shop 获取 shop_cipher。

    shop_cipher 是 TikTok Shop 每个店铺的加密标识符，每个 API 请求必须携带。

    Raises:
        RuntimeError: 当 API 返回失败或无 shop_cipher 时
    """
    params: dict = {
        "app_key": app_key,
        "access_token": access_token,
        "timestamp": str(int(time.time())),
    }
    params["sign"] = _sign_request(app_secret, params)

    resp = requests.get(
        f"{BASE_URL}/api/shops/get_authorized_shop",
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(
            f"获取 shop_cipher 失败，code={data.get('code')}，message={data.get('message')}"
        )

    shops = data.get("data", {}).get("shops", [])
    if not shops:
        raise RuntimeError("获取 shop_cipher 失败：shops 列表为空")

    shop_cipher = shops[0].get("cipher")
    if not shop_cipher:
        raise RuntimeError("获取 shop_cipher 失败：cipher 字段缺失")

    return shop_cipher


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

        _access_token = _refresh_access_token(creds)
        _shop_cipher = _get_shop_cipher(
            creds["TIKTOK_APP_KEY"],
            creds["TIKTOK_APP_SECRET"],
            _access_token,
        )

        logger.info("[tiktok] 认证 ... 成功")
        return True

    except Exception as e:
        logger.error(f"[tiktok] 认证 ... 失败：{e}")
        _access_token = None
        _shop_cipher = None
        return False


def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """抓取 TikTok Shop 订单样本数据。

    调用 /api/orders/search，返回至少一条订单记录。
    table_name 参数忽略（TikTok 只有一个端点）。

    Returns:
        list[dict]: 原始 API 响应中的订单记录列表

    Raises:
        RuntimeError: 认证未完成或 API 调用失败
    """
    if not _access_token or not _shop_cipher:
        raise RuntimeError("[tiktok] fetch_sample 调用前必须先成功调用 authenticate()")

    creds = _creds_module.get_credentials()
    app_key = creds["TIKTOK_APP_KEY"]
    app_secret = creds["TIKTOK_APP_SECRET"]

    # 构造请求参数（query string）
    params: dict = {
        "app_key": app_key,
        "access_token": _access_token,
        "shop_cipher": _shop_cipher,
        "timestamp": str(int(time.time())),
    }
    # 请求体（JSON body）
    payload: dict = {"page_size": 1}

    # 签名时包含 query params + body 参数
    params["sign"] = _sign_request(app_secret, {**params, **payload})

    logger.info("[tiktok] 获取订单样本 ...")
    resp = requests.post(
        f"{BASE_URL}/api/orders/search",
        params=params,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(
            f"[tiktok] 订单查询失败，code={data.get('code')}，message={data.get('message')}"
        )

    orders = data.get("data", {}).get("order_list", [])
    if not orders:
        raise RuntimeError("[tiktok] 订单查询返回空列表，无法完成字段发现")

    logger.info(f"[tiktok] 获取订单样本 ... 成功（{len(orders)} 条记录）")
    return orders


def extract_fields(sample: list[dict]) -> list[dict]:
    """从订单样本中提取字段信息。

    从第一条订单记录中提取所有顶层字段，推断数据类型（string/number/boolean/array/object/null）。
    嵌套结构（如 recipient_address、skus）作为整体字段返回，不展开内层键。

    Returns:
        list[dict]: 标准 FieldInfo 格式列表，每项含 field_name/data_type/sample_value/nullable
    """
    if not sample:
        return []

    first_record = sample[0]
    fields: list[dict] = []

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
