# triplewhale 字段验证报告（Raw）

**生成时间：** 2026-04-08 16:11:32

## 接口：pixel_orders_table

**样本记录数：** 1

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| account_id | null |  | 是 |
| ad_id | string |  | 否 |
| ad_name | null |  | 是 |
| adset_id | string |  | 否 |
| adset_name | null |  | 是 |
| attribution_window | string | lifetime | 否 |
| billing_city | string | Smethport | 否 |
| billing_country | string | United States | 否 |
| billing_country_code | string | US | 否 |
| billing_province | string | Pennsylvania | 否 |
| browser | string | Chrome | 否 |
| campaign_id | string |  | 否 |
| campaign_name | string |  | 否 |
| campaign_type | null |  | 是 |
| cancelled_at | null |  | 是 |
| channel | string | smile_rewards | 否 |
| click_date | string | 2026-03-13 | 否 |
| click_ts | string | 2026-03-12 18:16:33 | 否 |
| cogs | number | 0 | 否 |
| cost_of_goods | number | 0 | 否 |
| created_at | string | 2026-03-25 00:14:57 | 否 |
| currency | string | USD | 否 |
| currency_rate | number | 1 | 否 |
| custom_combined_gross_profit | number | 213.17 | 否 |
| custom_combined_gross_sales | number | 224.67 | 否 |
| custom_combined_net_revenue | number | 203.18 | 否 |
| custom_expenses | number | 0 | 否 |
| custom_gross_profit | number | 0 | 否 |
| custom_gross_sales | number | 0 | 否 |
| custom_net_revenue | number | 0 | 否 |
| custom_number | number | 0 | 否 |
| custom_orders_quantity | number | 0 | 否 |
| custom_status | null |  | 是 |
| custom_string | null |  | 是 |
| custom_total_items_quantity | number | 0 | 否 |
| customer_email | string | blocked | 否 |
| customer_first_name | string | blocked | 否 |
| customer_from_city | string | Smethport | 否 |
| customer_from_country_code | string | US | 否 |
| customer_from_country_name | string | United States | 否 |
| customer_from_state_code | string | PA | 否 |
| customer_id | string | 5690818723909 | 否 |
| customer_last_name | string | blocked | 否 |
| customer_tags | array | ['member-label', 'signed up'] | 否 |
| device | string | desktop | 否 |
| discount_amount | number | 32.99 | 否 |
| discount_code | string | BG30 | 否 |
| discount_codes | array | [{'amount': 32.99, 'code': 'BG30', 'type': 'percentage'}] | 否 |
| event_date | string | 2026-03-25 | 否 |
| event_hour | number | 0 | 否 |
| financial_status | string | paid | 否 |
| fulfillment_status | string | fulfilled | 否 |
| gross_product_sales | number | 224.67 | 否 |
| gross_sales | number | 203.17999267578125 | 否 |
| handling_fees | number | 0 | 否 |
| integration_id | string | piscifun.myshopify.com | 否 |
| is_first_order_in_subscription | boolean | False | 否 |
| is_new_customer | boolean | False | 否 |
| is_subscription_order | boolean | False | 否 |
| landing_page | string | / | 否 |
| linear_weight | number | 1 | 否 |
| model | string | Triple Attribution | 否 |
| order_id | string | 6507850104901 | 否 |
| order_name | string | #298688 | 否 |
| order_revenue | number | 203.17999267578125 | 否 |
| orders_quantity | number | 1 | 否 |
| payment_gateway_costs | number | 0 | 否 |
| platform | string | shopify | 否 |
| product_quantity_sold_in_order | number | 3 | 否 |
| products_info | array | [{'product_id': '7796364640325', 'product_name': 'worry-free purchase', 'vendor': None, 'product_type': None, 'product_tags': [], 'product_sku': 'SEEL-WFP', 'variant_id': '43800087461957', 'product_name_price': 4.68999, 'discount_amount_for_product': 0, 'net_discount_amount_for_product': 0, 'product_name_quantity_sold': 1, 'is_gift_card': False, 'single_product_cost': 0, 'properties': [], 'duties': []}, {'product_id': '3958726983703', 'product_name': 'piscifun®  alinox 300 low profile baitcasting reel casting reels', 'vendor': None, 'product_type': None, 'product_tags': [], 'product_sku': 'RL170-L-V2-PN', 'variant_id': '29491487768599', 'product_name_price': 109.99, 'discount_amount_for_product': 0, 'net_discount_amount_for_product': 0, 'product_name_quantity_sold': 1, 'is_gift_card': False, 'single_product_cost': 0, 'properties': [], 'duties': []}, {'product_id': '3958726983703', 'product_name': 'piscifun®  alinox 300 low profile baitcasting reel casting reels', 'vendor': None, 'product_type': None, 'product_tags': [], 'product_sku': 'RL170-L-V2-PN', 'variant_id': '29491487768599', 'product_name_price': 109.99, 'discount_amount_for_product': 0, 'net_discount_amount_for_product': 32.99, 'product_name_quantity_sold': 1, 'is_gift_card': False, 'single_product_cost': 0, 'properties': [], 'duties': []}] | 否 |
| refund_money | number | 0 | 否 |
| session_city | string | State College | 否 |
| session_country | string | United States | 否 |
| session_id | string | cls0o6e5o1sCLUO24s_1774368616379 | 否 |
| shipping_city | string | blocked | 否 |
| shipping_costs | number | 0 | 否 |
| shipping_country | string | United States | 否 |
| shipping_country_code | string | US | 否 |
| shipping_country_name | string | United States | 否 |
| shipping_price | number | 0 | 否 |
| shipping_state | string | blocked | 否 |
| shipping_state_code | string | blocked | 否 |
| shipping_tax | number | 0 | 否 |
| shipping_zip | string | blocked | 否 |
| shop_id | string | piscifun.myshopify.com | 否 |
| shop_name | string | piscifun | 否 |
| shop_timezone | string | Asia/Shanghai | 否 |
| source_name | string | web | 否 |
| tags | array | ['seel-wfd'] | 否 |
| taxes | number | 11.5 | 否 |
| triple_id | string | cls0o6e5o1sCLUO24s | 否 |
| utm_medium | string |  | 否 |
| utm_source | string | smile_rewards | 否 |

## 需求字段（待人工对照）

| 需求字段（中文） | 报表 | 对照结果 |
|----------------|------|---------|
| 日期 | profit_table | ⬜ 待确认 |
| 销售额 | profit_table | ⬜ 待确认 |
| 订单量 | profit_table | ⬜ 待确认 |
| 曝光量 | marketing_table | ⬜ 待确认 |
| 点击量 | marketing_table | ⬜ 待确认 |
| 广告花费 | marketing_table | ⬜ 待确认 |
| ROAS | marketing_table | ⬜ 待确认 |

---

## 接口：pixel_joined_tvf

**生成时间：** 2026-04-08 16:11:37

**样本记录数：** 1

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| account_id | string | 1773257068 | 否 |
| ad_ai_recommendation | array | ['', '', '', ''] | 否 |
| ad_ai_roas_pacing | array | ['', '', '', ''] | 否 |
| ad_bid_amount | null |  | 是 |
| ad_copies | array | [] | 否 |
| ad_copy | null |  | 是 |
| ad_id | string | (not set) | 否 |
| ad_image_url | null |  | 是 |
| ad_manager_url | string | https://adwords.google.com/aw/overview?__e=1773257068&campaignId=11234696296 | 否 |
| ad_name | string | (not set) | 否 |
| ad_status | null |  | 是 |
| ad_study_cell_id | null |  | 是 |
| ad_study_end_date | null |  | 是 |
| ad_study_id | null |  | 是 |
| ad_study_integration_id | null |  | 是 |
| ad_study_name | null |  | 是 |
| ad_study_objective_id | null |  | 是 |
| ad_study_start_date | null |  | 是 |
| ad_title | null |  | 是 |
| ad_titles | array | [] | 否 |
| ad_type | null |  | 是 |
| add_to_carts | null |  | 是 |
| addresses | null |  | 是 |
| adset_ai_recommendation | array | ['', '', '', ''] | 否 |
| adset_ai_roas_pacing | array | ['', '', '', ''] | 否 |
| adset_bid_amount | number | 45 | 否 |
| adset_bid_strategy | string | MAXIMIZE_CONVERSION_VALUE | 否 |
| adset_daily_budget | null |  | 是 |
| adset_id | string | 111857950232 | 否 |
| adset_lifetime_budget | null |  | 是 |
| adset_name | string | DSA | 否 |
| adset_status | string | ACTIVE | 否 |
| asin | null |  | 是 |
| attribution_window | string | lifetime | 否 |
| book_demos | null |  | 是 |
| bounces | null |  | 是 |
| campaign_ai_recommendation | array | ['', '', '', ''] | 否 |
| campaign_ai_roas_pacing | array | ['', '', '', ''] | 否 |
| campaign_bid_strategy | string | MAXIMIZE_CONVERSION_VALUE | 否 |
| campaign_daily_budget | number | 30000 | 否 |
| campaign_id | string | 11234696296 | 否 |
| campaign_lifetime_budget | null |  | 是 |
| campaign_name | string | CPC_Search_品类 | 否 |
| campaign_status | string | ACTIVE | 否 |
| campaign_sub_type | null |  | 是 |
| campaign_type | string | SEARCH | 否 |
| channel | string | google-ads | 否 |
| channel_ai_recommendation | array | ['', '', '', ''] | 否 |
| channel_ai_roas_pacing | array | ['', '', '', ''] | 否 |
| channel_reported_all_conversions | number | 0 | 否 |
| channel_reported_conversion_value | number | 0 | 否 |
| channel_reported_conversions | number | 0 | 否 |
| channel_reported_onsite_conversion_value | number | 0 | 否 |
| channel_reported_onsite_purchases | number | 0 | 否 |
| channel_reported_visits | number | 0 | 否 |
| channel_type | null |  | 是 |
| checkouts | null |  | 是 |
| click_orders | number | 0 | 否 |
| click_revenue | number | 0 | 否 |
| clicks | number | 0 | 否 |
| cogs | number | 0 | 否 |
| contacts | null |  | 是 |
| cost_of_goods | number | 0 | 否 |
| creative_cta_type | null |  | 是 |
| creative_distribution_format | null |  | 是 |
| creative_format | null |  | 是 |
| creative_id | null |  | 是 |
| custom_combined_gross_profit | number | 0 | 否 |
| custom_combined_gross_sales | number | 0 | 否 |
| custom_combined_net_revenue | number | 0 | 否 |
| custom_expenses | number | 0 | 否 |
| custom_gross_profit | number | 0 | 否 |
| custom_gross_sales | number | 0 | 否 |
| custom_net_revenue | number | 0 | 否 |
| custom_orders_quantity | number | 0 | 否 |
| custom_total_items_quantity | number | 0 | 否 |
| delivered | null |  | 是 |
| destination_url | null |  | 是 |
| discount_codes | array | [] | 否 |
| email_signups | null |  | 是 |
| event_date | string | 2026-03-31 | 否 |
| experiment_CPIC | null |  | 是 |
| experiment_CPIC_lower | null |  | 是 |
| experiment_CPIC_upper | null |  | 是 |
| experiment_conversions_incremental | null |  | 是 |
| experiment_conversions_incremental_lower | null |  | 是 |
| experiment_conversions_incremental_share_percent | null |  | 是 |
| experiment_conversions_incremental_upper | null |  | 是 |
| experiment_event_date | null |  | 是 |
| experiment_i_ROAS | null |  | 是 |
| experiment_i_ROAS_lower_bound | null |  | 是 |
| experiment_i_ROAS_upper_bound | null |  | 是 |
| experiment_incremental_conversions_confidence_percent | null |  | 是 |
| experiment_incremental_revenue_confidence_percent | null |  | 是 |
| experiment_revenue_incremental_share_percent | null |  | 是 |
| gross_product_sales | number | 0 | 否 |
| gross_sales | number | 0 | 否 |
| i_revenue | null |  | 是 |
| i_roas | null |  | 是 |
| impressions | number | 0 | 否 |
| incremental_revenue_experiment | null |  | 是 |
| incremental_revenue_lower_bound_experiment | null |  | 是 |
| incremental_revenue_upper_bound_experiment | null |  | 是 |
| integration_id | string | 1773257068 | 否 |
| is_utm_valid | null |  | 是 |
| leads | null |  | 是 |
| links | array | [] | 否 |
| marked_as_spam | null |  | 是 |
| message_subject | null |  | 是 |
| message_template_html_url | null |  | 是 |
| meta_conversion_value | number | 0 | 否 |
| meta_facebook_orders | number | 0 | 否 |
| model | string | Triple Attribution | 否 |
| mqls | null |  | 是 |
| new_customer_cogs | number | 0 | 否 |
| new_customer_gross_sales | number | 0 | 否 |
| new_customer_order_revenue | number | 0 | 否 |
| new_customer_orders | number | 0 | 否 |
| new_visitors | null |  | 是 |
| non_meta_facebook_orders | number | 0 | 否 |
| non_tracked_spend | number | 0 | 否 |
| number_of_image_assets | null |  | 是 |
| number_of_video_assets | null |  | 是 |
| one_day_view_conversion_value | number | 0 | 否 |
| one_day_view_purchases | number | 0 | 否 |
| opened | null |  | 是 |
| opportunities | null |  | 是 |
| order_revenue | number | 0 | 否 |
| orders_quantity | number | 0 | 否 |
| original_provider_id | string | google-ads | 否 |
| outbound_clicks | number | 0 | 否 |
| payments | null |  | 是 |
| product_quantity_sold_in_order | number | 0 | 否 |
| provider_id | string | google-ads | 否 |
| received | null |  | 是 |
| recipients | null |  | 是 |
| refund_money | number | 0 | 否 |
| sent | null |  | 是 |
| session_page_views | null |  | 是 |
| sessions | null |  | 是 |
| seven_day_view_conversion_value | number | 0 | 否 |
| seven_day_view_purchases | number | 0 | 否 |
| shipping | null |  | 是 |
| shop_id | null |  | 是 |
| shop_name | null |  | 是 |
| spend | number | 0 | 否 |
| spend_experiment | null |  | 是 |
| sqls | null |  | 是 |
| subscribed_to_list | null |  | 是 |
| subscription_id_canceled_only_first | null |  | 是 |
| subscription_id_cancelled | null |  | 是 |
| subscription_id_signed | null |  | 是 |
| subscription_quantity | number | 0 | 否 |
| subscriptions_arr | number | 0 | 否 |
| suggested_budget | null |  | 是 |
| time_on_site | null |  | 是 |
| total_video_view | number | 0 | 否 |
| unique_visitors | null |  | 是 |
| unsubscribed | null |  | 是 |
| url_template | null |  | 是 |
| video_duration | null |  | 是 |
| video_p100_watched | number | 0 | 否 |
| video_p25_watched | number | 0 | 否 |
| video_p50_watched | number | 0 | 否 |
| video_p75_watched | number | 0 | 否 |
| video_url | null |  | 是 |
| video_url_iframe | null |  | 是 |
| video_url_source | null |  | 是 |
| view_orders | number | 0 | 否 |
| view_revenue | number | 0 | 否 |
| website_purchases | number | 0 | 否 |

---

## 接口：sessions_table

**生成时间：** 2026-04-08 16:11:39

**样本记录数：** 1

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| ad_id | string |  | 否 |
| adset_id | string |  | 否 |
| browser | string | Edge | 否 |
| campaign_id | string |  | 否 |
| channel | string | AMZN_US_ShopDirect | 否 |
| city | string | Waitsfield | 否 |
| country | string | United States | 否 |
| country_code | string | US | 否 |
| device | string | desktop | 否 |
| device_model | string |  | 否 |
| domain | string | piscifun.com | 否 |
| event_date | string | 2026-04-04 | 否 |
| event_date_timezone | string | Asia/Shanghai | 否 |
| event_hour | number | 5 | 否 |
| is_new_visitor | boolean | False | 否 |
| keyword_id | string |  | 否 |
| landing_page | string | /products/wholesale-piscifun-kraken-electric-big-game-reels-heiko-recommended-fishing-reels | 否 |
| ms_country | string |  | 否 |
| ms_country_name | string |  | 否 |
| session_elapsed_time | number | 0 | 否 |
| session_id | string | cm67sgko71RDOCj1zv_1775251636062 | 否 |
| session_page_views | number | 1 | 否 |
| session_start_ts | string | 2026-04-03 21:27:16 | 否 |
| shop_id | string | piscifun.myshopify.com | 否 |
| shop_name | string | piscifun | 否 |
| source | string | AMZN_US_ShopDirect | 否 |
| triple_id | string | cm67sgko71RDOCj1zv | 否 |
| utm_medium | string |  | 否 |
| utm_source | string | AMZN_US_ShopDirect | 否 |

---

## 接口：product_analytics_tvf

**生成时间：** 2026-04-08 16:11:49

**样本记录数：** 1

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| added_to_cart_events | number | 18 | 否 |
| added_to_cart_items | number | 20 | 否 |
| clicks | number | 10.176470588235293 | 否 |
| collection_id | null |  | 是 |
| collection_name | null |  | 是 |
| customers | number | 1 | 否 |
| entity | string | product | 否 |
| event_date | string | 2026-04-07 | 否 |
| fulfillment_costs | number | 0.45000001788139343 | 否 |
| id | string | 7924793049157 | 否 |
| images | array | [{'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/02_3bea92ca-d8de-4cdf-a7e3-db091a395a62.jpg?v=1762495087', 'image_alt': '', 'image_id': 38150929907781}, {'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/03_36536bf0-f3fb-4be6-aee8-a537f98e4253.jpg?v=1762495087', 'image_alt': '', 'image_id': 36689198874693}, {'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/04_eaee19f5-d3d0-4d8d-875c-e4e6d9798754.jpg?v=1762495087', 'image_alt': '', 'image_id': 36638147313733}, {'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/06_28280523-2679-46d9-b6d2-c950d1e3a050.jpg?v=1762495087', 'image_alt': '', 'image_id': 36689197531205}, {'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/06_4062a332-1478-4c83-8616-66123b637a72.jpg?v=1762495087', 'image_alt': '', 'image_id': 36689197563973}, {'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/08_c9541cba-7904-4ae3-a1bd-5e88bc89d465.jpg?v=1762495087', 'image_alt': '', 'image_id': 36638147182661}, {'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/09_98ccb0c1-aee2-45ab-ac73-89e9a3b66a35.jpg?v=1762495087', 'image_alt': '', 'image_id': 36638147051589}, {'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/05_41a75feb-192b-4bb5-889e-eaa0714e736a.jpg?v=1762495087', 'image_alt': '', 'image_id': 36696799477829}, {'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/011_4b2cd3d6-f10a-48f7-add9-bf09b68b77be.jpg?v=1762495087', 'image_alt': '', 'image_id': 36689197105221}, {'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/07_X-CROSS_59f6abc4-2846-4bde-a098-e3844803442e.jpg?v=1762495087', 'image_alt': '', 'image_id': 36689197137989}, {'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/010_39363f82-dd1e-4539-90bb-232619331440.jpg?v=1762495087', 'image_alt': '', 'image_id': 36689197498437}, {'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/01_f60c6e80-6eae-46c6-8e49-6818068d6e88.jpg?v=1762495087', 'image_alt': '', 'image_id': 36662885449797}, {'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/01_56532f84-8f2c-46ba-871f-eac3d8be0d2e.jpg?v=1762495087', 'image_alt': '', 'image_id': 36696854822981}, {'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/01_ebc395d9-9da7-4fff-bfdd-6e49f30e9e6c.jpg?v=1762495087', 'image_alt': '', 'image_id': 36696873697349}, {'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/01_5e267867-f638-4dbe-83a8-2fea82cb2a6b.jpg?v=1762495087', 'image_alt': '', 'image_id': 38150929842245}, {'image_src': 'https://cdn.shopify.com/s/files/1/1515/7758/files/02_449c8fca-2ccc-4caa-9c37-0c24537282e8.jpg?v=1762140911', 'image_alt': '', 'image_id': 38150929940549}] | 否 |
| impressions | number | 271.05882352941177 | 否 |
| inventory_quantity | number | 195 | 否 |
| name | string | Flash Sale PISCIFUN® Lumicat E Catfish Rods 1 or 2-Piece Casting Rod or Spinning Rod | 否 |
| new_customer_fulfillment_costs | number | 0 | 否 |
| new_customer_orders | number | 0 | 否 |
| new_customer_revenue | number | 0 | 否 |
| new_customer_total_items_sold | number | 0 | 否 |
| new_customer_total_order_value | number | 0 | 否 |
| number_of_ads | number | 3 | 否 |
| orders | number | 1 | 否 |
| product_id | string | 7924793049157 | 否 |
| product_image_url | string | https://cdn.shopify.com/s/files/1/1515/7758/files/02_3bea92ca-d8de-4cdf-a7e3-db091a395a62.jpg?v=1762495087 | 否 |
| product_name | string | Flash Sale PISCIFUN® Lumicat E Catfish Rods 1 or 2-Piece Casting Rod or Spinning Rod | 否 |
| product_status | string | active | 否 |
| product_tags | array | [] | 否 |
| product_title | string | Flash Sale PISCIFUN® Lumicat E Catfish Rods 1 or 2-Piece Casting Rod or Spinning Rod | 否 |
| repeat_customer | number | 0 | 否 |
| returns | null |  | 是 |
| revenue | number | 80.99 | 否 |
| shop_id | string | piscifun.myshopify.com | 否 |
| shop_name | string | piscifun | 否 |
| sku | string |  | 否 |
| spend | number | 1.7611765020033892 | 否 |
| title | string | Flash Sale PISCIFUN® Lumicat E Catfish Rods 1 or 2-Piece Casting Rod or Spinning Rod | 否 |
| total_items_sold | number | 1 | 否 |
| total_order_value | number | 130.76 | 否 |
| variant_id | null |  | 是 |
| variant_name | null |  | 是 |
| variant_title | null |  | 是 |
| vendor | string | Piscifun | 否 |
| visits | number | 10.529411764705882 | 否 |

---

## 接口：pixel_keywords_joined_tvf

**生成时间：** 2026-04-08 16:11:52

**样本记录数：** 1

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| account_id | string | 1773257068 | 否 |
| ad_study_cell_id | null |  | 是 |
| ad_study_end_date | null |  | 是 |
| ad_study_id | null |  | 是 |
| ad_study_integration_id | null |  | 是 |
| ad_study_name | null |  | 是 |
| ad_study_objective_id | null |  | 是 |
| ad_study_start_date | null |  | 是 |
| add_to_carts | null |  | 是 |
| addresses | null |  | 是 |
| adset_bid_amount | number | 70 | 否 |
| adset_bid_strategy | string | MAXIMIZE_CONVERSION_VALUE | 否 |
| adset_id | string | 111863109324 | 否 |
| adset_name | string | Carbon | 否 |
| adset_status | string | ACTIVE | 否 |
| attribution_window | string | lifetime | 否 |
| book_demos | null |  | 是 |
| bounces | null |  | 是 |
| campaign_bid_strategy | string | MAXIMIZE_CONVERSION_VALUE | 否 |
| campaign_id | string | 11234696296 | 否 |
| campaign_name | string | CPC_Search_品类 | 否 |
| campaign_status | string | ACTIVE | 否 |
| channel | string | google-ads | 否 |
| channel_reported_all_conversions | number | 0 | 否 |
| channel_reported_conversion_value | number | 0 | 否 |
| channel_type | null |  | 是 |
| checkouts | null |  | 是 |
| click_orders | number | 0 | 否 |
| click_revenue | number | 0 | 否 |
| clicks | number | 0 | 否 |
| cogs | number | 0 | 否 |
| contacts | null |  | 是 |
| cost_of_goods | number | 0 | 否 |
| custom_combined_gross_profit | number | 0 | 否 |
| custom_combined_gross_sales | number | 0 | 否 |
| custom_combined_net_revenue | number | 0 | 否 |
| custom_expenses | number | 0 | 否 |
| custom_gross_profit | number | 0 | 否 |
| custom_gross_sales | number | 0 | 否 |
| custom_net_revenue | number | 0 | 否 |
| custom_orders_quantity | number | 0 | 否 |
| custom_total_items_quantity | number | 0 | 否 |
| delivered | null |  | 是 |
| discount_codes | array | [] | 否 |
| email_signups | null |  | 是 |
| event_date | string | 2026-04-08 | 否 |
| experiment_CPIC | null |  | 是 |
| experiment_CPIC_lower | null |  | 是 |
| experiment_CPIC_upper | null |  | 是 |
| experiment_conversions_incremental | null |  | 是 |
| experiment_conversions_incremental_lower | null |  | 是 |
| experiment_conversions_incremental_share_percent | null |  | 是 |
| experiment_conversions_incremental_upper | null |  | 是 |
| experiment_event_date | null |  | 是 |
| experiment_i_ROAS | null |  | 是 |
| experiment_i_ROAS_lower_bound | null |  | 是 |
| experiment_i_ROAS_upper_bound | null |  | 是 |
| experiment_incremental_conversions_confidence_percent | null |  | 是 |
| experiment_incremental_revenue_confidence_percent | null |  | 是 |
| experiment_revenue_incremental_share_percent | null |  | 是 |
| gross_product_sales | number | 0 | 否 |
| gross_sales | number | 0 | 否 |
| impressions | number | 5 | 否 |
| incremental_revenue_experiment | null |  | 是 |
| incremental_revenue_lower_bound_experiment | null |  | 是 |
| incremental_revenue_upper_bound_experiment | null |  | 是 |
| integration_id | string | 1773257068 | 否 |
| keyword_cpc_bid | null |  | 是 |
| keyword_effective_cpc_bid | number | 7000 | 否 |
| keyword_id | string | 651999988516 | 否 |
| keyword_match_type | string | BROAD | 否 |
| keyword_quality_score | null |  | 是 |
| keyword_status | string | ENABLED | 否 |
| keyword_system_serving_status | string | ELIGIBLE | 否 |
| keyword_text | string | carbon x reel | 否 |
| leads | null |  | 是 |
| links | array | [] | 否 |
| marked_as_spam | null |  | 是 |
| message_subject | null |  | 是 |
| message_template_html_url | null |  | 是 |
| model | string | Triple Attribution | 否 |
| mqls | null |  | 是 |
| new_customer_cogs | number | 0 | 否 |
| new_customer_gross_sales | number | 0 | 否 |
| new_customer_order_revenue | number | 0 | 否 |
| new_customer_orders | number | 0 | 否 |
| new_visitors | null |  | 是 |
| non_meta_facebook_orders | number | 0 | 否 |
| one_day_view_conversion_value | number | 0 | 否 |
| one_day_view_purchases | number | 0 | 否 |
| opened | null |  | 是 |
| opportunities | null |  | 是 |
| order_revenue | number | 0 | 否 |
| orders_quantity | number | 0 | 否 |
| original_provider_id | string | google-ads | 否 |
| payments | null |  | 是 |
| product_quantity_sold_in_order | number | 0 | 否 |
| provider_id | string | google-ads | 否 |
| received | null |  | 是 |
| recipients | null |  | 是 |
| refund_money | number | 0 | 否 |
| sent | null |  | 是 |
| session_page_views | null |  | 是 |
| sessions | null |  | 是 |
| seven_day_view_conversion_value | number | 0 | 否 |
| seven_day_view_purchases | number | 0 | 否 |
| shipping | null |  | 是 |
| shop_id | null |  | 是 |
| shop_name | null |  | 是 |
| spend | number | 0 | 否 |
| spend_experiment | null |  | 是 |
| sqls | null |  | 是 |
| subscribed_to_list | null |  | 是 |
| subscription_id_canceled_only_first | null |  | 是 |
| subscription_id_cancelled | null |  | 是 |
| subscription_id_signed | null |  | 是 |
| subscription_quantity | number | 0 | 否 |
| subscriptions_arr | number | 0 | 否 |
| time_on_site | null |  | 是 |
| unique_visitors | null |  | 是 |
| unsubscribed | null |  | 是 |
| view_orders | number | 0 | 否 |
| view_revenue | number | 0 | 否 |
| website_purchases | number | 0 | 否 |

---

## 接口：ads_table

**生成时间：** 2026-04-08 16:11:56

**样本记录数：** 1

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| account_id | string | 1773257068 | 否 |
| actions | array | [] | 否 |
| ad_ai_recommendation | array | ['', '', '', ''] | 否 |
| ad_ai_roas_pacing | array | ['', '', '', ''] | 否 |
| ad_bid_amount | null |  | 是 |
| ad_copies | array | [] | 否 |
| ad_copy | null |  | 是 |
| ad_id | string |  | 否 |
| ad_image_url | null |  | 是 |
| ad_name | string | SEARCH_CAMPAIGN | 否 |
| ad_post_id | null |  | 是 |
| ad_status | string | ACTIVE | 否 |
| ad_title | null |  | 是 |
| ad_titles | array | [] | 否 |
| ad_type | null |  | 是 |
| adset_ai_recommendation | array | ['', '', '', ''] | 否 |
| adset_ai_roas_pacing | array | ['', '', '', ''] | 否 |
| adset_bid_amount | number | 45 | 否 |
| adset_bid_strategy | string | MAXIMIZE_CONVERSION_VALUE | 否 |
| adset_daily_budget | null |  | 是 |
| adset_id | string | 111857950232 | 否 |
| adset_lifetime_budget | null |  | 是 |
| adset_name | string | DSA | 否 |
| adset_status | string | ACTIVE | 否 |
| adset_target_cpa | number | 12 | 否 |
| adset_target_roas | number | 12 | 否 |
| adset_targeting | null |  | 是 |
| all_conversion_value | number | 0 | 否 |
| all_conversions | number | 0 | 否 |
| amazon_marketplace_id | null |  | 是 |
| amazon_report_type | null |  | 是 |
| asin | null |  | 是 |
| asset_id | null |  | 是 |
| asset_type | null |  | 是 |
| breakdown_country_name | null |  | 是 |
| campaign_ai_recommendation | array | ['', '', '', ''] | 否 |
| campaign_ai_roas_pacing | array | ['', '', '', ''] | 否 |
| campaign_bid_strategy | string | MAXIMIZE_CONVERSION_VALUE | 否 |
| campaign_created_at | null |  | 是 |
| campaign_daily_budget | number | 30000 | 否 |
| campaign_id | string | 11234696296 | 否 |
| campaign_lifetime_budget | null |  | 是 |
| campaign_name | string | CPC_Search_品类 | 否 |
| campaign_status | string | ACTIVE | 否 |
| campaign_sub_type | null |  | 是 |
| campaign_target_cpa | null |  | 是 |
| campaign_target_roas | number | 12 | 否 |
| campaign_type | string | SEARCH | 否 |
| channel | string | google-ads | 否 |
| channel_ai_recommendation | array | ['', '', '', ''] | 否 |
| channel_ai_roas_pacing | array | ['', '', '', ''] | 否 |
| clicks | number | 0 | 否 |
| complete_payment | null |  | 是 |
| conversion_value | number | 0 | 否 |
| conversions | number | 0 | 否 |
| creative_cta_type | null |  | 是 |
| creative_distribution_format | null |  | 是 |
| creative_format | null |  | 是 |
| creative_id | null |  | 是 |
| currency | string | USD | 否 |
| currency_rate | number | 1 | 否 |
| destination_url | string |  | 否 |
| engagements | number | 0 | 否 |
| event_date | string | 2026-03-30 | 否 |
| event_hour | number | 0 | 否 |
| follows | number | 0 | 否 |
| i_revenue | null |  | 是 |
| i_roas | null |  | 是 |
| impressions | number | 0 | 否 |
| inline_post_engagement | null |  | 是 |
| integration_id | string | 1773257068 | 否 |
| is_utm_valid | null |  | 是 |
| meta_conversion_value | number | 0 | 否 |
| meta_purchases | number | 0 | 否 |
| non_tracked_spend | number | 0 | 否 |
| on_web_order | null |  | 是 |
| one_day_click_comments | number | 0 | 否 |
| one_day_click_conversion_value | number | 0 | 否 |
| one_day_click_likes | number | 0 | 否 |
| one_day_click_link_clicks | number | 0 | 否 |
| one_day_click_purchases | number | 0 | 否 |
| one_day_click_reactions | number | 0 | 否 |
| one_day_click_shares | number | 0 | 否 |
| one_day_view_conversion_value | number | 0 | 否 |
| one_day_view_purchases | number | 0 | 否 |
| onsite_conversion_value | number | 0 | 否 |
| onsite_one_day_click_conversion_value | number | 0 | 否 |
| onsite_one_day_click_purchases | number | 0 | 否 |
| onsite_one_day_view_conversion_value | number | 0 | 否 |
| onsite_one_day_view_purchases | number | 0 | 否 |
| onsite_purchases | number | 0 | 否 |
| onsite_seven_day_click_conversion_value | number | 0 | 否 |
| onsite_seven_day_click_purchases | number | 0 | 否 |
| onsite_seven_day_view_conversion_value | number | 0 | 否 |
| onsite_seven_day_view_purchases | number | 0 | 否 |
| onsite_twenty_eight_day_click_conversion_value | number | 0 | 否 |
| onsite_twenty_eight_day_click_purchases | number | 0 | 否 |
| onsite_twenty_eight_day_view_conversion_value | number | 0 | 否 |
| onsite_twenty_eight_day_view_purchases | number | 0 | 否 |
| outbound_clicks | number | 0 | 否 |
| reach | null |  | 是 |
| search_absolute_top_impression_share | number | 0 | 否 |
| search_absolute_top_impressions | number | 0 | 否 |
| search_budget_lost_absolute_top_impression_share | number | 0 | 否 |
| search_budget_lost_absolute_top_impressions | number | 0 | 否 |
| search_budget_lost_top_impression_share | number | 0 | 否 |
| search_budget_lost_top_impressions | number | 0 | 否 |
| search_impression_share | number | 0 | 否 |
| search_impressions | number | 0 | 否 |
| search_rank_lost_impression_share | number | 0 | 否 |
| search_rank_lost_impressions | number | 0 | 否 |
| search_rank_lost_top_impression_share | number | 0 | 否 |
| search_rank_lost_top_impressions | number | 0 | 否 |
| search_top_impression_share | number | 0 | 否 |
| search_top_impressions | number | 0 | 否 |
| seven_day_click_comments | number | 0 | 否 |
| seven_day_click_conversion_value | number | 0 | 否 |
| seven_day_click_likes | number | 0 | 否 |
| seven_day_click_link_clicks | number | 0 | 否 |
| seven_day_click_purchases | number | 0 | 否 |
| seven_day_click_reactions | number | 0 | 否 |
| seven_day_click_shares | number | 0 | 否 |
| seven_day_view_conversion_value | number | 0 | 否 |
| seven_day_view_purchases | number | 0 | 否 |
| shop_id | null |  | 是 |
| shop_name | null |  | 是 |
| spend | number | 0 | 否 |
| suggested_budget | null |  | 是 |
| three_second_video_view | number | 0 | 否 |
| thruplays | null |  | 是 |
| total_complete_payment_rate | number | 0 | 否 |
| total_on_web_order_value | number | 0 | 否 |
| total_video_view | null |  | 是 |
| twenty_eight_day_click_conversion_value | number | 0 | 否 |
| twenty_eight_day_click_link_clicks | number | 0 | 否 |
| twenty_eight_day_click_purchases | number | 0 | 否 |
| twenty_eight_day_view_conversion_value | number | 0 | 否 |
| twenty_eight_day_view_purchases | number | 0 | 否 |
| url_template | null |  | 是 |
| video_duration | null |  | 是 |
| video_p100_watched | number | 0 | 否 |
| video_p25_watched | number | 0 | 否 |
| video_p50_watched | number | 0 | 否 |
| video_p75_watched | number | 0 | 否 |
| video_p95_watched | number | 0 | 否 |
| video_url | null |  | 是 |
| video_url_iframe | null |  | 是 |
| video_url_source | null |  | 是 |
| visits | number | 0 | 否 |
| weight | number | 1 | 否 |

---

## 接口：social_media_comments_table

**生成时间：** 2026-04-08 16:11:58

**样本记录数：** 1

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| account_id | string | 869728316447140 | 否 |
| channel | string | meta-analytics | 否 |
| comment_id | string | 1137422478597595_25123754527274812 | 否 |
| comment_text | string | I'm thinking about buying some of these. What line are you guys using? | 否 |
| created_at | string | 2025-12-04 00:37:09 | 否 |
| integration_id | string | c7b7e0c3-dd09-469b-87cc-906165fc434f | 否 |
| page_id | string | 869728316447140 | 否 |
| post_id | string | 869728316447140_1137422478597595 | 否 |
| risk | string | low | 否 |
| sentiment | string | neutral | 否 |
| topic | string | question | 否 |
| user_id | string | 6964598016947027 | 否 |
| visibility_changed_at | string | 2025-12-04 00:37:09 | 否 |
| visibility_changed_by | string |  | 否 |
| visibility_status | string |  | 否 |

---

## 接口：social_media_pages_table

**生成时间：** 2026-04-08 16:12:00

**样本记录数：** 1

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| about | string | Piscifun, a Professional Brand of fishing tackle, including fishing reels, rods and accessories.  We offer great fishing gear at an affordable price with excellent Custom Service! | 否 |
| category | string | Fishing Store | 否 |
| channel | string | meta-analytics | 否 |
| cover_url | string | https://scontent-ord5-3.xx.fbcdn.net/v/t39.30808-6/539424799_1084919173847926_4937721089198745518_n.jpg?_nc_cat=107&ccb=1-7&_nc_sid=dc4938&_nc_ohc=2-xVAwvqMmkQ7kNvwHZVB-I&_nc_oc=AdmgdVf1MWXPN6EladiIWBcICr5xPLMGjJSyBMNa1xKEPicc_XQwtMZZu9H-tSYBaI8&_nc_zt=23&_nc_ht=scontent-ord5-3.xx&edm=AJdBtusEAAAA&_nc_gid=p3X-AXUhtOQV-QQc38Nibw&_nc_tpa=Q5bMBQFL3XQixdCUsScr_abe-Kp-HNCLjFumlmMcR3y-q4b2H-95Yx8joerAcVFwtUwVXDmjS9QrMPn7GQ&oh=00_AfuETkdmSp-EwIojTUNeVC1PAo58e7d7fzh17T5rwUJ8kA&oe=6985F553 | 否 |
| event_date | string | 2026-04-06 | 否 |
| fan_adds | number | 33 | 否 |
| fan_removes | number | 6 | 否 |
| image_url | string | https://scontent-ord5-3.xx.fbcdn.net/v/t39.30808-1/415005887_672024161804098_1318847427524706965_n.jpg?stp=dst-jpg_s720x720_tt6&_nc_cat=106&ccb=1-7&_nc_sid=79bf43&_nc_ohc=GVgUBRUB3zEQ7kNvwGsFjTm&_nc_oc=AdmfoNgTeQh5koqN8sjdbUJN9PlsGieymBZSD0Vw53E1XYG7-H728Y4onu6YiL_hrFo&_nc_zt=24&_nc_ht=scontent-ord5-3.xx&edm=AJdBtusEAAAA&_nc_gid=p3X-AXUhtOQV-QQc38Nibw&_nc_tpa=Q5bMBQFXG8qGrLGC8zokR9N9t0qyyx5gGs7Hd1haMvgYR2ayE1x0SzuMeZ_9U1jIuX_WRj1dtDEFwQGX1g&oh=00_AftMaotNj1-eyK1bHTWqM4_CQ8ork_mFEnbzdHcV6AxgZQ&oe=6985E4A9 | 否 |
| impressions | number | 249738 | 否 |
| impressions_paid | null |  | 是 |
| impressions_unique | null |  | 是 |
| impressions_viral | null |  | 是 |
| page_id | string | 869728316447140 | 否 |
| page_name | string | Piscifun | 否 |
| page_permalink | string | https://www.facebook.com/869728316447140 | 否 |
| video_views | number | 19939 | 否 |
| views_total | number | 924 | 否 |
| website | string | https://linktr.ee/Piscifun | 否 |

---

## 接口：creatives_table

**生成时间：** 2026-04-08 16:12:05

**样本记录数：** 1

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| account_id | string | act_447339210551911 | 否 |
| ad_copies | array | [] | 否 |
| ad_copy | null |  | 是 |
| ad_id | string | 120225644298550499 | 否 |
| ad_image_url | string | https://storage.googleapis.com/file-hosting-bucket-shofifi/thumbnails/facebook-ads/act_447339210551911/297297039842891.jpg | 否 |
| ad_title | string | Don't Miss Out on This Deal! 🔥 30% OFF the Piscifun Carbon X 🐟 Lightweight ✨ Smooth 💪 Powerful | 否 |
| ad_titles | array | [] | 否 |
| ad_type | string | video | 否 |
| asset_id | string | 297297039842891 | 否 |
| asset_type | string | video | 否 |
| attribution_window | string | lifetime | 否 |
| channel | string | facebook-ads | 否 |
| channel_reported_conversion_value | number | 0 | 否 |
| channel_reported_conversions | number | 0 | 否 |
| channel_reported_onsite_conversion_value | number | 0 | 否 |
| channel_reported_onsite_purchases | number | 0 | 否 |
| channel_reported_visits | number | 0 | 否 |
| clicks | number | 57 | 否 |
| cost_of_goods | number | 0 | 否 |
| creative_cta_type | null |  | 是 |
| creative_distribution_format | null |  | 是 |
| creative_format | null |  | 是 |
| creative_id | string | 1202936074964251 | 否 |
| destination_url | string |  | 否 |
| event_date | string | 2026-04-07 | 否 |
| gross_product_sales | number | 0 | 否 |
| impressions | number | 2028 | 否 |
| meta_conversion_value | number | 0 | 否 |
| meta_facebook_orders | number | 0 | 否 |
| model | string | Triple Attribution | 否 |
| new_customer_cogs | number | 0 | 否 |
| new_customer_order_revenue | number | 0 | 否 |
| new_customer_orders | number | 0 | 否 |
| non_meta_facebook_orders | number | 0 | 否 |
| non_tracked_spend | number | 0 | 否 |
| number_of_ads | number | 1 | 否 |
| one_day_view_conversion_value | number | 86.51000213623047 | 否 |
| one_day_view_purchases | number | 1 | 否 |
| order_revenue | number | 0 | 否 |
| orders_quantity | number | 0 | 否 |
| outbound_clicks | number | 20 | 否 |
| seven_day_view_conversion_value | number | 0 | 否 |
| seven_day_view_purchases | number | 0 | 否 |
| shop_id | null |  | 是 |
| shop_name | null |  | 是 |
| spend | number | 14.050000190734863 | 否 |
| three_second_video_view | number | 290 | 否 |
| thruplays | number | 66 | 否 |
| total_video_view | number | 1387 | 否 |
| url_template | string | utm_source=facebook&utm_medium=paid&utm_campaign={{campaign.name}}&utm_term={{adset.name}}&utm_content={{ad.name}}&fbadid={{ad.id}} | 否 |
| video_duration | number | 21 | 否 |
| video_p100_watched | number | 39 | 否 |
| video_p25_watched | number | 180 | 否 |
| video_p50_watched | number | 102 | 否 |
| video_p75_watched | number | 63 | 否 |
| video_p95_watched | number | 42 | 否 |
| video_url | string | https://files.triplewhale.com/videos/facebook-ads/act_447339210551911/297297039842891.mp4 | 否 |
| website_purchases | number | 0 | 否 |

---

## 接口：ai_visibility_table

**生成时间：** 2026-04-08 16:12:07

**样本记录数：** 0

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|

---

## 数据概况（TripleWhale 专属）

| 表名 | 日期列 | 最早数据日期 | 总行数 | Rate Limit (RPM) | 每次最大行数 | 全量拉取预估时长 |
|------|--------|-------------|--------|-----------------|------------|----------------|
| pixel_orders_table | created_at | 2022-03-21 08:12:15 | 346122 | 60 | 1000 | 5.78 min |
| pixel_joined_tvf | event_date | 2021-12-05 | 340302 | 60 | 1000 | 5.68 min |
| sessions_table | event_date | 2023-12-03 | 10678877 | 60 | 1000 | 177.98 min |
| product_analytics_tvf | event_date | 2022-03-21 | 34786 | 60 | 1000 | 0.58 min |
| pixel_keywords_joined_tvf | event_date | 2023-07-18 | 70558 | 60 | 1000 | 1.18 min |
| ads_table | event_date | 2021-12-05 | 299878 | 60 | 1000 | 5.00 min |
| social_media_comments_table | created_at | 2025-09-28 19:45:04 | 1926 | 60 | 1000 | 0.03 min |
| social_media_pages_table | event_date | 2026-01-04 | 95 | 60 | 1000 | 0.02 min |
| creatives_table | event_date | 2022-05-13 | 86277 | 60 | 1000 | 1.45 min |
| ai_visibility_table | event_date | 1970-01-01 | 0 | 60 | 1000 | - |
