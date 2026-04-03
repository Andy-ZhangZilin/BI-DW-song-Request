"""Awin 爬虫数据源模块。

通过 Playwright 浏览器自动化登录 Awin 联盟后台，导航至报表页面，抓取字段发现报告。

接口契约（ARCH2）：
    authenticate() -> bool
    fetch_sample(table_name: str = None) -> list[dict]
    extract_fields(sample: list[dict]) -> list[dict]

超时规范（ARCH10）：
    PAGE_WAIT_TIMEOUT_MS = 15000  # Playwright 页面等待 15s
    TOTAL_TIMEOUT_S = 60          # 单 source 整体执行 60s 内完成

安全规范（NFR2）：
    日志输出凭证时必须使用 mask_credential()，禁止输出完整密码/Token。
"""
import logging
import time
from typing import Optional

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from config.credentials import get_credentials, mask_credential
from reporter import write_raw_report, init_validation_report

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

AWIN_LOGIN_URL = "https://ui.awin.com/user/login"
# 报表页（publisher transactions 列表）
AWIN_REPORT_URL = "https://ui.awin.com/awin/publisher/transactions/listing"

# 超时设置（ARCH10）
PAGE_WAIT_TIMEOUT_MS = 15_000  # 15 秒
TOTAL_TIMEOUT_S = 60            # 60 秒

# 验证码/登录拦截关键词（大小写不敏感匹配）
CAPTCHA_KEYWORDS = [
    "captcha",
    "verify you are human",
    "robot",
    "human verification",
    "challenge",
    "验证码",
    "are you a robot",
    "security check",
    "cloudflare",
]


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------

def authenticate() -> bool:
    """通过账号密码完成 Awin 后台登录。

    使用 sync_playwright 启动 headless Chromium，填入 AWIN_USERNAME /
    AWIN_PASSWORD，等待登录成功后返回 True。

    Returns:
        True  — 登录成功
        False — 凭证无效或页面异常

    Side effects:
        登录成功后调用 init_validation_report("awin")（仅首次创建模板文件）。
    """
    creds = get_credentials()
    username = creds["AWIN_USERNAME"]
    password = creds["AWIN_PASSWORD"]
    logger.info(f"[awin] 认证，用户名：{mask_credential(username)}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(AWIN_LOGIN_URL, timeout=PAGE_WAIT_TIMEOUT_MS)

            # 填写登录表单
            page.fill("input[name='username']", username)
            page.fill("input[name='password']", password)
            page.click("button[type='submit']")

            # 等待跳转至已登录页面
            page.wait_for_url(
                "**/awin/**",
                timeout=PAGE_WAIT_TIMEOUT_MS,
            )

            logger.info("[awin] 认证 ... 成功")
            init_validation_report("awin")
            return True

        except PlaywrightTimeoutError as e:
            logger.error(f"[awin] 认证 ... 失败：页面等待超时 — {e}")
            return False
        except Exception as e:
            logger.error(f"[awin] 认证 ... 失败：{e}")
            return False
        finally:
            browser.close()


def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """导航至 Awin 报表页面，抓取样本数据行。

    Args:
        table_name: 保留参数，与接口契约保持一致（ARCH2）；Awin 无多表路由，实际忽略。

    Returns:
        样本记录列表（list[dict]），每项为报表表格中一行的原始字段字典。

    Raises:
        RuntimeError: 检测到验证码或登录拦截时，提示操作者手动干预。

    Notes:
        - 整体执行时间不超过 TOTAL_TIMEOUT_S（60s）
        - 页面操作超时设置为 PAGE_WAIT_TIMEOUT_MS（15s）
        - 浏览器在 finally 块中保证关闭（NFR6 — 不静默失败）
        - 抓取完成后调用 write_raw_report("awin", ...)
    """
    creds = get_credentials()
    username = creds["AWIN_USERNAME"]
    password = creds["AWIN_PASSWORD"]

    start_time = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()

            # Step 1: 登录
            page.goto(AWIN_LOGIN_URL, timeout=PAGE_WAIT_TIMEOUT_MS)
            page.fill("input[name='username']", username)
            page.fill("input[name='password']", password)
            page.click("button[type='submit']")
            page.wait_for_url("**/awin/**", timeout=PAGE_WAIT_TIMEOUT_MS)

            # Step 2: 检测验证码（在导航至报表前）
            _check_captcha(page)

            # Step 3: 整体超时检查
            if time.time() - start_time > TOTAL_TIMEOUT_S:
                raise RuntimeError("[awin] 整体执行超过 60s 限制，中止")

            # Step 4: 导航至报表页
            page.goto(AWIN_REPORT_URL, timeout=PAGE_WAIT_TIMEOUT_MS)
            page.wait_for_load_state("networkidle", timeout=PAGE_WAIT_TIMEOUT_MS)

            # Step 5: 再次检测验证码
            _check_captcha(page)

            # Step 6: 抓取表格行
            sample = _extract_table_rows(page)

            if not sample:
                logger.warning("[awin] 报表页未发现数据行，返回空样本")

            # Step 7: 生成报告
            fields = extract_fields(sample)
            write_raw_report("awin", fields, table_name, len(sample))
            logger.info(f"[awin] fetch_sample ... 成功，抓取 {len(sample)} 条记录")
            return sample

        except RuntimeError:
            # CAPTCHA / 超时异常直接上抛，不包装
            raise
        except PlaywrightTimeoutError as e:
            logger.error(f"[awin] fetch_sample ... 失败：页面等待超时 — {e}")
            raise
        except Exception as e:
            logger.error(f"[awin] fetch_sample ... 失败：{e}")
            raise
        finally:
            browser.close()


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
            nullable     (bool) — True = 样本中存在 None 或空字符串 ""
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
        non_empty = [v for v in values if v is not None and v != ""]
        sample_value = non_empty[0] if non_empty else None
        nullable = any(v is None or v == "" for v in values)
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

def _check_captcha(page) -> None:
    """检测当前页面是否出现验证码或登录拦截。

    Args:
        page: Playwright Page 对象。

    Raises:
        RuntimeError: 检测到验证码关键词时抛出，提示操作者手动干预。
    """
    try:
        page_text = page.content().lower()
    except Exception:
        return  # 无法获取页面内容时跳过检测

    for keyword in CAPTCHA_KEYWORDS:
        if keyword in page_text:
            raise RuntimeError(
                "[awin] 遇到验证码，请手动完成验证后重新运行"
            )


def _extract_table_rows(page) -> list[dict]:
    """从报表页表格中提取所有数据行。

    尝试解析 <table> 元素的表头与数据行，构建字段名 → 值的字典列表。
    若找不到 <table>，尝试通用列表结构（<tr> 第一行作为表头）。

    Args:
        page: Playwright Page 对象（已导航至报表页）。

    Returns:
        list[dict]：每个 dict 代表一行数据，key 为列名，value 为单元格文本。
    """
    rows: list[dict] = []
    try:
        # 尝试读取表格表头
        headers = page.evaluate("""
            () => {
                const th = Array.from(document.querySelectorAll('table thead th, table thead td, table tr:first-child th'));
                return th.map(h => h.innerText.trim());
            }
        """)

        if not headers:
            # 无表头，使用 col_0, col_1, ... 作为字段名
            data_rows = page.query_selector_all("table tbody tr, table tr:not(:first-child)")
            for row in data_rows[:20]:  # 最多取 20 行
                cells = row.query_selector_all("td")
                if cells:
                    record = {f"col_{i}": cell.inner_text().strip()
                              for i, cell in enumerate(cells)}
                    rows.append(record)
        else:
            # 有表头，按列名构建字典
            data_rows = page.query_selector_all("table tbody tr")
            for row in data_rows[:20]:
                cells = row.query_selector_all("td")
                if len(cells) >= len(headers):
                    record = {
                        headers[i]: cells[i].inner_text().strip()
                        for i in range(len(headers))
                    }
                    rows.append(record)

    except Exception as e:
        logger.warning(f"[awin] 提取表格行时发生异常：{e}")

    return rows


def _infer_type(value) -> str:
    """根据 Python 原生类型推断 data_type 标签。

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
    return "string"
