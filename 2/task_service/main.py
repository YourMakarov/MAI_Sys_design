from fastapi import FastAPI, HTTPException, Depends, status, Request
from enum import Enum
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
import logging
import os
from typing import List, Optional
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")

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

fake_tasks_db = {}
task_id_counter = 1

app = FastAPI()

async def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    token = auth_header.split(" ")[1] if " " in auth_header else auth_header
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/auth/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Could not validate credentials"
                )
                
            return UserPublic(**response.json())
            
        except httpx.RequestError as e:
            logger.error(f"Auth service connection error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )

async def get_current_active_user(current_user: UserPublic = Depends(get_current_user)):
    return current_user

@app.post("/tasks/", status_code=status.HTTP_201_CREATED, response_model=Task)
async def create_task(
    task: TaskCreate,
    current_user: UserPublic = Depends(get_current_active_user)
):
    global task_id_counter

    task_id = task_id_counter
    task_id_counter += 1
    
    now = datetime.utcnow()
    
    new_task = Task(
        task_id=task_id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        created_at=now,
        updated_at=now,
        due_date=task.due_date,
        assignee_id=task.assignee_id
    )

    fake_tasks_db[task_id] = new_task
    logger.info(f"Task {task_id} created by {current_user.username}")
    return new_task

@app.get("/tasks/", response_model=List[Task])
async def read_tasks(current_user: UserPublic = Depends(get_current_active_user)):
    # In a real app, we would filter tasks based on user role and ownership
    return list(fake_tasks_db.values())

@app.get("/tasks/{task_id}", response_model=Task)
async def read_task(
    task_id: int,
    current_user: UserPublic = Depends(get_current_active_user)
):
    task = fake_tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: UserPublic = Depends(get_current_active_user)
):
    task = fake_tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    now = datetime.utcnow()
    
    if task_update.status:
        task.status = task_update.status
    
    if task_update.priority:
        task.priority = task_update.priority
    
    if task_update.due_date:
        task.due_date = task_update.due_date
    
    if task_update.assignee_id is not None:
        task.assignee_id = task_update.assignee_id
    
    task.updated_at = now
    
    logger.info(f"Task {task_id} updated by {current_user.username}")
    return task

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")