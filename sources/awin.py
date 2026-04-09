"""Awin REST API 数据源模块。

通过 Awin 官方 REST API（Performance Data）获取广告主报表数据。

接口契约（ARCH2）：
    authenticate() -> bool
    fetch_sample(table_name: str = None) -> list[dict]
    extract_fields(sample: list[dict]) -> list[dict]

认证方式：
    OAuth 2.0 Bearer Token — Authorization: Bearer <AWIN_API_TOKEN>

超时规范（ARCH10）：
    HTTP_TIMEOUT_S = 30   # HTTP 请求超时 30s
    TOTAL_TIMEOUT_S = 60  # 单 source 整体执行 60s 内完成

安全规范（NFR2）：
    日志输出凭证时必须使用 mask_credential()，禁止输出完整 Token。
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import requests

from config.credentials import get_credentials, mask_credential
from reporter import write_raw_report, init_validation_report

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

AWIN_API_BASE = "https://api.awin.com"

# 超时设置（ARCH10）
HTTP_TIMEOUT_S = 30   # HTTP 请求超时 30s
TOTAL_TIMEOUT_S = 60  # 单 source 整体执行 60s

# 默认查询最近 7 天数据
DEFAULT_DATE_RANGE_DAYS = 7

# 最大样本行数
MAX_SAMPLE_ROWS = 20


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------

def authenticate() -> bool:
    """通过 GET /accounts 验证 Awin API Token 有效性。

    Returns:
        True  — Token 有效，且关联的 advertiser 账户可访问
        False — Token 无效或网络异常

    Side effects:
        认证成功后调用 init_validation_report("awin")（仅首次创建模板文件）。
    """
    try:
        creds = get_credentials()
        token = creds["AWIN_API_TOKEN"]
        advertiser_id = creds["AWIN_ADVERTISER_ID"]
    except (KeyError, ValueError) as e:
        logger.error(f"[awin] 认证 ... 失败：凭证获取失败 — {e}")
        return False

    logger.info(f"[awin] 认证，Token：{mask_credential(token)}，advertiserId：{advertiser_id}")

    try:
        resp = requests.get(
            f"{AWIN_API_BASE}/accounts",
            headers={"Authorization": f"Bearer {token}"},
            timeout=HTTP_TIMEOUT_S,
        )

        if resp.status_code == 200:
            data = resp.json()
            accounts = data.get("accounts", [])
            found = any(
                str(acc.get("accountId")) == str(advertiser_id)
                for acc in accounts
            )
            if found:
                logger.info("[awin] 认证 ... 成功")
                try:
                    init_validation_report("awin")
                except OSError as e:
                    logger.warning(f"[awin] init_validation_report 写入失败（认证已成功）：{e}")
                return True
            else:
                logger.error(f"[awin] 认证 ... 失败：advertiserId {advertiser_id} 未在账户列表中找到")
                return False
        else:
            logger.error(f"[awin] 认证 ... 失败：HTTP {resp.status_code} — {resp.text[:200]}")
            return False

    except requests.RequestException as e:
        logger.error(f"[awin] 认证 ... 失败：网络请求异常 — {e}")
        return False


def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """调用 Publisher Performance API 获取样本数据。

    Args:
        table_name: 保留参数，与接口契约保持一致（ARCH2）；实际忽略。

    Returns:
        样本记录列表（list[dict]），每项为 API 返回的一条 publisher 报表记录。

    Raises:
        RuntimeError: API 请求失败、网络超时或报告写入失败时抛出。
    """
    try:
        creds = get_credentials()
        token = creds["AWIN_API_TOKEN"]
        advertiser_id = creds["AWIN_ADVERTISER_ID"]
    except (KeyError, ValueError) as e:
        logger.error(f"[awin] fetch_sample ... 失败：凭证获取失败 — {e}")
        raise RuntimeError(f"[awin] 凭证获取失败：{e}") from e

    logger.info(f"[awin] fetch_sample，advertiserId：{advertiser_id}")
    start_time = time.time()

    # 计算日期范围：最近 7 天
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=DEFAULT_DATE_RANGE_DAYS)).strftime("%Y-%m-%d")

    url = f"{AWIN_API_BASE}/advertisers/{advertiser_id}/reports/publisher"
    params = {
        "startDate": start_date,
        "endDate": end_date,
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=HTTP_TIMEOUT_S)

        if resp.status_code != 200:
            logger.error(f"[awin] fetch_sample ... 失败：HTTP {resp.status_code} — {resp.text[:200]}")
            raise RuntimeError(f"[awin] API 请求失败：HTTP {resp.status_code}")

        sample = resp.json()

        if not isinstance(sample, list):
            logger.error(f"[awin] fetch_sample ... 失败：API 返回非列表格式 — {type(sample)}")
            raise RuntimeError("[awin] API 返回格式异常：期望列表")

        # 限制样本行数
        sample = sample[:MAX_SAMPLE_ROWS]

        if not sample:
            logger.warning("[awin] API 返回空数据，返回空样本")

        # 整体超时检查
        elapsed = time.time() - start_time
        if elapsed > TOTAL_TIMEOUT_S:
            raise RuntimeError(f"[awin] 整体执行超过 {TOTAL_TIMEOUT_S}s 限制，中止")

        # 生成报告
        fields = extract_fields(sample)
        try:
            write_raw_report("awin", fields, None, len(sample))
        except OSError as e:
            logger.error(f"[awin] write_raw_report 写入失败：{e}")
            raise RuntimeError(f"[awin] 报告写入失败：{e}") from e

        logger.info(f"[awin] fetch_sample ... 成功，获取 {len(sample)} 条记录")
        return sample

    except RuntimeError:
        raise
    except requests.RequestException as e:
        logger.error(f"[awin] fetch_sample ... 失败：网络请求异常 — {e}")
        raise RuntimeError(f"[awin] API 请求失败：{e}") from e


def extract_fields(sample: list[dict]) -> list[dict]:
    """从样本数据中提取标准 FieldInfo 结构列表（ARCH2）。

    纯函数，不依赖外部 IO，单元测试直接调用即可。

    Args:
        sample: fetch_sample() 返回的原始记录列表。

    Returns:
        FieldInfo 列表，按字段名字母顺序排列，每项包含：
            field_name   (str)  — 字段名
            data_type    (str)  — 推断类型：string / integer / number / boolean / unknown
            sample_value (Any)  — 第一个非空值；全部为空时为 None
            nullable     (bool) — True = 样本中存在 None、空字符串 "" 或纯空白字符串
    """
    if not sample:
        return []

    # 合并所有记录的键集
    all_keys: set[str] = set()
    for record in sample:
        all_keys.update(record.keys())

    fields: list[dict] = []
    for key in sorted(all_keys):
        values = [rec.get(key) for rec in sample]
        non_empty = [v for v in values if not _is_empty(v)]
        sample_value = non_empty[0] if non_empty else None
        nullable = any(_is_empty(v) for v in values)
        data_type = _infer_type(sample_value)

        fields.append({
            "field_name": key,
            "data_type": data_type,
            "sample_value": sample_value,
            "nullable": nullable,
        })

    return fields


# ---------------------------------------------------------------------------
# 私有辅助函数
# ---------------------------------------------------------------------------

def _is_empty(value) -> bool:
    """判断值是否为空（None、空字符串、纯空白字符串）。"""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _infer_type(value) -> str:
    """根据值推断 data_type 标签。

    API 返回已是正确 JSON 类型，但保留字符串解析逻辑以兼容边界情况。

    Args:
        value: 待推断的值（任意类型）。

    Returns:
        'boolean' / 'integer' / 'number' / 'string' / 'unknown'
    """
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        try:
            int(value)
            return "integer"
        except ValueError:
            pass
        try:
            float(value)
            return "number"
        except ValueError:
            pass
    return "string"
