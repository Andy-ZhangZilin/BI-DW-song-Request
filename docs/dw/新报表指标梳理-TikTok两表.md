# 新增报表指标梳理 — TikTok 两张报表

**梳理日期：** 2026-04-27
**依据：** 指标梳理及数据需求沟通-2026.03.31.xlsx（Sheet: 数据表需求 2026.04.24）

---

## 总览

| 报表 | 视角 | 核心数据源 | 可用状态 |
|------|------|----------|---------|
| **A. TikTok达人表现表** | KOL/Creator 维度，含订单、佣金、寄样费 | TikTok联盟订单（Creator order）+ ods_tiktok_video_performances | ⚠️ 联盟订单表尚未接入 Doris |
| **B. TikTok自店铺视频表现表** | 视频维度，自店铺发布视频表现 | ods_tiktok_video_performances | ✅ 可直接加工（字段均已有） |

---

## 报表 A — TikTok达人表现表

### 字段来源梳理

| # | 报表字段 | 需求文档说明 | Doris 对应表 | 对应字段 | 状态 | 问题说明 |
|---|---------|------------|------------|---------|------|---------|
| 1 | **店铺** | — | `ods_tiktok_video_performances` | `shop_name` | ✅ 可用 | |
| 2 | **日期** | 寄样单创建时间 / 视频数据时间 / 订单创建时间（三种日期口径混用） | 联盟订单（未接入）/ `ods_tiktok_video_performances.collect_date` | `collect_date` / 订单创建时间 | ⚠️ 口径待统一 | **需业务确认：以哪个日期为准？** 联盟订单未接入时以 collect_date 代替 |
| 3 | **product_id** | TikTok Product ID | `ods_tiktok_video_performances` | `products` JSON → `id` | ⚠️ 需解析 JSON | `products` 字段为 JSON 数组，如 `[{"id":"172...","name":"..."}]`；一条视频可能关联多个商品 |
| 4 | **sku_id** | SKU ID（**仅联盟订单可获取**） | TikTok 联盟订单（未接入） | SKU ID | ❌ 数据源未接入 | 需求文档注："只有联盟订单能到这个级别"；`ods_tiktok_video_performances` 无 sku_id |
| 5 | **sku** | 通过 sku_id 关联本地 SKU | 待提供的 SKU 映射表 | `sku` | ❌ 映射表未提供 | 依赖 sku_id（同上）；需 TikTok product_id/sku_id → 内部 SKU 映射 |
| 6 | **订单类型** | 区分视频、直播、商品卡 | TikTok 联盟订单（未接入） | — | ❌ 数据源未接入 | `ods_tiktok_video_performances` 无该字段；联盟订单才有 content_type |
| 7 | **达人id** | Creator Username | `ods_tiktok_video_performances` | `username` | ✅ 可用 | |
| 8 | **内容类型** | Content Type（影刀-TikTok后台） | TikTok 联盟订单（未接入） | content_type | ❌ 数据源未接入 | 影刀采集的后台数据=ods_tiktok_video_performances，但该表无 content_type 字段 |
| 9 | **视频id** | Content ID（若多行则聚合） | `ods_tiktok_video_performances` | `video_id` | ✅ 可用 | |
| 10 | **视频URL** | Tiktok合作表 → 内容发布 | `ods_dingtalk_kol_tidwe_content` | `content_url` | ⚠️ 覆盖不全 | 需求文档标注"Piscifun内容发布记录不全"；已知 KOL 可取钉钉表 URL，其余需构造：`https://www.tiktok.com/@{username}/video/{video_id}` |
| 11 | **播放量** | ods_tiktok_video_performances.views，通过 video_id 关联 | `ods_tiktok_video_performances` | `views` | ✅ 可用 | 需求文档注：**没有 page_views 数据** |
| 12 | **订单数** | count(distinct Order ID)，来自联盟订单 | TikTok 联盟订单（未接入） | COUNT(DISTINCT order_id) | ❌ 数据源未接入 | `ods_tiktok_video_performances.sku_orders` 为汇总值（非 distinct 订单数），二者可能有差异 |
| 13 | **销量** | Quantity，来自联盟订单 | TikTok 联盟订单（未接入） | `quantity` | ❌ 数据源未接入 | `ods_tiktok_video_performances.items_sold` 为近似值，可临时代替 |
| 14 | **销售额** | Payment Amount，来自联盟订单 | TikTok 联盟订单（未接入） | `payment_amount` | ❌ 数据源未接入 | `ods_tiktok_video_performances.gmv_amount` 可临时代替 |
| 15 | **佣金** | Est. standard commission + Est. Shop Ads commission（预估佣金，来自联盟订单） | TikTok 联盟订单（未接入） | `est_commission` | ❌ 数据源未接入 | 需求文档注："Affiliate partner order 可不取，佣金使用预估佣金" |
| 16 | **寄样费** | 销售额=0 的 TikTok 订单，通过 username 关联达人，计算 SKU 寄样费（采购+关税+头程+尾程） | `ods_finance_bi_report_middle_multi_order` JOIN `ods_dingtalk_kol_tidwe_sample` | `amount` | ⚠️ JOIN 路径受阻 | 同报表7问题：`tracking_number`（TideWe内部单号）与 `platform_order_no`（Amazon格式）无法匹配 → 当前返回 0 行 |

### 数据源概览

| 数据源 | 在需求文档中的描述 | Doris 表名 | 接入状态 |
|-------|-----------------|----------|---------|
| 影刀-TikTok后台数据 | 达人视频表现（views、video_id、username、products） | `ods_tiktok_video_performances`（47,499行） | ✅ 已接入 |
| 联盟订单-Creator order | 订单数、销量、销售额、佣金、sku_id、content_type | ❌ Doris 中无对应 ODS 表 | ❌ **未接入** |
| 钉钉TikTok合作表-内容发布 | 视频URL（`content_url`）、promo_code | `ods_dingtalk_kol_tidwe_content`（819行，Piscifun覆盖不全） | ✅ 已接入（不完整） |
| 本地SKU映射 | product_id / sku_id → 内部 SKU | — | ❌ **映射表未提供** |
| 寄样费（多平台订单） | 寄样费用（采购/关税/头程/尾程） | `ods_finance_bi_report_middle_multi_order` | ✅ 已接入，但 JOIN 键不匹配 |

### ⚠️ 关键问题清单（需业务确认/解决）

| # | 问题 | 影响字段 | 紧急程度 |
|---|-----|---------|---------|
| P1 | **TikTok联盟订单（Creator order）尚未接入 Doris**，影响 sku_id、订单类型、内容类型、订单数、销量、销售额、佣金 共 7 个字段 | sku_id、订单类型、内容类型、订单数、销量、销售额、佣金 | 🔴 高 |
| P2 | **SKU ID 映射表未提供**：TikTok product_id（18位数字）→ 内部 SKU 的对照表缺失 | sku_id、sku | 🔴 高 |
| P3 | **日期口径不统一**：视频发布时间（`video_post_time`，部分为 NULL）、数据采集时间（`collect_date`）、订单创建时间（联盟订单）三者不同，以哪个为主？ | 日期 | 🟡 中 |
| P4 | **视频URL覆盖不全**：钉钉内容表仅记录部分 KOL 的视频 URL，Piscifun 尤其不全；建议以 `https://www.tiktok.com/@{username}/video/{video_id}` 规则构造作为兜底 | 视频URL | 🟡 中 |
| P5 | **寄样费 JOIN 路径受阻**：`tracking_number`（TideWe 内部格式）≠ `platform_order_no`（Amazon 格式），当前返回 0 行 | 寄样费 | 🟡 中 |
| P6 | **product_id 一视频多商品**：`ods_tiktok_video_performances.products` 为 JSON 数组，一条视频可挂多个商品，是展开成多行还是只取第一个？ | product_id | 🟡 中 |

---

## 报表 B — TikTok自店铺视频表现表

### 字段来源梳理

| # | 报表字段 | 需求文档说明 | Doris 对应表 | 对应字段 | 状态 | 问题说明 |
|---|---------|------------|------------|---------|------|---------|
| 1 | **店铺** | — | `ods_tiktok_video_performances` | `shop_name` | ✅ 可用 | |
| 2 | **日期** | — | `ods_tiktok_video_performances` | `collect_date` | ✅ 可用 | 注：`video_post_time` 为 bigint ms 时间戳，且部分为 NULL；建议用 `collect_date` |
| 3 | **product_id** | — | `ods_tiktok_video_performances` | `products` JSON → `[*].id` | ⚠️ 需解析 JSON | 同报表A P6；一视频可挂多个商品，需确认展开策略 |
| 4 | **视频id** | — | `ods_tiktok_video_performances` | `video_id` | ✅ 可用 | |
| 5 | **视频URL** | — | `ods_tiktok_video_performances` | 无直接字段 | ⚠️ 需构造 | 构造规则：`CONCAT('https://www.tiktok.com/@', username, '/video/', video_id)` |
| 6 | **视频标题** | — | `ods_tiktok_video_performances` | `title` | ✅ 可用 | |
| 7 | **播放量** | — | `ods_tiktok_video_performances` | `views` | ✅ 可用 | |
| 8 | **订单数** | — | `ods_tiktok_video_performances` | `sku_orders` | ✅ 可用（近似） | `sku_orders` 为平台汇总值，与"联盟订单 COUNT(distinct order_id)"口径略有不同，但对自店铺视频表够用 |
| 9 | **销量** | — | `ods_tiktok_video_performances` | `items_sold` | ✅ 可用 | |
| 10 | **销售额** | — | `ods_tiktok_video_performances` | `gmv_amount` | ✅ 可用 | 货币：`gmv_currency` = USD；注意该字段类型为 DECIMAL(18,4) |

### 结论

报表 B **所有字段均可从 `ods_tiktok_video_performances` 取到**，仅有两处处理要点：

1. **product_id**：从 `products` JSON 字段中解析，格式为 `[{"id":"...","name":"..."}]`；若一视频多商品需展开成多行（或只取第一个，待业务确认）
2. **视频URL**：无直接字段，按规则构造：`CONCAT('https://www.tiktok.com/@', username, '/video/', video_id)`

⚠️ **一个待确认点**：`product_id` 在 `ods_tiktok_video_performances` 中来自视频挂载的商品，但**不是每条视频都挂了商品**（`products = []` 或 NULL 时无 product_id）。需业务确认：无商品视频是否也需要出现在报表中？

---

## 两表差异对比

| 维度 | 报表 A（TikTok达人表现表） | 报表 B（TikTok自店铺视频表现表） |
|------|--------------------------|-------------------------------|
| 分析视角 | KOL/Creator 维度（以达人为主轴） | 视频维度（以视频内容为主轴） |
| 核心数据源 | 联盟订单（未接入）+ video_performances | 仅 video_performances |
| 精细度 | 需要 sku_id、订单明细、佣金 | 产品+视频汇总即可 |
| 可用状态 | ⚠️ 部分字段数据源未接入，**需先解决 P1** | ✅ 可立即开发 |
| 建设优先级建议 | 等联盟订单接入后再开发完整版；可先做临时版（用 video_performances 字段代替） | 优先开发 |

---

## 开发建议

### 报表 B — 立即可开发
- 所有字段均已有数据，直接按加工逻辑开发即可
- 加工文档可参考报表8（`dw-report8-tiktok-sales-by-type.md`）的基础结构

### 报表 A — 建议分两阶段

**阶段一（临时版，当前可做）：**
用 `ods_tiktok_video_performances` 现有字段输出：

| 字段 | 临时方案 |
|------|---------|
| product_id | `products` JSON 解析 |
| 达人id | `username` |
| 视频id | `video_id` |
| 视频URL | 规则构造 |
| 播放量 | `views` |
| 订单数 | `sku_orders`（汇总值，非 distinct 订单数） |
| 销量 | `items_sold` |
| 销售额 | `gmv_amount` |
| sku_id、sku、订单类型、内容类型、佣金 | 置 NULL，标注"待联盟订单接入" |
| 寄样费 | 置 NULL，标注"JOIN路径待修复" |

**阶段二（完整版，依赖数据接入）：**
1. 接入 TikTok 联盟订单（Creator order）为 `ods_tiktok_affiliate_order`
2. 提供 TikTok product_id → 内部 SKU 映射表
3. 修复寄样费 JOIN 键问题
