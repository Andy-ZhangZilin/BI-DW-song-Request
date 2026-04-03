---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
status: 'complete'
completedAt: '2026-04-02'
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/product-brief-outdoor-data-validator.md"
  - "_bmad-output/docs/datasource-api-research-report.md"
  - "_bmad-output/docs/api-access-archive.md"
  - "_bmad-output/docs/credentials.md"
workflowType: 'architecture'
project_name: 'outdoor-data-validator'
user_name: 'dadong'
date: '2026-04-02'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements（30 条，8 类）：**
- 工具运行控制（FR1-3）：CLI 单源/全量运行 + 控制台日志
- 凭证与配置管理（FR4-6）：.env 凭证隔离 + YAML 字段需求配置
- 数据源接入认证（FR7-12）：API Key / OAuth+签名 / Access Token / Playwright 登录，失败需明确报错
- 样本数据抓取（FR13-15）：至少一条真实记录，完整字段输出，需标注样本记录数量作为可信度参考
- 字段对标分析（FR16-20）：自动比对 + 三态标注 + 人工可补注说明；"模糊匹配"算法需在架构层明确定义
- 验证报告生成（FR21-25）：Markdown 输出，统一模板，覆盖更新（⚠️ 人工标注内容保留策略为显式架构决策点）
- 日志与错误处理（FR26-28）：结构化日志，单源失败隔离
- 项目可交接性（FR29-30）：README + requirements.txt 一键复现（含 Playwright 浏览器二进制安装说明）

**Non-Functional Requirements（架构驱动）：**
- 安全性：凭证仅从 .env 读取，日志/报告不暴露完整凭证
- 可靠性：单源失败隔离，幂等运行，爬虫不静默失败
- 可维护性：插件式 source 模块，统一接口契约（含明确的返回值数据结构），新增源无需改核心逻辑
- 性能：单源 60s 内完成（正常网络），全量无硬性限制

**Scale & Complexity：**
- Primary domain：本地 CLI 工具 / API 集成 / 浏览器自动化
- Complexity level：中等
- Estimated architectural components：~13

### Technical Constraints & Dependencies

- 语言：Python 3.x，本地运行，无服务器依赖
- 爬虫引擎：Playwright（需额外执行 `playwright install chromium`，requirements.txt 无法体现，必须在 README 和架构文档中显式说明）
- 特殊技术约束：
  - **TikTok Shop**：HmacSHA256 签名 + 时间戳偏移，shopDomain = piscifun.myshopify.com；授权分两阶段：① 首次人工完成 OAuth 浏览器授权，将 refresh_token 保存到 .env；② 后续每次调用用 refresh_token 自动换取 access_token（不可缓存）
  - **TripleWhale**：SQL API 使用 shopDomain 参数（非 shopId）；多表 schema 差异大（pixel_orders_table / pixel_joined_tvf / sessions_table / product_analytics_tvf），字段对标路由需按数据表名而非仅按数据源名区分，单一 triplewhale.py 模块需内部按表路由
  - **钉钉**：关联字段 API 兼容性风险，公式字段需验证，关联字段可能返回空
  - **爬虫源**：验证码中断机制必须支持手动干预，不静默失败

### Cross-Cutting Concerns Identified

1. **凭证管理层**：统一 .env 加载，模块不直接调用 os.getenv；需区分 TikTok OAuth 两阶段凭证
2. **日志脱敏**：所有 source 日志输出过滤凭证信息（Token、密码、API Key）
3. **统一 source 接口契约**：`authenticate() → fetch_sample() → extract_fields()`，且 `extract_fields()` 返回值结构需统一：
   ```python
   List[{"field_name": str, "data_type": str, "sample_value": Any, "nullable": bool}]
   ```
4. **异常隔离层**：调度器对每个 source 独立 try/except，失败记录不传染
5. **报告模板引擎**：统一渲染逻辑，所有 source 共享同一 Markdown 模板
6. **字段对标算法**：需明确"模糊匹配"的实现方式（字符串相似度 vs 人工映射表），并在报告中标注匹配置信度
7. **抓取完整性**：报告需标注每个数据源的实际样本记录数，作为字段覆盖结论的可信度参考

## Starter Template Evaluation

### Primary Technology Domain

本地 Python CLI 工具 — 无适用的 Web starter 框架。
PRD 已完整定义项目结构，采用手工搭建方式初始化。

### Project Scaffolding Approach

无需第三方 starter，直接按 PRD 定义结构初始化，原因：
1. PRD 已明确完整目录结构和文件命名规范
2. 本项目为一次性内部工具，无需包发布、CI/CD 等额外配置
3. 引入 cookiecutter 等模板会带来不必要的复杂度

### Tool Library Decisions

| 类别 | 选型 | 来源 |
|------|------|------|
| CLI 参数解析 | argparse（标准库） | 零依赖，PRD 示例语法匹配 |
| .env 加载 | python-dotenv | 凭证管理标准方案 |
| HTTP 客户端 | requests | PRD 代码示例已使用 |
| 浏览器自动化 | playwright（Python） | PRD 指定 |
| YAML 读取 | PyYAML | field-requirements.yaml 解析 |
| 日志 | logging（标准库） | 零依赖，满足结构化日志需求 |
| 测试 | pytest | Python 事实标准 |

### 初始化方式

**注意**：Playwright 需额外执行浏览器安装命令，requirements.txt 无法自动处理：

```bash
pip install -r requirements.txt
playwright install chromium  # 必须单独执行
```

**Note:** 项目结构初始化应作为第一个实现故事。

---

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions（阻塞实现）：**
- 字段需求 YAML 组织方式（影响对标引擎核心逻辑）
- 报告覆盖策略（影响人工劳动可持续性）
- TikTok 认证机制（影响可运行性）

**Important Decisions（影响架构）：**
- 字段对标模式（影响报告格式与人工工作流）
- TripleWhale 模块粒度（影响代码组织）
- 凭证加载方式（影响安全性与可维护性）

**Deferred Decisions（Post-MVP）：**
- 字段 AI 辅助分析（验证后根据需要引入）

### 数据架构

**字段需求 YAML 组织方式：按报表分组**

按报表（而非数据源）组织，与《数据表需求》文档结构一一对应：

```yaml
# config/field-requirements.yaml
profit_table:       # 利润表（04-08 截止）
  - display_name: 日期
    source: triplewhale
    table: pixel_orders_table
  - display_name: 销售额
    source: triplewhale
    table: pixel_orders_table
  - display_name: SKU
    source: tiktok
    table: orders
marketing_table:    # 营销表现表（04-20 截止）
  - display_name: 曝光量
    source: triplewhale
    table: pixel_joined_tvf
```

- 每条记录包含：`display_name`（中文需求字段名）、`source`（数据源）、`table`（具体表/端点）
- 不预填 `api_field` — 工具以纯发现模式运行，不做自动中英文映射

**字段对标模式：纯发现模式 + 双列对照报告**

工具不做字段名匹配，只负责"抓取并展示"：
- Raw 报告输出实际返回字段完整列表（字段名、类型、示例值）
- 报告同时展示 YAML 中定义的中文需求字段
- 人工（或后续 AI 辅助）对照两列做结论判断
- 无 fuzzy matching，无置信度算法，避免误导

**报告覆盖策略：双文件**

- `reports/{source}-raw.md`：每次运行完全覆盖，记录最新实际字段
- `reports/{source}-validation.md`：人工维护，记录对标结论，工具不覆盖
- 职责分离：工具负责发现，人负责判断

### Authentication & Security

**凭证加载方式：统一加载器**

- `config/credentials.py` 统一从 `.env` 读取所有凭证
- 各 source 模块从 `credentials` 模块导入，不直接调用 `os.getenv`
- 凭证校验集中处理：缺失时在启动阶段统一报错，不在运行时抛异常
- 日志脱敏过滤器只需在 `credentials.py` 层统一实现

**TikTok Shop 认证：refresh_token 自动刷新（无浏览器授权）**

- DTC Hub 已有 `access_token` + `refresh_token`，手动填入 `.env`
- 脚本每次调用前自动用 `refresh_token` 换取新 `access_token`（HmacSHA256 签名）
- 无需浏览器 OAuth 初始授权流程，完全脚本化
- `shop_cipher` 通过 `/api/shops/get_authorized_shop` 自动获取

### API & Communication Patterns

**数据源接入方式汇总（修正版）：**

| # | 数据源 | 接入方式 | 认证 |
|---|--------|---------|------|
| 1 | TripleWhale | REST API（SQL endpoint） | API Key（X-API-KEY header） |
| 2 | TikTok Shop | REST API | refresh_token → access_token + HmacSHA256 签名 |
| 3 | 钉钉 Bitable | REST API | AppKey + AppSecret → Access Token |
| 4 | YouTube | REST API | API Key |
| 5 | CartSee | Playwright 爬虫 | 账号密码登录 |
| 6 | Awin | Playwright 爬虫 | 账号密码登录 |
| 7 | PartnerBoost | Playwright 爬虫 | 账号密码登录 |
| 8 | 社媒后台 | Playwright 爬虫（待跟进） | 账号密码（待获取） |

**错误处理标准：**
- 格式：`[{source}] {操作描述} ... 成功/失败`
- 单源失败：记录完整错误信息，继续执行下一个 source，退出码 ≠ 0
- 爬虫验证码：中断执行，打印提示，不静默失败

### 模块架构

**TripleWhale 模块粒度：单文件按表路由**

`sources/triplewhale.py` 内部根据 `table_name` 参数路由，保持 8 模块结构：

```python
def fetch_sample(table_name: str) -> List[dict]:
    if table_name == "pixel_orders_table": ...
    elif table_name == "pixel_joined_tvf": ...
    elif table_name == "sessions_table": ...
    elif table_name == "product_analytics_tvf": ...
```

**统一 source 接口契约：**

```python
def authenticate() -> bool
def fetch_sample(table_name: str = None) -> List[dict]
def extract_fields(sample: List[dict]) -> List[FieldInfo]

# FieldInfo 标准结构
{"field_name": str, "data_type": str, "sample_value": Any, "nullable": bool}
```

### Infrastructure & Deployment

- 本地运行，无部署需求
- 依赖管理：`requirements.txt`（pip install）+ `playwright install chromium`（单独执行）
- 环境配置：`.env`（不提交 git）+ `.env.example`（模板，提交 git）
- 无 CI/CD，无容器化需求

### Decision Impact Analysis

**实现顺序建议：**
1. 项目结构初始化 + `config/credentials.py` + `.env.example`
2. `config/field-requirements.yaml` 基础结构（利润表相关字段）
3. TripleWhale source 模块（优先级最高，覆盖利润表 + 营销表现表）
4. TikTok Shop source 模块（利润表 + TikTok 销售表）
5. 钉钉 Bitable source 模块
6. YouTube source 模块
7. 爬虫源（Awin / CartSee / PartnerBoost）
8. 报告渲染器 + validate.py 统一入口
9. 社媒后台（待凭证就绪）

**跨组件依赖：**
- `credentials.py` 是所有 source 模块的前置依赖
- `field-requirements.yaml` 结构决定报告渲染器的输入格式
- Raw 报告格式决定 validation.md 的人工填写模板设计

---

### Open Architecture Decision Points（已全部决策，见 Core Architectural Decisions）

---

## Implementation Patterns & Consistency Rules

### 潜在冲突点识别

共识别 6 类 AI 实现可能产生冲突的区域：命名、文件结构、接口契约、日志格式、错误处理、爬虫实现模式。

### Naming Patterns

**Python 命名规范：**

| 类别 | 规范 | 示例 |
|------|------|------|
| 文件/模块 | snake_case | `triplewhale.py`, `field_matcher.py` |
| 类 | PascalCase | `TripleWhaleSource`, `FieldReport` |
| 函数/方法 | snake_case | `fetch_sample()`, `extract_fields()` |
| 变量 | snake_case | `table_name`, `field_list` |
| 常量 | UPPER_SNAKE_CASE | `DEFAULT_TIMEOUT = 60` |
| .env 变量 | UPPER_SNAKE_CASE | `TRIPLEWHALE_API_KEY` |
| 私有方法 | 单下划线前缀 | `_sign_request()`, `_load_token()` |

**报告文件命名：**
- Raw 报告：`reports/{source}-raw.md`（如 `triplewhale-raw.md`）
- 验证报告：`reports/{source}-validation.md`
- source 名与 `sources/` 目录下模块文件名一致（不含 `.py`）

### Structure Patterns

**目录结构规范（每个 source 模块的职责边界）：**

```
sources/
  {source}.py       # 每个 source 一个文件，内含三个公开函数
config/
  credentials.py    # 唯一凭证加载入口，各模块从此导入
  field_requirements.yaml
reports/            # 仅由工具写入，不手动修改 raw 报告
tests/
  test_{source}.py  # 测试文件与 source 模块同名
```

**禁止行为：**
- ❌ source 模块内直接调用 `os.getenv()`
- ❌ source 模块内不通过 credentials.py 获取凭证
- ❌ 在 `reports/` 之外写入报告文件
- ❌ `validate.py` 以外的入口执行验证逻辑

### Interface Contract Patterns

**所有 source 模块必须实现的三个函数（统一签名）：**

```python
def authenticate() -> bool:
    """验证凭证是否有效。成功返回 True，失败打印错误并返回 False。"""
    ...

def fetch_sample(table_name: str = None) -> list[dict]:
    """抓取至少一条样本记录。返回原始记录列表，失败抛出异常。"""
    ...

def extract_fields(sample: list[dict]) -> list[dict]:
    """从样本中提取字段信息。返回标准 FieldInfo 列表。"""
    ...
```

**FieldInfo 标准结构（所有 source 必须遵守）：**

```python
{
    "field_name": str,      # 字段名（API 返回的原始名称）
    "data_type": str,       # 类型：string / number / boolean / array / object / null
    "sample_value": any,    # 示例值（脱敏处理，不含凭证信息）
    "nullable": bool        # 是否可为空
}
```

### Format Patterns

**日志格式（所有模块统一）：**

```python
# 格式：[{source}] {操作描述} ... 成功/失败
import logging
logger = logging.getLogger(__name__)

logger.info("[triplewhale] 获取 pixel_orders_table 样本 ... 成功")
logger.error("[tiktok] 认证 ... 失败：Invalid access_token")
```

**日志脱敏规则：**
- 禁止在日志中输出 API Key、Token、密码的完整值
- 如需展示，只显示前 4 位：`key[:4] + "****"`

**Raw 报告 Markdown 格式（统一模板）：**

```markdown
# {Source} 字段验证报告（Raw）

**生成时间：** {datetime}
**数据表：** {table_name}
**样本记录数：** {count}

## 实际返回字段

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| {field_name} | {type} | {sample} | {nullable} |

## 需求字段（待人工对照）

| 需求字段（中文） | 报表 | 对照结果 |
|----------------|------|---------|
| {display_name} | {report} | ⬜ 待确认 |
```

### Process Patterns

**错误处理规范（调度器层）：**

```python
for source_name, source_module in sources.items():
    try:
        ok = source_module.authenticate()
        if not ok:
            results[source_name] = "认证失败"
            continue
        sample = source_module.fetch_sample(table_name)
        fields = source_module.extract_fields(sample)
        results[source_name] = "成功"
    except Exception as e:
        logger.error(f"[{source_name}] 执行失败：{e}")
        results[source_name] = f"失败：{e}"

sys.exit(0 if all(v == "成功" for v in results.values()) else 1)
```

**Playwright 爬虫规范（同步模式）：**

```python
from playwright.sync_api import sync_playwright

def fetch_sample(table_name: str = None) -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            ...
        except Exception as e:
            if "验证码" in str(e) or "captcha" in str(e).lower():
                raise RuntimeError(
                    f"[{SOURCE_NAME}] 遇到验证码，请手动完成验证后重新运行"
                )
            raise
        finally:
            browser.close()
```

**超时规范：**
- HTTP 请求：`requests.get(url, timeout=30)`（统一 30s）
- Playwright 页面等待：`page.wait_for_selector(..., timeout=15000)`（15s）
- 单 source 整体超时：60s

### Enforcement Guidelines

**所有 AI Agent 实现时 MUST：**

1. source 模块只暴露 `authenticate()`、`fetch_sample()`、`extract_fields()` 三个公开函数
2. 凭证统一从 `config.credentials` 导入，不直接读取环境变量
3. 日志格式严格遵守 `[{source}] {操作} ... 成功/失败`
4. FieldInfo 结构使用规定的四字段格式
5. Playwright 使用 `sync_playwright`，不使用 async 版本
6. 报告写入路径固定为 `reports/{source}-raw.md`
7. 所有函数必须有类型注解
8. 字符串格式化使用 f-string

**Anti-Patterns（禁止）：**

```python
# ❌ 直接读取环境变量
api_key = os.getenv("TRIPLEWHALE_API_KEY")

# ✅ 从统一加载器导入
from config.credentials import TRIPLEWHALE_API_KEY

# ❌ 爬虫静默失败
except Exception:
    pass

# ✅ 爬虫明确报错
except Exception as e:
    raise RuntimeError(f"[awin] 爬虫异常：{e}")

---

## Project Structure & Boundaries

### 完整项目目录结构

```
outdoor-data-validator/
├── validate.py                        # 统一入口：CLI 解析 + 调度器（FR1-3）
├── reporter.py                        # 报告渲染器：raw.md 写入 + validation.md 首次创建（FR21-25）
├── requirements.txt                   # 依赖声明（FR30）
├── .env                               # 凭证文件（不提交 Git）
├── .env.example                       # 凭证模板（FR5）
├── .gitignore                         # 排除 .env / __pycache__
├── README.md                          # 运行说明 + Playwright 安装步骤（FR29）
│
├── config/
│   ├── __init__.py
│   ├── credentials.py                 # 凭证加载器，暴露 get_credentials() 函数（FR4）
│   └── field_requirements.yaml       # 字段需求配置，按报表分组（FR6，下划线命名）
│
├── sources/
│   ├── __init__.py
│   ├── triplewhale.py                 # TripleWhale SQL API（FR7，4 表内部路由）
│   ├── tiktok.py                      # TikTok Shop OAuth+HmacSHA256（FR8）
│   ├── dingtalk.py                    # 钉钉多维表 Access Token（FR9）
│   ├── youtube.py                     # YouTube Data API v3（FR7）
│   ├── awin.py                        # Awin Playwright 爬虫（FR10）
│   ├── cartsee.py                     # CartSee Playwright 爬虫（FR10）
│   ├── partnerboost.py                # PartnerBoost Playwright 爬虫（FR10）
│   └── social_media.py                # 社媒后台 stub（raise NotImplementedError，待凭证就绪）
│
├── reports/                           # 报告输出目录（FR21-25）
│   ├── triplewhale-raw.md             # 每次运行覆盖（reporter.py 写入）
│   ├── triplewhale-validation.md      # 首次由 reporter.py 创建模板，后续不覆盖（人工维护）
│   ├── tiktok-raw.md
│   ├── tiktok-validation.md
│   ├── dingtalk-raw.md
│   ├── dingtalk-validation.md
│   ├── youtube-raw.md
│   ├── youtube-validation.md
│   ├── awin-raw.md
│   ├── awin-validation.md
│   ├── cartsee-raw.md
│   ├── cartsee-validation.md
│   ├── partnerboost-raw.md
│   ├── partnerboost-validation.md
│   ├── social_media-raw.md
│   └── social_media-validation.md
│
└── tests/
    ├── __init__.py
    ├── conftest.py                     # pytest fixtures，统一 patch get_credentials()
    ├── fixtures/                       # API 响应样本（JSON），供 mock 使用
    │   ├── triplewhale_sample.json
    │   ├── tiktok_sample.json
    │   ├── dingtalk_sample.json
    │   ├── youtube_sample.json
    │   ├── awin_sample.json
    │   ├── cartsee_sample.json
    │   └── partnerboost_sample.json
    ├── test_triplewhale.py             # 单元测试（mock get_credentials + fixture）
    ├── test_tiktok.py
    ├── test_dingtalk.py
    ├── test_youtube.py
    ├── test_awin.py                    # 仅测试 extract_fields()，fetch_sample 标注集成测试
    ├── test_cartsee.py
    ├── test_partnerboost.py
    └── test_social_media.py           # 仅验证 NotImplementedError 正确抛出
```

### Architectural Boundaries

**外部 API 边界：**

| 模块 | 外部端点 | 认证边界 |
|------|---------|---------|
| `triplewhale.py` | `api.triplewhale.com/api/v2/tw-metrics/*` | `get_credentials()["TRIPLEWHALE_API_KEY"]` → X-API-KEY header |
| `tiktok.py` | TikTok Shop Open Platform API | `get_credentials()["TIKTOK_REFRESH_TOKEN"]` → 每次调用前换取 access_token |
| `dingtalk.py` | 钉钉开放平台 API | `get_credentials()["DINGTALK_APP_KEY/SECRET"]` → access_token |
| `youtube.py` | YouTube Data API v3 | `get_credentials()["YOUTUBE_API_KEY"]` |

**爬虫边界：**

| 模块 | 目标站点 | 浏览器边界 |
|------|---------|-----------|
| `awin.py` | Awin 联盟后台 | sync_playwright，headless，账号密码登录 |
| `cartsee.py` | CartSee EDM 后台 | sync_playwright，headless，账号密码登录 |
| `partnerboost.py` | PartnerBoost 后台 | sync_playwright，headless，账号密码登录 |
| `social_media.py` | 待定 | raise NotImplementedError（凭证就绪后实现）|

**组件边界（内部数据流）：**

```
validate.py（CLI 解析 + 调度）
  ├─ 启动阶段 → config/credentials.py → get_credentials()（集中校验，缺失则快速失败）
  ├─ 读取 → config/field_requirements.yaml（字段需求，供 reporter.py 渲染）
  ├─ 调度循环 → sources/{source}.py
  │     authenticate() → bool
  │     fetch_sample(table_name) → List[dict]
  │     extract_fields(sample) → List[FieldInfo]
  └─ 渲染 → reporter.py
        write_raw_report()         → reports/{source}-raw.md（每次覆盖）
        init_validation_report()   → reports/{source}-validation.md（仅首次创建）
```

**凭证隔离边界：**
- `credentials.py` 是唯一允许读取 `.env` 的位置
- 所有 source 模块：`from config.credentials import get_credentials`
- 测试 mock：`@patch("config.credentials.get_credentials", return_value={...})`
- 日志脱敏：凭证值仅显示 `key[:4] + "****"`

### Requirements to Structure Mapping

**FR 类别 → 文件对应：**

| FR 类别 | FR 编号 | 实现位置 |
|---------|--------|---------|
| 工具运行控制 | FR1-3 | `validate.py`（argparse + 调度循环 + logging） |
| 凭证与配置管理 | FR4-6 | `config/credentials.py`、`.env.example`、`config/field_requirements.yaml` |
| 数据源接入认证 | FR7-12 | `sources/{source}.py::authenticate()` |
| 样本数据抓取 | FR13-15 | `sources/{source}.py::fetch_sample()` + `extract_fields()` |
| 字段对标分析 | FR16-20 | `reporter.py` 双列渲染（实际字段 + 需求字段）|
| 验证报告生成 | FR21-25 | `reporter.py` + `reports/` 目录 |
| 日志与错误处理 | FR26-28 | `validate.py` 调度器 try/except + 各模块 logger |
| 项目可交接性 | FR29-30 | `README.md`、`requirements.txt` |

**横切关注点 → 位置：**

| 关注点 | 实现位置 |
|--------|---------|
| 凭证安全 | `credentials.py::get_credentials()` + `.gitignore` |
| 日志脱敏 | 各模块 logger 调用点手动掩码 |
| 异常隔离 | `validate.py` 调度器独立 try/except |
| Playwright 安装 | `README.md` 显式说明 `playwright install chromium` |
| 验证码中断 | 各爬虫 `fetch_sample()` 检测并 raise RuntimeError |
| stub 模块 | `social_media.py` 所有函数 raise NotImplementedError |
| validation.md 保护 | `reporter.py` 用 `Path.exists()` 判断首次创建 |

### Integration Points

**内部数据流：**

```
CLI 参数（--source / --all）
  → validate.py 解析
  → get_credentials() 校验凭证完整性（启动失败快）
  → field_requirements.yaml 加载字段需求
  → for each source:
      authenticate() → True/False
      fetch_sample(table_name) → List[dict]（原始记录）
      extract_fields(sample) → List[FieldInfo]（标准字段结构）
      reporter.write_raw_report()（每次覆盖）
      reporter.init_validation_report()（仅首次）
  → 控制台汇总日志 + 退出码
```

**外部集成点：**

| 集成点 | 位置 | 特殊处理 |
|--------|------|---------|
| TripleWhale SQL API | `triplewhale.py` | shopDomain=piscifun.myshopify.com，4 表内部路由 |
| TikTok refresh_token 换取 | `tiktok.py::_load_token()` | HmacSHA256 签名，时间戳略靠前偏移，每次重新获取 |
| 钉钉 Access Token | `dingtalk.py::_load_token()` | AppKey+AppSecret，token 有效期内可复用 |
| YouTube API Key | `youtube.py` | 直接 header 传入，无动态刷新 |
| Playwright Chromium | 爬虫模块 | 系统级安装，`playwright install chromium` |

### File Organization Patterns

**配置文件：**
- `.env`：本机凭证，不提交 Git
- `.env.example`：模板，提交 Git，列出所有必填凭证键名
- `config/field_requirements.yaml`：字段需求，按报表分组，可不改代码直接更新
- `requirements.txt`：`python-dotenv requests playwright PyYAML pytest`

**测试组织：**
- `tests/conftest.py`：全局 fixture，`mock_credentials` patch `get_credentials()`
- `tests/fixtures/*.json`：各数据源 API 响应样本，测试用
- 爬虫模块：unit test 仅覆盖 `extract_fields()`；`fetch_sample()` 标注 `@pytest.mark.integration`
- `test_social_media.py`：仅验证三个接口均抛出 `NotImplementedError`

---

## Architecture Validation Results

### 完整性检查清单

**需求分析：**
- [x] 项目上下文深度分析（8 数据源 × 多报表，特殊约束全记录）
- [x] 规模与复杂度评估（中等，~13 架构组件）
- [x] 技术约束识别（TikTok 签名、TripleWhale shopDomain、钉钉关联字段、Playwright 二进制）
- [x] 横切关注点映射（凭证管理、日志脱敏、异常隔离、接口契约、报告模板）

**架构决策：**
- [x] 关键决策文档化（YAML 组织方式、报告覆盖策略、TikTok 认证、字段对标模式）
- [x] 技术栈完整指定（Python 3.x + requests + playwright + python-dotenv + PyYAML）
- [x] 集成模式定义（API Key / OAuth+签名 / Access Token / Playwright 爬虫）
- [x] 性能约束处理（HTTP 30s / Playwright 15s / 单源 60s）

**实现模式：**
- [x] 命名约定建立（文件/类/函数/变量/常量/私有方法全覆盖）
- [x] 结构模式定义（目录边界、禁止行为、职责边界）
- [x] 接口契约规范（三函数签名 + FieldInfo 四字段结构）
- [x] 过程模式文档化（错误处理代码示例、爬虫规范、超时规范）

**项目结构：**
- [x] 完整目录树定义（含 tests/fixtures/，共 ~35 个文件）
- [x] 组件边界建立（validate.py / reporter.py / credentials.py / sources/* 职责分离）
- [x] 集成点映射（外部 API 边界 + 爬虫边界 + 内部数据流）
- [x] 需求到结构映射完整（FR1-30 全部对应到具体文件）

### 差距分析结果

**次要差距（不阻塞实现）：**

| # | 差距 | 处理方式 |
|---|------|---------|
| 1 | `get_credentials()` 返回键名清单未枚举 | 在 credentials.py 实现故事中定义，与 .env.example 对齐 |
| 2 | TikTok 时间戳偏移量具体秒数未量化 | 在 tiktok.py 实现故事中参照 Java 文档确认 |
| 3 | field_requirements.yaml 中 `table` 字段对非 SQL 源是否可选未说明 | 实现时标注为 Optional，None 表示无表路由 |

### 架构就绪性评估

**整体状态：** READY FOR IMPLEMENTATION

**置信度：** 高 — 所有关键决策已达成共识，无阻塞性开放问题

**关键优势：**
- 插件式架构保证新增数据源零改核心逻辑
- 双文件报告策略（raw 自动覆盖 + validation 首次创建）保护人工标注成果
- `get_credentials()` 统一加载层简化测试 mock，patch 路径唯一
- Enforcement Guidelines + Anti-Patterns 明确列出，确保 AI Agent 实现一致性
- reporter.py 抽离报告渲染，validate.py 保持单一职责

**后续关注点（非阻塞）：**
- TikTok 时间戳偏移量在实现故事中参照 Java 文档确认具体数值
- field_requirements.yaml `table` 字段对非 SQL 数据源标注为 Optional
- requirements.txt 在全部实现完成后 pip freeze 固定版本号

### Implementation Handoff

**AI Agent 实施指引：**
- 严格遵循三函数接口契约：`authenticate()` / `fetch_sample()` / `extract_fields()`
- 凭证仅通过 `get_credentials()` 获取，禁止直接调用 `os.getenv()`
- 日志格式严格遵守 `[{source}] 操作描述 ... 成功/失败`
- Playwright 使用 `sync_playwright`，禁止 async 版本
- 报告写入路径固定：raw → `reports/{source}-raw.md`，validation → 首次创建后不覆盖
- 所有函数必须有类型注解，字符串格式化使用 f-string

**推荐实现顺序：**
1. 项目结构初始化 + `config/credentials.py` + `.env.example`（凭证框架优先）
2. `config/field_requirements.yaml` 基础内容（利润表相关字段）
3. `reporter.py` 报告渲染器（raw 写入 + validation 首次创建）
4. `sources/triplewhale.py`（优先级最高，覆盖利润表 + 营销表现表）
5. `sources/tiktok.py`（利润表 + TikTok 销售表）
6. `sources/dingtalk.py`（营销表现表）
7. `sources/youtube.py`
8. `validate.py` 统一入口（调度器 + CLI）
9. 爬虫源（`awin.py` / `cartsee.py` / `partnerboost.py`）
10. `sources/social_media.py` stub
