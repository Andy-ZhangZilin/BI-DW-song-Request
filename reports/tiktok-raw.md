# tiktok 字段验证报告（Raw）

**生成时间：** 2026-04-07 01:21:59

## 接口：shop_product_performance

**样本记录数：** 0

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|

## 需求字段（待人工对照）

| 需求字段（中文） | 报表 | 对照结果 |
|----------------|------|---------|
| SKU | profit_table | ⬜ 待确认 |
| TikTok 销售额 | profit_table | ⬜ 待确认 |

---

## 接口：affiliate_creator_orders

**生成时间：** 2026-04-07 01:22:00

**样本记录数：** 0

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|

---

## 接口：video_performances

**生成时间：** 2026-04-07 01:22:01

**样本记录数：** 0

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|

---

## 接口：ad_spend

**生成时间：** 2026-04-07 01:22:01

**样本记录数：** 0

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|

---

## 接口：return_refund

**生成时间：** 2026-04-07 01:22:05

**样本记录数：** 18

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| combined_return_id | string | 0 | 否 |
| create_time | number | 1697402608 | 否 |
| discount_amount | array | [{'currency': 'USD', 'product_platform_discount': '24', 'product_seller_discount': '10', 'shipping_fee_platform_discount': '10.99', 'shipping_fee_seller_discount': '0'}] | 否 |
| handover_method | string | DROP_OFF | 否 |
| is_combined_return | boolean | False | 否 |
| order_id | string | 576500383223812672 | 否 |
| refund_amount | object | {'currency': 'USD', 'refund_shipping_fee': '0', 'refund_subtotal': '60.79', 'refund_tax': '4.8', 'refund_total': '60.79'} | 否 |
| return_id | string | 4035228871802065472 | 否 |
| return_line_items | array | [{'order_line_item_id': '576500383224009280', 'product_image': {'height': 200, 'url': 'https://p16-oec-general-useast5.ttcdn-us.com/tos-useast5-i-omjb5zjo8w-tx/29990ea64bd74c13a3f8d7df01138265~tplv-fhlh96nyum-origin-jpeg.jpeg?dr=12178&from=3548368146&idc=useast5&ps=933b5bde&shcp=fd1b0147&shp=d37fcd12&t=555f072d', 'width': 200}, 'product_name': 'TideWe Chest Waders with Boots Hanger, Realtree MAX5 Camo Neoprene Hunting Fishing Bootfoot Waders', 'refund_amount': {'currency': 'USD', 'refund_shipping_fee': '0', 'refund_subtotal': '60.79', 'refund_tax': '4.8', 'refund_total': '60.79'}, 'return_line_item_id': '4035228871802131008', 'seller_sku': 'WD010-M11', 'sku_id': '1729385925305012875', 'sku_name': 'M11'}] | 否 |
| return_method | string | PLATFORM_SHIPPED | 否 |
| return_provider_id | string | 7117858858072016686 | 否 |
| return_provider_name | string | USPS | 否 |
| return_reason | string | ecom_order_delivered_refund_and_return_reason_wrong_product | 否 |
| return_reason_text | string | Wrong item was sent | 否 |
| return_shipping_document_type | string | SHIPPING_LABEL | 否 |
| return_status | string | RETURN_OR_REFUND_REQUEST_COMPLETE | 否 |
| return_tracking_number | string | 9302210602900000356714 | 否 |
| return_type | string | RETURN_AND_REFUND | 否 |
| return_warehouse_address | object | {'full_address': '30 Executive Avenue,,Edison,Middlesex,New Jersey,United States'} | 否 |
| role | string | BUYER | 否 |
| shipment_type | string | PLATFORM | 否 |
| shipping_fee_amount | array | [{'buyer_paid_return_shipping_fee': '0', 'currency': 'USD', 'platform_paid_return_shipping_fee': '0', 'seller_paid_return_shipping_fee': '7.99'}] | 否 |
| update_time | number | 1698998277 | 否 |

---

## 接口：affiliate_sample_status

**生成时间：** 2026-04-07 01:22:05

**样本记录数：** 0

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|

---

## 接口：affiliate_campaign_performance

**生成时间：** 2026-04-07 01:22:05

**样本记录数：** 0

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
