db = db.getSiblingDB('task_tracker');

db.tasks.createIndex({ "status": 1 });
db.tasks.createIndex({ "priority": 1 });
db.tasks.createIndex({ "assignee_id": 1 });
db.tasks.createIndex({ "creator_id": 1 });

db.tasks.insertMany([
    {
        title: "Тестовая задача 1",
        description: "Описание тестовой задачи 1",
        status: "todo",
        priority: "medium",
        created_at: new Date(),
        updated_at: new Date(),
        due_date: "2025-04-15",
        creator_id: 1
    },
    {
        title: "Тестовая задача 2",
        description: "Описание тестовой задачи 2",
        status: "in_progress",
        priority: "high",
        created_at: new Date(),
        updated_at: new Date(),
        due_date: "2025-04-20",
        creator_id: 1
    }
]);