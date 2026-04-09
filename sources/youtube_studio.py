"""YouTube Studio 爬虫数据源模块。

通过 Playwright 浏览器自动化登录 YouTube Studio（Google 账号），
导航至频道分析概览页，抓取频道运营指标字段发现报告。

接口契约（ARCH2）：
    authenticate() -> bool
    fetch_sample(table_name: str = None) -> list[dict]
    extract_fields(sample: list[dict]) -> list[dict]

超时规范（与 Story 4.5 Facebook 一致）：
    PAGE_WAIT_TIMEOUT_MS = 20000  # Playwright 页面等待 20s
    TOTAL_TIMEOUT_S = 90          # 单 source 整体执行 90s 内完成

安全规范（NFR2）：
    日志输出凭证时必须使用 mask_credential()，禁止输出完整密码/邮箱。
"""
import logging
import time
from typing import Optional

# playwright 仅在实际调用时导入，避免顶层 import 在不支持 greenlet 的环境下报错
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    sync_playwright = None  # type: ignore[assignment]
    PlaywrightTimeoutError = Exception  # type: ignore[assignment,misc]

from config.credentials import get_credentials, mask_credential
from reporter import write_raw_report

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

STUDIO_URL = "https://studio.youtube.com"
ANALYTICS_URL = "https://studio.youtube.com/analytics/tab-overview/period-default"

# 超时设置（与 Story 4.5 AC 一致，Google 重定向链路较长）
PAGE_WAIT_TIMEOUT_MS = 20_000  # 20 秒
TOTAL_TIMEOUT_S = 90            # 90 秒

# 目标字段清单（6 个固定中文字段，对应 YouTube Studio 分析概览指标卡片）
TARGET_FIELDS = [
    "播放量",
    "观看时长（小时）",
    "订阅者",
    "曝光次数",
    "点击率",
    "平均观看时长",
]

# 验证码/登录拦截关键词（大小写不敏感匹配）
CAPTCHA_KEYWORDS = [
    "captcha",
    "verify you are human",
    "robot",
    "human verification",
    "验证码",
    "are you a robot",
    "security check",
    "cloudflare",
    "confirm it's you",      # Google 人机验证特有提示
    "verify your identity",  # Google 身份验证提示
]


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------

def authenticate() -> bool:
    """通过 Google 账号完成 YouTube Studio 登录。

    使用 sync_playwright 启动 headless Chromium，打开 YouTube Studio，
    完成 Google 两步登录（先输入邮箱，再输入密码），等待跳转回 studio.youtube.com。

    Returns:
        True  — 登录成功
        False — 凭证无效或页面异常
    """
    if sync_playwright is None:
        logger.error("[youtube_studio] 认证 ... 失败：playwright 未安装，请运行 pip install playwright")
        return False

    try:
        creds = get_credentials()
        email = creds["YOUTUBE_STUDIO_EMAIL"]
        password = creds["YOUTUBE_STUDIO_PASSWORD"]
    except (KeyError, ValueError) as e:
        logger.error(f"[youtube_studio] 认证 ... 失败：凭证获取失败 — {e}")
        return False

    logger.info(f"[youtube_studio] 认证，账号：{mask_credential(email)}")

    browser = None
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            _login(page, email, password)
            _check_captcha(page)

            logger.info("[youtube_studio] 认证 ... 成功")
            return True

        except PlaywrightTimeoutError as e:
            logger.error(f"[youtube_studio] 认证 ... 失败：页面等待超时 — {e}")
            return False
        except RuntimeError as e:
            logger.error(f"[youtube_studio] 认证 ... 失败：{e}")
            return False
        except Exception as e:
            logger.error(f"[youtube_studio] 认证 ... 失败：{e}")
            return False
        finally:
            if browser is not None:
                browser.close()


def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """导航至 YouTube Studio 分析概览页，抓取频道指标样本。

    Args:
        table_name: 保留参数，与接口契约保持一致（ARCH2）；youtube_studio 无多表路由，实际忽略。

    Returns:
        样本记录列表（list[dict]），固定 1 条记录，包含 TARGET_FIELDS 对应的指标值。

    Raises:
        RuntimeError: 检测到验证码、登录拦截、超时或报告写入失败时抛出。

    Notes:
        - 整体执行时间不超过 TOTAL_TIMEOUT_S（90s），多点检查
        - 页面操作超时设置为 PAGE_WAIT_TIMEOUT_MS（20s）
        - 浏览器在 finally 块中保证关闭（NFR6 — 不静默失败）
        - 抓取完成后调用 write_raw_report("youtube_studio", fields, None, ...)
    """
    if sync_playwright is None:
        raise RuntimeError("[youtube_studio] playwright 未安装，请运行 pip install playwright")

    try:
        creds = get_credentials()
        email = creds["YOUTUBE_STUDIO_EMAIL"]
        password = creds["YOUTUBE_STUDIO_PASSWORD"]
    except (KeyError, ValueError) as e:
        logger.error(f"[youtube_studio] fetch_sample ... 失败：凭证获取失败 — {e}")
        raise RuntimeError(f"[youtube_studio] 凭证获取失败：{e}") from e

    logger.info(f"[youtube_studio] fetch_sample，账号：{mask_credential(email)}")
    start_time = time.time()

    browser = None
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Step 1: 登录
            _login(page, email, password)

            # Step 2: 检测验证码（登录后）
            _check_captcha(page)

            # Step 3: 整体超时检查（登录后）
            _check_total_timeout(start_time)

            # Step 4: 导航至分析概览页
            page.goto(ANALYTICS_URL, timeout=PAGE_WAIT_TIMEOUT_MS)
            page.wait_for_load_state("networkidle", timeout=PAGE_WAIT_TIMEOUT_MS)

            # Step 5: 再次检测验证码 + 超时（分析页导航后）
            _check_captcha(page)
            _check_total_timeout(start_time)

            # Step 6: 提取分析指标
            sample = _extract_analytics_metrics(page)
            _check_total_timeout(start_time)

            if not sample:
                logger.warning("[youtube_studio] 分析页未发现指标数据，返回空样本")

            # Step 7: 生成报告
            fields = extract_fields(sample)
            try:
                write_raw_report("youtube_studio", fields, None, len(sample))
            except OSError as e:
                logger.error(f"[youtube_studio] write_raw_report 写入失败：{e}")
                raise RuntimeError(f"[youtube_studio] 报告写入失败：{e}") from e

            logger.info(f"[youtube_studio] fetch_sample ... 成功，抓取 {len(sample)} 条记录")
            return sample

        except RuntimeError:
            # CAPTCHA / 超时 / 报告写入异常直接上抛，不包装
            raise
        except PlaywrightTimeoutError as e:
            logger.error(f"[youtube_studio] fetch_sample ... 失败：页面等待超时 — {e}")
            raise
        except Exception as e:
            logger.error(f"[youtube_studio] fetch_sample ... 失败：{e}")
            raise
        finally:
            if browser is not None:
                browser.close()


def extract_fields(sample: list[dict]) -> list[dict]:
    """从样本数据中提取标准 FieldInfo 结构列表（ARCH2）。

    纯函数，不依赖外部 IO，单元测试直接调用即可。
    使用固定 6 字段映射（TARGET_FIELDS），按 sorted 顺序排列。

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


def _login(page, email: str, password: str) -> None:
    """在已打开的 page 上完成 Google 两步登录，进入 YouTube Studio。

    步骤 1：打开 YouTube Studio（STUDIO_URL），等待自动跳转至 Google 登录页。
    步骤 2：输入邮箱，点击下一步。
    步骤 3：输入密码，点击下一步，等待跳转回 studio.youtube.com。

    Args:
        page: Playwright Page 对象（已创建，未导航）。
        email: Google 登录邮箱。
        password: Google 登录密码。

    Raises:
        PlaywrightTimeoutError: 页面等待超时。
        RuntimeError: 登录后仍在 Google 账号页（凭证错误、2FA 拦截等）。
    """
    # 步骤 1：打开 YouTube Studio，等待跳转至 Google 登录页
    page.goto(STUDIO_URL, timeout=PAGE_WAIT_TIMEOUT_MS)
    page.wait_for_selector("input[type='email']", timeout=PAGE_WAIT_TIMEOUT_MS)

    # 步骤 2：输入邮箱，点击下一步（兼容英文/中文界面）
    page.fill("input[type='email']", email)
    try:
        page.click("button:has-text('Next')", timeout=PAGE_WAIT_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        try:
            page.click("button:has-text('下一步')", timeout=PAGE_WAIT_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            logger.warning("[youtube_studio] 未找到 Next/下一步 按钮，使用 Enter 键提交邮箱")
            page.press("input[type='email']", "Enter")

    # 等待页面过渡完成（Google 登录页邮箱→密码步骤切换）
    page.wait_for_load_state("domcontentloaded", timeout=PAGE_WAIT_TIMEOUT_MS)

    # 步骤 3：等待密码框出现，输入密码
    page.wait_for_selector("input[type='password']", timeout=PAGE_WAIT_TIMEOUT_MS)
    page.fill("input[type='password']", password)
    try:
        page.click("button:has-text('Next')", timeout=PAGE_WAIT_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        try:
            page.click("button:has-text('下一步')", timeout=PAGE_WAIT_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            logger.warning("[youtube_studio] 未找到 Next/下一步 按钮，使用 Enter 键提交密码")
            page.press("input[type='password']", "Enter")

    # 步骤 4：等待跳转回 YouTube Studio（登录链路较长，使用 2× 超时）
    page.wait_for_url("**/studio.youtube.com/**", timeout=PAGE_WAIT_TIMEOUT_MS * 2)

    # 验证确实进入了 Studio（不在 Google 账号页）
    if "accounts.google.com" in page.url or "signin" in page.url.lower():
        raise RuntimeError(
            "[youtube_studio] 登录后仍在 Google 登录页，"
            "凭证可能无效或账号启用了两步验证（2FA）"
        )


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
    except Exception as e:
        logger.warning(f"[youtube_studio] CAPTCHA 检测跳过：无法获取页面内容 — {e}")
        return

    for keyword in CAPTCHA_KEYWORDS:
        if keyword in page_text:
            raise RuntimeError(
                "[youtube_studio] 遇到验证码，请手动完成验证后重新运行"
            )


def _check_total_timeout(start_time: float) -> None:
    """检查整体执行是否超过 TOTAL_TIMEOUT_S（90s）限制。

    Args:
        start_time: 计时起点（time.time() 返回值）。

    Raises:
        RuntimeError: 超时时抛出。
    """
    if time.time() - start_time > TOTAL_TIMEOUT_S:
        raise RuntimeError("[youtube_studio] 整体执行超过 90s 限制，中止")


def _extract_analytics_metrics(page) -> list[dict]:
    """从 YouTube Studio 分析概览页提取频道指标数值。

    YouTube Studio 为 React SPA，使用 JavaScript evaluate 提取指标卡片数据
    比 CSS 选择器更稳定（适应 DOM 版本变动）。

    等待页面内容加载后，依次尝试多种 DOM 结构：
    1. data-testid 属性（标准组件）
    2. 通用 class 名称（备用）
    3. 通用文本节点扫描（兜底）

    Args:
        page: Playwright Page 对象（已导航至 ANALYTICS_URL）。

    Returns:
        list[dict]：固定 1 条记录，key 为 TARGET_FIELDS 中的字段名，
        "—" / "--" 等无数据占位值映射为 None。
    """
    # 等待分析内容区域出现
    try:
        page.wait_for_selector(
            "[data-testid='analytics-card'], .analytics-card, ytcp-analytics-stat-box",
            timeout=PAGE_WAIT_TIMEOUT_MS,
        )
    except Exception:
        logger.warning("[youtube_studio] 未发现标准分析卡片，尝试直接提取页面文本")

    # 使用 JavaScript 提取指标卡片（label + value 配对）
    try:
        metrics_raw: dict = page.evaluate("""
            () => {
                const result = {};

                // 方案 1：ytcp-analytics-stat-box 组件（YouTube Studio 常见结构）
                const statBoxes = document.querySelectorAll('ytcp-analytics-stat-box');
                statBoxes.forEach(box => {
                    const label = box.querySelector('.title-text, [slot="title"], .stat-title');
                    const value = box.querySelector('.value, [slot="value"], .stat-value, .primary-value');
                    if (label && value) {
                        result[label.innerText.trim()] = value.innerText.trim();
                    }
                });

                if (Object.keys(result).length > 0) return result;

                // 方案 2：通用 data-testid 或 analytics-card class
                const cards = document.querySelectorAll(
                    '[data-testid="analytics-card"], .analytics-card'
                );
                cards.forEach(card => {
                    const label = card.querySelector(
                        '.title, [data-testid="title"], h3, h4, .card-title'
                    );
                    const value = card.querySelector(
                        '.value, [data-testid="value"], .metric-value, .card-value'
                    );
                    if (label && value) {
                        result[label.innerText.trim()] = value.innerText.trim();
                    }
                });

                if (Object.keys(result).length > 0) return result;

                // 方案 3：兜底——扫描所有包含数字的短文本节点对
                const allText = document.querySelectorAll('h3, h4, .title, .label');
                allText.forEach(el => {
                    const sibling = el.nextElementSibling;
                    if (sibling && /[\\d,\\.\\-—%:]+/.test(sibling.innerText)) {
                        result[el.innerText.trim()] = sibling.innerText.trim();
                    }
                });

                return result;
            }
        """)
    except Exception as e:
        logger.error(f"[youtube_studio] JS 指标提取失败：{e}")
        metrics_raw = {}

    # 将原始提取结果映射到 TARGET_FIELDS
    record: dict = {}
    for field_name in TARGET_FIELDS:
        raw_value = metrics_raw.get(field_name)
        # "—" 或 "--" 表示无数据，映射为 None
        if raw_value and raw_value.strip() not in ("—", "--", ""):
            record[field_name] = raw_value.strip()
        else:
            record[field_name] = None

    logger.debug(f"[youtube_studio] 提取到的原始指标：{metrics_raw}")

    # 全 None 检查：所有指标为空时明确警告
    if all(v is None for v in record.values()):
        logger.warning("[youtube_studio] 所有指标值均为空（可能页面无数据或 DOM 结构已变更）")

    return [record]


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
        # 去除千位分隔符再尝试解析（如 "1,234" → "1234"）
        cleaned = value.replace(",", "")
        try:
            int(cleaned)
            return "integer"
        except ValueError:
            pass
        try:
            float(cleaned)
            return "number"
        except ValueError:
            pass
    return "string"
