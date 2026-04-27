# 加工文档 — 报表5：KOL信息表

**关联报表：** 营销推广-KOL效果
**需求时间：** 2026-05-15 | **上线时间：** 2026-06-12
**文档版本：** v2.0 | **日期：** 2026-04-24

> **v2.0 变更（2026-04-24）：** 经 Doris 实际数据验证，更新全部 ODS 表名及字段名（中文字段名 → 英文字段名）；`sample_date` / `contract_date` / `actual_publish_date` 均已为 DATE 类型，无需毫秒时间戳转换。

---

## ODS 表名对照

| 原文档名称（设计阶段） | 实际 Doris 表名 | 说明 |
|---------------------|----------------|------|
| `ods_dd_kol_info` | `ods_dingtalk_kol_tidwe_kol_info` | KOL 主数据，294行 |
| `ods_dd_kol_shooting_resource` | `ods_dingtalk_outdoor_shoot_kol` | 拍摄资源 KOL 信息 |
| `ods_dd_kol_content` | `ods_dingtalk_kol_tidwe_content` | 内容上线记录 |
| `ods_dd_kol_sample_records` | `ods_dingtalk_kol_tidwe_sample` | 寄样记录 |
| `ods_dd_kol_payment` | `ods_dingtalk_outdoor_material_analysis` | KOL 红人支付表 |

---

## 整体数据血缘

```
ODS 层                                    DIM 层     DWD 层                    ADS 层
──────────────────────────────────────────────────────────────────────────────────────
ods_dingtalk_kol_tidwe_kol_info ──────┐                      ┌──────────────────────┐
ods_dingtalk_outdoor_shoot_kol ───────┤                      │                      │
ods_dingtalk_kol_tidwe_content ───────┤──────────────────────► dwd_kol_info_snapshot ──► ads_kol_profile
ods_dingtalk_kol_tidwe_sample ────────┤                      │                      │
ods_dingtalk_outdoor_material_analysis┘                      └──────────────────────┘
```

**说明：** 报表5为 KOL 信息快照表，无时序聚合，输出最新版 KOL 主数据。来源为多张钉钉多维表，以 `kol_id` 为主键合并。无 DWS 层（非事实数据），DWD 直出 ADS。

---

## ODS 源表说明

| ODS 表名 | 来源接口 | 业务含义 | 关键字段 |
|---------|---------|---------|---------|
| `ods_dingtalk_kol_tidwe_kol_info` | dingtalk / kol_tidwe_红人信息汇总 | KOL 主数据（294行） | `kol_id`, `follow_up_person`, `homepage_url`, `follower_count`, `long_video_avg_views`, `kol_level`, `cooperation_mode`, `payment_mode`, `promo_code`, `original_utm`, `email`, `sample_address`, `commission_rate`, `kol_type`, `state`, `full_name`, `payment_info`, `price_and_delivery`, `cooperation_review`, `next_action` |
| `ods_dingtalk_outdoor_shoot_kol` | dingtalk / outdoor_拍摄资源表KOL信息 | 拍摄资源 KOL 补充数据（含 TK 达人） | `shoot_kol`, `channel`, `followers`, `cooperation_phase`, `contact_person`, `youtube_url`, `tiktok_url`, `fb_ig_url`, `promo_code`, `payment_mode`, `cooperation_mode`, `kol_level`, `brand`, `contract_date` |
| `ods_dingtalk_kol_tidwe_content` | dingtalk / kol_tidwe_内容上线 | 内容发布记录（819行） | `kol_id`, `publish_platform`, `actual_publish_date`, `content_url`, `promo_code`, `promoted_product`, `cooperation_mode` |
| `ods_dingtalk_kol_tidwe_sample` | dingtalk / kol_tidwe_寄样记录 | 寄样记录（305行） | `kol_id`, `product`, `sample_date`, `tracking_number`, `sample_purpose` |
| `ods_dingtalk_outdoor_material_analysis` | dingtalk_sheet | KOL 红人支付表 | `username`, `round_actual_amount`, `store_attribution`, `cooperation_content`, `date` |

**字段类型说明：**
- `sample_date`：DATE 类型（已为标准日期，无需转换）
- `contract_date`：DATE 类型（已为标准日期，无需转换）
- `actual_publish_date`：DATE 类型（已为标准日期，无需转换）
- `follower_count`：VARCHAR，单位为 k（如 `5` 表示 5,000；`1.42` 表示 1,420）

---

## DIM 层

### `dim_kol`（本报表同时完善此维度表）

**业务含义：** KOL 全局维度表，汇总所有来源 KOL 的主键映射和基础属性
**粒度：** 每个 KOL 一条记录（全量快照）
**更新策略：** 每日全量覆盖

| 字段名 | 类型 | 来源 | 加工逻辑 |
|-------|------|------|----|
| `kol_id` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info | `kol_id` 直取（主键） |
| `kol_name` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info | `full_name` 直取 |
| `tiktok_username` | VARCHAR | ods_dingtalk_outdoor_shoot_kol | 从 `tiktok_url` 提取用户名 |
| `youtube_channel_id` | VARCHAR | ods_dingtalk_outdoor_shoot_kol | 从 `youtube_url` 提取频道 ID |
| `platform` | VARCHAR | ods_dingtalk_outdoor_shoot_kol | `channel` 直取 |
| `follower_cnt` | BIGINT | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_outdoor_shoot_kol | `follower_count`×1000（kol_info，单位k）或 `followers`（shoot，已为原始数值） |
| `etl_load_ts` | TIMESTAMP | — | ETL 写入时间 |

---

## DWD 层

### `dwd_kol_info_snapshot`

**业务含义：** KOL 信息多源合并快照，以 `kol_id` 为主键合并钉钉各表属性
**粒度：** 每个 KOL 一条记录（全量快照，无时序）
**更新策略：** 每日全量覆盖

#### 数据血缘

```
ods_dingtalk_kol_tidwe_kol_info（主表）
  LEFT JOIN ods_dingtalk_outdoor_shoot_kol ON kol_id = shoot_kol（名称/链接匹配，待维护映射表）
  LEFT JOIN ods_dingtalk_kol_tidwe_content ON kol_id（取最新发布日期 + 统计内容数量）
  LEFT JOIN ods_dingtalk_kol_tidwe_sample ON kol_id（统计寄样次数）
  LEFT JOIN ods_dingtalk_outdoor_material_analysis ON username ≈ kol_id（统计累计合作费）
  → 主键去重：保留 ods_dingtalk_kol_tidwe_kol_info 中最新 etl_time 的 kol_id 记录
        ↓
dwd_kol_info_snapshot
```

**合并策略：**
- 主表：`ods_dingtalk_kol_tidwe_kol_info`；`kol_id` 作为主键
- `ods_dingtalk_outdoor_shoot_kol` 通过 `shoot_kol` ↔ `kol_id` 名称/链接映射 JOIN（**待业务提供映射关系表**）
- 若同一 `kol_id` 在两表均有数据，主表字段优先，拍摄资源表补充缺失字段

#### 字段定义

| 字段名 | 类型 | 来源表 | 来源字段 | 加工逻辑 |
|-------|------|-------|----|--------|
| `partition_dt` | DATE | — | — | 等于数据提取日期 |
| `kol_id` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info | `kol_id` | 主键，直取 |
| `kol_full_name` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_outdoor_shoot_kol | `full_name` / `real_name` | 主表优先；为空则取拍摄资源表 `real_name` |
| `kol_type` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info | `kol_type` | 直取（如"工具, 枪支"） |
| `platform` | VARCHAR | ods_dingtalk_outdoor_shoot_kol | `channel` | 直取（如 YouTube / TikTok） |
| `owner` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_outdoor_shoot_kol | `follow_up_person` / `contact_person` | 主表优先 |
| `homepage_url` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_outdoor_shoot_kol | `homepage_url` | 主表优先；拍摄资源表按 channel 选择对应平台链接字段 |
| `ytb_url` | VARCHAR | ods_dingtalk_outdoor_shoot_kol | `youtube_url` | 直取 |
| `tiktok_url` | VARCHAR | ods_dingtalk_outdoor_shoot_kol | `tiktok_url` | 直取 |
| `ig_url` | VARCHAR | ods_dingtalk_outdoor_shoot_kol | `fb_ig_url` | 直取 |
| `location_state` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info | `state` | 直取 |
| `follower_cnt` | BIGINT | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_outdoor_shoot_kol | `follower_count` / `followers` | kol_info: CAST × 1000（单位 k，VARCHAR，如 `'5'`→5000, `'1.42'`→1420）；shoot: CAST AS BIGINT（原始数值）；主表优先 |
| `avg_views_k` | DECIMAL(10,2) | ods_dingtalk_kol_tidwe_kol_info | `long_video_avg_views` | 直取（单位 k，VARCHAR，保留原始值） |
| `kol_grade` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_outdoor_shoot_kol | `kol_level` | 直取（如 A / B / C） |
| `cooperation_mode` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_outdoor_shoot_kol | `cooperation_mode` | 主表优先 |
| `payment_mode` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_outdoor_shoot_kol | `payment_mode` / `cooperation_form` | 主表优先 |
| `price_note` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_outdoor_shoot_kol | `price_and_delivery` / `price_note` | 主表优先；非结构化文本，原样存储 |
| `commission_rate` | DECIMAL(6,4) | ods_dingtalk_kol_tidwe_kol_info | `commission_rate` | 解析百分比为小数；含 `#REF!` 的值置 NULL，`is_data_error = True` |
| `promo_code` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_kol_tidwe_content | `promo_code` / `promo_code` | 主表优先；多个 CODE 用逗号分隔 |
| `utm_url` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info | `original_utm` | 直取 |
| `email` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_outdoor_shoot_kol | `email` | 主表优先 |
| `other_contact` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_outdoor_shoot_kol | `other_contact` / `whatsapp` / `phone` | 拼接（格式：`"Whatsapp: xxx; Phone: xxx"`） |
| `shipping_address` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info | `sample_address` | 直取 |
| `payment_info` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info | `payment_info` | 直取（非结构化文本） |
| `cooperation_review` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info | `cooperation_review` | 直取 |
| `next_action` | VARCHAR | ods_dingtalk_kol_tidwe_kol_info | `next_action` | 直取 |
| `content_cnt` | BIGINT | ods_dingtalk_kol_tidwe_content | COUNT(*) per kol_id | 统计该 KOL 的内容上线数 |
| `latest_publish_dt` | DATE | ods_dingtalk_kol_tidwe_content | MAX(`actual_publish_date`) | 直取最大 DATE 值（已为 DATE 类型，无需转换） |
| `sample_cnt` | BIGINT | ods_dingtalk_kol_tidwe_sample | COUNT(*) per kol_id | 统计寄样次数 |
| `cooperation_status` | VARCHAR | ods_dingtalk_outdoor_shoot_kol | `cooperation_phase` | 直取（如"合作中"/"已结束"） |
| `brand` | VARCHAR | ods_dingtalk_outdoor_shoot_kol | `brand` | 直取（TideWe / Piscifun） |
| `is_data_error` | BOOLEAN | — | — | `commission_rate` 含 `#REF!` 等公式错误时置 True |
| `etl_load_ts` | TIMESTAMP | — | — | ETL 写入时间 |
| `data_source` | VARCHAR | — | — | 常量 `'dingtalk'` |

#### 关键加工逻辑

**粉丝数统一（单位 k → 原始数值）：**

```sql
-- ods_dingtalk_kol_tidwe_kol_info：follower_count 为 VARCHAR，单位 k
follower_cnt = CASE
  WHEN kol_info.follower_count IS NOT NULL
    THEN CAST(CAST(kol_info.follower_count AS DECIMAL(10,3)) * 1000 AS BIGINT)
  WHEN shoot.followers IS NOT NULL
    THEN CAST(shoot.followers AS BIGINT)  -- 已是原始数值
  ELSE NULL
END
```

**佣金率解析：**

```sql
-- commission_rate：格式为 "20%" 或 "#REF!" 等错误
commission_rate = CASE
  WHEN commission_rate LIKE '%REF%' OR commission_rate LIKE '%N/A%' THEN NULL
  WHEN commission_rate LIKE '%\%%' THEN CAST(REPLACE(commission_rate, '%', '') AS DECIMAL) / 100
  ELSE NULL
END
```

**日期字段（已为 DATE 类型，直接使用）：**

```sql
-- ods_dingtalk_kol_tidwe_sample.sample_date → DATE 类型，直接取值
-- ods_dingtalk_outdoor_shoot_kol.contract_date → DATE 类型，直接取值
-- ods_dingtalk_kol_tidwe_content.actual_publish_date → DATE 类型，直接取值

latest_publish_dt = MAX(c.actual_publish_date)  -- 无需时间戳转换
```

---

## ADS 层

### `ads_kol_profile`

**业务含义：** 报表5直接展示层，KOL 信息全量快照，字段名与《数据表需求》对齐
**粒度：** 每个 KOL 一条记录（全量快照）
**更新策略：** 每日全量覆盖
**下游使用：** 营销推广-KOL效果-KOL信息看板

#### 字段级血缘（ODS → ADS 完整链路）

| 报表字段 | ADS字段名 | 来源DWD字段 | 来源ODS表 | 来源ODS字段 | 加工类型 |
|---------|----------|-----------|---------|-----------|----|
| 红人ID | `kol_id` | `kol_id` | ods_dingtalk_kol_tidwe_kol_info | `kol_id` | 直取 |
| 红人类型 | `kol_type` | `kol_type` | ods_dingtalk_kol_tidwe_kol_info | `kol_type` | 直取 |
| 合作平台 | `platform` | `platform` | ods_dingtalk_outdoor_shoot_kol | `channel` | 直取 |
| 跟进人 | `owner` | `owner` | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_outdoor_shoot_kol | `follow_up_person` / `contact_person` | 主表优先 |
| 主页链接 | `homepage_url` | `homepage_url` | ods_dingtalk_kol_tidwe_kol_info | `homepage_url` | 直取 |
| 所在州 | `location_state` | `location_state` | ods_dingtalk_kol_tidwe_kol_info | `state` | 直取 |
| 粉丝数 | `follower_cnt` | `follower_cnt` | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_outdoor_shoot_kol | `follower_count` / `followers` | 统一为原始数值（kol_info ×1000） |
| 均播 | `avg_views_k` | `avg_views_k` | ods_dingtalk_kol_tidwe_kol_info | `long_video_avg_views` | 直取（单位 k） |
| 红人等级 | `kol_grade` | `kol_grade` | ods_dingtalk_kol_tidwe_kol_info | `kol_level` | 直取 |
| 合作模式 | `cooperation_mode` | `cooperation_mode` | ods_dingtalk_kol_tidwe_kol_info | `cooperation_mode` | 直取 |
| 付费模式 | `payment_mode` | `payment_mode` | ods_dingtalk_kol_tidwe_kol_info | `payment_mode` | 直取 |
| 合作价格及交付项 | `price_note` | `price_note` | ods_dingtalk_kol_tidwe_kol_info | `price_and_delivery` | 直取 |
| 佣金率 | `commission_rate` | `commission_rate` | ods_dingtalk_kol_tidwe_kol_info | `commission_rate` | 解析百分比；`#REF!` → NULL |
| 合作review | `cooperation_review` | `cooperation_review` | ods_dingtalk_kol_tidwe_kol_info | `cooperation_review` | 直取 |
| 后续动作 | `next_action` | `next_action` | ods_dingtalk_kol_tidwe_kol_info | `next_action` | 直取 |
| Code | `promo_code` | `promo_code` | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_kol_tidwe_content | `promo_code` | 主表优先 |
| UTM短链 | `utm_url` | `utm_url` | ods_dingtalk_kol_tidwe_kol_info | `original_utm` | 直取 |
| Email | `email` | `email` | ods_dingtalk_kol_tidwe_kol_info | `email` | 直取 |
| 其他联系方式 | `other_contact` | `other_contact` | ods_dingtalk_kol_tidwe_kol_info / ods_dingtalk_outdoor_shoot_kol | `other_contact` / `whatsapp` / `phone` | 拼接 |
| 全名 | `kol_full_name` | `kol_full_name` | ods_dingtalk_kol_tidwe_kol_info | `full_name` | 直取 |
| 寄样地址 | `shipping_address` | `shipping_address` | ods_dingtalk_kol_tidwe_kol_info | `sample_address` | 直取 |
| 收款信息 | `payment_info` | `payment_info` | ods_dingtalk_kol_tidwe_kol_info | `payment_info` | 直取 |
| 合作日期 | `contract_dt` | — | ods_dingtalk_outdoor_shoot_kol | `contract_date` | 直取（已为 DATE 类型） |
| 合作产品 | `cooperation_product` | — | ods_dingtalk_kol_tidwe_content | `promoted_product` | 取最近一条内容的推广产品；或聚合为逗号分隔列表 |
| 内容发布 | `latest_content_url` | — | ods_dingtalk_kol_tidwe_content | `content_url` | 取最新 `actual_publish_date` 对应链接 |

---

## 数据质量检查点

| 检查项 | 检查规则 | 处理方式 |
|-------|---------|---------|
| kol_id 唯一性 | `kol_id` 在 dwd_kol_info_snapshot 中不应有重复 | 去重保留最新 `etl_time` 行 |
| 佣金率错误值 | `commission_rate` 含 `#REF!` 或 `#N/A` | 置 NULL，`is_data_error = True`，告警人工核查 |
| 粉丝数单位 | `ods_dingtalk_kol_tidwe_kol_info.follower_count` 单位 k；`shoot.followers` 为原始数值 | 统一换算规则，验证换算后数值在合理范围内（100~10,000,000） |
| 跨表 kol_id 匹配 | `ods_dingtalk_outdoor_shoot_kol.shoot_kol` 通过名称/链接映射 `kol_id`，匹配失败率 | 记录未匹配行数，超过 10% 告警，提示维护映射配置 |
| 日期字段有效性 | `sample_date` / `actual_publish_date` / `contract_date` 均为 DATE 类型，直接校验范围 | 不在 2020~2030 范围内的记录置 NULL 并告警 |
| 钉钉表字段变更 | 每次钉钉 ODS 拉取后校验关键字段存在性（`kol_id`、`email`、`promo_code`） | 字段缺失则 DWD 停止更新，触发告警 |
