# Story 4.1：Awin 爬虫数据源接入

Status: done

## Story

作为操作者，
我希望验证器能通过 Playwright 自动登录 Awin 联盟后台并抓取报表字段，
以便我能获得 Awin 平台数据的实际字段报告。

## Acceptance Criteria

1. **Given** `get_credentials()` 返回有效的 `AWIN_USERNAME` 和 `AWIN_PASSWORD`，**When** 调用 `awin.authenticate()`，**Then** 使用 `sync_playwright` 启动 headless Chromium，完成账号密码登录，返回 `True`，日志输出 `[awin] 认证 ... 成功`
2. **Given** 登录成功后，**When** 调用 `awin.fetch_sample()`，**Then** 导航至报表页面，抓取至少一条数据记录，Playwright 页面等待超时设置为 15s，整体执行在 60s 内完成
3. **Given** `fetch_sample` 返回的样本数据，**When** 调用 `awin.extract_fields(sample)`，**Then** 返回符合标准 FieldInfo 结构的字段列表（每项含 `field_name`、`data_type`、`sample_value`、`nullable`）
4. **Given** 字段提取完成，**When** `write_raw_report("awin", fields, ...)` 被调用，**Then** `reports/awin-raw.md` 包含实际字段表格和需求字段对照区块
5. **Given** 页面出现验证码或登录拦截，**When** `fetch_sample()` 检测到验证码关键词，**Then** 抛出 `RuntimeError("[awin] 遇到验证码，请手动完成验证后重新运行")`，不静默失败，浏览器在 `finally` 块中正确关闭
6. **Given** 登录凭证无效，**When** 调用 `authenticate()`，**Then** 日志输出 `[awin] 认证 ... 失败：{错误详情}`，返回 `False`，浏览器正确关闭
7. **Given** 单元测试环境，**When** 运行 `tests/test_awin.py`，**Then** `extract_fields()` 单元测试通过（使用 `tests/fixtures/awin_sample.json`）；`fetch_sample()` 标注 `@pytest.mark.integration`，不在单元测试中执行

## Tasks / Subtasks

- [x] 创建 `sources/awin.py`（AC: #1 #2 #3 #4 #5 #6）
  - [x] 模块顶部：导入 `sync_playwright`、`get_credentials`、`mask_credential`、`write_raw_report`、`init_validation_report`、`logging`
  - [x] 实现 `authenticate() -> bool`：启动 headless Chromium、导航至登录页、填入凭证、检测登录成功标识、返回 True/False，浏览器对象复用（存为模块级变量）或 Context Manager 管理
  - [x] 实现 `fetch_sample(table_name: str = None) -> list[dict]`：导航至报表页、等待 15s 超时、提取表格行、检测验证码关键词（捕获后 raise RuntimeError），浏览器在 `finally` 块关闭
  - [x] 实现 `extract_fields(sample: list[dict]) -> list[dict]`：纯数据转换，遍历样本记录，推断 `data_type`、设置 `nullable`，返回 FieldInfo 列表
  - [x] 在 `authenticate()` 完成后调用 `init_validation_report("awin")`
  - [x] 在 `fetch_sample()` 完成后调用 `write_raw_report("awin", fields, None, len(sample))`
  - [x] 所有日志使用 `[awin]` 前缀，凭证使用 `mask_credential()` 脱敏

- [x] 创建 `tests/fixtures/awin_sample.json`（AC: #7）
  - [x] 包含 3-5 条模拟报表记录，字段名用英文，值类型多样（str / int / float）

- [x] 创建 `tests/test_awin.py`（AC: #7）
  - [x] `TestExtractFields`：加载 `awin_sample.json`，验证返回 FieldInfo 结构正确（field_name/data_type/sample_value/nullable 四字段齐全）
  - [x] `TestExtractFieldsEdgeCases`：空列表输入返回空列表；含 None 值的字段 nullable=True
  - [x] `fetch_sample` 集成测试仅打标注，不在单元测试套件执行：`@pytest.mark.integration`

## Dev Notes

### 必须创建的文件

| 文件路径 | 说明 |
|---------|------|
| `sources/awin.py` | Playwright 爬虫模块，实现三接口 |
| `tests/test_awin.py` | 单元测试（extract_fields + 边界用例） |
| `tests/fixtures/awin_sample.json` | 模拟 Awin 报表行数据 |

### `sources/awin.py` 代码骨架

```python
"""Awin 爬虫数据源模块。

通过 Playwright 自动化登录 Awin 联盟后台，抓取报表字段。

接口契约（ARCH2）：
    authenticate() -> bool
    fetch_sample(table_name: str = None) -> list[dict]
    extract_fields(sample: list[dict]) -> list[dict]
"""
import logging
import time
from typing import Optional

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from config.credentials import get_credentials, mask_credential
from reporter import write_raw_report, init_validation_report

logger = logging.getLogger(__name__)

# Awin 登录地址（根据实际调整）
AWIN_LOGIN_URL = "https://ui.awin.com/user/login"
AWIN_REPORT_URL = "https://ui.awin.com/awin/publisher/..."  # 实现时替换为真实报表页

# 超时设置（ARCH10）
PAGE_WAIT_TIMEOUT_MS = 15_000   # 15s
TOTAL_TIMEOUT_S = 60             # 60s

# CAPTCHA 关键词（用于检测拦截，扩展时增加此列表）
CAPTCHA_KEYWORDS = ["captcha", "验证码", "robot", "human verification", "challenge"]


def authenticate() -> bool:
    """通过账号密码完成 Awin 后台登录。

    Returns:
        True 表示登录成功，False 表示失败。
    """
    creds = get_credentials()
    username = creds["AWIN_USERNAME"]
    password = creds["AWIN_PASSWORD"]
    logger.info(f"[awin] 认证，用户名：{mask_credential(username)}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(AWIN_LOGIN_URL, timeout=PAGE_WAIT_TIMEOUT_MS)
                page.fill("input[name='username']", username)  # 选择器实现时调整
                page.fill("input[name='password']", password)
                page.click("button[type='submit']")
                page.wait_for_url("**/awin/**", timeout=PAGE_WAIT_TIMEOUT_MS)
                logger.info("[awin] 认证 ... 成功")
                init_validation_report("awin")
                return True
            except Exception as e:
                logger.error(f"[awin] 认证 ... 失败：{e}")
                return False
            finally:
                browser.close()
    except Exception as e:
        logger.error(f"[awin] 认证 ... 失败：{e}")
        return False


def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """导航至 Awin 报表页面，抓取样本数据行。

    Args:
        table_name: 未使用（Awin 爬虫无多表路由需求），保持接口一致性。

    Returns:
        样本记录列表，每项为原始字段字典。

    Raises:
        RuntimeError: 检测到验证码时。
    """
    creds = get_credentials()
    username = creds["AWIN_USERNAME"]
    password = creds["AWIN_PASSWORD"]
    start = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            # 登录
            page.goto(AWIN_LOGIN_URL, timeout=PAGE_WAIT_TIMEOUT_MS)
            page.fill("input[name='username']", username)
            page.fill("input[name='password']", password)
            page.click("button[type='submit']")
            page.wait_for_url("**/awin/**", timeout=PAGE_WAIT_TIMEOUT_MS)

            # 检测验证码
            page_text = page.content().lower()
            for kw in CAPTCHA_KEYWORDS:
                if kw in page_text:
                    raise RuntimeError("[awin] 遇到验证码，请手动完成验证后重新运行")

            # 导航至报表页
            page.goto(AWIN_REPORT_URL, timeout=PAGE_WAIT_TIMEOUT_MS)
            page.wait_for_load_state("networkidle", timeout=PAGE_WAIT_TIMEOUT_MS)

            # 检测超时
            if time.time() - start > TOTAL_TIMEOUT_S:
                raise RuntimeError("[awin] 整体执行超过 60s 限制")

            # 抓取报表数据（示例：读取表格行）
            rows = page.query_selector_all("table tbody tr")
            sample: list[dict] = []
            for row in rows[:10]:  # 最多取 10 行
                cells = row.query_selector_all("td")
                record = {f"col_{i}": cell.inner_text() for i, cell in enumerate(cells)}
                sample.append(record)

            if not sample:
                logger.warning("[awin] 报表页无数据行，返回空样本")

            fields = extract_fields(sample)
            write_raw_report("awin", fields, table_name, len(sample))
            logger.info(f"[awin] fetch_sample ... 成功，抓取 {len(sample)} 条记录")
            return sample

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"[awin] fetch_sample ... 失败：{e}")
            raise
        finally:
            browser.close()


def extract_fields(sample: list[dict]) -> list[dict]:
    """从样本数据中提取 FieldInfo 结构列表。

    Args:
        sample: fetch_sample() 返回的原始记录列表。

    Returns:
        FieldInfo 列表，每项含 field_name / data_type / sample_value / nullable。
    """
    if not sample:
        return []

    # 以第一条记录的键为字段名基准，合并全部记录做 nullable 推断
    all_keys: set[str] = set()
    for record in sample:
        all_keys.update(record.keys())

    fields: list[dict] = []
    for key in sorted(all_keys):
        values = [rec.get(key) for rec in sample]
        non_null_values = [v for v in values if v is not None and v != ""]
        sample_value = non_null_values[0] if non_null_values else None
        nullable = any(v is None or v == "" for v in values)
        data_type = _infer_type(sample_value)
        fields.append({
            "field_name": key,
            "data_type": data_type,
            "sample_value": sample_value,
            "nullable": nullable,
        })

    return fields


def _infer_type(value) -> str:
    """根据 Python 类型推断 data_type 标签。"""
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return "string"
```

### `tests/fixtures/awin_sample.json` 示例

```json
[
  {
    "date": "2024-01-15",
    "transaction_id": "TXN-001",
    "amount": "99.00",
    "currency": "USD",
    "status": "approved",
    "publisher_id": "12345",
    "commission": "4.95"
  },
  {
    "date": "2024-01-16",
    "transaction_id": "TXN-002",
    "amount": "149.50",
    "currency": "USD",
    "status": "pending",
    "publisher_id": "12345",
    "commission": null
  }
]
```

### `tests/test_awin.py` 示例骨架

```python
"""Awin 数据源单元测试。

AC7: extract_fields() 使用 fixtures/awin_sample.json 完成单元测试；
     fetch_sample() 标注 @pytest.mark.integration，不在 CI 单元测试套件运行。
"""
import json
import pytest
from pathlib import Path

import sources.awin as awin

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestExtractFields:
    """AC3 & AC7: extract_fields 返回标准 FieldInfo 结构。"""

    @pytest.fixture
    def sample(self):
        with open(FIXTURES_DIR / "awin_sample.json", encoding="utf-8") as f:
            return json.load(f)

    def test_returns_list(self, sample):
        result = awin.extract_fields(sample)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_each_item_has_required_keys(self, sample):
        result = awin.extract_fields(sample)
        for item in result:
            assert "field_name" in item
            assert "data_type" in item
            assert "sample_value" in item
            assert "nullable" in item

    def test_nullable_detected_correctly(self, sample):
        """commission 在第 2 条记录中为 null，应 nullable=True。"""
        result = awin.extract_fields(sample)
        commission = next(f for f in result if f["field_name"] == "commission")
        assert commission["nullable"] is True


class TestExtractFieldsEdgeCases:
    def test_empty_sample_returns_empty_list(self):
        assert awin.extract_fields([]) == []

    def test_all_none_value_nullable(self):
        sample = [{"field_x": None}, {"field_x": None}]
        result = awin.extract_fields(sample)
        assert result[0]["nullable"] is True


@pytest.mark.integration
class TestFetchSampleIntegration:
    """集成测试：需要真实 Awin 账号，CI 中跳过。"""

    def test_fetch_sample_returns_list(self, mock_credentials):
        result = awin.fetch_sample()
        assert isinstance(result, list)
```

### 架构约束（必须遵守）

| 规则 | 说明 |
|------|------|
| **ARCH2** | 接口契约：`authenticate() -> bool`，`fetch_sample(table_name=None) -> list[dict]`，`extract_fields(sample) -> list[dict]` |
| **ARCH3** | 凭证必须通过 `get_credentials()` 获取，**禁止直接调用 `os.getenv()`** |
| **ARCH10** | Playwright 使用 `sync_playwright` 同步模式；页面等待超时 15s；单 source 整体超时 60s |
| **ARCH12** | `fetch_sample()` 标注 `@pytest.mark.integration`；fixtures 存放于 `tests/fixtures/awin_sample.json` |
| **NFR2** | 日志输出凭证时必须调用 `mask_credential()`，不输出完整 Token/密码 |
| **NFR6** | 爬虫异常不静默失败，必须有明确错误提示（raise 或 logger.error + return False） |

### 关键实现细节

1. **浏览器生命周期**：`authenticate()` 和 `fetch_sample()` 各自独立启动/关闭 browser（不跨函数共享 playwright context），浏览器关闭放在 `finally` 块。

2. **验证码检测时机**：在 `fetch_sample()` 内登录成功后立即检测，在导航至报表页之前执行 CAPTCHA 检查。

3. **CSS 选择器**：Awin 登录表单实现时需实际检查页面 DOM 结构；初始骨架使用通用选择器（`input[name='username']`），集成测试阶段按实际调整。

4. **extract_fields 纯函数**：不调用任何外部 API，不依赖 mock_credentials，单元测试直接调用即可。

5. **FieldInfo 标准结构**（ARCH2）：
   ```python
   {
       "field_name": str,    # 字段名
       "data_type": str,     # "string" / "integer" / "number" / "boolean" / "unknown"
       "sample_value": Any,  # 第一个非空值；全部为空时 None
       "nullable": bool,     # True = 样本中存在 None 或 ""
   }
   ```

6. **write_raw_report 调用位置**：在 `fetch_sample()` 内 `extract_fields()` 完成后调用，`table_name=None`（Awin 无多表路由）。

7. **init_validation_report 调用位置**：在 `authenticate()` 登录成功后调用（仅首次创建，已存在则跳过）。

### 注意事项：Awin 存在 REST API

研究报告显示 Awin 有公开 Publisher API（OAuth 2.0）。但本 Story（Epic 4）按架构决策使用 Playwright 浏览器自动化，与 CartSee / PartnerBoost 保持统一的爬虫技术路线，不改用 API 方式。如未来有 API 接入需求可另起 Story。

### 已实现的依赖组件（可直接使用）

- `reporter.write_raw_report(source_name, fields, table_name, sample_count)` — 生成 raw.md ✅
- `reporter.init_validation_report(source_name)` — 首次创建 validation.md ✅
- `config.credentials.get_credentials()` — 返回凭证字典，缺失时 raise ValueError ✅
- `config.credentials.mask_credential(value)` — 日志脱敏，前 4 位 + `****` ✅
- `tests/conftest.py` — `mock_credentials` fixture，patch `get_credentials()` 返回 `TEST_CREDENTIALS` ✅

### Project Structure Notes

本 Story 新增文件清单：

```
outdoor-data-validator/
├── sources/
│   └── awin.py                        ← 新建（Playwright 爬虫）
├── tests/
│   ├── test_awin.py                   ← 新建（单元测试）
│   └── fixtures/
│       └── awin_sample.json           ← 新建（测试 fixture）
```

不修改：`reporter.py`、`config/credentials.py`、`config/field_requirements.yaml`、`validate.py`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#ARCH2 统一接口契约]
- [Source: _bmad-output/planning-artifacts/architecture.md#ARCH10 超时配置]
- [Source: _bmad-output/planning-artifacts/architecture.md#ARCH12 测试规范]
- [Source: _bmad-output/docs/datasource-api-research-report.md#6. Awin Publisher API]
- [Source: _bmad-output/implementation-artifacts/1-1-项目结构初始化.md#Dev Notes 测试模式]
- [Source: config/credentials.py — get_credentials / mask_credential 实现]
- [Source: reporter.py — write_raw_report / init_validation_report 实现]
- [Source: tests/conftest.py — mock_credentials fixture]
- [Source: tests/test_reporter.py — 测试组织模式（class-based, monkeypatch）]

### Review Findings

- [x] [Review][Decision] authenticate() 与 fetch_sample() 各自独立登录 → 决策 B：提取 _login(page) helper，消除重复，各自保持独立浏览器生命周期
- [x] [Review][Decision] _infer_type() 不解析字符串编码的数值 → 决策 B：尝试 int/float 解析，"99.00" 推断为 "number"
- [x] [Review][Decision] 纯空白字符串是否视为空值 → 决策 B：改用 _is_empty() 统一判断，处理 None/""/"   "
- [x] [Review][Patch] browser 变量未在 try 块外初始化，launch() 失败时 finally 抛出 UnboundLocalError [sources/awin.py:28,53]
- [x] [Review][Patch] 60s 总超时仅单点检查（登录后、报表导航前），报表页 goto + networkidle 可各占 15s [sources/awin.py:59-62]
- [x] [Review][Patch] _check_captcha() 对 page.content()（原始 HTML）匹配关键词，脚本/CSS 中的 "challenge" 等词可触发误报 [sources/awin.py:99]
- [x] [Review][Patch] _extract_table_rows() 吞没所有异常仅记 warning，提取失败与合法空表行为无法区分 [sources/awin.py:93-107]
- [x] [Review][Patch] 硬编码 [:20] 行上限未定义为命名常量 MAX_SAMPLE_ROWS [sources/awin.py:95,103]
- [x] [Review][Patch] get_credentials() 的 KeyError/ValueError 在 authenticate() 和 fetch_sample() 中未捕获，直接传播给调用方 [sources/awin.py:26,50]
- [x] [Review][Patch] init_validation_report() 的 OSError 未处理，文件写入失败导致 authenticate() 返回 False 尽管登录已成功 [sources/awin.py:41]
- [x] [Review][Patch] 登录 URL 模式 **/awin/** 过于宽泛，凭证错误时错误页面也可能匹配导致误判为登录成功 [sources/awin.py:36,59]
- [x] [Review][Patch] write_raw_report() 的 OSError 未专门处理，被 bare except 捕获重抛，无特定日志 [sources/awin.py:65]
- [x] [Review][Patch] 重复列名会导致同名单元格值互相覆盖 [sources/awin.py:104-106]
- [x] [Review][Patch] 表头 trim 后为空字符串时用作 dict key，多列可能冲突 [sources/awin.py:104-106]
- [x] [Review][Patch] cells 数量少于 headers 的不完整行被静默丢弃，无 warning 日志 [sources/awin.py:103]
- [x] [Review][Patch] 无表头分支选择器 "table tr:not(:first-child)" 可能将 th 表头行包含为数据行 [sources/awin.py:95]
- [x] [Review][Patch] pytest.ini 缺少 addopts = -m "not integration"，需手动记住传参才能跳过集成测试 [pytest.ini:1]
- [x] [Review][Patch] write_raw_report 透传 table_name 参数而非硬编码 None，不符合 Dev Note 4 [sources/awin.py:65]
- [x] [Review][Defer] 集成测试仅断言返回类型 (bool/list)，不验证正确性 [tests/test_awin.py] — deferred, pre-existing
- [x] [Review][Defer] fetch_sample() 入口未记录 mask 后的凭证日志（不同于 authenticate() 的日志模式） [sources/awin.py:50-57] — deferred, pre-existing

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

（无）

### Completion Notes List

- 创建 `sources/awin.py`：完整实现三接口契约（authenticate / fetch_sample / extract_fields），遵循 ARCH2/ARCH10/NFR2
- `authenticate()`：sync_playwright headless Chromium，填写用户名密码，等待 URL 跳转，在 finally 关闭浏览器，返回 True/False
- `fetch_sample()`：复用登录流程 → 验证码检测 → 报表页导航 → 表格行提取 → 调用 write_raw_report，整体超时 60s，页面等待 15s
- `extract_fields()`：纯函数，合并所有记录键集，推断 data_type（string/integer/number/boolean/unknown），检测 nullable（None 或 ""），按字段名排序返回
- `_check_captcha()`：私有辅助函数，检测 CAPTCHA 关键词（8 个），raise RuntimeError 而非静默失败（NFR6）
- `_extract_table_rows()`：尝试读取 `<table>` 表头，有表头按列名构建字典，无表头用 col_N 作为键名，最多取 20 行
- 创建 `tests/fixtures/awin_sample.json`：3 条模拟 Awin 交易记录，包含 null 值（commission=null）
- 创建 `tests/test_awin.py`：20 个单元测试（11 个 TestExtractFields + 9 个 TestExtractFieldsEdgeCases），2 个集成测试标注 @pytest.mark.integration
- 新增 `pytest.ini`：注册 integration marker，消除 PytestUnknownMarkWarning
- 全量回归测试：191 passed, 4 deselected（integration 跳过），无回归

### File List

- sources/awin.py（新建）
- tests/test_awin.py（新建）
- tests/fixtures/awin_sample.json（新建）
- pytest.ini（新建）
- _bmad-output/implementation-artifacts/4-1-awin-爬虫数据源接入.md（更新状态）
- _bmad-output/implementation-artifacts/sprint-status.yaml（更新 4-1 状态）
