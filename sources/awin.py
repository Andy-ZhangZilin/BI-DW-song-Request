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

# playwright 仅在实际调用时导入，避免顶层 import 在不支持 greenlet 的环境下（Windows 部分配置）报错
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    sync_playwright = None  # type: ignore[assignment]
    PlaywrightTimeoutError = Exception  # type: ignore[assignment,misc]

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

# 最大样本行数
MAX_SAMPLE_ROWS = 20

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
    try:
        creds = get_credentials()
        username = creds["AWIN_USERNAME"]
        password = creds["AWIN_PASSWORD"]
    except (KeyError, ValueError) as e:
        logger.error(f"[awin] 认证 ... 失败：凭证获取失败 — {e}")
        return False

    logger.info(f"[awin] 认证，用户名：{mask_credential(username)}")

    browser = None
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            _login(page, username, password)

            logger.info("[awin] 认证 ... 成功")
            try:
                init_validation_report("awin")
            except OSError as e:
                logger.warning(f"[awin] init_validation_report 写入失败（登录已成功）：{e}")
            return True

        except PlaywrightTimeoutError as e:
            logger.error(f"[awin] 认证 ... 失败：页面等待超时 — {e}")
            return False
        except RuntimeError as e:
            logger.error(f"[awin] 认证 ... 失败：{e}")
            return False
        except Exception as e:
            logger.error(f"[awin] 认证 ... 失败：{e}")
            return False
        finally:
            if browser is not None:
                browser.close()


def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """导航至 Awin 报表页面，抓取样本数据行。

    Args:
        table_name: 保留参数，与接口契约保持一致（ARCH2）；Awin 无多表路由，实际忽略。

    Returns:
        样本记录列表（list[dict]），每项为报表表格中一行的原始字段字典。

    Raises:
        RuntimeError: 检测到验证码、登录拦截、超时或报告写入失败时抛出。

    Notes:
        - 整体执行时间不超过 TOTAL_TIMEOUT_S（60s），多点检查
        - 页面操作超时设置为 PAGE_WAIT_TIMEOUT_MS（15s）
        - 浏览器在 finally 块中保证关闭（NFR6 — 不静默失败）
        - 抓取完成后调用 write_raw_report("awin", fields, None, ...)
    """
    try:
        creds = get_credentials()
        username = creds["AWIN_USERNAME"]
        password = creds["AWIN_PASSWORD"]
    except (KeyError, ValueError) as e:
        logger.error(f"[awin] fetch_sample ... 失败：凭证获取失败 — {e}")
        raise RuntimeError(f"[awin] 凭证获取失败：{e}") from e

    logger.info(f"[awin] fetch_sample，用户名：{mask_credential(username)}")
    start_time = time.time()

    browser = None
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Step 1: 登录
            _login(page, username, password)

            # Step 2: 检测验证码（在导航至报表前）
            _check_captcha(page)

            # Step 3: 整体超时检查（登录后）
            _check_total_timeout(start_time)

            # Step 4: 导航至报表页
            page.goto(AWIN_REPORT_URL, timeout=PAGE_WAIT_TIMEOUT_MS)
            page.wait_for_load_state("networkidle", timeout=PAGE_WAIT_TIMEOUT_MS)

            # Step 5: 再次检测验证码 + 超时（报表页导航后）
            _check_captcha(page)
            _check_total_timeout(start_time)

            # Step 6: 抓取表格行
            sample = _extract_table_rows(page)

            if not sample:
                logger.warning("[awin] 报表页未发现数据行，返回空样本")

            # Step 7: 生成报告（table_name 硬编码 None，Awin 无多表路由）
            fields = extract_fields(sample)
            try:
                write_raw_report("awin", fields, None, len(sample))
            except OSError as e:
                logger.error(f"[awin] write_raw_report 写入失败：{e}")
                raise RuntimeError(f"[awin] 报告写入失败：{e}") from e

            logger.info(f"[awin] fetch_sample ... 成功，抓取 {len(sample)} 条记录")
            return sample

        except RuntimeError:
            # CAPTCHA / 超时 / 报告写入异常直接上抛，不包装
            raise
        except PlaywrightTimeoutError as e:
            logger.error(f"[awin] fetch_sample ... 失败：页面等待超时 — {e}")
            raise
        except Exception as e:
            logger.error(f"[awin] fetch_sample ... 失败：{e}")
            raise
        finally:
            if browser is not None:
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


def _login(page, username: str, password: str) -> None:
    """在已打开的 page 上完成 Awin 账号登录。

    两个公开函数（authenticate / fetch_sample）各自独立管理浏览器生命周期，
    但共享此登录逻辑，避免重复代码。

    Args:
        page: Playwright Page 对象（已创建，未导航）。
        username: Awin 登录用户名。
        password: Awin 登录密码。

    Raises:
        PlaywrightTimeoutError: 页面等待超时。
        RuntimeError: 登录后仍停留在登录页（凭证错误或其他拦截）。
    """
    page.goto(AWIN_LOGIN_URL, timeout=PAGE_WAIT_TIMEOUT_MS)

    # Step 1: 填入邮箱，点击 Continue（两步登录流程）
    page.wait_for_selector("input[type='email'], input[name='username'], input[type='text']", timeout=PAGE_WAIT_TIMEOUT_MS)
    email_input = page.query_selector("input[type='email']") or page.query_selector("input[name='username']") or page.query_selector("input[type='text']")
    if email_input is None:
        raise RuntimeError("[awin] 未找到邮箱输入框")
    email_input.fill(username)
    page.click("button[type='submit'], button:has-text('Continue')")

    # Step 2: 等待密码框出现，填入密码并提交
    page.wait_for_selector("input[type='password']", timeout=PAGE_WAIT_TIMEOUT_MS)
    page.fill("input[type='password']", password)
    page.click("button[type='submit']")

    # 等待页面跳出登录流程（URL 不再含 login/prelogin/idp 关键词）
    page.wait_for_function(
        "() => !['login', 'prelogin', '/idp/'].some(k => window.location.href.includes(k))",
        timeout=PAGE_WAIT_TIMEOUT_MS,
    )

    # 验证确实离开了登录页
    current_url = page.url.lower()
    if any(k in current_url for k in ("login", "prelogin", "/idp/")):
        raise RuntimeError("[awin] 登录后仍停留在登录页，凭证可能无效")


def _check_captcha(page) -> None:
    """检测当前页面是否出现验证码或登录拦截。

    使用 document.body.innerText 而非 page.content()，
    避免脚本/CSS 中嵌入的关键词触发误报。

    Args:
        page: Playwright Page 对象。

    Raises:
        RuntimeError: 检测到验证码关键词时抛出，提示操作者手动干预。
    """
    try:
        page_text = page.evaluate("() => document.body ? document.body.innerText : ''").lower()
    except Exception:
        return  # 无法获取页面内容时跳过检测

    for keyword in CAPTCHA_KEYWORDS:
        if keyword in page_text:
            raise RuntimeError(
                "[awin] 遇到验证码，请手动完成验证后重新运行"
            )


def _check_total_timeout(start_time: float) -> None:
    """检查整体执行是否超过 TOTAL_TIMEOUT_S 限制。

    Args:
        start_time: 计时起点（time.time() 返回值）。

    Raises:
        RuntimeError: 超时时抛出。
    """
    if time.time() - start_time > TOTAL_TIMEOUT_S:
        raise RuntimeError("[awin] 整体执行超过 60s 限制，中止")


def _extract_table_rows(page) -> list[dict]:
    """从报表页表格中提取所有数据行。

    尝试解析 <table> 元素的表头与数据行，构建字段名 → 值的字典列表。
    若找不到显式表头，使用 col_0, col_1, ... 作为字段名。

    Args:
        page: Playwright Page 对象（已导航至报表页）。

    Returns:
        list[dict]：每个 dict 代表一行数据，key 为列名，value 为单元格文本。

    Raises:
        RuntimeError: 表格提取过程中发生不可恢复的 Playwright 错误。
    """
    rows: list[dict] = []
    try:
        # 尝试读取表格表头
        raw_headers = page.evaluate("""
            () => {
                const th = Array.from(document.querySelectorAll('table thead th, table thead td, table tr:first-child th'));
                return th.map(h => h.innerText.trim());
            }
        """)

        # 规范化表头：补全空字符串、去重重复列名
        headers = _normalize_headers(raw_headers)

        if not headers:
            # 无表头：使用 col_0, col_1, ... 作为字段名
            # 优先使用 tbody tr，避免将 thead/th 行混入数据
            data_rows = page.query_selector_all("table tbody tr")
            if not data_rows:
                # 无 tbody 时，跳过第一行（潜在表头）
                all_rows = page.query_selector_all("table tr")
                data_rows = all_rows[1:] if len(all_rows) > 1 else []
            for row in data_rows[:MAX_SAMPLE_ROWS]:
                cells = row.query_selector_all("td")
                if cells:
                    record = {f"col_{i}": cell.inner_text().strip()
                              for i, cell in enumerate(cells)}
                    rows.append(record)
        else:
            # 有表头，按列名构建字典
            data_rows = page.query_selector_all("table tbody tr")
            for row in data_rows[:MAX_SAMPLE_ROWS]:
                cells = row.query_selector_all("td")
                if len(cells) < len(headers):
                    logger.warning(
                        f"[awin] 跳过不完整行：期望 {len(headers)} 列，实际 {len(cells)} 列"
                    )
                    continue
                record = {
                    headers[i]: cells[i].inner_text().strip()
                    for i in range(len(headers))
                }
                rows.append(record)

    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"[awin] 提取表格行时发生异常：{e}")
        raise RuntimeError(f"[awin] 表格提取失败：{e}") from e

    return rows


def _normalize_headers(raw_headers: list) -> list[str]:
    """规范化表头列表：补全空字符串、去重重复列名。

    Args:
        raw_headers: evaluate() 返回的原始表头字符串列表。

    Returns:
        规范化后的列名列表（与输入等长）。
    """
    if not raw_headers:
        return []

    seen: dict[str, int] = {}
    result: list[str] = []
    for i, h in enumerate(raw_headers):
        name = h.strip() if h else f"col_{i}"
        if not name:
            name = f"col_{i}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        result.append(name)
    return result


def _infer_type(value) -> str:
    """根据值推断 data_type 标签。

    对字符串值尝试解析为数值类型（Playwright inner_text 始终返回字符串，
    但字段语义类型对报告更有价值）。

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
        # 尝试解析字符串编码的数值（Playwright inner_text 始终返回字符串）
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
