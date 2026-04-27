# 加工文档 — 报表6：KOL内容表现表

**关联报表：** 营销推广-KOL效果
**需求时间：** 2026-05-15 | **上线时间：** 2026-06-12
**文档版本：** v2.0 | **日期：** 2026-04-24

> **v2.0 变更（2026-04-24）：** 经 Doris 实际数据验证：
> 1. 全部 ODS 表名更新为实际表名
> 2. TikTok 数据已扁平化，无嵌套 `videos[]`，直接使用 `video_id`、`views`、`sku_orders`、`gmv_amount` 等字段
> 3. YouTube 通过 `ods_youtube_video_stats.dingtalk_record_id` = `ods_dingtalk_kol_tidwe_content.record_id` 直接关联，**无需 URL 解析**
> 4. `ods_tiktok_shop_video_performance_detail` 有 2,218 行数据（可用）
> 5. `actual_publish_date` 已为 DATE 类型，无需毫秒时间戳转换
> 6. `ods_tiktok_video_performances.video_post_time` 为 bigint（毫秒时间戳），需转换

---

## ODS 表名对照

| 原文档名称（设计阶段） | 实际 Doris 表名 | 行数 | 说明 |
|---------------------|----------------|------|------|
| `ods_dd_kol_content` | `ods_dingtalk_kol_tidwe_content` | 819行 | 内容发布记录（含 `record_id`） |
| `ods_tiktok_video_perf` | `ods_tiktok_video_performances` | — | TikTok 视频表现（扁平化字段） |
| `ods_tiktok_video_detail` | `ods_tiktok_shop_video_performance_detail` | 2,218行 | TikTok 视频互动明细 |
| `ods_youtube_url` | `ods_youtube_video_stats` | — | YouTube 视频统计（含 `dingtalk_record_id`） |
| `ods_tw_pixel_orders` | `ods_tw_pixel_orders` | — | TW 像素订单归因表（表名不变） |

---

## 整体数据血缘

```
ODS 层                                  DWD 层                        DWS 层                          ADS 层
─────────────────────────────────────────────────────────────────────────────────────────────────────────
ods_dingtalk_kol_tidwe_content ──────┐
ods_tiktok_video_performances ───────┤
ods_tiktok_shop_video_performance ───┼──► dwd_kol_content_detail ──► dws_kol_content_snap ──► ads_kol_content_performance
  _detail                            │
ods_youtube_video_stats ─────────────┤
ods_tw_pixel_orders ─────────────────┘
```

**说明：** 报表6以钉钉内容上线记录为主键，关联 TikTok / YouTube 平台接口获取实时播放、互动数据，并通过折扣码（`promo_code`）在 TW pixel_orders 中归因 KOL 带来的销售转化。TikTok 达人 GMV 直接从 `ods_tiktok_video_performances.gmv_amount` 取值；YouTube KOL GMV 通过折扣码在 pixel_orders 匹配。

**YouTube JOIN 优化：** `ods_youtube_video_stats` 含 `dingtalk_record_id` 字段，直接与 `ods_dingtalk_kol_tidwe_content.record_id` 关联，无需从 URL 解析视频 ID。

---

## ODS 源表说明

| ODS 表名 | 来源接口 | 业务含义 | 关键字段 |
|---------|---------|---------|---------|
| `ods_dingtalk_kol_tidwe_content` | dingtalk / kol_tidwe_内容上线 | KOL内容发布记录（819行） | `record_id`, `kol_id`, `publish_platform`, `actual_publish_date`, `content_url`, `promo_code`, `promoted_product`, `cooperation_mode`, `views`, `content_type` |
| `ods_tiktok_video_performances` | tiktok / video_performances | TikTok 达人视频表现（扁平化） | `video_id`, `username`, `video_post_time`（bigint, ms）, `views`, `sku_orders`, `items_sold`, `gmv_amount`, `gmv_currency`, `click_through_rate`, `shop_id`, `collect_date` |
| `ods_tiktok_shop_video_performance_detail` | tiktok / shop_video_performance_detail | TikTok 视频互动明细（2,218行，按 video_id 查询） | `video_id`, `traffic_views`, `traffic_likes`, `traffic_comments`, `traffic_shares`, `traffic_new_followers`, `sales_overall_items_sold`, `sales_overall_gmv_amount`, `collect_date` |
| `ods_youtube_video_stats` | youtube_url | YouTube 视频统计数据（含钉钉记录关联字段） | `video_id`, `dingtalk_record_id`, `view_count`, `like_count`, `comment_count`, `published_at` |
| `ods_tw_pixel_orders` | triplewhale / pixel_orders | TW 像素订单归因表 | `discount_code`, `order_revenue`, `orders_quantity`, `product_quantity_sold_in_order`, `is_new_customer`, `shop_name` |

---

## DWD 层

### `dwd_kol_content_detail`

**业务含义：** KOL 内容发布明细，以内容 URL 为主键，整合钉钉发布记录与平台实时表现数据
**粒度：** 每条内容发布记录（`content_url` 为主键）× 最新快照
**更新策略：** 每日全量覆盖

#### 数据血缘

```
ods_dingtalk_kol_tidwe_content（主表，record_id + kol_id + content_url）
  LEFT JOIN ods_tiktok_video_performances
    ON REGEXP_EXTRACT(content_url, '/video/([0-9]+)', 1) = video_id
    （仅 publish_platform = 'TT' 的记录参与 JOIN）
  LEFT JOIN ods_tiktok_shop_video_performance_detail
    ON REGEXP_EXTRACT(content_url, '/video/([0-9]+)', 1) = video_id
    （仅 publish_platform = 'TT' 的记录，获取互动明细）
  LEFT JOIN ods_youtube_video_stats
    ON record_id = dingtalk_record_id
    （仅 publish_platform = 'YT' 的记录参与 JOIN；直接通过 record_id 关联，无需 URL 解析）
  LEFT JOIN ods_tw_pixel_orders
    ON promo_code = discount_code
    （非 TikTok 渠道归因；聚合 SUM order_revenue / COUNT orders / SUM items_sold）
       ↓
dwd_kol_content_detail
```

**关联说明：**
- TikTok 视频ID提取：从 `content_url`（如 `https://www.tiktok.com/@user/video/7536784906265890103`）中提取末段数字，与 `ods_tiktok_video_performances.video_id` 关联
- YouTube JOIN：直接使用 `ods_youtube_video_stats.dingtalk_record_id` = `ods_dingtalk_kol_tidwe_content.record_id`（**已验证，JOIN 正常**）
- TikTok 平台数据优先于钉钉手工维护的 `views`
- YouTube 统计数据优先于钉钉手工维护的 `views`
- TikTok GMV：直接取 `gmv_amount`（USD，`gmv_currency = 'USD'` 已确认）
- YouTube / 其他平台 GMV：通过 `promo_code` ↔ `discount_code` 在 pixel_orders 归因

#### 字段定义

| 字段名 | 类型 | 来源表 | 来源字段 | 加工逻辑 |
|-------|------|-------|----|--------|
| `partition_dt` | DATE | — | — | 等于数据提取日期 |
| `kol_id` | VARCHAR | ods_dingtalk_kol_tidwe_content | `kol_id` | 直取（主键之一） |
| `content_url` | VARCHAR | ods_dingtalk_kol_tidwe_content | `content_url` | 直取（主键之一，全局唯一） |
| `record_id` | VARCHAR | ods_dingtalk_kol_tidwe_content | `record_id` | 直取；用于 YouTube JOIN |
| `content_id` | VARCHAR | — | — | 从 `content_url` 解析 TikTok 视频 ID（`publish_platform = 'TT'`）；YouTube 使用 `record_id` 直接关联，不再解析 URL |
| `platform` | VARCHAR | ods_dingtalk_kol_tidwe_content | `publish_platform` | 直取（如 `YT` / `TT`） |
| `content_type` | VARCHAR | ods_dingtalk_kol_tidwe_content | `content_type` | 直取（如 `YT 长视频` / `TT视频`） |
| `publish_dt` | DATE | ods_dingtalk_kol_tidwe_content | `actual_publish_date` | 直取（已为 DATE 类型，无需转换） |
| `promo_code` | VARCHAR | ods_dingtalk_kol_tidwe_content | `promo_code` | 直取；用于 pixel_orders 归因 |
| `promotion_product` | VARCHAR | ods_dingtalk_kol_tidwe_content | `promoted_product` | 直取 |
| `tiktok_username` | VARCHAR | ods_tiktok_video_performances | `username` | TikTok 平台用户名；非 TikTok 记录置 NULL |
| `views_cnt` | BIGINT | ods_dingtalk_kol_tidwe_content / ods_tiktok_video_performances / ods_youtube_video_stats | `views` / `views` / `view_count` | 优先级：TikTok: `ods_tiktok_video_performances.views`；YouTube: `ods_youtube_video_stats.view_count`；其他/无接口数据：钉钉手工 `views`（VARCHAR, CAST AS BIGINT） |
| `likes_cnt` | BIGINT | ods_tiktok_shop_video_performance_detail / ods_youtube_video_stats | `traffic_likes` / `like_count` | TikTok: `traffic_likes`（via video_id JOIN）；YouTube: `like_count`；其他平台: NULL |
| `comments_cnt` | BIGINT | ods_tiktok_shop_video_performance_detail / ods_youtube_video_stats | `traffic_comments` / `comment_count` | TikTok: `traffic_comments`；YouTube: `comment_count`；其他: NULL |
| `shares_cnt` | BIGINT | ods_tiktok_shop_video_performance_detail | `traffic_shares` | 仅 TikTok 可用；其他平台: NULL |
| `click_through_rate` | DECIMAL(8,4) | ods_tiktok_video_performances | `click_through_rate` | TikTok 视频点击转化率；其他平台: NULL |
| `orders_cnt` | BIGINT | ods_tiktok_video_performances / ods_tw_pixel_orders | `sku_orders` / COUNT per discount_code | TikTok: `sku_orders`；非 TikTok: `COUNT(*) FROM ods_tw_pixel_orders WHERE discount_code = promo_code` |
| `items_qty` | BIGINT | ods_tiktok_video_performances / ods_tw_pixel_orders | `items_sold` / SUM(`product_quantity_sold_in_order`) | TikTok: `items_sold`；非 TikTok: SUM per discount_code |
| `gmv_amt` | DECIMAL(18,2) | ods_tiktok_video_performances / ods_tw_pixel_orders | `gmv_amount` / SUM(`order_revenue`) | TikTok: `gmv_amount`（USD）；非 TikTok: SUM(`order_revenue`) per discount_code（USD） |
| `new_customer_cnt` | BIGINT | ods_tw_pixel_orders | `is_new_customer` | 非 TikTok: `WHERE discount_code = promo_code AND is_new_customer = 1 → COUNT`；TikTok: NULL |
| `etl_load_ts` | TIMESTAMP | — | — | ETL 写入时间 |
| `data_source` | VARCHAR | — | — | 常量 `'dingtalk+tiktok+youtube+triplewhale'` |

#### 关键加工逻辑

**TikTok 视频ID提取（仅 TikTok 需要，YouTube 直接用 record_id）：**

```sql
-- TikTok URL：https://www.tiktok.com/@username/video/7536784906265890103
content_id = CASE
  WHEN publish_platform = 'TT'
    THEN REGEXP_EXTRACT(content_url, '/video/([0-9]+)', 1)
  ELSE NULL  -- YouTube 使用 record_id 直接 JOIN，不需要 content_id
END
```

**YouTube JOIN（直接关联，无需 URL 解析）：**

```sql
-- 直接通过 dingtalk_record_id 关联（已验证 JOIN 正常）
LEFT JOIN ods_youtube_video_stats yt
  ON yt.dingtalk_record_id = c.record_id
  AND c.publish_platform = 'YT'
```

**播放量优先级：**

```sql
views_cnt = CASE
  WHEN publish_platform = 'TT' AND tk.views IS NOT NULL THEN tk.views          -- ods_tiktok_video_performances.views
  WHEN publish_platform = 'YT' AND yt.view_count IS NOT NULL THEN yt.view_count  -- ods_youtube_video_stats.view_count
  ELSE CAST(c.views AS BIGINT)   -- 钉钉手工维护兜底（ods_dingtalk_kol_tidwe_content.views, VARCHAR）
END
```

**TikTok 互动数据（ods_tiktok_shop_video_performance_detail）：**

```sql
-- JOIN via video_id（TikTok URL 提取后的 content_id）
LEFT JOIN ods_tiktok_shop_video_performance_detail td
  ON td.video_id = REGEXP_EXTRACT(c.content_url, '/video/([0-9]+)', 1)
  AND c.publish_platform = 'TT'

likes_cnt    = td.traffic_likes
comments_cnt = td.traffic_comments
shares_cnt   = td.traffic_shares
```

**GMV 归因逻辑：**

```sql
-- TikTok 达人：直接取视频GMV
gmv_amt (TikTok) = CAST(tk.gmv_amount AS DECIMAL(18,2))
-- 注：gmv_currency 已确认为 'USD'

-- YouTube KOL 及其他平台：折扣码归因
gmv_amt (other) = (
  SELECT COALESCE(SUM(order_revenue), 0)
  FROM ods_tw_pixel_orders
  WHERE discount_code = c.promo_code
)
-- 注：promo_code 为 NULL 时 gmv_amt = NULL
```

**TikTok video_post_time 转换（时间展示用）：**

```sql
-- video_post_time 为 bigint 毫秒时间戳，转换为 DATETIME 展示
FROM_UNIXTIME(video_post_time / 1000) AS video_post_datetime
```

---

## DWS 层

### `dws_kol_content_snap`

**业务含义：** KOL 内容表现快照，以内容 URL 为主键，输出最新表现数据
**粒度：** 每条内容记录（`content_url` 为主键）× 最新快照
**更新策略：** 每日全量覆盖（用新快照值覆盖历史行，保留最新播放/互动数）
**下游使用：** ads_kol_content_performance

#### 数据血缘

```
dwd_kol_content_detail
  JOIN dim_kol ON kol_id（获取 kol_full_name, platform, follower_cnt 等基础属性）
       ↓
dws_kol_content_snap
```

#### 字段定义

| 字段名 | 类型 | 含义 | 加工逻辑概述 |
|-------|------|------|------------|
| `partition_dt` | DATE | 快照日期 | 等于 ETL 提取日期 |
| `kol_id` | VARCHAR | KOL ID | 直取 dwd |
| `kol_full_name` | VARCHAR | KOL 全名 | JOIN dim_kol |
| `platform` | VARCHAR | 发布平台 | 直取 dwd（如 YT / TT） |
| `content_url` | VARCHAR | 内容发布链接 | 直取 dwd（主键） |
| `record_id` | VARCHAR | 钉钉记录ID | 直取 dwd（用于 YouTube 关联溯源） |
| `content_id` | VARCHAR | TikTok 视频ID | 直取 dwd（仅 TikTok） |
| `content_type` | VARCHAR | 内容类型 | 直取 dwd |
| `publish_dt` | DATE | 实际发布日期 | 直取 dwd（DATE 类型） |
| `promo_code` | VARCHAR | 推广码 | 直取 dwd |
| `promotion_product` | VARCHAR | 推广产品 | 直取 dwd |
| `tiktok_username` | VARCHAR | TikTok 用户名 | 直取 dwd |
| `views_cnt` | BIGINT | 播放量 | 直取 dwd |
| `likes_cnt` | BIGINT | 点赞数 | 直取 dwd |
| `comments_cnt` | BIGINT | 评论数 | 直取 dwd |
| `shares_cnt` | BIGINT | 转发数 | 直取 dwd（仅 TikTok） |
| `click_through_rate` | DECIMAL(8,4) | 点击转化率 | 直取 dwd（仅 TikTok） |
| `orders_cnt` | BIGINT | 订单数 | 直取 dwd |
| `items_qty` | BIGINT | 销量 | 直取 dwd |
| `gmv_amt` | DECIMAL(18,2) | 销售额（USD） | 直取 dwd |
| `new_customer_cnt` | BIGINT | 新客数 | 直取 dwd |
| `etl_load_ts` | TIMESTAMP | ETL写入时间 | ETL 写入时间 |

#### 字段级血缘（ODS → DWS）

| 输出字段 | 来源DWD表 | 来源DWD字段 | 来源ODS表 | 来源ODS字段 | 加工逻辑 |
|---------|----------|-----------|---------|-----------|----|
| `kol_full_name` | dim_kol | `kol_name` | ods_dingtalk_kol_tidwe_kol_info | `full_name` | JOIN dim_kol ON kol_id |
| `content_url` | dwd_kol_content_detail | `content_url` | ods_dingtalk_kol_tidwe_content | `content_url` | 直取 |
| `publish_dt` | dwd_kol_content_detail | `publish_dt` | ods_dingtalk_kol_tidwe_content | `actual_publish_date` | 直取（已为 DATE） |
| `views_cnt` | dwd_kol_content_detail | `views_cnt` | ods_tiktok_video_performances / ods_youtube_video_stats / ods_dingtalk_kol_tidwe_content | `views` / `view_count` / `views` | 平台接口优先，钉钉手工值兜底 |
| `likes_cnt` | dwd_kol_content_detail | `likes_cnt` | ods_tiktok_shop_video_performance_detail / ods_youtube_video_stats | `traffic_likes` / `like_count` | 按平台分支取值 |
| `comments_cnt` | dwd_kol_content_detail | `comments_cnt` | ods_tiktok_shop_video_performance_detail / ods_youtube_video_stats | `traffic_comments` / `comment_count` | 按平台分支取值 |
| `shares_cnt` | dwd_kol_content_detail | `shares_cnt` | ods_tiktok_shop_video_performance_detail | `traffic_shares` | 仅 TikTok 可用 |
| `orders_cnt` | dwd_kol_content_detail | `orders_cnt` | ods_tiktok_video_performances / ods_tw_pixel_orders | `sku_orders` / COUNT per discount_code | TikTok直取；其他折扣码归因 |
| `gmv_amt` | dwd_kol_content_detail | `gmv_amt` | ods_tiktok_video_performances / ods_tw_pixel_orders | `gmv_amount` / SUM(`order_revenue`) | TikTok直取；其他折扣码归因 |
| `new_customer_cnt` | dwd_kol_content_detail | `new_customer_cnt` | ods_tw_pixel_orders | `is_new_customer` | 非TikTok: discount_code归因后过滤is_new_customer=1 |

---

## ADS 层

### `ads_kol_content_performance`

**业务含义：** 报表6直接展示层，KOL内容发布基础信息及互动数据
**粒度：** 每条内容记录（`content_url` 为主键，最新快照）
**更新策略：** 每日全量覆盖
**下游使用：** 营销推广-KOL效果-内容表现看板

> **报表字段（v2.0 精简）：** 内容发布id、内容发布url、日期、播放、点赞数、评论数（共6个展示字段）

#### 数据血缘

```
dws_kol_content_snap
  直接透传（ADS 层选取6个报表展示字段）
       ↓
ads_kol_content_performance
```

#### 字段级血缘（ODS → ADS 完整链路）

| 报表字段 | ADS字段名 | 来源DWS字段 | 来源ODS表 | 来源ODS字段 | 加工类型 |
|---------|----------|-----------|---------|-----------|----|
| 内容发布id | `content_id` | `content_id` | ods_dingtalk_kol_tidwe_content / ods_youtube_video_stats | `content_url`（TikTok 正则提取视频ID） / `video_id`（YouTube 直取） | TikTok: `REGEXP_EXTRACT(content_url, '/video/([0-9]+)', 1)`；YouTube: `ods_youtube_video_stats.video_id` via `dingtalk_record_id = record_id` |
| 内容发布url | `content_url` | `content_url` | ods_dingtalk_kol_tidwe_content | `content_url` | 直取 |
| 日期 | `publish_dt` | `publish_dt` | ods_dingtalk_kol_tidwe_content | `actual_publish_date` | 直取（DATE 类型） |
| 播放 | `views_cnt` | `views_cnt` | ods_tiktok_video_performances / ods_youtube_video_stats / ods_dingtalk_kol_tidwe_content | `views` / `view_count` / `views` | 平台接口优先；钉钉手工值兜底 |
| 点赞数 | `likes_cnt` | `likes_cnt` | ods_tiktok_shop_video_performance_detail / ods_youtube_video_stats | `traffic_likes` / `like_count` | 按平台取值；无数据置 NULL |
| 评论数 | `comments_cnt` | `comments_cnt` | ods_tiktok_shop_video_performance_detail / ods_youtube_video_stats | `traffic_comments` / `comment_count` | 按平台取值；无数据置 NULL |

**说明：** DWS 层保留完整字段（包括 promo_code、gmv_amt、orders_cnt 等），供其他报表复用；ADS 层仅对报表6输出以上6个展示字段。

---

## 数据质量检查点

| 检查项 | 检查规则 | 处理方式 |
|-------|---------|---------|
| content_url 唯一性 | `content_url` 在 dwd_kol_content_detail 中不应重复 | 去重保留最新 `etl_time` 行 |
| TikTok 视频ID匹配率 | `publish_platform = 'TT'` 且 content_id 匹配到 `ods_tiktok_video_performances.video_id` 的比例 | 匹配率低于 80% 告警，检查 URL 格式变化 |
| YouTube record_id 匹配率 | `publish_platform = 'YT'` 且 `record_id` 匹配到 `ods_youtube_video_stats.dingtalk_record_id` 的比例 | 匹配率低于 80% 告警；比 URL 解析方式更稳定 |
| 折扣码归因覆盖率 | 非 TikTok 记录中 `promo_code IS NOT NULL` 且在 pixel_orders 有订单归因的比例 | 归因率低时记录日志，不阻断流程 |
| 播放量合理性 | `views_cnt` > 0 且 < 100,000,000 | 超范围置 NULL 并告警，可能是单位异常 |
| GMV 币种一致 | TikTok: `gmv_currency = 'USD'` 确认（已在 Doris 中验证）；pixel_orders: `order_revenue` 默认 USD | 每日校验两类来源的 gmv 加总是否合理 |
| 日期字段有效性 | `actual_publish_date` 为 DATE 类型，直接校验 2020~2030 范围 | 超范围置 NULL 并告警 |
| TikTok video_post_time | `video_post_time` 为 bigint 毫秒时间戳，转换后校验范围 | 仅用于展示，不影响核心指标 |
