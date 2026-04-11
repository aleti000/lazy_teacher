from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Экспортируем объект db, чтобы избежать циклических импортов
db = SQLAlchemy()

class Setting(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    setting_value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'key': self.setting_key,
            'value': self.setting_value,
            'description': self.description
        }

    def __repr__(self):
        return f"<Setting {self.setting_key}={self.setting_value}>"