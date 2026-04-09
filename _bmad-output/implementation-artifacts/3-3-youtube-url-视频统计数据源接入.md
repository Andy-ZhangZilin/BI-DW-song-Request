# Story 3.3: YouTube URL 视频统计数据源接入（youtube_url）

Status: ready-for-dev

## Story

作为操作者，
我希望通过指定 YouTube 视频 URL 获取该视频的播放数和点赞数，
以便我能作为独立数据源验证 YouTube 视频统计数据的可用性。

## Acceptance Criteria

1. **Given** `sources/youtube_url.py` 已创建，**When** 检查模块接口，**Then** 实现 ARCH2 三接口契约（`authenticate()` / `fetch_sample()` / `extract_fields()`）

2. **Given** `get_credentials()` 返回有效的 `YOUTUBE_API_KEY`，**When** 调用 `youtube_url.authenticate()`，**Then** 复用 YouTube API Key 验证逻辑（channels.list 轻量探测），返回 `True`，日志输出 `[youtube_url] 认证 ... 成功`

3. **Given** authenticate 成功后，**When** 调用 `youtube_url.fetch_sample()`，**Then** 使用写死的视频 URL `https://www.youtube.com/watch?v=1laF2zVhbcE` 调用 `videos.list?id=<video_id>&part=statistics`，返回含 statistics 的原始记录列表

4. **Given** fetch_sample 返回的样本数据，**When** 调用 `youtube_url.extract_fields(sample)`，**Then** 返回标准 FieldInfo 列表，包含 viewCount / likeCount 等 statistics 字段

5. **Given** `python validate.py --source youtube_url` 执行完成，**When** 检查输出，**Then** 正常运行并生成 `reports/youtube_url-raw.md`

6. **Given** 单元测试环境（mock get_credentials + fixture），**When** 运行 `tests/test_youtube_url.py`，**Then** 所有单元测试通过，全 mock 无需真实 API Key

## Tasks / Subtasks

- [ ] 创建 `sources/youtube_url.py` 实现三接口契约（AC: #1 #2 #3 #4）
  - [ ] `authenticate()` — 复用 youtube.py 同款 channels.list 探测逻辑（独立实现，SOURCE_NAME 改为 "youtube_url"）
  - [ ] `fetch_sample(table_name=None)` — 写死 URL，调用 `youtube.extract_video_id()` 解析 video_id，再请求 videos.list?part=statistics
  - [ ] `extract_fields(sample)` — 扁平化提取 statistics 下的 FieldInfo 列表

- [ ] 修改 `config/credentials.py`（AC: #5）
  - [ ] `get_credentials()` 新增可选参数 `source_name: str = None`
  - [ ] 新增 `_SOURCE_CREDENTIALS` 映射表（每个源对应哪些凭证 key）
  - [ ] `source_name=None` 时全量校验（--all 模式不变）
  - [ ] `source_name` 有值时只校验该源所需凭证

- [ ] 修改 `validate.py`（AC: #5）
  - [ ] `SOURCES` 注册表新增 `"youtube_url": "sources.youtube_url"`
  - [ ] 启动凭证校验改为 `get_credentials(source_name=args.source)`

- [ ] 创建 `tests/test_youtube_url.py`（AC: #6）
  - [ ] `test_authenticate_success` — mock requests.get 返回 200
  - [ ] `test_authenticate_failure` — mock requests.get 返回 403
  - [ ] `test_fetch_sample_returns_records` — mock API 返回含 statistics 的 items
  - [ ] `test_fetch_sample_uses_hardcoded_url` — 验证请求的 video_id 为 "1laF2zVhbcE"
  - [ ] `test_fetch_sample_raises_on_empty` — API 返回空 items 时抛 RuntimeError
  - [ ] `test_extract_fields_contains_viewcount_likecount` — 验证 FieldInfo 含 viewCount/likeCount
  - [ ] `test_extract_fields_empty_sample` — 空列表输入返回空列表
  - [ ] `test_extract_fields_has_required_keys` — 每个 FieldInfo 含四键

## Dev Notes

### 关键约束（必须遵守）

**1. 复用 youtube.py 已有函数**
- `sources/youtube.py` 中的 `extract_video_id(url)` 和 `fetch_video_stats(url)` 已通过 14 个单元测试
- `youtube_url.py` 的 `fetch_sample()` 应调用 `youtube.extract_video_id()` 解析 video_id
- **不要**复制粘贴这些函数到 youtube_url.py，直接 import 复用

**2. 凭证管理改造要点**
- `get_credentials(source_name=None)` 签名变更，保持向后兼容
- `_SOURCE_CREDENTIALS` 映射表内容参见 sprint-change-proposal-2026-04-09.md 4.2 节：

```python
_SOURCE_CREDENTIALS = {
    "triplewhale": ["TRIPLEWHALE_API_KEY"],
    "tiktok": ["TIKTOK_APP_KEY", "TIKTOK_APP_SECRET"],
    "dingtalk": ["DINGTALK_APP_KEY", "DINGTALK_APP_SECRET", "DINGTALK_WORKBOOK_ID"],
    "youtube": ["YOUTUBE_API_KEY"],
    "youtube_url": ["YOUTUBE_API_KEY"],
    "awin": ["AWIN_API_TOKEN", "AWIN_ADVERTISER_ID"],
    "cartsee": ["CARTSEE_USERNAME", "CARTSEE_PASSWORD"],
    "partnerboost": ["PARTNERBOOST_USERNAME", "PARTNERBOOST_PASSWORD"],
    "facebook": ["FACEBOOK_USERNAME", "FACEBOOK_PASSWORD"],
    "youtube_studio": ["YOUTUBE_STUDIO_EMAIL", "YOUTUBE_STUDIO_PASSWORD"],
}
```

- `source_name=None`：遍历 `_REQUIRED_KEYS` 全量校验（现有行为不变）
- `source_name` 有值：只从 `_SOURCE_CREDENTIALS[source_name]` 取 key 列表校验

**3. validate.py 改动最小化**
- SOURCES 字典新增一行：`"youtube_url": "sources.youtube_url"`
- 启动凭证校验改为 `get_credentials(source_name=args.source)`（`--all` 时 `args.source` 为 None，触发全量校验，行为不变）

**4. 接口契约与日志格式**
- SOURCE_NAME = "youtube_url"
- 日志格式：`[youtube_url] 操作描述 ... 成功/失败`
- FieldInfo 标准四键：`field_name` / `data_type` / `sample_value` / `nullable`
- 凭证通过 `import config.credentials as _creds_module` 获取，禁止 `os.getenv()`

**5. 写死的验证用视频 URL**
- `_DEFAULT_URL = "https://www.youtube.com/watch?v=1laF2zVhbcE"`
- 这是已通过真实 API 验证的视频（viewCount=919, likeCount=89）

**6. HTTP 超时 30s**

### 文件位置汇总

| 文件 | 路径 | 操作 |
|------|------|------|
| Source 模块 | `sources/youtube_url.py` | 新建 |
| 凭证管理器 | `config/credentials.py` | 修改 |
| CLI 入口 | `validate.py` | 修改 |
| 测试文件 | `tests/test_youtube_url.py` | 新建 |

### 前置 Story 经验（Story 3.2 youtube）

- `authenticate()` 使用 channels.list?part=id 探测，配额消耗最低
- `extract_fields()` 使用递归 `_flatten()` 处理嵌套 dict
- mock 模式：`patch("sources.youtube.requests.get", return_value=mock_resp)` — youtube_url.py 中对应路径为 `sources.youtube_url.requests.get`
- conftest.py 的 `mock_credentials` fixture 已就绪，测试中直接用 `def test_xxx(mock_credentials):` 即可

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-09.md#4.1]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2: YouTube 数据源接入]
- [Source: _bmad-output/planning-artifacts/architecture.md#Interface Contract Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#ARCH2 统一 source 接口契约]
- [Source: _bmad-output/planning-artifacts/architecture.md#ARCH3 凭证加载入口]

## Dev Agent Record

### Agent Model Used

claude-opus-4-6

### Debug Log References

### Completion Notes List

### File List
