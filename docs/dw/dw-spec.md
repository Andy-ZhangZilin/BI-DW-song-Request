# 数仓设计规范 — 大户外业务数据平台

**项目：** 大户外数据平台（Piscifun / TideWe）
**版本：** v1.0
**日期：** 2026-04-14

---

## 1. 分层架构

```
数据源（API / 爬虫 / 文件）
        │
        ▼
  ┌─────────────┐
  │  ODS 贴源层  │  原始数据，结构不变，全量或增量入库
  └─────────────┘
        │
        ▼
  ┌─────────────┐
  │  DIM 维度层  │  跨层复用的主数据（店铺/渠道/KOL/产品/日期/财务科目）
  └─────────────┘
        │
        ▼
  ┌─────────────┐
  │  DWD 明细层  │  清洗、标准化、关联维度，保留最细粒度
  └─────────────┘
        │
        ▼
  ┌─────────────┐
  │  DWS 汇总层  │  按业务主题聚合，一张表支撑多张报表
  └─────────────┘
        │
        ▼
  ┌─────────────┐
  │  ADS 应用层  │  字段名与需求文档对齐，直连 BI
  └─────────────┘
```

### 各层职责边界

| 层级 | 职责 | 禁止 |
|------|------|------|
| ODS | 一个接口/源表对应一张 ODS 表；字段名保留源系统原始名；只做类型最小转换（数字/字符/时间） | 不做业务计算；不做多源合并 |
| DIM | 维护全局通用主数据；字段需结构化、有明确主键 | 不含事实度量值 |
| DWD | 清洗去重、类型标准化、关联维度 ID、过滤无效记录 | 不做跨主题聚合 |
| DWS | 按业务主题按日/月聚合 | 不直接引用 ODS |
| ADS | 字段名直接对应业务报表需求文档 | 不含未在需求中定义的字段 |

---

## 2. 命名规范

### 2.1 表命名格式

```
{层级前缀}_{数据域缩写}_{主题}[_{粒度后缀}]
```

| 层级 | 前缀 | 示例 |
|------|------|------|
| ODS | `ods_` | `ods_tw_pixel_orders` |
| DIM | `dim_` | `dim_kol` |
| DWD | `dwd_` | `dwd_order_detail` |
| DWS | `dws_` | `dws_marketing_channel_d` |
| ADS | `ads_` | `ads_profit_report` |

**粒度后缀：**`_d`（日）、`_m`（月）、`_all`（全量快照）

**数据域缩写参考：**

| 数据域 | 缩写 | 包含数据源 |
|-------|------|----------|
| TripleWhale | `tw_` | TripleWhale 全部接口 |
| TikTok | `tiktok_` | TikTok Shop API |
| 钉钉 | `dd_` | 钉钉多维表 / 普通表格 |
| 联盟 | `aff_` | Awin / PartnerBoost |
| EDM | `edm_` | CartSee |
| YouTube | `yt_` | YouTube API / URL 解析 |
| 财务 | `finance_` | 财务BI多平台订单 |

**规则：** 全部小写；单词间用下划线；不使用中文；不超过 64 字符。

### 2.2 字段命名规则

| 字段类别 | 命名格式 | 示例 |
|---------|---------|------|
| 业务主键 | `{实体}_id` | `kol_id`, `order_id` |
| 外键 | `{关联实体}_id` | `shop_id`, `sku_id` |
| 分区日期 | `partition_dt` | — |
| 业务日期 | `{语义}_dt` / `dt` | `publish_dt`, `dt` |
| 时间戳 | `{语义}_ts` | `create_ts` |
| 金额 | `{语义}_amt` | `revenue_amt`, `cost_amt` |
| 数量 | `{语义}_cnt` / `{语义}_qty` | `order_cnt`, `item_qty` |
| 比率 | `{语义}_rate` | `commission_rate`, `open_rate` |
| 布尔标志 | `is_{语义}` | `is_new_customer`, `is_deleted` |
| 枚举类型 | `{语义}_type` / `{语义}_category` | `content_type`, `channel_category` |

### 2.3 通用技术字段

**所有 ODS 和 DWD 表必含以下字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `partition_dt` | DATE | 数据分区日期（增量表=数据业务日期；全量表=抽取日期） |
| `etl_load_ts` | TIMESTAMP | ETL 写入时间，用于追溯 |
| `data_source` | VARCHAR(50) | 数据源标识，与 outdoor-data-validator 的 source 名称对齐 |

---

## 3. 数据更新策略

| 策略 | 适用场景 | 说明 |
|------|---------|------|
| **增量追加** | API 接口类 ODS（TW、TikTok、Awin、PB、CartSee） | 按 `partition_dt` 分区写入，历史分区不覆盖 |
| **每日全量覆盖** | 钉钉类 ODS、财务 BI | 每次抽取全量数据，以 `etl_load_ts` 区分版本 |
| **静态手动维护** | dim_finance_subject、dim_channel_keyword | 人工更新，不设自动 ETL |
| **T+1 全量重算** | DWS 层、ADS 层 | 每日全量重跑，保证幂等，容许下游重复读 |

---

## 4. 数据质量规则

| 规则类型 | 检测点 | 处理方式 |
|---------|-------|---------|
| 主键唯一 | ODS/DWD 主键不允许重复 | ETL 去重，保留 `etl_load_ts` 最新记录 |
| 非空约束 | 主键、分区字段、核心度量值（金额/数量）不允许为 NULL | ETL 过滤，写入异常日志 |
| 数值合理性 | 金额、数量不允许负数 | 过滤，标记 `is_data_error = True` |
| 枚举合法性 | `content_type`、`channel_category` 等枚举字段 | 不在枚举范围内的写入 `unknown`，不丢弃 |
| 分区完整性 | 每日增量分区必须到货 | 缺数告警，不阻塞下游（下游保持前一日数据） |
| 错误值处理 | 钉钉公式字段可能含 `#REF!`、`#N/A` 等错误 | 置 NULL，标记 `is_data_error = True` |
| 删除记录 | 财务 BI `是否删除 = 1` | ODS 全量保留原始数据；DWD 过滤 `is_deleted = 0` |

---

## 5. 数据血缘规范

### 5.1 血缘描述格式

每张 DWD/DWS/ADS 表必须在加工文档中包含以下血缘信息：

```
来源表                加工逻辑摘要              目标表
──────────────────────────────────────────────────────
ods_xxx             过滤/清洗/关联/聚合 →     dwd_xxx / dws_xxx / ads_xxx
dim_yyy             关联维度 →
```

### 5.2 血缘关系图（全局层级视图）

血缘图以"报表域"为单位组织，每个报表域展示从 ODS 到 ADS 的完整链路：

```
报表域：{报表名称}

ODS 层                DIM 层          DWD 层            DWS 层          ADS 层
───────────────────────────────────────────────────────────────────────────────
ods_xxx_a  ─┐
            ├─(JOIN dim_yyy)─→  dwd_aaa  ─┐
ods_xxx_b  ─┘                              ├─(聚合)─→  dws_bbb  ─→  ads_report_x
dim_yyy    ──────────────────────────────  ┘
```

### 5.3 字段级血缘表（每张 ADS 表必含）

在 ADS 层加工文档中，每个输出字段必须记录来源：

| 输出字段 | 来源层级 | 来源表 | 来源字段 | 加工逻辑 |
|---------|---------|-------|---------|---------|
| `字段名` | DWS/DWD | `表名` | `字段名` | 直取 / 计算公式 / 枚举转换 / JOIN 关联 |

**加工逻辑类型说明：**

| 类型 | 说明 | 示例 |
|------|------|------|
| 直取 | 字段直接映射，无转换 | `dt = event_date` |
| 类型转换 | 数据类型或单位转换 | `publish_dt = FROM_UNIXTIME(ts/1000)` |
| 计算 | 数值聚合或计算公式 | `open_cnt = sent_cnt × open_rate` |
| 枚举转换 | 枚举值映射 | `platform = CASE channel WHEN 'meta-analytics' THEN 'Facebook'` |
| JOIN 关联 | 通过主键关联其他表取值 | `shop_name = JOIN dim_shop ON shop_id` |
| 过滤 | 字段值约束条件 | `WHERE is_deleted = 0` |
| 缺失 | 当前无数据来源 | 标注缺失原因和建议补充方案 |

---

## 6. 加工文档模板

每张 DWD/DWS/ADS 表对应一份加工文档，统一以下结构：

```markdown
## {表名}

**层级：** DWD / DWS / ADS
**业务含义：** 一句话说明该表的业务用途
**粒度：** 每行代表什么（如：每日×渠道×店铺 一条记录）
**更新策略：** 增量追加 / T+1 全量重算
**下游使用：** {被哪些 DWS/ADS 表使用}

### 数据血缘

{按 5.2 格式绘制血缘图}

### 字段定义

{按 5.3 格式的字段级血缘表}

### 关键加工逻辑

{说明非直取字段的具体处理逻辑，含 SQL 片段}

### 数据质量检查点

{列出该表的特殊质量检查规则}
```

---

## 7. 开发前置输入要求

以下主数据在 ETL 开发启动前须由业务/财务确认并提供，否则对应 ADS 表无法完整实现：

| # | 输入项 | 责任方 | 影响层级 |
|---|-------|-------|---------|
| 1 | 财务科目四级树（ID / 名称 / 层级归属） | 财务 | dim_finance_subject → ads_finance_subject |
| 2 | 渠道归因关键词映射（TW pixel 渠道分类规则） | 业务 | dim_channel_keyword → dws_marketing_channel_d |
| 3 | TikTok 店铺 ID → 店铺名称 配置 | 运营 | ads_tiktok_sales_category |
| 4 | 合思费控数据接入方案（KOL/EDM/联盟花费） | 数据/财务 | dws_marketing_channel_d / ads_kol_cooperation_effect |
| 5 | OMS 寄样单接入方案（样品费 = 采购 + 头程 + 尾程） | 数据/供应链 | ads_kol_cooperation_effect |
| 6 | TikTok 新客判断口径（平台接口无此字段） | 业务 | ads_tiktok_sales_category |
| 7 | 多品牌 KOL 表合并规则（TideWe / Piscifun / TK 达人三表） | 业务/数据 | dim_kol / dwd_kol_info |
| 8 | Facebook / YouTube Studio 账号授权（当前认证失败） | 运营 | ads_social_account / ads_social_content |
