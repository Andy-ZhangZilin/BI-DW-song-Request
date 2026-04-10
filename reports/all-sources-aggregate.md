# 数据源聚合结论文档

**生成时间：** 2026-04-10 11:55:04
**AI 分析完成时间：** 2026-04-10（Part 3 字段映射已填充）

---

## Part 1：数据源采集结论汇总

| 分类 | 数据来源 | 接口/表 | 采集状态 | 字段数 | 说明 |
|-----|---------|--------|---------|-------|------|
| TripleWhale | triplewhale | pixel_orders_table | 已生成 | 93 |  |
| TripleWhale | triplewhale | pixel_joined_tvf | 已生成 | 171 |  |
| TripleWhale | triplewhale | sessions_table | 已生成 | 29 |  |
| TripleWhale | triplewhale | product_analytics_tvf | 已生成 | 42 |  |
| TripleWhale | triplewhale | pixel_keywords_joined_tvf | 已生成 | 124 |  |
| TripleWhale | triplewhale | ads_table | 已生成 | 150 |  |
| TripleWhale | triplewhale | social_media_comments_table | 已生成 | 15 |  |
| TripleWhale | triplewhale | social_media_pages_table | 已生成 | 18 |  |
| TripleWhale | triplewhale | creatives_table | 已生成 | 58 |  |
| TripleWhale | triplewhale | ai_visibility_table | 采集失败 | 0 |  |
| TikTok-API | tiktok | shop_product_performance | 已生成 | 23 |  |
| TikTok-API | tiktok | video_performances | 已生成 | 20 |  |
| TikTok-API | tiktok | ad_spend | 采集失败 | 0 |  |
| TikTok-API | tiktok | return_refund | 已生成 | 50 |  |
| TikTok-API | tiktok | affiliate_sample_status | 采集失败 | 0 |  |
| TikTok-API | tiktok | affiliate_campaign_performance | 采集失败 | 0 |  |
| TikTok-API | tiktok | shop_video_performance_detail | 已生成 | 28 |  |
| 钉钉 | dingtalk | dingtalk | 已生成 | 24 |  |
| 钉钉 | dingtalk_sheet（普通表格） | dingtalk_sheet | 已生成 | 21 |  |
| 社媒后台 | youtube（热门榜） | — | ProxyError | 0 | HTTPSConnectionPool(host='www.googleapis.com', port=443): Max retries exceeded with url: /youtube/v3/videos?part=snippet%2Cstatistics&chart=mostPopular&maxResults=1&key=AIzaSyA8vwnXPVu9JLFwL8JnLPE3JP5CTKycKEY (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response'))) |
| youtube | youtube_url（视频URL） | youtube_url | 已生成 | 7 |  |
| 联盟后台 | awin | awin | 已生成 | 10 |  |
| EDM | cartsee | cartsee | 已生成 | 16 |  |
| 联盟后台 | partnerboost | partnerboost | 已生成 | 12 |  |
| 社媒后台 | facebook（social_media） | — | 认证失败 | 0 | authenticate() 返回 False |
| youtube | youtube_studio | — | 认证失败 | 0 | authenticate() 返回 False |
| 财务BI | multi_order | dws_finance_bi_report_middle_multi_order | 已生成 | 50 | 本地数据库表；示例数据来自 多平台订单汇总表.xlsx |

---

## Part 2：各数据源字段详情

> 各数据源字段明细请查阅对应 raw 报告文件（`reports/{source}-raw.md`）。
> AI 分析时请打开对应文件引用真实字段，不可虚构字段名。

| 分类 | 数据来源 | Raw 报告文件 | 采集状态 | 字段数 |
|-----|---------|------------|---------|-------|
| TripleWhale | triplewhale | `reports/triplewhale-raw.md` | 已生成 | 700 |
| TikTok-API | tiktok | `reports/tiktok-raw.md` | 已生成 | 121 |
| 钉钉 | dingtalk | `reports/dingtalk-raw.md` | 已生成 | 24 |
| 钉钉 | dingtalk_sheet（普通表格） | `reports/dingtalk_sheet-raw.md` | 已生成 | 21 |
| 社媒后台 | youtube（热门榜） | — | ProxyError | 0 |
| youtube | youtube_url（视频URL） | `reports/youtube_url-raw.md` | 已生成 | 7 |
| 联盟后台 | awin | `reports/awin-raw.md` | 已生成 | 10 |
| EDM | cartsee | `reports/cartsee-raw.md` | 已生成 | 16 |
| 联盟后台 | partnerboost | `reports/partnerboost-raw.md` | 已生成 | 12 |
| 社媒后台 | facebook（social_media） | — | 认证失败 | 0 |
| youtube | youtube_studio | — | 认证失败 | 0 |
| 财务BI | multi_order | `reports/multi-order-raw.md` | 已生成 | 50 |

---

## Part 3：报表字段映射分析

> 以下 11 张报表的字段映射待 AI 根据 Part 2 的真实字段数据进行分析填充。

### 报表 1：利润表

- **所属报表：** 销售表现、利润表
- **需求时间：** 2026-04-08
- **上线时间：** 2026-04-24
- **备注：** 销量、订单量、收入、成本、费用的数据来源；费用科目需要到四级

| 报表字段 | 来源数据源 | 来源字段（真实） | 映射状态 | 备注 |
|---------|----------|---------------|---------|------|
| 日期 | 财务BI / multi_order | 统计时间 | 可映射 | 示例：2025-10-02；备选：订购时间、付款时间、发货时间（根据业务口径选择） |
| 渠道 | 财务BI / multi_order | 渠道名称 | 可映射 | 示例：Amazon-SC（DE）；更粗粒度可用 平台名称（示例：Amazon） |
| 店铺 | 财务BI / multi_order | 店铺名 | 可映射 | 示例：Amazon-Greenstell Direct-DE；数字编号备选：店铺no |
| 国家 | 财务BI / multi_order | 商城所在国家名称 | 可映射 | 示例：德国；二字码备选：发货国家二字码 / 收货国家二字码 |
| ASIN/sku_id | 财务BI / multi_order | ASIN/商品ID | 可映射 | 示例：B0DG33Y2T3；字段名即为 ASIN/商品ID |
| MSKU | 财务BI / multi_order | MSKU | 可映射 | 示例：E-CPT017-V2-WBK135-A |
| SKU | 财务BI / multi_order | SKU | 可映射 | 示例：CPT017-V2-WBK135-RR-EU；SPU 备选：spu |
| 科目 | 财务BI / multi_order | 报表项目 | 可映射 | 示例：管理费用；即财务科目四级项目，与报表 2 科目表中的四级科目对应；字段 报表项目id 可作为关联主键 |
| 数值 | 财务BI / multi_order | 金额 | 可映射 | 原币种金额；人民币换算备选：金额(CNY)；汇率参考：CNY汇率；注意过滤 是否删除 = 0 排除已删除记录 |

### 报表 2：财务科目表

- **所属报表：** 销售表现、利润表
- **需求时间：** 2026-04-08
- **上线时间：** 2026-04-24
- **备注：** 财务科目级别关系主数据，可能需要财务提供（更新较少，变动需手动更新）；或使用四级科目作为主键

| 报表字段 | 来源数据源 | 来源字段（真实） | 映射状态 | 备注 |
|---------|----------|---------------|---------|------|
| 项ID | — | — | 缺失 | 当前所有数据源均无科目 ID 字段，需业务/财务自行定义并手动维护 |
| 科目名称 | — | — | 缺失 | 同上，需财务提供标准科目名称 |
| 科目级别 | — | — | 缺失 | 同上 |
| 一级科目 | — | — | 缺失 | 同上 |
| 二级科目 | — | — | 缺失 | 同上 |
| 三级科目 | — | — | 缺失 | 同上 |
| 四级科目 | — | — | 缺失 | 同上；建议将四级科目作为主键与报表 1 科目字段关联 |
| 说明/备注 | — | — | 缺失 | 同上；整张表需财务以静态主数据方式提供，变动时手动更新 |

### 报表 3：营销表现表

- **所属报表：** 营销推广-渠道效果
- **需求时间：** 2026-04-20
- **上线时间：** 2026-05-18
- **备注：** 营销归因数据，需要按营销的归因逻辑进行归因处理；维度需要到日维度；涉及花费部分获取到的数据全量入表

| 报表字段 | 来源数据源 | 来源字段（真实） | 映射状态 | 备注 |
|---------|----------|---------------|---------|------|
| 日期 | triplewhale / pixel_joined_tvf | event_date | 可映射 | 日维度；TikTok 部分用 shop_product_performance → performance.intervals[].start_date |
| 店铺 | triplewhale / pixel_orders_table | shop_name | 可映射 | pixel_joined_tvf 中 shop_name 示例为 null，建议以 pixel_orders_table 为主 |
| 推广渠道 | triplewhale / pixel_joined_tvf | channel | 可映射 | 示例值：google-ads、facebook-ads 等；TikTok 店铺渠道另从 shop_product_performance 获取 |
| 推广渠道细分类 | triplewhale / pixel_joined_tvf | channel | 需转换 | 按业务归因规则将 channel 值分类为 DTC-硬广/KOL/联盟/EDM/SEO/TikTok/社媒；需业务提供归因关键词映射辅助表 |
| 曝光量 | 多数据源 | （见备注） | 需转换 | DTC-硬广/TikTok信息流：pixel_joined_tvf → impressions；DTC-TikTok达人：video_performances → videos[].views；DTC-联盟：awin → impressions（partnerboost 无曝光字段，缺失）；DTC-EDM：cartsee → 打开率×已发送数 计算得出；DTC-KOL YouTube：youtube_url → statistics.viewCount；DTC-社媒（Facebook/YouTube Studio）：认证失败，待人工确认 |
| 流量 | 多数据源 | （见备注） | 需转换 | DTC 各渠道：pixel_joined_tvf → clicks；DTC-联盟 Awin：awin → clicks；DTC-联盟 PB：partnerboost → Clicks；TikTok 店铺：shop_product_performance → performance.intervals[].traffic.breakdowns[].traffic.page_views |
| 订单量 | triplewhale / pixel_joined_tvf | orders_quantity | 可映射 | TikTok 店铺：shop_product_performance → performance.intervals[].sales.orders |
| 销量 | triplewhale / pixel_joined_tvf | product_quantity_sold_in_order | 可映射 | TikTok 店铺：shop_product_performance → performance.intervals[].sales.items_sold |
| 销售额 | triplewhale / pixel_joined_tvf | order_revenue | 可映射 | TikTok 店铺：shop_product_performance → performance.intervals[].sales.gmv.amount；联盟：awin → totalValue，partnerboost → Gross Sales |
| 花费 | triplewhale / pixel_joined_tvf | spend | 可映射 | TikTok 信息流广告：ad_spend 接口采集失败，待人工确认；联盟佣金：awin → totalComm，partnerboost → Commission；KOL/EDM 花费无数字化数据源（来自合思费控，未接入） |
| 新客数 | triplewhale / pixel_joined_tvf | new_customer_orders | 可映射 | 注意：new_customer_orders 是新客订单数，可作为新客数近似；TikTok 无新客字段，缺失 |

**数据来源提示：**

- 渠道分类：DTC（硬广/KOL/联盟/EDM/SEO/TikTok/社媒）、TikTok（店铺/达人）
- DTC 流量/订单量/销量/销售额/新客数：均来自 TW pixel_joined_tvf()
- DTC-硬广 曝光量：TW；花费（信息流广告）：TW
- DTC-KOL 曝光量：KOL内容URL播放数；花费分效果侧/品牌侧（合思费控-红人支付表+红人信息表）+样品费（OMS发货单-寄样单头采尾）
- DTC-联盟 曝光量：Awin展现量 + PartnerBoost展现量；花费：合思费控-联盟
- DTC-EDM 曝光量：cartsee打开数；花费：合思费控
- DTC-SEO 曝光量：无；花费：合思费控
- DTC-TikTok 曝光量：video_performances播放数；花费（信息流广告）：平台广告花费（导流到独立站）
- DTC-社媒 曝光量：youtube/Instagram/TK/FB曝光量；花费：无
- TikTok-店铺：TikTok API-商品表现；花费（信息流广告）：目前暂只有店铺后台导出；新客数：无
- TikTok-达人：video_performances（播放数/点击率/订单量/销量/GMV）；佣金从TK联盟履约状态获取；样品费从LX平台订单或TK寄样单获取；新客数：无
- TW 归因说明：业务人员提供归因方式（适用TW的一套SQL），需辅助输入1-2张表（业务维护）取各渠道归因关键词范围
- 相关 TW 表：pixel_joined_tvf()、Pixel_order_table、sessions_table

### 报表 4：DTC广告投放数据

- **所属报表：** 营销推广-广告投放
- **需求时间：** 2026-05-10
- **上线时间：** 2026-06-03
- **备注：** TW可获取；活动/广告组/广告需含 id/名称

| 报表字段 | 来源数据源 | 来源字段（真实） | 映射状态 | 备注 |
|---------|----------|---------------|---------|------|
| 日期 | triplewhale / pixel_joined_tvf | event_date | 可映射 | |
| 店铺名称 | triplewhale / pixel_joined_tvf | integration_id | 待人工确认 | pixel_joined_tvf 中 shop_name 示例为 null，integration_id 为账号 ID 非可读名称；建议确认是否可通过配置映射；备选：pixel_orders_table → shop_name（但该表为订单粒度，非广告粒度） |
| 推广渠道 | triplewhale / pixel_joined_tvf | channel | 可映射 | 示例：google-ads、facebook-ads |
| 推广渠道细分类 | triplewhale / pixel_joined_tvf | channel | 需转换 | 按 channel 值进一步分类，如 facebook-ads→DTC-硬广/Meta，google-ads→DTC-硬广/Google |
| 活动 | triplewhale / pixel_joined_tvf | campaign_id / campaign_name | 可映射 | 两字段均存在，campaign_id 示例：11234696296，campaign_name 示例：CPC_Search_品类 |
| 广告组 | triplewhale / pixel_joined_tvf | adset_id / adset_name | 可映射 | adset_id 示例：111857950232，adset_name 示例：DSA |
| 广告 | triplewhale / pixel_joined_tvf | ad_id / ad_name | 可映射 | 注意：当过滤 NOT NULL AND <> '' 后，ad_id/ad_name 可能为空，参考文档提示的 WHERE 条件 |
| 曝光量 | triplewhale / pixel_joined_tvf | impressions | 可映射 | |
| 流量 | triplewhale / pixel_joined_tvf | clicks | 可映射 | |
| 订单量 | triplewhale / pixel_joined_tvf | orders_quantity | 可映射 | |
| 销量 | triplewhale / pixel_joined_tvf | product_quantity_sold_in_order | 可映射 | |
| 销售额 | triplewhale / pixel_joined_tvf | order_revenue | 可映射 | 备选：gross_sales |
| 花费 | triplewhale / pixel_joined_tvf | spend | 可映射 | |
| 新客数 | triplewhale / pixel_joined_tvf | new_customer_orders | 可映射 | new_customer_orders 为新客订单数，可作为新客数近似；若需区分新客人数需另行判断 |

**数据来源提示：**

- 全部数据可从 TW pixel_joined_tvf() 获取
- 查询示例：FROM pixel_joined_tvf() WHERE channel='facebook-ads' AND model='Linear All' AND attribution_window='lifetime' AND NOT (ad_name IS NULL) AND ad_name <> ''
- 活动/广告组/广告字段需包含 id 和名称

### 报表 5：KOL信息表

- **所属报表：** 营销推广-KOL效果
- **需求时间：** 2026-05-15
- **上线时间：** 2026-06-12
- **备注：** 钉钉多维表数据源；三张源表字段有不同（尤其TK达人信息），缺失字段忽略

| 报表字段 | 来源数据源 | 来源字段（真实） | 映射状态 | 备注 |
|---------|----------|---------------|---------|------|
| 红人ID | dingtalk | *红人ID | 可映射 | 三张源表均有该字段 |
| 红人类型 | dingtalk | 红人类型 | 可映射 | 示例：工具, 枪支；TK达人信息表可能缺失，缺失时忽略 |
| 合作平台 | dingtalk | *主页链接 | 需转换 | 钉钉无"合作平台"字段，需从 *主页链接 URL 解析平台（youtube.com→YouTube，tiktok.com→TikTok 等） |
| 跟进人 | dingtalk | *跟进人 | 可映射 | |
| 主页链接 | dingtalk | *主页链接 | 可映射 | |
| 所在州 | dingtalk | *所在州 | 可映射 | |
| 粉丝数 | dingtalk | *粉丝数（k） | 可映射 | 单位为 k（千），使用时注意单位换算 |
| 均播 | dingtalk | 长视频均播（k） | 可映射 | 单位为 k；TK达人信息表可能缺失 |
| 红人等级 | dingtalk | 红人等级 | 可映射 | 示例：B |
| 合作模式 | dingtalk | *合作模式 | 可映射 | 示例：单次合作 |
| 付费模式 | dingtalk | *付费模式 | 可映射 | 示例：纯样品置换 |
| 合作价格及交付项 | dingtalk | *合作价格及交付项（格式：合作周期-价格-交付内容） | 可映射 | 为非结构化文本，不易二次计算 |
| 佣金率 | dingtalk | *佣金率 | 可映射 | 注意：示例值含 #REF! 错误，数据质量需人工核查 |
| 合作review | dingtalk | 合作review | 可映射 | |
| 后续动作 | dingtalk | 后续动作 | 可映射 | |
| Code | dingtalk | *Code | 可映射 | 折扣码，可用于在 TW pixel_orders_table 中识别 KOL 带来的订单 |
| UTM长链 | — | — | 缺失 | 钉钉无 UTM 长链字段，仅有原UTM；建议在钉钉表中补充该列 |
| UTM短链 | — | — | 缺失 | 同上 |
| 原UTM | dingtalk | 原UTM | 可映射 | |
| Email | dingtalk | *Email | 可映射 | |
| 其他联系方式 | dingtalk | 其他联系方式 | 可映射 | |
| 备注 | dingtalk | 备注 | 可映射 | |
| 全名 | dingtalk | *全名 | 可映射 | |
| 寄样地址 | dingtalk | *寄样地址 | 可映射 | |
| 收款信息 | dingtalk | *收款信息 | 可映射 | 示例为文本格式（$5000/video），非结构化 |
| 合作日期 | — | — | 缺失 | 当前采集的钉钉 raw 无合作日期字段；建议确认是否在钉钉寄样记录或其他子表中存在 |
| 合作产品 | — | — | 缺失 | 当前 raw 无合作产品字段；建议确认钉钉寄样记录子表 |
| 内容发布 | — | — | 缺失 | 当前 raw 无内容发布字段；TikTok 视频ID 可作为部分补充（video_performances → videos[].id），但覆盖不完整 |

**数据来源提示：**

- 数据源1：KOL营销管理总表-TideWe → 红人信息汇总
- 数据源2：KOL营销管理总表-Piscifun → 红人信息汇总
- 数据源3：TikTok达人合作管理总表-TideWe → 达人信息汇总
- 三张表字段有不同，尤其TK达人信息表，缺失的字段忽略

### 报表 6：KOL内容表现表

- **所属报表：** 营销推广-KOL效果
- **需求时间：** 2026-05-15
- **上线时间：** 2026-06-12
- **备注：** YouTube等平台内容表现数据

| 报表字段 | 来源数据源 | 来源字段（真实） | 映射状态 | 备注 |
|---------|----------|---------------|---------|------|
| 内容发布id | tiktok / video_performances；youtube_url | videos[].id；id | 可映射 | TikTok 视频 ID：videos[].id；YouTube 视频 ID：youtube_url → id |
| 内容发布url | tiktok / video_performances；youtube_url | videos[].id；id | 需转换 | 无直接 URL 字段，需根据平台+ID 拼接：TikTok URL 格式：https://www.tiktok.com/@{username}/video/{id}；YouTube URL 格式：https://www.youtube.com/watch?v={id} |
| 日期 | tiktok / video_performances | videos[].video_post_time | 可映射 | TikTok 有发布时间；YouTube URL 接口（youtube_url）无日期字段，缺失 |
| 播放 | tiktok / video_performances；youtube_url | videos[].views；statistics.viewCount | 可映射 | TikTok：videos[].views；YouTube：statistics.viewCount |
| 点赞数 | tiktok / shop_video_performance_detail；youtube_url | performance.intervals[].traffic.likes；statistics.likeCount | 可映射 | TikTok 需通过 shop_video_performance_detail 按 video_id 查询；YouTube：statistics.likeCount；文档注：若获取不到可放弃 |
| 评论数 | tiktok / shop_video_performance_detail；youtube_url | performance.intervals[].traffic.comments；statistics.commentCount | 可映射 | TikTok 需通过 shop_video_performance_detail 按 video_id 查询；YouTube：statistics.commentCount；文档注：若获取不到可放弃 |
| GMV | tiktok / video_performances；triplewhale / pixel_orders_table | videos[].gmv.amount；order_revenue | 需转换 | TikTok 达人视频 GMV：videos[].gmv.amount（直接可用）；KOL YouTube GMV：pixel_orders_table 中过滤 discount_code IN (KOL折扣码列表) 后汇总 order_revenue |
| 新客数 | triplewhale / pixel_orders_table | is_new_customer / discount_code | 需转换 | 通过折扣码圈定 KOL 带来的订单，再过滤 is_new_customer = True 计数；TikTok video_performances → videos[].avg_customers 含义为"平均客户数"非新客数，不可直接使用 |

**数据来源提示：**

- 数据源1：KOL营销管理总表-TideWe → 红人信息汇总
- 数据源2：KOL营销管理总表-Piscifun → 红人信息汇总
- 数据源3：TikTok达人合作管理总表-TideWe → 达人信息汇总
- KOL GMV：通过折扣码识别订单及对应GMV（TW Pixel_order_table）
- TikTok：video_performances 的 ID 对应达人信息表 url 中的 ID 实现关联，无点赞/评论数
- 点赞数、评论数若获取不到便放弃

### 报表 7：KOL/达人合作效果表

- **所属报表：** 营销推广-KOL效果、营销推广-TikTok销售
- **需求时间：** 2026-05-25
- **上线时间：** 2026-06-12
- **备注：** KOL、达人寄样成本、合作费用、佣金以及产出；样品费=采购+头程+尾程

| 报表字段 | 来源数据源 | 来源字段（真实） | 映射状态 | 备注 |
|---------|----------|---------------|---------|------|
| 寄样单号 | dingtalk（寄样记录子表） | — | 待人工确认 | 当前 dingtalk raw 采集的是"红人信息汇总"，寄样记录子表未单独采集；需确认钉钉多维表中寄样记录的字段结构 |
| 合作状态 | dingtalk（寄样记录子表） | — | 待人工确认 | 同上，未采集寄样记录表 |
| 红人ID/达人ID | dingtalk | *红人ID | 可映射 | 通过 *红人ID 与寄样记录关联 |
| 寄样时间 | dingtalk（寄样记录子表） | — | 待人工确认 | 未采集寄样记录表 |
| 寄样产品SKU | dingtalk（寄样记录子表） | — | 待人工确认 | 未采集寄样记录表 |
| 样品费 | — | — | 缺失 | 据业务提示来源为 OMS 发货单（寄样单头采尾），当前无 OMS 数据源接入；建议后续接入 OMS 或从合思费控导入 |
| 合作费 | dingtalk | *收款信息 | 待人工确认 | *收款信息为非结构化文本（如"$5000/video"），无法直接作为数值字段使用；需结构化处理或另行采集 |
| 佣金 | — | — | 待人工确认 | 钉钉仅有 *佣金率（百分比），无佣金金额；可计算：销售额 × 佣金率；TikTok affiliate_campaign_performance 接口采集失败，无法直接获取联盟佣金金额 |
| 合作视频/素材 | tiktok / video_performances；youtube_url | videos[].id；id | 需转换 | TikTok 通过达人 username 关联视频 ID；YouTube 通过 KOL 主页链接关联 URL；需人工维护 KOL-视频 ID 映射关系 |
| 曝光量 | tiktok / video_performances；youtube_url | videos[].views；statistics.viewCount | 可映射 | TikTok 达人视频：videos[].views；YouTube：statistics.viewCount |
| 流量 | triplewhale / pixel_joined_tvf | clicks | 需转换 | 通过折扣码/UTM 在 pixel_joined_tvf 中过滤对应渠道后取 clicks；需业务提供 KOL 归因关键词范围 |
| 订单数 | triplewhale / pixel_orders_table | orders_quantity / discount_code | 需转换 | 过滤 discount_code IN (KOL折扣码列表) 后按 order_id 去重计数 |
| 销量 | triplewhale / pixel_orders_table | product_quantity_sold_in_order / discount_code | 需转换 | 同上，汇总 product_quantity_sold_in_order |
| 销售额 | triplewhale / pixel_orders_table；tiktok / video_performances | order_revenue；videos[].gmv.amount | 需转换 | KOL：pixel_orders_table 过滤折扣码后汇总 order_revenue；TikTok 达人：videos[].gmv.amount |
| 新客数 | triplewhale / pixel_orders_table | is_new_customer / discount_code | 需转换 | 过滤折扣码后，统计 is_new_customer = True 的订单数 |

**数据来源提示：**

- 数据源1：KOL营销管理总表-TideWe → 寄样记录
- 数据源2：KOL营销管理总表-Piscifun → 寄样记录
- 数据源3：TikTok达人合作管理总表-TideWe → 寄样记录

### 报表 8：TikTok销售分类表

- **所属报表：** 营销推广-TikTok销售
- **需求时间：** 2026-06-05
- **上线时间：** 2026-06-19
- **备注：** 区分视频、直播、商品卡；TikTok接口

| 报表字段 | 来源数据源 | 来源字段（真实） | 映射状态 | 备注 |
|---------|----------|---------------|---------|------|
| 店铺 | — | — | 待人工确认 | TikTok 所有接口均无店铺名称字段；可通过账号配置（shop_id/账号归属）映射，需业务补充配置数据 |
| 日期 | tiktok / video_performances；tiktok / shop_product_performance | videos[].video_post_time；performance.intervals[].start_date | 需转换 | 视频部分：videos[].video_post_time（精确到秒）；非视频（直播/商品卡）：shop_product_performance 为区间粒度，需拆解到日维度，实际只能获取区间汇总 |
| sku | tiktok / return_refund | return_line_items[].seller_sku | 待人工确认 | shop_product_performance 和 video_performances 均无 SKU 字段；return_refund 有 seller_sku，但仅覆盖退款订单；shop_video_performance_detail 有 product_id，非 SKU；建议确认 TikTok 是否有订单明细接口可提供 SKU |
| 订单类型 | tiktok / shop_product_performance | performance.intervals[].sales.breakdowns[].content_type | 可映射 | 值为 LIVE（直播）、VIDEO（视频）、PRODUCT_CARD（商品卡）等 |
| 账号 | tiktok / video_performances | videos[].username | 可映射 | 视频部分可获取达人/账号用户名；非视频部分（shop_product_performance）无账号字段 |
| 视频id | tiktok / video_performances | videos[].id | 可映射 | 视频部分：videos[].id；非视频部分无视频 ID |
| 达人 | tiktok / video_performances | videos[].username | 可映射 | 同账号字段；需与钉钉 TK 达人合作管理表关联以获取达人 ID 对应的中文名等信息 |
| 订单数 | tiktok / shop_product_performance | performance.intervals[].sales.orders | 可映射 | 非视频部分；视频部分（shop_video_performance_detail）仅有 customers（客户数）而非 orders，待人工确认是否等同 |
| 销量 | tiktok / shop_product_performance；tiktok / video_performances | performance.intervals[].sales.items_sold；videos[].items_sold | 可映射 | shop_product_performance 提供直播/商品卡销量；video_performances 提供视频销量 |
| 销售额 | tiktok / shop_product_performance；tiktok / video_performances | performance.intervals[].sales.gmv.amount；videos[].gmv.amount | 可映射 | 货币单位：USD；两个接口均有 GMV 字段 |
| 新客数 | — | — | 缺失 | TikTok 所有已采集接口均无新客字段；TikTok 店铺后台导出数据未接入系统，缺失 |

**数据来源提示：**

- 非视频（直播/商品卡）：TikTok API-商品表现表
- 视频：视频ID+达人来自 /analytics/{period}/shop_videos/{video_id}/performance 接口，关联TK达人合作表

### 报表 9：产品营销表现表

- **所属报表：** 营销推广-产品级明细
- **需求时间：** 2026-06-10
- **上线时间：** 2026-06-30
- **备注：** 产品级营销及产出数据（若可能，需要做到渠道级）

| 报表字段 | 来源数据源 | 来源字段（真实） | 映射状态 | 备注 |
|---------|----------|---------------|---------|------|
| 日期 | triplewhale / product_analytics_tvf | event_date | 可映射 | |
| 店铺 | triplewhale / product_analytics_tvf | shop_name | 可映射 | 示例：piscifun |
| SKU/SPU | triplewhale / product_analytics_tvf | sku / product_id / product_name | 可映射 | sku 字段存在（示例值为空字符串，需确认数据完整性）；product_id 作为 SPU 标识；product_name 为产品名称 |
| 推广渠道 | triplewhale / pixel_orders_table | channel | 需转换 | product_analytics_tvf 无渠道维度；需通过 pixel_orders_table 中 products_info[].product_sku 与 channel 关联，但无法精确到渠道×产品的展现/流量；文档已说明此维度组合存在数据局限 |
| 推广渠道细分类 | triplewhale / pixel_orders_table | channel | 需转换 | 同上，按 channel 值分类；渠道×产品维度不完整 |
| 曝光量 | triplewhale / product_analytics_tvf | impressions | 可映射 | 仅产品级，无渠道维度 |
| 流量 | triplewhale / product_analytics_tvf | visits | 可映射 | 仅产品级，无渠道维度；clicks 字段也可参考 |
| 订单量 | triplewhale / product_analytics_tvf | orders | 可映射 | 仅产品级；若需渠道×产品维度，需用 pixel_orders_table 展开 products_info 后关联 channel，但无展现/流量 |
| 销量 | triplewhale / product_analytics_tvf | total_items_sold | 可映射 | |
| 销售额 | triplewhale / product_analytics_tvf | revenue | 可映射 | 备选：total_order_value（含税/运费） |
| 新客订单 | triplewhale / product_analytics_tvf | new_customer_orders | 可映射 | |
| 新客销量 | triplewhale / product_analytics_tvf | new_customer_total_items_sold | 可映射 | |
| 新客销售额 | triplewhale / product_analytics_tvf | new_customer_revenue | 可映射 | 备选：new_customer_total_order_value |
| 新客数 | triplewhale / product_analytics_tvf | customers | 待人工确认 | product_analytics_tvf 有 customers 字段（所有客户数），无单独的新客人数字段；new_customer_orders 是新客订单数；若一个新客下多单则会被多计，请业务确认是否可接受 |

**数据来源提示：**

- 现无确切数据来源可完成产品×渠道维度的完整汇总
- product_analytics_tvf()：只到产品级数据（无渠道维度）
- pixel_joined_tvf()：只到渠道级（无产品维度）
- Pixel_order_table：有渠道+产品的订单相关数据，但没有展现量和流量
- 需要组合多个表或接受维度缺失

### 报表 10：社媒账号信息

- **需求时间：** 非本期需求，但需要展现量（关联社媒发布内容信息表）
- **上线时间：** 2026-05-18
- **备注：** youtube、Instagram、TikTok、Facebook 账号的粉丝、曝光、点赞、评论、转发；可能需要抓取或接入平台接口

| 报表字段 | 来源数据源 | 来源字段（真实） | 映射状态 | 备注 |
|---------|----------|---------------|---------|------|
| 平台 | triplewhale / social_media_pages_table | channel | 需转换 | channel 值为"meta-analytics"，需转换为"Facebook"；其他平台（YouTube、TikTok、Instagram）认证失败，暂无数据 |
| 账号 | triplewhale / social_media_pages_table | page_name | 可映射 | 仅 Facebook 页面可用；示例：Piscifun |
| 日期 | triplewhale / social_media_pages_table | event_date | 可映射 | 仅 Facebook 可用 |
| 粉丝量 | — | — | 缺失 | social_media_pages_table 仅有 fan_adds（新增粉丝）和 fan_removes（取消粉丝），无总粉丝量字段；YouTube、TikTok、Instagram 认证失败，无法获取；建议接入各平台官方 API 或通过 TW 补充配置 |
| 帖子数 | — | — | 缺失 | social_media_pages_table 无帖子数字段；views_total 为页面浏览数而非帖子数；其他平台均认证失败 |

### 报表 11：社媒发布内容信息

- **需求时间：** 非本期需求，但需要展现量
- **上线时间：** 2026-05-18
- **备注：** 可能需要抓取，或接入平台接口

| 报表字段 | 来源数据源 | 来源字段（真实） | 映射状态 | 备注 |
|---------|----------|---------------|---------|------|
| 平台 | tiktok / video_performances；youtube_url | （推断） | 需转换 | TikTok 无平台字段，需在数据写入时标记为"TikTok"；YouTube 同理标记为"YouTube"；Facebook/Instagram 认证失败，待人工确认 |
| 账号 | tiktok / video_performances | videos[].username | 可映射 | TikTok 可用；YouTube URL 接口无账号字段，缺失 |
| 内容ID | tiktok / video_performances；youtube_url | videos[].id；id | 可映射 | TikTok：videos[].id；YouTube：youtube_url → id |
| 内容 | tiktok / video_performances | videos[].title | 可映射 | TikTok：videos[].title（视频标题）；YouTube URL 接口无内容/标题字段，缺失 |
| 日期 | tiktok / video_performances | videos[].video_post_time | 可映射 | TikTok：videos[].video_post_time（发布时间）；YouTube URL 接口无日期字段，缺失 |
| 观看数 | tiktok / video_performances；youtube_url | videos[].views；statistics.viewCount | 可映射 | TikTok：videos[].views；YouTube：statistics.viewCount |
| 点赞数 | tiktok / shop_video_performance_detail；youtube_url | performance.intervals[].traffic.likes；statistics.likeCount | 可映射 | TikTok 需按 video_id 查询 shop_video_performance_detail；YouTube：statistics.likeCount |
| 评论数 | tiktok / shop_video_performance_detail；youtube_url | performance.intervals[].traffic.comments；statistics.commentCount | 可映射 | TikTok 需按 video_id 查询 shop_video_performance_detail；YouTube：statistics.commentCount |
| 转发数 | tiktok / shop_video_performance_detail | performance.intervals[].traffic.shares | 可映射 | TikTok 有转发数；YouTube URL 接口无转发数字段，缺失；Facebook/Instagram 认证失败，待人工确认 |

---

## Part 4：AI 分析提示语

请根据以下要求对本文档进行分析：

### 任务

对照 Part 2 中各数据源的**真实字段清单**，逐一分析 Part 3 中 11 张报表的每个字段，
判断该字段是否可以从现有数据源中获取，并填写字段映射关系。

### 规则

1. **来源字段必须真实**：只能引用 Part 2 中实际存在的字段名，不可虚构或假设字段存在
2. **映射状态**使用以下标记：
   - `可映射`：数据源中存在直接对应的字段
   - `需转换`：数据源中有相关字段但需要格式转换或计算（在备注中说明转换逻辑）
   - `缺失`：当前所有数据源中均无法获取该字段（在备注中说明建议的补充方案）
   - `待人工确认`：存在疑似对应字段但无法确定（在备注中说明原因）
3. **一个报表字段可能来自多个数据源**：如果多个数据源都能提供，列出主要来源并在备注中注明备选来源
4. **注意数据源的采集状态**：Part 1 中标注为"失败"/"未实现"/"跳过"的数据源暂无字段数据，
   若报表字段预期来自这些数据源，映射状态填"待人工确认"并在备注中说明原因

### 输出格式

直接在 Part 3 的表格中填写 `来源数据源`、`来源字段（真实）`、`映射状态`、`备注` 四列，
保持 Markdown 表格格式不变。
