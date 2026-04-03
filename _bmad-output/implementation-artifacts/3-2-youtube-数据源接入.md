# Story 3.2: YouTube 数据源接入

Status: done

## Story

作为操作者，
我希望验证器能通过 API Key 连接 YouTube Data API v3 并抓取频道/视频数据字段，
以便我能获得 YouTube 数据的实际字段报告。

## Acceptance Criteria

1. **Given** `get_credentials()` 返回有效的 `YOUTUBE_API_KEY`，**When** 调用 `youtube.authenticate()`，**Then** 验证 API Key 有效性（发送一次轻量探测请求），返回 `True`，日志输出 `[youtube] 认证 ... 成功`

2. **Given** authenticate 成功后，**When** 调用 `youtube.fetch_sample()`，**Then** 通过 YouTube Data API v3 返回至少一条视频样本记录，超时设置为 30s，`table_name` 参数为 `None`（非 SQL 数据源）

3. **Given** fetch_sample 返回的样本数据，**When** 调用 `youtube.extract_fields(sample)`，**Then** 返回符合标准 FieldInfo 结构的字段列表

4. **Given** 字段提取完成，**When** `write_raw_report("youtube", fields, None, sample_count)` 被调用，**Then** `reports/youtube-raw.md` 包含实际字段表格和需求字段对照区块

5. **Given** API Key 无效（403 / 401 响应），**When** 调用 `authenticate()`，**Then** 日志输出 `[youtube] 认证 ... 失败：{HTTP 错误码和说明}`，返回 `False`

6. **Given** 单元测试环境（mock get_credentials + fixture），**When** 运行 `tests/test_youtube.py`，**Then** 所有单元测试通过，不需要真实 API Key

## Tasks / Subtasks

- [x] 创建 `sources/youtube.py` 实现三个公开接口（AC: #1 #2 #3）
  - [x] `authenticate()` — 用轻量探测请求验证 API Key（channels.list?part=id）
  - [x] `fetch_sample(table_name=None)` — 抓取 chart=mostPopular 热门视频，返回原始记录列表
  - [x] `extract_fields(sample)` — 扁平化提取 snippet.* 和 statistics.* 字段，返回 FieldInfo 列表

- [ ] 调用 reporter.py 生成双文件报告（AC: #4）
  - [ ] `write_raw_report("youtube", fields, None, len(sample))` — table_name 传 None
  - [ ] `init_validation_report("youtube")` — 首次创建 validation 模板

- [x] 创建 `tests/fixtures/youtube_sample.json`（AC: #6）
  - [x] 存放 YouTube Data API v3 `videos.list` 接口响应样本（含 snippet + statistics）

- [x] 创建 `tests/test_youtube.py`（AC: #5 #6）
  - [x] `test_authenticate_success` — mock requests.get 返回 200，验证返回 True
  - [x] `test_authenticate_failure_403` — mock requests.get 返回 403，验证返回 False
  - [x] `test_authenticate_failure_network_error` — mock requests.get 抛异常，验证返回 False
  - [x] `test_fetch_sample_returns_records` — mock requests.get，验证返回非空列表
  - [x] `test_extract_fields_returns_list` — 使用 fixture，验证列表非空
  - [x] `test_extract_fields_has_required_keys` — 验证每个字段含四键
  - [x] `test_extract_fields_empty_sample` — 传空列表，验证返回空列表

## Dev Notes

### 关键约束（必须遵守）

**1. 仅使用 `requests` 库，禁止 `googleapiclient`**

**2. 凭证必须通过 `import config.credentials as _creds_module` 获取**

**3. 日志格式严格遵守（所有模块统一格式）**

**4. FieldInfo 标准四键结构**

**5. `table_name` 传 `None`**

**6. HTTP 超时 30s**

### 文件位置汇总

| 文件 | 路径 | 状态 |
|------|------|------|
| Source 模块 | `sources/youtube.py` | 已创建 |
| 测试文件 | `tests/test_youtube.py` | 已创建 |
| 样本 Fixture | `tests/fixtures/youtube_sample.json` | 已创建 |

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2: YouTube 数据源接入]
- [Source: _bmad-output/planning-artifacts/architecture.md#Interface Contract Patterns]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- AC1-3, AC5-6 完整实现并通过 18 项单元测试
- AC4（reporter 调用）defer 至 Epic 5 validate.py dispatcher（架构设计决策）

### File List

- sources/youtube.py
- tests/test_youtube.py
- tests/fixtures/youtube_sample.json

### Review Findings

- [x] [Review][Patch] KeyError when YOUTUBE_API_KEY missing from credentials [sources/youtube.py:36,75]
- [x] [Review][Patch] No [youtube] log entry in fetch_sample() failure path [sources/youtube.py:84-85]
- [x] [Review][Defer] AC4 missing: write_raw_report not called in source module [sources/youtube.py] — deferred, pre-existing architecture decision (validate.py / Epic 5 dispatcher responsibility)
- [x] [Review][Defer] JSONDecodeError not handled in fetch_sample() resp.json() [sources/youtube.py:87] — deferred, pre-existing pattern (same as triplewhale)
