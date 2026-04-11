import os

class Config:
    # Используем localhost для подключения через Unix-сокет (надежнее чем 127.0.0.1)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://lt_user:LazyPass2024!@localhost/lazy_teacher_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'lt-dev-key-change-me')
