from fastapi import FastAPI, HTTPException, Depends, status, Request
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime, date
import logging
import os
from typing import List, Optional
import httpx
from pymongo import MongoClient
from bson import ObjectId

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongo:mongo@mongodb:27017/task_tracker?authSource=admin")

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
    task_id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.TODO
    priority: Priority = Priority.MEDIUM
    created_at: datetime
    updated_at: datetime
    due_date: Optional[str] = None
    assignee_id: Optional[int] = None
    creator_id: int

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat() if v else None
        }

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

def get_db_client():
    return MongoClient(MONGODB_URL)

async def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    token = auth_header.split(" ")[1] if " " in auth_header else auth_header
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/auth/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            return UserPublic(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Could not validate credentials")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Auth service error: {str(e)}")

@app.post("/tasks/", status_code=status.HTTP_201_CREATED, response_model=Task)
async def create_task(task: TaskCreate, current_user: UserPublic = Depends(get_current_user)):
    try:
        client = get_db_client()
        db = client.task_tracker
        task_dict = task.dict(exclude_unset=True)
        if task_dict.get("due_date"):
            task_dict["due_date"] = task_dict["due_date"].isoformat()
        task_dict.update({
            "status": TaskStatus.TODO.value,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "creator_id": current_user.user_id
        })
        result = db.tasks.insert_one(task_dict)
        task_dict["_id"] = result.inserted_id
        task_dict["task_id"] = str(result.inserted_id)
        client.close()
        return Task(**task_dict)
    except Exception as e:
        logger.error(f"Ошибка при создании задачи: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при создании задачи: {str(e)}")

@app.get("/tasks/", response_model=List[Task])
async def read_tasks(current_user: UserPublic = Depends(get_current_user)):
    try:
        client = get_db_client()
        db = client.task_tracker
        tasks = db.tasks.find({
            "$or": [
                {"creator_id": current_user.user_id},
                {"assignee_id": current_user.user_id}
            ]
        })
        result = []
        for task in tasks:
            task["task_id"] = str(task["_id"])
            task.pop("_id")
            if isinstance(task.get("due_date"), datetime):
                task["due_date"] = task["due_date"].strftime("%Y-%m-%d")
            result.append(Task(**task))
        client.close()
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении списка задач: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении списка задач: {str(e)}")

@app.get("/tasks/{task_id}", response_model=Task)
async def read_task(task_id: str, current_user: UserPublic = Depends(get_current_user)):
    try:
        if not ObjectId.is_valid(task_id):
            raise HTTPException(status_code=400, detail="Invalid task_id format")
        
        client = get_db_client()
        db = client.task_tracker
        task = db.tasks.find_one({
            "_id": ObjectId(task_id),
            "$or": [
                {"creator_id": current_user.user_id},
                {"assignee_id": current_user.user_id}
            ]
        })
        client.close()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        task["task_id"] = str(task["_id"])
        task.pop("_id")
        if isinstance(task.get("due_date"), datetime):
            task["due_date"] = task["due_date"].strftime("%Y-%m-%d")
        return Task(**task)
    except HTTPException as e:
        raise e
    except ValueError as e:
        logger.error(f"Неверный формат task_id: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid task_id format")
    except Exception as e:
        logger.error(f"Ошибка при получении задачи: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении задачи: {str(e)}")

@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: TaskUpdate, current_user: UserPublic = Depends(get_current_user)):
    try:
        if not ObjectId.is_valid(task_id):
            raise HTTPException(status_code=400, detail="Invalid task_id format")
        
        client = get_db_client()
        db = client.task_tracker
        task = db.tasks.find_one({"_id": ObjectId(task_id), "creator_id": current_user.user_id})
        if not task:
            client.close()
            raise HTTPException(status_code=404, detail="Task not found")
        
        update_data = {"updated_at": datetime.utcnow()}
        if task_update.status:
            update_data["status"] = task_update.status.value
        if task_update.priority:
            update_data["priority"] = task_update.priority.value
        if task_update.due_date is not None:
            update_data["due_date"] = task_update.due_date.isoformat() if task_update.due_date else None
        if task_update.assignee_id is not None:
            update_data["assignee_id"] = task_update.assignee_id

        if update_data:
            db.tasks.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": update_data}
            )
        updated_task = db.tasks.find_one({"_id": ObjectId(task_id)})
        client.close()
        updated_task["task_id"] = str(updated_task["_id"])
        updated_task.pop("_id")
        if isinstance(updated_task.get("due_date"), datetime):
            updated_task["due_date"] = updated_task["due_date"].strftime("%Y-%m-%d")
        return Task(**updated_task)
    except HTTPException as e:
        raise e
    except ValueError as e:
        logger.error(f"Неверный формат task_id: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid task_id format")
    except Exception as e:
        logger.error(f"Ошибка при обновлении задачи: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении задачи: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)