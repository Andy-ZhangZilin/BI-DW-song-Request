"""YouTube Data API v3 数据源接入模块。

通过 API Key 验证并抓取热门视频样本，提取字段信息。

公开接口：
    authenticate() -> bool        — 发送轻量探测请求验证 API Key 有效性
    fetch_sample(table_name=None) -> list[dict]  — 抓取最热门视频样本（非 SQL，table_name 忽略）
    extract_fields(sample) -> list[dict]         — 递归扁平化提取 FieldInfo 列表
"""

import logging
from typing import Optional

import requests

import config.credentials as _creds_module

logger = logging.getLogger(__name__)

SOURCE_NAME = "youtube"

BASE_URL = "https://www.googleapis.com/youtube/v3"
# 用于认证探测的公开频道 ID（Rick Astley，全球可访问的稳定公开频道）
_PROBE_CHANNEL_ID = "UCuAXFkgsw1L7xaCfnd5JJOw"


def authenticate() -> bool:
    """验证 API Key 有效性（轻量探测请求）。成功返回 True，失败日志记录后返回 False。

    发送一次 channels.list 请求（part=id，配额消耗最低），验证 API Key 是否被接受。

    Returns:
        True — API Key 有效；False — API Key 无效或网络异常
    """
    creds = _creds_module.get_credentials()
    try:
        api_key = creds["YOUTUBE_API_KEY"]
    except KeyError:
        logger.error(f"[{SOURCE_NAME}] 认证 ... 失败：凭证中未找到 YOUTUBE_API_KEY")
        return False
    logger.debug(f"[{SOURCE_NAME}] 使用 API Key: {_creds_module.mask_credential(api_key)}")

    url = f"{BASE_URL}/channels"
    params = {
        "part": "id",
        "id": _PROBE_CHANNEL_ID,
        "key": api_key,
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            logger.info(f"[{SOURCE_NAME}] 认证 ... 成功")
            return True
        else:
            logger.error(f"[{SOURCE_NAME}] 认证 ... 失败：{resp.status_code} {resp.reason}")
            return False
    except requests.RequestException as e:
        logger.error(f"[{SOURCE_NAME}] 认证 ... 失败：{e}")
        return False


def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """通过 YouTube Data API v3 抓取最热门视频样本（1 条）。

    使用 videos.list?chart=mostPopular 接口获取当前最热门视频，
    返回含 snippet 和 statistics 的原始记录列表。

    Args:
        table_name: YouTube 为非 SQL 数据源，此参数忽略，传 None 即可

    Returns:
        原始记录列表（list[dict]），每条为 YouTube API video item 结构

    Raises:
        requests.HTTPError: API 请求失败时（含 403 配额超限）
        RuntimeError: API 返回空结果时，或凭证中未找到 YOUTUBE_API_KEY
    """
    creds = _creds_module.get_credentials()
    try:
        api_key = creds["YOUTUBE_API_KEY"]
    except KeyError as exc:
        raise RuntimeError(f"[{SOURCE_NAME}] 凭证中未找到 YOUTUBE_API_KEY") from exc

    url = f"{BASE_URL}/videos"
    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "maxResults": 1,
        "key": api_key,
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"[{SOURCE_NAME}] 获取视频样本 ... 失败：{e}")
        raise

    items = resp.json().get("items", [])
    if not items:
        raise RuntimeError(f"[{SOURCE_NAME}] API 返回空结果，无可用视频样本")

    logger.info(f"[{SOURCE_NAME}] 获取视频样本 ... 成功（{len(items)} 条记录）")
    return items


def extract_fields(sample: list[dict]) -> list[dict]:
    """从 YouTube 视频样本中递归扁平化提取 FieldInfo 列表。

    对嵌套 dict（如 snippet、statistics、localized）使用点路径命名：
    例如 snippet.title、statistics.viewCount、snippet.localized.title

    数据类型推断规则：
    - None → "null"
    - bool → "boolean"
    - int / float → "number"
    - list → "array"
    - dict → "object"
    - 其他 → "string"

    Args:
        sample: fetch_sample() 返回的原始记录列表

    Returns:
        FieldInfo 列表，每项含 field_name / data_type / sample_value / nullable
    """
    if not sample:
        return []

    record = sample[0]
    fields: list[dict] = []

    def _infer_type(value) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, (int, float)):
            return "number"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        return "string"

    def _flatten(obj: dict, prefix: str = "") -> None:
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                _flatten(value, full_key)
            else:
                fields.append({
                    "field_name": full_key,
                    "data_type": _infer_type(value),
                    "sample_value": value,
                    "nullable": value is None,
                })

    _flatten(record)
    return fields
