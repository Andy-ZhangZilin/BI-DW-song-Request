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
- （已提前实现）字段 AI 辅助分析 — 聚合文档内嵌 AI 分析提示语，指导 AI 完成字段映射

### 数据架构

**字段需求 YAML 组织方式：按报表分组（reports 列表结构）**

按报表（而非数据源）组织，与《数据表需求》文档结构一一对应：

```yaml
# config/field_requirements.yaml
reports:
  - report_name: 利润表
    dashboard: 销售表现、利润表
    deadline: "2026-04-08"
    launch_date: "2026-04-24"
    notes: 费用科目需要到四级
    fields:
      - 日期
      - 渠道
      - 店铺
      - 销售额
      # ...共 9 个字段
  - report_name: 营销表现表
    dashboard: 营销表现表
    deadline: "2026-04-20"
    launch_date: "2026-04-24"
    fields:
      - 日期
      - 渠道
      - 曝光量
      # ...共 11 个字段
  # ...共 11 张报表
```

- 每张报表包含：`report_name`（中文报表名）、`fields`（字段名列表，纯字符串）
- 可选属性：`dashboard`、`deadline`、`launch_date`、`notes`
- 字段不绑定数据源——由聚合文档的 AI 分析提示语驱动映射

**字段对标模式：纯发现模式 + AI 辅助分析**

工具不做字段名匹配，只负责"抓取并展示"：
- Raw 报告仅输出实际返回字段完整列表（字段名、类型、示例值、可空性）
- 不在 raw 报告中展示需求字段对照（已移除）
- `--all` 模式生成聚合结论文档，内嵌 AI 分析提示语，由 AI 完成字段映射分析

**报告覆盖策略：raw + aggregate**

- `reports/{source}-raw.md`：每次运行完全覆盖，记录最新实际字段
- `reports/all-sources-aggregate.md`：`--all` 模式生成，包含 4 部分（采集状态汇总 + 字段清单汇编 + 报表映射模板 + AI 分析提示语），每次覆盖更新
- 已废弃：`{source}-validation.md` 双文件策略及 `init_validation_report()` 函数

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
- 聚合文档：`reports/all-sources-aggregate.md`（`--all` 模式生成）
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
```

> 注意：raw 报告仅包含实际返回字段，不再包含"需求字段（待人工对照）"区块。
> 字段映射分析由 `--all` 模式生成的聚合结论文档（`all-sources-aggregate.md`）中的 AI 分析提示语驱动。

**聚合结论文档格式（`--all` 模式生成）：**

```markdown
# 数据源字段验证 — 聚合结论文档
## Part 1: 数据源采集状态汇总（表格：数据源/状态/错误信息）
## Part 2: 各数据源实际字段清单汇编
## Part 3: 11 张报表字段映射模板（字段 × 数据源映射）
## Part 4: AI 分析提示语（指导 AI 完成字段映射分析）
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
├── reporter.py                        # 报告渲染器：raw.md 写入 + aggregate.md 聚合文档生成（FR21-25）
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
│   ├── youtube_url.py                 # YouTube URL 解析数据源
│   ├── awin.py                        # Awin REST API（FR10）
│   ├── cartsee.py                     # CartSee Playwright 爬虫（FR10）
│   ├── partnerboost.py                # PartnerBoost Playwright 爬虫（FR10）
│   ├── social_media.py                # Facebook Business Suite Playwright 爬虫
│   └── youtube_studio.py              # YouTube Studio Playwright 爬虫
│
├── reports/                           # 报告输出目录（FR21-25）
│   ├── triplewhale-raw.md             # 每次运行覆盖（reporter.py 写入）
│   ├── tiktok-raw.md
│   ├── dingtalk-raw.md
│   ├── youtube-raw.md
│   ├── youtube_url-raw.md
│   ├── awin-raw.md
│   ├── cartsee-raw.md
│   ├── partnerboost-raw.md
│   ├── social_media-raw.md
│   ├── youtube_studio-raw.md
│   └── all-sources-aggregate.md       # --all 模式生成的聚合结论文档（覆盖更新）
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
  ├─ 读取 → config/field_requirements.yaml（字段需求，供聚合文档渲染）
  ├─ 调度循环 → sources/{source}.py
  │     authenticate() → bool
  │     fetch_sample(table_name) → List[dict]
  │     extract_fields(sample) → List[FieldInfo]
  │     _run_source() 返回 Dict: {success, status, error, fields}
  ├─ 渲染 → reporter.py
  │     write_raw_report()         → reports/{source}-raw.md（每次覆盖）
  └─ --all 模式 → reporter.py
        write_aggregate_report()   → reports/all-sources-aggregate.md（覆盖更新）
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
| 聚合文档生成 | `reporter.py::write_aggregate_report()` — `--all` 模式覆盖更新 |

### Integration Points

**内部数据流：**

```
CLI 参数（--source / --all）
  → validate.py 解析
  → get_credentials() 校验凭证完整性（启动失败快）
  → for each source:
      authenticate() → True/False
      fetch_sample(table_name) → List[dict]（原始记录）
      extract_fields(sample) → List[FieldInfo]（标准字段结构）
      reporter.write_raw_report()（每次覆盖）
      → 收集 source_results: Dict[str, Dict]（成功/失败/字段数据）
  → if --all: reporter.write_aggregate_report(source_results)
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
- raw + aggregate 报告策略（raw 自动覆盖 + --all 生成聚合文档含 AI 分析提示语）
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
- 报告写入路径固定：raw → `reports/{source}-raw.md`，聚合 → `reports/all-sources-aggregate.md`（`--all` 模式覆盖更新）
- 所有函数必须有类型注解，字符串格式化使用 f-string

**推荐实现顺序：**
1. 项目结构初始化 + `config/credentials.py` + `.env.example`（凭证框架优先）
2. `config/field_requirements.yaml` 完整内容（全部 11 张数据表字段，来源：《指标梳理及数据需求沟通-2026.03.31.xlsx》）
3. `reporter.py` 报告渲染器（raw 写入 + validation 首次创建）
4. `sources/triplewhale.py`（优先级最高，覆盖利润表 + 营销表现表）
5. `sources/tiktok.py`（利润表 + TikTok 销售表）
6. `sources/dingtalk.py`（营销表现表）
7. `sources/youtube.py`
8. `validate.py` 统一入口（调度器 + CLI）
9. 爬虫源（`awin.py` / `cartsee.py` / `partnerboost.py`）

---

## Phase 2 Architecture — 数据采集与落库

> **版本记录：** 本章节由 CC Phase2（2026-04-15）新增，Phase 1 架构全部保持不变。

### Phase 2 整体架构

**代码位置：** `bi/python_sdk/outdoor_collector/`（独立部署单元，与主工具无依赖）

**调用关系：**

```
海豚调度（DolphinScheduler）
    ↓ 执行脚本
collectors/{source}_collector.py
    ↓ 调用 SDK 客户端
sdk/{source}/client.py  →  外部 API
    ↓
common/doris_writer.py  →  Apache Doris (pymysql)
    ↑
common/watermark.py   （水位线读写）
common/chunked_fetch.py（分片并发，大表使用）
```

**核心设计原则：**
- collectors 层只含业务逻辑，认证/HTTP 细节全部封装在 SDK 层
- 公共工具（水位线、分片、写入）集中在 common/ 层，不在 collectors 中重复实现
- 各 collector 独立运行，互不干扰，单个失败不传染其他

### 目录结构

```
bi/python_sdk/outdoor_collector/
├── doris_config.py              # Doris 连接单例（与现有各目录模式一致，自含）
├── sdk/                         # API 客户端层
│   ├── __init__.py
│   ├── tiktok/
│   │   ├── __init__.py
│   │   ├── auth.py              # refresh_token 换取 access_token、HmacSHA256 签名、shop_cipher 获取
│   │   └── client.py            # TikTokClient 类，接口方法封装（订单、商品、财务等）
│   ├── triplewhale/
│   │   ├── __init__.py
│   │   ├── auth.py              # API Key 认证（X-API-KEY header）
│   │   └── client.py            # TripleWhaleClient 类，GraphQL/REST 请求封装、表路由
│   └── dingtalk/
│       ├── __init__.py
│       ├── auth.py              # app_key/secret → access_token 获取与有效期内复用
│       └── client.py            # DingTalkClient 类，Bitable 记录分页读取
├── common/                      # 采集基础设施
│   ├── __init__.py
│   ├── watermark.py             # 水位线管理（读取 / 更新 etl_watermark 表）
│   ├── chunked_fetch.py         # 分片并发框架
│   └── doris_writer.py          # upsert 写入封装
├── collectors/                  # 各数据源采集脚本
│   ├── tw_collector.py          # TripleWhale（Story 7.1）
│   ├── tiktok_collector.py      # TikTok Shop（Story 7.2）
│   ├── dingtalk_collector.py    # 钉钉 Bitable（Story 7.3）
│   ├── youtube_collector.py     # YouTube 统计（Story 7.4，依赖 7.3 完成）
│   ├── awin_collector.py        # Awin 联盟 API（Story 7.5）
│   └── partnerboost_collector.py # PartnerBoost 爬虫（Story 8.2）
└── requirements.txt             # 独立依赖列表
```

### SDK 层设计

**设计原则：** 每个 SDK 客户端隐藏认证细节，向 collector 暴露业务方法。

#### TikTokClient

```python
class TikTokClient:
    def __init__(self):
        # 从 .env 读取 app_key, app_secret, refresh_token, shop_id
        ...

    def _refresh_access_token(self) -> str:
        """每次调用前重新获取，不缓存。使用 HmacSHA256 签名。"""

    def _get_shop_cipher(self) -> str:
        """通过 /api/shops/get_authorized_shop 自动获取。"""

    def get_orders(self, start_time: int, end_time: int) -> list[dict]:
        ...

    # 其他接口方法（商品、财务等）
```

**关键约束（继承自 Phase 1 验证结论）：**
- TikTok access_token **每次重新获取，不可缓存**
- 签名时间戳需使用略靠前的时间（参照 Java 历史实现偏移处理）

#### TripleWhaleClient

```python
class TripleWhaleClient:
    def __init__(self):
        # 从 .env 读取 api_key，shopDomain = piscifun.myshopify.com

    def query_table(self, table_name: str, start_date: str, end_date: str) -> list[dict]:
        """按表名路由，内部区分 pixel_orders_table / sessions_table 等。"""
```

#### DingTalkClient

```python
class DingTalkClient:
    def __init__(self):
        # 从 .env 读取 app_key, app_secret
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    def _get_access_token(self) -> str:
        """有效期内复用，到期重新获取，避免重复换取。"""

    def get_bitable_records(self, space_id: str, sheet_id: str, page_token: str = None) -> list[dict]:
        """分页读取 Bitable 记录。"""
```

**凭证加载规范：** SDK 层全部从 `.env` 加载（`python-dotenv`），不从主工具的 `config/credentials.py` 导入（两个独立模块，互不依赖）。

### Doris 写入封装

```python
# common/doris_writer.py

def write_to_doris(
    table: str,
    records: list[dict],
    unique_keys: list[str],
    batch_size: int = 1000
) -> int:
    """
    幂等 upsert 写入。
    返回写入行数。
    """
    conn = DorisConfig().get_connection()
    cursor = conn.cursor()
    # 写入前设置 Doris upsert 参数
    cursor.execute("SET enable_unique_key_partial_update = true")
    cursor.execute("SET enable_insert_strict = false")
    # 分 batch 写入，使用 executemany
    ...
```

**日志格式：** `[{source}][{table}] 写入 {n} 行 ... 成功/失败`

### 水位线机制

**etl_watermark 表结构（Doris Unique Key 模型）：**

```sql
CREATE TABLE etl_watermark (
    source          VARCHAR(64)   NOT NULL,
    table_name      VARCHAR(128)  NOT NULL,
    last_success_time DATETIME,
    run_mode        VARCHAR(16),      -- 'full' | 'incremental'
    updated_at      DATETIME,
    -- 分片字段（Story 6.3 新增）
    chunk_start     DATE,
    chunk_end       DATE,
    chunk_status    VARCHAR(16)       -- 'pending' | 'done' | 'failed'
) UNIQUE KEY (source, table_name);
```

**水位线接口：**

```python
# common/watermark.py

def get_watermark(source: str, table: str) -> dict | None:
    """返回水位线记录，无记录时返回 None（触发全量）。"""

def update_watermark(source: str, table: str, success_time: datetime) -> None:
    """仅在成功写入 Doris 后调用，失败时不更新。"""

def reset_watermark(source: str, table: str) -> None:
    """--mode full 参数触发，强制重置水位线。"""
```

**运行模式判断逻辑：**

```python
wm = get_watermark(source, table)
if wm is None or mode == "full":
    # 全量拉取（mode full 时先 reset_watermark）
    start_date = EARLIEST_DATE
else:
    # 增量拉取
    start_date = wm["last_success_time"]
```

### 分片并发框架

适用场景：TripleWhale `sessions_table` 等千万级数据量的历史全量拉取。

```python
# common/chunked_fetch.py

def chunked_fetch(
    source: str,
    table: str,
    fetch_fn: Callable[[str, str], list[dict]],  # (start_date, end_date) -> records
    start: date,
    end: date,
    chunk_days: int = 30,
    workers: int = 4
) -> int:
    """
    将 [start, end] 按 chunk_days 分片，使用 ThreadPoolExecutor 并发执行。
    每个分片独立维护 chunk_status（pending/done/failed）。
    重启时跳过 done 分片，仅重跑 pending/failed。
    返回总写入行数。
    """
```

**并发约束：**
- 默认 `workers=4`，受 API Rate Limit 约束，调用方可按数据源调整
- 单片失败记录 `failed` 状态并打印完整错误，不影响其他分片

### Phase 2 技术决策汇总

| # | 决策点 | 结论 |
|---|--------|------|
| 1 | 调度机制 | 海豚调度（DolphinScheduler），直接调用脚本路径 |
| 2 | Doris 连接 | pymysql 直连，沿用 `doris_config.py` 单例模式 |
| 3 | SDK 复用范围 | tiktok / triplewhale / dingtalk 三个客户端，collector 不重复实现认证 |
| 4 | YouTube 数据来源 | 从 Doris 已入库钉钉表读取 URL，依赖 Story 7.3 先完成 |
| 5 | CartSee | 暂缓（页面结构变更），Story 8.1 保留占位，不进入当前排期 |
| 6 | 部署方式 | `outdoor_collector/` 整目录 rsync，自含依赖，无需额外 pip install 内部 SDK |
| 7 | `doris_config.py` | 各业务目录自含副本（与现有模式一致），不共享单一实例跨目录 |

### Phase 2 实现顺序

```
Story 6.0（SDK 层：tiktok / triplewhale / dingtalk 客户端）
    ↓
Story 6.1（目录初始化 + doris_writer.py 写入封装）
    ↓
Story 6.2（watermark.py 水位线管理器）
    ↓
Story 6.3（chunked_fetch.py 分片并发框架）
    ↓
Story 7.1（TripleWhale 采集）→ Story 7.2（TikTok 采集）→ Story 7.3（钉钉采集）
    ↓
Story 7.4（YouTube 采集，依赖 7.3）→ Story 7.5（Awin 采集）
    ↓
Story 8.2（PartnerBoost 爬虫）→ Story 8.3（Facebook Business Suite 爬虫）
```

**注意：** Story 8.1（CartSee）保持 `blocked` 状态，不在当前排期内。
10. `sources/social_media.py` stub
