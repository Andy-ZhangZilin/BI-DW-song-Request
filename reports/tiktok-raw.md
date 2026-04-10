# tiktok 字段验证报告（Raw）

**生成时间：** 2026-04-10 11:49:16

## 接口：shop_product_performance

**样本记录数：** 1

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| latest_available_date | string | 2026-04-08 | 否 |
| performance.intervals[].end_date | string | 2026-04-10 | 否 |
| performance.intervals[].sales.breakdowns[].content_type | string | LIVE | 否 |
| performance.intervals[].sales.breakdowns[].sales.avg_customers | number | 0 | 否 |
| performance.intervals[].sales.breakdowns[].sales.gmv.amount | string | 0.00 | 否 |
| performance.intervals[].sales.breakdowns[].sales.gmv.currency | string | USD | 否 |
| performance.intervals[].sales.breakdowns[].sales.items_sold | number | 0 | 否 |
| performance.intervals[].sales.gmv.amount | string | 0.00 | 否 |
| performance.intervals[].sales.gmv.currency | string | USD | 否 |
| performance.intervals[].sales.items_sold | number | 0 | 否 |
| performance.intervals[].sales.orders | number | 0 | 否 |
| performance.intervals[].start_date | string | 2026-03-11 | 否 |
| performance.intervals[].traffic.breakdowns[].content_type | string | LIVE | 否 |
| performance.intervals[].traffic.breakdowns[].traffic.avg_conversion_rate | string | 0.00 | 否 |
| performance.intervals[].traffic.breakdowns[].traffic.avg_unique_page_views | number | 0 | 否 |
| performance.intervals[].traffic.breakdowns[].traffic.ctr | string | 0.00 | 否 |
| performance.intervals[].traffic.breakdowns[].traffic.impressions | number | 0 | 否 |
| performance.intervals[].traffic.breakdowns[].traffic.page_views | number | 0 | 否 |
| performance.ratings[].count | number | 0 | 否 |
| performance.ratings[].percentage | string | NaN | 否 |
| performance.ratings[].stars | string | 5_STAR | 否 |
| performance.top_contents | array | [] | 否 |
| performance.top_creators | array | [] | 否 |

---

## 接口：video_performances

**生成时间：** 2026-04-10 11:49:18

**样本记录数：** 1

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| latest_available_date | string | 2026-04-08 | 否 |
| next_page_token | string | cGFnZV9udW1iZXI9MQ== | 否 |
| total_count | number | 9147 | 否 |
| videos[].avg_customers | number | 9 | 否 |
| videos[].click_through_rate | string | 0.0326 | 否 |
| videos[].duration | number | 39 | 否 |
| videos[].gmv.amount | string | 1090.85 | 否 |
| videos[].gmv.currency | string | USD | 否 |
| videos[].gpm.amount | string | 279.28 | 否 |
| videos[].gpm.currency | string | USD | 否 |
| videos[].hash_tags[] | array<string> | ['turkeyhunting', 'runandgun', 'turkeyseason', 'huntinggear', 'tiktokshop', 'camo'] | 否 |
| videos[].id | string | 7536784906265890103 | 否 |
| videos[].items_sold | number | 12 | 否 |
| videos[].products[].id | string | 1731440173610668683 | 否 |
| videos[].products[].name | string | 【Tidewe Hunting Winter】Tidewe Amazing Offer 270° See Through 1-2/2-3/3-4/4-6 Person Hunting Blind, Pop Up Ground Deer Blind Tent | 否 |
| videos[].sku_orders | number | 9 | 否 |
| videos[].title | string | Hunting Blind That Is See Through From The Inside And Camo Concealed on The Outside. @tideweofficial #hunting #deerhunting #huntingblind #deerstand #camo  | 否 |
| videos[].username | string | sintexan | 否 |
| videos[].video_post_time | string | 2025-08-09 18:55:09 | 否 |
| videos[].views | number | 3906 | 否 |

---

## 接口：ad_spend

**生成时间：** 2026-04-10 11:49:18

**样本记录数：** 0

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|

---

## 接口：return_refund

**生成时间：** 2026-04-10 11:49:20

**样本记录数：** 10

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| combined_return_id | string | 0 | 否 |
| create_time | number | 1774397640 | 否 |
| discount_amount[].currency | string | USD | 否 |
| discount_amount[].product_platform_discount | string | 48 | 否 |
| discount_amount[].product_seller_discount | string | 55 | 否 |
| discount_amount[].shipping_fee_platform_discount | string | 0 | 否 |
| discount_amount[].shipping_fee_seller_discount | string | 0 | 否 |
| handover_method | string | DROP_OFF | 否 |
| is_combined_return | boolean | False | 否 |
| is_quick_refund | boolean | True | 否 |
| order_id | string | 576495391452468877 | 否 |
| refund_amount.currency | string | USD | 否 |
| refund_amount.refund_shipping_fee | string | 0 | 否 |
| refund_amount.refund_subtotal | string | 116.35 | 否 |
| refund_amount.refund_tax | string | 9.36 | 否 |
| refund_amount.refund_total | string | 116.35 | 否 |
| return_id | string | 4035316690400940685 | 否 |
| return_line_items[].order_line_item_id | string | 576495391452599949 | 否 |
| return_line_items[].product_image.height | number | 200 | 否 |
| return_line_items[].product_image.url | string | https://p16-oec-general-useast5.ttcdn-us.com/tos-useast5-i-omjb5zjo8w-tx/1c44232294af49dbb0aa862967702698~tplv-fhlh96nyum-origin-jpeg.jpeg?dr=12178&from=3548368146&idc=useast5&ps=933b5bde&shcp=fd1b014... | 否 |
| return_line_items[].product_image.width | number | 200 | 否 |
| return_line_items[].product_name | string | Tidewe LightWade Men’s Camouflage Waterproof Insulated Waist Waders \| Breathable Bootfoot Waterfowl Hunting Waders | 否 |
| return_line_items[].refund_amount.currency | string | USD | 否 |
| return_line_items[].refund_amount.refund_shipping_fee | string | 0 | 否 |
| return_line_items[].refund_amount.refund_subtotal | string | 116.35 | 否 |
| return_line_items[].refund_amount.refund_tax | string | 9.36 | 否 |
| return_line_items[].refund_amount.refund_total | string | 116.35 | 否 |
| return_line_items[].return_line_item_id | string | 4035316690401006221 | 否 |
| return_line_items[].seller_sku | string | WD026-VA-12-TE | 否 |
| return_line_items[].sku_id | string | 1732116937818477195 | 否 |
| return_line_items[].sku_name | string | Veil Avayde, 12 | 否 |
| return_method | string | PLATFORM_SHIPPED | 否 |
| return_provider_id | string | 7426268197461952274 | 否 |
| return_provider_name | string | FedEx™ | 否 |
| return_reason | string | ecom_order_delivered_reason_no_need_edt_test | 否 |
| return_reason_text | string | No longer needed | 否 |
| return_shipping_document_type | string | QR_CODE | 否 |
| return_status | string | BUYER_SHIPPED_ITEM | 否 |
| return_tracking_number | string | 792247950210 | 否 |
| return_type | string | RETURN_AND_REFUND | 否 |
| return_warehouse_address.full_address | string | 1251 South Rockefeller Avenue,,Ontario,San Bernardino,California,United States | 否 |
| role | string | BUYER | 否 |
| seller_next_action_response[].action | string | SELLER_RESPOND_RECEIVE_PACKAGE | 否 |
| seller_next_action_response[].deadline | number | 1778283275 | 否 |
| shipment_type | string | PLATFORM | 否 |
| shipping_fee_amount[].buyer_paid_return_shipping_fee | string | 0 | 否 |
| shipping_fee_amount[].currency | string | USD | 否 |
| shipping_fee_amount[].platform_paid_return_shipping_fee | string | 0 | 否 |
| shipping_fee_amount[].seller_paid_return_shipping_fee | string | 6.99 | 否 |
| update_time | number | 1775702792 | 否 |

---

## 接口：affiliate_sample_status

**生成时间：** 2026-04-10 11:49:22

**样本记录数：** 0

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|

---

## 接口：affiliate_campaign_performance

**生成时间：** 2026-04-10 11:49:23

**样本记录数：** 0

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|

---

## 接口：shop_video_performance_detail

**生成时间：** 2026-04-10 11:49:25

**样本记录数：** 1

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| latest_available_date | string | 2026-04-08 | 否 |
| performance.intervals[].end_date | string | 2026-04-10 | 否 |
| performance.intervals[].sales.breakdowns[].ctr | string | 0.0326 | 否 |
| performance.intervals[].sales.breakdowns[].customers | number | 9 | 否 |
| performance.intervals[].sales.breakdowns[].gmv.amount | string | 1090.85 | 否 |
| performance.intervals[].sales.breakdowns[].gmv.currency | string | USD | 否 |
| performance.intervals[].sales.breakdowns[].gpm.amount | string | 247.30 | 否 |
| performance.intervals[].sales.breakdowns[].gpm.currency | string | USD | 否 |
| performance.intervals[].sales.breakdowns[].items_sold | number | 12 | 否 |
| performance.intervals[].sales.breakdowns[].product_clicks | number | 144 | 否 |
| performance.intervals[].sales.breakdowns[].product_id | string | 1731440173610668683 | 否 |
| performance.intervals[].sales.breakdowns[].product_impressions | number | 4411 | 否 |
| performance.intervals[].sales.overall.ctr | string | 0.0326 | 否 |
| performance.intervals[].sales.overall.customers | number | 9 | 否 |
| performance.intervals[].sales.overall.gmv.amount | string | 1090.85 | 否 |
| performance.intervals[].sales.overall.gmv.currency | string | USD | 否 |
| performance.intervals[].sales.overall.gpm.amount | string | 279.28 | 否 |
| performance.intervals[].sales.overall.gpm.currency | string | USD | 否 |
| performance.intervals[].sales.overall.items_sold | number | 12 | 否 |
| performance.intervals[].sales.overall.product_clicks | number | 144 | 否 |
| performance.intervals[].sales.overall.product_impressions | number | 4411 | 否 |
| performance.intervals[].start_date | string | 2026-03-11 | 否 |
| performance.intervals[].traffic.comments | number | 0 | 否 |
| performance.intervals[].traffic.likes | number | 11 | 否 |
| performance.intervals[].traffic.new_followers | number | 1 | 否 |
| performance.intervals[].traffic.shares | number | 3 | 否 |
| performance.intervals[].traffic.views | number | 3906 | 否 |
| performance.viewer_profile | array | [] | 否 |
