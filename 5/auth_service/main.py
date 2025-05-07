from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, validator, Field
from typing import Optional
from datetime import datetime, timedelta
import jwt
import os
import bcrypt
import logging
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from enum import Enum
import redis
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "your-secure-secret-key-with-at-least-32-chars")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
MASTER_USERNAME = os.getenv("MASTER_USERNAME", "admin")
MASTER_PASSWORD = os.getenv("MASTER_PASSWORD", "secret")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DB_CONFIG = {
    "dbname": "task_tracker",
    "user": "postgres",
    "password": "postgres",
    "host": "postgres",
    "port": "5432"
}

# Инициализация Redis
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

class Role(str, Enum):
    CLIENT = "client"
    ADMIN = "admin"
    EXECUTOR = "executor"

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    full_name: Optional[str] = Field(None, max_length=100)
    role: Role = Role.CLIENT

    @validator('username')
    def validate_username(cls, v):
        if not re.match("^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username can only contain letters, numbers and underscores")
        return v

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserInDB(UserBase):
    user_id: int
    hashed_password: str
    disabled: bool = False

class UserPublic(UserBase):
    user_id: int

class Token(BaseModel):
    access_token: str
    token_type: str

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_user_by_username(username: str) -> Optional[UserInDB]:
    # Проверяем кэш
    cached_user = redis_client.get(f"user:username:{username}")
    if cached_user:
        logger.info(f"Cache hit for username: {username}")
        return UserInDB(**json.loads(cached_user))

    # Если в кэше нет, идем в базу
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            if user:
                # Сохраняем в кэш
                user_data = UserInDB(**user).dict()
                redis_client.setex(f"user:username:{username}", 3600, json.dumps(user_data))
                logger.info(f"Cache miss for username: {username}, stored in cache")
                return UserInDB(**user)
            return None

def get_user_by_id(user_id: int) -> Optional[UserInDB]:
    # Проверяем кэш
    cached_user = redis_client.get(f"user:id:{user_id}")
    if cached_user:
        logger.info(f"Cache hit for user_id: {user_id}")
        return UserInDB(**json.loads(cached_user))

    # Если в кэше нет, идем в базу
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()
            if user:
                # Сохраняем в кэш
                user_data = UserInDB(**user).dict()
                redis_client.setex(f"user:id:{user_id}", 3600, json.dumps(user_data))
                logger.info(f"Cache miss for user_id: {user_id}, stored in cache")
                return UserInDB(**user)
            return None

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = get_user_by_username(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = get_user_by_id(int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

@app.post("/auth/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": str(user.user_id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/users/me", response_model=UserPublic)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    return current_user

@app.post("/auth/users/", response_model=UserPublic)
async def create_user(user: UserCreate):
    if get_user_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = hash_password(user.password)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, full_name, role, hashed_password) VALUES (%s, %s, %s, %s) RETURNING user_id",
                (user.username, user.full_name, user.role.value, hashed_password)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            
            # После создания пользователя получаем его данные
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            new_user = cur.fetchone()
            user_data = UserInDB(**new_user).dict()
            # Сохраняем в кэш (write-through)
            redis_client.setex(f"user:username:{user.username}", 3600, json.dumps(user_data))
            redis_client.setex(f"user:id:{user_id}", 3600, json.dumps(user_data))
            logger.info(f"User {user.username} created and cached")
    
    return UserPublic(user_id=user_id, username=user.username, full_name=user.full_name, role=user.role)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)