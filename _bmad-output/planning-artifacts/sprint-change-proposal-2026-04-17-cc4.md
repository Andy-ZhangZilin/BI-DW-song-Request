# Sprint Change Proposal — CC#4
**日期：** 2026-04-17
**状态：** 已批准
**范围：** Moderate（需 PO/SM 协调）

---

## 第一节：问题摘要

**触发点：** Phase 2 数据采集落库（Epic 7/8）实施过程中，在拉取源数据时发现 Doris ODS 层所有表的字段定义严重不完整。

**核心问题：**
`init_doris_tables.py` 中的建表 SQL 为早期占位骨架，每张表仅有 3~13 个字段，而实际 API 接口返回的字段数量远超此范围（如 `ods_tw_pixel_orders` 实际有 ~95 个字段，`ods_tw_ads` 有 ~143 个字段）。作为 BI 数仓的 ODS 层，应落库接口返回的所有字段，不做业务筛选。

**附加问题：**
1. 缺少 ODS 层通用设计原则的架构规范
2. 各 collector 的 API 调用缺少速率限制，逐 ID 查询类接口（TikTok shop_product_performance、shop_video_performance_detail）在数据量大时会触发 API 封禁
3. 全量拉取起始时间各表不统一，需统一为测试用常量便于后续修改

---

## 第二节：影响分析

### Epic 影响
| Epic | 影响 | 说明 |
|------|------|------|
| Epic 6 | 直接影响 | `init_doris_tables.py` 需全量重写 |
| Epic 7 | 直接影响 | 所有 API collector 字段映射需补全 |
| Epic 8 | 直接影响 | 爬虫 collector 字段映射需补全 |

### Artifact 影响
| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `architecture.md` | 新增 | ARCH14/15/16 三条架构规范 |
| `init_doris_tables.py` | 全量重写 | 26 张表补全所有字段 |
| `collectors/tiktok_collector.py` | 修改 | 速率限制 + EARLIEST_DATE |
| `collectors/tw_collector.py` | 修改 | 速率限制 + EARLIEST_DATE |
| `collectors/awin_collector.py` | 修改 | 速率限制 + EARLIEST_DATE |
| `collectors/youtube_collector.py` | 修改 | 速率限制 |

### 技术影响
- 现有 Doris 表需 DROP 后重建（字段变更无法 ALTER 追加所有字段）
- collector 写入逻辑无需修改（`write_to_doris` 动态映射字段）

---

## 第三节：推荐方案

**选择：直接调整（Option 1）**

在现有 Epic 7/8 框架内补全，不需要回滚或 MVP 调整。

**理由：**
- 字段补全是 ODS 层的基本要求，不影响业务逻辑
- `write_to_doris` 已支持动态字段映射，collector 代码无需大改
- 速率限制为防御性修改，风险极低

**工作量：** 低（主要是 DDL 补全，已完成）
**风险：** 低（需重建 Doris 表，但当前为测试环境）

---

## 第四节：详细变更

### 变更 1 — architecture.md 新增三条规范

**ARCH14：ODS 层全字段落库原则**
- ODS 表包含 API 返回所有字段，不做业务筛选
- 英文字段直接使用原名；中文字段转英文 snake_case，COMMENT 写原中文
- 嵌套 list/dict → TEXT COMMENT '...(JSON)'
- 每表统一追加 `etl_time DATETIME COMMENT 'ETL写入时间'`

**ARCH15：API 调用速率限制规范**
- 逐 ID 查询：每次请求后 `sleep(0.3s)`
- 翻页类：每页请求后 `sleep(0.2s)`
- 429 错误：指数退避重试，最多 3 次

**ARCH16：全量拉取统一起始时间常量**
- 统一使用 `EARLIEST_DATE = "2026-03-01"`
- 测试完成后统一修改此常量

---

### 变更 2 — init_doris_tables.py 全量重写

| 数据源 | 表数量 | 字段变化 |
|--------|--------|----------|
| TripleWhale | 10 | 3~8 → 30~143 |
| TikTok | 4 | 9~13 → 20~30 |
| 钉钉 | 8 | 3~5 → 20~45（中文字段转英文） |
| Awin | 1 | 5 → 23 |
| PartnerBoost | 1 | 6 → 13 |
| YouTube | 1 | 8 → 25 |
| 水位线 | 1 | 不变 |

---

### 变更 3 — Collector 速率限制

| 文件 | 变更 |
|------|------|
| `tiktok_collector.py` | 逐 ID 循环加 `sleep(0.3)`，翻页加 `sleep(0.2)`，`EARLIEST_DATE = "2026-03-01"` |
| `tw_collector.py` | 按天循环加 `sleep(0.2)`，`TABLE_EARLIEST_DATES` 全部改为 `"2026-03-01"` |
| `awin_collector.py` | 翻页加 `sleep(0.2)`，`AWIN_EARLIEST_DATE` 默认值改为 `"2026-03-01"` |
| `youtube_collector.py` | 批量请求加 `sleep(0.3)` |

---

## 第五节：实施交接

**变更范围：** Moderate

**交接对象：**
- 开发团队：重建 Doris 表（DROP + 重新执行 `init_doris_tables.py`）
- 开发团队：验证各 collector 写入字段与新表结构匹配

**成功标准：**
1. `python init_doris_tables.py` 执行成功，26 张表创建完毕
2. 各 collector 运行后 Doris 表字段完整落库
3. TikTok 逐 ID 查询不再触发 429 错误

**注意事项：**
- 现有 Doris 测试表需先 DROP（字段变更不兼容 ALTER）
- 生产环境切换前需确认全量拉取时间常量已调整为正确历史起始日期
