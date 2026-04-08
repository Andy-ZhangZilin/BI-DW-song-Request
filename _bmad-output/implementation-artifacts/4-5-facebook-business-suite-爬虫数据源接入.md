# Story 4.5: Facebook Business Suite 爬虫数据源接入

Status: done

## Story

作为操作者，
我希望验证器能通过 Playwright 自动登录 Meta Business Suite 并抓取帖子和 Reels 列表数据字段，
以便我能获得 Facebook 社媒内容数据的实际字段报告。

## Acceptance Criteria

1. `get_credentials()` 返回有效的 `FACEBOOK_USERNAME` 和 `FACEBOOK_PASSWORD` 时，调用 `social_media.authenticate()` 使用 `sync_playwright` 启动 headless Chromium，打开 `https://business.facebook.com/business/loginpage`，点击"使用 Facebook 登录"按钮，完成账号密码登录，返回 `True`，日志输出 `[social_media] 认证 ... 成功`
2. 登录成功后，调用 `social_media.fetch_sample()` 导航至帖子和 Reels 页面（`/latest/posts/published_posts`），抓取列表中至少一条记录，页面等待超时 20s，整体执行在 90s 内完成
3. `extract_fields(sample)` 返回包含以下字段的标准 FieldInfo 列表：标题、发布日期、状态、覆盖人数、获赞数和心情数、评论数、分享次数
4. `write_raw_report("social_media", fields, ...)` 被调用后，`reports/social_media-raw.md` 包含实际字段表格和需求字段对照区块
5. 页面出现验证码或人机验证时，`fetch_sample()` 抛出 `RuntimeError("[social_media] 遇到验证码，请手动完成验证后重新运行")`，浏览器在 finally 块中正确关闭
6. `tests/test_social_media.py` 中 `extract_fields()` 单元测试通过（使用 `tests/fixtures/social_media_sample.json`）；`authenticate()` 和 `fetch_sample()` 标注 `@pytest.mark.integration`，不在单元测试中执行

## Tasks / Subtasks

- [x] 更新 `config/credentials.py` (AC: #1)
  - [x] 在 `_REQUIRED_KEYS` 列表中添加 `"FACEBOOK_USERNAME"` 和 `"FACEBOOK_PASSWORD"`
- [x] 更新 `.env.example` (AC: #1)
  - [x] 在文件末尾添加 Facebook 凭证区块（`FACEBOOK_USERNAME=` / `FACEBOOK_PASSWORD=`）
- [x] 实现 `sources/social_media.py` (AC: #1 #2 #3 #4 #5)
  - [x] 移除 stub 内容，重写为完整 Playwright 爬虫实现
  - [x] 实现 `authenticate()` — 两步登录（点击按钮 → 填入账号密码），等待跳转至 `business.facebook.com/latest`
  - [x] 实现 `fetch_sample()` — 导航至 `/latest/posts/published_posts`，抓取至少一条记录，调用 `write_raw_report` 和 `init_validation_report`
  - [x] 实现 `extract_fields(sample)` — 纯函数，从 dict 列表中提取 7 个目标字段的 FieldInfo 列表
  - [x] 实现 `_login(page, username, password)` 私有辅助函数
  - [x] 实现 `_check_captcha(page)` 私有辅助函数
  - [x] 实现 `_check_total_timeout(start_time)` 私有辅助函数
  - [x] 实现 `_extract_post_rows(page)` 私有辅助函数
  - [x] 复用 `_is_empty()` 和 `_infer_type()` 逻辑（参照 awin.py）
- [x] 创建 `tests/fixtures/social_media_sample.json` (AC: #6)
  - [x] 创建包含至少 2 条记录的 JSON fixture，字段对应 7 个目标字段
- [x] 更新 `tests/test_social_media.py` (AC: #6)
  - [x] 删除 stub 测试（原 NotImplementedError 测试）
  - [x] 添加 `TestExtractFields` 类，使用 fixture 验证 FieldInfo 结构
  - [x] 添加边界情况测试（空列表、全 None 等）
  - [x] 将 `TestAuthenticateIntegration` 和 `TestFetchSampleIntegration` 标注 `@pytest.mark.integration`

### Review Findings (AI) — 2026-04-08

- [x] [Review][Patch] `_login()` 缺少登录后 URL 验证 [sources/social_media.py `_login()`] — 已修复：`wait_for_url` 后添加 `if "login" in page.url.lower(): raise RuntimeError(...)` 检查
- [x] [Review][Patch] `_extract_post_rows()` 表头空字符串误入 table 分支 [sources/social_media.py `_extract_post_rows()`] — 已修复：`if raw_headers:` 改为 `if any(h.strip() for h in raw_headers):`
- [x] [Review][Defer] FACEBOOK 凭证强制全局注册 [config/credentials.py] — deferred, pre-existing（与其他 11 个数据源凭证的注册方式一致，项目设计如此）
- [x] [Review][Defer] `sync_playwright` None 检查缺失（Playwright 未安装时） [sources/social_media.py] — deferred, pre-existing（与 awin.py/cartsee.py 等相同模式）
- [x] [Review][Defer] `PlaywrightTimeoutError = Exception` fallback 导致异常过度捕获 [sources/social_media.py] — deferred, pre-existing（与 awin.py 相同模式）
- [x] [Review][Defer] CAPTCHA 检测误报（帖子正文含关键词触发误检） [sources/social_media.py `_check_captcha()`] — deferred, pre-existing（与 awin.py 相同 innerText 检测方案）
- [x] [Review][Defer] 90s 总超时未覆盖 `_extract_post_rows` 内部等待 [sources/social_media.py] — deferred, pre-existing（与 awin.py 两点检测设计一致）
- [x] [Review][Defer] 空样本不抛异常，仅 warning [sources/social_media.py `fetch_sample()`] — deferred, pre-existing（与 awin.py 相同）
- [x] [Review][Defer] `authenticate()` 和 `fetch_sample()` 各自独立登录，无会话复用 [sources/social_media.py] — deferred, pre-existing（与 awin.py/cartsee.py 设计一致）
- [x] [Review][Defer] ARIA 分支按位置映射字段，列序错误时静默产生错误数据 [sources/social_media.py `_extract_post_rows()`] — deferred（动态 SPA 页面结构未知，fallback 设计限制）

## Dev Notes

### 核心实现：登录流程（两步）

Facebook Business Suite 登录与其他爬虫不同，分两步：

```python
def _login(page, username: str, password: str) -> None:
    # 步骤 1：打开登录入口，点击 FB 登录按钮（跳转至 Facebook 账号登录页）
    page.goto("https://business.facebook.com/business/loginpage", timeout=PAGE_WAIT_TIMEOUT_MS)
    page.click("text=使用 Facebook 登录", timeout=PAGE_WAIT_TIMEOUT_MS)  # 或 button[data-testid*='login']

    # 步骤 2：填入账号密码（Facebook 标准登录页）
    page.wait_for_selector("input[name='email']", timeout=PAGE_WAIT_TIMEOUT_MS)
    page.fill("input[name='email']", username)
    page.fill("input[name='pass']", password)
    page.click("button[name='login']")

    # 等待跳转回 Business Suite（成功标志：URL 包含 business.facebook.com/latest）
    page.wait_for_url("**/latest/**", timeout=PAGE_WAIT_TIMEOUT_MS)
```

**注意：** "使用 Facebook 登录"按钮的选择器需根据实际 DOM 调整。备选方案：
- `page.get_by_text("使用 Facebook 登录")`
- `page.get_by_role("button", name="使用 Facebook 登录")`
- CSS selector 如 `a[data-testid='royal_login_button']` 或类似属性

### 核心实现：数据抓取页面

```python
# 导航至帖子和 Reels 页面
page.goto(POSTS_URL, timeout=PAGE_WAIT_TIMEOUT_MS)
page.wait_for_load_state("networkidle", timeout=PAGE_WAIT_TIMEOUT_MS)
```

`POSTS_URL` 形如：
`https://business.facebook.com/latest/posts/published_posts`

页面加载后可能有动态内容渲染（React/Vue），需等待列表元素出现。

### extract_fields 实现规范

`extract_fields()` 是纯函数（无 IO），只从 `sample` 字典中提取/映射 7 个目标字段。与其他爬虫模块不同，Facebook 的字段名是**固定的中文预定义字段**，不做动态发现：

```python
# 目标字段清单（7 个）
TARGET_FIELDS = [
    "标题",
    "发布日期",
    "状态",
    "覆盖人数",
    "获赞数和心情数",
    "评论数",
    "分享次数",
]

def extract_fields(sample: list[dict]) -> list[dict]:
    if not sample:
        return []
    fields = []
    for field_name in sorted(TARGET_FIELDS):  # 按字母顺序，与 awin.py 一致
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

### 超时常量（与 awin.py 不同）

```python
# Story 4.5 AC 明确指定的超时值（比其他爬虫更长）
PAGE_WAIT_TIMEOUT_MS = 20_000  # 20 秒（awin 是 15s）
TOTAL_TIMEOUT_S = 90           # 90 秒（awin/cartsee 是 60s）
```

### 凭证键名

```python
# authenticate() 中
creds = get_credentials()
username = creds["FACEBOOK_USERNAME"]
password = creds["FACEBOOK_PASSWORD"]
```

这两个键需同步添加到：
1. `config/credentials.py` 的 `_REQUIRED_KEYS` 列表
2. `.env.example` 的末尾

### 验证码检测（复用 awin.py 关键词列表）

```python
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
```

### 模块文件头常量

```python
FB_LOGIN_URL = "https://business.facebook.com/business/loginpage"
POSTS_URL = "https://business.facebook.com/latest/posts/published_posts"
PAGE_WAIT_TIMEOUT_MS = 20_000
TOTAL_TIMEOUT_S = 90
MAX_SAMPLE_ROWS = 20
```

### 禁止行为

- ❌ 直接调用 `os.getenv("FACEBOOK_USERNAME")`，必须用 `get_credentials()`
- ❌ 使用 `async_playwright`，必须用 `sync_playwright`
- ❌ 在公开函数之外写报告（只在 `fetch_sample()` 内调用 `write_raw_report` 和 `init_validation_report`）
- ❌ 静默忽略验证码，必须抛出 `RuntimeError`

### Fixture 文件格式（social_media_sample.json）

```json
[
  {
    "标题": "Piscifun 新品发布：XYZ 钓竿上线",
    "发布日期": "4月7日 21:30",
    "状态": "已发布",
    "覆盖人数": "1,234",
    "获赞数和心情数": "89",
    "评论数": "12",
    "分享次数": "5"
  },
  {
    "标题": "春季促销活动开始",
    "发布日期": "4月6日 10:00",
    "状态": "已发布",
    "覆盖人数": "2,456",
    "获赞数和心情数": null,
    "评论数": "34",
    "分享次数": "18"
  }
]
```

第二条记录中 `获赞数和心情数` 为 null，用于测试 `nullable=True` 逻辑。

### 测试文件结构

```python
# tests/test_social_media.py 新结构

class TestExtractFields:
    """AC3 & AC6：使用 fixture 数据验证 FieldInfo 结构。"""
    @pytest.fixture
    def sample(self):
        with open(FIXTURES_DIR / "social_media_sample.json", encoding="utf-8") as f:
            return json.load(f)
    # test_returns_list, test_each_item_has_four_required_keys, ...
    # test_nullable_when_value_is_none (获赞数和心情数)
    # test_returns_sorted_fields (TARGET_FIELDS 按 sorted 排列)

class TestExtractFieldsEdgeCases:
    """边界情况：空列表等。"""
    def test_empty_sample_returns_empty_list(self): ...

@pytest.mark.integration
class TestAuthenticateIntegration:
    """AC1 集成测试：需要真实 Facebook 账号，CI 中跳过。"""
    def test_authenticate_returns_bool(self, mock_credentials): ...

@pytest.mark.integration
class TestFetchSampleIntegration:
    """AC2 集成测试：需要真实 Facebook 账号，CI 中跳过。"""
    def test_fetch_sample_returns_list(self, mock_credentials): ...
```

### Project Structure Notes

**新增/修改文件：**
- `sources/social_media.py`（修改：替换 stub 实现为完整爬虫）
- `tests/test_social_media.py`（修改：替换 stub 测试为 extract_fields 单元测试 + 集成测试）
- `tests/fixtures/social_media_sample.json`（新增：extract_fields 单元测试 fixture）
- `config/credentials.py`（修改：`_REQUIRED_KEYS` 添加 FACEBOOK_USERNAME/PASSWORD）
- `.env.example`（修改：添加 Facebook 凭证区块）

**不修改的文件：**
- `validate.py`：`SOURCES` 注册表已含 `"social_media": "sources.social_media"`，无需改动
- `reporter.py`：通用，无需修改
- `sources/__init__.py`：空文件，无需修改

**重要：** `validate.py` 的 `_run_source` 默认分支（`else`）已处理 `social_media`，调用 `module.fetch_sample()`（无 table_name），然后 `write_raw_report(source_name, fields, None, len(sample))`。Story 4.5 实现不需要修改 validate.py。

### 参考模式（awin.py 是主参照）

```
awin.py → social_media.py 对应关系：
- AWIN_LOGIN_URL      → FB_LOGIN_URL = "https://business.facebook.com/business/loginpage"
- AWIN_REPORT_URL     → POSTS_URL = "https://business.facebook.com/latest/posts/published_posts"
- PAGE_WAIT_TIMEOUT_MS = 15_000 → 20_000（Story 4.5 AC 指定）
- TOTAL_TIMEOUT_S = 60 → 90（Story 4.5 AC 指定）
- _login()：两步登录（awin 是单步）
- _extract_table_rows() → _extract_post_rows()（DOM 结构不同）
- extract_fields()：固定 7 字段映射（非动态列名）
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.5: Facebook Business Suite 爬虫数据源接入]
- [Source: _bmad-output/docs/datasource-api-research-report.md#8.1 Facebook Business Suite（Playwright 爬虫）]
- [Source: _bmad-output/planning-artifacts/architecture.md#Playwright 爬虫规范（同步模式）]
- [Source: _bmad-output/planning-artifacts/architecture.md#Interface Contract Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Enforcement Guidelines]
- [Source: sources/awin.py] — 主参照实现模式
- [Source: config/credentials.py] — _REQUIRED_KEYS 需添加 FACEBOOK_USERNAME/PASSWORD

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

无阻塞问题，直接实现完成。

### Completion Notes List

- 实现了完整的 Facebook Business Suite Playwright 爬虫，替换 stub 模块
- 两步登录流程：Business Suite 登录页 → 点击"使用 Facebook 登录" → Facebook 账密填写 → 等待 /latest/ 跳转
- PAGE_WAIT_TIMEOUT_MS=20000, TOTAL_TIMEOUT_S=90（Story 4.5 AC 指定，比其他爬虫更长）
- extract_fields 使用固定 7 字段映射（sorted 排列），与 awin.py 动态发现不同
- _extract_post_rows 支持标准 HTML table 和 ARIA role='row' 两种结构（适配 React 渲染）
- "--" 值映射为 None（Facebook 页面空值展示方式）
- tests/conftest.py 同步添加 FACEBOOK_USERNAME/PASSWORD，修复 test_structure.py 同步检查
- 15 个单元测试全部通过，0 回归

### File List

- sources/social_media.py（修改：替换 stub 为完整 Playwright 爬虫实现）
- tests/test_social_media.py（修改：替换 stub 测试，添加 extract_fields 单元测试 + 集成测试标注）
- tests/fixtures/social_media_sample.json（新增：extract_fields 单元测试 fixture，2 条记录含 null 字段）
- config/credentials.py（修改：_REQUIRED_KEYS 添加 FACEBOOK_USERNAME/PASSWORD）
- .env.example（修改：添加 Facebook 凭证区块）
- tests/conftest.py（修改：TEST_CREDENTIALS 添加 FACEBOOK_USERNAME/PASSWORD，与 _REQUIRED_KEYS 同步）
