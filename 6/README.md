# Task Tracker API

Task Tracker API — это микросервисное приложение для управления задачами. Оно состоит из трех основных сервисов: **Auth Service** (управление аутентификацией), **Task Service** (управление задачами) и **Task Consumer** (обработка событий задач). Проект использует PostgreSQL для хранения данных пользователей, MongoDB для хранения задач, Redis для кэширования, Kafka для асинхронной обработки событий и Docker для контейнеризации.

## О проекте

Проект разделен на три микросервиса:
- **Auth Service**: отвечает за аутентификацию и авторизацию пользователей. Использует PostgreSQL для хранения данных пользователей и Redis для кэширования.
- **Task Service**: отвечает за создание, чтение и обновление задач. Использует MongoDB для чтения задач, Redis для кэширования и Kafka для асинхронной обработки создания задач.
- **Task Consumer**: обрабатывает события создания задач из Kafka и сохраняет их в MongoDB.

Оба сервиса (`Auth Service` и `Task Service`) взаимодействуют через REST API, а `Task Service` зависит от `Auth Service` для проверки токенов JWT. Для создания задач реализован паттерн CQRS: `Task Service` публикует события в Kafka и кэширует задачи в Redis (write-through), а `Task Consumer` записывает данные в MongoDB.

## Технологии

- **FastAPI**: для создания REST API.
- **PostgreSQL**: база данных для Auth Service.
- **MongoDB**: база данных для Task Service и Task Consumer.
- **Redis**: кэширование данных пользователей и задач.
- **Kafka**: брокер сообщений для асинхронной обработки событий задач.
- **Zookeeper**: координация Kafka.
- **Docker**: для контейнеризации.

## Требования

- Docker и Docker Compose
- Python 3.9+

## Запуск

1. Убедитесь, что Docker и Docker Compose установлены.
2. Выполните команду `docker compose up` для запуска всех сервисов (PostgreSQL, MongoDB, Redis, Kafka, Zookeeper, Auth Service, Task Service, Task Consumer).
3. Используйте endpoint `/tasks/` для создания задач, которые будут кэшироваться в Redis и асинхронно записываться в MongoDB через Kafka.
