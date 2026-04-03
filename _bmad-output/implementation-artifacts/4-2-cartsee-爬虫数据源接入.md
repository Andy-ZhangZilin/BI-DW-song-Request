# Story 4.2: CartSee 爬虫数据源接入

Status: done
<!-- reviewed: 2026-04-03 -->

## Story

作为操作者，
我希望验证器能通过 Playwright 自动登录 CartSee EDM 后台并抓取邮件营销数据字段，
以便我能获得 CartSee 平台数据的实际字段报告。

## Acceptance Criteria

1. **Given** `get_credentials()` 返回有效的 `CARTSEE_USERNAME` 和 `CARTSEE_PASSWORD`；**When** 调用 `cartsee.authenticate()`；**Then** 使用 `sync_playwright` 启动 headless Chromium，完成账号密码登录，返回 `True`，日志输出 `[cartsee] 认证 ... 成功`

2. **Given** 登录成功后；**When** 调用 `cartsee.fetch_sample()`；**Then** 抓取至少一条 EDM 数据记录，页面等待超时 15s，整体执行在 60s 内完成

3. **Given** `fetch_sample` 返回的样本数据；**When** 调用 `cartsee.extract_fields(sample)`；**Then** 返回符合标准 FieldInfo 结构的字段列表

4. **Given** 字段提取完成；**When** `write_raw_report("cartsee", fields, None, sample_count)` 被调用；**Then** `reports/cartsee-raw.md` 包含实际字段表格和需求字段对照区块

5. **Given** 页面出现验证码；**When** `fetch_sample()` 检测到验证码关键词；**Then** 抛出 `RuntimeError("[cartsee] 遇到验证码，请手动完成验证后重新运行")`，浏览器在 finally 块中正确关闭

6. **Given** 单元测试环境；**When** 运行 `tests/test_cartsee.py`；**Then** `extract_fields()` 单元测试通过（使用 `tests/fixtures/cartsee_sample.json`）；`fetch_sample()` 标注 `@pytest.mark.integration`，不在单元测试中执行

## Tasks / Subtasks

- [ ] Task 1: 实现 `sources/cartsee.py` (AC: 1, 2, 3, 5)
  - [ ] Task 1.1: 添加模块顶部常量 `SOURCE_NAME = "cartsee"`，导入 `sync_playwright`、`logging`、`from config.credentials import get_credentials`
  - [ ] Task 1.2: 实现 `authenticate() -> bool`：启动 headless Chromium，填写账号密码，检测登录成功标志，返回 True/False，finally 块关闭浏览器
  - [ ] Task 1.3: 实现 `fetch_sample(table_name: str = None) -> list[dict]`：登录后导航至 EDM 报表/数据页面，抓取至少 1 条记录，检测验证码并 raise RuntimeError，finally 关闭浏览器
  - [ ] Task 1.4: 实现 `extract_fields(sample: list[dict]) -> list[dict]`：从样本列表提取所有字段，推断数据类型和可空性，返回标准 FieldInfo 列表

- [ ] Task 2: 创建测试 fixture `tests/fixtures/cartsee_sample.json` (AC: 6)
  - [ ] Task 2.1: 根据 CartSee EDM 可能返回的字段（邮件营销指标）创建测试用样本 JSON

- [ ] Task 3: 编写单元测试 `tests/test_cartsee.py` (AC: 6)
  - [ ] Task 3.1: 测试 `extract_fields()` 使用 cartsee_sample.json fixture，验证返回 FieldInfo 结构正确
  - [ ] Task 3.2: 验证 FieldInfo 四字段均存在：field_name(str)、data_type(str)、sample_value(any)、nullable(bool)
  - [ ] Task 3.3: 标注 `fetch_sample()` 和 `authenticate()` 的集成测试为 `@pytest.mark.integration`（不在普通 pytest 运行中执行）

## Dev Notes

### 关键实现约束（必须遵守）

1. **凭证获取**：必须使用 `from config.credentials import get_credentials`，禁止直接调用 `os.getenv()`
2. **Playwright 模式**：必须使用 `from playwright.sync_api import sync_playwright`，禁止 async 版本
3. **浏览器关闭**：必须在 `finally` 块中调用 `browser.close()`，确保异常情况下也能正确关闭
4. **日志格式**：严格遵守 `[cartsee] {操作} ... 成功/失败`，凭证日志使用 `mask_credential()`
5. **函数签名**：三个公开函数签名固定，不得添加额外公开函数

### sources/cartsee.py 完整函数签名（必须遵守）

```python
import logging
from playwright.sync_api import sync_playwright
from config.credentials import get_credentials, mask_credential

logger = logging.getLogger(__name__)
SOURCE_NAME = "cartsee"

def authenticate() -> bool:
    """使用账号密码通过 Playwright 登录 CartSee EDM 后台。
    成功返回 True，失败打印错误并返回 False。浏览器在 finally 块中关闭。
    """
    ...

def fetch_sample(table_name: str = None) -> list[dict]:
    """登录 CartSee 后台并抓取至少 1 条 EDM 数据记录。
    遇到验证码时 raise RuntimeError，浏览器在 finally 块中关闭。
    table_name 参数忽略（非 SQL 数据源）。
    """
    ...

def extract_fields(sample: list[dict]) -> list[dict]:
    """从样本数据中提取字段信息，返回标准 FieldInfo 列表。"""
    ...
```

### FieldInfo 标准结构（必须遵守）

```python
{
    "field_name": str,      # 字段名（后台页面返回的原始名称）
    "data_type": str,       # 类型：string / number / boolean / array / object / null
    "sample_value": any,    # 示例值（脱敏处理，不含账号密码信息）
    "nullable": bool        # 是否可为空
}
```

### Playwright 爬虫标准模板（必须参照此模式）

```python
def fetch_sample(table_name: str = None) -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # 登录
            page.goto("https://cartsee.io/login", timeout=15000)
            creds = get_credentials()
            page.fill("input[name='email']", creds["CARTSEE_USERNAME"])
            page.fill("input[name='password']", creds["CARTSEE_PASSWORD"])
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle", timeout=15000)

            # 验证码检测
            if "captcha" in page.url.lower() or page.query_selector(".captcha"):
                raise RuntimeError(
                    "[cartsee] 遇到验证码，请手动完成验证后重新运行"
                )

            # 导航至数据页面并抓取
            page.goto("https://cartsee.io/campaigns", timeout=15000)
            page.wait_for_selector("table", timeout=15000)
            # 抓取表格行...
            records = []
            # ... 提取逻辑 ...
            if not records:
                raise RuntimeError("[cartsee] 未找到任何 EDM 数据记录")
            logger.info(f"[cartsee] 抓取 {len(records)} 条 EDM 记录 ... 成功")
            return records
        except RuntimeError:
            raise
        except Exception as e:
            if "captcha" in str(e).lower() or "验证码" in str(e):
                raise RuntimeError(
                    "[cartsee] 遇到验证码，请手动完成验证后重新运行"
                )
            raise RuntimeError(f"[cartsee] fetch_sample 异常：{e}")
        finally:
            browser.close()
```

**注意**：登录选择器（email/password input 的 CSS selector、Submit 按钮 selector、成功标志 selector）需在运行时根据实际页面结构调整。上述示例为推测性占位，实际实现时需根据页面结构更新。

### authenticate() 实现要点

```python
def authenticate() -> bool:
    creds = get_credentials()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("https://cartsee.io/login", timeout=15000)
            page.fill(...)  # email selector
            page.fill(...)  # password selector
            page.click(...)  # submit
            page.wait_for_load_state("networkidle", timeout=15000)
            # 检测登录成功：URL 变化或特定元素出现
            if "login" not in page.url:  # 不再在 login 页面 = 成功
                logger.info("[cartsee] 认证 ... 成功")
                return True
            else:
                logger.error("[cartsee] 认证 ... 失败：登录后仍在登录页")
                return False
        except Exception as e:
            logger.error(f"[cartsee] 认证 ... 失败：{e}")
            return False
        finally:
            browser.close()
```

### extract_fields() 实现要点

```python
def extract_fields(sample: list[dict]) -> list[dict]:
    """纯内存操作，不启动浏览器。"""
    if not sample:
        return []
    fields: list[dict] = []
    # 从样本第一条记录的 key 推断字段结构
    first = sample[0]
    for key, value in first.items():
        if isinstance(value, bool):
            data_type = "boolean"
        elif isinstance(value, int | float):
            data_type = "number"
        elif isinstance(value, list):
            data_type = "array"
        elif isinstance(value, dict):
            data_type = "object"
        elif value is None:
            data_type = "null"
        else:
            data_type = "string"
        nullable = any(record.get(key) is None for record in sample)
        fields.append({
            "field_name": key,
            "data_type": data_type,
            "sample_value": value,
            "nullable": nullable,
        })
    return fields
```

### 超时规范

| 操作 | 超时 |
|------|------|
| `page.goto()` | `timeout=15000`（15s） |
| `page.wait_for_selector()` | `timeout=15000`（15s） |
| `page.wait_for_load_state()` | `timeout=15000`（15s） |
| 单 source 整体 | 60s 内完成 |

### CartSee 平台背景

- 平台类型：Shopify App（EDM 邮件营销插件），无公开 API
- 接入方式：Playwright headless Chromium 账号密码登录
- 可查看指标：发送量、打开率、点击率、退订率、转化率、Contacts、自动化 GMV、Pop-up 转化率
- 登录入口：CartSee 后台（Shopify 应用内嵌或独立后台）
- `table_name` 参数：传入 `None`（非 SQL 数据源）

### 凭证键名

| 键名 | 用途 |
|------|------|
| `CARTSEE_USERNAME` | CartSee 登录账号（邮箱） |
| `CARTSEE_PASSWORD` | CartSee 登录密码 |

两个键已在 `config/credentials.py` 的 `_REQUIRED_KEYS` 列表中注册，无需修改 credentials.py。

### field_requirements.yaml 状态

当前 `config/field_requirements.yaml` **尚无 cartsee 数据源条目**。`write_raw_report("cartsee", ...)` 调用后，报告"需求字段"区块将显示"暂无配置的需求字段"。

若需添加 cartsee 字段需求，在 YAML 中追加：
```yaml
cartsee_table:
  - display_name: 发送量
    source: cartsee
    table: null
  - display_name: 打开率
    source: cartsee
    table: null
  # ... 其他指标
```
**本 Story 不要求修改 field_requirements.yaml**，field 配置由业务决策，可在后续单独添加。

### 测试结构要求

```python
# tests/test_cartsee.py
import json
import pytest
from pathlib import Path
from unittest.mock import patch

# 单元测试：仅测试 extract_fields()，不启动浏览器
def test_extract_fields_returns_field_info_structure(mock_credentials):
    from sources.cartsee import extract_fields
    fixture_path = Path("tests/fixtures/cartsee_sample.json")
    sample = json.loads(fixture_path.read_text(encoding="utf-8"))
    fields = extract_fields(sample)
    assert len(fields) > 0
    for f in fields:
        assert "field_name" in f
        assert "data_type" in f
        assert "sample_value" in f
        assert "nullable" in f
        assert isinstance(f["field_name"], str)
        assert f["data_type"] in {"string", "number", "boolean", "array", "object", "null"}
        assert isinstance(f["nullable"], bool)

def test_extract_fields_empty_sample(mock_credentials):
    from sources.cartsee import extract_fields
    assert extract_fields([]) == []

# 集成测试：标注 integration，不在单元测试中执行
@pytest.mark.integration
def test_authenticate_with_real_credentials():
    from sources.cartsee import authenticate
    result = authenticate()
    assert isinstance(result, bool)

@pytest.mark.integration
def test_fetch_sample_returns_records():
    from sources.cartsee import fetch_sample
    records = fetch_sample()
    assert len(records) >= 1
```

### cartsee_sample.json Fixture 示例

```json
[
  {
    "campaign_name": "Abandoned Cart Recovery #1",
    "sent": 1250,
    "opened": 387,
    "open_rate": 30.96,
    "clicked": 98,
    "click_rate": 7.84,
    "unsubscribed": 3,
    "revenue": 1842.50,
    "status": "active",
    "created_at": "2026-03-15"
  }
]
```

### 禁止行为

```python
# ❌ 直接读取环境变量
username = os.getenv("CARTSEE_USERNAME")

# ✅ 从统一加载器导入
creds = get_credentials()
username = creds["CARTSEE_USERNAME"]

# ❌ 爬虫静默失败
except Exception:
    pass

# ✅ 爬虫明确报错
except Exception as e:
    raise RuntimeError(f"[cartsee] 爬虫异常：{e}")

# ❌ 浏览器可能未关闭
browser = p.chromium.launch(...)
page = browser.new_page()
# 直接操作，无 try/finally

# ✅ finally 确保关闭
browser = p.chromium.launch(...)
try:
    ...
finally:
    browser.close()
```

### 项目结构目标文件

| 文件 | 操作 |
|------|------|
| `sources/cartsee.py` | **新建**（核心交付） |
| `tests/fixtures/cartsee_sample.json` | **新建**（测试数据） |
| `tests/test_cartsee.py` | **新建**（单元测试） |

**不触碰：**
- `config/credentials.py`（CARTSEE 凭证键已注册）
- `reporter.py`（不做修改）
- `validate.py`（Epic 5 职责）
- 其他 `sources/*.py` 文件

### 与 Awin/PartnerBoost 的关系

CartSee 与 Story 4-1（Awin）、Story 4-3（PartnerBoost）是同类爬虫模块，共享相同的实现模式：
- 同样使用 `sync_playwright` + headless Chromium
- 同样实现三函数接口 `authenticate / fetch_sample / extract_fields`
- 同样在 `finally` 块关闭浏览器
- 同样检测验证码并 raise RuntimeError
- 仅目标站点、选择器、数据结构不同

若 Story 4-1 已完成，参照 `sources/awin.py` 实现模式。

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.2: CartSee 爬虫数据源接入]
- [Source: _bmad-output/planning-artifacts/architecture.md#Process Patterns] — Playwright 爬虫标准模板、验证码处理
- [Source: _bmad-output/planning-artifacts/architecture.md#Interface Contract Patterns] — 三函数签名、FieldInfo 四字段结构
- [Source: _bmad-output/planning-artifacts/architecture.md#Structure Patterns] — 目录规范、禁止行为
- [Source: _bmad-output/planning-artifacts/architecture.md#Enforcement Guidelines] — AI Agent 必须遵守规则
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns] — 命名规范
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns] — 爬虫边界表
- [Source: _bmad-output/docs/datasource-api-research-report.md#5. CartSee] — 平台背景、可获取指标
- [Source: _bmad-output/implementation-artifacts/1-4-报告渲染器.md] — reporter.py 调用方式参考
- [Source: config/credentials.py] — CARTSEE_USERNAME / CARTSEE_PASSWORD 键名确认
- [Source: tests/conftest.py] — mock_credentials fixture 用法

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List

### Review Findings

- [x] [Review][Patch] browser 在 new_page() 失败时未关闭 — 已修复：browser.new_page() 移入 try 块 [sources/cartsee.py:27-29, 60-62]
- [x] [Review][Patch] page.content() 在验证码检测中被调用两次 — 已修复：赋变量 page_content 后复用 [sources/cartsee.py:70-72]
- [x] [Review][Patch] _try_extract_json_data 静默丢弃 dict 类型结果 — 已修复：补充 elif isinstance(data, dict): return [data] [sources/cartsee.py:136-141]
- [x] [Review][Patch] 测试文件使用相对路径 — 已修复：改为 Path(__file__).parent / "fixtures/cartsee_sample.json" [tests/test_cartsee.py]
- [x] [Review][Defer] URL 含 "login" 子路径时登录成功判断可能误判 [sources/cartsee.py:40] — deferred, CartSee 实际 URL 结构未知，推测性问题
- [x] [Review][Defer] fetch_sample() 无整体 60s 超时限制 [sources/cartsee.py:fetch_sample] — deferred, 各步骤均有 15s timeout，暂不加全局 timer
- [x] [Review][Defer] pytest.ini 未配置 addopts 默认过滤 integration 测试 [pytest.ini] — deferred, 设计选择，手动 -m "not integration" 符合项目约定
- [x] [Review][Patch] extract_fields 仅迭代 sample[0] 的键，后续记录独有字段被忽略 — 已修复：合并所有记录键集合，保留首次出现顺序 [sources/cartsee.py:extract_fields]
- [x] [Review][Patch] extract_fields 从 sample[0] 推断字段类型，首值为 None 时永久标注 "null" — 已修复：取首条非 None 值推断类型，提取 _infer_type() 辅助函数 [sources/cartsee.py:extract_fields]
- [x] [Review][Patch] _extract_table_records 无表头时静默丢弃所有行（应生成 col_0, col_1 备用键） — 已修复：无表头时生成 col_{i} 键 [sources/cartsee.py:_extract_table_records]
- [x] [Review][Patch] 凭证 KeyError 未处理：缺失 CARTSEE_USERNAME/PASSWORD 时抛出 KeyError 而非友好错误 — 已修复：try/except KeyError，authenticate 返回 False，fetch_sample 抛出 RuntimeError [sources/cartsee.py:22,63]
- [x] [Review][Defer] 无样本数量上限（MAX_SAMPLE_ROWS）[sources/cartsee.py:_extract_table_records] — deferred, 项目级决策，大量行场景暂未遇到
- [x] [Review][Defer] _try_extract_json_data 返回未经结构验证的 JS 对象 [sources/cartsee.py:_try_extract_json_data] — deferred, 辅助回退路径，主路径为 HTML table 提取
