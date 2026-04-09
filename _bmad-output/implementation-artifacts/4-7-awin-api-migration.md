# Story 4.7：Awin 爬虫迁移为 API 调用

Status: done

## Story

作为操作者，
我希望 Awin 数据源从 Playwright 爬虫改为官方 REST API 调用（Performance Data API），
以便获得更稳定、更快速的数据采集，同时覆盖 Performance Over Time 报告的全部数据维度。

## 背景

- 原实现（Story 4.1）使用 Playwright 浏览器自动化登录 Awin 后台，抓取 Transactions 页面表格
- Awin 提供官方 REST API，已验证 API Token 可用，三个 Performance Data 端点均返回 200
- API 方式无需浏览器、无验证码风险、速度更快、数据结构更稳定

## API 调研结果

### 认证方式
- OAuth 2.0 Bearer Token：`Authorization: Bearer <token>`
- Token 绑定用户级别，可访问该用户下所有 advertiser/publisher 账户

### 可用端点（For Advertisers > Performance Data）

| API | 端点 | 返回字段 |
|-----|------|----------|
| Publisher Performance | `GET /advertisers/{id}/reports/publisher` | impressions, clicks, totalNo, totalValue, totalComm, pendingNo/Value/Comm, confirmedNo/Value/Comm, bonusNo/Value/Comm, declinedNo/Value/Comm |
| Campaign Performance | `GET /advertisers/{id}/reports/campaign` | quantity(click/pending/approved/bonus/total), saleAmount, commissionAmount；支持 interval=day/month/year |
| Creative Performance | `GET /advertisers/{id}/reports/creative` | 同 Publisher Performance + creativeId/creativeName/tagName |

### 已验证参数
- advertiserId: `89509`（Piscifun）
- API Token: 已验证可用（HTTP 200）
- startDate / endDate: 必填，格式 YYYY-MM-DD，最大跨度 400 天
- dateType: transaction / validation（可选）
- timezone: UTC（可选）
- interval: day / month / year（Campaign API 专属，可选）
- region: US（Creative API 必填）

### Performance Over Time 目标字段覆盖

| 目标字段 | 来源 | API 字段 |
|----------|------|----------|
| Impressions | 直接 | `impressions` (Publisher/Creative API) |
| Clicks | 直接 | `clicks` / `quantity.click` |
| Transactions | 直接 | `totalNo` / `quantity.total` |
| Commission | 直接 | `totalComm` / `commissionAmount.total` |
| Revenue | 直接 | `totalValue` / `saleAmount.total` |
| Conversion Rate | 计算 | totalNo / clicks |
| AOV | 计算 | totalValue / totalNo |
| CPA | 计算 | totalComm / totalNo |
| CPC | 计算 | totalComm / clicks |
| ROI | 计算 | totalValue / totalComm |

## Acceptance Criteria

1. **Given** `get_credentials()` 返回有效的 `AWIN_API_TOKEN` 和 `AWIN_ADVERTISER_ID`，**When** 调用 `awin.authenticate()`，**Then** 通过 `GET https://api.awin.com/accounts` 验证 Token 有效性，返回 `True`，日志输出 `[awin] 认证 ... 成功`

2. **Given** 认证成功后，**When** 调用 `awin.fetch_sample()`，**Then** 调用 Publisher Performance API（`GET /advertisers/{advertiserId}/reports/publisher`）获取样本数据，返回 `list[dict]`，HTTP 请求超时 30s，整体执行在 60s 内完成

3. **Given** `fetch_sample` 返回的样本数据，**When** 调用 `awin.extract_fields(sample)`，**Then** 返回符合标准 FieldInfo 结构的字段列表（每项含 `field_name`、`data_type`、`sample_value`、`nullable`）

4. **Given** 字段提取完成，**When** `write_raw_report("awin", fields, ...)` 被调用，**Then** `reports/awin-raw.md` 包含实际字段表格和需求字段对照区块

5. **Given** API Token 无效（401/403），**When** 调用 `authenticate()`，**Then** 日志输出 `[awin] 认证 ... 失败：{HTTP 状态码和说明}`，返回 `False`

6. **Given** API 请求网络超时或服务不可用，**When** 调用 `fetch_sample()`，**Then** 抛出 `RuntimeError("[awin] API 请求失败：{错误详情}")`，不静默失败

7. **Given** 单元测试环境，**When** 运行 `tests/test_awin.py`，**Then** `extract_fields()` 单元测试通过（使用更新后的 `tests/fixtures/awin_sample.json`）；`authenticate()` 和 `fetch_sample()` 标注 `@pytest.mark.integration`

## Tasks / Subtasks

- [x] 更新 `.env.example`：将 `AWIN_USERNAME` / `AWIN_PASSWORD` 替换为 `AWIN_API_TOKEN` / `AWIN_ADVERTISER_ID`（AC: #1）
- [x] 更新 `config/credentials.py`：将 `_REQUIRED_KEYS` 中的 `AWIN_USERNAME`/`AWIN_PASSWORD` 替换为 `AWIN_API_TOKEN`/`AWIN_ADVERTISER_ID`
- [x] 重写 `sources/awin.py`（AC: #1 #2 #3 #4 #5 #6）
  - [x] 移除所有 Playwright 相关代码（sync_playwright、浏览器启动、页面操作、验证码检测等）
  - [x] 新增 `import requests`
  - [x] 常量替换：`AWIN_API_BASE = "https://api.awin.com"`，移除 LOGIN_URL / REPORT_URL / CAPTCHA_KEYWORDS 等
  - [x] 重写 `authenticate() -> bool`：用 `GET /accounts` 验证 Token + advertiserId，Bearer Token 认证
  - [x] 重写 `fetch_sample(table_name=None) -> list[dict]`：调用 Publisher Performance API，参数 startDate/endDate（默认最近 7 天），解析 JSON 响应
  - [x] 保留 `extract_fields(sample) -> list[dict]`：纯函数逻辑基本不变（API 返回已是正确类型，无需字符串类型推断）
  - [x] 保留 `_is_empty()` 和 `_infer_type()` 辅助函数
  - [x] 删除 `_login()`、`_check_captcha()`、`_check_total_timeout()`、`_extract_table_rows()`、`_normalize_headers()` 等爬虫专用函数
  - [x] 所有日志保持 `[awin]` 前缀，凭证使用 `mask_credential()` 脱敏
- [x] 更新 `tests/fixtures/awin_sample.json`（AC: #7）
  - [x] 替换为 Publisher Performance API 返回格式的 mock 数据（含 impressions, clicks, totalNo, totalValue, totalComm 等字段）
- [x] 更新 `tests/test_awin.py`（AC: #7）
  - [x] 更新 `TestExtractFields` 和 `TestExtractFieldsEdgeCases` 以匹配新 fixture 格式
  - [x] 移除 Playwright 相关的 integration test（如有）
  - [x] 新增 `TestAuthenticateIntegration` 和 `TestFetchSampleIntegration`（标注 `@pytest.mark.integration`）

## Dev Notes

- 接口契约（ARCH2）不变：`authenticate() -> bool`、`fetch_sample() -> list[dict]`、`extract_fields() -> list[dict]`
- 凭证加载方式（ARCH3）不变：通过 `from config.credentials import get_credentials`
- 报告策略（ARCH4）不变：`write_raw_report` + `init_validation_report`
- 超时规范参考其他 API 数据源（ARCH10 中 HTTP 请求 30s），不再需要 Playwright 的 15s 页面等待
- `requirements.txt` 中 `playwright` 依赖如果其他模块仍在使用则保留，否则可移除
- Campaign Performance API 支持 `interval=day` 按天聚合，可作为后续扩展（本 Story 先用 Publisher Performance API 获取汇总数据）

## Dev Agent Record

### Implementation Plan
- 将 Awin 数据源从 Playwright 爬虫迁移为 REST API 调用
- 认证改用 Bearer Token，通过 GET /accounts 验证
- 数据获取改用 Publisher Performance API
- 保持 ARCH2 接口契约不变

### Completion Notes
- sources/awin.py：完全重写，从 460 行爬虫代码精简为 ~230 行 API 调用代码
- 移除了全部 Playwright 依赖：sync_playwright、浏览器管理、CAPTCHA 检测、HTML 表格解析等
- 新增 requests 库进行 HTTP 调用，使用 Bearer Token 认证
- authenticate() 通过 GET /accounts 验证 Token 和 advertiserId
- fetch_sample() 调用 Publisher Performance API，默认查询最近 7 天数据
- extract_fields() 和辅助函数 _is_empty()/_infer_type() 保留不变
- 更新 .env.example、credentials.py、conftest.py 中的凭证键名
- 更新 fixture 为 Publisher Performance API 真实数据格式
- 更新测试用例匹配新数据结构，24 个单元测试全部通过
- 已有的 test_validate.py / test_e2e.py / test_tiktok.py / test_triplewhale.py 失败为已有问题，非本次变更引起

### Debug Log
无异常

## File List

- `.env.example` — 修改：AWIN_USERNAME/AWIN_PASSWORD -> AWIN_API_TOKEN/AWIN_ADVERTISER_ID
- `config/credentials.py` — 修改：_REQUIRED_KEYS 中替换 Awin 凭证键名
- `sources/awin.py` — 重写：Playwright 爬虫 -> REST API 调用
- `tests/conftest.py` — 修改：TEST_CREDENTIALS 中替换 Awin 凭证键名
- `tests/fixtures/awin_sample.json` — 重写：Transaction 格式 -> Publisher Performance API 格式
- `tests/test_awin.py` — 重写：测试用例匹配新 API 数据结构
- `tests/test_credentials.py` — 修改：ALL_VALID_ENV 中替换 Awin 凭证键名

## Change Log

- 2026-04-09: Awin 数据源从 Playwright 爬虫迁移为官方 REST API 调用（Story 4.7）
