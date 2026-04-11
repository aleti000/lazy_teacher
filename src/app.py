#!/usr/bin/env python3
"""lazy-teacher v2.0.2 - Entry point"""
import sys
import os

# Гарантируем, что корень проекта (/root/lazy_teacher) в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models.setting import db, Setting

app = create_app()

@app.route('/')
def index():
    return {"status": "running", "version": "2.0.2", "db_ready": True}

@app.route('/db/test')
def db_test():
    try:
        test_key = 'v2.0.2_ping'
        setting = Setting.query.filter_by(setting_key=test_key).first()
        if not setting:
            setting = Setting(setting_key=test_key, setting_value='ok', description='Проверка подключения к БД')
            db.session.add(setting)
        else:
            setting.setting_value = 'ok'
        db.session.commit()

        record = Setting.query.filter_by(setting_key=test_key).first()
        return {
            "status": "success",
            "message": "База данных подключена и работает",
            "record": record.to_dict()
        }
    except Exception as e:
        db.session.rollback()
        return {"status": "error", "message": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)