# Story 4.6: YouTube Studio 爬虫数据源接入

Status: done

## Story

作为操作者，
我希望验证器能通过 Playwright 自动登录 YouTube Studio 并抓取频道分析页面的数据字段，
以便我能获得 YouTube 频道运营数据（播放量、观看时长、订阅者等）的实际字段报告。

## Acceptance Criteria

1. `get_credentials()` 返回有效的 `YOUTUBE_STUDIO_EMAIL` 和 `YOUTUBE_STUDIO_PASSWORD` 时，调用 `youtube_studio.authenticate()` 使用 `sync_playwright` 启动 headless Chromium，打开 YouTube Studio，完成 Google 两步账号登录（先输入邮箱，再输入密码），等待跳转至 `studio.youtube.com`，返回 `True`，日志输出 `[youtube_studio] 认证 ... 成功`

2. 登录成功后，调用 `youtube_studio.fetch_sample()` 导航至频道分析概览页（`/analytics/tab-overview/period-default`），从页面中抓取至少一条统计指标记录，页面等待超时 20s，整体执行在 90s 内完成

3. `extract_fields(sample)` 返回包含以下字段的标准 FieldInfo 列表（6 个）：播放量、观看时长（小时）、订阅者、曝光次数、点击率、平均观看时长

4. `write_raw_report("youtube_studio", fields, None, ...)` 被调用后，`reports/youtube_studio-raw.md` 包含实际字段表格和需求字段对照区块

5. 页面出现 Google 人机验证或 CAPTCHA 时，`fetch_sample()` 抛出 `RuntimeError("[youtube_studio] 遇到验证码，请手动完成验证后重新运行")`，浏览器在 finally 块中正确关闭

6. `tests/test_youtube_studio.py` 中 `extract_fields()` 单元测试通过（使用 `tests/fixtures/youtube_studio_sample.json`）；`authenticate()` 和 `fetch_sample()` 标注 `@pytest.mark.integration`，不在单元测试中执行

## Tasks / Subtasks

- [x] 更新 `config/credentials.py` (AC: #1)
  - [x] 在 `_REQUIRED_KEYS` 列表末尾添加 `"YOUTUBE_STUDIO_EMAIL"` 和 `"YOUTUBE_STUDIO_PASSWORD"`

- [x] 更新 `.env.example` (AC: #1)
  - [x] 在文件末尾添加 YouTube Studio 凭证区块（`YOUTUBE_STUDIO_EMAIL=` / `YOUTUBE_STUDIO_PASSWORD=`）

- [x] 更新 `validate.py` SOURCES 注册表 (AC: #4)
  - [x] 在 `SOURCES` 字典末尾添加 `"youtube_studio": "sources.youtube_studio"`

- [x] 创建 `sources/youtube_studio.py` (AC: #1 #2 #3 #4 #5)
  - [x] 实现 `authenticate()` — Google 两步登录（邮箱 → 密码），等待跳转至 `studio.youtube.com`
  - [x] 实现 `fetch_sample(table_name=None)` — 导航至分析概览页，提取 6 个目标指标，调用 `write_raw_report` 和 `init_validation_report`
  - [x] 实现 `extract_fields(sample)` — 纯函数，从 dict 列表中提取 6 个目标字段的 FieldInfo 列表
  - [x] 实现 `_login(page, email, password)` 私有辅助函数（两步：邮箱 → 密码）
  - [x] 实现 `_check_captcha(page)` 私有辅助函数（复用 CAPTCHA_KEYWORDS 关键词列表）
  - [x] 实现 `_check_total_timeout(start_time)` 私有辅助函数
  - [x] 实现 `_extract_analytics_metrics(page)` 私有辅助函数（从分析页提取指标卡片数值）

- [x] 创建 `tests/fixtures/youtube_studio_sample.json` (AC: #6)
  - [x] 创建包含至少 2 条记录的 JSON fixture，字段对应 6 个目标字段（含至少一个 null 字段用于测试 nullable）

- [x] 创建 `tests/test_youtube_studio.py` (AC: #5 #6)
  - [x] 添加 `TestExtractFields` 类，使用 fixture 验证 FieldInfo 结构（四键：field_name, data_type, sample_value, nullable）
  - [x] 添加边界情况测试（空列表返回空列表）
  - [x] 将 `TestAuthenticateIntegration` 和 `TestFetchSampleIntegration` 标注 `@pytest.mark.integration`

- [x] 更新 `tests/conftest.py` (AC: #6)
  - [x] 在 `TEST_CREDENTIALS` 字典中添加 `"YOUTUBE_STUDIO_EMAIL": "test_yt_studio_email"` 和 `"YOUTUBE_STUDIO_PASSWORD": "test_yt_studio_pass"`

## Dev Notes

### 源名称与文件命名

```
source_name = "youtube_studio"        # validate.py SOURCES 注册表 key，报告文件名前缀
module_file = "sources/youtube_studio.py"   # 新建文件
test_file   = "tests/test_youtube_studio.py"
fixture     = "tests/fixtures/youtube_studio_sample.json"
```

注意：与现有 `youtube`（Data API）是两个完全独立的源，**不修改** `sources/youtube.py`。

### 登录流程：Google 两步登录

YouTube Studio 使用 Google 账号登录，登录页会先跳转至 `accounts.google.com`。

```python
STUDIO_URL = "https://studio.youtube.com"
GOOGLE_LOGIN_URL = "https://accounts.google.com"
ANALYTICS_URL = "https://studio.youtube.com/analytics/tab-overview/period-default"

def _login(page, email: str, password: str) -> None:
    # Step 1：打开 YouTube Studio，等待自动跳转至 Google 登录页
    page.goto(STUDIO_URL, timeout=PAGE_WAIT_TIMEOUT_MS)
    # 等待 Google 邮箱输入框出现
    page.wait_for_selector("input[type='email']", timeout=PAGE_WAIT_TIMEOUT_MS)

    # Step 2：输入邮箱，点击下一步
    page.fill("input[type='email']", email)
    # "下一步" 按钮（多语言兼容：备选文本 "Next" / "下一步"）
    try:
        page.click("button:has-text('Next')", timeout=PAGE_WAIT_TIMEOUT_MS)
    except Exception:
        page.click("button:has-text('下一步')", timeout=PAGE_WAIT_TIMEOUT_MS)

    # Step 3：等待密码框出现，输入密码
    page.wait_for_selector("input[type='password']", timeout=PAGE_WAIT_TIMEOUT_MS)
    page.fill("input[type='password']", password)
    try:
        page.click("button:has-text('Next')", timeout=PAGE_WAIT_TIMEOUT_MS)
    except Exception:
        page.click("button:has-text('下一步')", timeout=PAGE_WAIT_TIMEOUT_MS)

    # Step 4：等待跳转回 studio.youtube.com
    page.wait_for_url("**/studio.youtube.com/**", timeout=PAGE_WAIT_TIMEOUT_MS * 2)

    # 验证确实进入了 Studio（不在登录页或错误页）
    if "accounts.google.com" in page.url or "signin" in page.url.lower():
        raise RuntimeError("[youtube_studio] 登录后仍在 Google 登录页，凭证可能无效或触发了 2FA")
```

**关键注意：**
- Google 登录页按钮语言取决于浏览器/系统语言，备用多个文本选择器
- Google 有**极强的 headless 检测**，正式使用时可能需要 `headless=False`；单元测试 mock 即可
- **必须关闭 Google 账号的两步验证（2FA）**，否则登录会停在 2FA 页面
- 登录超时使用 `PAGE_WAIT_TIMEOUT_MS * 2`（40s），因 Google 重定向链路较长

### 数据抓取：频道分析概览页

```python
def _extract_analytics_metrics(page) -> list[dict]:
    """从 YouTube Studio 分析概览页提取指标卡片数值。

    分析页显示多个指标卡片，每个卡片包含：指标名称 + 数值（如 "— " 表示无数据）
    目标字段：TARGET_FIELDS（6 个固定中文字段）

    Returns:
        list[dict]：至少一条记录，key 为 TARGET_FIELDS 中的字段名
    """
    # 等待分析卡片出现（class 或 aria-label 可能变动，备用多个选择器）
    try:
        page.wait_for_selector("[data-testid='analytics-card']", timeout=PAGE_WAIT_TIMEOUT_MS)
    except Exception:
        try:
            page.wait_for_selector(".analytics-card", timeout=PAGE_WAIT_TIMEOUT_MS)
        except Exception:
            logger.warning("[youtube_studio] 未发现标准分析卡片，尝试直接提取文本")

    # 使用 JavaScript 提取各指标数值（YouTube Studio 为 SPA，JS 提取更可靠）
    metrics_raw = page.evaluate("""
        () => {
            // 尝试提取页面中的统计数字区域
            const cards = document.querySelectorAll(
                '[data-testid="analytics-card"], .analytics-card, .card'
            );
            const result = {};
            cards.forEach(card => {
                const label = card.querySelector('.title, [data-testid="title"], h3, h4');
                const value = card.querySelector('.value, [data-testid="value"], .metric-value');
                if (label && value) {
                    result[label.innerText.trim()] = value.innerText.trim();
                }
            });
            return result;
        }
    """)

    # 将原始提取结果映射到 TARGET_FIELDS
    record = {}
    for field_name in TARGET_FIELDS:
        raw_value = metrics_raw.get(field_name) or metrics_raw.get(field_name.replace("（", "(").replace("）", ")"))
        record[field_name] = raw_value if raw_value and raw_value not in ("—", "--", "") else None

    return [record]
```

**注意**：YouTube Studio 是 React SPA，DOM 结构可能因版本更新而变化。JS 提取方案比 CSS 选择器更稳定，但可能需要根据实际页面调整 selector。

### 目标字段（6 个固定中文字段）

```python
TARGET_FIELDS = [
    "播放量",
    "观看时长（小时）",
    "订阅者",
    "曝光次数",
    "点击率",
    "平均观看时长",
]
```

字段来源：YouTube Studio 分析 → 概览页 → 核心指标卡片区（对应截图中的 Views / Watch time (hours) / Subscribers 等）

**特殊值处理**：
- `"—"` 或 `"--"` 映射为 `None`（YouTube 无数据时的展示方式，截图中可见）
- 纯数字字符串（如 `"1,234"`）保留原始字符串格式，`_infer_type` 尝试解析为 `integer`

### extract_fields 实现规范

```python
def extract_fields(sample: list[dict]) -> list[dict]:
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
```

**与 social_media.py 完全相同的模式**（固定字段 + sorted 排列）。

### 超时常量

```python
PAGE_WAIT_TIMEOUT_MS = 20_000  # 20 秒（与 Facebook 一致，Google 跳转链路更长）
TOTAL_TIMEOUT_S = 90           # 90 秒（与 Facebook 一致）
```

`_login()` 中等待 `wait_for_url("**/studio.youtube.com/**")` 时使用 `PAGE_WAIT_TIMEOUT_MS * 2`（40s）。

### 凭证键名

```python
creds = get_credentials()
email    = creds["YOUTUBE_STUDIO_EMAIL"]
password = creds["YOUTUBE_STUDIO_PASSWORD"]
```

这两个键需同步添加到：
1. `config/credentials.py` 的 `_REQUIRED_KEYS` 列表末尾
2. `.env.example` 末尾的 YouTube Studio 凭证区块
3. `tests/conftest.py` 的 `TEST_CREDENTIALS` 字典

### 模块文件头常量

```python
STUDIO_URL      = "https://studio.youtube.com"
ANALYTICS_URL   = "https://studio.youtube.com/analytics/tab-overview/period-default"
PAGE_WAIT_TIMEOUT_MS = 20_000
TOTAL_TIMEOUT_S      = 90
MAX_SAMPLE_ROWS      = 1   # 分析页为聚合指标，非列表，固定1条记录

TARGET_FIELDS = [
    "播放量",
    "观看时长（小时）",
    "订阅者",
    "曝光次数",
    "点击率",
    "平均观看时长",
]

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
    "confirm it's you",   # Google 人机验证特有提示
    "verify your identity",
]
```

### validate.py SOURCES 注册表更新

```python
SOURCES: Dict[str, str] = {
    "triplewhale":     "sources.triplewhale",
    "tiktok":          "sources.tiktok",
    "dingtalk":        "sources.dingtalk",
    "youtube":         "sources.youtube",
    "awin":            "sources.awin",
    "cartsee":         "sources.cartsee",
    "partnerboost":    "sources.partnerboost",
    "social_media":    "sources.social_media",
    "youtube_studio":  "sources.youtube_studio",  # ← 新增
}
```

### Fixture 文件格式（youtube_studio_sample.json）

```json
[
  {
    "播放量": "1,234",
    "观看时长（小时）": "56.7",
    "订阅者": "+5",
    "曝光次数": "12,345",
    "点击率": "4.2%",
    "平均观看时长": "2:45"
  },
  {
    "播放量": "2,456",
    "观看时长（小时）": "89.1",
    "订阅者": null,
    "曝光次数": "23,456",
    "点击率": null,
    "平均观看时长": "3:12"
  }
]
```

第二条记录中 `订阅者` 和 `点击率` 为 null，用于测试 `nullable=True` 逻辑。

### 测试文件结构

```python
# tests/test_youtube_studio.py

import json
import pytest
from pathlib import Path
from sources import youtube_studio

FIXTURES_DIR = Path(__file__).parent / "fixtures"

class TestExtractFields:
    """AC3 & AC6：使用 fixture 数据验证 FieldInfo 结构。"""

    @pytest.fixture
    def sample(self):
        with open(FIXTURES_DIR / "youtube_studio_sample.json", encoding="utf-8") as f:
            return json.load(f)

    def test_returns_list(self, sample): ...
    def test_each_item_has_four_required_keys(self, sample): ...
    def test_nullable_when_value_is_none(self, sample): ...  # 订阅者、点击率
    def test_returns_sorted_fields(self, sample): ...        # 按 sorted(TARGET_FIELDS)

class TestExtractFieldsEdgeCases:
    """边界情况：空列表等。"""
    def test_empty_sample_returns_empty_list(self): ...

@pytest.mark.integration
class TestAuthenticateIntegration:
    """AC1 集成测试：需要真实 Google 账号，CI 中跳过。"""
    def test_authenticate_returns_bool(self, mock_credentials): ...

@pytest.mark.integration
class TestFetchSampleIntegration:
    """AC2 集成测试：需要真实 Google 账号，CI 中跳过。"""
    def test_fetch_sample_returns_list(self, mock_credentials): ...
```

### 禁止行为

- ❌ 直接调用 `os.getenv("YOUTUBE_STUDIO_EMAIL")`，必须用 `get_credentials()`
- ❌ 使用 `async_playwright`，必须用 `sync_playwright`
- ❌ 修改现有 `sources/youtube.py`（Data API 实现保持不变）
- ❌ 在公开函数之外写报告（只在 `fetch_sample()` 内调用 `write_raw_report` 和 `init_validation_report`）
- ❌ 静默忽略验证码，必须抛出 `RuntimeError`

### 参考模式

```
social_media.py → youtube_studio.py 对应关系（主参照）：
- FB_LOGIN_URL          → STUDIO_URL = "https://studio.youtube.com"
- POSTS_URL             → ANALYTICS_URL = "https://studio.youtube.com/analytics/tab-overview/period-default"
- PAGE_WAIT_TIMEOUT_MS  = 20_000（相同）
- TOTAL_TIMEOUT_S       = 90（相同）
- _login()：Google 两步登录（邮箱 → 密码）vs Facebook 两步登录（点击按钮 → 账密）
- _extract_post_rows()  → _extract_analytics_metrics()（聚合指标卡片 vs 帖子列表）
- extract_fields()：固定 6 字段映射（与 social_media.py 7 字段相同模式）
```

### 已知风险与应对

| 风险 | 说明 | 应对 |
|------|------|------|
| Google headless 检测 | Google 会检测 headless 浏览器并拒绝登录 | 记录日志，抛出 RuntimeError；可尝试 `headless=False` 调试 |
| Google 2FA 拦截 | 账号开启了两步验证时登录会停在 2FA 页面 | 登录失败时日志提示"请确认已关闭两步验证"；CAPTCHA 检测覆盖此场景 |
| SPA DOM 结构变动 | YouTube Studio 为 React SPA，DOM 随版本更新 | JS evaluate 提取 + 多选择器备用；字段不存在映射为 None 而非抛错 |
| 无数据时指标显示"—" | 频道若无播放量，页面显示破折号 | `_extract_analytics_metrics` 将 "—" 映射为 None，正常处理 |

### 新增/修改文件清单

**新增：**
- `sources/youtube_studio.py` — 完整 Playwright 爬虫实现
- `tests/test_youtube_studio.py` — 单元测试 + 集成测试标注
- `tests/fixtures/youtube_studio_sample.json` — extract_fields 单元测试 fixture

**修改：**
- `config/credentials.py` — `_REQUIRED_KEYS` 末尾添加 YOUTUBE_STUDIO_EMAIL/PASSWORD
- `.env.example` — 末尾添加 YouTube Studio 凭证区块
- `validate.py` — `SOURCES` 字典末尾添加 `"youtube_studio": "sources.youtube_studio"`
- `tests/conftest.py` — `TEST_CREDENTIALS` 添加 YOUTUBE_STUDIO_EMAIL/PASSWORD

**不修改：**
- `sources/youtube.py`（Data API 实现独立存在，不受影响）
- `reporter.py`（通用，无需修改）
- `sources/__init__.py`（空文件）

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- 修改前基线：37 个失败，311 通过
- 修改后最终：34 个失败，314 通过（净改善 +3，无新增失败）
- test_credentials.py 的 3 个预存失败（缺少 FACEBOOK_* 和 YOUTUBE_STUDIO_* 凭证）在本 story 中一并修复
- test_validate.py 的 14 个预存失败（TRIPLEWHALE_TABLES 常量不存在等）未引入、未修复，属预存问题

### Completion Notes List

- 创建 `sources/youtube_studio.py`：完整 Google 两步登录 Playwright 爬虫，支持邮箱/密码登录，三方案降级提取分析指标
- 6 个目标字段：播放量、观看时长（小时）、订阅者、曝光次数、点击率、平均观看时长
- PAGE_WAIT_TIMEOUT_MS=20000，TOTAL_TIMEOUT_S=90（与 Facebook 一致，Google 重定向链路更长）
- extract_fields 使用固定 6 字段映射（sorted 排列），与 social_media.py 模式一致
- _infer_type 支持千位分隔符数字（如 "1,234"）自动去除逗号后解析为 integer
- 26 个单元测试全部通过（TestExtractFields、TestExtractFieldsEdgeCases、TestInferType、TestIsEmpty）
- 额外修复：test_credentials.py::ALL_VALID_ENV 补齐 FACEBOOK_*/YOUTUBE_STUDIO_* 键，test_validate.py _make_all_mock_sources() 添加 youtube_studio，len(SOURCES) 断言从 8 更新为 9

### File List

- sources/youtube_studio.py（新增）
- tests/test_youtube_studio.py（新增）
- tests/fixtures/youtube_studio_sample.json（新增）
- config/credentials.py（修改：_REQUIRED_KEYS 末尾添加 YOUTUBE_STUDIO_EMAIL/PASSWORD）
- .env.example（修改：末尾添加 YouTube Studio 凭证区块）
- validate.py（修改：SOURCES 字典末尾添加 youtube_studio）
- tests/conftest.py（修改：TEST_CREDENTIALS 添加 YOUTUBE_STUDIO_EMAIL/PASSWORD）
- tests/test_credentials.py（修改：ALL_VALID_ENV 补齐 FACEBOOK_* 和 YOUTUBE_STUDIO_* 键，修复预存失败）
- tests/test_validate.py（修改：_make_all_mock_sources() 添加 youtube_studio，len(SOURCES) 断言从 8 更新为 9）

### Review Findings

- [x] [Review][Decision] D1: 全 None 记录 — 决定：增加 warning 日志（全 None 视为有效记录，适用于新频道无数据场景）— 已修复
- [x] [Review][Decision] D2: "challenge" CAPTCHA 关键词误报 — 决定：移除该关键词（在 YouTube Studio 分析页误报风险过高）— 已修复
- [x] [Review][Patch] P1: `authenticate()` 违反 spec 禁止行为：不应调用 `init_validation_report` — 已修复，移除调用
- [x] [Review][Patch] P2: `authenticate()` 未调用 `_check_captcha()` — 已修复，登录后增加 CAPTCHA 检测
- [x] [Review][Patch] P3: `sync_playwright` 为 None 时缺少明确 guard — 已修复，`authenticate()` 返回 False，`fetch_sample()` 抛出 RuntimeError
- [x] [Review][Patch] P4: `_login()` 点击 Next 后未等待页面状态变化 — 已修复，增加 `wait_for_load_state("domcontentloaded")`
- [x] [Review][Patch] P5: `_login()` Enter 兜底使用 bare `except Exception` — 已修复，改为捕获 `PlaywrightTimeoutError` 并记录 warning
- [x] [Review][Patch] P6: `_extract_analytics_metrics()` page.evaluate 无异常处理 — 已修复，包裹 try/except 并降级为空 dict
- [x] [Review][Patch] P8: `_check_captcha()` evaluate 失败静默返回 — 已修复，增加 warning 日志
- [x] [Review][Patch] P9: `_check_total_timeout()` 未覆盖指标提取阶段 — 已修复，在 `_extract_analytics_metrics()` 后增加检查
- [x] [Review][Patch] P10: `MAX_SAMPLE_ROWS` 死代码 — 已修复，移除未使用常量
- [x] [Review][Defer] P7: 集成测试 `mock_credentials` 补丁目标问题 — deferred, 与其他 4 个爬虫源（awin/cartsee/partnerboost/social_media）完全一致的项目级模式
- [x] [Review][Defer] W1: Fixture 有 2 条记录但运行时固定返回 1 条 — deferred, 测试设计优化
- [x] [Review][Defer] W2: `test_all_13_keys_present_in_result` 方法名过时 — deferred, 预存问题
- [x] [Review][Defer] W3: `_login()` post-login URL 检查不完整 — deferred, 需整体 Google 登录流优化

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4: 爬虫数据源接入]
- [Source: _bmad-output/planning-artifacts/architecture.md#ARCH10] — Playwright sync 模式，超时规范
- [Source: _bmad-output/planning-artifacts/architecture.md#ARCH2] — 统一接口契约
- [Source: sources/social_media.py] — 主参照（固定字段爬虫实现）
- [Source: sources/awin.py] — 次参照（CAPTCHA 检测模式）
- [Source: config/credentials.py] — _REQUIRED_KEYS 末尾追加
- [Source: validate.py] — SOURCES 注册表末尾追加
