from fastapi import FastAPI, HTTPException, Depends, status, Request
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime, date
import logging
import os
from typing import List, Optional
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
DB_CONFIG = {
    "dbname": "task_tracker",
    "user": "postgres",
    "password": "postgres",
    "host": "postgres",
    "port": "5432"
}

class Role(str, Enum):
    CLIENT = "client"
    ADMIN = "admin"
    EXECUTOR = "executor"

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class UserPublic(BaseModel):
    user_id: int
    username: str
    full_name: Optional[str]
    role: Role

class Task(BaseModel):
    task_id: int
    title: str
    description: str
    status: TaskStatus = TaskStatus.TODO
    priority: Priority = Priority.MEDIUM
    created_at: datetime
    updated_at: datetime
    due_date: Optional[date] = None
    assignee_id: Optional[int] = None

class TaskCreate(BaseModel):
    title: str = Field(..., max_length=100)
    description: str
    priority: Priority = Priority.MEDIUM
    due_date: Optional[date] = None
    assignee_id: Optional[int] = None

class TaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    due_date: Optional[date] = None
    assignee_id: Optional[int] = None

app = FastAPI()

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

async def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    token = auth_header.split(" ")[1] if " " in auth_header else auth_header
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AUTH_SERVICE_URL}/auth/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Could not validate credentials")
        return UserPublic(**response.json())

@app.post("/tasks/", status_code=status.HTTP_201_CREATED, response_model=Task)
async def create_task(task: TaskCreate, current_user: UserPublic = Depends(get_current_user)):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO tasks (title, description, status, priority, due_date, assignee_id, creator_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *
                """,
                (task.title, task.description, TaskStatus.TODO.value, task.priority.value,
                 task.due_date, task.assignee_id, current_user.user_id)
            )
            new_task = cur.fetchone()
            conn.commit()
    return Task(**new_task)

@app.get("/tasks/", response_model=List[Task])
async def read_tasks(current_user: UserPublic = Depends(get_current_user)):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tasks WHERE creator_id = %s OR assignee_id = %s",
                        (current_user.user_id, current_user.user_id))
            tasks = cur.fetchall()
    return [Task(**task) for task in tasks]

@app.get("/tasks/{task_id}", response_model=Task)
async def read_task(task_id: int, current_user: UserPublic = Depends(get_current_user)):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tasks WHERE task_id = %s AND (creator_id = %s OR assignee_id = %s)",
                        (task_id, current_user.user_id, current_user.user_id))
            task = cur.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return Task(**task)

@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int, task_update: TaskUpdate, current_user: UserPublic = Depends(get_current_user)):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tasks WHERE task_id = %s AND creator_id = %s",
                        (task_id, current_user.user_id))
            task = cur.fetchone()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            update_data = {}
            if task_update.status:
                update_data["status"] = task_update.status.value
            if task_update.priority:
                update_data["priority"] = task_update.priority.value
            if task_update.due_date is not None:
                update_data["due_date"] = task_update.due_date
            if task_update.assignee_id is not None:
                update_data["assignee_id"] = task_update.assignee_id
            update_data["updated_at"] = datetime.utcnow()

            if update_data:
                set_clause = ", ".join(f"{k} = %s" for k in update_data.keys())
                cur.execute(
                    f"UPDATE tasks SET {set_clause} WHERE task_id = %s RETURNING *",
                    (*update_data.values(), task_id)
                )
                updated_task = cur.fetchone()
                conn.commit()
                return Task(**updated_task)
            return Task(**task)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)