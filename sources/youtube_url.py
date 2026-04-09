"""YouTube URL 视频统计数据源模块。

通过指定视频 URL 获取播放数（viewCount）和点赞数（likeCount）。

公开接口：
    authenticate() -> bool        — 复用 YouTube API Key 验证逻辑
    fetch_sample(table_name=None) -> list[dict]  — 写死 URL 获取视频 statistics
    extract_fields(sample) -> list[dict]         — 提取标准 FieldInfo 列表
"""

import logging
from typing import Optional

import requests

import config.credentials as _creds_module
from sources.youtube import extract_video_id

logger = logging.getLogger(__name__)

SOURCE_NAME = "youtube_url"

BASE_URL = "https://www.googleapis.com/youtube/v3"
# 用于认证探测的公开频道 ID（Rick Astley，全球可访问的稳定公开频道）
_PROBE_CHANNEL_ID = "UCuAXFkgsw1L7xaCfnd5JJOw"
# 写死的验证用视频 URL（已通过真实 API 验证：viewCount=919, likeCount=89）
_DEFAULT_URL = "https://www.youtube.com/watch?v=1laF2zVhbcE"


def authenticate() -> bool:
    """验证 API Key 有效性（轻量探测请求）。成功返回 True，失败日志记录后返回 False。

    Returns:
        True — API Key 有效；False — API Key 无效或网络异常
    """
    creds = _creds_module.get_credentials(source_name=SOURCE_NAME)
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
    """使用写死的视频 URL 获取 statistics 数据。

    调用 YouTube Data API v3 的 videos.list 接口，part=statistics，
    返回含 statistics 的原始记录列表。

    Args:
        table_name: youtube_url 为非 SQL 数据源，此参数忽略

    Returns:
        原始记录列表（list[dict]），每条为 YouTube API video item 结构

    Raises:
        RuntimeError: 凭证缺失或 API 返回空结果
        requests.HTTPError: API 请求失败
    """
    video_id = extract_video_id(_DEFAULT_URL)

    creds = _creds_module.get_credentials(source_name=SOURCE_NAME)
    try:
        api_key = creds["YOUTUBE_API_KEY"]
    except KeyError as exc:
        raise RuntimeError(f"[{SOURCE_NAME}] 凭证中未找到 YOUTUBE_API_KEY") from exc

    url = f"{BASE_URL}/videos"
    params = {
        "part": "statistics",
        "id": video_id,
        "key": api_key,
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"[{SOURCE_NAME}] 获取视频统计 ... 失败：{e}")
        raise

    items = resp.json().get("items", [])
    if not items:
        raise RuntimeError(f"[{SOURCE_NAME}] 视频 {video_id} 未找到（API 返回空结果）")

    logger.info(f"[{SOURCE_NAME}] 获取视频统计 ... 成功（{len(items)} 条记录）")
    return items


def extract_fields(sample: list[dict]) -> list[dict]:
    """从视频 statistics 样本中提取 FieldInfo 列表。

    对嵌套 dict（如 statistics）使用点路径命名：
    例如 statistics.viewCount、statistics.likeCount

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
