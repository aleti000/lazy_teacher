#!/usr/bin/env python3
"""
lazy-teacher v2.0.1 - Basic Flask page
"""
import os
from flask import Flask, render_template

app = Flask(__name__, template_folder='templates')
app.config.from_prefixed_env()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin_stub():
    return render_template('index.html') # Заглушка для кнопки

if __name__ == '__main__':
    # Для разработки: хост 0.0.0.0, порт 5000
    app.run(host='0.0.0.0', port=5000, debug=True)