-- lazy-teacher v2 | Database Initialization
-- Совместимость: MySQL 8.0+ / MariaDB 10.2+
-- Запуск: mysql -u root -p < db/init.sql

CREATE DATABASE IF NOT EXISTS lazy_teacher_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'lt_user'@'localhost' IDENTIFIED BY 'LazyPass2024!';
GRANT ALL PRIVILEGES ON lazy_teacher_db.* TO 'lt_user'@'localhost';
FLUSH PRIVILEGES;

USE lazy_teacher_db;

CREATE TABLE IF NOT EXISTS settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    description VARCHAR(255),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Базовые настройки по умолчанию
INSERT IGNORE INTO settings (setting_key, setting_value, description) VALUES
('bridge_dynamic_start', '2000', 'Начальный номер для динамических мостов'),
('bridge_dynamic_end', '2999', 'Конечный номер для динамических мостов'),
('max_session_time', '3600', 'Максимальное время сессии в секундах'),
('pve_default_timeout', '60', 'Таймаут запросов к PVE API в секундах');