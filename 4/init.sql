-- Подключение к базе данных (уже создана через POSTGRES_DB)
-- \c task_tracker; -- Эта строка не нужна в Docker, так как скрипт выполняется в контексте указанной базы

-- Создание таблицы пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(100),
    role VARCHAR(20) NOT NULL CHECK (role IN ('client', 'admin', 'executor')),
    hashed_password VARCHAR(255) NOT NULL,
    disabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индекса для поиска по username
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_users_username') THEN
        CREATE INDEX idx_users_username ON users (username);
    END IF;
END $$;

-- Создание таблицы задач
CREATE TABLE IF NOT EXISTS tasks (
    task_id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('todo', 'in_progress', 'done', 'cancelled')),
    priority VARCHAR(20) NOT NULL CHECK (priority IN ('low', 'medium', 'high')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_date DATE,
    assignee_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    creator_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE
);

-- Создание индексов для поиска по статусу и приоритету
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_tasks_status') THEN
        CREATE INDEX idx_tasks_status ON tasks (status);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_tasks_priority') THEN
        CREATE INDEX idx_tasks_priority ON tasks (priority);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_tasks_assignee_id') THEN
        CREATE INDEX idx_tasks_assignee_id ON tasks (assignee_id);
    END IF;
END $$;

-- Вставка тестовых данных (мастер-пользователь), если он еще не существует
INSERT INTO users (username, full_name, role, hashed_password)
SELECT 'admin', 'Master Administrator', 'admin', '$2b$12$C4e8jcxuZjpVAdTJ5IFQiOIOnRX1bTCNO/IN1Xa9Bn0GQXZuskFLC'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin');

-- Вставка тестовой задачи, если она еще не существует
INSERT INTO tasks (title, description, status, priority, due_date, creator_id)
SELECT 'Тестовая задача', 'Описание тестовой задачи', 'todo', 'medium', '2025-04-15', 1
WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE title = 'Тестовая задача');