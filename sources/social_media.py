"""Facebook Business Suite 爬虫数据源模块。

通过 Playwright 浏览器自动化登录 Meta Business Suite，导航至帖子和 Reels 页面，
抓取帖子列表字段发现报告。

接口契约（ARCH2）：
    authenticate() -> bool
    fetch_sample(table_name: str = None) -> list[dict]
    extract_fields(sample: list[dict]) -> list[dict]

超时规范（Story 4.5 AC 指定，比其他爬虫更长）：
    PAGE_WAIT_TIMEOUT_MS = 20000  # Playwright 页面等待 20s
    TOTAL_TIMEOUT_S = 90          # 单 source 整体执行 90s 内完成

安全规范（NFR2）：
    日志输出凭证时必须使用 mask_credential()，禁止输出完整密码/Token。
"""
import logging
import os
import time
from typing import Optional

# playwright 仅在实际调用时导入，避免顶层 import 在不支持 greenlet 的环境下报错
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

FB_LOGIN_URL = "https://business.facebook.com/business/loginpage"
POSTS_URL = "https://business.facebook.com/latest/posts/published_posts"

# 超时设置（Facebook 页面加载较慢，需要更长超时）
PAGE_WAIT_TIMEOUT_MS = 60_000  # 60 秒
TOTAL_TIMEOUT_S = 180           # 180 秒

# 最大样本行数
MAX_SAMPLE_ROWS = 20

# 目标字段清单（7 个固定中文字段，Facebook 页面列名与此一致）
TARGET_FIELDS = [
    "标题",
    "发布日期",
    "状态",
    "覆盖人数",
    "获赞数和心情数",
    "评论数",
    "分享次数",
]

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
    "confirm your identity",  # Facebook 人机验证特有提示
]


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------

def authenticate() -> bool:
    """通过账号密码完成 Meta Business Suite 登录。

    使用 sync_playwright 启动 headless Chromium，打开 Business Suite 登录页，
    点击"使用 Facebook 登录"按钮，填入账号密码，等待跳转成功后返回 True。

    Returns:
        True  — 登录成功
        False — 凭证无效或页面异常

    Side effects:
        登录成功后调用 init_validation_report("social_media")（仅首次创建模板文件）。
    """
    try:
        creds = get_credentials()
        username = creds["FACEBOOK_USERNAME"]
        password = creds["FACEBOOK_PASSWORD"]
    except (KeyError, ValueError) as e:
        logger.error(f"[social_media] 认证 ... 失败：凭证获取失败 — {e}")
        return False

    logger.info(f"[social_media] 认证，用户名：{mask_credential(username)}")

    browser = None
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=os.environ.get("PLAYWRIGHT_HEADED") != "1")
            page = browser.new_page()
            _login(page, username, password)

            logger.info("[social_media] 认证 ... 成功")
            try:
                init_validation_report("social_media")
            except OSError as e:
                logger.warning(f"[social_media] init_validation_report 写入失败（登录已成功）：{e}")
            return True

        except PlaywrightTimeoutError as e:
            logger.error(f"[social_media] 认证 ... 失败：页面等待超时 — {e}")
            return False
        except RuntimeError as e:
            logger.error(f"[social_media] 认证 ... 失败：{e}")
            return False
        except Exception as e:
            logger.error(f"[social_media] 认证 ... 失败：{e}")
            return False
        finally:
            if browser is not None:
                browser.close()


def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """导航至帖子和 Reels 页面，抓取样本数据行。

    Args:
        table_name: 保留参数，与接口契约保持一致（ARCH2）；social_media 无多表路由，实际忽略。

    Returns:
        样本记录列表（list[dict]），每项为列表中一行的原始字段字典。

    Raises:
        RuntimeError: 检测到验证码、登录拦截、超时或报告写入失败时抛出。

    Notes:
        - 整体执行时间不超过 TOTAL_TIMEOUT_S（90s），多点检查
        - 页面操作超时设置为 PAGE_WAIT_TIMEOUT_MS（20s）
        - 浏览器在 finally 块中保证关闭（NFR6 — 不静默失败）
        - 抓取完成后调用 write_raw_report("social_media", fields, None, ...)
    """
    try:
        creds = get_credentials()
        username = creds["FACEBOOK_USERNAME"]
        password = creds["FACEBOOK_PASSWORD"]
    except (KeyError, ValueError) as e:
        logger.error(f"[social_media] fetch_sample ... 失败：凭证获取失败 — {e}")
        raise RuntimeError(f"[social_media] 凭证获取失败：{e}") from e

    logger.info(f"[social_media] fetch_sample，用户名：{mask_credential(username)}")
    start_time = time.time()

    browser = None
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=os.environ.get("PLAYWRIGHT_HEADED") != "1")
            page = browser.new_page()

            # Step 1: 登录
            _login(page, username, password)

            # Step 2: 检测验证码（登录后）
            _check_captcha(page)

            # Step 3: 整体超时检查（登录后）
            _check_total_timeout(start_time)

            # Step 4: 导航至帖子和 Reels 页面
            page.goto(POSTS_URL, timeout=PAGE_WAIT_TIMEOUT_MS, wait_until="domcontentloaded")
            page.wait_for_load_state("domcontentloaded", timeout=PAGE_WAIT_TIMEOUT_MS)

            # Step 5: 再次检测验证码 + 超时（帖子页导航后）
            _check_captcha(page)
            _check_total_timeout(start_time)

            # Step 6: 抓取帖子行
            sample = _extract_post_rows(page)

            if not sample:
                logger.warning("[social_media] 帖子页未发现数据行，返回空样本")

            # Step 7: 生成报告
            fields = extract_fields(sample)
            try:
                write_raw_report("social_media", fields, None, len(sample))
                init_validation_report("social_media")
            except OSError as e:
                logger.error(f"[social_media] write_raw_report 写入失败：{e}")
                raise RuntimeError(f"[social_media] 报告写入失败：{e}") from e

            logger.info(f"[social_media] fetch_sample ... 成功，抓取 {len(sample)} 条记录")
            return sample

        except RuntimeError:
            # CAPTCHA / 超时 / 报告写入异常直接上抛，不包装
            raise
        except PlaywrightTimeoutError as e:
            logger.error(f"[social_media] fetch_sample ... 失败：页面等待超时 — {e}")
            raise
        except Exception as e:
            logger.error(f"[social_media] fetch_sample ... 失败：{e}")
            raise
        finally:
            if browser is not None:
                browser.close()


def extract_fields(sample: list[dict]) -> list[dict]:
    """从样本数据中提取标准 FieldInfo 结构列表（ARCH2）。

    纯函数，不依赖外部 IO，单元测试直接调用即可。
    使用固定 7 字段映射（TARGET_FIELDS），按 sorted 顺序排列，不做动态列名发现。

    Args:
        sample: fetch_sample() 返回的原始记录列表。

    Returns:
        FieldInfo 列表，按字段名 sorted 顺序排列，每项包含：
            field_name   (str)  — 字段名（TARGET_FIELDS 中的固定中文字段）
            data_type    (str)  — 推断类型：string / integer / number / boolean / unknown
            sample_value (Any)  — 第一个非空值；全部为空时为 None
            nullable     (bool) — True = 样本中存在 None、空字符串 "" 或纯空白字符串
    """
    if not sample:
        return []

    fields = []
    for field_name in sorted(TARGET_FIELDS):
        values = [rec.get(field_name) for rec in sample]
        non_empty = [v for v in values if not _is_empty(v)]
        sample_value = non_empty[0] if non_empty else None
        nullable = any(_is_empty(v) for v in values)
        fields.append({
            "field_name": field_name,
            "data_type": _infer_type(sample_value),
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
    """在已打开的 page 上完成 Meta Business Suite 登录。

    支持两种登录路径（自动探测）：
      A) 页面直接展示邮箱/密码输入框 — 直接填写提交。
      B) 页面右侧展示"使用 Facebook 登录"按钮 — 点击后弹出 popup 窗口填写。

    Args:
        page: Playwright Page 对象（已创建，未导航）。
        username: Facebook 登录邮箱/手机号。
        password: Facebook 登录密码。

    Raises:
        PlaywrightTimeoutError: 页面等待超时。
        RuntimeError: 登录后仍停留在登录页（凭证错误或其他拦截）。
    """
    # 步骤 1：打开 Business Suite 登录入口
    page.goto(FB_LOGIN_URL, timeout=PAGE_WAIT_TIMEOUT_MS, wait_until="domcontentloaded")

    # 步骤 2：探测登录方式 — 页面内直接输入 vs. popup 弹窗
    email_input = page.locator("input[name='email']")
    try:
        email_input.wait_for(state="visible", timeout=10_000)
        # 路径 A：页面内直接有输入框，直接填写
        logger.info("[social_media] 登录路径 A：页面内直接输入")
        page.fill("input[name='email']", username)
        page.fill("input[name='pass']", password)
        page.click("button[name='login'], button[type='submit']")
    except Exception:
        # 路径 B：需要点击"使用 Facebook 登录"按钮触发 popup
        logger.info("[social_media] 登录路径 B：popup 弹窗登录")
        with page.expect_popup(timeout=PAGE_WAIT_TIMEOUT_MS) as popup_info:
            try:
                page.click("text=使用 Facebook 登录", timeout=PAGE_WAIT_TIMEOUT_MS)
            except Exception:
                try:
                    page.get_by_role("link", name="使用 Facebook 登录").click(timeout=PAGE_WAIT_TIMEOUT_MS)
                except Exception:
                    page.get_by_text("使用 Facebook 登录").click(timeout=PAGE_WAIT_TIMEOUT_MS)

        popup = popup_info.value
        popup.wait_for_selector("input[name='email']", timeout=PAGE_WAIT_TIMEOUT_MS)
        popup.fill("input[name='email']", username)
        popup.fill("input[name='pass']", password)
        popup.click("button[name='login']")

    # 步骤 3：等待跳转回 Business Suite 主页面
    page.wait_for_url("**/latest/**", timeout=PAGE_WAIT_TIMEOUT_MS)

    # 验证确实离开了登录页（凭证错误/2FA 重定向时 URL 可能误匹配）
    if "login" in page.url.lower():
        raise RuntimeError("[social_media] 登录后仍停留在登录页，凭证可能无效")


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
                "[social_media] 遇到验证码，请手动完成验证后重新运行"
            )


def _check_total_timeout(start_time: float) -> None:
    """检查整体执行是否超过 TOTAL_TIMEOUT_S（90s）限制。

    Args:
        start_time: 计时起点（time.time() 返回值）。

    Raises:
        RuntimeError: 超时时抛出。
    """
    if time.time() - start_time > TOTAL_TIMEOUT_S:
        raise RuntimeError("[social_media] 整体执行超过 90s 限制，中止")


def _extract_post_rows(page) -> list[dict]:
    """从帖子和 Reels 页面列表中提取数据行。

    等待页面列表内容出现后，先尝试标准 HTML table，再尝试 ARIA role='row' 结构。
    按 TARGET_FIELDS 列名构建字典，"--" 视为空值（映射为 None）。

    Args:
        page: Playwright Page 对象（已导航至 POSTS_URL）。

    Returns:
        list[dict]：每个 dict 代表一行数据，key 为 TARGET_FIELDS 中的列名。

    Raises:
        RuntimeError: 提取过程中发生不可恢复的 Playwright 错误。
    """
    rows: list[dict] = []
    try:
        # 等待表格或列表行出现
        try:
            page.wait_for_selector("table", timeout=PAGE_WAIT_TIMEOUT_MS)
        except Exception:
            try:
                page.wait_for_selector("[role='row']", timeout=PAGE_WAIT_TIMEOUT_MS)
            except Exception:
                logger.warning("[social_media] 未发现表格或列表行元素，尝试直接提取")

        # 尝试提取标准 HTML table 表头
        raw_headers = page.evaluate("""
            () => {
                const ths = Array.from(document.querySelectorAll(
                    'table thead th, table thead td, table tr:first-child th'
                ));
                return ths.map(h => h.innerText.trim());
            }
        """)

        if any(h.strip() for h in raw_headers):
            # 找到表头，按表头与 TARGET_FIELDS 交叉匹配提取数据行
            data_rows = page.query_selector_all("table tbody tr")
            for row_el in data_rows[:MAX_SAMPLE_ROWS]:
                cells = row_el.query_selector_all("td")
                if not cells:
                    continue
                record = {}
                for i, header in enumerate(raw_headers):
                    if header in TARGET_FIELDS and i < len(cells):
                        text = cells[i].inner_text().strip()
                        record[header] = text if text and text != "--" else None
                if record:
                    rows.append(record)
        else:
            # 无标准表头，尝试 ARIA role='row' 结构（React 渲染列表）
            all_rows = page.query_selector_all("[role='row']")
            # 过滤出含有 role='cell' 子元素的行（跳过表头行）
            data_rows = [r for r in all_rows if r.query_selector_all("[role='cell']")]
            for row_el in data_rows[:MAX_SAMPLE_ROWS]:
                cells = row_el.query_selector_all("[role='cell']")
                if len(cells) < len(TARGET_FIELDS):
                    continue
                record = {}
                for i, field_name in enumerate(TARGET_FIELDS):
                    text = cells[i].inner_text().strip() if i < len(cells) else None
                    record[field_name] = text if text and text != "--" else None
                rows.append(record)

    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"[social_media] 提取帖子行时发生异常：{e}")
        raise RuntimeError(f"[social_media] 帖子列表提取失败：{e}") from e

    return rows


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
