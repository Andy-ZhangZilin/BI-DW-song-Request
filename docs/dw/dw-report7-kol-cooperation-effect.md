# 加工文档 — 报表7：KOL/达人合作效果表

**关联报表：** 营销推广-KOL效果
**需求时间：** 2026-05-25 | **上线时间：** 2026-06-12
**文档版本：** v3.0 | **日期：** 2026-04-24

> **v3.0 变更（2026-04-24）：** 报表7拆分为两张独立表：
> - **KOL合作效果表**（`ads_kol_cooperation_cost`）：日粒度费用明细，含寄样单号、样品费、合作费
> - **KOL销售表**（`ads_kol_sales`）：日粒度销售明细，含 sku、CODE、订单数、销量、销售额
>
> v2.0 所有已验证的 Doris 表名和字段名保留，样品费 JOIN 路径仍为待解决问题。

---

## ODS 表名对照

| 原文档名称（设计阶段） | 实际 Doris 表名 | 说明 |
|---------------------|----------------|------|
| `ods_dd_kol_sample_records` | `ods_dingtalk_kol_tidwe_sample` | 寄样记录（305行） |
| `ods_dd_kol_payment` | `ods_dingtalk_outdoor_material_analysis` | KOL红人支付表 |
| `ods_finance_multi_order` | `ods_finance_bi_report_middle_multi_order` | 多平台订单汇总表（样品费路径受阻） |
| — | `ods_tiktok_video_performances` | TikTok视频销售（直取gmv_amount, sku_orders） |
| — | `ods_tw_pixel_orders` | TW像素订单归因（折扣码归因YouTube/其他KOL销售） |
| — | `ods_dingtalk_kol_tidwe_content` | 内容上线记录（取promo_code） |

---

## 整体数据血缘

```
表1 — KOL合作效果表（费用视角，日×红人粒度）
────────────────────────────────────────────────────────────────────
ods_dingtalk_kol_tidwe_sample ──────────────────────────────────────► dws_kol_cooperation_cost_d ──► ads_kol_cooperation_cost
ods_dingtalk_outdoor_material_analysis ─────────────────────────────►
ods_finance_bi_report_middle_multi_order ──(⚠️ JOIN受阻，暂NULL)────►

表2 — KOL销售表（销售视角，日×红人×SKU×CODE 粒度）
────────────────────────────────────────────────────────────────────
ods_tiktok_video_performances ──────────────────────────────────────► dws_kol_sales_d ──► ads_kol_sales
ods_tw_pixel_orders ─────────────────────────────────────────────────►
ods_dingtalk_kol_tidwe_content ──(取promo_code)──────────────────────►
```

---

## 表1 — KOL合作效果表

### DWS 层：`dws_kol_cooperation_cost_d`

**业务含义：** KOL 合作费用日明细，以付款/寄样发生日期为准，每条合作费支出或寄样记录一行
**粒度：** 每日 × kol_id × 费用类型 一条记录
**更新策略：** T+1 全量重算

#### 数据血缘

```
Path A — 合作费（ods_dingtalk_outdoor_material_analysis）
  dt     = date（DATE 类型，直取）
  kol_id = username（username ↔ kol_id 映射，待维护；直接以 username 作 kol_id 输出）
  fee_type = '合作费'
  amount_usd = CAST(REPLACE(REPLACE(COALESCE(round_actual_amount,'0'), '$', ''), ',', '') AS DECIMAL(16,2))

Path B — 寄样记录（ods_dingtalk_kol_tidwe_sample）
  dt              = sample_date（DATE 类型，直取）
  kol_id          = kol_id
  sample_order_id = tracking_number
  sample_sku      = product
  fee_type        = '样品费'
  sample_cost_usd = ⚠️ 待修复（tracking_number 格式与 platform_order_no 不匹配，当前置 NULL）
  预期逻辑（待修复后启用）：
    JOIN ods_finance_bi_report_middle_multi_order ON platform_order_no = tracking_number
    WHERE bi_report_project_name IN ('采购成本','关税','头程成本','尾程成本') AND is_deleted = 0
    → amount AS sample_cost_usd

UNION ALL → dws_kol_cooperation_cost_d
```

#### 字段定义

| 字段名 | 类型 | 含义 | 来源 / 加工逻辑 |
|-------|------|------|---------------|
| `partition_dt` | DATE | 分区日期 | 等于 `dt` |
| `dt` | DATE | 日期 | Path A: `date`；Path B: `sample_date`（均为 DATE 类型，直取） |
| `kol_id` | VARCHAR | 红人ID | Path A: `username`（直接使用，待业务维护 username↔kol_id 映射）；Path B: `kol_id` |
| `fee_type` | VARCHAR | 费用类型 | Path A: `'合作费'`；Path B: `'样品费'` |
| `sample_order_id` | VARCHAR | 寄样单号 | Path B: `tracking_number`；Path A: NULL |
| `sample_sku` | VARCHAR | 寄样产品SKU | Path B: `product`；Path A: NULL |
| `sample_cost_usd` | DECIMAL(18,2) | 样品费（USD） | ⚠️ 当前置 NULL（JOIN 路径受阻）；Path A: NULL |
| `cooperation_fee_usd` | DECIMAL(18,2) | 合作费（USD） | Path A: `CAST(REPLACE(REPLACE(COALESCE(round_actual_amount,'0'),'$',''),',','') AS DECIMAL(16,2))`；Path B: NULL |
| `etl_load_ts` | TIMESTAMP | ETL写入时间 | ETL 写入时间 |

#### 关键加工逻辑

```sql
-- Path A：合作费
SELECT
    a.date           AS dt,
    a.username       AS kol_id,
    '合作费'          AS fee_type,
    NULL             AS sample_order_id,
    NULL             AS sample_sku,
    NULL             AS sample_cost_usd,
    CAST(REPLACE(REPLACE(COALESCE(a.round_actual_amount, '0'), '$', ''), ',', '')
         AS DECIMAL(16, 2)) AS cooperation_fee_usd
FROM ods_dingtalk_outdoor_material_analysis a

UNION ALL

-- Path B：寄样记录（样品费当前 NULL）
SELECT
    s.sample_date    AS dt,
    s.kol_id         AS kol_id,
    '样品费'          AS fee_type,
    s.tracking_number AS sample_order_id,
    s.product         AS sample_sku,
    NULL              AS sample_cost_usd,   -- ⚠️ tracking_number ≠ platform_order_no，0行
    NULL              AS cooperation_fee_usd
FROM ods_dingtalk_kol_tidwe_sample s
```

---

### ADS 层：`ads_kol_cooperation_cost`

**业务含义：** 报表7-表1 直接展示层，KOL合作效果表（费用视角）
**粒度：** 每日 × kol_id × 费用类型（合作费/样品费）一条记录
**更新策略：** T+1 全量重算
**下游使用：** 营销推广-KOL效果看板

#### 字段级血缘（ODS → ADS）

| 报表字段 | ADS字段名 | 来源DWS字段 | 来源ODS表 | 来源ODS字段 | 加工类型 |
|---------|----------|-----------|---------|-----------|----|
| 日期 | `dt` | `dt` | ods_dingtalk_outdoor_material_analysis / ods_dingtalk_kol_tidwe_sample | `date` / `sample_date` | 直取（DATE 类型） |
| 红人ID | `kol_id` | `kol_id` | ods_dingtalk_outdoor_material_analysis / ods_dingtalk_kol_tidwe_sample | `username` / `kol_id` | 直取 |
| 寄样单号 | `sample_order_id` | `sample_order_id` | ods_dingtalk_kol_tidwe_sample | `tracking_number` | 直取；合作费行为 NULL |
| 寄样产品SKU | `sample_sku` | `sample_sku` | ods_dingtalk_kol_tidwe_sample | `product` | 直取；合作费行为 NULL |
| 样品费 | `sample_cost_usd` | `sample_cost_usd` | ods_finance_bi_report_middle_multi_order | `amount` | ⚠️ 当前置 NULL（JOIN 路径受阻） |
| 合作费 | `cooperation_fee_usd` | `cooperation_fee_usd` | ods_dingtalk_outdoor_material_analysis | `round_actual_amount` | CAST+REPLACE 清洗；样品费行为 NULL |

---

## 表2 — KOL销售表

### DWS 层：`dws_kol_sales_d`

**业务含义：** KOL 带来的销售日明细，TikTok 直取平台数据，YouTube/其他通过折扣码在 TW pixel_orders 归因
**粒度：** 每日 × kol_id × sku × promo_code 一条记录
**更新策略：** T+1 全量重算

#### 数据血缘

```
Path A — TikTok 达人销售（直接来自视频带货数据）
  ods_tiktok_video_performances
    JOIN ods_dingtalk_kol_tidwe_content ON REGEXP_EXTRACT(content_url,'/video/([0-9]+)',1) = video_id
    → kol_id（来自 kol_tidwe_content.kol_id）
    → dt = FROM_UNIXTIME(video_post_time/1000) 所在日期（或 collect_date）
    → promo_code（来自 kol_tidwe_content.promo_code）
    → sku = NULL（TikTok 视频级别无 SKU 拆分，⚠️ 待 TikTok product_id → SKU 映射表）
    → orders_cnt = sku_orders, items_qty = items_sold, gmv_amt = gmv_amount

Path B — YouTube/其他 KOL 销售（折扣码归因）
  ods_dingtalk_kol_tidwe_content（取 kol_id, promo_code, actual_publish_date）
    JOIN ods_tw_pixel_orders ON discount_code = promo_code
    → dt = ods_tw_pixel_orders.event_date
    → kol_id（来自 kol_tidwe_content.kol_id）
    → promo_code = discount_code
    → sku = NULL（pixel_orders 无 SKU 字段，⚠️ 如需 SKU 需关联 products_info JSON）
    → orders_cnt = COUNT(*), items_qty = SUM(product_quantity_sold_in_order)
    → gmv_amt = SUM(order_revenue)
```

**⚠️ SKU 字段说明：**
- TikTok：`ods_tiktok_video_performances` 为视频×日期粒度，无 SKU 拆分；需 TikTok product_id → 内部 SKU 映射表（待业务提供）
- YouTube/其他：`ods_tw_pixel_orders.products_info` 为 JSON 字段，可解析获取 SKU；当前 `sku` 字段置 NULL，待业务确认解析方式

#### 字段定义

| 字段名 | 类型 | 含义 | 来源 / 加工逻辑 |
|-------|------|------|---------------|
| `partition_dt` | DATE | 分区日期 | 等于 `dt` |
| `dt` | DATE | 日期 | Path A: `FROM_UNIXTIME(video_post_time/1000)` 所在日期；Path B: `ods_tw_pixel_orders.event_date` |
| `kol_id` | VARCHAR | 红人ID | 均来自 ods_dingtalk_kol_tidwe_content.kol_id |
| `sku` | VARCHAR | 产品SKU | ⚠️ 当前置 NULL（TikTok 需 product_id→SKU 映射；pixel_orders 需解析 products_info JSON） |
| `promo_code` | VARCHAR | 推广码 | Path A: ods_dingtalk_kol_tidwe_content.promo_code；Path B: ods_tw_pixel_orders.discount_code |
| `orders_cnt` | BIGINT | 订单数 | Path A: `sku_orders`；Path B: COUNT(*) per discount_code |
| `items_qty` | BIGINT | 销量 | Path A: `items_sold`；Path B: SUM(`product_quantity_sold_in_order`) |
| `gmv_amt` | DECIMAL(18,2) | 销售额（USD） | Path A: `gmv_amount`（已确认 USD）；Path B: SUM(`order_revenue`）（USD） |
| `data_source` | VARCHAR | 数据来源 | Path A: `'tiktok'`；Path B: `'triplewhale'` |
| `etl_load_ts` | TIMESTAMP | ETL写入时间 | ETL 写入时间 |

---

### ADS 层：`ads_kol_sales`

**业务含义：** 报表7-表2 直接展示层，KOL销售明细
**粒度：** 每日 × kol_id × sku × promo_code 一条记录
**更新策略：** T+1 全量重算
**下游使用：** 营销推广-KOL效果看板

#### 字段级血缘（ODS → ADS）

| 报表字段 | ADS字段名 | 来源DWS字段 | 来源ODS表 | 来源ODS字段 | 加工类型 |
|---------|----------|-----------|---------|-----------|----|
| 日期 | `dt` | `dt` | ods_tiktok_video_performances / ods_tw_pixel_orders | `video_post_time` / `event_date` | TikTok: FROM_UNIXTIME/1000；其他: 直取 |
| 红人ID | `kol_id` | `kol_id` | ods_dingtalk_kol_tidwe_content | `kol_id` | 直取 |
| sku | `sku` | `sku` | — | — | ⚠️ 当前置 NULL，待映射表 |
| CODE | `promo_code` | `promo_code` | ods_dingtalk_kol_tidwe_content / ods_tw_pixel_orders | `promo_code` / `discount_code` | 直取 |
| 订单数 | `orders_cnt` | `orders_cnt` | ods_tiktok_video_performances / ods_tw_pixel_orders | `sku_orders` / COUNT | TikTok直取；其他折扣码归因 |
| 销量 | `items_qty` | `items_qty` | ods_tiktok_video_performances / ods_tw_pixel_orders | `items_sold` / SUM(`product_quantity_sold_in_order`) | TikTok直取；其他折扣码归因 |
| 销售额 | `gmv_amt` | `gmv_amt` | ods_tiktok_video_performances / ods_tw_pixel_orders | `gmv_amount` / SUM(`order_revenue`) | TikTok直取（USD）；其他折扣码归因（USD） |

---

## 数据质量检查点

| 检查项 | 检查规则 | 处理方式 |
|-------|---------|---------|
| 样品费 JOIN | ⚠️ tracking_number 格式不匹配 platform_order_no，返回 0 行 | 输出告警，sample_cost_usd 置 NULL |
| 合作费 username 匹配 | username 能否在 kol_id 体系中命中 | 低于 80% 告警，提示维护映射关系 |
| 合作费清洗 | round_actual_amount 清洗（去 $ 和 ,）后 CAST DECIMAL 成功率 | 失败记录置 NULL 告警 |
| TikTok video_id 匹配 | TikTok content_url 解析出 video_id 后在 ods_tiktok_video_performances 的命中率 | 低于 80% 告警 |
| 折扣码归因覆盖 | promo_code 非空且在 pixel_orders 有订单的比例 | 归因率低时记录日志 |
| sku 字段 | 当前两路均为 NULL | 有映射表后激活，前期 NULL 为预期行为 |
| 日期字段范围 | dt 在 2020~2030 范围内 | 超范围置 NULL 告警 |
