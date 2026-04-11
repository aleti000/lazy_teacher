#!/usr/bin/env python3
"""Независимый тест подключения к БД без запуска Flask"""
import pymysql
import os

DB_CONF = {
    'host': '127.0.0.1',
    'user': 'lt_user',
    'password': os.environ.get('DB_PASS', 'LazyPass2024!'),
    'database': 'lazy_teacher_db',
    'charset': 'utf8mb4'
}

print("🔍 Тест подключения к MariaDB...")
try:
    conn = pymysql.connect(**DB_CONF)
    with conn.cursor() as cur:
        cur.execute("SELECT 1 AS connection_test")
        res = cur.fetchone()
        print(f"✅ Соединение установлено. SELECT 1 = {res}")
        
        cur.execute("SHOW TABLES LIKE 'settings'")
        tbl = cur.fetchone()
        print(f"📊 Таблица 'settings': {'✅ найдена' if tbl else '❌ не найдена'}")
    conn.close()
    print("🟢 Тест успешно пройден.")
except Exception as e:
    print(f"🔴 Ошибка: {e}")
    exit(1)