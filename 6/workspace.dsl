workspace {
    model {
        user = person "User"

        auth = softwareSystem "Authentication Service" "auth" {
            AuthApi = container "Auth API" "authApi" {
                description "Handles authentication"
                technology "FastAPI"
            }
        }

        task = softwareSystem "Task Service" "task" {
            TaskApi = container "Task API" "taskApi" {
                description "Manages tasks"
                technology "FastAPI"
            }
        }

        task_consumer = softwareSystem "Task Consumer Service" "taskConsumer" {
            TaskConsumer = container "Task Consumer" "taskConsumer" {
                description "Consumes task creation events from Kafka and saves to MongoDB"
                technology "Python"
            }
        }

        postgresql = softwareSystem "PostgreSQL" "postgresql" {
            AuthDb = container "Auth Database" "authDb" {
                description "Stores user data"
                technology "PostgreSQL 14"
            }
        }

        mongodb = softwareSystem "MongoDB" "mongodb" {
            TaskDb = container "Task Database" "taskDb" {
                description "Stores tasks"
                technology "MongoDB 5.0"
            }
        }

        redis = softwareSystem "Redis" "redis" {
            Cache = container "Cache" "cache" {
                description "Caches data"
                technology "Redis 7.0"
            }
        }

        kafka = softwareSystem "Kafka" "kafka" {
            description "Message broker for events"
        }

        zookeeper = softwareSystem "ZooKeeper" "zookeeper" {
            description "Coordinates Kafka"
        }

        // Relationships
        user -> auth.AuthApi "Uses for authentication"
        auth.AuthApi -> postgresql.AuthDb "Reads/writes user data"
        auth.AuthApi -> redis.Cache "Caches user data"
        user -> task.TaskApi "Manages tasks"
        task.TaskApi -> auth.AuthApi "Validates tokens"
        task.TaskApi -> redis.Cache "Caches tasks (write-through)"
        task.TaskApi -> kafka "Publishes task creation events"
        task.TaskApi -> mongodb.TaskDb "Reads tasks"
        task_consumer.TaskConsumer -> kafka "Consumes task creation events"
        task_consumer.TaskConsumer -> mongodb.TaskDb "Writes tasks"
        kafka -> zookeeper "Depends on"
    }
}