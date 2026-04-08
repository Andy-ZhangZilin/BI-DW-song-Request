---
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories", "step-04-final-validation"]
status: complete
completedAt: '2026-04-03'
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/architecture.md"
---

# outdoor-data-validator - Epic Breakdown

## Overview

本文档对 outdoor-data-validator 项目进行完整的 Epic 和 Story 拆解，将 PRD 和架构决策文档中的需求分解为可实施的开发故事。

## Requirements Inventory

### Functional Requirements

FR1: 操作者可通过命令行指定单个数据源名称运行该数据源的验证流程
FR2: 操作者可通过命令行一次性运行全部数据源的验证流程
FR3: 系统在每次运行时将执行过程打印到控制台，包含数据源名称、当前操作步骤和最终状态
FR4: 操作者可通过 `.env` 文件配置所有数据源的认证凭证（API Key、账号密码、Token 等）
FR5: 系统提供 `.env.example` 模板，列出所有需要填写的凭证字段
FR6: 操作者可通过 YAML 配置文件定义各数据源的字段需求清单，无需修改代码
FR7: 系统可完成 API Key 方式的认证接入（TripleWhale、YouTube）
FR8: 系统可完成 OAuth 2.0 + HmacSHA256 签名方式的认证接入（TikTok Shop）
FR9: 系统可完成钉钉开放平台 Access Token 方式的认证接入（钉钉多维表）
FR10: 系统可完成账号密码登录方式的浏览器自动化接入（Awin、CartSee、PartnerBoost）
FR11: 系统在接入失败时输出具体错误信息，指明失败原因（认证错误、网络超时等）
FR12: 系统在爬虫接入遇到验证码或登录拦截时，中断执行并提示操作者手动干预
FR13: 系统可从每个数据源抓取至少一条真实样本记录
FR14: 系统可完整列出样本记录中所有返回的字段（字段名、数据类型、示例值）
FR15: 系统可将原始字段列表输出到对应数据源的验证报告文件
FR16: 系统可将数据源返回的字段与配置文件中定义的需求字段逐一比对
FR17: 系统可对每个需求字段自动标注匹配状态（精确匹配 / 模糊匹配 / 未匹配）
FR18: 操作者可在报告中为每个字段填写人工判断结论（✅ 直接可用 / ⚠️ 需转换 / ❌ 缺失）
FR19: 操作者可在报告中为"需转换"字段填写转换逻辑说明
FR20: 操作者可在报告中为"缺失"字段填写替代方案或明确结论
FR21: 系统可为每个数据源生成独立的 Markdown 验证报告，输出到 `reports/` 目录
FR22: 验证报告包含：数据源基本信息、接入状态、原始字段列表、字段对标结果表
FR23: 字段对标结果表使用统一三态标注（✅ / ⚠️ / ❌），每条结论附带说明
FR24: 每次运行覆盖更新同名报告文件，保持报告内容为最新验证结果
FR25: 系统可生成符合统一模板格式的报告，可直接作为 ETL 开发的输入文档
FR26: 系统对每个操作步骤输出结构化日志（格式：`[数据源] 操作描述 ... 成功/失败`）
FR27: 系统在发生异常时输出完整错误信息，包含错误类型、位置和建议排查方向
FR28: 系统在单个数据源失败时不影响其他数据源的验证流程继续执行
FR29: 项目提供 README 文档，说明运行环境要求、安装步骤和各数据源的运行命令
FR30: 项目通过 `requirements.txt` 管理所有依赖，支持一键安装

### NonFunctional Requirements

NFR1: 安全性 — 凭证仅从 `.env` 文件读取，不硬编码在代码中
NFR2: 安全性 — 日志和报告输出中不包含完整凭证信息（Access Token、密码等），凭证仅显示前 4 位 + "****"
NFR3: 安全性 — `.env` 在 `.gitignore` 中明确排除，严禁提交版本控制
NFR4: 可靠性 — 相同输入在不同时间运行，字段列表输出结果一致（幂等运行）
NFR5: 可靠性 — 单个数据源失败不中断其他数据源的验证流程（异常隔离）
NFR6: 可靠性 — 爬虫异常不静默失败，有明确错误提示和退出状态码（非零）
NFR7: 可维护性 — 新增数据源只需在 `sources/` 目录添加新模块，无需修改核心入口逻辑
NFR8: 可维护性 — 每个数据源模块遵循统一接口规范（authenticate / fetch_sample / extract_fields）
NFR9: 可维护性 — 关键逻辑（TikTok 签名算法、时间戳偏移）有代码注释说明
NFR10: 性能 — 单个数据源的样本抓取和报告生成在正常网络条件下 60 秒内完成

### Additional Requirements

来自架构文档的技术需求：

- ARCH1: 无需第三方 starter，直接按 PRD 定义结构手工初始化项目（第一个故事为项目结构初始化）
- ARCH2: 统一 source 接口契约：`authenticate() -> bool`、`fetch_sample(table_name: str = None) -> list[dict]`、`extract_fields(sample: list[dict]) -> list[dict]`，FieldInfo 标准结构为 `{field_name, data_type, sample_value, nullable}` 四字段
- ARCH3: `config/credentials.py` 作为唯一凭证加载入口，各 source 模块从此导入（`from config.credentials import get_credentials`），不直接调用 `os.getenv`
- ARCH4: 双文件报告策略：`reports/{source}-raw.md`（每次运行完全覆盖）+ `reports/{source}-validation.md`（仅首次由 reporter.py 创建模板，后续不覆盖，人工维护）
- ARCH5: TikTok 认证采用 refresh_token 自动刷新模式（refresh_token 手动填入 .env，脚本每次调用前自动换取 access_token），无需浏览器 OAuth 初始授权；shop_cipher 通过 API 自动获取
- ARCH6: TripleWhale 单文件按 `table_name` 内部路由（pixel_orders_table / pixel_joined_tvf / sessions_table / product_analytics_tvf），shopDomain = piscifun.myshopify.com
- ARCH7: 字段对标采用纯发现模式（不做 fuzzy matching），双列对照报告（实际字段列表 + 需求字段清单），人工对照判断
- ARCH8: `config/field_requirements.yaml` 按数据表分组，分组键为以下 11 个（来源：《指标梳理及数据需求沟通-2026.03.31.xlsx》"数据表需求"sheet）：`profit_table` / `financial_accounts_table` / `marketing_performance_table` / `dtc_ad_spend_table` / `kol_info_table` / `kol_content_performance_table` / `kol_collaboration_table` / `tiktok_sales_table` / `product_marketing_table` / `social_media_account_table` / `social_media_content_table`；每条记录含 `display_name`（中文字段名）、`source`（数据源模块名）、`table`（端点/表名）三字段
- ARCH9: `reporter.py` 抽离报告渲染逻辑，`validate.py` 保持单一职责（CLI 解析 + 调度循环）
- ARCH10: Playwright 使用 `sync_playwright` 同步模式；HTTP 请求超时 30s，Playwright 页面等待 15s，单 source 整体超时 60s
- ARCH11: `sources/social_media.py` 作为 stub 模块（三个接口均 raise NotImplementedError，凭证就绪后实现）
- ARCH12: `tests/conftest.py` 全局 fixture patch `get_credentials()`；爬虫模块 `fetch_sample` 标注 `@pytest.mark.integration`；`tests/fixtures/*.json` 存放各数据源 API 响应样本
- ARCH13: Playwright 需额外执行 `playwright install chromium`（requirements.txt 无法自动处理），必须在 README 中显式说明

### UX Design Requirements

本项目为纯命令行开发工具，不涉及 UI 界面设计，无 UX 设计需求。

### FR Coverage Map

FR1:  Epic 5 — CLI 单源运行入口（--source 参数）
FR2:  Epic 5 — CLI 全量运行入口（--all 参数）
FR3:  Epic 5 — 控制台执行过程日志
FR4:  Epic 1 — .env 凭证文件支持
FR5:  Epic 1 — .env.example 模板
FR6:  Epic 1 — field_requirements.yaml 字段需求配置
FR7:  Epic 2/3 — API Key 认证接入（TripleWhale/YouTube）
FR8:  Epic 2 — OAuth+HmacSHA256 认证接入（TikTok Shop）
FR9:  Epic 3 — Access Token 认证接入（钉钉）
FR10: Epic 4 — Playwright 账号密码登录接入
FR11: Epic 2/3/4 — 接入失败明确报错（各 source 实现时覆盖）
FR12: Epic 4 — 验证码中断提示
FR13: Epic 2/3/4 — 各数据源样本抓取（各 source 实现时覆盖）
FR14: Epic 2/3/4 — 字段完整列出（各 source extract_fields）
FR15: Epic 2/3/4 — 字段列表输出到报告（调用 reporter.py）
FR16: Epic 1 — reporter.py 双列对照渲染（实际字段 + 需求字段）
FR17: Epic 1 — reporter.py 报告结构（供人工对照，无自动匹配）
FR18: Epic 1 — validation.md 模板包含人工结论列（⬜ 待确认）
FR19: Epic 1 — validation.md 转换逻辑说明行
FR20: Epic 1 — validation.md 替代方案说明行
FR21: Epic 1 — reporter.py 生成 reports/ 目录下 Markdown 报告
FR22: Epic 1 — 报告结构定义（基本信息 + 字段列表 + 对照表）
FR23: Epic 1 — 三态标注格式（✅/⚠️/❌）
FR24: Epic 1 — raw.md 每次覆盖更新策略
FR25: Epic 1 — validation.md 首次创建后不覆盖（人工维护保护）
FR26: Epic 5 — 结构化日志格式（[source] 操作 ... 成功/失败）
FR27: Epic 5 — 完整异常错误信息输出
FR28: Epic 5 — 单源失败隔离（调度器独立 try/except）
FR29: Epic 1 — README（安装步骤 + Playwright 说明）
FR30: Epic 1 — requirements.txt 依赖管理

## Epic List

### Epic 1: 项目初始化与基础设施
操作者能完成项目安装、配置凭证和字段需求，并具备可运行的报告生成框架（raw + validation 双文件策略）
**覆盖 FR：** FR4, FR5, FR6, FR16, FR17, FR18, FR19, FR20, FR21, FR22, FR23, FR24, FR25, FR29, FR30
**架构需求：** ARCH1, ARCH2, ARCH3, ARCH4, ARCH7, ARCH8, ARCH9, ARCH12, ARCH13

### Epic 2: 高优先级 API 数据源接入
操作者能验证 TripleWhale（4 表路由）和 TikTok Shop（refresh_token 自动刷新），获取字段发现报告
**覆盖 FR：** FR7, FR8, FR11, FR13, FR14, FR15
**架构需求：** ARCH5, ARCH6

### Epic 3: 标准 API 数据源接入
操作者能验证钉钉多维表和 YouTube，完成全部 API 类数据源覆盖
**覆盖 FR：** FR7, FR9, FR11, FR13, FR14, FR15

### Epic 4: 爬虫数据源接入
操作者能通过浏览器自动化验证 Awin、CartSee、PartnerBoost，并在遇到验证码时获得明确中断提示
**覆盖 FR：** FR10, FR11, FR12, FR13, FR14, FR15
**架构需求：** ARCH10, ARCH11

### Epic 5: 统一 CLI 验证入口与完整流水线
操作者能通过一条命令运行单个或全部数据源的验证，获得控制台反馈、完整报告和正确的退出码
**覆盖 FR：** FR1, FR2, FR3, FR26, FR27, FR28

---

## Epic 1: 项目初始化与基础设施

操作者能完成项目安装、配置凭证和字段需求，并具备可运行的报告生成框架（raw + validation 双文件策略）

### Story 1.1: 项目结构初始化

作为操作者，
我希望按照架构规范初始化完整的项目目录结构、基础文件和依赖管理，
以便能在新机器上一键安装并获得可运行的工具脚手架。

**Acceptance Criteria:**

**Given** 一个空目录
**When** 执行 `pip install -r requirements.txt` 后再执行 `playwright install chromium`
**Then** 所有依赖安装成功，无报错，可执行 `python validate.py --help`

**Given** 项目初始化完成
**When** 检查目录结构
**Then** 存在以下文件/目录：`validate.py`（空 CLI 骨架）、`reporter.py`（空骨架）、`requirements.txt`（含 python-dotenv requests playwright PyYAML pytest）、`.env.example`、`.gitignore`、`README.md`、`config/__init__.py`、`config/credentials.py`（骨架）、`config/field_requirements.yaml`（骨架）、`sources/__init__.py`、`reports/`（空目录）、`tests/__init__.py`、`tests/conftest.py`（骨架）、`tests/fixtures/`（空目录）

**Given** 项目被克隆到新机器
**When** 检查 `.gitignore`
**Then** 明确排除 `.env`、`__pycache__/`、`*.pyc`、`.pytest_cache/`

**Given** 读取 `README.md`
**When** 查看安装步骤
**Then** 包含：环境要求（Python 3.x）、`pip install -r requirements.txt` 命令、`playwright install chromium` 的显式说明（注明该步骤无法通过 requirements.txt 自动完成）、各数据源运行命令示例、字段分析工作流说明（运行完成后将 raw.md 提交给 AI 助手进行字段满足性分析，分析结论对应 config/field_requirements.yaml 中的 11 张数据表）

### Story 1.2: 凭证管理器

作为操作者，
我希望有一个集中的凭证加载器，在工具启动时统一校验所有必需的 API Key 和 Token，
以便在任何数据源运行之前就能获得明确的缺失凭证提示。

**Acceptance Criteria:**

**Given** `.env` 文件包含所有必需的凭证键
**When** 调用 `get_credentials()`
**Then** 返回包含所有凭证键值的字典，函数执行成功无报错

**Given** `.env` 文件缺少一个或多个凭证键
**When** 调用 `get_credentials()`
**Then** 抛出 `ValueError`，错误信息列出所有缺失的键名

**Given** 任意 source 模块需要凭证
**When** 通过 `from config.credentials import get_credentials` 获取
**Then** 可正常取得凭证字典，且该模块内无直接调用 `os.getenv()` 的代码

**Given** 工具运行时产生任何日志输出
**When** 检查日志内容
**Then** 所有凭证值仅显示前 4 位 + `****`（例如：`abc1****`），完整 Token/密码/API Key 不出现在日志中

**Given** `tests/conftest.py` 中的 `mock_credentials` fixture
**When** 在任意单元测试中使用该 fixture
**Then** `get_credentials()` 被 mock 返回测试用字典，无需真实 `.env` 文件

### Story 1.3: 字段需求配置

作为操作者，
我希望通过 YAML 配置文件按报表分组定义各数据源的字段需求清单，
以便在不修改任何代码的情况下更新字段需求。

**Acceptance Criteria:**

**Given** `config/field_requirements.yaml` 包含全部 11 个数据表分组（profit_table / financial_accounts_table / marketing_performance_table / dtc_ad_spend_table / kol_info_table / kol_content_performance_table / kol_collaboration_table / tiktok_sales_table / product_marketing_table / social_media_account_table / social_media_content_table）
**When** 使用 PyYAML 加载该文件
**Then** 解析结果为字典，每条记录均包含 `display_name`（中文字段名）、`source`（数据源名称）、`table`（表/端点名称）三个字段

**Given** 在 YAML 文件中新增一个字段条目
**When** 重新运行验证器
**Then** 新字段出现在对应数据源报告的需求字段列中，无需修改任何 Python 代码

**Given** YouTube 等非 SQL 数据源的字段条目
**When** 解析该条目
**Then** `table` 字段为 `None` 或缺省时不报错，视为可选字段

**Given** 初始 YAML 文件
**When** 查看内容
**Then** 包含全部 11 张数据表的字段需求，字段内容来源于《指标梳理及数据需求沟通-2026.03.31.xlsx》"数据表需求"sheet，每条记录含完整三字段结构（display_name / source / table）

### Story 1.4: 报告渲染器

作为操作者，
我希望有一个报告渲染器能生成 raw 字段发现报告和 validation 人工标注模板，
以便我能看到实际 API 返回字段与需求字段的对照视图，并在 validation 文件中填写人工判断结论。

**Acceptance Criteria:**

**Given** 一个数据源名称、FieldInfo 列表、表名和样本数量
**When** 调用 `write_raw_report(source_name, fields, table_name, sample_count)`
**Then** `reports/{source_name}-raw.md` 被创建（或覆盖），包含：生成时间戳、表名、样本记录数、实际返回字段表格（字段名/类型/示例值/可空）

**Given** `config/field_requirements.yaml` 已加载
**When** `write_raw_report()` 被调用
**Then** 报告末尾包含"需求字段（待人工对照）"区块，列出该数据源所有 `display_name` 字段，初始状态标记为 `⬜ 待确认`

**Given** `reports/{source_name}-validation.md` 不存在
**When** 调用 `init_validation_report(source_name)`
**Then** 创建人工标注模板文件，包含三态标注占位符（✅ 直接可用 / ⚠️ 需转换 / ❌ 缺失）、转换逻辑说明行、替代方案说明行

**Given** `reports/{source_name}-validation.md` 已存在且有人工标注内容
**When** 再次调用 `init_validation_report(source_name)`
**Then** 现有文件**不被覆盖**，人工标注内容完整保留（通过 `Path.exists()` 判断）

**Given** raw 报告生成完成
**When** 检查报告内容
**Then** 不包含任何完整 API Key、Token 或密码值

---

## Epic 2: 高优先级 API 数据源接入

操作者能验证 TripleWhale（4 表路由）和 TikTok Shop（refresh_token 自动刷新），获取字段发现报告

### Story 2.1: TripleWhale 数据源接入

作为操作者，
我希望验证器能通过 API Key 连接 TripleWhale，并针对 4 张业务表分别抓取样本字段，
以便我能获得利润表和营销表现表所需字段的实际可用性报告。

**Acceptance Criteria:**

**Given** `get_credentials()` 返回有效的 `TRIPLEWHALE_API_KEY`
**When** 调用 `triplewhale.authenticate()`
**Then** 返回 `True`，并在日志中输出 `[triplewhale] 认证 ... 成功`

**Given** 认证成功后传入 `table_name="pixel_orders_table"`
**When** 调用 `triplewhale.fetch_sample("pixel_orders_table")`
**Then** 返回至少一条原始记录（`list[dict]`），请求使用 `shopDomain=piscifun.myshopify.com` 参数，超时设置为 30s

**Given** fetch_sample 返回的样本数据
**When** 调用 `triplewhale.extract_fields(sample)`
**Then** 返回 `list[dict]`，每条记录符合标准 FieldInfo 结构（`field_name`, `data_type`, `sample_value`, `nullable`）

**Given** 4 张表（pixel_orders_table / pixel_joined_tvf / sessions_table / product_analytics_tvf）逐一执行
**When** 每张表的 `fetch_sample` + `extract_fields` + `write_raw_report` 完成
**Then** `reports/triplewhale-raw.md` 被创建，包含该表实际字段列表和需求字段对照区块

**Given** API Key 无效或网络超时
**When** 调用 `authenticate()` 或 `fetch_sample()`
**Then** 在日志中输出 `[triplewhale] 认证 ... 失败：{具体错误信息}`，函数返回 `False` 或抛出异常，不静默失败

**Given** 单元测试环境（mock get_credentials + fixture）
**When** 运行 `tests/test_triplewhale.py`
**Then** 所有单元测试通过，不需要真实 API Key

### Story 2.2: TikTok Shop 数据源接入

作为操作者，
我希望验证器能通过 refresh_token 自动换取 access_token 并连接 TikTok Shop API，
以便我能获得 TikTok 销售订单数据的实际字段报告。

**Acceptance Criteria:**

**Given** `get_credentials()` 返回有效的 `TIKTOK_REFRESH_TOKEN` 和 `TIKTOK_APP_KEY`/`TIKTOK_APP_SECRET`
**When** 调用 `tiktok.authenticate()`
**Then** 自动换取 `access_token`（每次重新获取，不缓存），返回 `True`，日志输出 `[tiktok] 认证 ... 成功`

**Given** authenticate 成功后
**When** 调用 `tiktok.fetch_sample()`
**Then** 使用 HmacSHA256 签名构造请求，自动通过 `/api/shops/get_authorized_shop` 获取 `shop_cipher`，返回至少一条订单样本记录

**Given** fetch_sample 返回的样本数据
**When** 调用 `tiktok.extract_fields(sample)`
**Then** 返回符合标准 FieldInfo 结构的字段列表

**Given** 字段提取完成
**When** `write_raw_report("tiktok", fields, ...)` 被调用
**Then** `reports/tiktok-raw.md` 包含实际字段表格和需求字段对照区块

**Given** refresh_token 过期或无效
**When** 调用 `authenticate()`
**Then** 日志输出 `[tiktok] 认证 ... 失败：{错误详情}`，返回 `False`，不静默失败

**Given** 签名生成逻辑
**When** 检查 `tiktok.py` 源码
**Then** `_sign_request()` 函数包含 HmacSHA256 算法说明注释，时间戳偏移逻辑有注释说明

**Given** 单元测试环境（mock get_credentials + fixture）
**When** 运行 `tests/test_tiktok.py`
**Then** 所有单元测试通过，mock 覆盖 authenticate 和 fetch_sample

---

## Epic 3: 标准 API 数据源接入

操作者能验证钉钉多维表和 YouTube，完成全部 API 类数据源覆盖

### Story 3.1: 钉钉多维表数据源接入

作为操作者，
我希望验证器能通过 AppKey + AppSecret 换取 Access Token 并连接钉钉多维表 API，
以便我能获得钉钉 Bitable 中业务数据的实际字段报告。

**Acceptance Criteria:**

**Given** `get_credentials()` 返回有效的 `DINGTALK_APP_KEY` 和 `DINGTALK_APP_SECRET`
**When** 调用 `dingtalk.authenticate()`
**Then** 向钉钉开放平台换取 Access Token，返回 `True`，日志输出 `[dingtalk] 认证 ... 成功`

**Given** Access Token 在有效期内
**When** 再次调用 `authenticate()`
**Then** 可复用已有 Token（token 有效期内不重复请求），避免不必要的换取调用

**Given** authenticate 成功后
**When** 调用 `dingtalk.fetch_sample()`
**Then** 返回至少一条多维表记录（`list[dict]`），超时设置为 30s

**Given** fetch_sample 返回的样本数据
**When** 调用 `dingtalk.extract_fields(sample)`
**Then** 返回符合标准 FieldInfo 结构的字段列表；若关联字段返回空值，`nullable=True` 且 `sample_value=None`

**Given** 字段提取完成
**When** `write_raw_report("dingtalk", fields, ...)` 被调用
**Then** `reports/dingtalk-raw.md` 包含实际字段表格和需求字段对照区块

**Given** AppKey 或 AppSecret 无效
**When** 调用 `authenticate()`
**Then** 日志输出 `[dingtalk] 认证 ... 失败：{错误详情}`，返回 `False`

**Given** 单元测试环境（mock get_credentials + fixture）
**When** 运行 `tests/test_dingtalk.py`
**Then** 所有单元测试通过，不需要真实凭证

### Story 3.2: YouTube 数据源接入

作为操作者，
我希望验证器能通过 API Key 连接 YouTube Data API v3 并抓取频道/视频数据字段，
以便我能获得 YouTube 数据的实际字段报告。

**Acceptance Criteria:**

**Given** `get_credentials()` 返回有效的 `YOUTUBE_API_KEY`
**When** 调用 `youtube.authenticate()`
**Then** 验证 API Key 有效性（发送一次轻量探测请求），返回 `True`，日志输出 `[youtube] 认证 ... 成功`

**Given** authenticate 成功后
**When** 调用 `youtube.fetch_sample()`
**Then** 通过 YouTube Data API v3 返回至少一条视频/频道样本记录，超时设置为 30s，`table` 参数为 `None`（非 SQL 数据源）

**Given** fetch_sample 返回的样本数据
**When** 调用 `youtube.extract_fields(sample)`
**Then** 返回符合标准 FieldInfo 结构的字段列表

**Given** 字段提取完成
**When** `write_raw_report("youtube", fields, ...)` 被调用
**Then** `reports/youtube-raw.md` 包含实际字段表格和需求字段对照区块

**Given** API Key 无效（403 / 401 响应）
**When** 调用 `authenticate()`
**Then** 日志输出 `[youtube] 认证 ... 失败：{HTTP 错误码和说明}`，返回 `False`

**Given** 单元测试环境（mock get_credentials + fixture）
**When** 运行 `tests/test_youtube.py`
**Then** 所有单元测试通过，不需要真实 API Key

---

## Epic 4: 爬虫数据源接入

操作者能通过浏览器自动化验证 Awin、CartSee、PartnerBoost，并在遇到验证码时获得明确中断提示

### Story 4.1: Awin 爬虫数据源接入

作为操作者，
我希望验证器能通过 Playwright 自动登录 Awin 联盟后台并抓取报表字段，
以便我能获得 Awin 平台数据的实际字段报告。

**Acceptance Criteria:**

**Given** `get_credentials()` 返回有效的 `AWIN_USERNAME` 和 `AWIN_PASSWORD`
**When** 调用 `awin.authenticate()`
**Then** 使用 `sync_playwright` 启动 headless Chromium，完成账号密码登录，返回 `True`，日志输出 `[awin] 认证 ... 成功`

**Given** 登录成功后
**When** 调用 `awin.fetch_sample()`
**Then** 导航至报表页面，抓取至少一条数据记录，Playwright 页面等待超时设置为 15s，整体执行在 60s 内完成

**Given** fetch_sample 返回的样本数据
**When** 调用 `awin.extract_fields(sample)`
**Then** 返回符合标准 FieldInfo 结构的字段列表

**Given** 字段提取完成
**When** `write_raw_report("awin", fields, ...)` 被调用
**Then** `reports/awin-raw.md` 包含实际字段表格和需求字段对照区块

**Given** 页面出现验证码或登录拦截
**When** `fetch_sample()` 检测到验证码关键词
**Then** 抛出 `RuntimeError("[awin] 遇到验证码，请手动完成验证后重新运行")`，不静默失败，浏览器在 finally 块中正确关闭

**Given** 登录凭证无效
**When** 调用 `authenticate()`
**Then** 日志输出 `[awin] 认证 ... 失败：{错误详情}`，返回 `False`，浏览器正确关闭

**Given** 单元测试环境
**When** 运行 `tests/test_awin.py`
**Then** `extract_fields()` 单元测试通过（使用 `tests/fixtures/awin_sample.json`）；`fetch_sample()` 标注 `@pytest.mark.integration`，不在单元测试中执行

### Story 4.2: CartSee 爬虫数据源接入

作为操作者，
我希望验证器能通过 Playwright 自动登录 CartSee EDM 后台并抓取邮件营销数据字段，
以便我能获得 CartSee 平台数据的实际字段报告。

**Acceptance Criteria:**

**Given** `get_credentials()` 返回有效的 `CARTSEE_USERNAME` 和 `CARTSEE_PASSWORD`
**When** 调用 `cartsee.authenticate()`
**Then** 使用 `sync_playwright` 启动 headless Chromium，完成账号密码登录，返回 `True`，日志输出 `[cartsee] 认证 ... 成功`

**Given** 登录成功后
**When** 调用 `cartsee.fetch_sample()`
**Then** 抓取至少一条 EDM 数据记录，页面等待超时 15s，整体执行在 60s 内完成

**Given** fetch_sample 返回的样本数据
**When** 调用 `cartsee.extract_fields(sample)`
**Then** 返回符合标准 FieldInfo 结构的字段列表

**Given** 字段提取完成
**When** `write_raw_report("cartsee", fields, ...)` 被调用
**Then** `reports/cartsee-raw.md` 包含实际字段表格和需求字段对照区块

**Given** 页面出现验证码
**When** `fetch_sample()` 检测到
**Then** 抛出 `RuntimeError("[cartsee] 遇到验证码，请手动完成验证后重新运行")`，浏览器正确关闭

**Given** 单元测试环境
**When** 运行 `tests/test_cartsee.py`
**Then** `extract_fields()` 单元测试通过；`fetch_sample()` 标注 `@pytest.mark.integration`

### Story 4.3: PartnerBoost 爬虫数据源接入

作为操作者，
我希望验证器能通过 Playwright 自动登录 PartnerBoost 后台并抓取联盟营销数据字段，
以便我能获得 PartnerBoost 平台数据的实际字段报告。

**Acceptance Criteria:**

**Given** `get_credentials()` 返回有效的 `PARTNERBOOST_USERNAME` 和 `PARTNERBOOST_PASSWORD`
**When** 调用 `partnerboost.authenticate()`
**Then** 使用 `sync_playwright` 启动 headless Chromium，完成账号密码登录，返回 `True`，日志输出 `[partnerboost] 认证 ... 成功`

**Given** 登录成功后
**When** 调用 `partnerboost.fetch_sample()`
**Then** 抓取至少一条联盟报表记录，页面等待超时 15s，整体执行在 60s 内完成

**Given** fetch_sample 返回的样本数据
**When** 调用 `partnerboost.extract_fields(sample)`
**Then** 返回符合标准 FieldInfo 结构的字段列表

**Given** 字段提取完成
**When** `write_raw_report("partnerboost", fields, ...)` 被调用
**Then** `reports/partnerboost-raw.md` 包含实际字段表格和需求字段对照区块

**Given** 页面出现验证码
**When** `fetch_sample()` 检测到
**Then** 抛出 `RuntimeError("[partnerboost] 遇到验证码，请手动完成验证后重新运行")`，浏览器正确关闭

**Given** 单元测试环境
**When** 运行 `tests/test_partnerboost.py`
**Then** `extract_fields()` 单元测试通过；`fetch_sample()` 标注 `@pytest.mark.integration`

### Story 4.4: 社媒后台 Stub 模块

作为操作者，
我希望社媒后台数据源以占位模块形式存在，在凭证就绪前提供明确的未实现提示，
以便工具的模块结构完整，且在未来凭证就绪时只需填充实现而无需修改框架。

**Acceptance Criteria:**

**Given** `sources/social_media.py` 存在
**When** 调用 `social_media.authenticate()`
**Then** 抛出 `NotImplementedError("social_media: 凭证未就绪，暂未实现")`

**Given** `sources/social_media.py` 存在
**When** 调用 `social_media.fetch_sample()`
**Then** 抛出 `NotImplementedError`

**Given** `sources/social_media.py` 存在
**When** 调用 `social_media.extract_fields([])`
**Then** 抛出 `NotImplementedError`

**Given** 单元测试环境
**When** 运行 `tests/test_social_media.py`
**Then** 三个接口均验证 `NotImplementedError` 被正确抛出，测试全部通过

### Story 4.5: Facebook Business Suite 爬虫数据源接入

作为操作者，
我希望验证器能通过 Playwright 自动登录 Meta Business Suite 并抓取帖子和 Reels 列表数据字段，
以便我能获得 Facebook 社媒内容数据的实际字段报告。

**Acceptance Criteria:**

**Given** `get_credentials()` 返回有效的 `FACEBOOK_USERNAME` 和 `FACEBOOK_PASSWORD`
**When** 调用 `social_media.authenticate()`
**Then** 使用 `sync_playwright` 启动 headless Chromium，打开 `https://business.facebook.com/business/loginpage`，点击"使用 Facebook 登录"按钮，完成账号密码登录，返回 `True`，日志输出 `[social_media] 认证 ... 成功`

**Given** 登录成功后
**When** 调用 `social_media.fetch_sample()`
**Then** 导航至帖子和 Reels 页面（`/latest/posts/published_posts`），抓取列表中至少一条记录，页面等待超时 20s，整体执行在 90s 内完成

**Given** fetch_sample 返回的样本数据
**When** 调用 `social_media.extract_fields(sample)`
**Then** 返回包含以下字段的标准 FieldInfo 列表：标题、发布日期、状态、覆盖人数、获赞数和心情数、评论数、分享次数

**Given** 字段提取完成
**When** `write_raw_report("social_media", fields, ...)` 被调用
**Then** `reports/social_media-raw.md` 包含实际字段表格和需求字段对照区块

**Given** 页面出现验证码或人机验证
**When** `fetch_sample()` 检测到
**Then** 抛出 `RuntimeError("[social_media] 遇到验证码，请手动完成验证后重新运行")`，浏览器正确关闭

**Given** 单元测试环境
**When** 运行 `tests/test_social_media.py`
**Then** `extract_fields()` 单元测试通过；`authenticate()` 和 `fetch_sample()` 标注 `@pytest.mark.integration`

---

## Epic 5: 统一 CLI 验证入口与完整流水线

操作者能通过一条命令运行单个或全部数据源的验证，获得控制台反馈、完整报告和正确的退出码

### Story 5.1: validate.py CLI 入口与调度器

作为操作者，
我希望通过 `python validate.py --source <名称>` 或 `python validate.py --all` 一条命令运行验证，
以便我能获得带明确执行状态的控制台反馈，并在单源失败时不影响其他数据源继续运行。

**Acceptance Criteria:**

**Given** 运行 `python validate.py --source triplewhale`
**When** 命令执行完成
**Then** 仅运行 triplewhale 的 authenticate → fetch_sample → extract_fields → write_raw_report 流程，控制台输出每个步骤的结构化日志，格式为 `[triplewhale] {操作描述} ... 成功/失败`

**Given** 运行 `python validate.py --all`
**When** 命令执行完成
**Then** 按顺序运行全部已实现数据源（triplewhale / tiktok / dingtalk / youtube / awin / cartsee / partnerboost），每个数据源独立执行，任一数据源失败不中断其他数据源

**Given** 某个数据源在执行中抛出异常
**When** 调度器的 try/except 捕获该异常
**Then** 日志输出完整错误信息（含错误类型和来源），该数据源标记为失败，其余数据源正常继续执行

**Given** 所有数据源执行完毕
**When** `validate.py` 退出
**Then** 若全部成功则退出码为 `0`；若有任一数据源失败则退出码为 `1`；控制台输出汇总结果（各数据源：成功/失败）

**Given** 运行 `python validate.py --help`
**When** 输出帮助信息
**Then** 显示 `--source` 和 `--all` 参数说明及示例命令

**Given** `get_credentials()` 在启动阶段校验失败（缺少必填凭证键）
**When** `validate.py` 启动
**Then** 立即打印缺失凭证列表并以非零退出码退出，不进入调度循环（快速失败）

**Given** social_media 数据源（stub 模块）
**When** 被 `--all` 调用时抛出 `NotImplementedError`
**Then** 调度器捕获异常，标记该数据源为失败，继续执行后续数据源

### Story 5.2: 端到端集成验证

作为操作者，
我希望能通过一个集成验证流程确认整个流水线的关键路径可正确运行，
以便在部署到新机器时快速确认工具可用性。

**Acceptance Criteria:**

**Given** mock 凭证和 mock source 模块（每个 source 返回预设样本数据）
**When** 运行完整的 `--all` 调度流程
**Then** 所有 mock source 的 authenticate → fetch_sample → extract_fields → write_raw_report → init_validation_report 链路均被执行，`reports/` 目录下生成对应的 raw.md 和 validation.md 文件

**Given** 一个 mock source 的 `authenticate()` 返回 `False`
**When** 调度器处理该数据源
**Then** 跳过该数据源的 fetch_sample，记录为失败，继续处理下一个数据源，最终退出码为 `1`

**Given** 一个 mock source 的 `fetch_sample()` 抛出异常
**When** 调度器的 try/except 捕获
**Then** 完整错误信息被记录到日志，该数据源标记为失败，其余数据源不受影响

**Given** `reports/{source}-validation.md` 已存在（模拟人工已标注）
**When** 同一数据源再次运行
**Then** raw.md 被覆盖更新，validation.md 内容保持不变（人工标注得到保护）

**Given** 集成测试套件
**When** 运行 `pytest tests/ -m "not integration"`
**Then** 所有单元测试通过，无需真实 API 凭证或网络连接
