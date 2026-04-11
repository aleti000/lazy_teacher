import os
from flask import Flask
from .config import Config
from .models.setting import db

def create_app():
    app = Flask(__name__, template_folder='../templates')
    app.config.from_object(Config)

    # Инициализация SQLAlchemy
    db.init_app(app)

    # Создание таблиц при первом запуске (для разработки)
    with app.app_context():
        db.create_all()

    # Регистрация будущих blueprint-ов будет здесь
    # from .routes import admin_bp
    # app.register_blueprint(admin_bp, url_prefix='/admin')

    return app