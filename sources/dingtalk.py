"""钉钉多维表格（Notable Bitable）数据源：authenticate / fetch_sample / extract_fields

公开接口（与其他 source 模块对齐）：
    authenticate() -> bool
    fetch_sample(table_name=None) -> list[dict]
    extract_fields(sample) -> list[dict]

凭证要求（.env）：
    DINGTALK_APP_KEY          企业内部应用 AppKey
    DINGTALK_APP_SECRET       企业内部应用 AppSecret
    DINGTALK_OPERATOR_ID      操作者 unionId（必填，用于 notable API 鉴权）

TABLES 字典格式：{table_key: (base_id, sheet_name)}
    base_id:    多维表格的 BaseId（文档唯一标识）
    sheet_name: 多维表格中的 Sheet 名称

支持的表（共 8 张）：
    KOL营销管理总表-TideWe (Gl6Pm2Db8D332mAgCnk7N0AaJxLq0Ee4)：
        kol_tidwe_红人信息汇总  → 红人信息汇总
        kol_tidwe_寄样记录     → 寄样记录
        kol_tidwe_内容上线     → 内容上线

    26年新版-大户外一张表3.0 (Qnp9zOoBVBZZXzArF0nlpBn0V1DK0g6l)：
        outdoor_原始素材生产及优化   → 原始素材生产及优化
        outdoor_拍摄资源表KOL信息   → 拍摄资源表-KOL信息
        outdoor_素材分析表格        → 素材分析表格
        outdoor_参数表             → 参数表|勿动

    视频组日常工作总表 (20eMKjyp81RR5NAQC79gy2YEWxAZB1Gv)：
        video_成片交付             → 视频组成片交付&数据汇总表
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

# /fields 接口返回的官方列顺序（按 table_name 缓存）
_field_order_cache: dict[str, list[str]] = {}

_TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
_NOTABLE_BASE = "https://api.dingtalk.com/v1.0/notable/bases"

# ---------------------------------------------------------------------------
# 多维表格注册表：{table_key: (base_id, sheet_name)}
# ---------------------------------------------------------------------------
TABLES: dict[str, tuple[str, str]] = {
    # KOL营销管理总表-TideWe
    "kol_tidwe_红人信息汇总":  ("Gl6Pm2Db8D332mAgCnk7N0AaJxLq0Ee4", "红人信息汇总"),
    "kol_tidwe_寄样记录":      ("Gl6Pm2Db8D332mAgCnk7N0AaJxLq0Ee4", "寄样记录"),
    "kol_tidwe_内容上线":      ("Gl6Pm2Db8D332mAgCnk7N0AaJxLq0Ee4", "内容上线"),
    # 26年新版-大户外一张表3.0-原始素材+产品信息
    "outdoor_原始素材生产及优化": ("Qnp9zOoBVBZZXzArF0nlpBn0V1DK0g6l", "原始素材生产及优化"),
    "outdoor_拍摄资源表KOL信息":  ("Qnp9zOoBVBZZXzArF0nlpBn0V1DK0g6l", "拍摄资源表-KOL信息"),
    "outdoor_素材分析表格":       ("Qnp9zOoBVBZZXzArF0nlpBn0V1DK0g6l", "素材分析表格"),
    "outdoor_参数表":             ("Qnp9zOoBVBZZXzArF0nlpBn0V1DK0g6l", "参数表|勿动"),
    # 视频组日常工作总表
    "video_成片交付": ("20eMKjyp81RR5NAQC79gy2YEWxAZB1Gv", "视频组成片交付&数据汇总表"),
}


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


def _resolve_sheet_id(base_id: str, sheet_name: str, headers: dict, params_base: dict) -> str:
    """根据 sheet_name 查找对应的 sheet_id。

    Args:
        base_id:    多维表格 BaseId
        sheet_name: Sheet 名称
        headers:    HTTP 请求头（含 token）
        params_base: 公共查询参数（含 operatorId）

    Returns:
        sheet_id 字符串

    Raises:
        RuntimeError: 未找到对应 sheet 时抛出
    """
    resp = requests.get(
        f"{_NOTABLE_BASE}/{base_id}/sheets",
        headers=headers, params=params_base, timeout=30,
    )
    resp.raise_for_status()
    sheets = resp.json().get("value", [])
    if not sheets:
        raise RuntimeError(f"[{SOURCE_NAME}] base {base_id} 中未找到任何 Sheet")
    matched = next((s for s in sheets if s.get("name") == sheet_name), None)
    if not matched:
        available = [s.get("name") for s in sheets]
        raise RuntimeError(
            f"[{SOURCE_NAME}] base {base_id} 中未找到名称为 '{sheet_name}' 的 Sheet，"
            f"可用 Sheet：{available}"
        )
    return matched["id"]


def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """从钉钉多维表格拉取全量记录并归一化为扁平字典列表。

    使用 notable API（/v1.0/notable/bases/...）分页拉取，
    自动解析复合字段值（URL / 单选 / 多选 / 人员等）。
    同时调用 /fields 接口获取官方列顺序，存入模块缓存供 extract_fields 使用。

    Args:
        table_name: TABLES 中的 key（如 "kol_tidwe_红人信息汇总"）。
                    为 None 时取 TABLES 第一个条目。

    Returns:
        记录列表，每条记录为 {列名: 标量值} 的字典。空表返回 []。
    """
    if table_name is None:
        table_name = next(iter(TABLES))

    if table_name not in TABLES:
        raise ValueError(
            f"[{SOURCE_NAME}] 未知 table_name '{table_name}'，"
            f"可选值：{list(TABLES.keys())}"
        )

    base_id, sheet_name = TABLES[table_name]

    token = _load_token()
    operator_id = _creds_module.get_optional_config("DINGTALK_OPERATOR_ID")
    if not operator_id:
        raise RuntimeError(
            f"[{SOURCE_NAME}] 未配置 DINGTALK_OPERATOR_ID，请在 .env 中填入操作者 unionId"
        )

    headers = {"x-acs-dingtalk-access-token": token}
    params_base = {"operatorId": operator_id}

    # 通过 sheet_name 查找 sheet_id
    sheet_id = _resolve_sheet_id(base_id, sheet_name, headers, params_base)

    # 拉取 /fields 获取官方列顺序（失败不阻断主流程）
    try:
        resp_fields = requests.get(
            f"{_NOTABLE_BASE}/{base_id}/sheets/{sheet_id}/fields",
            headers=headers, params=params_base, timeout=30,
        )
        resp_fields.raise_for_status()
        _field_order_cache[table_name] = [
            f["name"] for f in resp_fields.json().get("value", [])
        ]
        logger.debug(
            f"[{SOURCE_NAME}] {table_name}: 获取到 {len(_field_order_cache[table_name])} 个字段顺序定义"
        )
    except Exception as fe:
        logger.warning(f"[{SOURCE_NAME}] {table_name}: 获取字段顺序失败，将按记录顺序输出：{fe}")
        _field_order_cache[table_name] = []

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


def extract_fields(sample: list[dict], table_name: Optional[str] = None) -> list[dict]:
    """从样本数据中提取字段描述列表（FieldInfo 标准四键结构）。

    Args:
        sample:     fetch_sample() 返回的记录列表。
        table_name: TABLES 中的 key，用于读取对应的字段顺序缓存。
                    为 None 时跳过顺序排序。

    Returns:
        字段描述列表，每条含 field_name / data_type / sample_value / nullable。
    """
    if not sample:
        return []

    field_order = _field_order_cache.get(table_name, []) if table_name else []

    # 保序去重收集所有列名（来自记录数据）
    record_keys: list[str] = []
    seen: set[str] = set()
    for record in sample:
        for key in record:
            if key not in seen:
                record_keys.append(key)
                seen.add(key)

    # 按 /fields 官方顺序排列；records 中有但 /fields 没有的列追加到末尾
    if field_order:
        ordered = [k for k in field_order if k in seen]
        tail = [k for k in record_keys if k not in set(field_order)]
        all_keys = ordered + tail
    else:
        all_keys = record_keys

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
