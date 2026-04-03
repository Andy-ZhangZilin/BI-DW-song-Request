"""PartnerBoost 联盟营销平台爬虫数据源接入模块。

通过 Playwright headless Chromium 完成账号密码登录并抓取报表页数据字段。

公开接口：
    authenticate() -> bool                              — 验证账号密码可登录
    fetch_sample(table_name=None) -> list[dict]         — 登录后抓取报表样本记录
    extract_fields(sample) -> list[dict]                — 从样本中提取标准 FieldInfo 列表
"""

import logging
from typing import Optional

from playwright.sync_api import sync_playwright, Page

import config.credentials as _creds_module

logger = logging.getLogger(__name__)

SOURCE_NAME = "partnerboost"
LOGIN_URL = "https://app.partnerboost.com/login"
REPORTS_URL = "https://app.partnerboost.com/reports"

# 验证码关键词（大小写不敏感）
_CAPTCHA_KEYWORDS = ["captcha", "robot", "verify you are human"]

# 页面等待超时：15s（来自 ARCH10）
_PAGE_TIMEOUT = 15_000


def _check_captcha(content: str) -> None:
    """检查页面内容是否含验证码关键词，是则抛出 RuntimeError。"""
    lower = content.lower()
    if any(kw in lower for kw in _CAPTCHA_KEYWORDS):
        raise RuntimeError(f"[{SOURCE_NAME}] 遇到验证码，请手动完成验证后重新运行")


def authenticate() -> bool:
    """使用 sync_playwright 启动 headless Chromium 完成账号密码登录。

    成功返回 True，失败日志记录后返回 False。浏览器始终在 finally 块中关闭。

    Returns:
        True — 登录成功；False — 登录失败或异常
    """
    creds = _creds_module.get_credentials()
    username = creds["PARTNERBOOST_USERNAME"]
    password = creds["PARTNERBOOST_PASSWORD"]
    logger.debug(f"[{SOURCE_NAME}] 使用账号：{_creds_module.mask_credential(username)}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(LOGIN_URL, timeout=_PAGE_TIMEOUT)
            page.fill("input[name=email]", username)
            page.fill("input[name=password]", password)
            page.click("button[type=submit]")
            # 等待跳离登录页（使用 lambda 谓词，避免 glob 不支持 (a|b) 交替语法）
            page.wait_for_url(lambda url: "login" not in url, timeout=_PAGE_TIMEOUT)
            logger.info(f"[{SOURCE_NAME}] 认证 ... 成功")
            return True
        except Exception as e:
            logger.info(f"[{SOURCE_NAME}] 认证 ... 失败：{e}")
            return False
        finally:
            browser.close()


def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """登录 PartnerBoost 后导航至报表页，抓取至少一条记录。

    页面等待超时 15s；遇到验证码抛出 RuntimeError；
    其他爬虫异常包装为 RuntimeError 后重新抛出。
    浏览器始终在 finally 块中关闭。

    Args:
        table_name: 爬虫数据源为单表，此参数忽略，传 None 即可

    Returns:
        原始记录列表（list[dict]），至少一条

    Raises:
        RuntimeError: 遇到验证码、未找到数据行、或爬虫其他异常
    """
    creds = _creds_module.get_credentials()
    username = creds["PARTNERBOOST_USERNAME"]
    password = creds["PARTNERBOOST_PASSWORD"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # ── 登录 ──────────────────────────────────────────────────────────
            page.goto(LOGIN_URL, timeout=_PAGE_TIMEOUT)
            page.fill("input[name=email]", username)
            page.fill("input[name=password]", password)
            page.click("button[type=submit]")
            # 等待跳离登录页（lambda 谓词，避免 glob (a|b) 非标准语法）
            page.wait_for_url(lambda url: "login" not in url, timeout=_PAGE_TIMEOUT)
            # 等待页面稳定后再检测验证码
            page.wait_for_load_state("networkidle", timeout=_PAGE_TIMEOUT)

            # 登录后验证码检测
            _check_captcha(page.content())

            # ── 导航至报表页 ──────────────────────────────────────────────────
            page.goto(REPORTS_URL, timeout=_PAGE_TIMEOUT)
            page.wait_for_load_state("networkidle", timeout=_PAGE_TIMEOUT)

            # 报表页验证码检测
            _check_captcha(page.content())

            # ── 抓取表格数据 ──────────────────────────────────────────────────
            records = _extract_table_records(page)

            if not records:
                raise RuntimeError(
                    f"[{SOURCE_NAME}] 未找到数据行，页面可能无数据或表格结构已变更"
                )

            logger.info(f"[{SOURCE_NAME}] 获取报表样本 ... 成功，共 {len(records)} 条记录")
            return records

        except RuntimeError:
            raise  # 验证码 / 数据缺失错误直接透传
        except Exception as e:
            raise RuntimeError(f"[{SOURCE_NAME}] 爬虫异常：{e}")
        finally:
            browser.close()


def _extract_table_records(page: Page) -> list[dict]:
    """从当前页面提取第一个 <table> 的表头 + 第一行数据，返回记录列表。"""
    header_cells = page.query_selector_all("table thead th, table thead td")
    headers = [cell.inner_text().strip() or f"_col{i}" for i, cell in enumerate(header_cells)]

    rows = page.query_selector_all("table tbody tr")
    if not rows or not headers:
        return []

    first_row = rows[0]
    cells = first_row.query_selector_all("td")
    values = [cell.inner_text().strip() for cell in cells]

    col_count = min(len(headers), len(values))
    if col_count == 0:
        return []

    record = {headers[i]: values[i] for i in range(col_count)}
    return [record]


def extract_fields(sample: list[dict]) -> list[dict]:
    """从报表样本中提取标准 FieldInfo 列表。纯函数，无 I/O。

    PartnerBoost 报表为扁平结构（无嵌套 dict），直接按列名提取。
    数据类型推断：None → null；bool → boolean；int/float → number；其他 → string。

    Args:
        sample: fetch_sample() 返回的原始记录列表

    Returns:
        FieldInfo 列表，每项含 field_name / data_type / sample_value / nullable
    """
    if not sample:
        return []

    # 合并所有记录的键（防止首条记录缺失某列）
    all_keys: list[str] = []
    seen: set[str] = set()
    for record in sample:
        for key in record:
            if key not in seen:
                all_keys.append(key)
                seen.add(key)

    fields: list[dict] = []
    for key in all_keys:
        sample_value = None
        nullable = False

        for record in sample:
            val = record.get(key)
            if val is None or val == "":
                nullable = True
            else:
                if sample_value is None:
                    sample_value = val

        data_type = _infer_type(sample_value)

        fields.append({
            "field_name": key,
            "data_type": data_type,
            "sample_value": sample_value,
            "nullable": nullable,
        })

    return fields


def _infer_type(value) -> str:
    """推断值的数据类型字符串。"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    return "string"
