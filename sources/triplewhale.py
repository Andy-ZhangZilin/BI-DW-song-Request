"""TripleWhale 数据源接入模块

认证方式：x-api-key header（小写，HTTP/2 兼容）
数据端点：/api/v2/orcabase/api/sql（ClickHouse SQL 查询，各表独立查询）
认证探针：/api/v2/summary-page/get-data
接入表：pixel_orders_table / pixel_joined_tvf / sessions_table / product_analytics_tvf /
        pixel_keywords_joined_tvf / ads_table / social_media_comments_table /
        social_media_pages_table / creatives_table / ai_visibility_table
shopDomain：piscifun.myshopify.com（固定）

公开接口（统一 source 契约）：
    authenticate() -> bool
    fetch_sample(table_name: str = None) -> list[dict]
    extract_fields(sample: list[dict]) -> list[dict]
    fetch_data_profile(table_name: str) -> dict
"""
import logging
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Optional

import requests

import config.credentials as _creds_module
from config.credentials import mask_credential

logger = logging.getLogger(__name__)

# --- 常量 ---
_API_BASE: str = "https://api.triplewhale.com/api/v2"
AUTH_URL: str = f"{_API_BASE}/summary-page/get-data"
SQL_URL: str = f"{_API_BASE}/orcabase/api/sql"
SHOP_DOMAIN: str = "piscifun.myshopify.com"
DEFAULT_TIMEOUT: int = 30   # 秒，sample 查询超时
PROFILE_TIMEOUT: int = 120  # 秒，MIN/COUNT 等 profile 查询超时（数据量大，耗时较长）
_SAMPLE_DAYS: int = 14  # 样本抓取天数（扩大窗口以确保有数据）
MAX_SAMPLE_ROWS: int = 1  # 每张表最多保留的样本行数
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

# --- 数据概况相关常量（Task 4.1）---
RATE_LIMIT_RPM: int = 60          # TripleWhale API 速率限制（每分钟请求数，保守估计）
MAX_ROWS_PER_REQUEST: int = 1000  # 每次 SQL 请求最大返回行数
_PROFILE_START_DATE: str = "2019-01-01"  # 数据概况查询起始日期（覆盖全历史）

# 各表必填过滤条件（某些表强制要求 WHERE 子句，否则 API 返回 500）
_TABLE_REQUIRED_FILTERS: dict[str, str] = {
    "creatives_table": "asset_type = 'video'",
}

# MIN 聚合在服务端超时/内存超限的表，改用 ORDER BY date_col ASC LIMIT 1
_TABLE_SKIP_MIN_AGG: set[str] = {
    "creatives_table",
    "product_analytics_tvf",  # MIN 聚合服务端 Timeout error（HTTP 400）
}

# COUNT 不可用的表（保留用于未来扩展；当前所有表均走分段路径或普通 COUNT）
_TABLE_NO_COUNT: set[str] = set()


# 各表日期列名（基于表结构规范；None 表示该表暂无已知日期列）
_TABLE_DATE_COLUMNS: dict[str, Optional[str]] = {
    "pixel_orders_table":           "created_at",   # 实测字段
    "pixel_joined_tvf":             "event_date",   # 修正：实测字段（原错误：created_at）
    "sessions_table":               "event_date",   # 修正：实测字段（原错误：session_date）
    "product_analytics_tvf":        "event_date",   # 修正：实测字段（原错误：date）
    "pixel_keywords_joined_tvf":    "event_date",   # 修正：实测字段（原错误：date）
    "ads_table":                    "event_date",   # 修正：实测字段（原错误：date）
    "social_media_comments_table":  "created_at",   # 实测字段
    "social_media_pages_table":     "event_date",   # 修正：实测字段（原错误：created_at）
    "creatives_table":              "event_date",   # 修正：实测字段（原错误：created_at）
    "ai_visibility_table":          "event_date",   # 修正：原 created_at 报 Unknown identifier
}


# ---------------------------------------------------------------------------
# 公开接口（统一 source 契约）
# ---------------------------------------------------------------------------

def authenticate() -> bool:
    """验证 TRIPLEWHALE_API_KEY 是否有效。

    通过向 summary-page/get-data 发送探测请求来验证 API Key。
    成功返回 True，失败打印错误并返回 False。
    日志格式：[triplewhale] 认证 ... 成功/失败：{原因}

    Returns:
        True 表示认证成功，False 表示认证失败。
    """
    try:
        api_key = _get_api_key()
        logger.info(f"[triplewhale] 认证中，使用 API Key: {mask_credential(api_key)}")
        start, end = _sample_date_range()
        resp = requests.post(
            AUTH_URL,
            headers={"x-api-key": api_key, "content-type": "application/json"},
            json={"shopDomain": SHOP_DOMAIN, "period": {"start": start, "end": end}},
            timeout=DEFAULT_TIMEOUT,
        )
        if resp.status_code == 200:
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
        原始记录的列表（list[dict]），若该表无数据则返回空列表。

    Raises:
        ValueError: table_name 不在 TABLES 中
        requests.Timeout: 请求超时
        RuntimeError: API 返回非 2xx 状态码
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
    sample = sample[:MAX_SAMPLE_ROWS]
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


def fetch_data_profile(table_name: str) -> dict:
    """获取指定表的数据概况：最早数据日期、总行数、rate limit、全量拉取预估时长。

    执行两次 SQL 查询（MIN + COUNT）探测表的数据概况，用于评估全量拉取代价。
    无数据时返回 earliest_date=None、total_rows=0、estimated_pull_minutes=None，
    日志输出警告级别提示，不抛出异常。

    Args:
        table_name: 表名，必须为 TABLES 中的一个。

    Returns:
        {
            "table_name": str,
            "date_column": str | None,       # 该表使用的日期列名
            "earliest_date": str | None,     # MIN(date_col) 结果，无数据时为 None
            "total_rows": int,               # COUNT(*) 结果
            "rate_limit_rpm": int,           # API 速率限制（常量）
            "max_rows_per_request": int,     # 单次最大行数（常量）
            "estimated_pull_minutes": float | None,  # ceil(rows/max_rows)/rpm，无数据时 None
        }

    Raises:
        ValueError: table_name 不在 TABLES 中
    """
    if table_name not in TABLES:
        raise ValueError(f"未知表名：{table_name}，可用：{TABLES}")

    api_key = _get_api_key()
    date_col = _TABLE_DATE_COLUMNS.get(table_name)

    earliest_date = _fetch_earliest_date(table_name, api_key) if date_col else None
    total_rows_raw = _fetch_row_count(table_name, api_key)

    # total_rows_raw 语义：
    #   int  → 查询成功（0 表示真无数据，>0 表示有数据）
    #   None → 查询失败（超时 / 内存超限 / 服务端错误等）
    count_failed = total_rows_raw is None
    total_rows = total_rows_raw if not count_failed else 0

    if count_failed:
        estimated_pull_minutes = None
        logger.warning(
            f"[triplewhale] 探测 {table_name} 数据概况 ... COUNT 查询失败，行数未知"
        )
    elif total_rows > 0:
        estimated_pull_minutes: Optional[float] = (
            ceil(total_rows / MAX_ROWS_PER_REQUEST) / RATE_LIMIT_RPM
        )
        logger.info(f"[triplewhale] 探测 {table_name} 数据概况 ... 成功")
    else:
        estimated_pull_minutes = None
        logger.warning(f"[triplewhale] 探测 {table_name} 数据概况 ... 无数据（total_rows=0）")

    return {
        "table_name": table_name,
        "date_column": date_col,
        "earliest_date": earliest_date,
        "total_rows": total_rows if not count_failed else None,  # None 表示未知
        "rate_limit_rpm": RATE_LIMIT_RPM,
        "max_rows_per_request": MAX_ROWS_PER_REQUEST,
        "estimated_pull_minutes": estimated_pull_minutes,
    }


# ---------------------------------------------------------------------------
# 私有辅助函数
# ---------------------------------------------------------------------------

def _required_where(table_name: str) -> str:
    """返回指定表的必填 WHERE 子句（含 WHERE 关键字），无要求时返回空字符串。"""
    condition = _TABLE_REQUIRED_FILTERS.get(table_name)
    return f" WHERE {condition}" if condition else ""


def _get_api_key() -> str:
    """获取 API Key，统一通过 config.credentials 模块引用取，不直接调用 os.getenv。

    通过模块属性调用而非直接导入函数，确保测试中的 mock 能正确生效。
    """
    return _creds_module.get_credentials()["TRIPLEWHALE_API_KEY"]


def _sample_date_range() -> tuple[str, str]:
    """返回 (start_date, end_date) 用于样本请求，格式 YYYY-MM-DD，最近 N 天。"""
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=_SAMPLE_DAYS)
    return str(start), str(end)


def _fetch_table(table_name: str, api_key: str) -> list[dict]:
    """向 TripleWhale SQL 端点查询指定表的样本数据，返回原始记录列表。

    使用 /api/v2/orcabase/api/sql 端点，以 SQL 方式直接查询各 ClickHouse 表。
    每张表独立查询，返回真实的表结构和数据。

    Args:
        table_name: 表名（TABLES 中的一个）。
        api_key: TripleWhale API Key。

    Returns:
        原始记录列表（list[dict]），若该表无数据则返回空列表。

    Raises:
        requests.Timeout: 请求超时（30s）
        RuntimeError: HTTP 非 2xx
    """
    start, end = _sample_date_range()
    headers = {"x-api-key": api_key, "content-type": "application/json"}
    payload = {
        "period": {"startDate": start, "endDate": end},
        "shopId": SHOP_DOMAIN,
        "query": f"SELECT * FROM {table_name}{_required_where(table_name)} LIMIT {MAX_SAMPLE_ROWS}",
        "currency": "USD",
    }

    resp = requests.post(
        SQL_URL,
        headers=headers,
        json=payload,
        timeout=DEFAULT_TIMEOUT,
    )

    if not resp.ok:
        # 5xx 服务端错误（如该表权限未开通）→ 警告并返回空列表，不中断整体验证
        if resp.status_code >= 500:
            logger.warning(
                f"[triplewhale] {table_name} 服务端错误（HTTP {resp.status_code}）"
                f"，响应：{resp.text[:300]}，跳过该表"
            )
            return []
        raise RuntimeError(
            f"[triplewhale] 获取 {table_name} 失败：HTTP {resp.status_code} {resp.text[:200]}"
        )

    body = resp.json()
    if isinstance(body, list):
        return body
    raise RuntimeError(
        f"[triplewhale] 无法解析 {table_name} 响应结构：{type(body)}"
    )


def _fetch_earliest_date(table_name: str, api_key: str) -> Optional[str]:
    """执行 MIN 查询获取表的最早数据日期。

    Args:
        table_name: 表名（TABLES 中的一个）。
        api_key: TripleWhale API Key。

    Returns:
        最早日期字符串（str），表无数据或查询失败时返回 None。
    """
    date_col = _TABLE_DATE_COLUMNS.get(table_name)
    if not date_col:
        return None

    where = _required_where(table_name)
    # MIN 聚合超时/内存超限的表改用 ORDER BY LIMIT 1 取最早日期
    if table_name in _TABLE_SKIP_MIN_AGG:
        query = (
            f"SELECT {date_col} as earliest FROM {table_name}"
            f"{where} ORDER BY {date_col} ASC LIMIT 1"
        )
    else:
        query = f"SELECT MIN({date_col}) as earliest FROM {table_name}{where}"

    try:
        rows = _run_sql_query(query, api_key)
        if rows and rows[0].get("earliest") is not None:
            return str(rows[0]["earliest"])
        return None
    except Exception as e:
        logger.warning(f"[triplewhale] {table_name} MIN 查询失败：{e}")
        return None


def _fetch_row_count(table_name: str, api_key: str) -> Optional[int]:
    """执行 COUNT(*) 查询获取表的总行数。

    对 _TABLE_SKIP_AGG 中的表，改用按年分段 COUNT 再求和，
    避免全表聚合触发 ArrayJoinTransform 内存超限。

    Args:
        table_name: 表名（TABLES 中的一个）。
        api_key: TripleWhale API Key。

    Returns:
        总行数（int），查询失败时返回 None。
    """
    if table_name in _TABLE_NO_COUNT:
        logger.warning(f"[triplewhale] {table_name} COUNT 不可用，行数标记为 N/A")
        return None

    if table_name in _TABLE_SKIP_MIN_AGG:
        return _fetch_row_count_chunked(table_name, api_key)

    query = f"SELECT COUNT(*) as total FROM {table_name}{_required_where(table_name)}"
    try:
        rows = _run_sql_query(query, api_key)
        if rows and rows[0].get("total") is not None:
            return int(rows[0]["total"])
        return 0
    except Exception as e:
        logger.warning(f"[triplewhale] {table_name} COUNT 查询失败：{e}")
        return None


def _fetch_row_count_chunked(table_name: str, api_key: str) -> Optional[int]:
    """按年分段 COUNT，适用于全表聚合内存超限的大表。

    从 _PROFILE_START_DATE 年份逐年查询 COUNT，累加得到总行数。
    单年若仍超限则跳过该年（计入警告），不影响其他年份统计。

    Returns:
        累计总行数（int），全部年份均失败时返回 None。
    """
    date_col = _TABLE_DATE_COLUMNS.get(table_name)
    if not date_col:
        logger.warning(f"[triplewhale] {table_name} 无日期列，无法分段 COUNT")
        return None

    start_year = int(_PROFILE_START_DATE[:4])
    current_year = datetime.now(timezone.utc).year
    base_filter = _TABLE_REQUIRED_FILTERS.get(table_name, "")

    total = 0
    any_success = False
    for year in range(start_year, current_year + 1):
        year_start = f"{year}-01-01"
        year_end = f"{year}-12-31"
        date_filter = f"{date_col} >= '{year_start}' AND {date_col} <= '{year_end}'"
        where_clause = (
            f" WHERE {base_filter} AND {date_filter}" if base_filter
            else f" WHERE {date_filter}"
        )
        query = f"SELECT COUNT(*) as total FROM {table_name}{where_clause}"
        try:
            rows = _run_sql_query(
                query, api_key,
                period_start=year_start,
                period_end=year_end,
            )
            if rows and rows[0].get("total") is not None:
                total += int(rows[0]["total"])
                any_success = True
        except Exception as e:
            logger.warning(f"[triplewhale] {table_name} {year} 年 COUNT 失败，跳过：{e}")

    if not any_success:
        logger.warning(f"[triplewhale] {table_name} 分段 COUNT 全部失败")
        return None

    logger.info(f"[triplewhale] {table_name} 分段 COUNT 完成，总行数：{total}")
    return total


def _run_sql_query(
    query: str,
    api_key: str,
    timeout: int = PROFILE_TIMEOUT,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> list[dict]:
    """向 TripleWhale SQL 端点执行任意 SQL 查询，返回结果列表。

    Args:
        query: SQL 查询字符串。
        api_key: TripleWhale API Key。
        timeout: 请求超时秒数，默认 PROFILE_TIMEOUT（120s）。
        period_start: payload period startDate，默认 _PROFILE_START_DATE（全历史）。
        period_end:   payload period endDate，默认今天。

    Returns:
        结果记录列表（list[dict]），无结果时返回空列表。

    Raises:
        requests.Timeout: 请求超时
        RuntimeError: HTTP 4xx 错误
    """
    p_start = period_start or _PROFILE_START_DATE
    p_end = period_end or str(datetime.now(timezone.utc).date())
    headers = {"x-api-key": api_key, "content-type": "application/json"}
    payload = {
        "period": {"startDate": p_start, "endDate": p_end},
        "shopId": SHOP_DOMAIN,
        "query": query,
        "currency": "USD",
    }

    resp = requests.post(
        SQL_URL,
        headers=headers,
        json=payload,
        timeout=timeout,
    )

    if not resp.ok:
        if resp.status_code >= 500:
            logger.warning(
                f"[triplewhale] SQL 查询服务端错误（HTTP {resp.status_code}）"
                f"，响应：{resp.text[:300]}，返回空结果"
            )
            return []
        raise RuntimeError(
            f"SQL 查询失败：HTTP {resp.status_code} {resp.text[:200]}"
        )

    body = resp.json()
    if isinstance(body, list):
        return body
    return []


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
