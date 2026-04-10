"""钉钉普通表格（工作簿/Workbook）数据源：authenticate / fetch_sample / extract_fields

与 dingtalk.py（多维表格/Notable）不同，本模块使用工作簿 API：
    /v1.0/table/workbooks/{workbookId}/...

公开接口（与其他 source 模块对齐）：
    authenticate() -> bool
    fetch_sample(table_name=None) -> list[dict]
    extract_fields(sample) -> list[dict]

凭证要求（.env）：
    DINGTALK_APP_KEY          企业内部应用 AppKey
    DINGTALK_APP_SECRET       企业内部应用 AppSecret
    DINGTALK_OPERATOR_ID      操作者 unionId（必填）

支持的表（共 1 张）：
    红人支付需求 (XPwkYGxZV3RRlXAQCjaPjk6zWAgozOKL)：取第一个 Sheet
"""
import logging
import time
from typing import Optional

import requests

import config.credentials as _creds_module

logger = logging.getLogger(__name__)
SOURCE_NAME = "dingtalk_sheet"

_cached_token: str | None = None
_token_expiry: float = 0.0

_TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
_WORKBOOK_BASE = "https://api.dingtalk.com/v1.0/doc/workbooks"

# 工作簿 ID：红人支付需求
WORKBOOK_ID = "XPwkYGxZV3RRlXAQCjaPjk6zWAgozOKL"

# 每次拉取的最大行数（含表头），超过 200 行会触发 503
_CHUNK_ROWS = 200
# 数据列上限（不超过 Z 列，即 26 列）
_MAX_COL = "Z"


def _load_token() -> str:
    """获取有效 access token（优先使用缓存，过期前 60s 刷新）。"""
    global _cached_token, _token_expiry
    if _cached_token and time.time() < _token_expiry - 60:
        return _cached_token
    creds = _creds_module.get_credentials(source_name=SOURCE_NAME)
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


def _get_first_sheet_id(token: str, operator_id: str) -> str:
    """列出工作簿所有 Sheet，返回第一个 Sheet 的 id。"""
    headers = {"x-acs-dingtalk-access-token": token}
    resp = requests.get(
        f"{_WORKBOOK_BASE}/{WORKBOOK_ID}/sheets",
        headers=headers,
        params={"operatorId": operator_id},
        timeout=30,
    )
    resp.raise_for_status()
    sheets = resp.json().get("value", [])
    if not sheets:
        raise RuntimeError(f"[{SOURCE_NAME}] 工作簿 {WORKBOOK_ID} 中未找到任何 Sheet")
    return sheets[0]["id"]


def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """从钉钉普通表格读取数据，返回扁平字典列表。

    流程：
      1. 列出工作簿 Sheets，取第一个 Sheet 的 id
      2. 通过 ranges API 批量读取数据（A1:{_MAX_COL}{_MAX_ROWS}）
      3. 第一行作为表头，后续行作为数据，过滤空行

    Args:
        table_name: 未使用，保留以对齐公共接口签名。

    Returns:
        记录列表，每条记录为 {列名: 标量值} 的字典。
    """
    token = _load_token()
    operator_id = _creds_module.get_optional_config("DINGTALK_OPERATOR_ID")
    if not operator_id:
        raise RuntimeError(
            f"[{SOURCE_NAME}] 未配置 DINGTALK_OPERATOR_ID，请在 .env 中填入操作者 unionId"
        )

    req_headers = {"x-acs-dingtalk-access-token": token}
    sheet_id = _get_first_sheet_id(token, operator_id)

    def _fetch_range(row_start: int, row_end: int) -> list:
        """拉取指定行范围，返回 displayValues 二维列表。"""
        rng = f"A{row_start}:{_MAX_COL}{row_end}"
        resp = requests.get(
            f"{_WORKBOOK_BASE}/{WORKBOOK_ID}/sheets/{sheet_id}/ranges/{rng}",
            headers=req_headers,
            params={"operatorId": operator_id},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("displayValues", [])

    # 首次拉取：第 1 行表头 + 数据
    first_block = _fetch_range(1, _CHUNK_ROWS)
    if not first_block:
        logger.warning(f"[{SOURCE_NAME}] 工作簿返回空数据")
        return []

    headers_row = [str(c) if c is not None else "" for c in first_block[0]]
    all_rows = first_block[1:]  # 去掉表头行

    # 继续分批拉取剩余数据（每次 CHUNK_ROWS 行）
    batch_start = _CHUNK_ROWS + 1
    while True:
        batch_end = batch_start + _CHUNK_ROWS - 1
        try:
            block = _fetch_range(batch_start, batch_end)
        except Exception as e:
            logger.warning(f"[{SOURCE_NAME}] 拉取第 {batch_start}-{batch_end} 行失败，停止：{e}")
            break
        if not block:
            break
        # 全空块表示到达末尾
        non_empty = [r for r in block if any(c is not None and c != "" for c in r)]
        if not non_empty:
            break
        all_rows.extend(block)
        if len(block) < _CHUNK_ROWS:
            break
        batch_start = batch_end + 1

    # 构造扁平字典列表
    records: list[dict] = []
    for row in all_rows:
        if not any(cell is not None and cell != "" for cell in row):
            continue
        padded = list(row) + [None] * max(0, len(headers_row) - len(row))
        record = {
            headers_row[i]: padded[i]
            for i in range(len(headers_row))
            if headers_row[i]
        }
        records.append(record)

    logger.info(f"[{SOURCE_NAME}] 读取到 {len(records)} 条记录")
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
            (r.get(key) for r in sample if r.get(key) is not None and r.get(key) != ""),
            None,
        )
        all_none = all(r.get(key) is None or r.get(key) == "" for r in sample)
        nullable = sample_value is None or all_none

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
