#!/usr/bin/env python3
"""
lazy-teacher v2.0.2 - DB connection & settings model
"""
from app import create_app
from app.models.setting import db, Setting

app = create_app()

@app.route('/')
def index():
    return {"status": "running", "version": "2.0.2", "db_ready": True}

@app.route('/db/test')
def db_test():
    """Тестовый маршрут: запись/чтение из БД"""
    try:
        test_key = 'v2.0.2_ping'
        # Проверяем, есть ли запись, если нет - создаём
        setting = Setting.query.filter_by(setting_key=test_key).first()
        if not setting:
            setting = Setting(
                setting_key=test_key,
                setting_value='ok',
                description='Проверка подключения к БД'
            )
            db.session.add(setting)
        else:
            setting.setting_value = 'ok'
        db.session.commit()

        # Читаем обратно
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