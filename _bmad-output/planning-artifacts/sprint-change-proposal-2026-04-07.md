# Sprint Change Proposal — 2026-04-07

**项目：** outdoor-data-validator
**提案人：** dadong
**日期：** 2026-04-07
**变更范围：** Minor（可由开发团队直接实现）

---

## Section 1：问题摘要

### 变更触发

在 Story 2.1（TripleWhale 数据源接入）完成并产出 `triplewhale-raw.md` 字段验证报告后，业务团队提出新的信息需求：

> 当前报告只展示了"字段有哪些"，但无法回答"历史数据能追溯多久"以及"如果要全量拉取需要多长时间"，这两个问题对 ETL 开发排期至关重要。

### 新增需求

针对 TripleWhale 全部 10 张表，新增以下探测能力：

1. **最早数据时间** — 每张表中最早一条记录的日期（`MIN(date_column)`）
2. **请求频率限制** — API 允许的请求速率（rate limit，60 req/min，来源：TripleWhale 文档）
3. **全量拉取预估时长** — 基于 `COUNT(*)` 总行数 + rate limit 计算全量拉取所需时间

### 发现时机

Sprint 执行中，所有 Epic 均已完成（done）。此变更为追加需求，不涉及已交付功能的回退或修复。

---

## Section 2：影响分析

### Epic 影响

| Epic | 影响 | 说明 |
|------|------|------|
| Epic 2：高优先级 API 数据源接入 | 受影响 | Story 2.1 需补充新 AC 和实现 |
| Epic 1：项目初始化与基础设施 | 轻微受影响 | reporter.py 需新增报告区块渲染 |
| Epic 3/4/5 | 不受影响 | 变更仅限 triplewhale 模块 |

### Story 影响

| Story | 变更类型 | 说明 |
|-------|---------|------|
| Story 2.1 triplewhale-数据源接入 | 补充 AC + Tasks | 新增 AC 8/9/10，新增 Tasks 4/5 |
| Story 1.4 报告渲染器 | 轻微扩展 | reporter.py 新增 `write_triplewhale_data_profile()` 函数 |

### 产物冲突

| 产物 | 变更 |
|------|------|
| `sources/triplewhale.py` | 新增常量 + `fetch_data_profile()` + 两个私有函数 |
| `tests/test_triplewhale.py` | 新增 `fetch_data_profile` 相关测试用例 |
| `reporter.py` | 新增"数据概况"区块渲染逻辑 |
| `_bmad-output/implementation-artifacts/2-1-triplewhale-数据源接入.md` | 新增 AC 8/9/10 + Task 4/5 |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | Story 2-1 状态回退为 ready-for-dev |

### 技术影响

- **额外 API 请求**：每次运行 triplewhale 时额外发 20 次 SQL 查询（10 张表 × MIN + COUNT 各 1 次），在 60 req/min rate limit 下约需额外 20 秒
- **架构边界**：`fetch_data_profile()` 作为 TripleWhale 专属扩展函数，不纳入通用 source 接口契约（即 validate.py 单独处理 triplewhale 的该调用）
- **无破坏性变更**：不影响现有三函数接口契约，不影响其他 source 模块

---

## Section 3：推荐方案

### 方案：直接调整（Direct Adjustment）

在 Story 2.1 的基础上追加实现，无需回滚或重新规划。

**理由：**
- 变更范围明确，仅限 `triplewhale.py` 和 `reporter.py` 两个文件
- 不破坏已有接口契约和其他 source 模块
- 新函数逻辑复用已有 `_fetch_table` 中的 SQL 查询模式，实现成本低

**工作量估算：**
- `sources/triplewhale.py` 新增约 60 行代码（常量 + 3 个函数）
- `tests/test_triplewhale.py` 新增约 30 行测试
- `reporter.py` 新增约 20 行渲染逻辑
- Story 2.1 文件更新：约 30 分钟
- 合计：约 2-3 小时开发工作量

**风险：**
- `creatives_table` 和 `ai_visibility_table` 当前无数据（0 条记录），MIN/COUNT 将返回 NULL/0，需做 None 防护处理
- TripleWhale SQL API rate limit 60 req/min 为文档值，实际可能不同，若超限需降速或增加 retry 逻辑（本次不实现，记录为 deferred）

---

## Section 4：详细变更提案

### 变更 4-1：`sources/triplewhale.py`

**新增常量（在现有常量块末尾追加）：**

```
OLD:
MAX_SAMPLE_ROWS: int = 1  # 每张表最多保留的样本行数

NEW:
MAX_SAMPLE_ROWS: int = 1  # 每张表最多保留的样本行数
RATE_LIMIT_RPM: int = 60          # 每分钟最大请求数（来源：TripleWhale 官方文档）
MAX_ROWS_PER_REQUEST: int = 1000  # 每次 SQL 查询最大返回行数

# 各表日期列名（基于 triplewhale-raw.md 2026-04-07 实际返回字段确认）
_TABLE_DATE_COLUMNS: dict[str, str] = {
    "pixel_orders_table":          "event_date",
    "pixel_joined_tvf":            "event_date",
    "sessions_table":              "event_date",
    "product_analytics_tvf":       "event_date",
    "pixel_keywords_joined_tvf":   "event_date",
    "ads_table":                   "event_date",
    "social_media_comments_table": "created_at",
    "social_media_pages_table":    "event_date",
    "creatives_table":             "event_date",
    "ai_visibility_table":         "event_date",
}
```

**新增公开函数 `fetch_data_profile()`（在 `extract_fields` 之后追加）：**

```python
def fetch_data_profile(table_name: str) -> dict:
    """探测指定表的数据概况：最早数据时间、总行数、全量拉取预估时长。

    发送两次 SQL 查询（MIN date 和 COUNT *），均在 DEFAULT_TIMEOUT 内完成。
    当前无数据的表（如 creatives_table）返回 earliest_date=None、total_rows=0。

    Args:
        table_name: 表名，必须为 TABLES 中的一个。

    Returns:
        {
            "table_name": str,
            "date_column": str,
            "earliest_date": str | None,          # ISO 日期字符串，无数据则 None
            "total_rows": int | None,             # 总行数，查询失败则 None
            "rate_limit_rpm": int,                # 常量 RATE_LIMIT_RPM
            "max_rows_per_request": int,          # 常量 MAX_ROWS_PER_REQUEST
            "estimated_pull_minutes": float | None # 预估全量拉取分钟数
        }

    Raises:
        ValueError: table_name 不在 TABLES 中
    """

新增私有函数 _fetch_earliest_date() 和 _fetch_row_count()：

_fetch_earliest_date(table_name, api_key) -> str | None
    SQL: SELECT MIN({date_col}) as earliest FROM {table_name}
    返回首行首列的字符串值；无数据或查询失败返回 None（警告日志，不抛异常）

_fetch_row_count(table_name, api_key) -> int | None
    SQL: SELECT COUNT(*) as total FROM {table_name}
    返回整数；查询失败返回 None（警告日志，不抛异常）
```

**预估时长计算逻辑：**
```
如果 total_rows 不为 None 且 total_rows > 0：
    total_requests = ceil(total_rows / MAX_ROWS_PER_REQUEST)
    estimated_pull_minutes = round(total_requests / RATE_LIMIT_RPM, 2)
否则：
    estimated_pull_minutes = None
```

**变更理由：** 满足 ETL 团队对历史数据范围和全量拉取工时的评估需求。

---

### 变更 4-2：Story 2.1 文件（`_bmad-output/implementation-artifacts/2-1-triplewhale-数据源接入.md`）

**新增 Acceptance Criteria（在原有 AC 7 之后追加）：**

```
OLD:
（AC 7 结尾）
7. **Given** 单元测试环境（mock get_credentials + fixture）；**When** 运行 `tests/test_triplewhale.py`；
   **Then** 所有单元测试通过，覆盖全部 10 张表的路由分支，不需要真实 API Key

NEW:（追加以下三条）

8. **Given** 认证成功后传入有效 table_name；**When** 调用 `fetch_data_profile(table_name)`；
   **Then** 返回含 `earliest_date`、`total_rows`、`rate_limit_rpm`、`max_rows_per_request`、
   `estimated_pull_minutes` 的字典，两次 SQL 查询（MIN + COUNT）均在 30s 超时内完成，
   日志输出 `[triplewhale] 探测 {table_name} 数据概况 ... 成功`

9. **Given** 表当前无数据（如 creatives_table / ai_visibility_table）；
   **When** 调用 `fetch_data_profile(table_name)`；
   **Then** 返回 `earliest_date=None`、`total_rows=0`、`estimated_pull_minutes=None`，
   日志输出警告级别提示，不抛出异常

10. **Given** validate.py 运行 triplewhale 流程；
    **When** 全部 10 张表的 `fetch_data_profile` 执行完成；
    **Then** reporter 将"数据概况"区块写入 `reports/triplewhale-raw.md`，
    包含每张表的最早数据日期、总行数、rate limit、预估拉取时长
```

**新增 Tasks（在原有 Task 3 之后追加）：**

```
- [ ] Task 4: 实现 fetch_data_profile() 及私有辅助函数（AC: 8, 9）
  - [ ] Task 4.1: 在常量块追加 RATE_LIMIT_RPM、MAX_ROWS_PER_REQUEST、_TABLE_DATE_COLUMNS
  - [ ] Task 4.2: 实现 _fetch_earliest_date(table_name, api_key) -> str | None
  - [ ] Task 4.3: 实现 _fetch_row_count(table_name, api_key) -> int | None
  - [ ] Task 4.4: 实现 fetch_data_profile(table_name) -> dict（调用上述两个私有函数，组装返回值）

- [ ] Task 5: 新增单元测试覆盖 fetch_data_profile（AC: 8, 9）
  - [ ] Task 5.1: test_fetch_data_profile_success（mock 两次 SQL 查询返回有效数据，验证字典结构）
  - [ ] Task 5.2: test_fetch_data_profile_no_data（mock COUNT 返回 0，验证 estimated_pull_minutes=None）
  - [ ] Task 5.3: test_fetch_data_profile_query_failure（mock SQL 查询抛异常，验证返回 None 不传播）
  - [ ] Task 5.4: test_fetch_data_profile_invalid_table（验证抛出 ValueError）
```

**变更理由：** 与代码变更保持文档同步，为 dev agent 提供完整实现指引。

---

### 变更 4-3：`reporter.py`

**新增函数 `write_triplewhale_data_profile()`：**

```
OLD:
（reporter.py 末尾）

NEW:（追加）

def write_triplewhale_data_profile(profiles: list[dict]) -> None:
    """将 TripleWhale 数据概况写入 reports/triplewhale-raw.md（追加到文件末尾）。

    Args:
        profiles: fetch_data_profile() 返回值的列表，每张表一条。
    """
    渲染格式：
    ## 数据概况（TripleWhale 专属）

    | 表名 | 日期列 | 最早数据日期 | 总行数 | Rate Limit | 每次最大行数 | 全量拉取预估时长 |
    |------|-------|------------|--------|-----------|------------|----------------|
    | {table_name} | {date_column} | {earliest_date 或 "-"} | {total_rows 或 "-"} | 60 req/min | 1000 | {estimated_pull_minutes 分钟 或 "-"} |
```

**变更理由：** 报告呈现层与数据探测层分离，符合现有 reporter.py 职责设计。

---

## Section 5：实现交接

### 变更范围分类：**Minor**

可由开发团队直接实现，无需 PO/SM 重新规划 backlog，无需 PM/Architect 介入。

### 交接对象

**开发团队（dev agent）**，执行 Story 2.1 补充实现。

### 实现前置条件

- Story 2.1 分支已合并（或在原分支上追加）
- `sprint-status.yaml` 中 `2-1-triplewhale-数据源接入` 状态改为 `ready-for-dev`

### 实现顺序建议

1. 更新 Story 2.1 文件（添加 AC 8/9/10 + Task 4/5）
2. 实现 `sources/triplewhale.py` 新增部分
3. 更新 `reporter.py`
4. 补充 `tests/test_triplewhale.py`
5. 更新 `sprint-status.yaml`

### 成功验收标准

- [ ] `fetch_data_profile()` 对全部 10 张表均能正常调用
- [ ] creatives_table / ai_visibility_table（无数据表）返回优雅 None，不抛异常
- [ ] `triplewhale-raw.md` 末尾包含"数据概况"区块，10 张表信息齐全
- [ ] 新增测试用例全部通过（无需真实 API Key）
- [ ] `pytest tests/ -m "not integration"` 全量通过

---

*Sprint Change Proposal 由 bmad-correct-course 工作流生成*
*变更触发：新增功能需求 — TripleWhale 数据历史范围与全量拉取预估*
