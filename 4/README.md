# Task Tracker API

![Python](https://img.shields.io/badge/Python-3.9-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95.0-green)
![Docker](https://img.shields.io/badge/Docker-supported-blue)

RESTful API для управления задачами с JWT-аутентификацией, построенное на FastAPI.

## ✨ Особенности
- Аутентификация через JWT
- Управление задачами (создание, просмотр, обновление)
- Приоритизация и статусы задач
- Контейнеризация через Docker

## 🛠 Технологический стек
- **Python 3.9** - основа приложения
- **FastAPI** - высокопроизводительный веб-фреймворк
- **JWT** - безопасная аутентификация
- **Docker** - контейнеризация
- **OpenAPI 3.0** - спецификация API
- **PostgreSQL 14** - реляционная база данных

## 📋 Требования
- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)

## 🚀 Быстрый старт

1. Запустите приложение:
docker-compose up --build

2. Сервисы будут доступны:
- **Auth Service**: `http://localhost:8000`
- **Task Service**: `http://localhost:8001`

## 📡 Основные эндпоинты

### 🔐 Auth Service (`http://localhost:8000`)

#### Информация о пользователе
GET /auth/users/me
Authorization: Bearer <ваш_токен>

### 📝 Task Service (`http://localhost:8001`)
#### Создание задачи
POST /tasks/
Authorization: Bearer <ваш_токен>
Content-Type: application/json

{
  "title": "Сделать презентацию",
  "description": "Подготовить слайды к митапу",
  "priority": "high",
  "due_date": "2024-06-01"
}

**Поля:**
| Поле          | Тип     | Обязательное | Значения                   |
|---------------|---------|--------------|----------------------------|
| title         | string  | ✓            | max 100 символов          |
| description   | string  | ✓            | -                         |
| priority      | string  |              | "low", "medium", "high"   |
| due_date      | date    |              | YYYY-MM-DD                |
| assignee_id   | integer |              | ID пользователя           |

#### Список задач
GET /tasks/
Authorization: Bearer <ваш_токен>

#### Обновление задачи
PUT /tasks/{task_id}
Authorization: Bearer <ваш_токен>
Content-Type: application/json

{
  "status": "in_progress",
  "priority": "medium"
}

## 🔑 Данные мастер-пользователя
- **Логин**: `admin`
- **Пароль**: `secret`

Спецификация OpenAPI: `openapi.yml`


## ⚙️ Технические детали
- JWT-аутентификация с Bearer токенами
- Поддержка методов GET/POST/PUT
- Валидация через Pydantic
- Хранение данных в postgreSQL
- Запуск через Docker Compose

## 🏗 Архитектура
Два микросервиса:
1. **Auth Service**: управление пользователями и токенами
2. **Task Service**: CRUD операции с задачами

Схема: `workspace.dsl` (Structurizr DSL)

## 📜 Коды ответов
| Код | Описание              |
|-----|-----------------------|
| 200 | Успешно               |
| 201 | Создано               |
| 400 | Неверный запрос       |
| 401 | Не авторизован        |
| 403 | Доступ запрещен       |
| 404 | Не найдено            |
| 422 | Ошибка валидации      |