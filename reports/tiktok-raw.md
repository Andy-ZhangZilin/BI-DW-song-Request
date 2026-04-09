# tiktok 字段验证报告（Raw）

**生成时间：** 2026-04-07 16:41:58

## 接口：shop_product_performance

**样本记录数：** 1

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| latest_available_date | string | 2026-04-05 | 否 |
| performance | object | {'intervals': [{'end_date': '2026-04-07', 'start_date': '2026-03-08'}], 'ratings': [{'count': 0, 'percentage': 'NaN', 'stars': '1_STAR'}, {'count': 0, 'percentage': 'NaN', 'stars': '4_STAR'}, {'count': 0, 'percentage': 'NaN', 'stars': '5_STAR'}, {'count': 0, 'percentage': 'NaN', 'stars': '2_STAR'}, {'count': 0, 'percentage': 'NaN', 'stars': '3_STAR'}], 'top_contents': [], 'top_creators': []} | 否 |

## 需求字段（待人工对照）

| 需求字段（中文） | 报表 | 对照结果 |
|----------------|------|---------|
| SKU | profit_table | ⬜ 待确认 |
| TikTok 销售额 | profit_table | ⬜ 待确认 |

---

## 接口：video_performances

**生成时间：** 2026-04-07 16:42:00

**样本记录数：** 1

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| latest_available_date | string | 2026-04-05 | 否 |
| next_page_token | string | cGFnZV9udW1iZXI9MQ== | 否 |
| total_count | number | 9327 | 否 |
| videos | array | [{'avg_customers': 6, 'click_through_rate': '0.0288', 'duration': 42, 'gmv': {'amount': '916.87', 'currency': 'USD'}, 'gpm': {'amount': '24.45', 'currency': 'USD'}, 'hash_tags': ['botas', 'agua', 'botasdeagua', 'botasdetrabajo', 'trabajo'], 'id': '7587892716835523854', 'items_sold': 8, 'products': [{'id': '1729386241510642315', 'name': '【Early Bird Deal】TideWe StrutBack Turkey Camo Vest with Kickstand Adjustable'}], 'sku_orders': 6, 'title': '#hunting #huntingtiktok #turkeyhunting #turkey #camo ', 'username': 'cody_finds', 'video_post_time': '2025-12-25 12:19:34', 'views': 37498}, {'avg_customers': 28, 'click_through_rate': '0.0314', 'duration': 52, 'gmv': {'amount': '1318.64', 'currency': 'USD'}, 'gpm': {'amount': '25.71', 'currency': 'USD'}, 'hash_tags': ['botas', 'agua', 'botasdeagua', 'botasdetrabajo', 'trabajo'], 'id': '7593855779233418551', 'items_sold': 28, 'products': [{'id': '1729385852300857995', 'name': 'TIDEWE Rain Suit, Lightweight Waterproof Breathable Rain Coat & Pant for Outdoor Activities Working Suit Daily Wear field gear mens clothing Rainproof Full Body Cover'}], 'sku_orders': 28, 'title': 'Rain suit #rainsuit #caza #pesca #caseria #hunting ', 'username': 'jay__alonso', 'video_post_time': '2026-01-10 13:59:21', 'views': 51281}, {'avg_customers': 19, 'click_through_rate': '0.0192', 'duration': 78, 'gmv': {'amount': '1149.02', 'currency': 'USD'}, 'gpm': {'amount': '12.54', 'currency': 'USD'}, 'hash_tags': ['botas', 'agua', 'botasdeagua', 'botasdetrabajo', 'trabajo'], 'id': '7610931607049964813', 'items_sold': 19, 'products': [{'id': '1729488071694063243', 'name': '【Early Bird Mega Deal】Tidewe FlexGrid Turkey Vest \| Modular Lightweight Turkey Hunting Seat Vest \| Magnetic Silent Pockets for Mobile Hunters'}], 'sku_orders': 19, 'title': 'Just got it in. This is what I’m planning to run this season. #turkeyseason #turkeyhunting #turkeyvest #runandgun #mobilehunter', 'username': 'brogan.berry', 'video_post_time': '2026-02-28 16:47:00', 'views': 91635}, {'avg_customers': 16, 'click_through_rate': '0.0207', 'duration': 41, 'gmv': {'amount': '917.68', 'currency': 'USD'}, 'gpm': {'amount': '12.49', 'currency': 'USD'}, 'hash_tags': ['botas', 'agua', 'botasdeagua', 'botasdetrabajo', 'trabajo'], 'id': '7616274982586338590', 'items_sold': 17, 'products': [{'id': '1729488071694063243', 'name': '【Early Bird Mega Deal】Tidewe FlexGrid Turkey Vest \| Modular Lightweight Turkey Hunting Seat Vest \| Magnetic Silent Pockets for Mobile Hunters'}], 'sku_orders': 16, 'title': 'Keep your gear organized and your movement minimal. Success comes next. 🦃#TIDEWE #TurkeySeason #TurkeyHunting #tiktokshopspringglowup #Hunting', 'username': 'tidewe_official', 'video_post_time': '2026-03-14 05:00:00', 'views': 73447}, {'avg_customers': 7, 'click_through_rate': '0.0299', 'duration': 20, 'gmv': {'amount': '776.25', 'currency': 'USD'}, 'gpm': {'amount': '30.03', 'currency': 'USD'}, 'hash_tags': ['botas', 'agua', 'botasdeagua', 'botasdetrabajo', 'trabajo'], 'id': '7589416903458704654', 'items_sold': 7, 'products': [{'id': '1729386241510642315', 'name': '【Early Bird Deal】TideWe StrutBack Turkey Camo Vest with Kickstand Adjustable'}], 'sku_orders': 7, 'title': '#hunting #huntingtiktok #tidewe #turkeyhunting #tiktokshop ', 'username': 'cody_finds', 'video_post_time': '2025-12-29 14:54:09', 'views': 25851}, {'avg_customers': 6, 'click_through_rate': '0.0511', 'duration': 153, 'gmv': {'amount': '565.15', 'currency': 'USD'}, 'gpm': {'amount': '370.35', 'currency': 'USD'}, 'hash_tags': ['hunting', 'deerhunting', 'huntingblind', 'deerstand', 'camo', 'calzado', 'caza', 'pesca'], 'id': '7517000439167061279', 'items_sold': 7, 'products': [{'id': '1729409149230158475', 'name': 'TIDEWE Work Boots Puncture-Proof with Steel Toe & Shank, Waterproof Anti Slip Rubber Boots for men worker, 6mm Neoprene Outdoor Boots Boy Footwear Walking Shoes Comfort Rain Shoes for Men steel toe boot men s boots work Closed Onyx'}], 'sku_orders': 6, 'title': 'Botas altas de trabajo con casquillo para protección no les entra agua muy fuertes #botas #agua #botasdeagua #botasdetrabajo #trabajo #zapatos #calzado #caza #pesca ', 'username': 'productosdehoy', 'video_post_time': '2025-06-17 11:21:09', 'views': 1526}, {'avg_customers': 5, 'click_through_rate': '0.0299', 'duration': 39, 'gmv': {'amount': '531.36', 'currency': 'USD'}, 'gpm': {'amount': '141.73', 'currency': 'USD'}, 'hash_tags': ['hunting', 'deerhunting', 'huntingblind', 'deerstand', 'camo'], 'id': '7536784906265890103', 'items_sold': 6, 'products': [{'id': '1731440173610668683', 'name': '【Tidewe Hunting Winter】Tidewe Amazing Offer 270° See Through 1-2/2-3/3-4/4-6 Person Hunting Blind, Pop Up Ground Deer Blind Tent'}], 'sku_orders': 5, 'title': 'Hunting Blind That Is See Through From The Inside And Camo Concealed on The Outside. @tideweofficial #hunting #deerhunting #huntingblind #deerstand #camo ', 'username': 'sintexan', 'video_post_time': '2025-08-09 18:55:09', 'views': 3749}, {'avg_customers': 55, 'click_through_rate': '0.0239', 'duration': 84, 'gmv': {'amount': '3104.12', 'currency': 'USD'}, 'gpm': {'amount': '8.69', 'currency': 'USD'}, 'hash_tags': ['turkeyhunting', 'turkeyseason', 'runandgun', 'longbeard', 'turkeyhunter'], 'id': '7617697612589796621', 'items_sold': 55, 'products': [{'id': '1729488071694063243', 'name': '【Early Bird Mega Deal】Tidewe FlexGrid Turkey Vest \| Modular Lightweight Turkey Hunting Seat Vest \| Magnetic Silent Pockets for Mobile Hunters'}], 'sku_orders': 55, 'title': 'I said what I said… you don’t need a $300 turkey vest. Change my mind. #turkeyhunting #turkeyseason #runandgun #longbeard #turkeyhunter ', 'username': 'brogan.berry', 'video_post_time': '2026-03-16 08:47:00', 'views': 357338}, {'avg_customers': 15, 'click_through_rate': '0.0200', 'duration': 23, 'gmv': {'amount': '1895.93', 'currency': 'USD'}, 'gpm': {'amount': '30.46', 'currency': 'USD'}, 'id': '7599022564974824735', 'items_sold': 17, 'products': [{'id': '1729386241510642315', 'name': '【Early Bird Deal】TideWe StrutBack Turkey Camo Vest with Kickstand Adjustable'}], 'sku_orders': 15, 'title': '', 'username': 'cody_finds', 'video_post_time': '2026-01-24 12:08:54', 'views': 62244}, {'avg_customers': 12, 'click_through_rate': '0.0223', 'duration': 64, 'gmv': {'amount': '1358.87', 'currency': 'USD'}, 'gpm': {'amount': '62.49', 'currency': 'USD'}, 'hash_tags': ['rainsuit', 'caza', 'pesca', 'caseria'], 'id': '7343421758495526187', 'items_sold': 12, 'products': [{'id': '1729386241510642315', 'name': '【Early Bird Deal】TideWe StrutBack Turkey Camo Vest with Kickstand Adjustable'}], 'sku_orders': 12, 'title': 'Found my new mountain seat. @tideweofficial #hunting #vest #turkeyhunting ', 'username': 'western_muleys', 'video_post_time': '2024-03-06 17:07:11', 'views': 21744}] | 否 |

---

## 接口：ad_spend

**生成时间：** 2026-04-07 16:42:00

**样本记录数：** 0

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|

---

## 接口：return_refund

**生成时间：** 2026-04-07 16:42:03

**样本记录数：** 10

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| combined_return_id | string | 4035318467501200120 | 否 |
| create_time | number | 1775473889 | 否 |
| discount_amount | array | [{'currency': 'USD', 'product_platform_discount': '0', 'product_seller_discount': '12', 'shipping_fee_platform_discount': '0', 'shipping_fee_seller_discount': '0'}] | 否 |
| handover_method | string | DROP_OFF | 否 |
| is_combined_return | boolean | True | 否 |
| is_quick_refund | boolean | True | 否 |
| order_id | string | 577314180216361720 | 否 |
| refund_amount | object | {'currency': 'USD', 'refund_shipping_fee': '0', 'refund_subtotal': '52.99', 'refund_tax': '0', 'refund_total': '53.16', 'retail_delivery_fee': '0.17'} | 否 |
| return_id | string | 4035318467501462264 | 否 |
| return_line_items | array | [{'order_line_item_id': '577314179380843256', 'product_image': {'height': 200, 'url': 'https://p16-oec-general-useast5.ttcdn-us.com/tos-useast5-i-omjb5zjo8w-tx/2c550a85e87046c789c809e3f8bfb2ae~tplv-fhlh96nyum-origin-jpeg.jpeg?dr=12178&from=3548368146&idc=useast5&ps=933b5bde&shcp=fd1b0147&shp=d37fcd12&t=555f072d', 'width': 200}, 'product_name': '[Amazing Offer] TIDEWE Rain Suit, Lightweight Waterproof Breathable Rain Coat & Pant for Outdoor Activities Working Suit Daily Wear field gear mens clothing', 'refund_amount': {'currency': 'USD', 'refund_shipping_fee': '0', 'refund_subtotal': '52.99', 'refund_tax': '0', 'refund_total': '53.16', 'retail_delivery_fee': '0.17'}, 'return_line_item_id': '4035318467501527800', 'seller_sku': 'RS002-BKM-V2-TE', 'sku_id': '1731389584718140043', 'sku_name': 'Black, M'}] | 否 |
| return_method | string | PLATFORM_SHIPPED | 否 |
| return_provider_id | string | 7117859084333745966 | 否 |
| return_provider_name | string | UPS | 否 |
| return_reason | string | ecom_order_delivered_reason_no_need_edt_test | 否 |
| return_reason_text | string | No longer needed | 否 |
| return_shipping_document_type | string | QR_CODE_NBNL | 否 |
| return_status | string | BUYER_SHIPPED_ITEM | 否 |
| return_tracking_number | string | 1ZR08H699013863459 | 否 |
| return_type | string | RETURN_AND_REFUND | 否 |
| return_warehouse_address | object | {'full_address': '30 Executive Avenue,,Edison,Middlesex,New Jersey,United States'} | 否 |
| role | string | BUYER | 否 |
| seller_next_action_response | array | [{'action': 'SELLER_RESPOND_RECEIVE_PACKAGE', 'deadline': 1778109755}] | 否 |
| shipment_type | string | PLATFORM | 否 |
| shipping_fee_amount | array | [{'buyer_paid_return_shipping_fee': '0', 'currency': 'USD', 'platform_paid_return_shipping_fee': '0', 'seller_paid_return_shipping_fee': '0'}] | 否 |
| update_time | number | 1775519179 | 否 |

---

## 接口：affiliate_sample_status

**生成时间：** 2026-04-07 16:42:05

**样本记录数：** 0

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|

---

## 接口：affiliate_campaign_performance

**生成时间：** 2026-04-07 16:42:06

**样本记录数：** 0

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
