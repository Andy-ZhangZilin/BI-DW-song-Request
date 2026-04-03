"""钉钉多维表数据源：authenticate / fetch_sample / extract_fields

公开接口（与其他 source 模块对齐）：
    authenticate() -> bool
    fetch_sample(table_name=None) -> list[dict]
    extract_fields(sample) -> list[dict]
"""
import logging
import time
from typing import Optional

import requests

import config.credentials as _creds_module

logger = logging.getLogger(__name__)
SOURCE_NAME = "dingtalk"

# 模块级 token 缓存（单进程，非多线程安全，但 CLI 场景无需考虑）
_cached_token: str | None = None
_token_expiry: float = 0.0

_TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
_SHEETS_URL = "https://api.dingtalk.com/v1.0/doc/workbooks/{workbook_id}/sheets"
_RANGE_URL = "https://api.dingtalk.com/v1.0/doc/workbooks/{workbook_id}/sheets/{sheet_id}/range"


def _load_token() -> str:
    """获取有效 access token（优先使用缓存，过期前 60s 刷新）。"""
    global _cached_token, _token_expiry
    if _cached_token and time.time() < _token_expiry - 60:
        return _cached_token
    creds = _creds_module.get_credentials()
    resp = requests.post(
        _TOKEN_URL,
        json={"appKey": creds["DINGTALK_APP_KEY"], "appSecret": creds["DINGTALK_APP_SECRET"]},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    _cached_token = data["accessToken"]
    _token_expiry = time.time() + data.get("expireIn", 7200)
    return _cached_token


def authenticate() -> bool:
    """验证钉钉凭证有效性（获取 access token）。

    Returns:
        True 表示认证成功，False 表示失败。
    """
    try:
        _load_token()
        logger.info(f"[{SOURCE_NAME}] 认证 ... 成功")
        return True
    except Exception as e:
        logger.error(f"[{SOURCE_NAME}] 认证 ... 失败：{e}")
        return False


def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """从钉钉多维表拉取样本数据（默认取第一个 Sheet 的 A1:Z100 区域）。

    Args:
        table_name: 未使用，保留以对齐公共接口签名。

    Returns:
        记录列表，每条记录为 {列名: 值} 的字典。空表返回 []。
    """
    token = _load_token()
    creds = _creds_module.get_credentials()
    workbook_id = creds["DINGTALK_WORKBOOK_ID"]
    headers = {"x-acs-dingtalk-access-token": token}

    # 优先使用显式指定的 sheet_id，否则自动获取第一个 Sheet
    sheet_id = creds.get("DINGTALK_SHEET_ID", "")
    if not sheet_id:
        sheets_url = _SHEETS_URL.format(workbook_id=workbook_id)
        resp = requests.get(sheets_url, headers=headers, timeout=30)
        resp.raise_for_status()
        sheets = resp.json().get("value", [])
        if not sheets:
            raise RuntimeError(f"[{SOURCE_NAME}] workbook {workbook_id} 中未找到任何 Sheet")
        sheet_id = sheets[0].get("id") or sheets[0].get("sheetId", "")

    range_url = _RANGE_URL.format(workbook_id=workbook_id, sheet_id=sheet_id)
    resp = requests.get(
        range_url,
        headers=headers,
        params={"range": "A1:Z100"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    values = data.get("value", {}).get("values", [])
    if not values or len(values) < 2:
        return []

    headers_row = values[0]
    records = []
    for row in values[1:]:
        record = {
            str(col_name): (row[i] if i < len(row) else None)
            for i, col_name in enumerate(headers_row)
        }
        records.append(record)
    return records


def extract_fields(sample: list[dict]) -> list[dict]:
    """从样本数据中提取字段描述列表（FieldInfo 标准四键结构）。

    Args:
        sample: fetch_sample() 返回的记录列表。

    Returns:
        字段描述列表，每条含 field_name / data_type / sample_value / nullable。
    """
    if not sample:
        return []

    # 保序去重收集所有列名
    all_keys: list[str] = []
    seen: set[str] = set()
    for record in sample:
        for key in record:
            if key not in seen:
                all_keys.append(key)
                seen.add(key)

    fields = []
    for key in all_keys:
        sample_value = next(
            (r.get(key) for r in sample if r.get(key) is not None), None
        )
        all_none = all(r.get(key) is None for r in sample)
        # 含"关联"的列名或全为 null 的列视为可空
        is_association = "关联" in key or all_none
        nullable = sample_value is None or is_association

        if sample_value is None:
            data_type = "null"
        elif isinstance(sample_value, bool):
            data_type = "boolean"
        elif isinstance(sample_value, (int, float)):
            data_type = "number"
        elif isinstance(sample_value, list):
            data_type = "array"
        elif isinstance(sample_value, dict):
            data_type = "object"
        else:
            data_type = "string"

        fields.append(
            {
                "field_name": key,
                "data_type": data_type,
                "sample_value": sample_value if not nullable else None,
                "nullable": nullable,
            }
        )
    return fields
