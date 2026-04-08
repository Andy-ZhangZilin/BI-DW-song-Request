"""钉钉多维表格（Notable Bitable）数据源：authenticate / fetch_sample / extract_fields

公开接口（与其他 source 模块对齐）：
    authenticate() -> bool
    fetch_sample(table_name=None) -> list[dict]
    extract_fields(sample) -> list[dict]

凭证要求（.env）：
    DINGTALK_APP_KEY          企业内部应用 AppKey
    DINGTALK_APP_SECRET       企业内部应用 AppSecret
    DINGTALK_WORKBOOK_ID      多维表格 BaseId（文档唯一标识）
    DINGTALK_OPERATOR_ID      操作者 unionId（必填，用于 notable API 鉴权）
    DINGTALK_SHEET_ID         （可选）指定 Sheet ID；未配置时按名称或取第一个
    DINGTALK_SHEET_NAME       （可选）指定 Sheet 名称，如"红人信息汇总"
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
_NOTABLE_BASE = "https://api.dingtalk.com/v1.0/notable/bases"


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


def _flatten_value(value: object) -> object:
    """将 bitable 字段值归一化为简单标量类型。

    bitable 返回的复合值类型：
    - URL:    {"link": "...", "text": "..."}  → 取 link
    - 单选:   {"name": "...", "id": "..."}   → 取 name
    - 人员:   {"unionId": "...", "name": "..."} → 取 name
    - 多选/多人员: [{"name":...}, ...]         → 逗号拼接 name
    """
    if value is None:
        return None
    if isinstance(value, dict):
        if "link" in value:
            return value["link"]
        if "name" in value:
            return value["name"]
    if isinstance(value, list):
        if not value:
            return None
        first = value[0]
        if isinstance(first, dict) and "name" in first:
            return ", ".join(item.get("name", "") for item in value)
        return str(value)
    return value


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
    """从钉钉多维表格拉取全量记录并归一化为扁平字典列表。

    使用 notable API（/v1.0/notable/bases/...）分页拉取，
    自动解析复合字段值（URL / 单选 / 多选 / 人员等）。

    Args:
        table_name: 未使用，保留以对齐公共接口签名。

    Returns:
        记录列表，每条记录为 {列名: 标量值} 的字典。空表返回 []。
    """
    token = _load_token()
    creds = _creds_module.get_credentials()
    base_id = creds["DINGTALK_WORKBOOK_ID"]
    operator_id = _creds_module.get_optional_config("DINGTALK_OPERATOR_ID")
    if not operator_id:
        raise RuntimeError(
            f"[{SOURCE_NAME}] 未配置 DINGTALK_OPERATOR_ID，请在 .env 中填入操作者 unionId"
        )

    headers = {"x-acs-dingtalk-access-token": token}
    params_base = {"operatorId": operator_id}

    # 确定 sheet_id：优先显式配置，次之按名称查找，最后取第一个
    sheet_id = _creds_module.get_optional_config("DINGTALK_SHEET_ID", "")
    if not sheet_id:
        sheet_name = _creds_module.get_optional_config("DINGTALK_SHEET_NAME", "")
        resp = requests.get(
            f"{_NOTABLE_BASE}/{base_id}/sheets",
            headers=headers, params=params_base, timeout=30,
        )
        resp.raise_for_status()
        sheets = resp.json().get("value", [])
        if not sheets:
            raise RuntimeError(f"[{SOURCE_NAME}] base {base_id} 中未找到任何 Sheet")
        if sheet_name:
            matched = next((s for s in sheets if s.get("name") == sheet_name), None)
            if not matched:
                raise RuntimeError(f"[{SOURCE_NAME}] 未找到名称为 '{sheet_name}' 的 Sheet")
            sheet_id = matched["id"]
        else:
            sheet_id = sheets[0]["id"]

    # 分页拉取全量记录
    all_records: list[dict] = []
    next_token: str | None = None
    while True:
        params = {**params_base, "maxResults": 100}
        if next_token:
            params["nextToken"] = next_token
        resp = requests.get(
            f"{_NOTABLE_BASE}/{base_id}/sheets/{sheet_id}/records",
            headers=headers, params=params, timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        records = data.get("records", [])
        for rec in records:
            flat = {k: _flatten_value(v) for k, v in rec.get("fields", {}).items()}
            all_records.append(flat)
        next_token = data.get("nextToken")
        if not next_token or not records:
            break

    return all_records


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
