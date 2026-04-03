# Story 4.3: PartnerBoost 爬虫数据源接入

Status: done

## Story

作为操作者，
我希望验证器能通过 Playwright 自动登录 PartnerBoost 后台并抓取联盟营销数据字段，
以便我能获得 PartnerBoost 平台数据的实际字段报告。

## Acceptance Criteria

1. **Given** `get_credentials()` 返回有效的 `PARTNERBOOST_USERNAME` 和 `PARTNERBOOST_PASSWORD`；**When** 调用 `partnerboost.authenticate()`；**Then** 使用 `sync_playwright` 启动 headless Chromium，完成账号密码登录，返回 `True`，日志输出 `[partnerboost] 认证 ... 成功`

2. **Given** 登录成功后；**When** 调用 `partnerboost.fetch_sample()`；**Then** 抓取至少一条联盟报表记录，页面等待超时 15s，整体执行在 60s 内完成

3. **Given** fetch_sample 返回的样本数据；**When** 调用 `partnerboost.extract_fields(sample)`；**Then** 返回符合标准 FieldInfo 结构的字段列表

4. **Given** 字段提取完成；**When** `write_raw_report("partnerboost", fields, ...)` 被调用；**Then** `reports/partnerboost-raw.md` 包含实际字段表格和需求字段对照区块

5. **Given** 页面出现验证码；**When** `fetch_sample()` 检测到；**Then** 抛出 `RuntimeError("[partnerboost] 遇到验证码，请手动完成验证后重新运行")`，浏览器正确关闭

6. **Given** 单元测试环境；**When** 运行 `tests/test_partnerboost.py`；**Then** `extract_fields()` 单元测试通过（使用 `tests/fixtures/partnerboost_sample.json`）；`fetch_sample()` 标注 `@pytest.mark.integration`，不在单元测试中执行

## Tasks / Subtasks

- [x] Task 1: 实现 `sources/partnerboost.py` (AC: 1, 2, 3, 5)
  - [x] Task 1.1: 添加模块级导入和常量定义（sync_playwright, logging, credentials）
  - [x] Task 1.2: 实现 `authenticate()` — sync_playwright 登录，检测登录成功，返回 bool
  - [x] Task 1.3: 实现 `fetch_sample()` — sync_playwright 登录 + 导航报表页 + 抓取数据行，15s/60s 超时
  - [x] Task 1.4: 在 `fetch_sample()` 中添加验证码关键词检测，抛出标准 RuntimeError
  - [x] Task 1.5: 实现 `extract_fields(sample)` — 纯函数，将原始 dict 列表转为 FieldInfo 列表
  - [x] Task 1.6: 确保 `finally` 块中 `browser.close()` 被可靠调用

- [x] Task 2: 创建测试夹具 `tests/fixtures/partnerboost_sample.json` (AC: 6)
  - [x] Task 2.1: 根据 PartnerBoost 典型报表结构定义 1 条样本记录

- [x] Task 3: 编写单元测试 `tests/test_partnerboost.py` (AC: 6)
  - [x] Task 3.1: 测试 `extract_fields()` 使用夹具数据，验证 FieldInfo 四字段结构
  - [x] Task 3.2: 测试 `extract_fields()` 处理空列表（边界情况）
  - [x] Task 3.3: 验证 `fetch_sample()` 标注了 `@pytest.mark.integration`
  - [x] Task 3.4: 测试 `authenticate()` 在凭证异常时的行为（mock playwright）

### Review Findings（代码审查，2026-04-03）

- [x] [Review][Patch] 移除未使用导入 `PlaywrightTimeoutError` [sources/partnerboost.py:15] — 已修复
- [x] [Review][Patch][HIGH] `wait_for_url` glob 含 `(a|b)` 非标准语法，改为 lambda 谓词 [sources/partnerboost.py:56,90] — 已修复
- [x] [Review][Patch] `_extract_table_records(page)` 缺少 `Page` 类型注解 [sources/partnerboost.py:119] — 已修复
- [x] [Review][Patch] 表头空列名导致字典键覆盖，改为 `_col{i}` 占位 [sources/partnerboost.py:121] — 已修复
- [x] [Review][Patch] 登录后 captcha 检测需先等 networkidle [sources/partnerboost.py:94] — 已修复
- [x] [Review][Defer] authenticate() debug/info 日志级别不一致 [sources/partnerboost.py:47] — deferred, pre-existing
- [x] [Review][Defer] 登录逻辑在 authenticate/fetch_sample 中重复 — deferred, architectural decision
- [x] [Review][Defer] headless 模式未设 viewport，可能影响 SPA 渲染 — deferred, optional improvement

## Dev Notes

### 实现目标文件

| 文件 | 说明 |
|------|------|
| `sources/partnerboost.py` | **核心新建文件**，位于 `sources/` 目录 |
| `tests/test_partnerboost.py` | 单元测试 |
| `tests/fixtures/partnerboost_sample.json` | 测试夹具数据 |

> Story 4-3 **不修改** `validate.py`、`reporter.py`、`config/credentials.py`（已含 PARTNERBOOST_* 凭证键）、其他 source 文件。

### 函数签名（必须严格遵守）

```python
# sources/partnerboost.py

from playwright.sync_api import sync_playwright
from config.credentials import get_credentials, mask_credential
import logging

logger = logging.getLogger(__name__)
SOURCE_NAME = "partnerboost"

def authenticate() -> bool:
    """使用 sync_playwright 完成 PartnerBoost 账号密码登录。
    成功返回 True，失败日志输出错误并返回 False。
    """
    ...

def fetch_sample(table_name: str = None) -> list[dict]:
    """启动 Playwright，登录后导航报表页，抓取至少一条记录。
    检测到验证码时抛出 RuntimeError。
    页面等待超时 15s，整体 60s 内完成。
    """
    ...

def extract_fields(sample: list[dict]) -> list[dict]:
    """从样本记录列表中提取 FieldInfo 结构。纯函数，无 I/O。
    返回 list[{"field_name": str, "data_type": str, "sample_value": Any, "nullable": bool}]
    """
    ...
```

### Playwright 实现规范（来自 ARCH10）

**必须使用同步模式**：`from playwright.sync_api import sync_playwright`，禁止使用 `async_playwright`。

```python
# authenticate() 实现模板
def authenticate() -> bool:
    creds = get_credentials()
    username = creds["PARTNERBOOST_USERNAME"]
    password = creds["PARTNERBOOST_PASSWORD"]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("https://app.partnerboost.com/login", timeout=15000)
            page.fill("input[name=email]", username)
            page.fill("input[name=password]", password)
            page.click("button[type=submit]")
            page.wait_for_url("**/dashboard**", timeout=15000)  # 登录成功后跳转 dashboard
            logger.info(f"[{SOURCE_NAME}] 认证 ... 成功")
            return True
        except Exception as e:
            logger.info(f"[{SOURCE_NAME}] 认证 ... 失败：{e}")
            return False
        finally:
            browser.close()

# fetch_sample() 实现模板
def fetch_sample(table_name: str = None) -> list[dict]:
    creds = get_credentials()
    username = creds["PARTNERBOOST_USERNAME"]
    password = creds["PARTNERBOOST_PASSWORD"]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # 登录
            page.goto("https://app.partnerboost.com/login", timeout=15000)
            page.fill("input[name=email]", username)
            page.fill("input[name=password]", password)
            page.click("button[type=submit]")
            page.wait_for_url("**/dashboard**", timeout=15000)

            # 检测验证码（登录页或跳转后）
            content = page.content()
            if any(kw in content.lower() for kw in ["captcha", "robot", "verify you are human"]):
                raise RuntimeError(f"[{SOURCE_NAME}] 遇到验证码，请手动完成验证后重新运行")

            # 导航至报表页
            page.goto("https://app.partnerboost.com/reports", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # 再次检测验证码
            content = page.content()
            if any(kw in content.lower() for kw in ["captcha", "robot", "verify you are human"]):
                raise RuntimeError(f"[{SOURCE_NAME}] 遇到验证码，请手动完成验证后重新运行")

            # 抓取数据行
            rows = page.query_selector_all("table tbody tr")
            if not rows:
                # 备选：尝试其他常见选择器
                rows = page.query_selector_all("tr[class*='row'], .data-row, [data-testid*='row']")

            records = []
            if rows:
                # 获取表头
                header_cells = page.query_selector_all("table thead th, table thead td")
                headers = [cell.inner_text().strip() for cell in header_cells]

                # 取第一行数据
                first_row = rows[0]
                cells = first_row.query_selector_all("td")
                values = [cell.inner_text().strip() for cell in cells]

                if headers and values:
                    record = {headers[i]: values[i] for i in range(min(len(headers), len(values)))}
                    records.append(record)

            if not records:
                raise RuntimeError(f"[{SOURCE_NAME}] 未找到数据行，页面可能无数据或结构已变更")

            logger.info(f"[{SOURCE_NAME}] 获取报表样本 ... 成功，共 {len(records)} 条记录")
            return records

        except RuntimeError:
            raise  # 直接重新抛出 RuntimeError（含验证码和数据缺失）
        except Exception as e:
            raise RuntimeError(f"[{SOURCE_NAME}] 爬虫异常：{e}")
        finally:
            browser.close()
```

### extract_fields() 实现规范

`extract_fields()` 是**纯函数**（无 I/O，无网络请求，无浏览器），负责将 `fetch_sample()` 返回的 `list[dict]` 转为标准 FieldInfo 格式。这是单元测试的核心目标。

```python
def extract_fields(sample: list[dict]) -> list[dict]:
    if not sample:
        return []

    # 合并所有记录的键（处理第一条记录可能缺失某些字段的情况）
    all_keys: set[str] = set()
    for record in sample:
        all_keys.update(record.keys())

    fields = []
    for key in sorted(all_keys):
        # 从所有记录中找第一个非 None 的示例值
        sample_value = None
        nullable = False
        for record in sample:
            val = record.get(key)
            if val is None or val == "":
                nullable = True
            else:
                sample_value = val

        # 推断数据类型
        if sample_value is None:
            data_type = "null"
        elif isinstance(sample_value, bool):
            data_type = "boolean"
        elif isinstance(sample_value, int):
            data_type = "number"
        elif isinstance(sample_value, float):
            data_type = "number"
        else:
            # 尝试从字符串判断数值型
            try:
                float(str(sample_value).replace(",", "").replace("$", ""))
                data_type = "number"
            except (ValueError, AttributeError):
                data_type = "string"

        fields.append({
            "field_name": key,
            "data_type": data_type,
            "sample_value": sample_value,
            "nullable": nullable,
        })

    return fields
```

### 测试夹具格式 `tests/fixtures/partnerboost_sample.json`

```json
[
    {
        "Date": "2026-03-01",
        "Partner": "BestReviews",
        "Click": "150",
        "Sale": "3",
        "Revenue": "299.97",
        "Commission": "29.99",
        "Status": "Approved",
        "Channel": "Content",
        "Payment Status": "Pending"
    }
]
```

### 测试文件结构 `tests/test_partnerboost.py`

```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sources.partnerboost as partnerboost

FIXTURE_PATH = Path("tests/fixtures/partnerboost_sample.json")


def load_fixture():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_extract_fields_returns_field_info_structure():
    """extract_fields 必须返回含四字段的 FieldInfo 列表"""
    sample = load_fixture()
    fields = partnerboost.extract_fields(sample)
    assert len(fields) > 0
    for field in fields:
        assert "field_name" in field
        assert "data_type" in field
        assert "sample_value" in field
        assert "nullable" in field
        assert isinstance(field["field_name"], str)
        assert isinstance(field["data_type"], str)
        assert isinstance(field["nullable"], bool)


def test_extract_fields_empty_input():
    """extract_fields 处理空列表时返回空列表"""
    assert partnerboost.extract_fields([]) == []


def test_extract_fields_known_fields():
    """extract_fields 从夹具数据中正确提取所有键"""
    sample = load_fixture()
    fields = partnerboost.extract_fields(sample)
    field_names = {f["field_name"] for f in fields}
    assert "Date" in field_names
    assert "Partner" in field_names
    assert "Commission" in field_names


@pytest.mark.integration
def test_fetch_sample_integration(mock_credentials):
    """集成测试：fetch_sample 需要真实凭证和网络，标注 integration 跳过单元测试"""
    sample = partnerboost.fetch_sample()
    assert isinstance(sample, list)
    assert len(sample) > 0


def test_authenticate_returns_false_on_failure(mock_credentials):
    """authenticate 凭证无效时返回 False，不抛出异常"""
    with patch("sources.partnerboost.sync_playwright") as mock_pw:
        mock_instance = MagicMock()
        mock_pw.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_pw.return_value.__exit__ = MagicMock(return_value=False)
        browser = MagicMock()
        page = MagicMock()
        mock_instance.chromium.launch.return_value = browser
        browser.new_page.return_value = page
        page.wait_for_url.side_effect = Exception("Timeout waiting for url")
        result = partnerboost.authenticate()
        assert result is False
```

**重要**：`@pytest.mark.integration` 标注的测试在 `pytest tests/ -m "not integration"` 时**自动跳过**，无需额外配置。

### FieldInfo 标准结构（来自 ARCH2）

```python
{
    "field_name": str,      # 字段名（页面表格原始列名）
    "data_type": str,       # "string" / "number" / "boolean" / "null"
    "sample_value": Any,    # 示例值（来自夹具或真实抓取）
    "nullable": bool        # True = 存在空值
}
```

### 凭证安全规范（来自 ARCH3、NFR2）

```python
# ✅ 正确：从统一加载器导入
from config.credentials import get_credentials, mask_credential

creds = get_credentials()
username = creds["PARTNERBOOST_USERNAME"]
password = creds["PARTNERBOOST_PASSWORD"]
logger.info(f"[{SOURCE_NAME}] 使用账号：{mask_credential(username)}")  # 仅前4位

# ❌ 禁止：直接调用 os.getenv()
import os
username = os.getenv("PARTNERBOOST_USERNAME")  # 严格禁止
```

### 超时规范（来自 ARCH10）

| 场景 | 设置值 | 参数写法 |
|------|--------|----------|
| `page.goto()` | 15000ms | `timeout=15000` |
| `page.wait_for_url()` | 15000ms | `timeout=15000` |
| `page.wait_for_load_state()` | 15000ms | `timeout=15000` |
| 单 source 整体执行 | 60s | 调度器层限制，source 内无需显式设置 |

### 日志格式规范（来自 Format Patterns）

```python
# 认证成功
logger.info(f"[{SOURCE_NAME}] 认证 ... 成功")
# 认证失败
logger.info(f"[{SOURCE_NAME}] 认证 ... 失败：{具体错误}")
# 数据抓取成功
logger.info(f"[{SOURCE_NAME}] 获取报表样本 ... 成功，共 {n} 条记录")
```

### 验证码检测规范（来自 AC5、FR12）

验证码检测需在**以下两个时机**执行：
1. 登录后（跳转到 dashboard 前或后）
2. 导航至报表页后

关键词列表（大小写不敏感）：`["captcha", "robot", "verify you are human"]`

**必须**：检测到验证码时抛出 `RuntimeError`（含 source 名和中文提示），并在 `finally` 块中关闭浏览器。

### Project Structure Notes

**本 Story 仅涉及以下文件：**
```
outdoor-data-validator/
├── sources/
│   └── partnerboost.py              ← 新建（核心交付）
└── tests/
    ├── fixtures/
    │   └── partnerboost_sample.json ← 新建（测试夹具）
    └── test_partnerboost.py         ← 新建（单元测试）
```

**不触碰：**
- `config/credentials.py`（已有 `PARTNERBOOST_USERNAME`/`PARTNERBOOST_PASSWORD`，Story 1-2 已实现）
- `reporter.py`（Story 1-4 已实现，直接调用即可）
- `validate.py`（Epic 5 职责，不在本 Story 范围）
- `config/field_requirements.yaml`（暂无 partnerboost 字段条目，报告需求区块会显示"暂无配置的需求字段"，属正常情况）
- 其他 `sources/*.py` 文件

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.3: PartnerBoost 爬虫数据源接入] — AC 定义
- [Source: _bmad-output/planning-artifacts/architecture.md#Playwright 爬虫规范] — sync_playwright 模板、超时、异常处理
- [Source: _bmad-output/planning-artifacts/architecture.md#Interface Contract Patterns] — 三函数签名、FieldInfo 结构
- [Source: _bmad-output/planning-artifacts/architecture.md#ARCH10] — sync 模式、15s/60s 超时约定
- [Source: _bmad-output/planning-artifacts/architecture.md#ARCH12] — 测试夹具路径、@pytest.mark.integration 标注
- [Source: _bmad-output/planning-artifacts/architecture.md#Enforcement Guidelines] — 禁用 os.getenv、日志格式等强制要求
- [Source: _bmad-output/docs/api-access-archive.md#7. PartnerBoost] — 登录 URL: https://app.partnerboost.com/login，selectors: input[name=email], input[name=password]
- [Source: _bmad-output/implementation-artifacts/1-4-报告渲染器.md] — reporter.py write_raw_report() 调用方式

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

无阻断性问题，全流程顺利完成。

### Completion Notes List

- 实现 `sources/partnerboost.py`：`authenticate()`、`fetch_sample()`、`extract_fields()` 三函数，严格遵守 ARCH10 sync_playwright 规范，`finally` 块可靠关闭浏览器
- `fetch_sample()` 在登录后及导航报表页后各做一次验证码关键词检测（captcha/robot/verify you are human），检测到时抛 `RuntimeError`
- `extract_fields()` 为纯函数，保持原始键插入顺序，字符串数字值保留为 string 类型（不做隐式转换）
- 新增测试夹具 `tests/fixtures/partnerboost_sample.json`（9 列 PartnerBoost 报表典型数据）
- 新增单元测试 `tests/test_partnerboost.py`（16 个单元测试 + 1 个 integration 测试），全部通过
- 完整回归套件 166 passed，0 failed，0 regressions

### File List

- `sources/partnerboost.py` （新建）
- `tests/fixtures/partnerboost_sample.json` （新建）
- `tests/test_partnerboost.py` （新建）
- `_bmad-output/implementation-artifacts/4-3-partnerboost-爬虫数据源接入.md` （更新：状态、任务完成标记）
- `_bmad-output/implementation-artifacts/sprint-status.yaml` （更新：epic-4 in-progress、4-3 review）
