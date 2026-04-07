"""CartSee EDM 爬虫数据源接入模块。

通过 Playwright headless Chromium 登录 CartSee 后台，抓取 EDM 邮件营销数据字段。

公开接口：
    authenticate() -> bool
    fetch_sample(table_name: str = None) -> list[dict]
    extract_fields(sample: list[dict]) -> list[dict]
"""
import logging
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None  # type: ignore[assignment]
from config.credentials import get_credentials, mask_credential

logger = logging.getLogger(__name__)
SOURCE_NAME = "cartsee"


def authenticate() -> bool:
    """使用账号密码通过 Playwright 登录 CartSee EDM 后台。
    成功返回 True，失败打印错误并返回 False。浏览器在 finally 块中关闭。
    """
    try:
        creds = get_credentials()
        username = creds["CARTSEE_USERNAME"]
        password = creds["CARTSEE_PASSWORD"]
    except KeyError as e:
        logger.error(f"[cartsee] 认证 ... 失败：缺失凭证键 {e}")
        return False
    logger.info(f"[cartsee] 认证 用户 {mask_credential(username)} ...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto("https://app.cartsee.com/cartsee-new/login", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # 填写账号密码（选择器基于 CartSee 登录页实际结构）
            page.fill("input[type='email'], input[name='email'], input[placeholder*='email' i]", username)
            page.fill("input[type='password'], input[name='password']", password)
            page.click("button[type='submit'], button:has-text('Login'), button:has-text('Sign in')")
            page.wait_for_load_state("networkidle", timeout=15000)

            # 判断登录成功：不再停留在登录页
            if "/cartsee-new/login" not in page.url.lower():
                logger.info("[cartsee] 认证 ... 成功")
                return True
            else:
                logger.error("[cartsee] 认证 ... 失败：登录后仍在登录页，请检查账号密码")
                return False
        except Exception as e:
            logger.error(f"[cartsee] 认证 ... 失败：{e}")
            return False
        finally:
            browser.close()


def fetch_sample(table_name: str = None) -> list[dict]:
    """登录 CartSee 后台并抓取至少 1 条 EDM 数据记录。
    遇到验证码时 raise RuntimeError，浏览器在 finally 块中关闭。
    table_name 参数忽略（非 SQL 数据源）。
    """
    try:
        creds = get_credentials()
        username = creds["CARTSEE_USERNAME"]
        password = creds["CARTSEE_PASSWORD"]
    except KeyError as e:
        raise RuntimeError(f"[cartsee] fetch_sample 失败：缺失凭证键 {e}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            # 登录
            page.goto("https://app.cartsee.com/cartsee-new/login", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)

            page.fill("input[type='email'], input[name='email'], input[placeholder*='email' i]", username)
            page.fill("input[type='password'], input[name='password']", password)
            page.click("button[type='submit'], button:has-text('Login'), button:has-text('Sign in')")
            page.wait_for_load_state("networkidle", timeout=15000)

            # 验证码检测
            if "captcha" in page.url.lower() or page.query_selector(".captcha, #captcha, [class*='captcha']"):
                raise RuntimeError("[cartsee] 遇到验证码，请手动完成验证后重新运行")
            page_content = page.content()
            if "captcha" in page_content.lower() or "验证码" in page_content:
                raise RuntimeError("[cartsee] 遇到验证码，请手动完成验证后重新运行")

            # 检查登录是否成功
            if "/cartsee-new/login" in page.url.lower():
                raise RuntimeError("[cartsee] 登录失败，请检查账号密码")

            # 导航至营销活动列表页面
            page.goto("https://app.cartsee.com/cartsee-new/campaign/list", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # 再次验证码检测
            if "captcha" in page.url.lower() or "captcha" in page.content().lower():
                raise RuntimeError("[cartsee] 遇到验证码，请手动完成验证后重新运行")

            # 等待数据表格加载
            page.wait_for_selector("table, [class*='table'], [class*='campaign'], [class*='list']", timeout=15000)

            # 抓取表格数据
            records = _extract_table_records(page)

            if not records:
                raise RuntimeError("[cartsee] 未找到任何 EDM 数据记录")

            logger.info(f"[cartsee] 抓取 {len(records)} 条 EDM 记录 ... 成功")
            return records

        except RuntimeError:
            raise
        except Exception as e:
            if "captcha" in str(e).lower() or "验证码" in str(e):
                raise RuntimeError("[cartsee] 遇到验证码，请手动完成验证后重新运行")
            raise RuntimeError(f"[cartsee] fetch_sample 异常：{e}")
        finally:
            browser.close()


def _extract_table_records(page) -> list[dict]:
    """从页面表格中提取数据记录。"""
    records = []

    # 尝试从标准 HTML table 提取
    table = page.query_selector("table")
    if table:
        headers = []
        header_cells = table.query_selector_all("thead th, thead td")
        if header_cells:
            headers = [cell.inner_text().strip() for cell in header_cells]

        rows = table.query_selector_all("tbody tr")
        for row in rows:
            cells = row.query_selector_all("td")
            if cells:
                record = {}
                for i, cell in enumerate(cells):
                    if headers and i < len(headers):
                        key = headers[i]
                    elif headers and i >= len(headers):
                        key = f"field_{i}"
                    else:
                        key = f"col_{i}"
                    record[key] = cell.inner_text().strip()
                if record:
                    records.append(record)

    # 若无标准 table，尝试抓取页面 JSON 数据
    if not records:
        records = _try_extract_json_data(page)

    return records


def _try_extract_json_data(page) -> list[dict]:
    """尝试从页面脚本/API 响应中提取 JSON 数据。"""
    try:
        # 尝试通过 JavaScript 获取页面内嵌数据
        data = page.evaluate("""
            () => {
                // 查找常见的数据存储位置
                if (window.__NUXT__ && window.__NUXT__.data) return window.__NUXT__.data;
                if (window.__INITIAL_STATE__) return window.__INITIAL_STATE__;
                if (window.__APP_STATE__) return window.__APP_STATE__;
                return null;
            }
        """)
        if data and isinstance(data, (list, dict)):
            if isinstance(data, list):
                return data[:5]  # 最多返回 5 条
            elif isinstance(data, dict):
                return [data]
    except Exception:
        pass
    return []


def _infer_type(value) -> str:
    """从单个值推断数据类型字符串。"""
    if isinstance(value, bool):
        return "boolean"
    elif isinstance(value, (int, float)):
        return "number"
    elif isinstance(value, list):
        return "array"
    elif isinstance(value, dict):
        return "object"
    elif value is None:
        return "null"
    else:
        return "string"


def extract_fields(sample: list[dict]) -> list[dict]:
    """从样本数据中提取字段信息，返回标准 FieldInfo 列表。"""
    if not sample:
        return []

    # 合并所有记录的键，保留首次出现的顺序
    all_keys: list[str] = []
    seen: set[str] = set()
    for record in sample:
        for key in record:
            if key not in seen:
                all_keys.append(key)
                seen.add(key)

    fields: list[dict] = []
    for key in all_keys:
        # 从首条非 None 值推断类型
        non_none_value = next(
            (record[key] for record in sample if key in record and record[key] is not None),
            None,
        )
        data_type = _infer_type(non_none_value)

        # 取第一条含该键的记录的值作为示例
        sample_value = next(
            (record[key] for record in sample if key in record),
            None,
        )
        nullable = any(record.get(key) is None for record in sample)

        fields.append({
            "field_name": key,
            "data_type": data_type,
            "sample_value": sample_value,
            "nullable": nullable,
        })

    return fields
