workspace {
    model {
        user = person "User"
        
        auth = softwareSystem "Authentication Service" "auth" {
            AuthApi = container "Auth API" "authApi" {
                description "Handles authentication"
                technology "FastAPI"
            }
            AuthDb = container "Auth Database" "authDb" {
                description "Stores user data"
                technology "PostgreSQL"
            }
            AuthApi -> AuthDb "Reads/writes"
        }
        
        task = softwareSystem "Task Service" "task" {
            TaskApi = container "Task API" "taskApi" {
                description "Manages tasks"
                technology "FastAPI"
            }
            TaskDb = container "Task Database" "taskDb" {
                description "Stores tasks"
                technology "PostgreSQL"
            }
            TaskApi -> TaskDb "Reads/writes"
        }
        
        // Relationships
        user -> auth "Logs in"
        auth -> user "Returns JWT"
        
        user -> task "Creates task"
        task -> auth "Validates token"
        task -> user "Returns tasks"
    }
}