# Sprint Change Proposal — 2026-04-15 CC Phase2

## 1. 问题摘要

**触发来源：** 第一阶段完成后，业务进入第二阶段（用户发起 BMAD CC 流程）

**问题描述：**

第一阶段（outdoor-data-validator 字段可行性验证工具）全部 5 个 Epic、23 个 Story 已于 2026-04-09 前完成。验证工具成功回答了"哪些字段能取到、哪些取不到"，并通过 AI 聚合分析完成了字段映射。

现需进入**第二阶段：数据采集与落库**——将各数据源的原始数据真正拉取并写入 Apache Doris 数据仓库，供后续报表开发和数据加工使用。

**变更性质：** 新阶段扩展（非纠错），第一阶段所有产物保持不变。

---

## 2. 影响分析

### Epic 影响

| 范围 | 结论 |
|------|------|
| Epic 1~5（已完成） | 不受影响，无需修改任何现有 Story |
| 新增 Epic 6/7/8 | 需新建，覆盖数据采集基础设施和全部数据源入库 |

### 产物影响

| 产物 | 影响类型 | 说明 |
|------|---------|------|
| `prd.md` | 需扩展 | 新增第二阶段章节（执行摘要、范围规划、FR31+、NFR补充、成功标准） |
| `architecture.md` | 需新增 | 新增 Phase 2 架构章节（Doris 表结构策略、水位线机制、分片并发设计） |
| `epics.md` | 需新增 | 新增 Epic 6/7/8 及全部 Story 定义 |
| `sprint-status.yaml` | 需更新 | 新增 Epic 6/7/8 条目 |
| `bi/python_sdk/outdoor_collector/` | 新增目录 | Phase 2 独立采集模块（SDK层 + 公共工具 + 采集脚本） |
| `bi/python_sdk/requirements.txt` | 可能更新 | 新增采集依赖 |

### 技术范围说明

- **代码位置：** `bi/python_sdk/outdoor_collector/`（独立目录，不与现有 `大户外事业部/` 混合）
- **调度平台：** 海豚调度（DolphinScheduler）
- **Doris 连接方式：** pymysql 直连（沿用现有 `doris_config.py` 单例模式）
- **现有 `bi/amazon-dingtalk-sdk-doris/` 为 Java 项目，与本次 Python 采集无直接复用关系**

### 目录结构

```
bi/python_sdk/
├── doris_config.py              # 现有（各业务目录各有副本，outdoor_collector 同理）
├── 大户外事业部/                 # 现有，不动
├── aliving价格监控/             # 现有，不动
├── checktask/                   # 现有，不动
│
└── outdoor_collector/           # Phase 2 新目录（独立部署单元）
    ├── doris_config.py          # Doris 连接单例（与现有模式一致，各目录自含）
    ├── sdk/                     # API 客户端层（供 collectors/ 复用）
    │   ├── __init__.py
    │   ├── tiktok/
    │   │   ├── __init__.py
    │   │   ├── auth.py          # refresh_token 换取、HmacSHA256 签名、shop_cipher 获取
    │   │   └── client.py        # 接口方法封装（订单、商品、财务等）
    │   ├── triplewhale/
    │   │   ├── __init__.py
    │   │   ├── auth.py          # API Key 认证
    │   │   └── client.py        # GraphQL/REST 请求封装、表路由
    │   └── dingtalk/
    │       ├── __init__.py
    │       ├── auth.py          # access_token 获取与有效期内复用
    │       └── client.py        # Bitable 记录读取接口
    ├── common/                  # 采集基础设施
    │   ├── __init__.py
    │   ├── watermark.py         # 水位线管理（Story 6.2）
    │   ├── chunked_fetch.py     # 分片并发框架（Story 6.3）
    │   └── doris_writer.py      # upsert 写入封装（Story 6.1）
    ├── collectors/              # 各数据源采集脚本
    │   ├── tw_collector.py      # TripleWhale（Story 7.1）
    │   ├── tiktok_collector.py  # TikTok Shop（Story 7.2）
    │   ├── dingtalk_collector.py # 钉钉 Bitable（Story 7.3）
    │   ├── youtube_collector.py # YouTube 统计（Story 7.4）
    │   ├── awin_collector.py    # Awin 联盟（Story 7.5）
    │   └── partnerboost_collector.py  # PartnerBoost 爬虫（Story 8.2）
    └── requirements.txt
```

**部署说明：** `outdoor_collector/` 整目录为独立部署单元，rsync 至服务器后直接在海豚调度中配置任务路径，无需额外 pip install 内部 SDK。

---

## 3. 推荐方案

**方案：直接新增 Epic（Option 1 — Direct Adjustment）**

- 第一阶段已完全交付，无需回滚任何已完成工作
- 新增 Epic 6/7/8 作为第二阶段独立交付单元
- 先完成 PRD 和架构文档更新，再启动 Epic/Story 开发排期

**工作量：** 中等
**风险：** 低（与现有代码无耦合）
**时间线影响：** 无（第一阶段不受影响）

---

## 4. 详细变更提案

### Epic 6：数据采集基础设施

**目标：** 在 `bi/python_sdk/outdoor_collector/` 下建立采集模块完整基础，包含 API 客户端 SDK 层、公共工具层（水位线、分片并发、写入封装）

#### Story 6.0：API 客户端 SDK 层建立

作为数据工程师，
我希望在 `outdoor_collector/sdk/` 下建立 TikTok、TripleWhale、钉钉三个 API 客户端模块，
以便后续所有采集脚本可复用统一的认证与请求封装，不重复实现。

**验收标准：**

- 创建 `sdk/tiktok/`：封装 refresh_token → access_token 换取（每次重新获取）、HmacSHA256 请求签名、shop_cipher 自动获取；对外暴露 `TikTokClient` 类
- 创建 `sdk/triplewhale/`：封装 API Key 认证、GraphQL/REST 请求发送、基础错误重试；对外暴露 `TripleWhaleClient` 类
- 创建 `sdk/dingtalk/`：封装 app_key/secret → access_token 获取与有效期内复用（避免重复换取）、Bitable 记录分页读取；对外暴露 `DingTalkClient` 类
- 凭证统一通过 `.env` 加载，SDK 内不硬编码任何密钥
- 各客户端提供统一日志格式：`[sdk][source] 操作描述 ... 成功/失败`
- 认证失败抛出明确异常，不静默返回空

#### Story 6.1：目录初始化与公共写入工具

作为数据工程师，
我希望初始化 `outdoor_collector/` 目录结构并建立公共 Doris 写入封装，
以便后续采集脚本有统一的写入入口。

**验收标准：**

- 创建完整目录结构：`sdk/`、`common/`、`collectors/`，各含 `__init__.py`
- 在目录根放置 `doris_config.py`（沿用单例模式，与现有业务目录保持一致）
- `common/doris_writer.py` 提供统一 upsert 写入封装：`write_to_doris(table, records, unique_keys)`
  - 内部使用 pymysql + `executemany`，batch_size=1000
  - 写入前执行 `SET enable_unique_key_partial_update = true` 和 `SET enable_insert_strict = false`
- 公共日志格式：`[source][table] 操作描述 ... 成功/失败`
- `requirements.txt` 列出所有第三方依赖（requests、pymysql、playwright、python-dotenv 等）
- Story 6.0（SDK层）必须先完成

#### Story 6.2：水位线管理器

作为数据工程师，
我希望有一套水位线管理机制，自动判断首次全量还是后续增量，
以便采集脚本无需手动区分运行模式。

**验收标准：**

- 在 Doris 中创建 `etl_watermark` 表，字段：`source`、`table_name`、`last_success_time`、`run_mode`、`updated_at`
- 提供 `get_watermark(source, table)` 和 `update_watermark(source, table, time)` 接口
- 首次运行（无水位线记录）→ 自动触发全量拉取
- 后续运行 → 读取水位线，以 `last_success_time` 为 `start_date` 做增量
- 支持 `--mode full` 参数强制重置水位线并重跑全量，无需手动删除水位线记录
- 水位线更新在每次成功写入 Doris 后执行，失败时不更新

#### Story 6.3：分片并发与断点续传框架

作为数据工程师，
我希望大数据量表（如 TripleWhale sessions_table）的全量拉取支持分片并发和断点续传，
以便避免单次长时间拉取超时或中断后需从头重来。

**验收标准：**

- `etl_watermark` 表扩展分片状态字段：`chunk_start`、`chunk_end`、`chunk_status`（pending/done/failed）
- 全量拉取时按时间区间自动分片，分片粒度可配置（默认 `chunk_days=30`）
- 支持并发执行多个分片，并发数可配置（默认 `workers=4`），受 API Rate Limit 约束
- 重启时自动跳过 `done` 状态分片，仅重跑 `pending` 和 `failed` 分片
- 单片失败不影响其他分片继续执行，失败分片状态记为 `failed` 并打印完整错误
- 提供通用 `chunked_fetch(source, table, fetch_fn, start, end, chunk_days, workers)` 接口

---

### Epic 7：API 类数据源采集落库

**目标：** 将 5 个 API 数据源的原始数据采集并写入对应 Doris 表

#### Story 7.1：TripleWhale 数据采集落库

作为数据工程师，
我希望能将 TripleWhale 的 10 张业务表数据采集并写入 Doris，
以便运营团队可以基于完整历史数据构建利润表和营销表现报表。

**验收标准：**

- 调用 `sdk/triplewhale/` 客户端（Story 6.0），不重复实现认证逻辑
- 支持 TripleWhale 全部已验证表（pixel_orders_table、pixel_joined_tvf、sessions_table、product_analytics_tvf 等）
- `sessions_table`（千万级数据）必须启用分片并发框架（Story 6.3），分片粒度和并发数可配置
- 各表独立维护水位线，互不干扰
- 增量模式：使用时间字段过滤（`start_date`/`end_date`）
- 写入策略：upsert，主键冲突则更新
- 单表失败不影响其他表继续执行
- 运行日志清晰记录每张表的拉取行数和写入状态

#### Story 7.2：TikTok Shop 数据采集落库

作为数据工程师，
我希望能将 TikTok Shop 的订单、财务等数据采集并写入 Doris，
以便后续构建 TikTok 销售表。

**验收标准：**

- 调用 `sdk/tiktok/` 客户端（Story 6.0），不重复实现 HmacSHA256 签名和 token 换取逻辑
- 支持已验证的 6 个接口路由（订单、商品、财务等）
- 增量模式：使用订单时间字段过滤，**归因窗口回溯 3 天**（补充晚到订单）
- 各接口独立水位线
- 写入策略：upsert，以订单 ID 为主键

#### Story 7.3：钉钉多维表数据采集落库

作为数据工程师，
我希望能将钉钉多维表（Bitable）中的业务数据采集并写入 Doris，
以便集中存储 KOL 信息、合作价格等内部管理数据。

**验收标准：**

- 调用 `sdk/dingtalk/` 客户端（Story 6.0），不重复实现 token 管理逻辑
- 支持已验证的多维表（包含 `kol_tidwe_内容上线` 等 Sheet）
- 增量策略：全量拉取 + upsert（钉钉 API 无时间过滤接口）
- 关联字段返回空时，Doris 对应字段写 NULL，不报错
- 写入策略：upsert，以钉钉行 ID 为主键

#### Story 7.4：YouTube 视频统计数据采集落库（钉钉 URL 驱动）

作为数据工程师，
我希望基于钉钉表中的视频 URL 字段，自动拉取对应 YouTube 视频的统计数据并写入 Doris，
以便 KOL 内容表可以关联真实播放数据。

**验收标准：**

- 数据来源驱动：从 Doris 中已入库的钉钉 `kol_tidwe_内容上线` 表读取 `内容发布链接` 字段
- 仅处理链接为 YouTube 域名的记录（`youtube.com/watch?v=` 或 `youtu.be/`）
- 提取 `video_id` 后调用 YouTube Data API v3 获取统计数据（viewCount、likeCount、commentCount 等）
- 写入 Doris 新表（YouTube 统计表），通过 `video_id` 或钉钉行 ID 与 KOL 表关联
- 增量策略：仅处理钉钉表中新增行（对应 video_id 在 YouTube 统计表中不存在）；已存在的定期刷新统计数据
- Story 7.4 执行依赖 Story 7.3 完成（钉钉数据已入库）

#### Story 7.5：Awin 联盟数据采集落库

作为数据工程师，
我希望能将 Awin 联盟交易数据采集并写入 Doris，
以便构建联盟营销渠道的佣金和转化报表。

**验收标准：**

- 支持 Awin Publisher API 的交易数据（Transactions）和聚合报表
- 增量模式：使用 `start_date`/`end_date` 时间过滤，**佣金状态回溯窗口可配置**（因佣金可能延迟确认）
- 写入策略：upsert，以 transaction_id 为主键

---

### Epic 8：爬虫类数据源采集落库

**目标：** 将爬虫类数据源的数据采集并写入对应 Doris 表

#### Story 8.1：CartSee EDM 数据采集落库

> **状态：`blocked - 暂缓`**
>
> CartSee 爬虫页面结构已变更，原有方案不可用。待确认新的数据获取方式后再启动开发。本 Story 保留占位，不进入当前开发排期。

#### Story 8.2：PartnerBoost 联盟数据采集落库

作为数据工程师，
我希望能每日自动抓取 PartnerBoost 的当天联盟数据并写入 Doris，
以便构建联盟营销渠道报表。

**验收标准：**

- 采用 Playwright 自动登录 PartnerBoost 后台
- **增量策略：每日定时执行，拉取当天数据**（平台 UI 无日期筛选器，仅展示当天）
- 写入策略：upsert，以日期 + 唯一记录 ID 为主键，确保幂等写入
- 遇验证码时抛出 RuntimeError 并中断，提示手动干预
- 不依赖水位线框架（每日全量当天数据）

#### Story 8.3：Facebook Business Suite 社媒数据采集落库

作为数据工程师，
我希望能将 Facebook Business Suite 的帖子/Reels 数据采集并写入 Doris，
以便构建社媒内容表现报表。

**验收标准：**

- 采用 Playwright 登录 Meta Business Suite，抓取帖子和 Reels 列表
- 增量策略：全量拉取 + upsert（UI 时间筛选稳定性待验证后可扩展增量）
- 写入字段：帖子 ID、标题、发布日期、状态、覆盖人数、获赞数、评论数、分享次数
- 写入策略：upsert，以帖子 ID 为主键
- 遇验证码时抛出 RuntimeError，不静默失败

---

## 5. 已确认技术决策

| # | 问题 | 确认结论 |
|---|------|---------|
| 1 | 调度机制 | **海豚调度（DolphinScheduler）** |
| 2 | Doris 连接方式 | **pymysql 直连**（沿用现有 `doris_config.py` 单例模式） |
| 3 | CartSee 暂缓原因 | **爬虫页面结构已变更**，待确认新方案后解锁 Story 8.1 |
| 4 | Phase 2 代码目录 | **`bi/python_sdk/outdoor_collector/`**（独立目录，不混入 `大户外事业部/`） |
| 5 | SDK 复用策略 | **在 `outdoor_collector/sdk/` 内建立三个 API 客户端**（tiktok/triplewhale/dingtalk），集中管理认证逻辑，collector 脚本调用 SDK，不重复实现 |
| 6 | 部署方式 | **整目录 rsync 到服务器**，`outdoor_collector/` 为自含部署单元，无需独立 pip install SDK |

---

## 6. 实施交接计划

### 变更范围分类：Moderate（需要 PO/SM + PM/架构师协同）

### 前置任务（开发启动前必须完成）

| 优先级 | 任务 | 负责方 | 状态 |
|--------|------|--------|------|
| P0 | 补充 PRD Phase 2 章节 | PM（bmad-edit-prd） | 进行中（新会话已启动） |
| P0 | 补充 Phase 2 架构文档 | 架构师（bmad-create-architecture） | 待启动 |
| P1 | 将 Epic 6/7/8 录入 epics.md | SM（bmad-create-epics-and-stories） | 待启动 |
| P1 | 更新 sprint-status.yaml | SM | 待启动 |
| P2 | 确认 CartSee 新的数据获取方式 | 达栋确认 | 待确认（不阻塞主线） |

### 开发顺序建议

```
Story 6.0（SDK层）
    ↓
Story 6.1（目录初始化 + 写入封装）
    ↓
Story 6.2（水位线）→ Story 6.3（分片并发）
    ↓
Epic 7（API 数据源，Story 7.3 先于 7.4）
    ↓
Epic 8（爬虫数据源，跳过 8.1）
```

### 成功标准

- 全部已验证数据源（除 CartSee 待确认外）的原始数据成功落库 Doris
- 水位线机制正常运转：首次全量、后续增量、中断续跑均验证通过
- TripleWhale sessions_table 分片并发拉取完成，无数据丢失
- 所有数据源写入均为幂等 upsert，重复运行不产生重复数据
- SDK 层（tiktok/triplewhale/dingtalk）被所有对应 collector 复用，无重复认证实现

---

**提案状态：已审批定稿**

**生成日期：** 2026-04-15
**审批日期：** 2026-04-15
**提案编号：** CC Phase2
