# 加工文档 — 报表8：TikTok销售分类表

**关联报表：** 营销推广-TikTok销售
**需求时间：** 2026-05-25 | **上线时间：** 2026-06-12
**文档版本：** v1.0 | **日期：** 2026-04-24

---

## 报表字段（最终需求）

`店铺`、`日期`、`product_id`、`sku_id`、`sku`、`订单类型`、`曝光量`、`页面浏览量`、`销量`、`销售额`

---

## ODS 源表说明

| ODS 表名 | 来源接口 | 业务含义 | 关键字段 |
|---------|---------|---------|---------|
| `ods_tiktok_shop_product_performance` | tiktok / shop_product_performance | TikTok 商品表现（产品级，4,876行） | `shop_id`, `shop_name`, `product_id`, `collect_date`, `sales_breakdowns`（JSON）, `traffic_breakdowns`（JSON） |
| SKU映射表（待提供） | 业务维护 | TikTok product_id → 内部 sku_id / sku | `product_id`, `sku_id`, `sku` |

**核心设计说明：**
- `ods_tiktok_shop_product_performance` 为**产品级**表，无 `sku_id`/`sku` 字段
- `sku_id` / `sku` 需通过 TikTok `product_id` 关联外部 SKU 映射表（**待业务提供**）
- `订单类型` 来自 `sales_breakdowns` JSON 中的 `content_type` 字段，展开后各行为独立订单类型
- `曝光量` / `页面浏览量` 来自 `traffic_breakdowns` JSON 中对应 `content_type` 的流量数据

**`sales_breakdowns` JSON 结构（实测样本）：**
```json
[
  {"content_type": "LIVE",         "sales": {"avg_customers": 0, "gmv": {"amount": "0.00", "currency": "USD"}, "items_sold": 0}},
  {"content_type": "VIDEO",        "sales": {"avg_customers": 5, "gmv": {"amount": "123.45", "currency": "USD"}, "items_sold": 8}},
  {"content_type": "PRODUCT_CARD", "sales": {"avg_customers": 2, "gmv": {"amount": "56.78", "currency": "USD"}, "items_sold": 3}},
  {"content_type": "SHOWCASE",     "sales": {"avg_customers": 0, "gmv": {"amount": "0.00", "currency": "USD"}, "items_sold": 0}}
]
```

**`traffic_breakdowns` JSON 结构（实测样本）：**
```json
[
  {"content_type": "LIVE",    "traffic": {"impressions": 0, "page_views": 0, "ctr": "0.00", "avg_unique_page_views": 0, "avg_conversion_rate": "0.00"}},
  {"content_type": "VIDEO",   "traffic": {"impressions": 21, "page_views": 3, "ctr": "0.143", "avg_unique_page_views": 1, "avg_conversion_rate": "0.00"}},
  {"content_type": "PRODUCT_CARD", "traffic": {...}},
  {"content_type": "SHOWCASE",    "traffic": {...}}
]
```

---

## 整体数据血缘

```
ODS 层                                    DWD 层                       DWS 层                     ADS 层
─────────────────────────────────────────────────────────────────────────────────────────────────────
ods_tiktok_shop_product_performance ────► dwd_tiktok_sales_by_type ──► dws_tiktok_sales_by_type ──► ads_tiktok_sales_by_type
  （JSON展开 sales_breakdowns +
    traffic_breakdowns）
SKU映射表（待提供）──────────────────────►
```

---

## DWD 层

### `dwd_tiktok_sales_by_type`

**业务含义：** TikTok 商品销售按订单类型展开明细，每条记录为一个产品×日期×订单类型
**粒度：** 每日 × shop_id × product_id × content_type（订单类型）一条记录
**更新策略：** T+1 全量重算

#### 数据血缘

```
ods_tiktok_shop_product_performance（每行含 sales_breakdowns + traffic_breakdowns JSON数组）
  JSON 展开：对 sales_breakdowns 数组按 content_type 逐行展开
  JOIN traffic_breakdowns 中对应 content_type 的流量数据
  LEFT JOIN SKU映射表 ON product_id（待提供；未提供时 sku_id / sku 置 NULL）
        ↓
dwd_tiktok_sales_by_type（每行 = 1个产品 × 1天 × 1个订单类型）
```

#### 字段定义

| 字段名 | 类型 | 来源表 | 来源字段 | 加工逻辑 |
|-------|------|-------|----|--------|
| `partition_dt` | DATE | — | — | 等于 `dt` |
| `dt` | DATE | ods_tiktok_shop_product_performance | `collect_date` | 直取（DATE 类型） |
| `shop_id` | VARCHAR | ods_tiktok_shop_product_performance | `shop_id` | 直取 |
| `shop_name` | VARCHAR | ods_tiktok_shop_product_performance | `shop_name` | 直取 |
| `product_id` | VARCHAR | ods_tiktok_shop_product_performance | `product_id` | 直取（TikTok 数字型产品ID，如 `1729385843129619083`） |
| `sku_id` | VARCHAR | SKU映射表 | `sku_id` | LEFT JOIN ON product_id；⚠️ 映射表未提供前置 NULL |
| `sku` | VARCHAR | SKU映射表 | `sku` | LEFT JOIN ON product_id；⚠️ 映射表未提供前置 NULL |
| `content_type` | VARCHAR | ods_tiktok_shop_product_performance | `sales_breakdowns[*].content_type` | JSON展开（枚举值：`LIVE` / `VIDEO` / `PRODUCT_CARD` / `SHOWCASE`） |
| `impressions` | BIGINT | ods_tiktok_shop_product_performance | `traffic_breakdowns[*].traffic.impressions` | JSON展开，取对应 content_type 的曝光量 |
| `page_views` | BIGINT | ods_tiktok_shop_product_performance | `traffic_breakdowns[*].traffic.page_views` | JSON展开，取对应 content_type 的页面浏览量 |
| `items_sold` | BIGINT | ods_tiktok_shop_product_performance | `sales_breakdowns[*].sales.items_sold` | JSON展开，取对应 content_type 的销量 |
| `gmv_amount` | DECIMAL(18,2) | ods_tiktok_shop_product_performance | `sales_breakdowns[*].sales.gmv.amount` | JSON展开后 CAST AS DECIMAL；`sales.gmv.currency` 已确认为 USD |
| `gmv_currency` | VARCHAR | ods_tiktok_shop_product_performance | `sales_breakdowns[*].sales.gmv.currency` | 直取（USD） |
| `etl_load_ts` | TIMESTAMP | — | — | ETL 写入时间 |

#### 关键加工逻辑

**JSON 展开（以 Doris JSON 函数为例）：**

```sql
-- 方式1：若 Doris 支持 JSON_TABLE / LATERAL VIEW + JSON_ARRAY 展开
-- 以下为伪 SQL，实际写法需按 Doris 版本确认

SELECT
    p.collect_date   AS dt,
    p.shop_id,
    p.shop_name,
    p.product_id,
    s.content_type,
    -- traffic 数据（对应 content_type 的行）
    CAST(JSON_EXTRACT(t_item.value, '$.traffic.impressions') AS BIGINT) AS impressions,
    CAST(JSON_EXTRACT(t_item.value, '$.traffic.page_views')  AS BIGINT) AS page_views,
    -- sales 数据
    CAST(JSON_EXTRACT(s_item.value, '$.sales.items_sold')    AS BIGINT) AS items_sold,
    CAST(JSON_EXTRACT(s_item.value, '$.sales.gmv.amount')    AS DECIMAL(18,2)) AS gmv_amount
FROM ods_tiktok_shop_product_performance p
-- 展开 sales_breakdowns
LATERAL VIEW JSON_EXPLODE(p.sales_breakdowns) s_table AS s_item
-- 展开 traffic_breakdowns，关联同一 content_type
LATERAL VIEW JSON_EXPLODE(p.traffic_breakdowns) t_table AS t_item
WHERE JSON_EXTRACT(s_item.value, '$.content_type') = JSON_EXTRACT(t_item.value, '$.content_type')

-- 方式2：若 Doris 不支持 LATERAL VIEW JSON_EXPLODE，
-- 可在 ETL（Python/Spark）层先展开 JSON，写入临时表，再加工
```

**订单类型（content_type）枚举：**

| 英文值 | 业务含义 |
|-------|---------|
| `LIVE` | 直播带货 |
| `VIDEO` | 短视频带货 |
| `PRODUCT_CARD` | 商品卡 |
| `SHOWCASE` | 橱窗展示 |

**SKU 映射（待业务提供）：**

```sql
-- 映射表 ods_udf_tiktok_product_sku_mapping（表名待确认）
-- 预期字段：product_id（TikTok数字ID）, sku_id（内部SKU编码）, sku（SKU名称）
LEFT JOIN ods_udf_tiktok_product_sku_mapping m ON p.product_id = m.product_id
-- 映射表未提供前：sku_id = NULL, sku = NULL
```

---

## DWS 层

### `dws_tiktok_sales_by_type`

**业务含义：** TikTok 销售按订单类型日汇总，为 ADS 层直接输出做准备
**粒度：** 每日 × shop_id × product_id × sku_id × content_type 一条记录
**更新策略：** T+1 全量重算

#### 字段定义

| 字段名 | 类型 | 含义 | 加工逻辑 |
|-------|------|------|---------|
| `partition_dt` | DATE | 分区日期 | 等于 `dt` |
| `dt` | DATE | 日期 | 直取 dwd |
| `shop_name` | VARCHAR | 店铺 | 直取 dwd |
| `product_id` | VARCHAR | TikTok产品ID | 直取 dwd |
| `sku_id` | VARCHAR | 内部SKU ID | 直取 dwd（当前 NULL） |
| `sku` | VARCHAR | 内部SKU名称 | 直取 dwd（当前 NULL） |
| `content_type` | VARCHAR | 订单类型（订单来源渠道） | 直取 dwd（LIVE/VIDEO/PRODUCT_CARD/SHOWCASE） |
| `impressions` | BIGINT | 曝光量 | 直取 dwd |
| `page_views` | BIGINT | 页面浏览量 | 直取 dwd |
| `items_sold` | BIGINT | 销量 | 直取 dwd |
| `gmv_amount` | DECIMAL(18,2) | 销售额（USD） | 直取 dwd |
| `etl_load_ts` | TIMESTAMP | ETL写入时间 | ETL 写入时间 |

---

## ADS 层

### `ads_tiktok_sales_by_type`

**业务含义：** 报表8直接展示层，TikTok商品销售按订单类型分类，字段名与《数据表需求》对齐
**粒度：** 每日 × 店铺 × product_id × sku_id × 订单类型 一条记录
**更新策略：** T+1 全量重算
**下游使用：** 营销推广-TikTok销售看板

#### 字段级血缘（ODS → ADS 完整链路）

| 报表字段 | ADS字段名 | 来源DWS字段 | 来源ODS表 | 来源ODS字段 | 加工类型 |
|---------|----------|-----------|---------|-----------|----|
| 店铺 | `shop_name` | `shop_name` | ods_tiktok_shop_product_performance | `shop_name` | 直取 |
| 日期 | `dt` | `dt` | ods_tiktok_shop_product_performance | `collect_date` | 直取（DATE 类型） |
| product_id | `product_id` | `product_id` | ods_tiktok_shop_product_performance | `product_id` | 直取 |
| sku_id | `sku_id` | `sku_id` | SKU映射表 | `sku_id` | LEFT JOIN ON product_id；⚠️ 当前 NULL |
| sku | `sku` | `sku` | SKU映射表 | `sku` | LEFT JOIN ON product_id；⚠️ 当前 NULL |
| 订单类型 | `content_type` | `content_type` | ods_tiktok_shop_product_performance | `sales_breakdowns[*].content_type` | JSON展开枚举（LIVE/VIDEO/PRODUCT_CARD/SHOWCASE） |
| 曝光量 | `impressions` | `impressions` | ods_tiktok_shop_product_performance | `traffic_breakdowns[*].traffic.impressions` | JSON展开，按 content_type 取对应值 |
| 页面浏览量 | `page_views` | `page_views` | ods_tiktok_shop_product_performance | `traffic_breakdowns[*].traffic.page_views` | JSON展开，按 content_type 取对应值 |
| 销量 | `items_sold` | `items_sold` | ods_tiktok_shop_product_performance | `sales_breakdowns[*].sales.items_sold` | JSON展开，按 content_type 取对应值 |
| 销售额 | `gmv_amount` | `gmv_amount` | ods_tiktok_shop_product_performance | `sales_breakdowns[*].sales.gmv.amount` | JSON展开后 CAST DECIMAL；币种 USD |

---

## 数据质量检查点

| 检查项 | 检查规则 | 处理方式 |
|-------|---------|---------|
| JSON 展开完整性 | 每条 product_id×dt 展开后应有 4 个 content_type 行（LIVE/VIDEO/PRODUCT_CARD/SHOWCASE） | 展开行数异常告警，检查 JSON 格式变化 |
| SKU 映射覆盖率 | ⚠️ 当前映射表未提供，sku_id/sku 全为 NULL | 映射表接入后激活，覆盖率低于 80% 告警 |
| 订单类型覆盖率 | `content_type` 枚举值应仅为 LIVE/VIDEO/PRODUCT_CARD/SHOWCASE | 出现新值时告警，补充到文档枚举表 |
| 销售额合计校验 | 各 content_type 的 gmv_amount SUM = `ods_tiktok_shop_product_performance.sales_gmv_amount` 汇总值 | 偏差 > 1% 告警，检查 JSON 解析精度 |
| 曝光量合计校验 | 各 content_type 的 impressions SUM = `traffic_impressions`（顶层字段） | 同上 |
| 零值过滤 | items_sold = 0 AND gmv_amount = 0 AND impressions = 0 的行视为"无数据行" | 可选：过滤零值行以减少数据量；或保留以备查 |
| collect_date 时效 | `collect_date` 应为 T-1 | 超过 T-2 告警，可能数据延迟 |
