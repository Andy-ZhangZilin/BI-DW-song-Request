#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Initialize Doris test database tables for outdoor-data-validator"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bi', 'python_sdk', 'outdoor_collector'))

import pymysql
from doris_config import DorisConfig

# SQL statements to create all required tables
CREATE_TABLES_SQL = [
    "CREATE DATABASE IF NOT EXISTS hqware_test",

    # TripleWhale tables
    """CREATE TABLE IF NOT EXISTS hqware_test.ods_tw_pixel_orders (
        order_id VARCHAR(255),
        event_date DATE,
        channel VARCHAR(100),
        amount DECIMAL(18, 2),
        currency VARCHAR(10),
        created_at DATETIME,
        updated_at DATETIME
    ) ENGINE=OLAP UNIQUE KEY(order_id) DISTRIBUTED BY HASH(order_id) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_tw_pixel_joined (
        event_date DATE,
        channel VARCHAR(100),
        account_id VARCHAR(255),
        campaign_id VARCHAR(255),
        adset_id VARCHAR(255),
        ad_id VARCHAR(255),
        impressions BIGINT,
        clicks BIGINT,
        spend DECIMAL(18, 2)
    ) ENGINE=OLAP UNIQUE KEY(event_date, channel, account_id, campaign_id, adset_id, ad_id) DISTRIBUTED BY HASH(event_date) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_tw_sessions (
        session_id VARCHAR(255),
        event_date DATE,
        channel VARCHAR(100),
        duration_seconds INT,
        created_at DATETIME
    ) ENGINE=OLAP UNIQUE KEY(session_id) DISTRIBUTED BY HASH(session_id) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_tw_product_analytics (
        event_date DATE,
        entity VARCHAR(100),
        id VARCHAR(255),
        revenue DECIMAL(18, 2),
        units_sold INT
    ) ENGINE=OLAP UNIQUE KEY(event_date, entity, id) DISTRIBUTED BY HASH(event_date) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_tw_pixel_keywords_joined (
        event_date DATE,
        channel VARCHAR(100),
        keyword_id VARCHAR(255),
        impressions BIGINT,
        clicks BIGINT
    ) ENGINE=OLAP UNIQUE KEY(event_date, channel, keyword_id) DISTRIBUTED BY HASH(event_date) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_tw_ads (
        event_date DATE,
        channel VARCHAR(100),
        account_id VARCHAR(255),
        campaign_id VARCHAR(255),
        adset_id VARCHAR(255),
        ad_id VARCHAR(255),
        spend DECIMAL(18, 2),
        impressions BIGINT
    ) ENGINE=OLAP UNIQUE KEY(event_date, channel, account_id, campaign_id, adset_id, ad_id) DISTRIBUTED BY HASH(event_date) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_tw_social_media_comments (
        comment_id VARCHAR(255),
        post_id VARCHAR(255),
        author_id VARCHAR(255),
        content TEXT,
        created_at DATETIME
    ) ENGINE=OLAP UNIQUE KEY(comment_id) DISTRIBUTED BY HASH(comment_id) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_tw_social_media_pages (
        event_date DATE,
        page_id VARCHAR(255),
        channel VARCHAR(100),
        followers BIGINT,
        engagement_rate DECIMAL(5, 2)
    ) ENGINE=OLAP UNIQUE KEY(event_date, page_id, channel) DISTRIBUTED BY HASH(event_date) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_tw_creatives (
        event_date DATE,
        channel VARCHAR(100),
        ad_id VARCHAR(255),
        asset_id VARCHAR(255),
        creative_type VARCHAR(50),
        performance_score DECIMAL(5, 2)
    ) ENGINE=OLAP UNIQUE KEY(event_date, channel, ad_id, asset_id) DISTRIBUTED BY HASH(event_date) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_tw_ai_visibility (
        event_date DATE,
        visibility_score DECIMAL(5, 2),
        trend VARCHAR(20)
    ) ENGINE=OLAP UNIQUE KEY(event_date) DISTRIBUTED BY HASH(event_date) BUCKETS 10""",

    # TikTok tables
    """CREATE TABLE IF NOT EXISTS hqware_test.ods_tiktok_return_refund (
        return_id VARCHAR(255),
        order_id VARCHAR(255),
        create_time BIGINT,
        update_time BIGINT,
        return_type VARCHAR(50),
        return_status VARCHAR(50),
        refund_amount DECIMAL(18,4),
        currency VARCHAR(10),
        reason VARCHAR(500),
        etl_time DATETIME
    ) ENGINE=OLAP UNIQUE KEY(return_id) DISTRIBUTED BY HASH(return_id) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_tiktok_video_performances (
        video_id VARCHAR(255),
        collect_date DATE,
        video_title VARCHAR(500),
        views BIGINT,
        likes BIGINT,
        comments BIGINT,
        shares BIGINT,
        product_clicks BIGINT,
        product_impressions BIGINT,
        orders BIGINT,
        gmv_amount DECIMAL(18,4),
        gmv_currency VARCHAR(10),
        etl_time DATETIME
    ) ENGINE=OLAP UNIQUE KEY(video_id, collect_date) DISTRIBUTED BY HASH(video_id) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_tiktok_shop_product_performance (
        product_id VARCHAR(255),
        collect_date DATE,
        views BIGINT,
        clicks BIGINT,
        orders BIGINT,
        revenue DECIMAL(18,4),
        currency VARCHAR(10),
        conversion_rate DECIMAL(10,4),
        etl_time DATETIME
    ) ENGINE=OLAP UNIQUE KEY(product_id, collect_date) DISTRIBUTED BY HASH(product_id) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_tiktok_shop_video_performance_detail (
        video_id VARCHAR(255),
        collect_date DATE,
        latest_available_date VARCHAR(50),
        views BIGINT,
        likes BIGINT,
        comments BIGINT,
        shares BIGINT,
        customers BIGINT,
        gmv_amount DECIMAL(18,4),
        gmv_currency VARCHAR(10),
        etl_time DATETIME
    ) ENGINE=OLAP UNIQUE KEY(video_id, collect_date) DISTRIBUTED BY HASH(video_id) BUCKETS 10""",

    # DingTalk tables
    """CREATE TABLE IF NOT EXISTS hqware_test.ods_dingtalk_kol_tidwe_content (
        record_id VARCHAR(255),
        event_date DATE,
        content_url TEXT,
        content_type VARCHAR(50),
        created_at DATETIME
    ) ENGINE=OLAP UNIQUE KEY(record_id) DISTRIBUTED BY HASH(record_id) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_dingtalk_kol_tidwe_kol_info (
        kol_id VARCHAR(255),
        kol_name VARCHAR(255),
        followers BIGINT,
        engagement_rate DECIMAL(5, 2)
    ) ENGINE=OLAP UNIQUE KEY(kol_id) DISTRIBUTED BY HASH(kol_id) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_dingtalk_kol_tidwe_sample (
        sample_id VARCHAR(255),
        kol_id VARCHAR(255),
        sample_data TEXT
    ) ENGINE=OLAP UNIQUE KEY(sample_id) DISTRIBUTED BY HASH(sample_id) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_dingtalk_outdoor_material_analysis (
        material_id VARCHAR(255),
        event_date DATE,
        analysis_result TEXT
    ) ENGINE=OLAP UNIQUE KEY(material_id) DISTRIBUTED BY HASH(material_id) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_dingtalk_outdoor_params (
        param_id VARCHAR(255),
        param_name VARCHAR(255),
        param_value TEXT
    ) ENGINE=OLAP UNIQUE KEY(param_id) DISTRIBUTED BY HASH(param_id) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_dingtalk_outdoor_raw_material (
        material_id VARCHAR(255),
        event_date DATE,
        material_type VARCHAR(50),
        raw_data TEXT
    ) ENGINE=OLAP UNIQUE KEY(material_id) DISTRIBUTED BY HASH(material_id) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_dingtalk_outdoor_shoot_kol (
        shoot_id VARCHAR(255),
        kol_id VARCHAR(255),
        event_date DATE,
        shoot_status VARCHAR(50)
    ) ENGINE=OLAP UNIQUE KEY(shoot_id) DISTRIBUTED BY HASH(shoot_id) BUCKETS 10""",

    """CREATE TABLE IF NOT EXISTS hqware_test.ods_dingtalk_video_delivery (
        delivery_id VARCHAR(255),
        video_id VARCHAR(255),
        event_date DATE,
        delivery_status VARCHAR(50)
    ) ENGINE=OLAP UNIQUE KEY(delivery_id) DISTRIBUTED BY HASH(delivery_id) BUCKETS 10""",

    # AWIN table
    """CREATE TABLE IF NOT EXISTS hqware_test.ods_awin_transactions (
        transaction_id VARCHAR(255),
        event_date DATE,
        amount DECIMAL(18, 2),
        commission DECIMAL(18, 2),
        status VARCHAR(50)
    ) ENGINE=OLAP UNIQUE KEY(transaction_id) DISTRIBUTED BY HASH(transaction_id) BUCKETS 10""",

    # PartnerBoost table
    """CREATE TABLE IF NOT EXISTS hqware_test.ods_partnerboost_performance (
        performance_id VARCHAR(255),
        event_date DATE,
        impressions BIGINT,
        clicks BIGINT,
        conversions BIGINT,
        revenue DECIMAL(18, 2)
    ) ENGINE=OLAP UNIQUE KEY(performance_id) DISTRIBUTED BY HASH(performance_id) BUCKETS 10""",

    # YouTube table
    """CREATE TABLE IF NOT EXISTS hqware_test.ods_youtube_video_stats (
        video_id VARCHAR(255),
        event_date DATE,
        views BIGINT,
        likes BIGINT,
        comments BIGINT,
        shares BIGINT,
        duration_seconds INT,
        published_at DATETIME
    ) ENGINE=OLAP UNIQUE KEY(video_id) DISTRIBUTED BY HASH(video_id) BUCKETS 10""",

    # Watermark table for incremental sync
    """CREATE TABLE IF NOT EXISTS hqware_test.watermark (
        source VARCHAR(100),
        table_name VARCHAR(255),
        watermark_value VARCHAR(255),
        updated_at DATETIME
    ) ENGINE=OLAP UNIQUE KEY(source, table_name) DISTRIBUTED BY HASH(source) BUCKETS 10""",
]

def init_database():
    """Initialize all required tables in Doris test database"""
    config = DorisConfig()
    db_config = config.DB_CONFIG

    print("=" * 70)
    print("Doris Test Database Initialization")
    print("=" * 70)
    print(f"Host: {db_config['host']}")
    print(f"Port: {db_config['port']}")
    print(f"Database: {db_config['database']}")
    print("=" * 70)

    try:
        conn = pymysql.connect(**db_config)
        print("\n[OK] Connected to Doris")

        try:
            with conn.cursor() as cursor:
                for i, stmt in enumerate(CREATE_TABLES_SQL, 1):
                    try:
                        cursor.execute(stmt)
                        conn.commit()
                        # Extract table name
                        if 'CREATE TABLE' in stmt:
                            table_name = stmt.split('hqware_test.')[1].split('(')[0].strip()
                            print(f"[{i:2d}] Created table: {table_name}")
                        elif 'CREATE DATABASE' in stmt:
                            print(f"[{i:2d}] Database ready")
                    except Exception as e:
                        print(f"[ERROR] Statement {i} failed: {e}")
                        conn.rollback()
                        raise
        finally:
            conn.close()

        print("\n" + "=" * 70)
        print("[SUCCESS] All tables initialized successfully!")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n[FAILED] Initialization error: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
