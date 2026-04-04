"""TripleWhale 数据源接入模块

认证方式：X-API-KEY header
接入表：pixel_orders_table / pixel_joined_tvf / sessions_table / product_analytics_tvf /
        pixel_keywords_joined_tvf / ads_table / social_media_comments_table /
        social_media_pages_table / creatives_table / ai_visibility_table
shopDomain：piscifun.myshopify.com（固定）

公开接口（统一 source 契约）：
    authenticate() -> bool
    fetch_sample(table_name: str = None) -> list[dict]
    extract_fields(sample: list[dict]) -> list[dict]
"""
import logging
from typing import Optional

import requests

import config.credentials as _creds_module
from config.credentials import mask_credential

logger = logging.getLogger(__name__)

# --- 常量 ---
BASE_URL: str = "https://api.triplewhale.com/api/v2/tw-metrics"
SHOP_DOMAIN: str = "piscifun.myshopify.com"
DEFAULT_TIMEOUT: int = 30  # 秒，与架构规范一致
TABLES: list[str] = [
    "pixel_orders_table",
    "pixel_joined_tvf",
    "sessions_table",
    "product_analytics_tvf",
    "pixel_keywords_joined_tvf",
    "ads_table",
    "social_media_comments_table",
    "social_media_pages_table",
    "creatives_table",
    "ai_visibility_table",
]
_DEFAULT_TABLE: str = "pixel_orders_table"


# ---------------------------------------------------------------------------
# 公开接口（统一 source 契约）
# ---------------------------------------------------------------------------

def authenticate() -> bool:
    """验证 TRIPLEWHALE_API_KEY 是否有效。

    通过向 metrics-data 端点发送探测请求来验证 API Key。
    成功返回 True，失败打印错误并返回 False。
    日志格式：[triplewhale] 认证 ... 成功/失败：{原因}

    Returns:
        True 表示认证成功，False 表示认证失败。
    """
    try:
        api_key = _get_api_key()
        logger.info(f"[triplewhale] 认证中，使用 API Key: {mask_credential(api_key)}")
        resp = requests.get(
            f"{BASE_URL}/metrics-data",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            params={"shopDomain": SHOP_DOMAIN},
            timeout=DEFAULT_TIMEOUT,
        )
        # HTTP 200 或 400（参数不完整但 Key 有效）均视为认证成功
        if resp.status_code in (200, 400):
            logger.info("[triplewhale] 认证 ... 成功")
            return True
        logger.error(
            f"[triplewhale] 认证 ... 失败：HTTP {resp.status_code} {resp.text[:200]}"
        )
        return False
    except requests.Timeout:
        logger.error("[triplewhale] 认证 ... 失败：请求超时")
        return False
    except Exception as e:
        logger.error(f"[triplewhale] 认证 ... 失败：{e}")
        return False


def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """抓取指定表的样本数据。

    Args:
        table_name: 表名，必须为 TABLES 中的一个。
                    为 None 时使用 pixel_orders_table（默认主表）。

    Returns:
        至少一条原始记录的列表（list[dict]）。

    Raises:
        ValueError: table_name 不在 TABLES 中
        requests.Timeout: 请求超时
        RuntimeError: API 返回非 2xx 状态码或返回空数据
    """
    resolved_table = table_name if table_name is not None else _DEFAULT_TABLE
    if resolved_table not in TABLES:
        raise ValueError(f"未知表名：{resolved_table}，可用：{TABLES}")

    api_key = _get_api_key()
    logger.info(f"[triplewhale] 获取 {resolved_table} 样本 ...")
    try:
        sample = _fetch_table(resolved_table, api_key)
    except requests.Timeout:
        logger.error(f"[triplewhale] 获取 {resolved_table} 样本 ... 失败：请求超时")
        raise
    except Exception as e:
        logger.error(f"[triplewhale] 获取 {resolved_table} 样本 ... 失败：{e}")
        raise
    logger.info(f"[triplewhale] 获取 {resolved_table} 样本 ... 成功，共 {len(sample)} 条记录")
    return sample


def extract_fields(sample: list[dict]) -> list[dict]:
    """从样本数据中提取标准 FieldInfo 列表。

    遍历样本中所有记录以确定字段完整性（nullable 检测）。
    返回按字段名字母序排列的 FieldInfo 列表。

    Args:
        sample: fetch_sample() 返回的原始记录列表。

    Returns:
        FieldInfo 列表，每项结构：
        {
            "field_name": str,      # 字段名（API 返回的原始键名）
            "data_type": str,       # string / number / boolean / array / object / null
            "sample_value": Any,    # 首条记录的值
            "nullable": bool        # 该字段在所有样本中是否存在 None/null 值
        }
    """
    if not sample:
        return []

    # 收集所有记录中出现的字段名
    all_keys: set[str] = set()
    for record in sample:
        all_keys.update(record.keys())

    fields: list[dict] = []
    for key in sorted(all_keys):
        first_val = sample[0].get(key)
        # nullable = 任意记录中该字段为 None，或该字段在某记录中缺失
        nullable = any(rec.get(key) is None for rec in sample)
        fields.append({
            "field_name": key,
            "data_type": _infer_type(first_val),
            "sample_value": first_val,
            "nullable": nullable,
        })
    return fields


# ---------------------------------------------------------------------------
# 私有辅助函数
# ---------------------------------------------------------------------------

def _get_api_key() -> str:
    """获取 API Key，统一通过 config.credentials 模块引用取，不直接调用 os.getenv。

    通过模块属性调用而非直接导入函数，确保测试中的 mock 能正确生效。
    """
    return _creds_module.get_credentials()["TRIPLEWHALE_API_KEY"]


def _fetch_table(table_name: str, api_key: str) -> list[dict]:
    """向 TripleWhale 请求指定表的数据，返回原始记录列表。

    Args:
        table_name: 表名（pixel_orders_table / pixel_joined_tvf / sessions_table /
                    product_analytics_tvf / pixel_keywords_joined_tvf / ads_table /
                    social_media_comments_table / social_media_pages_table /
                    creatives_table / ai_visibility_table）。
        api_key: TripleWhale API Key。

    Returns:
        原始记录列表。

    Raises:
        requests.Timeout: 请求超时（30s）
        RuntimeError: HTTP 非 2xx 或响应中无 data 字段
    """
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"shopDomain": SHOP_DOMAIN}

    resp = requests.post(
        f"{BASE_URL}/{table_name}",
        headers=headers,
        json=payload,
        timeout=DEFAULT_TIMEOUT,
    )

    if not resp.ok:
        raise RuntimeError(
            f"[triplewhale] 获取 {table_name} 失败：HTTP {resp.status_code} {resp.text[:200]}"
        )

    body = resp.json()
    # 兼容两种响应结构：{"data": [...]} 或直接为列表
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        if "data" in body and isinstance(body["data"], list):
            return body["data"]
        # 部分端点可能将结果放在其他键
        for key in ("rows", "records", "results", "items"):
            if key in body and isinstance(body[key], list):
                return body[key]
    raise RuntimeError(
        f"[triplewhale] 无法解析 {table_name} 响应结构，"
        f"响应键：{list(body.keys()) if isinstance(body, dict) else type(body)}"
    )


def _infer_type(value: object) -> str:
    """将 Python 值映射为标准 data_type 字符串。

    支持类型：string / number / boolean / array / object / null
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        # bool 必须在 int 之前判断（Python 中 bool 是 int 的子类）
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"
