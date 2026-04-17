#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Doris database connection"""
import sys
import os

# Add SDK path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bi', 'python_sdk', 'outdoor_collector'))

import pymysql
from doris_config import DorisConfig

def test_connection():
    """Test database connection"""
    config = DorisConfig()
    db_config = config.DB_CONFIG

    print("=" * 60)
    print("Doris Database Connection Test")
    print("=" * 60)
    print(f"Host: {db_config['host']}")
    print(f"Port: {db_config['port']}")
    print(f"User: {db_config['user']}")
    print(f"Database: {db_config['database']}")
    print("=" * 60)

    try:
        print("\nConnecting to database...")
        conn = pymysql.connect(**db_config)
        print("[OK] Connection successful!")

        # Test query
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"[OK] Doris version: {version[0]}")

            # List tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"[OK] Number of tables: {len(tables)}")
            if tables:
                print("  Tables:")
                for table in tables[:5]:
                    print(f"    - {table[0]}")
                if len(tables) > 5:
                    print(f"    ... and {len(tables) - 5} more tables")

        conn.close()
        print("\n[SUCCESS] All tests passed!")
        return True

    except pymysql.err.OperationalError as e:
        print(f"[FAILED] Connection error: {e}")
        print("\nTip: If connection fails, you may need to use SSH tunnel")
        print("Tunnel info:")
        print("  Host: 121.43.28.98")
        print("  Port: 22")
        print("  User: root")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
