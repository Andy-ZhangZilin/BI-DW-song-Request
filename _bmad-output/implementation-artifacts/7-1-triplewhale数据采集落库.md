# Story 7-1: TripleWhale 数据采集落库

**状态**: done
**Epic**: 7
**前置故事**: 6-0（SDK 客户端）、6-1（Doris 写入工具）、6-2（水位线管理器）
**生成时间**: 2026-04-16

---

## 背景与目标

TripleWhale 是主要的广告归因与数据分析平台。本 Story 实现 10 张 TripleWhale 表的
每日数据采集并落库 Apache Doris，供后续 BI 分析使用。

依赖关系：
- Story 6.0：SDK 客户端（`sdk/triplewhale/`）已完成
- Story 6.1：公共 Doris 写入工具（`common/doris_writer.py`）已完成
- Story 6.2：水位线管理器（`common/watermark.py`）已完成
- Story 6.3：分片并发框架（`common/chunked_fetch.py`）**仍在 backlog**
  → sessions_table（10M 行）需要特殊处理，见"sessions_table 特殊处理"章节

---

## 验收标准

1. 新增文件 `bi/python_sdk/outdoor_collector/collectors/tw_collector.py`
2. 支持 CLI：`python tw_collector.py --table TABLE_NAME [--mode full|incremental]
   [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]`
3. `--table all` 时按顺序采集所有 10 张表，单表失败打印错误后继续
4. 首次运行（无水位线 或 `--mode full`）→ 全量拉取（从各表最早日期至今）
5. 后续运行（有水位线 且未指定 `--mode full`）→ 增量拉取（从上次水位线至今）
6. 写入采用 upsert（ON DUPLICATE KEY UPDATE），多次运行结果幂等
7. sessions_table 按天分片拉取（每次拉取单天数据），加 TODO(story-6.3) 注释
8. `TRIPLEWHALE_API_KEY` 环境变量缺失时，启动即抛 RuntimeError（不执行任何网络请求）
9. 通过 `tests/test_tw_collector.py` 所有单元测试
10. 程序正常退出时打印采集摘要（各表写入行数）

---

## 任务清单

- [ ] 设计 10 张 Doris 表 DDL，在 `_TABLE_DDLS` 字典中定义
- [ ] 实现 `ensure_tables()` 函数：建表（幂等）
- [ ] 实现通用 `_serialize_row()` 函数：数组/布尔字段转换
- [ ] 为每张表实现 `_transform_<snake_table_name>()` 转换函数
- [ ] 实现 `collect_table()` 核心采集逻辑：水位线→日期范围→分批拉取→写入→更新水位线
- [ ] sessions_table 按天分片实现（加 TODO 注释）
- [ ] 实现 `collect_all()` 遍历所有表（异常捕获，单表不中断整体）
- [ ] CLI 入口（argparse）
- [ ] 编写 `tests/test_tw_collector.py`：覆盖 transform、collect_table 的 mock 测试

---

## 开发笔记

### 文件路径

```
bi/python_sdk/outdoor_collector/collectors/tw_collector.py   ← 新增（主仓库 bi/ 子模块）
tests/test_tw_collector.py                                   ← 新增（主仓库 tests/ 目录）
```

### import 路径模式

```python
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sdk.triplewhale.client import TripleWhaleClient
from sdk.triplewhale.auth import TABLE_DATE_COLUMNS
from common.watermark import (
    ensure_table as _ensure_watermark_table,
    get_watermark,
    update_watermark,
    reset_watermark,
)
from common.doris_writer import write_to_doris
import pymysql
import json
import logging
import argparse
from datetime import datetime, date, timedelta
from typing import Optional
from doris_config import DorisConfig
```

### 环境变量与 SDK 初始化

```python
SOURCE = "triplewhale"

def _get_client() -> TripleWhaleClient:
    api_key = os.environ.get("TRIPLEWHALE_API_KEY", "")
    if not api_key:
        raise RuntimeError("[tw_collector] 未配置 TRIPLEWHALE_API_KEY 环境变量")
    return TripleWhaleClient(api_key=api_key)
```

### 表名映射与元数据

```python
# TripleWhale 表名 → Doris 表名
TABLE_DORIS_NAMES = {
    "pixel_orders_table":           "hqware.ods_tw_pixel_orders",
    "pixel_joined_tvf":             "hqware.ods_tw_pixel_joined",
    "sessions_table":               "hqware.ods_tw_sessions",
    "product_analytics_tvf":        "hqware.ods_tw_product_analytics",
    "pixel_keywords_joined_tvf":    "hqware.ods_tw_pixel_keywords_joined",
    "ads_table":                    "hqware.ods_tw_ads",
    "social_media_comments_table":  "hqware.ods_tw_social_media_comments",
    "social_media_pages_table":     "hqware.ods_tw_social_media_pages",
    "creatives_table":              "hqware.ods_tw_creatives",
    "ai_visibility_table":          "hqware.ods_tw_ai_visibility",
}

# 各表唯一键列名列表（与 Doris DDL UNIQUE KEY 对应）
TABLE_UNIQUE_KEYS = {
    "pixel_orders_table":           ["order_id"],
    "pixel_joined_tvf":             ["event_date", "channel", "account_id", "campaign_id", "adset_id", "ad_id"],
    "sessions_table":               ["session_id"],
    "product_analytics_tvf":        ["event_date", "entity", "id"],
    "pixel_keywords_joined_tvf":    ["event_date", "channel", "keyword_id"],
    "ads_table":                    ["event_date", "channel", "account_id", "campaign_id", "adset_id", "ad_id"],
    "social_media_comments_table":  ["comment_id"],
    "social_media_pages_table":     ["event_date", "page_id", "channel"],
    "creatives_table":              ["event_date", "channel", "ad_id", "asset_id"],
    "ai_visibility_table":          ["event_date"],
}

# 各表全量拉取起始日期（来自 triplewhale-raw.md 数据概况）
TABLE_EARLIEST_DATES = {
    "pixel_orders_table":           "2022-03-21",
    "pixel_joined_tvf":             "2021-12-05",
    "sessions_table":               "2023-12-03",
    "product_analytics_tvf":        "2022-03-21",
    "pixel_keywords_joined_tvf":    "2023-07-18",
    "ads_table":                    "2021-12-05",
    "social_media_comments_table":  "2025-09-28",
    "social_media_pages_table":     "2026-01-04",
    "creatives_table":              "2022-05-13",
    "ai_visibility_table":          "2024-01-01",
}

ALL_TABLES = list(TABLE_DORIS_NAMES.keys())
```

### 通用行转换函数

```python
def _serialize_row(row: dict) -> dict:
    """
    通用转换：
      - list / dict  → json.dumps 字符串
      - bool         → 1 / 0（TINYINT）
      - 其他类型原样返回
    """
    result = {}
    for k, v in row.items():
        if isinstance(v, bool):
            result[k] = 1 if v else 0
        elif isinstance(v, (list, dict)):
            result[k] = json.dumps(v, ensure_ascii=False)
        else:
            result[k] = v
    return result
```

大多数表的 `_transform_<table>` 函数可直接调用 `_serialize_row`：

```python
def _transform_sessions_table(rows: list[dict]) -> list[dict]:
    return [_serialize_row(r) for r in rows]
```

对于字段多、需要重命名的表（目前 TripleWhale 字段名与 Doris 列名一致，无需重命名），
直接复用通用函数即可。每张表必须有独立的 `_transform_<snake_name>` 函数，便于后续
扩展字段过滤或类型强制转换。

### 全量/增量日期范围逻辑

```python
def _resolve_date_range(
    table_name: str,
    mode: str,
    start_date: Optional[str],
    end_date: Optional[str],
) -> tuple[str, str]:
    """
    返回 (period_start, period_end)。
    优先级：CLI 显式指定 > 水位线 > 最早日期（全量）。
    """
    today = str(date.today())
    if end_date is None:
        end_date = today

    if start_date is not None:
        return start_date, end_date

    if mode == "full":
        return TABLE_EARLIEST_DATES[table_name], end_date

    wm = get_watermark(SOURCE, table_name)
    if wm is None:
        # 首次运行 → 全量
        return TABLE_EARLIEST_DATES[table_name], end_date
    else:
        last_ok = wm["last_success_time"]
        if isinstance(last_ok, datetime):
            last_ok = last_ok.date()
        return str(last_ok), end_date
```

### 核心采集逻辑

```python
def collect_table(
    table_name: str,
    mode: str = "incremental",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> int:
    """
    采集单张表。返回写入行数。

    大致流程：
    1. 解析日期范围
    2. sessions_table 按天分片拉取；其他表一次性拉取
    3. 调用 _transform_<table> 转换
    4. write_to_doris upsert 写入
    5. 更新水位线（成功写入后）
    """
    client = _get_client()
    period_start, period_end = _resolve_date_range(table_name, mode, start_date, end_date)
    doris_table = TABLE_DORIS_NAMES[table_name]
    unique_keys = TABLE_UNIQUE_KEYS[table_name]
    date_col = TABLE_DATE_COLUMNS[table_name]
    transform_fn = _TRANSFORM_FUNCS[table_name]

    if table_name == "sessions_table":
        total = _collect_sessions_by_day(
            client, period_start, period_end, doris_table, unique_keys, transform_fn
        )
    else:
        sql = (
            f"SELECT * FROM {table_name} "
            f"WHERE {date_col} >= '{period_start}' "
            f"AND {date_col} <= '{period_end}'"
        )
        rows = client.execute_sql(sql, period_start, period_end)
        records = transform_fn(rows)
        total = write_to_doris(doris_table, records, unique_keys, source=SOURCE)

    if total > 0 or mode == "full":
        success_time = datetime.strptime(period_end, "%Y-%m-%d")
        update_watermark(SOURCE, table_name, success_time)

    return total
```

### sessions_table 特殊处理

sessions_table 历史数据约 1070 万行，单次 API 最多返回 1000 行。
全量拉取需按天切分，每次拉取单天数据。

```python
def _collect_sessions_by_day(
    client, period_start: str, period_end: str,
    doris_table: str, unique_keys: list, transform_fn
) -> int:
    # TODO(story-6.3): 当 chunked_fetch 框架可用时，迁移至
    # chunked_fetch.fetch_chunked(table="sessions_table", ...)
    # 以支持并发分片拉取，提升全量拉取速度（当前实现为串行按天分片）。
    total = 0
    cur = datetime.strptime(period_start, "%Y-%m-%d").date()
    end = datetime.strptime(period_end, "%Y-%m-%d").date()
    date_col = TABLE_DATE_COLUMNS["sessions_table"]

    while cur <= end:
        day_str = str(cur)
        sql = (
            f"SELECT * FROM sessions_table "
            f"WHERE {date_col} = '{day_str}'"
        )
        try:
            rows = client.execute_sql(sql, day_str, day_str)
            if rows:
                records = transform_fn(rows)
                written = write_to_doris(
                    doris_table, records, unique_keys, source=SOURCE
                )
                total += written
        except Exception as e:
            logger.warning(f"[{SOURCE}][sessions_table] {day_str} 拉取失败，跳过：{e}")
        cur += timedelta(days=1)
    return total
```

### ensure_tables 函数

```python
def ensure_tables() -> None:
    """建表（幂等），程序启动时调用。"""
    _ensure_watermark_table()
    config = DorisConfig()
    conn = None
    try:
        conn = pymysql.connect(**config.DB_CONFIG)
        with conn.cursor() as cursor:
            for table_name, ddl in _TABLE_DDLS.items():
                cursor.execute(ddl.strip())
                logger.info(f"[{SOURCE}] 表 {TABLE_DORIS_NAMES[table_name]} 确认存在")
        conn.commit()
    except Exception as e:
        raise RuntimeError(f"[{SOURCE}] 建表失败：{e}") from e
    finally:
        if conn:
            conn.close()
```

### collect_all 函数

```python
def collect_all(mode: str = "incremental") -> dict[str, int]:
    """采集所有 10 张表，单表异常不中断整体。返回各表写入行数。"""
    results = {}
    for table_name in ALL_TABLES:
        try:
            n = collect_table(table_name, mode=mode)
            results[table_name] = n
        except Exception as e:
            logger.error(f"[{SOURCE}][{table_name}] 采集失败：{e}")
            results[table_name] = -1
    return results
```

---

### Doris DDL（10 张表）

**建表原则：**
- UNIQUE KEY 模型，主键列必须 NOT NULL
- `string` → `VARCHAR(255)`；长文本（URL、HTML、注释等）→ `TEXT`
- `number` → `DOUBLE`
- `boolean` → `TINYINT`（Python True/False → 1/0）
- `array`/`object` → `TEXT`（存储 json.dumps 字符串，加 COMMENT 说明）
- `null`（未知类型）→ `VARCHAR(255) NULL`
- 所有表：`PROPERTIES ("replication_num" = "1")`

完整字段列表依据 `reports/triplewhale-raw.md`。

#### ods_tw_sessions

```sql
CREATE TABLE IF NOT EXISTS hqware.ods_tw_sessions (
    session_id              VARCHAR(128) NOT NULL COMMENT '会话ID（唯一键）',
    event_date              DATE         NOT NULL COMMENT '事件日期',
    event_date_timezone     VARCHAR(64)  NULL,
    event_hour              INT          NULL,
    session_start_ts        DATETIME     NULL,
    session_elapsed_time    DOUBLE       NULL,
    session_page_views      INT          NULL,
    shop_id                 VARCHAR(128) NULL,
    shop_name               VARCHAR(64)  NULL,
    domain                  VARCHAR(128) NULL,
    triple_id               VARCHAR(64)  NULL,
    channel                 VARCHAR(128) NULL,
    source                  VARCHAR(128) NULL,
    utm_source              VARCHAR(128) NULL,
    utm_medium              VARCHAR(128) NULL,
    ad_id                   VARCHAR(128) NULL,
    adset_id                VARCHAR(128) NULL,
    campaign_id             VARCHAR(128) NULL,
    keyword_id              VARCHAR(128) NULL,
    landing_page            TEXT         NULL,
    browser                 VARCHAR(64)  NULL,
    device                  VARCHAR(64)  NULL,
    device_model            VARCHAR(64)  NULL,
    country                 VARCHAR(64)  NULL,
    country_code            VARCHAR(8)   NULL,
    city                    VARCHAR(128) NULL,
    is_new_visitor          TINYINT      NULL,
    ms_country              VARCHAR(8)   NULL,
    ms_country_name         VARCHAR(64)  NULL
)
UNIQUE KEY(session_id)
DISTRIBUTED BY HASH(session_id) BUCKETS 8
PROPERTIES ("replication_num" = "1");
```

#### ods_tw_social_media_comments

```sql
CREATE TABLE IF NOT EXISTS hqware.ods_tw_social_media_comments (
    comment_id              VARCHAR(128) NOT NULL COMMENT '评论ID（唯一键）',
    post_id                 VARCHAR(128) NULL,
    page_id                 VARCHAR(128) NULL,
    user_id                 VARCHAR(128) NULL,
    account_id              VARCHAR(128) NULL,
    integration_id          VARCHAR(128) NULL,
    channel                 VARCHAR(64)  NULL,
    comment_text            TEXT         NULL,
    created_at              DATETIME     NULL,
    visibility_status       VARCHAR(64)  NULL,
    visibility_changed_at   DATETIME     NULL,
    visibility_changed_by   VARCHAR(128) NULL,
    risk                    VARCHAR(32)  NULL,
    sentiment               VARCHAR(32)  NULL,
    topic                   VARCHAR(64)  NULL
)
UNIQUE KEY(comment_id)
DISTRIBUTED BY HASH(comment_id) BUCKETS 4
PROPERTIES ("replication_num" = "1");
```

#### ods_tw_social_media_pages

```sql
CREATE TABLE IF NOT EXISTS hqware.ods_tw_social_media_pages (
    event_date              DATE         NOT NULL,
    page_id                 VARCHAR(128) NOT NULL,
    channel                 VARCHAR(64)  NOT NULL,
    page_name               VARCHAR(128) NULL,
    page_permalink          TEXT         NULL,
    website                 TEXT         NULL,
    about                   TEXT         NULL,
    category                VARCHAR(128) NULL,
    cover_url               TEXT         NULL,
    image_url               TEXT         NULL,
    fan_adds                DOUBLE       NULL,
    fan_removes             DOUBLE       NULL,
    impressions             DOUBLE       NULL,
    impressions_paid        DOUBLE       NULL,
    impressions_unique      DOUBLE       NULL,
    impressions_viral       DOUBLE       NULL,
    video_views             DOUBLE       NULL,
    views_total             DOUBLE       NULL
)
UNIQUE KEY(event_date, page_id, channel)
DISTRIBUTED BY HASH(event_date) BUCKETS 4
PROPERTIES ("replication_num" = "1");
```

#### ods_tw_product_analytics

```sql
CREATE TABLE IF NOT EXISTS hqware.ods_tw_product_analytics (
    event_date                      DATE         NOT NULL,
    entity                          VARCHAR(32)  NOT NULL COMMENT 'product 或 variant',
    id                              VARCHAR(64)  NOT NULL COMMENT '商品/变体 ID',
    product_id                      VARCHAR(64)  NULL,
    product_name                    TEXT         NULL,
    product_title                   TEXT         NULL,
    name                            TEXT         NULL,
    title                           TEXT         NULL,
    product_status                  VARCHAR(32)  NULL,
    product_image_url               TEXT         NULL,
    sku                             VARCHAR(128) NULL,
    vendor                          VARCHAR(128) NULL,
    number_of_ads                   DOUBLE       NULL,
    inventory_quantity              DOUBLE       NULL,
    collection_id                   VARCHAR(64)  NULL,
    collection_name                 VARCHAR(255) NULL,
    variant_id                      VARCHAR(64)  NULL,
    variant_name                    VARCHAR(255) NULL,
    variant_title                   VARCHAR(255) NULL,
    shop_id                         VARCHAR(128) NULL,
    shop_name                       VARCHAR(64)  NULL,
    clicks                          DOUBLE       NULL,
    impressions                     DOUBLE       NULL,
    visits                          DOUBLE       NULL,
    customers                       DOUBLE       NULL,
    orders                          DOUBLE       NULL,
    revenue                         DOUBLE       NULL,
    total_order_value               DOUBLE       NULL,
    total_items_sold                DOUBLE       NULL,
    spend                           DOUBLE       NULL,
    fulfillment_costs               DOUBLE       NULL,
    new_customer_orders             DOUBLE       NULL,
    new_customer_revenue            DOUBLE       NULL,
    new_customer_total_order_value  DOUBLE       NULL,
    new_customer_total_items_sold   DOUBLE       NULL,
    new_customer_fulfillment_costs  DOUBLE       NULL,
    repeat_customer                 DOUBLE       NULL,
    returns                         DOUBLE       NULL,
    added_to_cart_events            DOUBLE       NULL,
    added_to_cart_items             DOUBLE       NULL,
    product_tags                    TEXT         NULL COMMENT 'JSON array',
    images                          TEXT         NULL COMMENT 'JSON array'
)
UNIQUE KEY(event_date, entity, id)
DISTRIBUTED BY HASH(event_date) BUCKETS 4
PROPERTIES ("replication_num" = "1");
```

#### ods_tw_pixel_orders

```sql
CREATE TABLE IF NOT EXISTS hqware.ods_tw_pixel_orders (
    order_id                        VARCHAR(64)  NOT NULL COMMENT '订单ID（唯一键）',
    event_date                      DATE         NULL,
    created_at                      DATETIME     NULL,
    order_name                      VARCHAR(64)  NULL,
    shop_id                         VARCHAR(128) NULL,
    shop_name                       VARCHAR(64)  NULL,
    shop_timezone                   VARCHAR(64)  NULL,
    integration_id                  VARCHAR(128) NULL,
    platform                        VARCHAR(32)  NULL,
    channel                         VARCHAR(128) NULL,
    source_name                     VARCHAR(64)  NULL,
    financial_status                VARCHAR(32)  NULL,
    fulfillment_status              VARCHAR(32)  NULL,
    cancelled_at                    DATETIME     NULL,
    currency                        VARCHAR(8)   NULL,
    currency_rate                   DOUBLE       NULL,
    gross_sales                     DOUBLE       NULL,
    gross_product_sales             DOUBLE       NULL,
    order_revenue                   DOUBLE       NULL,
    refund_money                    DOUBLE       NULL,
    discount_amount                 DOUBLE       NULL,
    discount_code                   VARCHAR(64)  NULL,
    shipping_costs                  DOUBLE       NULL,
    shipping_price                  DOUBLE       NULL,
    shipping_tax                    DOUBLE       NULL,
    handling_fees                   DOUBLE       NULL,
    payment_gateway_costs           DOUBLE       NULL,
    taxes                           DOUBLE       NULL,
    cogs                            DOUBLE       NULL,
    cost_of_goods                   DOUBLE       NULL,
    orders_quantity                 DOUBLE       NULL,
    product_quantity_sold_in_order  DOUBLE       NULL,
    custom_gross_profit             DOUBLE       NULL,
    custom_gross_sales              DOUBLE       NULL,
    custom_net_revenue              DOUBLE       NULL,
    custom_combined_gross_profit    DOUBLE       NULL,
    custom_combined_gross_sales     DOUBLE       NULL,
    custom_combined_net_revenue     DOUBLE       NULL,
    custom_expenses                 DOUBLE       NULL,
    custom_number                   DOUBLE       NULL,
    custom_orders_quantity          DOUBLE       NULL,
    custom_total_items_quantity     DOUBLE       NULL,
    custom_status                   VARCHAR(64)  NULL,
    custom_string                   VARCHAR(255) NULL,
    customer_id                     VARCHAR(64)  NULL,
    customer_first_name             VARCHAR(128) NULL,
    customer_last_name              VARCHAR(128) NULL,
    customer_email                  VARCHAR(255) NULL,
    is_new_customer                 TINYINT      NULL,
    is_subscription_order           TINYINT      NULL,
    is_first_order_in_subscription  TINYINT      NULL,
    triple_id                       VARCHAR(64)  NULL,
    session_id                      VARCHAR(128) NULL,
    model                           VARCHAR(64)  NULL,
    attribution_window              VARCHAR(32)  NULL,
    linear_weight                   DOUBLE       NULL,
    ad_id                           VARCHAR(128) NULL,
    adset_id                        VARCHAR(128) NULL,
    campaign_id                     VARCHAR(128) NULL,
    ad_name                         VARCHAR(255) NULL,
    adset_name                      VARCHAR(255) NULL,
    campaign_name                   VARCHAR(255) NULL,
    campaign_type                   VARCHAR(64)  NULL,
    account_id                      VARCHAR(64)  NULL,
    click_date                      DATE         NULL,
    click_ts                        DATETIME     NULL,
    billing_city                    VARCHAR(128) NULL,
    billing_country                 VARCHAR(128) NULL,
    billing_country_code            VARCHAR(8)   NULL,
    billing_province                VARCHAR(128) NULL,
    shipping_city                   VARCHAR(128) NULL,
    shipping_country                VARCHAR(128) NULL,
    shipping_country_code           VARCHAR(8)   NULL,
    shipping_country_name           VARCHAR(128) NULL,
    shipping_state                  VARCHAR(128) NULL,
    shipping_state_code             VARCHAR(8)   NULL,
    shipping_zip                    VARCHAR(32)  NULL,
    customer_from_city              VARCHAR(128) NULL,
    customer_from_country_code      VARCHAR(8)   NULL,
    customer_from_country_name      VARCHAR(128) NULL,
    customer_from_state_code        VARCHAR(8)   NULL,
    session_city                    VARCHAR(128) NULL,
    session_country                 VARCHAR(128) NULL,
    browser                         VARCHAR(64)  NULL,
    device                          VARCHAR(64)  NULL,
    landing_page                    TEXT         NULL,
    event_hour                      DOUBLE       NULL,
    utm_source                      VARCHAR(128) NULL,
    utm_medium                      VARCHAR(128) NULL,
    customer_tags                   TEXT         NULL COMMENT 'JSON array',
    discount_codes                  TEXT         NULL COMMENT 'JSON array',
    products_info                   TEXT         NULL COMMENT 'JSON array',
    tags                            TEXT         NULL COMMENT 'JSON array'
)
UNIQUE KEY(order_id)
DISTRIBUTED BY HASH(order_id) BUCKETS 8
PROPERTIES ("replication_num" = "1");
```

#### ods_tw_pixel_joined

> 完整字段参见 `reports/triplewhale-raw.md` → `pixel_joined_tvf` 章节（约 120 列）。
> 以下为主要非空字段；未在此列出的 null-type 字段（如实验相关字段）需补充为
> `VARCHAR(255) NULL`。

```sql
CREATE TABLE IF NOT EXISTS hqware.ods_tw_pixel_joined (
    event_date                          DATE         NOT NULL,
    channel                             VARCHAR(128) NOT NULL,
    account_id                          VARCHAR(64)  NOT NULL,
    campaign_id                         VARCHAR(128) NOT NULL,
    adset_id                            VARCHAR(128) NOT NULL,
    ad_id                               VARCHAR(128) NOT NULL,
    -- 广告层级维度
    ad_name                             VARCHAR(255) NULL,
    ad_copy                             VARCHAR(255) NULL,
    ad_type                             VARCHAR(32)  NULL,
    ad_status                           VARCHAR(32)  NULL,
    ad_image_url                        TEXT         NULL,
    ad_bid_amount                       DOUBLE       NULL,
    adset_name                          VARCHAR(255) NULL,
    adset_status                        VARCHAR(32)  NULL,
    adset_bid_amount                    DOUBLE       NULL,
    adset_bid_strategy                  VARCHAR(64)  NULL,
    adset_daily_budget                  DOUBLE       NULL,
    adset_lifetime_budget               DOUBLE       NULL,
    campaign_name                       VARCHAR(255) NULL,
    campaign_status                     VARCHAR(32)  NULL,
    campaign_type                       VARCHAR(64)  NULL,
    campaign_sub_type                   VARCHAR(64)  NULL,
    campaign_bid_strategy               VARCHAR(64)  NULL,
    campaign_daily_budget               DOUBLE       NULL,
    campaign_lifetime_budget            DOUBLE       NULL,
    model                               VARCHAR(64)  NULL,
    attribution_window                  VARCHAR(32)  NULL,
    integration_id                      VARCHAR(128) NULL,
    original_provider_id                VARCHAR(64)  NULL,
    provider_id                         VARCHAR(64)  NULL,
    shop_id                             VARCHAR(128) NULL,
    shop_name                           VARCHAR(64)  NULL,
    -- 投放指标
    impressions                         DOUBLE       NULL,
    clicks                              DOUBLE       NULL,
    outbound_clicks                     DOUBLE       NULL,
    spend                               DOUBLE       NULL,
    non_tracked_spend                   DOUBLE       NULL,
    -- 转化指标
    orders_quantity                     DOUBLE       NULL,
    click_orders                        DOUBLE       NULL,
    view_orders                         DOUBLE       NULL,
    order_revenue                       DOUBLE       NULL,
    click_revenue                       DOUBLE       NULL,
    view_revenue                        DOUBLE       NULL,
    gross_sales                         DOUBLE       NULL,
    gross_product_sales                 DOUBLE       NULL,
    product_quantity_sold_in_order      DOUBLE       NULL,
    refund_money                        DOUBLE       NULL,
    new_customer_orders                 DOUBLE       NULL,
    new_customer_order_revenue          DOUBLE       NULL,
    new_customer_gross_sales            DOUBLE       NULL,
    new_customer_cogs                   DOUBLE       NULL,
    -- 自定义指标
    custom_gross_profit                 DOUBLE       NULL,
    custom_gross_sales                  DOUBLE       NULL,
    custom_net_revenue                  DOUBLE       NULL,
    custom_combined_gross_profit        DOUBLE       NULL,
    custom_combined_gross_sales         DOUBLE       NULL,
    custom_combined_net_revenue         DOUBLE       NULL,
    custom_expenses                     DOUBLE       NULL,
    custom_orders_quantity              DOUBLE       NULL,
    custom_total_items_quantity         DOUBLE       NULL,
    cogs                                DOUBLE       NULL,
    cost_of_goods                       DOUBLE       NULL,
    -- 视频指标
    total_video_view                    DOUBLE       NULL,
    video_p25_watched                   DOUBLE       NULL,
    video_p50_watched                   DOUBLE       NULL,
    video_p75_watched                   DOUBLE       NULL,
    video_p100_watched                  DOUBLE       NULL,
    -- Meta / 电商指标
    meta_conversion_value               DOUBLE       NULL,
    meta_facebook_orders                DOUBLE       NULL,
    non_meta_facebook_orders            DOUBLE       NULL,
    one_day_view_conversion_value       DOUBLE       NULL,
    one_day_view_purchases              DOUBLE       NULL,
    seven_day_view_conversion_value     DOUBLE       NULL,
    seven_day_view_purchases            DOUBLE       NULL,
    website_purchases                   DOUBLE       NULL,
    channel_reported_all_conversions    DOUBLE       NULL,
    channel_reported_conversion_value   DOUBLE       NULL,
    channel_reported_conversions        DOUBLE       NULL,
    channel_reported_onsite_conversion_value DOUBLE  NULL,
    channel_reported_onsite_purchases   DOUBLE       NULL,
    channel_reported_visits             DOUBLE       NULL,
    subscription_quantity               DOUBLE       NULL,
    subscriptions_arr                   DOUBLE       NULL,
    i_revenue                           DOUBLE       NULL,
    i_roas                              DOUBLE       NULL,
    -- 实验相关字段（null-type）
    experiment_CPIC                     VARCHAR(255) NULL,
    experiment_CPIC_lower               VARCHAR(255) NULL,
    experiment_CPIC_upper               VARCHAR(255) NULL,
    experiment_conversions_incremental  VARCHAR(255) NULL,
    experiment_conversions_incremental_lower VARCHAR(255) NULL,
    experiment_conversions_incremental_share_percent VARCHAR(255) NULL,
    experiment_conversions_incremental_upper VARCHAR(255) NULL,
    experiment_event_date               VARCHAR(255) NULL,
    experiment_i_ROAS                   VARCHAR(255) NULL,
    experiment_i_ROAS_lower_bound       VARCHAR(255) NULL,
    experiment_i_ROAS_upper_bound       VARCHAR(255) NULL,
    experiment_incremental_conversions_confidence_percent VARCHAR(255) NULL,
    experiment_incremental_revenue_confidence_percent VARCHAR(255) NULL,
    experiment_revenue_incremental_share_percent VARCHAR(255) NULL,
    incremental_revenue_experiment      VARCHAR(255) NULL,
    incremental_revenue_lower_bound_experiment VARCHAR(255) NULL,
    incremental_revenue_upper_bound_experiment VARCHAR(255) NULL,
    -- 其他维度
    channel_type                        VARCHAR(64)  NULL,
    creative_id                         VARCHAR(64)  NULL,
    creative_cta_type                   VARCHAR(64)  NULL,
    creative_format                     VARCHAR(64)  NULL,
    creative_distribution_format        VARCHAR(64)  NULL,
    is_utm_valid                        TINYINT      NULL,
    suggested_budget                    DOUBLE       NULL,
    url_template                        TEXT         NULL,
    video_url                           TEXT         NULL,
    video_url_iframe                    TEXT         NULL,
    video_url_source                    TEXT         NULL,
    video_duration                      DOUBLE       NULL,
    number_of_image_assets              DOUBLE       NULL,
    number_of_video_assets              DOUBLE       NULL,
    -- 数组字段（JSON 序列化）
    ad_copies                           TEXT         NULL COMMENT 'JSON array',
    ad_titles                           TEXT         NULL COMMENT 'JSON array',
    ad_ai_recommendation                TEXT         NULL COMMENT 'JSON array',
    ad_ai_roas_pacing                   TEXT         NULL COMMENT 'JSON array',
    adset_ai_recommendation             TEXT         NULL COMMENT 'JSON array',
    adset_ai_roas_pacing                TEXT         NULL COMMENT 'JSON array',
    campaign_ai_recommendation          TEXT         NULL COMMENT 'JSON array',
    campaign_ai_roas_pacing             TEXT         NULL COMMENT 'JSON array',
    channel_ai_recommendation           TEXT         NULL COMMENT 'JSON array',
    channel_ai_roas_pacing              TEXT         NULL COMMENT 'JSON array',
    discount_codes                      TEXT         NULL COMMENT 'JSON array',
    links                               TEXT         NULL COMMENT 'JSON array'
)
UNIQUE KEY(event_date, channel, account_id, campaign_id, adset_id, ad_id)
DISTRIBUTED BY HASH(event_date) BUCKETS 4
PROPERTIES ("replication_num" = "1");
```

#### ods_tw_pixel_keywords_joined

> 完整字段参见 `reports/triplewhale-raw.md` → `pixel_keywords_joined_tvf` 章节（约 80 列）。

```sql
CREATE TABLE IF NOT EXISTS hqware.ods_tw_pixel_keywords_joined (
    event_date                          DATE         NOT NULL,
    channel                             VARCHAR(128) NOT NULL,
    keyword_id                          VARCHAR(128) NOT NULL,
    -- 关键词维度
    keyword_text                        VARCHAR(255) NULL,
    keyword_match_type                  VARCHAR(32)  NULL,
    keyword_status                      VARCHAR(32)  NULL,
    keyword_system_serving_status       VARCHAR(64)  NULL,
    keyword_effective_cpc_bid           DOUBLE       NULL,
    keyword_cpc_bid                     DOUBLE       NULL,
    keyword_quality_score               DOUBLE       NULL,
    -- 广告层级维度
    account_id                          VARCHAR(64)  NULL,
    campaign_id                         VARCHAR(128) NULL,
    campaign_name                       VARCHAR(255) NULL,
    campaign_status                     VARCHAR(32)  NULL,
    campaign_bid_strategy               VARCHAR(64)  NULL,
    adset_id                            VARCHAR(128) NULL,
    adset_name                          VARCHAR(255) NULL,
    adset_status                        VARCHAR(32)  NULL,
    adset_bid_amount                    DOUBLE       NULL,
    adset_bid_strategy                  VARCHAR(64)  NULL,
    integration_id                      VARCHAR(128) NULL,
    original_provider_id                VARCHAR(64)  NULL,
    provider_id                         VARCHAR(64)  NULL,
    model                               VARCHAR(64)  NULL,
    attribution_window                  VARCHAR(32)  NULL,
    -- 投放指标
    impressions                         DOUBLE       NULL,
    clicks                              DOUBLE       NULL,
    spend                               DOUBLE       NULL,
    -- 转化指标
    orders_quantity                     DOUBLE       NULL,
    click_orders                        DOUBLE       NULL,
    view_orders                         DOUBLE       NULL,
    order_revenue                       DOUBLE       NULL,
    click_revenue                       DOUBLE       NULL,
    view_revenue                        DOUBLE       NULL,
    gross_sales                         DOUBLE       NULL,
    gross_product_sales                 DOUBLE       NULL,
    product_quantity_sold_in_order      DOUBLE       NULL,
    refund_money                        DOUBLE       NULL,
    new_customer_orders                 DOUBLE       NULL,
    new_customer_order_revenue          DOUBLE       NULL,
    new_customer_gross_sales            DOUBLE       NULL,
    new_customer_cogs                   DOUBLE       NULL,
    -- 自定义指标
    custom_gross_profit                 DOUBLE       NULL,
    custom_gross_sales                  DOUBLE       NULL,
    custom_net_revenue                  DOUBLE       NULL,
    custom_combined_gross_profit        DOUBLE       NULL,
    custom_combined_gross_sales         DOUBLE       NULL,
    custom_combined_net_revenue         DOUBLE       NULL,
    custom_expenses                     DOUBLE       NULL,
    custom_orders_quantity              DOUBLE       NULL,
    custom_total_items_quantity         DOUBLE       NULL,
    cogs                                DOUBLE       NULL,
    cost_of_goods                       DOUBLE       NULL,
    -- Meta 指标
    one_day_view_conversion_value       DOUBLE       NULL,
    one_day_view_purchases              DOUBLE       NULL,
    seven_day_view_conversion_value     DOUBLE       NULL,
    seven_day_view_purchases            DOUBLE       NULL,
    website_purchases                   DOUBLE       NULL,
    channel_reported_all_conversions    DOUBLE       NULL,
    channel_reported_conversion_value   DOUBLE       NULL,
    subscription_quantity               DOUBLE       NULL,
    subscriptions_arr                   DOUBLE       NULL,
    -- 实验字段
    experiment_CPIC                     VARCHAR(255) NULL,
    experiment_event_date               VARCHAR(255) NULL,
    experiment_i_ROAS                   VARCHAR(255) NULL,
    experiment_i_ROAS_lower_bound       VARCHAR(255) NULL,
    experiment_i_ROAS_upper_bound       VARCHAR(255) NULL,
    -- 数组字段
    discount_codes                      TEXT         NULL COMMENT 'JSON array',
    links                               TEXT         NULL COMMENT 'JSON array',
    -- shop 信息
    shop_id                             VARCHAR(128) NULL,
    shop_name                           VARCHAR(64)  NULL
)
UNIQUE KEY(event_date, channel, keyword_id)
DISTRIBUTED BY HASH(event_date) BUCKETS 4
PROPERTIES ("replication_num" = "1");
```

#### ods_tw_ads

> 完整字段参见 `reports/triplewhale-raw.md` → `ads_table` 章节（约 110 列）。

```sql
CREATE TABLE IF NOT EXISTS hqware.ods_tw_ads (
    event_date                          DATE         NOT NULL,
    channel                             VARCHAR(128) NOT NULL,
    account_id                          VARCHAR(64)  NOT NULL,
    campaign_id                         VARCHAR(128) NOT NULL,
    adset_id                            VARCHAR(128) NOT NULL,
    ad_id                               VARCHAR(128) NOT NULL,
    -- 广告层级维度
    ad_name                             VARCHAR(255) NULL,
    ad_status                           VARCHAR(32)  NULL,
    ad_type                             VARCHAR(32)  NULL,
    ad_image_url                        TEXT         NULL,
    ad_title                            VARCHAR(255) NULL,
    ad_copy                             VARCHAR(255) NULL,
    ad_post_id                          VARCHAR(64)  NULL,
    ad_bid_amount                       DOUBLE       NULL,
    adset_name                          VARCHAR(255) NULL,
    adset_status                        VARCHAR(32)  NULL,
    adset_bid_amount                    DOUBLE       NULL,
    adset_bid_strategy                  VARCHAR(64)  NULL,
    adset_daily_budget                  DOUBLE       NULL,
    adset_lifetime_budget               DOUBLE       NULL,
    adset_target_cpa                    DOUBLE       NULL,
    adset_target_roas                   DOUBLE       NULL,
    adset_targeting                     TEXT         NULL,
    campaign_name                       VARCHAR(255) NULL,
    campaign_status                     VARCHAR(32)  NULL,
    campaign_type                       VARCHAR(64)  NULL,
    campaign_sub_type                   VARCHAR(64)  NULL,
    campaign_bid_strategy               VARCHAR(64)  NULL,
    campaign_daily_budget               DOUBLE       NULL,
    campaign_lifetime_budget            DOUBLE       NULL,
    campaign_target_cpa                 DOUBLE       NULL,
    campaign_target_roas                DOUBLE       NULL,
    campaign_created_at                 VARCHAR(255) NULL,
    model                               VARCHAR(64)  NULL,
    attribution_window                  VARCHAR(32)  NULL,
    integration_id                      VARCHAR(128) NULL,
    is_utm_valid                        TINYINT      NULL,
    currency                            VARCHAR(8)   NULL,
    currency_rate                       DOUBLE       NULL,
    event_hour                          INT          NULL,
    destination_url                     TEXT         NULL,
    url_template                        TEXT         NULL,
    video_url                           TEXT         NULL,
    video_url_iframe                    TEXT         NULL,
    video_url_source                    TEXT         NULL,
    video_duration                      DOUBLE       NULL,
    asset_id                            VARCHAR(128) NULL,
    asset_type                          VARCHAR(64)  NULL,
    creative_id                         VARCHAR(128) NULL,
    creative_cta_type                   VARCHAR(64)  NULL,
    creative_format                     VARCHAR(64)  NULL,
    creative_distribution_format        VARCHAR(64)  NULL,
    -- 投放指标
    impressions                         DOUBLE       NULL,
    clicks                              DOUBLE       NULL,
    outbound_clicks                     DOUBLE       NULL,
    spend                               DOUBLE       NULL,
    non_tracked_spend                   DOUBLE       NULL,
    engagements                         DOUBLE       NULL,
    follows                             DOUBLE       NULL,
    weight                              DOUBLE       NULL,
    three_second_video_view             DOUBLE       NULL,
    video_p25_watched                   DOUBLE       NULL,
    video_p50_watched                   DOUBLE       NULL,
    video_p75_watched                   DOUBLE       NULL,
    video_p95_watched                   DOUBLE       NULL,
    video_p100_watched                  DOUBLE       NULL,
    -- 转化指标
    conversions                         DOUBLE       NULL,
    all_conversions                     DOUBLE       NULL,
    conversion_value                    DOUBLE       NULL,
    all_conversion_value                DOUBLE       NULL,
    -- Meta 点击类指标
    one_day_click_conversion_value      DOUBLE       NULL,
    one_day_click_purchases             DOUBLE       NULL,
    one_day_click_comments              DOUBLE       NULL,
    one_day_click_likes                 DOUBLE       NULL,
    one_day_click_link_clicks           DOUBLE       NULL,
    one_day_click_reactions             DOUBLE       NULL,
    one_day_click_shares                DOUBLE       NULL,
    seven_day_click_conversion_value    DOUBLE       NULL,
    seven_day_click_purchases           DOUBLE       NULL,
    seven_day_click_comments            DOUBLE       NULL,
    seven_day_click_likes               DOUBLE       NULL,
    seven_day_click_link_clicks         DOUBLE       NULL,
    seven_day_click_reactions           DOUBLE       NULL,
    seven_day_click_shares              DOUBLE       NULL,
    twenty_eight_day_click_conversion_value DOUBLE   NULL,
    twenty_eight_day_click_purchases    DOUBLE       NULL,
    twenty_eight_day_click_link_clicks  DOUBLE       NULL,
    twenty_eight_day_view_conversion_value DOUBLE    NULL,
    twenty_eight_day_view_purchases     DOUBLE       NULL,
    one_day_view_conversion_value       DOUBLE       NULL,
    one_day_view_purchases              DOUBLE       NULL,
    seven_day_view_conversion_value     DOUBLE       NULL,
    seven_day_view_purchases            DOUBLE       NULL,
    meta_conversion_value               DOUBLE       NULL,
    meta_purchases                      DOUBLE       NULL,
    website_purchases                   DOUBLE       NULL,
    onsite_purchases                    DOUBLE       NULL,
    onsite_conversion_value             DOUBLE       NULL,
    onsite_one_day_click_conversion_value DOUBLE     NULL,
    onsite_one_day_click_purchases      DOUBLE       NULL,
    onsite_one_day_view_conversion_value DOUBLE      NULL,
    onsite_one_day_view_purchases       DOUBLE       NULL,
    onsite_seven_day_click_conversion_value DOUBLE   NULL,
    onsite_seven_day_click_purchases    DOUBLE       NULL,
    onsite_seven_day_view_conversion_value DOUBLE    NULL,
    onsite_seven_day_view_purchases     DOUBLE       NULL,
    onsite_twenty_eight_day_click_conversion_value DOUBLE NULL,
    onsite_twenty_eight_day_click_purchases DOUBLE   NULL,
    onsite_twenty_eight_day_view_conversion_value DOUBLE NULL,
    onsite_twenty_eight_day_view_purchases DOUBLE    NULL,
    -- Google 搜索指标
    search_impression_share             DOUBLE       NULL,
    search_impressions                  DOUBLE       NULL,
    search_absolute_top_impression_share DOUBLE      NULL,
    search_absolute_top_impressions     DOUBLE       NULL,
    search_top_impression_share         DOUBLE       NULL,
    search_top_impressions              DOUBLE       NULL,
    search_budget_lost_absolute_top_impression_share DOUBLE NULL,
    search_budget_lost_absolute_top_impressions DOUBLE NULL,
    search_budget_lost_top_impression_share DOUBLE   NULL,
    search_budget_lost_top_impressions  DOUBLE       NULL,
    search_rank_lost_impression_share   DOUBLE       NULL,
    search_rank_lost_impressions        DOUBLE       NULL,
    search_rank_lost_top_impression_share DOUBLE     NULL,
    search_rank_lost_top_impressions    DOUBLE       NULL,
    total_complete_payment_rate         DOUBLE       NULL,
    total_on_web_order_value            DOUBLE       NULL,
    visits                              DOUBLE       NULL,
    -- 数组字段
    actions                             TEXT         NULL COMMENT 'JSON array',
    ad_copies                           TEXT         NULL COMMENT 'JSON array',
    ad_titles                           TEXT         NULL COMMENT 'JSON array',
    ad_ai_recommendation                TEXT         NULL COMMENT 'JSON array',
    ad_ai_roas_pacing                   TEXT         NULL COMMENT 'JSON array',
    adset_ai_recommendation             TEXT         NULL COMMENT 'JSON array',
    adset_ai_roas_pacing                TEXT         NULL COMMENT 'JSON array',
    campaign_ai_recommendation          TEXT         NULL COMMENT 'JSON array',
    campaign_ai_roas_pacing             TEXT         NULL COMMENT 'JSON array',
    channel_ai_recommendation           TEXT         NULL COMMENT 'JSON array',
    channel_ai_roas_pacing              TEXT         NULL COMMENT 'JSON array',
    shop_id                             VARCHAR(128) NULL,
    shop_name                           VARCHAR(64)  NULL
)
UNIQUE KEY(event_date, channel, account_id, campaign_id, adset_id, ad_id)
DISTRIBUTED BY HASH(event_date) BUCKETS 4
PROPERTIES ("replication_num" = "1");
```

#### ods_tw_creatives

```sql
CREATE TABLE IF NOT EXISTS hqware.ods_tw_creatives (
    event_date                          DATE         NOT NULL,
    channel                             VARCHAR(128) NOT NULL,
    ad_id                               VARCHAR(128) NOT NULL,
    asset_id                            VARCHAR(128) NOT NULL,
    -- 创意维度
    creative_id                         VARCHAR(128) NULL,
    asset_type                          VARCHAR(64)  NULL,
    ad_type                             VARCHAR(64)  NULL,
    ad_title                            VARCHAR(255) NULL,
    ad_copy                             VARCHAR(255) NULL,
    ad_image_url                        TEXT         NULL,
    video_url                           TEXT         NULL,
    video_url_iframe                    TEXT         NULL,
    video_url_source                    TEXT         NULL,
    video_duration                      DOUBLE       NULL,
    destination_url                     TEXT         NULL,
    url_template                        TEXT         NULL,
    creative_cta_type                   VARCHAR(64)  NULL,
    creative_format                     VARCHAR(64)  NULL,
    creative_distribution_format        VARCHAR(64)  NULL,
    account_id                          VARCHAR(64)  NULL,
    campaign_id                         VARCHAR(128) NULL,
    campaign_name                       VARCHAR(255) NULL,
    adset_id                            VARCHAR(128) NULL,
    adset_name                          VARCHAR(255) NULL,
    model                               VARCHAR(64)  NULL,
    attribution_window                  VARCHAR(32)  NULL,
    number_of_ads                       DOUBLE       NULL,
    shop_id                             VARCHAR(128) NULL,
    shop_name                           VARCHAR(64)  NULL,
    -- 投放指标
    impressions                         DOUBLE       NULL,
    clicks                              DOUBLE       NULL,
    outbound_clicks                     DOUBLE       NULL,
    spend                               DOUBLE       NULL,
    non_tracked_spend                   DOUBLE       NULL,
    three_second_video_view             DOUBLE       NULL,
    thruplays                           DOUBLE       NULL,
    total_video_view                    DOUBLE       NULL,
    video_p25_watched                   DOUBLE       NULL,
    video_p50_watched                   DOUBLE       NULL,
    video_p75_watched                   DOUBLE       NULL,
    video_p95_watched                   DOUBLE       NULL,
    video_p100_watched                  DOUBLE       NULL,
    -- 转化指标
    orders_quantity                     DOUBLE       NULL,
    order_revenue                       DOUBLE       NULL,
    gross_product_sales                 DOUBLE       NULL,
    new_customer_orders                 DOUBLE       NULL,
    new_customer_order_revenue          DOUBLE       NULL,
    new_customer_cogs                   DOUBLE       NULL,
    non_meta_facebook_orders            DOUBLE       NULL,
    meta_conversion_value               DOUBLE       NULL,
    meta_facebook_orders                DOUBLE       NULL,
    website_purchases                   DOUBLE       NULL,
    one_day_view_conversion_value       DOUBLE       NULL,
    one_day_view_purchases              DOUBLE       NULL,
    seven_day_view_conversion_value     DOUBLE       NULL,
    seven_day_view_purchases            DOUBLE       NULL,
    channel_reported_conversion_value   DOUBLE       NULL,
    channel_reported_conversions        DOUBLE       NULL,
    channel_reported_onsite_conversion_value DOUBLE  NULL,
    channel_reported_onsite_purchases   DOUBLE       NULL,
    channel_reported_visits             DOUBLE       NULL,
    -- 数组字段
    ad_copies                           TEXT         NULL COMMENT 'JSON array',
    ad_titles                           TEXT         NULL COMMENT 'JSON array'
)
UNIQUE KEY(event_date, channel, ad_id, asset_id)
DISTRIBUTED BY HASH(event_date) BUCKETS 4
PROPERTIES ("replication_num" = "1");
```

#### ods_tw_ai_visibility

> ai_visibility_table 当前无历史数据（来自 triplewhale-raw.md），仅建最小表结构。
> 后续可根据实际数据扩展字段。

```sql
CREATE TABLE IF NOT EXISTS hqware.ods_tw_ai_visibility (
    event_date  DATE         NOT NULL COMMENT '事件日期（暂定唯一键）',
    data        TEXT         NULL COMMENT '原始数据 JSON，待字段确认后展开'
)
UNIQUE KEY(event_date)
DISTRIBUTED BY HASH(event_date) BUCKETS 4
PROPERTIES ("replication_num" = "1");
```

> **注意**：ai_visibility_table 的 `_transform` 函数在无数据时应直接返回空列表，
> 不做任何写入。当 API 返回实际数据时，再补充完整字段。

---

### 测试要求（tests/test_tw_collector.py）

测试文件位于主仓库 `tests/` 目录（非 `bi/` 子模块内）。
路径设置模式参考 `tests/test_watermark.py`：

```python
_OUTDOOR_COLLECTOR_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "bi", "python_sdk", "outdoor_collector"
)
sys.path.insert(0, _OUTDOOR_COLLECTOR_ROOT)
```

**必须覆盖的测试用例：**

1. `test_serialize_row_arrays` — 验证 list/dict 字段被正确 json.dumps
2. `test_serialize_row_booleans` — 验证 True/False → 1/0
3. `test_transform_sessions_table` — 验证 sessions_table transform 函数
4. `test_transform_pixel_orders` — 验证含数组字段的 pixel_orders_table transform
5. `test_collect_table_incremental` — mock pymysql.connect + requests.post，
   验证增量模式：使用水位线时间作为 period_start
6. `test_collect_table_full_no_watermark` — 无水位线时触发全量（period_start =
   TABLE_EARLIEST_DATES[table]）
7. `test_collect_all_single_failure` — 一张表失败不影响其他表，返回 dict 中失败表
   值为 -1
8. `test_missing_api_key` — TRIPLEWHALE_API_KEY 未设置时抛 RuntimeError

---

### bi/ 子模块提交说明

1. 在 worktree 内的 `bi/` 目录提交 tw_collector.py：
   ```bash
   cd <worktree>/bi
   git add python_sdk/outdoor_collector/collectors/tw_collector.py
   git commit -m "feat(story-7.1): TripleWhale 数据采集落库"
   ```
2. 回到 worktree 根目录，更新 bi/ 子模块引用并提交测试文件：
   ```bash
   cd <worktree>
   git add bi tests/test_tw_collector.py
   git commit -m "feat(story-7.1): TripleWhale 采集落库 + 单元测试"
   ```

---

## Dev Agent Record

### 实现变更记录

- 新增 `bi/python_sdk/outdoor_collector/collectors/tw_collector.py`：完整实现10张表采集落库
- 新增 `tests/test_tw_collector.py`：18条单元测试全部通过

### 代码审查 Findings（2026-04-16）

- [x] [Review][Patch] 移除未使用的 `reset_watermark` import [tw_collector.py:36] — 已修复
- [x] [Review][Patch] datetime 列过滤用 `DATE()` 转换防止当天数据截断 [tw_collector.py:collect_table] — 已修复（`DATE({date_col})` 包装）
- [x] [Review][Patch] 测试 env var 泄漏改用 `monkeypatch.setenv` [test_tw_collector.py:多处] — 已修复
- [x] [Review][Defer] sessions_table 全量拉取约900次API调用无限速控制 [tw_collector.py:_collect_sessions_by_day] — deferred，Story 6.3 chunked_fetch 完成后迁移

### 调试笔记

- bi/ 子模块在新 worktree 中需手动 cp 初始化（git clone 网络不通）
- sessions_table 10M 行，全量按天约900次调用，增量场景无问题

### 经验总结

- TripleWhale 的 `created_at` 字段是 DATETIME，SQL 过滤必须用 `DATE()` 转换
- ai_visibility_table 目前无历史数据，表结构极简，待有数据时扩展字段

---

## CC#4 变更记录（2026-04-17）

**变更来源：** Sprint Change Proposal CC#4 — ODS 全字段补全 + 速率限制 + EARLIEST_DATE 统一

### 变更内容

1. **ODS 表字段补全（ARCH14）**
   - 所有 10 张 TripleWhale 表字段从 3~8 个补全至实际接口返回的完整字段数（30~143 个）
   - 嵌套 list/dict 字段序列化为 JSON TEXT 存储
   - 英文字段直接使用原名，每表统一追加 `etl_time DATETIME`
   - 权威 DDL 定义已迁移至 `init_doris_tables.py`（`hqware_test` 数据库）

2. **全量起始时间统一（ARCH16）**
   - `TABLE_EARLIEST_DATES` 所有表统一改为 `"2026-03-01"`
   - 测试完成后统一修改此常量以拉取更早历史数据

3. **速率限制（ARCH15）**
   - `_collect_sessions_by_day` 按天循环加 `time.sleep(0.2)`，防止 API 封禁
