# 加工文档 — 报表4：DTC广告投放数据

**关联报表：** 营销推广-广告投放
**需求时间：** 2026-05-10 | **上线时间：** 2026-06-03
**文档版本：** v2.0 | **日期：** 2026-04-24

> **v2.0 变更（2026-04-24）：** 经 Doris 实际数据验证，`ods_tw_pixel_joined` 中 `model` 字段仅存在 `'Triple Attribution'`，原文档 `'Linear All'` 已不适用，已全文修正。

---

## 整体数据血缘

```
ODS 层                           DIM 层          DWD 层                        DWS 层                      ADS 层
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
                                                                               ┌──────────────────────┐
ods_tw_pixel_joined ──┐                                                        │                      │
                      ├─(paid渠道过滤+JOIN dim_shop)──► dwd_marketing_ads ────► dws_marketing_ads_d ──► ads_marketing_ads_performance
dim_shop ─────────────┘                                                        │                      │
                                                                               └──────────────────────┘
```

**说明：** 报表4专注于付费广告渠道（channel_category IN ('广告（上层广告）','广告')）的投放明细，与报表3共享同一 ODS 源，但粒度更细（到活动/广告组/广告层级）。

---

## DWD 层

### 1. `dwd_marketing_ads_detail`

**业务含义：** DTC 付费广告投放明细，按渠道 × 活动 × 广告组 × 广告粒度的日事实数据
**粒度：** 每日 × channel × campaign_id × adset_id × ad_id × shop_id 一条记录
**更新策略：** T+1 全量重算

#### 数据血缘

```
ods_tw_pixel_joined
  过滤：model = 'Triple Attribution' AND lowerUTF8(attribution_window) = 'lifetime'
        AND channel_category IN ('广告（上层广告）','广告')   -- 仅保留付费广告行
  JOIN：dim_shop ON shop_name = dim_shop.shop_name → shop_id
  聚合：GROUP BY event_date, channel, channel_category, campaign_id, campaign_name,
                adset_id, adset_name, ad_id, ad_name, shop_id
  指标：SUM(impressions), SUM(clicks)→clicks_cnt, SUM(outbound_clicks)→outbound_clicks_cnt,
        SUM(orders_quantity), SUM(product_quantity_sold_in_order), SUM(order_revenue), SUM(spend),
        SUM(new_customer_orders)
  加购数来源（独立聚合后 JOIN）：
    ods_tw_product_analytics GROUP BY event_date, shop_id → SUM(added_to_cart_events) AS add_to_cart_cnt
    LEFT JOIN ON dt + shop_id（注：同日同店所有广告行填相同 add_to_cart 值）
        ↓
dwd_marketing_ads_detail
```

**注：** `channel_category` 由同一归因 CASE WHEN SQL（见报表3）在本 DWD 层加工完成；`channel_group` 直取原始 `channel` 字段值。

#### 字段定义

| 字段名 | 类型 | 来源表 | 来源字段 | 加工逻辑 |
|-------|------|-------|---------|---------|
| `partition_dt` | DATE | — | — | 等于 `dt` |
| `dt` | DATE | ods_tw_pixel_joined | `event_date` | 直取 |
| `shop_id` | VARCHAR | dim_shop | `shop_id` | JOIN dim_shop ON shop_name |
| `channel_category` | VARCHAR | ods_tw_pixel_joined | `channel` + `campaign_name` | CASE WHEN 归因 SQL，值：`广告（上层广告）` / `广告` |
| `channel_group` | VARCHAR | ods_tw_pixel_joined | `channel` | 直取原始值（如 `google-ads`、`facebook-ads`、`tiktok-ads`） |
| `campaign_id` | VARCHAR | ods_tw_pixel_joined | `campaign_id` | 直取 |
| `campaign_name` | VARCHAR | ods_tw_pixel_joined | `campaign_name` | 直取 |
| `adset_id` | VARCHAR | ods_tw_pixel_joined | `adset_id` | 直取 |
| `adset_name` | VARCHAR | ods_tw_pixel_joined | `adset_name` | 直取 |
| `ad_id` | VARCHAR | ods_tw_pixel_joined | `ad_id` | 直取；过滤 `ad_id IS NULL OR ad_id = '' OR ad_id = '(not set)'` 时保留为 NULL |
| `ad_name` | VARCHAR | ods_tw_pixel_joined | `ad_name` | 直取；同上处理 |
| `impressions` | BIGINT | ods_tw_pixel_joined | `impressions` | SUM |
| `clicks_cnt` | BIGINT | ods_tw_pixel_joined | `clicks` | SUM（广告总点击数，对应报表"点击数"） |
| `outbound_clicks_cnt` | BIGINT | ods_tw_pixel_joined | `outbound_clicks` | SUM（对应报表"流量"；Facebook 有值，Google/其他为 NULL，建议 `COALESCE(outbound_clicks, clicks)` 兜底） |
| `add_to_cart_cnt` | BIGINT | ods_tw_product_analytics | `added_to_cart_events` | SUM per dt × shop_id（仅 shop×日期粒度，**无法细化到活动/广告组层级**；来源为 ods_tw_product_analytics） |
| `orders_cnt` | BIGINT | ods_tw_pixel_joined | `orders_quantity` | SUM |
| `items_qty` | BIGINT | ods_tw_pixel_joined | `product_quantity_sold_in_order` | SUM |
| `revenue_amt` | DECIMAL(18,2) | ods_tw_pixel_joined | `order_revenue` | SUM（USD） |
| `spend_amt` | DECIMAL(18,2) | ods_tw_pixel_joined | `spend` | SUM（USD） |
| `new_customer_cnt` | BIGINT | ods_tw_pixel_joined | `new_customer_orders` | SUM |
| `etl_load_ts` | TIMESTAMP | — | — | ETL 写入时间 |
| `data_source` | VARCHAR | — | — | 常量 `'triplewhale'` |

#### 关键加工逻辑

**过滤条件（付费渠道判断）：**

```sql
-- 基础过滤
WHERE model = 'Triple Attribution'
  AND lowerUTF8(attribution_window) = 'lifetime'

-- 付费渠道白名单（与报表3归因 SQL 对应的 channel_category 过滤）
AND channel_category IN ('广告（上层广告）', '广告')
-- 等效于：channel 值属于 facebook-ads / google-ads / meta / bing / microsoft ads /
--         snapchat-ads / snapchat / tiktok-ads / tiktok / criteo 及相关 sitelink 变体

-- ad_id / ad_name 脏数据处理
ad_id = CASE
  WHEN ad_id IS NULL OR TRIM(ad_id) = '' OR ad_id = '(not set)' THEN NULL
  ELSE ad_id
END
```

**注：** 完整归因 CASE WHEN SQL 与报表3一致，ETL 直接引用，不在此重复。

---

## DWS 层

### `dws_marketing_ads_d`

**业务含义：** 付费广告投放日汇总，统一口径对齐报表4各字段
**粒度：** 每日 × shop_id × channel_group × campaign_id × adset_id × ad_id 一条记录
**更新策略：** T+1 全量重算
**下游使用：** ads_marketing_ads_performance

#### 数据血缘

```
dwd_marketing_ads_detail
  直接汇总（DWD 已为最细粒度，DWS 直传 + JOIN dim_shop 获取 shop_name）
        ↓
dws_marketing_ads_d
```

#### 字段定义

| 字段名 | 类型 | 含义 | 加工逻辑概述 |
|-------|------|------|------------|
| `partition_dt` | DATE | 分区日期 | 等于 `dt` |
| `dt` | DATE | 日期 | 直取 dwd |
| `shop_id` | VARCHAR | 店铺ID | 直取 |
| `shop_name` | VARCHAR | 店铺名 | JOIN dim_shop ON shop_id |
| `channel_category` | VARCHAR | 推广渠道 | 直取（`广告（上层广告）` / `广告`） |
| `channel_group` | VARCHAR | 推广渠道细分类 | 直取原始 channel 值 |
| `campaign_id` | VARCHAR | 活动ID | 直取 |
| `campaign_name` | VARCHAR | 活动名称 | 直取 |
| `adset_id` | VARCHAR | 广告组ID | 直取 |
| `adset_name` | VARCHAR | 广告组名称 | 直取 |
| `ad_id` | VARCHAR | 广告ID | 直取（NULL 时为活动/广告组级汇总行） |
| `ad_name` | VARCHAR | 广告名称 | 直取 |
| `impressions` | BIGINT | 曝光量 | 直取 dwd |
| `clicks_cnt` | BIGINT | 点击数（广告总点击数） | 直取 dwd |
| `outbound_clicks_cnt` | BIGINT | 流量（站外链接点击数） | 直取 dwd；Facebook有值，Google NULL；ADS层用 `COALESCE(outbound_clicks_cnt, clicks_cnt)` |
| `add_to_cart_cnt` | BIGINT | 加购数 | 来自 ods_tw_product_analytics，仅 shop×日期级别聚合，无广告组拆分 |
| `orders_cnt` | BIGINT | 订单量 | 直取 dwd |
| `items_qty` | BIGINT | 销量 | 直取 dwd |
| `revenue_amt` | DECIMAL(18,2) | 销售额（USD） | 直取 dwd |
| `spend_amt` | DECIMAL(18,2) | 花费（USD） | 直取 dwd |
| `new_customer_cnt` | BIGINT | 新客数 | 直取 dwd |
| `etl_load_ts` | TIMESTAMP | ETL写入时间 | ETL 写入时间 |

#### 字段级血缘（ODS → DWS）

| 输出字段 | 来源DWD表 | 来源DWD字段 | 来源ODS表 | 来源ODS字段 | 加工逻辑 |
|---------|----------|-----------|---------|-----------|---------|
| `dt` | dwd_marketing_ads_detail | `dt` | ods_tw_pixel_joined | `event_date` | 直取 |
| `shop_name` | — | — | dim_shop | `shop_name` | JOIN dim_shop ON shop_id |
| `channel_category` | dwd_marketing_ads_detail | `channel_category` | ods_tw_pixel_joined | `channel` + `campaign_name` | CASE WHEN 归因分类 |
| `channel_group` | dwd_marketing_ads_detail | `channel_group` | ods_tw_pixel_joined | `channel` | 直取原始值 |
| `campaign_id` / `campaign_name` | dwd_marketing_ads_detail | `campaign_id` / `campaign_name` | ods_tw_pixel_joined | `campaign_id` / `campaign_name` | 直取 |
| `adset_id` / `adset_name` | dwd_marketing_ads_detail | `adset_id` / `adset_name` | ods_tw_pixel_joined | `adset_id` / `adset_name` | 直取 |
| `ad_id` / `ad_name` | dwd_marketing_ads_detail | `ad_id` / `ad_name` | ods_tw_pixel_joined | `ad_id` / `ad_name` | 直取；脏数据置 NULL |
| `impressions` | dwd_marketing_ads_detail | `impressions` | ods_tw_pixel_joined | `impressions` | SUM |
| `clicks_cnt` | dwd_marketing_ads_detail | `clicks_cnt` | ods_tw_pixel_joined | `clicks` | SUM |
| `outbound_clicks_cnt` | dwd_marketing_ads_detail | `outbound_clicks_cnt` | ods_tw_pixel_joined | `outbound_clicks` | SUM；Facebook有值；Google/其他 NULL |
| `add_to_cart_cnt` | — | — | ods_tw_product_analytics | `added_to_cart_events` | SUM per dt×shop_id；LEFT JOIN dws ON dt+shop_id |
| `orders_cnt` | dwd_marketing_ads_detail | `orders_cnt` | ods_tw_pixel_joined | `orders_quantity` | SUM |
| `items_qty` | dwd_marketing_ads_detail | `items_qty` | ods_tw_pixel_joined | `product_quantity_sold_in_order` | SUM |
| `revenue_amt` | dwd_marketing_ads_detail | `revenue_amt` | ods_tw_pixel_joined | `order_revenue` | SUM（USD） |
| `spend_amt` | dwd_marketing_ads_detail | `spend_amt` | ods_tw_pixel_joined | `spend` | SUM（USD） |
| `new_customer_cnt` | dwd_marketing_ads_detail | `new_customer_cnt` | ods_tw_pixel_joined | `new_customer_orders` | SUM |

---

## ADS 层

### `ads_marketing_ads_performance`

**业务含义：** 报表4直接展示层，广告投放明细，字段名与《数据表需求》对齐
**粒度：** 每日 × 店铺 × 推广渠道 × 推广渠道细分类 × 活动 × 广告组 × 广告 一条记录
**更新策略：** T+1 全量重算
**下游使用：** 营销推广-广告投放看板

#### 数据血缘

```
dws_marketing_ads_d
  直接透传（ADS 层主要做字段重命名对齐报表需求）
        ↓
ads_marketing_ads_performance
```

#### 字段级血缘（ODS → ADS 完整链路）

| 报表字段 | ADS字段名 | 来源DWS字段 | 来源ODS表 | 来源ODS字段 | 加工类型 |
|---------|----------|-----------|---------|-----------|---------|
| 日期 | `dt` | `dt` | ods_tw_pixel_joined | `event_date` | 直取 |
| 店铺名称 | `shop_name` | `shop_name` | dim_shop | `shop_name` | JOIN 关联 |
| 推广渠道 | `channel_category` | `channel_category` | ods_tw_pixel_joined | `channel` + `campaign_name` | CASE WHEN 归因 |
| 推广渠道细分类 | `channel_group` | `channel_group` | ods_tw_pixel_joined | `channel` | 直取原始值 |
| 活动 | `campaign_name` | `campaign_name` | ods_tw_pixel_joined | `campaign_name` | 直取；`campaign_id` 同时保留 |
| 广告组 | `adset_name` | `adset_name` | ods_tw_pixel_joined | `adset_name` | 直取；`adset_id` 同时保留 |
| 广告 | `ad_name` | `ad_name` | ods_tw_pixel_joined | `ad_name` | 直取；`ad_id` 同时保留；NULL 时表示无广告层级数据 |
| 曝光量 | `impressions` | `impressions` | ods_tw_pixel_joined | `impressions` | 直取 |
| 点击数 | `clicks_cnt` | `clicks_cnt` | ods_tw_pixel_joined | `clicks` | 直取（广告总点击数） |
| 流量 | `outbound_clicks_cnt` | `outbound_clicks_cnt` | ods_tw_pixel_joined | `outbound_clicks` | `COALESCE(outbound_clicks_cnt, clicks_cnt)`；Facebook 区分 outbound，Google 等渠道 NULL 时 fallback clicks |
| 加购数 | `add_to_cart_cnt` | `add_to_cart_cnt` | ods_tw_product_analytics | `added_to_cart_events` | shop×日期聚合后 JOIN；**非广告组/活动级别**，同一店铺同日所有广告行填相同值 |
| 订单量 | `orders_cnt` | `orders_cnt` | ods_tw_pixel_joined | `orders_quantity` | 直取 |
| 销量 | `items_qty` | `items_qty` | ods_tw_pixel_joined | `product_quantity_sold_in_order` | 直取 |
| 销售额 | `revenue_amt` | `revenue_amt` | ods_tw_pixel_joined | `order_revenue` | 直取（USD） |
| 花费 | `spend_amt` | `spend_amt` | ods_tw_pixel_joined | `spend` | 直取（USD） |
| 新客数 | `new_customer_cnt` | `new_customer_cnt` | ods_tw_pixel_joined | `new_customer_orders` | 直取 |

---

## 数据质量检查点

| 检查项 | 检查规则 | 处理方式 |
|-------|---------|---------|
| TW 分区完整性 | 每日 pixel_joined 分区必须到货 | 告警，DWS 不重算 |
| 付费渠道覆盖率 | `channel_category` 非 NULL 且仅含 `广告（上层广告）`/`广告` | 若出现其他值说明归因 SQL 未命中，告警排查 |
| ad_id 空值率 | `ad_id IS NULL` 的行占比超过 50% 告警 | 说明 TW 未同步至广告层级，记录日志 |
| 花费合理性 | 日 `spend_amt` 为 0 但 `impressions` > 0 的行不应超过 10% | 告警，检查 TW spend 数据同步延迟 |
| campaign_id 唯一性 | 同 dt × shop × campaign_id × adset_id × ad_id 不应有重复行 | 去重保留最新 `etl_load_ts` 行 |
| 货币口径 | spend_amt / revenue_amt 均为 USD；ADS 层展示前需在报表标注币种 | 记录字段说明 |
