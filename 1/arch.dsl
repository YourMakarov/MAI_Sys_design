workspace {
    name "Планирование задач"
    description "Система управления пользователями, целями и задачами для достижения целей"

    !identifiers hierarchical

    model {
        admin = person "Администратор" {
            description "Управление пользователями, целями и задачами."
            tags "Person"
        }

        user = person "Пользователь" {
            description "Регистрация и управление профилем, создание целей и задач, отслеживание задач."
            tags "Person"
        }

        executor = person "Исполнитель" {
            description "Обновление статуса задач (например, 'в работе', 'выполнено')."
            tags "Person"
        }

        taskSystem = softwareSystem "Планирование задач" {
            description "Система управления пользователями, целями и задачами для достижения целей"

            apiGateway = container "API Gateway" {
                technology "Go, Gin"
                description "API-шлюз для маршрутизации запросов"
                tags "Backend"
            }

            webApp = container "Web Application" {
                technology "React, HTML, CSS, JavaScript"
                description "Веб-приложение для взаимодействия пользователей с системой"
                -> apiGateway "Передача запросов" "HTTPS/JSON"
                tags "Frontend"
            }

            userDb = container "User Database" {
                technology "PostgreSQL"
                description "База данных для хранения информации о пользователях"
                tags "Database"
            }

            goalDb = container "Goal Database" {
                technology "PostgreSQL"
                description "База данных для хранения информации о целях"
                tags "Database"
            }

            taskDb = container "Task Database" {
                technology "PostgreSQL"
                description "База данных для хранения информации о задачах"
                tags "Database"
            }

            messageBroker = container "Message Broker" {
                technology "RabbitMQ"
                description "Брокер сообщений для асинхронного взаимодействия между сервисами"
                tags "Messaging"
            }

            userService = container "User Service" {
                technology "Go, gRPC"
                description "Сервис управления пользователями (регистрация, поиск)"
                -> apiGateway "Запросы на управление пользователями" "HTTPS/JSON"
                -> userDb "Хранение информации о пользователях" "SQL"
                -> messageBroker "Публикация событий о пользователях" "AMQP"
                tags "Backend"
            }

            goalService = container "Goal Service" {
                technology "Go, gRPC"
                description "Сервис управления целями (создание, получение списка)"
                -> apiGateway "Запросы на управление целями" "HTTPS/JSON"
                -> goalDb "Хранение информации о целях" "SQL"
                -> messageBroker "Публикация событий о целях" "AMQP"
                tags "Backend"
            }

            taskService = container "Task Service" {
                technology "Go, gRPC"
                description "Сервис управления задачами (создание, изменение статуса, получение списка)"
                -> apiGateway "Запросы на управление задачами" "HTTPS/JSON"
                -> taskDb "Хранение информации о задачах" "SQL"
                -> messageBroker "Публикация событий о задачах" "AMQP"
                tags "Backend"
            }

            notificationService = container "Notification Service" {
                technology "Go"
                description "Сервис отправки уведомлений (SMS, email, push)"
                -> messageBroker "Получение событий для уведомлений" "AMQP"
                tags "Backend"
            }
        }

        authSystem = softwareSystem "Система аутентификации и авторизации" {
            description "Управление пользователями и их ролями. Обеспечение безопасности API."
            tags "ExternalSystem"
        }

        notificationGateway = softwareSystem "Система уведомлений" {
            description "Отправка уведомлений пользователям (SMS, email, push-уведомления) о статусе задач."
            tags "ExternalSystem"
        }

        calendarSystem = softwareSystem "Календарная система" {
            description "Синхронизация сроков задач с внешними календарями (Google Calendar, Outlook)."
            tags "ExternalSystem"
        }

        admin -> taskSystem.webApp "Управление пользователями, целями и задачами"
        user -> taskSystem.webApp "Регистрация, создание целей и задач, отслеживание задач"
        executor -> taskSystem.webApp "Обновление статуса задач"

        taskSystem.userService -> authSystem "Аутентификация и авторизация" "HTTPS/JSON"
        taskSystem.notificationService -> notificationGateway "Отправка уведомлений" "HTTPS/JSON"
        taskSystem.taskService -> calendarSystem "Синхронизация сроков задач" "HTTPS/JSON"
    }

    views {
        systemContext taskSystem "SystemContext" {
            include *
            autolayout lr
        }

        container taskSystem "Container" {
            include *
            autolayout lr
        }

        dynamic taskSystem "createUser" "Создание нового пользователя" {
            admin -> taskSystem.webApp "Создание нового пользователя"
            taskSystem.webApp -> taskSystem.apiGateway "POST /user"
            taskSystem.apiGateway -> taskSystem.userService "Создает запись в базе данных"
            taskSystem.userService -> taskSystem.userDb "INSERT INTO users"
            taskSystem.userService -> taskSystem.messageBroker "Публикует событие 'UserCreated'"
            taskSystem.messageBroker -> taskSystem.notificationService "Отправляет уведомление о создании"
            taskSystem.notificationService -> notificationGateway "Отправляет email/SMS"
            autolayout lr
        }

        dynamic taskSystem "searchUserByLogin" "Поиск пользователя по логину" {
            admin -> taskSystem.webApp "Поиск пользователя по логину"
            taskSystem.webApp -> taskSystem.apiGateway "GET /user?login={login}"
            taskSystem.apiGateway -> taskSystem.userService "Ищет пользователя в базе данных"
            taskSystem.userService -> taskSystem.userDb "SELECT * FROM users WHERE login={login}"
            autolayout lr
        }

        dynamic taskSystem "createGoal" "Создание новой цели" {
            user -> taskSystem.webApp "Создание новой цели"
            taskSystem.webApp -> taskSystem.apiGateway "POST /goal"
            taskSystem.apiGateway -> taskSystem.goalService "Создает запись о цели"
            taskSystem.goalService -> taskSystem.goalDb "INSERT INTO goals"
            taskSystem.goalService -> taskSystem.messageBroker "Публикует событие 'GoalCreated'"
            autolayout lr
        }

        dynamic taskSystem "createTask" "Создание новой задачи" {
            user -> taskSystem.webApp "Создание новой задачи"
            taskSystem.webApp -> taskSystem.apiGateway "POST /task"
            taskSystem.apiGateway -> taskSystem.taskService "Создает запись о задаче"
            taskSystem.taskService -> taskSystem.taskDb "INSERT INTO tasks"
            taskSystem.taskService -> taskSystem.messageBroker "Публикует событие 'TaskCreated'"
            taskSystem.messageBroker -> taskSystem.notificationService "Отправляет уведомление исполнителю"
            taskSystem.notificationService -> notificationGateway "Отправляет email/SMS"
            autolayout lr
        }

        dynamic taskSystem "updateTaskStatus" "Обновление статуса задачи" {
            executor -> taskSystem.webApp "Обновление статуса задачи"
            taskSystem.webApp -> taskSystem.apiGateway "PUT /task/{id}/status"
            taskSystem.apiGateway -> taskSystem.taskService "Обновляет статус задачи"
            taskSystem.taskService -> taskSystem.taskDb "UPDATE tasks SET status={status}"
            taskSystem.taskService -> taskSystem.messageBroker "Публикует событие 'TaskStatusUpdated'"
            taskSystem.messageBroker -> taskSystem.notificationService "Отправляет уведомление пользователю"
            taskSystem.notificationService -> notificationGateway "Отправляет email/SMS"
            autolayout lr
        }

        dynamic taskSystem "getTasksForGoal" "Получение всех задач цели" {
            user -> taskSystem.webApp "Просмотр задач для цели"
            taskSystem.webApp -> taskSystem.apiGateway "GET /goal/{id}/tasks"
            taskSystem.apiGateway -> taskSystem.taskService "Получает список задач"
            taskSystem.taskService -> taskSystem.taskDb "SELECT * FROM tasks WHERE goal_id={id}"
            autolayout lr
        }

        styles {
            element "Person" {
                shape Person
                background #08427b
                color #ffffff
            }
            element "Backend" {
                shape RoundedBox
                background #1168bd
                color #ffffff
            }
            element "Frontend" {
                shape WebBrowser
                background #438dd5
                color #ffffff
            }
            element "Database" {
                shape Cylinder
                background #85bbf0
                color #000000
            }
            element "Messaging" {
                shape Pipe
                background #ff8c00
                color #ffffff
            }
            element "ExternalSystem" {
                shape Box
                background #999999
                color #ffffff
            }
        }

        theme default
    }
}