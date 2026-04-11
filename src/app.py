#!/usr/bin/env python3
"""
lazy-teacher v2.0.0 - Project skeleton
"""
import os
from flask import Flask

app = Flask(__name__)
app.config.from_prefixed_env()  # Загрузка переменных окружения FLASK_*

@app.route('/')
def index():
    return {
        "service": "lazy-teacher",
        "version": "2.0.0",
        "status": "running",
        "message": "Скелет проекта инициализирован успешно"
    }

if __name__ == '__main__':
    # Для разработки: хост 0.0.0.0, порт 5000
    app.run(host='0.0.0.0', port=5000, debug=True)