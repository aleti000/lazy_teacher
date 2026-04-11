import os
from flask import Flask
from .config import Config
from .models.setting import db

def create_app():
    app = Flask(__name__, template_folder='../templates')
    app.config.from_object(Config)
    
    # Инициализация БД
    db.init_app(app)
    
    # Создание таблиц при первом запуске
    with app.app_context():
        db.create_all()
        
    return app
