# Sprint Change Proposal — 2026-04-09

## 1. 问题摘要

**触发来源：** Story 3.2（YouTube 数据源接入）功能扩展需求

**问题描述：** 现有 `youtube` 数据源只支持拉取热门视频榜验证 API 可用性，无法按指定视频 URL 获取播放数（viewCount）和点赞数（likeCount）。用户需要将两种验证能力作为独立数据源分别运行，分别生成报告。同时 `get_credentials()` 全量校验机制导致单源运行时必须配齐所有凭证，使用不便。

**发现时间：** 2026-04-09，实现 `fetch_video_stats()` 后发现无法通过标准 CLI 流程运行

**证据：**
- 已成功实现 `fetch_video_stats()` 并通过真实 API 调用验证（video_id=1laF2zVhbcE, viewCount=919, likeCount=89）
- `python validate.py --source youtube` 因全量凭证校验失败（只配了 YOUTUBE_API_KEY）
- 新功能未集成到标准 CLI 流程，与其他数据源运行方式不一致

---

## 2. 影响分析

### Epic 影响

| Epic | 影响 | 说明 |
|------|------|------|
| Epic 3（标准 API 数据源接入） | 新增 Story 3.3 | youtube_url 按视频 URL 获取 statistics |
| Epic 1（基础设施） | Story 1.2 追加修改 | 凭证管理器支持按源校验 |
| Epic 5（CLI 入口） | Story 5.1 追加修改 | SOURCES 注册表新增 youtube_url |

### 文档影响

| 文档 | 变更类型 | 具体内容 |
|------|---------|---------|
| epics.md | 新增 | Story 3.3 定义 |
| architecture.md | 修改 | ARCH3 凭证管理新增按源映射表 |
| validate.py | 修改 | SOURCES 注册表 + 启动凭证校验逻辑 |
| credentials.py | 修改 | get_credentials() 增加 source_name 参数 |
| sprint-status.yaml | 新增 | Story 3.3 条目 |
| field_requirements.yaml | 可选新增 | youtube_url 字段需求 |
| .env.example | 无需修改 | YOUTUBE_API_KEY 已存在，youtube_url 共用 |

### 技术影响

- 新建 `sources/youtube_url.py` 模块
- 新建 `tests/test_youtube_url.py` 测试
- `credentials.py` 增加 `_SOURCE_CREDENTIALS` 映射表
- `validate.py` 启动校验逻辑从 `get_credentials()` 改为 `get_credentials(source_name=args.source)`
- `--all` 模式行为不变（全量校验）

---

## 3. 推荐方案

**选择：直接调整**

在现有 Epic 结构下新增 Story 3.3，修改凭证管理器和 CLI 注册表。

**理由：**
- 核心函数（`extract_video_id`, `fetch_video_stats`）已实现并通过 14 个单元测试
- 凭证映射改动向后兼容：`--all` 保持全量校验，`--source` 改为按源校验
- 符合 NFR7 插件式扩展原则，新增 source 模块无需改核心逻辑
- 工作量：**低**
- 风险：**低**

---

## 4. 详细变更提案

### 4.1 epics.md — 新增 Story 3.3

**新增内容：**

```markdown
### Story 3.3 — YouTube URL 视频统计数据源接入（youtube_url）

**需求来源：** FR7（YouTube API Key 认证）扩展
**凭证：** YOUTUBE_API_KEY（与 youtube 共用）

**AC：**
1. `sources/youtube_url.py` 实现 ARCH2 三接口契约（authenticate / fetch_sample / extract_fields）
2. `authenticate()` 复用 YouTube API Key 验证逻辑
3. `fetch_sample()` 使用写死的视频 URL 调用 `videos.list?id=<video_id>&part=statistics`
4. `extract_fields()` 返回标准 FieldInfo 列表，包含 viewCount / likeCount
5. `python validate.py --source youtube_url` 正常运行，生成 `reports/youtube_url-raw.md`
6. 单元测试全 mock，无需真实 API Key
```

### 4.2 architecture.md — 凭证管理器修改

**修改内容：** ARCH3 凭证管理章节

`get_credentials(source_name=None)` 增加可选参数：
- `source_name=None`（默认）：全量校验，行为不变（`--all` 模式）
- `source_name="youtube"`：只校验该源所需凭证

新增源-凭证映射表 `_SOURCE_CREDENTIALS`：

| 数据源 | 所需凭证 |
|--------|---------|
| triplewhale | TRIPLEWHALE_API_KEY |
| tiktok | TIKTOK_APP_KEY, TIKTOK_APP_SECRET |
| dingtalk | DINGTALK_APP_KEY, DINGTALK_APP_SECRET, DINGTALK_WORKBOOK_ID |
| youtube | YOUTUBE_API_KEY |
| youtube_url | YOUTUBE_API_KEY |
| awin | AWIN_API_TOKEN, AWIN_ADVERTISER_ID |
| cartsee | CARTSEE_USERNAME, CARTSEE_PASSWORD |
| partnerboost | PARTNERBOOST_USERNAME, PARTNERBOOST_PASSWORD |
| facebook | FACEBOOK_USERNAME, FACEBOOK_PASSWORD |
| youtube_studio | YOUTUBE_STUDIO_EMAIL, YOUTUBE_STUDIO_PASSWORD |

### 4.3 validate.py — SOURCES 注册表

**修改内容：** 新增 `youtube_url` 条目，启动凭证校验传入 `source_name`

### 4.4 sprint-status.yaml

**新增内容：** `3-3-youtube-url-视频统计数据源接入: backlog`

---

## 5. 实施交接

**变更范围分类：Minor** — 开发团队可直接实施

**交接：**

| 角色 | 职责 |
|------|------|
| 开发（Amelia） | 创建 sources/youtube_url.py、修改 credentials.py、修改 validate.py、新增测试 |
| SM（Bob） | 更新 sprint-status.yaml、创建 Story 3.3 文件 |
| 架构（Winston） | 更新 architecture.md 凭证映射表和数据源注册表 |

**成功标准：**
1. `python validate.py --source youtube_url` 正常输出报告
2. `python validate.py --source youtube` 只需配置 YOUTUBE_API_KEY 即可运行
3. `python validate.py --all` 行为不变（全量凭证校验）
4. 所有单元测试通过
