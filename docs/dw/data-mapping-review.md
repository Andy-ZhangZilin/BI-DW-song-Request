# 数据源与字段映射确认文档

**更新时间：** 2026-04-27
**版本：** v2.0（按 Doris 真实表名 + 最新报表需求全面更新）

---

## Part 1：数据源采集状态汇总

> 表名已统一更新为 Doris 中的真实 ODS 表名。

| 分类 | 来源系统 | Doris ODS 表名 | 行数（近似） | 状态 | 备注 |
|-----|---------|--------------|------------|------|------|
| TripleWhale | triplewhale | `ods_tw_pixel_orders` | — | ✅ 已接入 | 含 `shop_name`、`discount_code`、`is_new_customer`、`order_revenue`、`products_info`(JSON) |
| TripleWhale | triplewhale | `ods_tw_pixel_joined` | 7,246 | ✅ 已接入 | `model` 值仅 `'Triple Attribution'`（无 Linear All）；含广告归因全字段 |
| TripleWhale | triplewhale | `ods_tw_sessions` | 345,265 | ✅ 已接入 | sessions 数据独立表，非 pixel_joined 字段 |
| TripleWhale | triplewhale | `ods_tw_product_analytics` | — | ✅ 已接入 | 含 `added_to_cart_events`（shop×date 粒度），无广告组维度 |
| TripleWhale | triplewhale | `ods_tw_pixel_keywords_joined` | — | ✅ 已接入 | 关键词归因 |
| TripleWhale | triplewhale | `ods_tw_ads` | — | ✅ 已接入 | 广告素材表 |
| TripleWhale | triplewhale | `ods_tw_social_media_comments` | — | ✅ 已接入 | 社媒评论 |
| TripleWhale | triplewhale | `ods_tw_social_media_pages` | — | ✅ 已接入 | 社媒主页数据（含 Facebook） |
| TripleWhale | triplewhale | `ods_tw_creatives` | — | ✅ 已接入 | 广告素材创意 |
| TikTok-API | tiktok | `ods_tiktok_shop_product_performance` | 4,876 | ✅ 已接入 | 字段扁平化；含 `sales_breakdowns`/`traffic_breakdowns`（JSON） |
| TikTok-API | tiktok | `ods_tiktok_video_performances` | 47,499 | ✅ 已接入 | 字段扁平化（无嵌套 videos[]）；`products` 为 JSON 数组；`video_post_time` 部分为 NULL |
| TikTok-API | tiktok | `ods_tiktok_shop_video_performance_detail` | 2,218 | ✅ 已接入 | 含 `traffic_likes`/`traffic_comments`/`traffic_shares` |
| TikTok-API | tiktok | `ods_tiktok_return_refund` | — | ✅ 已接入 | 含 `seller_sku`，但仅覆盖退款订单 |
| TikTok-API | tiktok | TikTok联盟订单（Creator order） | — | ❌ **未接入** | 影响报表A的7个字段；需业务推进接入（待建表 `ods_tiktok_affiliate_order`） |
| TikTok-API | tiktok | `ods_tiktok_ad_spend` | — | ❌ 采集失败 | TikTok 信息流广告花费接口失败 |
| 钉钉 | dingtalk | `ods_dingtalk_kol_tidwe_kol_info` | — | ✅ 已接入 | 红人信息汇总（含 `kol_id`、`username`、粉丝数等） |
| 钉钉 | dingtalk | `ods_dingtalk_kol_tidwe_sample` | 305–317 | ✅ 已接入 | 寄样记录；`tracking_number` 格式与 `platform_order_no` 不匹配（样品费 JOIN 受阻） |
| 钉钉 | dingtalk | `ods_dingtalk_kol_tidwe_content` | 819 | ✅ 已接入 | 内容上线记录；含 `record_id`（可直接 JOIN YouTube）、`promo_code`、`content_url` |
| 钉钉 | dingtalk | `ods_dingtalk_outdoor_material_analysis` | 4,847（892有效） | ✅ 已接入 | KOL 合作费支付表；`round_actual_amount` 含 '$' 需清洗 |
| 合思费控 | finance | `ods_finance_ekuaibao_apply` | 139 | ✅ 已接入 | 费用申请表头；含 `title`（标题）、`pay_date`、`submit_date`、`code` |
| 合思费控 | finance | `ods_finance_ekuaibao_apply_item` | 292 | ✅ 已接入 | 费用明细；含 `consumption_reasons`（消费事由）、`fee_type_name`、`amount`；JOIN key: `code` |
| 财务BI | finance | `ods_finance_bi_report_middle_multi_order` | 12,992,010 | ✅ 已接入 | 多平台订单汇总；`is_deleted` 需过滤 |
| YouTube | youtube_url | `ods_youtube_video_stats` | — | ✅ 已接入 | 含 `dingtalk_record_id`（可直接 JOIN 内容表）、`view_count`、`like_count`、`comment_count` |
| 联盟 | awin | `ods_awin_transactions` | 53 | ✅ 已接入 | 含 `total_commission`；日期字段 `collect_date` |
| 联盟 | partnerboost | `ods_partnerboost_performance` | 663 | ✅ 已接入 | 含 `commission`；日期字段 `collect_date` |
| EDM | cartsee | `ods_cartsee` | — | ⚠️ 未入库 | EDM 数据路径暂不可用 |
| 社媒后台 | facebook | — | — | ❌ 认证失败 | authenticate() 返回 False |
| 社媒后台 | youtube_studio | — | — | ❌ 认证失败 | authenticate() 返回 False |
| 维度表 | — | `dim_shop` | — | ✅ 已接入 | 含 `shop_id`、`shop_name`，用于 pixel_joined 中 shop 关联 |

---

## Part 3：报表字段映射分析

---

### 报表 1：利润表

- **所属报表：** 销售表现、利润表
- **需求时间：** 2026-04-08 | **上线时间：** 2026-04-24

| 报表字段 | Doris 表名 | 来源字段 | 映射状态 | 备注 |
|---------|-----------|---------|---------|------|
| 日期 | `ods_finance_bi_report_middle_multi_order` | `统计时间` | 可映射 | 备选：`订购时间`/`付款时间`/`发货时间`，按业务口径选择 |
| 渠道 | `ods_finance_bi_report_middle_multi_order` | `渠道名称` | 可映射 | 示例：Amazon-SC（DE）；粗粒度可用 `平台名称` |
| 店铺 | `ods_finance_bi_report_middle_multi_order` | `店铺名` | 可映射 | |
| 国家 | `ods_finance_bi_report_middle_multi_order` | `商城所在国家名称` | 可映射 | 二字码备选：`发货国家二字码` |
| ASIN/sku_id | `ods_finance_bi_report_middle_multi_order` | `ASIN/商品ID` | 可映射 | |
| MSKU | `ods_finance_bi_report_middle_multi_order` | `MSKU` | 可映射 | |
| SKU | `ods_finance_bi_report_middle_multi_order` | `SKU` | 可映射 | SPU 备选：`spu` |
| 科目 | `ods_finance_bi_report_middle_multi_order` | `报表项目` | 可映射 | 即财务科目四级项目；`报表项目id` 可作关联主键 |
| 数值 | `ods_finance_bi_report_middle_multi_order` | `金额` | 可映射 | 原币种；人民币：`金额(CNY)`；需过滤 `is_deleted = 0` |

---

### 报表 2：财务科目表

- **所属报表：** 销售表现、利润表
- **需求时间：** 2026-04-08 | **上线时间：** 2026-04-24
- **备注：** 科目主数据，变动少，需财务手动维护

| 报表字段 | Doris 表名 | 来源字段 | 映射状态 | 备注 |
|---------|-----------|---------|---------|------|
| 项ID | — | — | ❌ 缺失 | 需业务/财务自定义手动维护 |
| 科目名称 | — | — | ❌ 缺失 | 同上 |
| 科目级别 | — | — | ❌ 缺失 | 同上 |
| 一级科目 | — | — | ❌ 缺失 | 同上 |
| 二级科目 | — | — | ❌ 缺失 | 同上 |
| 三级科目 | — | — | ❌ 缺失 | 同上 |
| 四级科目 | — | — | ❌ 缺失 | 建议作为主键与报表1科目字段关联 |
| 说明/备注 | — | — | ❌ 缺失 | 整张表需财务以静态主数据方式提供 |

---

### 报表 3：营销表现表

- **所属报表：** 营销推广-渠道效果
- **需求时间：** 2026-04-20 | **上线时间：** 2026-05-18
- **备注：** 各渠道营销归因数据，含花费、曝光、流量、订单、新客；需按 TW 归因逻辑处理

| 报表字段 | Doris 表名 | 来源字段 | 映射状态 | 备注 |
|---------|-----------|---------|---------|------|
| 日期 | `ods_tw_pixel_joined` | `event_date` | 可映射 | 日维度；TikTok 商品部分用 `ods_tiktok_shop_product_performance.collect_date` |
| 店铺 | `dim_shop` | `shop_name` | 可映射 | `pixel_joined.shop_name` 为 NULL，通过 `dim_shop` JOIN 获取 |
| 推广渠道 | `ods_tw_pixel_joined` | `channel` | 可映射 | 示例：google-ads / facebook-ads；按归因 CASE WHEN 分类 |
| 推广渠道细分类 | `ods_tw_pixel_joined` | `channel` + `campaign_name` | 需转换 | 归因 CASE WHEN SQL：硬广/KOL/联盟/EDM/SEO/TikTok/社媒；详见 dw-report3 加工文档 |
| 曝光量 | 多数据源 | 见备注 | 需转换 | 硬广：`ods_tw_pixel_joined.impressions`；TikTok达人：`ods_tiktok_video_performances.views`；YouTube KOL：`ods_youtube_video_stats.view_count`；联盟 Awin：`ods_awin_transactions.impressions`；EDM/SEO/社媒：暂缺 |
| 流量 | 多数据源 | 见备注 | 需转换 | 硬广：`ods_tw_pixel_joined.clicks`；联盟 Awin：`ods_awin_transactions.clicks`；联盟 PB：`ods_partnerboost_performance.clicks`；TikTok商品：`traffic_breakdowns[*].traffic.page_views` |
| 订单量 | `ods_tw_pixel_joined` | `orders_quantity` | 可映射 | TikTok商品部分：`sales_breakdowns[*].sales.items_sold` 汇总 |
| 销量 | `ods_tw_pixel_joined` | `product_quantity_sold_in_order` | 可映射 | |
| 销售额 | `ods_tw_pixel_joined` | `order_revenue` | 可映射 | TikTok：`ods_tiktok_shop_product_performance` → `sales_breakdowns[*].sales.gmv.amount` |
| 花费 | 多数据源 | 见备注 | 需转换 | 硬广：`ods_tw_pixel_joined.spend`；KOL合作费：`ods_dingtalk_outdoor_material_analysis.round_actual_amount`（清洗$和,）；联盟佣金：`ods_awin_transactions.total_commission` / `ods_partnerboost_performance.commission`；SEO/EDM：`ods_finance_ekuaibao_apply` JOIN `ods_finance_ekuaibao_apply_item`（title/消费事由含关键词） |
| 新客数 | `ods_tw_pixel_joined` | `new_customer_orders` | 可映射 | 为新客订单数近似；TikTok 无新客字段 |

**SEO 费用过滤说明（v2.0 更正）：**
- 过滤条件：`a.title LIKE '%SEO%' OR i.consumption_reasons LIKE '%SEO%'`（`a`=表头，`i`=明细）
- 月份归属：从 `a.title` 提取"YY年M月"或"YYYY年M月"，fallback 用 `COALESCE(a.pay_date, a.submit_date)`
- 当前 Doris 中 SEO 费用为 0 条（数据未录入），逻辑已就绪

**关键过滤条件：**
```sql
WHERE model = 'Triple Attribution'                        -- ⚠️ 非 'Linear All'
  AND lowerUTF8(attribution_window) = 'lifetime'
```

---

### 报表 4：DTC广告投放数据

- **所属报表：** 营销推广-广告投放
- **需求时间：** 2026-05-10 | **上线时间：** 2026-06-03
- **备注：** 活动/广告组/广告含 id+名称；仅保留付费渠道行

| 报表字段 | Doris 表名 | 来源字段 | 映射状态 | 备注 |
|---------|-----------|---------|---------|------|
| 日期 | `ods_tw_pixel_joined` | `event_date` | 可映射 | |
| 店铺名称 | `dim_shop` | `shop_name` | 可映射 | JOIN `dim_shop` ON `shop_name`（`pixel_joined.shop_name` 为 NULL） |
| 推广渠道 | `ods_tw_pixel_joined` | `channel` + `campaign_name` CASE WHEN | 需转换 | 值：`广告（上层广告）` / `广告`（仅付费渠道行） |
| 推广渠道细分类 | `ods_tw_pixel_joined` | `channel` | 可映射 | 直取原始值（google-ads / facebook-ads / tiktok-ads 等） |
| 活动 | `ods_tw_pixel_joined` | `campaign_name` / `campaign_id` | 可映射 | 两字段均保留 |
| 广告组 | `ods_tw_pixel_joined` | `adset_name` / `adset_id` | 可映射 | 两字段均保留 |
| 广告 | `ods_tw_pixel_joined` | `ad_name` / `ad_id` | 可映射 | 脏数据处理：NULL/'(not set)'/空字符串统一置 NULL |
| 曝光量 | `ods_tw_pixel_joined` | `impressions` | 可映射 | SUM |
| 点击数 | `ods_tw_pixel_joined` | `clicks` | 可映射 | 广告总点击数；SUM |
| 流量 | `ods_tw_pixel_joined` | `outbound_clicks` | 可映射 | 站外链接点击数；Facebook 有值，Google 为 NULL；展示时用 `COALESCE(outbound_clicks, clicks)` |
| 加购数 | `ods_tw_product_analytics` | `added_to_cart_events` | 可映射（有限制） | **⚠️ 仅 shop×date 粒度**，无法细化到广告组/活动层级；同日同店所有广告行填同一值 |
| 订单量 | `ods_tw_pixel_joined` | `orders_quantity` | 可映射 | SUM |
| 销量 | `ods_tw_pixel_joined` | `product_quantity_sold_in_order` | 可映射 | SUM |
| 销售额 | `ods_tw_pixel_joined` | `order_revenue` | 可映射 | SUM（USD） |
| 花费 | `ods_tw_pixel_joined` | `spend` | 可映射 | SUM（USD） |
| 新客数 | `ods_tw_pixel_joined` | `new_customer_orders` | 可映射 | 新客订单数近似 |

**关键过滤条件：**
```sql
WHERE model = 'Triple Attribution'
  AND lowerUTF8(attribution_window) = 'lifetime'
  AND channel_category IN ('广告（上层广告）', '广告')   -- 仅付费渠道
```

---

### 报表 5：KOL信息表

- **所属报表：** 营销推广-KOL效果
- **需求时间：** 2026-05-15 | **上线时间：** 2026-06-12
- **备注：** 三张钉钉源表字段有不同，缺失字段忽略

| 报表字段 | Doris 表名 | 来源字段 | 映射状态 | 备注 |
|---------|-----------|---------|---------|------|
| 红人ID | `ods_dingtalk_kol_tidwe_kol_info` | `kol_id` | 可映射 | 以红人信息汇总为主 |
| 红人类型 | `ods_dingtalk_kol_tidwe_kol_info` | `红人类型` | 可映射 | |
| 合作平台 | `ods_dingtalk_outdoor_material_analysis` | `Channel` | 可映射 | 示例：YouTube；已结构化 |
| 跟进人 | `ods_dingtalk_kol_tidwe_kol_info` | `跟进人` | 可映射 | outdoor 表备选：`🤵对接人` |
| 主页链接 | `ods_dingtalk_kol_tidwe_kol_info` | `*主页链接` | 可映射 | outdoor 表按平台分列：`YTB主页链接`/`TK主页链接`/`FB/IG主页链接` |
| 所在州 | `ods_dingtalk_kol_tidwe_kol_info` | `*所在州` | 可映射 | outdoor 表仅有国家字段，粒度不足 |
| 粉丝数 | `ods_dingtalk_kol_tidwe_kol_info` | `*粉丝数（k）` | 可映射 | 单位 k；outdoor 表 `Followers` 为原始数值，单位不同需统一 |
| 均播 | `ods_dingtalk_kol_tidwe_kol_info` | `长视频均播（k）` | 可映射 | 单位 k |
| 红人等级 | `ods_dingtalk_kol_tidwe_kol_info` | `红人等级` | 可映射 | |
| 合作模式 | `ods_dingtalk_kol_tidwe_kol_info` | `*合作模式` | 可映射 | |
| 付费模式 | `ods_dingtalk_kol_tidwe_kol_info` | `*付费模式` | 可映射 | |
| 合作价格及交付项 | `ods_dingtalk_kol_tidwe_kol_info` | `*合作价格及交付项` | 可映射 | 非结构化文本 |
| 佣金率 | `ods_dingtalk_kol_tidwe_kol_info` | `*佣金率` | ⚠️ 待核查 | 示例值含 #REF! 错误 |
| 合作review | `ods_dingtalk_kol_tidwe_kol_info` | `合作review` | 可映射 | |
| 后续动作 | `ods_dingtalk_kol_tidwe_kol_info` | `后续动作` | 可映射 | |
| Code | `ods_dingtalk_kol_tidwe_kol_info` | `*Code` | 可映射 | 推广码；content 表备选：`promo_code` |
| UTM长链 | — | — | ❌ 缺失 | 所有钉钉子表均无此字段，建议新增列 |
| UTM短链 | — | — | ❌ 缺失 | 同上 |
| 原UTM | `ods_dingtalk_kol_tidwe_kol_info` | `原UTM` | 可映射 | |
| Email | `ods_dingtalk_kol_tidwe_kol_info` | `*Email` | 可映射 | |
| 其他联系方式 | `ods_dingtalk_kol_tidwe_kol_info` | `其他联系方式` | 可映射 | outdoor 表 `Whatsapp`/`Phone` 更结构化 |
| 备注 | `ods_dingtalk_kol_tidwe_kol_info` | `备注` | 可映射 | |
| 全名 | `ods_dingtalk_kol_tidwe_kol_info` | `*全名` | 可映射 | outdoor 表对应 `Real Name` |
| 寄样地址 | `ods_dingtalk_kol_tidwe_kol_info` | `*寄样地址` | 可映射 | |

---

### 报表 6：KOL内容表现表

- **所属报表：** 营销推广-KOL效果
- **需求时间：** 2026-05-15 | **上线时间：** 2026-06-12
- **最新需求字段（v2.0 精简）：** 内容发布id、内容发布url、日期、播放、点赞数、评论数（共 6 个）

| 报表字段 | Doris 表名 | 来源字段 | 映射状态 | 备注 |
|---------|-----------|---------|---------|------|
| 内容发布id | `ods_dingtalk_kol_tidwe_content` / `ods_youtube_video_stats` | TikTok: `REGEXP_EXTRACT(content_url,'/video/([0-9]+)',1)`；YouTube: `ods_youtube_video_stats.video_id` via `dingtalk_record_id=record_id` | 需转换 | TikTok 从 URL 正则提取视频 ID；YouTube 通过 `dingtalk_record_id` 直接 JOIN 获取 `video_id` |
| 内容发布url | `ods_dingtalk_kol_tidwe_content` | `content_url` | 可映射 | 819 条记录，Piscifun 覆盖不全 |
| 日期 | `ods_dingtalk_kol_tidwe_content` | `actual_publish_date` | 可映射 | 已为 DATE 类型，无需转换 |
| 播放 | `ods_tiktok_video_performances` / `ods_youtube_video_stats` / `ods_dingtalk_kol_tidwe_content` | `views` / `view_count` / `views` | 需转换 | 优先级：TikTok 平台接口 > YouTube 平台接口 > 钉钉手工维护值（VARCHAR→BIGINT） |
| 点赞数 | `ods_tiktok_shop_video_performance_detail` / `ods_youtube_video_stats` | `traffic_likes` / `like_count` | 可映射 | TikTok：按 `video_id` JOIN；YouTube：`like_count`；其他平台：NULL |
| 评论数 | `ods_tiktok_shop_video_performance_detail` / `ods_youtube_video_stats` | `traffic_comments` / `comment_count` | 可映射 | 同点赞数 |

**YouTube JOIN 方式（v2.0 更新）：**
- 直接 JOIN：`ods_youtube_video_stats.dingtalk_record_id = ods_dingtalk_kol_tidwe_content.record_id`
- 无需从 URL 解析视频 ID（已验证 JOIN 正常）

**DWS 层保留完整字段**（含 promo_code、gmv_amt、orders_cnt、new_customer_cnt 等），供其他报表复用；ADS 层仅输出以上 6 个字段。

---

### 报表 7：KOL/达人合作效果表（v3.0 拆分为两张表）

- **所属报表：** 营销推广-KOL效果
- **需求时间：** 2026-05-25 | **上线时间：** 2026-06-12

#### 表1 — KOL合作效果表（费用视角）

| 报表字段 | Doris 表名 | 来源字段 | 映射状态 | 备注 |
|---------|-----------|---------|---------|------|
| 日期 | `ods_dingtalk_outdoor_material_analysis` / `ods_dingtalk_kol_tidwe_sample` | `date` / `sample_date` | 可映射 | 均为 DATE 类型，直取 |
| 红人ID | `ods_dingtalk_outdoor_material_analysis` / `ods_dingtalk_kol_tidwe_sample` | `username` / `kol_id` | 可映射 | 合作费行用 `username` 作为 kol_id（待业务维护映射关系） |
| 寄样单号 | `ods_dingtalk_kol_tidwe_sample` | `tracking_number` | 可映射 | 仅样品费行有值；合作费行为 NULL |
| 寄样产品SKU | `ods_dingtalk_kol_tidwe_sample` | `product` | 可映射 | 仅样品费行有值 |
| 样品费 | `ods_finance_bi_report_middle_multi_order` | `amount` | ⚠️ 当前置 NULL | JOIN 路径受阻：`tracking_number`（内部格式）≠ `platform_order_no`（Amazon 格式），当前返回 0 行 |
| 合作费 | `ods_dingtalk_outdoor_material_analysis` | `round_actual_amount` | 可映射 | 清洗：`CAST(REPLACE(REPLACE(COALESCE(round_actual_amount,'0'),'$',''),',','') AS DECIMAL(16,2))`；样品费行为 NULL |

#### 表2 — KOL销售表（销售视角）

| 报表字段 | Doris 表名 | 来源字段 | 映射状态 | 备注 |
|---------|-----------|---------|---------|------|
| 日期 | `ods_tiktok_video_performances` / `ods_tw_pixel_orders` | `collect_date` / `event_date` | 可映射 | TikTok：`collect_date`（`video_post_time` 部分为 NULL）；其他：`ods_tw_pixel_orders.event_date` |
| 红人ID | `ods_dingtalk_kol_tidwe_content` | `kol_id` | 可映射 | 两路均经 `ods_dingtalk_kol_tidwe_content` 关联获取 |
| sku | — | — | ⚠️ 当前置 NULL | TikTok：需 `product_id → SKU` 映射表（待业务提供）；其他：`ods_tw_pixel_orders.products_info` JSON 可解析 SKU（待业务确认） |
| CODE | `ods_dingtalk_kol_tidwe_content` / `ods_tw_pixel_orders` | `promo_code` / `discount_code` | 可映射 | |
| 订单数 | `ods_tiktok_video_performances` / `ods_tw_pixel_orders` | `sku_orders` / `COUNT(*)` | 可映射 | TikTok：`sku_orders`（平台汇总值）；其他：折扣码归因 COUNT |
| 销量 | `ods_tiktok_video_performances` / `ods_tw_pixel_orders` | `items_sold` / `SUM(product_quantity_sold_in_order)` | 可映射 | |
| 销售额 | `ods_tiktok_video_performances` / `ods_tw_pixel_orders` | `gmv_amount` / `SUM(order_revenue)` | 可映射 | 均为 USD |

**路径说明：**
- TikTok路径：`ods_tiktok_video_performances` JOIN `ods_dingtalk_kol_tidwe_content` via `REGEXP_EXTRACT(content_url,'/video/([0-9]+)',1) = video_id`
- 其他KOL路径：`ods_dingtalk_kol_tidwe_content` JOIN `ods_tw_pixel_orders` via `promo_code = discount_code`

---

### 报表 8：TikTok销售分类表

- **所属报表：** 营销推广-TikTok销售
- **需求时间：** 2026-06-05 | **上线时间：** 2026-06-19
- **最新需求字段：** 店铺、日期、product_id、sku_id、sku、订单类型、曝光量、页面浏览量、销量、销售额

| 报表字段 | Doris 表名 | 来源字段 | 映射状态 | 备注 |
|---------|-----------|---------|---------|------|
| 店铺 | `ods_tiktok_shop_product_performance` | `shop_name` | 可映射 | |
| 日期 | `ods_tiktok_shop_product_performance` | `collect_date` | 可映射 | DATE 类型，直取 |
| product_id | `ods_tiktok_shop_product_performance` | `product_id` | 可映射 | TikTok 数字型产品 ID（18位）；如 `1729385843129619083` |
| sku_id | SKU映射表（待提供） | `sku_id` | ⚠️ 当前置 NULL | LEFT JOIN `ods_udf_tiktok_product_sku_mapping` ON `product_id`；映射表待业务提供 |
| sku | SKU映射表（待提供） | `sku` | ⚠️ 当前置 NULL | 同上 |
| 订单类型 | `ods_tiktok_shop_product_performance` | `sales_breakdowns[*].content_type` | 需解析 JSON | JSON 展开；枚举值：`LIVE`/`VIDEO`/`PRODUCT_CARD`/`SHOWCASE` |
| 曝光量 | `ods_tiktok_shop_product_performance` | `traffic_breakdowns[*].traffic.impressions` | 需解析 JSON | 按 `content_type` 取对应行；同一字段值对应 `订单类型` |
| 页面浏览量 | `ods_tiktok_shop_product_performance` | `traffic_breakdowns[*].traffic.page_views` | 需解析 JSON | 同上 |
| 销量 | `ods_tiktok_shop_product_performance` | `sales_breakdowns[*].sales.items_sold` | 需解析 JSON | 同上 |
| 销售额 | `ods_tiktok_shop_product_performance` | `sales_breakdowns[*].sales.gmv.amount` | 需解析 JSON | 类型 DECIMAL(18,4)；币种 USD（`gmv_currency`） |

**JSON展开粒度：** 每行 = 1个product_id × 1天 × 1个content_type
**DQ校验：** 各 content_type 的 `gmv_amount` SUM 应 ≈ 顶层 `sales_gmv_amount` 字段

---

### 报表 9：产品营销表现表

- **所属报表：** 营销推广-产品级明细
- **需求时间：** 2026-06-10 | **上线时间：** 2026-06-30
- **备注：** 产品级营销及产出数据，渠道×产品维度存在数据局限

| 报表字段 | Doris 表名 | 来源字段 | 映射状态 | 备注 |
|---------|-----------|---------|---------|------|
| 日期 | `ods_tw_product_analytics` | `event_date` | 可映射 | |
| 店铺 | `ods_tw_product_analytics` | `shop_name` | 可映射 | |
| SKU/SPU | `ods_tw_product_analytics` | `sku` / `product_id` / `product_name` | 可映射 | `sku` 字段需确认数据完整性 |
| 推广渠道 | `ods_tw_pixel_orders` | `channel` | 需转换 | 无法精确到渠道×产品的展现/流量维度 |
| 推广渠道细分类 | `ods_tw_pixel_orders` | `channel` | 需转换 | 同上 |
| 曝光量 | `ods_tw_product_analytics` | `impressions` | 可映射 | 仅产品级，无渠道维度 |
| 流量 | `ods_tw_product_analytics` | `visits` | 可映射 | 仅产品级；`clicks` 可参考 |
| 订单量 | `ods_tw_product_analytics` | `orders` | 可映射 | |
| 销量 | `ods_tw_product_analytics` | `total_items_sold` | 可映射 | |
| 销售额 | `ods_tw_product_analytics` | `revenue` | 可映射 | 备选：`total_order_value` |
| 新客订单 | `ods_tw_product_analytics` | `new_customer_orders` | 可映射 | |
| 新客销量 | `ods_tw_product_analytics` | `new_customer_total_items_sold` | 可映射 | |
| 新客销售额 | `ods_tw_product_analytics` | `new_customer_revenue` | 可映射 | |
| 新客数 | `ods_tw_product_analytics` | `customers` | ⚠️ 待确认 | `customers` 为所有客户数，`new_customer_orders` 为新客订单数，一新客多单会重复计 |

**维度局限说明：** 渠道×产品维度不完整；`ods_tw_product_analytics` 只到产品级（无渠道）；`ods_tw_pixel_joined` 只到渠道级（无产品）；`ods_tw_pixel_orders` 可通过 `products_info` JSON 展开关联渠道+产品，但无展现量和流量。

---

### 报表 10：社媒账号信息

- **需求时间：** 非本期需求 | **上线时间：** 2026-05-18

| 报表字段 | Doris 表名 | 来源字段 | 映射状态 | 备注 |
|---------|-----------|---------|---------|------|
| 平台 | `ods_tw_social_media_pages` | `channel` | 需转换 | 值为"meta-analytics"→"Facebook"；YouTube/TikTok/Instagram 认证失败 |
| 账号 | `ods_tw_social_media_pages` | `page_name` | 可映射 | 仅 Facebook 可用 |
| 日期 | `ods_tw_social_media_pages` | `event_date` | 可映射 | 仅 Facebook 可用 |
| 粉丝量 | — | — | ❌ 缺失 | `ods_tw_social_media_pages` 仅有 `fan_adds`/`fan_removes`（增减量），无总粉丝量 |
| 帖子数 | — | — | ❌ 缺失 | 无帖子数字段；其他平台认证失败 |

---

### 报表 11：社媒发布内容信息

- **需求时间：** 非本期需求 | **上线时间：** 2026-05-18

| 报表字段 | Doris 表名 | 来源字段 | 映射状态 | 备注 |
|---------|-----------|---------|---------|------|
| 平台 | — | — | 需转换 | TikTok/YouTube 在写入时标记平台；Facebook/Instagram 认证失败 |
| 账号 | `ods_tiktok_video_performances` | `username` | 可映射 | TikTok 可用；YouTube URL 接口无账号字段 |
| 内容ID | `ods_tiktok_video_performances` / `ods_youtube_video_stats` | `video_id` / `video_id` | 可映射 | TikTok：直取 `video_id`；YouTube：`ods_youtube_video_stats.video_id` |
| 内容 | `ods_tiktok_video_performances` | `title` | 可映射 | TikTok 有 `title`；YouTube URL 接口无标题字段 |
| 日期 | `ods_tiktok_video_performances` | `collect_date` | 可映射 | `video_post_time`（bigint ms）部分为 NULL，建议用 `collect_date`；YouTube：`ods_youtube_video_stats.published_at` |
| 观看数 | `ods_tiktok_video_performances` / `ods_youtube_video_stats` | `views` / `view_count` | 可映射 | |
| 点赞数 | `ods_tiktok_shop_video_performance_detail` / `ods_youtube_video_stats` | `traffic_likes` / `like_count` | 可映射 | TikTok：按 `video_id` JOIN |
| 评论数 | `ods_tiktok_shop_video_performance_detail` / `ods_youtube_video_stats` | `traffic_comments` / `comment_count` | 可映射 | |
| 转发数 | `ods_tiktok_shop_video_performance_detail` | `traffic_shares` | 可映射 | 仅 TikTok；YouTube/Facebook 不可用 |

---

### 报表 12：TikTok达人表现表（新增）

- **所属报表：** 营销推广-TikTok达人
- **备注：** 关键数据缺口：TikTok联盟订单（Creator order）**尚未接入 Doris**，影响 7 个字段；建议分两阶段开发

| 报表字段 | Doris 表名 | 来源字段 | 映射状态 | 备注 |
|---------|-----------|---------|---------|------|
| 店铺 | `ods_tiktok_video_performances` | `shop_name` | ✅ 可映射 | |
| 日期 | `ods_tiktok_video_performances` | `collect_date` | ✅ 可映射 | `video_post_time` 部分为 NULL，建议用 `collect_date`；⚠️ 与联盟订单日期口径待统一 |
| product_id | `ods_tiktok_video_performances` | `products` JSON → `[*].id` | ⚠️ 需解析 JSON | `products` 字段为 JSON 数组，一视频可挂多商品；展开策略（多行 or 取首个）待业务确认 |
| sku_id | TikTok联盟订单（未接入） | `sku_id` | ❌ 数据源未接入 | 仅联盟订单有此粒度；`ods_tiktok_video_performances` 无 sku_id |
| sku | SKU映射表（待提供） | — | ❌ 映射表未提供 | 依赖 sku_id；需 TikTok product_id → 内部 SKU 映射表 |
| 订单类型 | TikTok联盟订单（未接入） | `content_type` | ❌ 数据源未接入 | `ods_tiktok_video_performances` 无 `content_type` 字段 |
| 达人id | `ods_tiktok_video_performances` | `username` | ✅ 可映射 | |
| 内容类型 | TikTok联盟订单（未接入） | `content_type` | ❌ 数据源未接入 | 同订单类型 |
| 视频id | `ods_tiktok_video_performances` | `video_id` | ✅ 可映射 | |
| 视频URL | `ods_dingtalk_kol_tidwe_content` / 规则构造 | `content_url` | ⚠️ 覆盖不全 | 已知 KOL 取钉钉表 `content_url`；其余构造：`CONCAT('https://www.tiktok.com/@',username,'/video/',video_id)` |
| 播放量 | `ods_tiktok_video_performances` | `views` | ✅ 可映射 | 无 page_views 数据 |
| 订单数 | TikTok联盟订单（未接入） | `COUNT(DISTINCT order_id)` | ❌ 数据源未接入 | 临时方案：`sku_orders`（汇总值，口径不同） |
| 销量 | TikTok联盟订单（未接入） | `quantity` | ❌ 数据源未接入 | 临时方案：`items_sold` |
| 销售额 | TikTok联盟订单（未接入） | `payment_amount` | ❌ 数据源未接入 | 临时方案：`gmv_amount` |
| 佣金 | TikTok联盟订单（未接入） | `est_commission` | ❌ 数据源未接入 | 预估佣金（est. standard + est. Shop Ads commission） |
| 寄样费 | `ods_finance_bi_report_middle_multi_order` JOIN `ods_dingtalk_kol_tidwe_sample` | `amount` | ⚠️ JOIN受阻，置 NULL | 同报表7问题：`tracking_number` ≠ `platform_order_no` 格式不匹配 |

**待解决问题（按优先级）：**

| # | 问题 | 影响字段 | 优先级 |
|---|-----|---------|--------|
| P1 | TikTok联盟订单尚未接入 Doris | sku_id、订单类型、内容类型、订单数、销量、销售额、佣金 | 🔴 高 |
| P2 | SKU映射表未提供 | sku_id、sku | 🔴 高 |
| P3 | 日期口径不统一（collect_date vs 订单时间） | 日期 | 🟡 中 |
| P4 | 视频URL覆盖不全（Piscifun尤其不全） | 视频URL | 🟡 中 |
| P5 | 寄样费 JOIN 路径受阻 | 寄样费 | 🟡 中 |
| P6 | 一视频多商品展开策略未确认 | product_id | 🟡 中 |

---

### 报表 13：TikTok自店铺视频表现表（新增）

- **所属报表：** 营销推广-TikTok达人
- **备注：** 所有字段均可从 `ods_tiktok_video_performances` 取到，**立即可开发**

| 报表字段 | Doris 表名 | 来源字段 | 映射状态 | 备注 |
|---------|-----------|---------|---------|------|
| 店铺 | `ods_tiktok_video_performances` | `shop_name` | ✅ 可映射 | |
| 日期 | `ods_tiktok_video_performances` | `collect_date` | ✅ 可映射 | `video_post_time` 为 bigint ms 且部分 NULL，建议用 `collect_date` |
| product_id | `ods_tiktok_video_performances` | `products` JSON → `[*].id` | ⚠️ 需解析 JSON | 同报表12 P6；一视频可挂多商品，展开策略待确认 |
| 视频id | `ods_tiktok_video_performances` | `video_id` | ✅ 可映射 | |
| 视频URL | `ods_tiktok_video_performances` | 规则构造 | ⚠️ 需构造 | `CONCAT('https://www.tiktok.com/@', username, '/video/', video_id)` |
| 视频标题 | `ods_tiktok_video_performances` | `title` | ✅ 可映射 | |
| 播放量 | `ods_tiktok_video_performances` | `views` | ✅ 可映射 | |
| 订单数 | `ods_tiktok_video_performances` | `sku_orders` | ✅ 可映射（近似） | 平台汇总值，与"联盟订单 COUNT(distinct order_id)"口径略有不同，对自店铺视频表够用 |
| 销量 | `ods_tiktok_video_performances` | `items_sold` | ✅ 可映射 | |
| 销售额 | `ods_tiktok_video_performances` | `gmv_amount` | ✅ 可映射 | DECIMAL(18,4)；币种 USD（`gmv_currency`） |

**⚠️ 一个待确认点：** 无商品视频（`products = []` 或 NULL）是否也需要出现在报表中？

---

## 附录：关键待解决问题汇总

| 问题 | 影响报表 | 优先级 |
|-----|---------|--------|
| TikTok联盟订单（Creator order）未接入 Doris | 报表12（达人表现表）7个字段 | 🔴 高 |
| TikTok product_id → 内部 SKU 映射表未提供 | 报表8、报表12 | 🔴 高 |
| 样品费 JOIN 路径受阻（tracking_number ≠ platform_order_no） | 报表7-表1、报表12 | 🟡 中 |
| `ods_tw_pixel_joined.shop_name` 为 NULL | 报表3、报表4 | 🟡 中（已通过 dim_shop JOIN 解决） |
| EDM（cartsee）数据未入库 | 报表3（EDM花费路径） | 🟡 中 |
| TikTok ad_spend 接口采集失败 | 报表3（TikTok信息流广告花费） | 🟡 中 |
| Facebook / YouTube Studio 认证失败 | 报表10、11 | 🟡 中（非本期核心） |
