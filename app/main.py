from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from pydantic import BaseModel
import hashlib
import base64
import json
import os
import requests

SQLALCHEMY_DATABASE_URL = "sqlite:///./tasks.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    is_completed = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="tasks")

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain, hashed):
    return hashlib.sha256(plain.encode()).hexdigest() == hashed

def get_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data):
    return base64.b64encode(json.dumps(data).encode()).decode()

def decode_token(token):
    return json.loads(base64.b64decode(token.encode()).decode())

def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)):
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
    except:
        raise HTTPException(status_code=401)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401)
    return user


@app.get("/")
def root():
    return FileResponse("app/static/index.html")

class ChatRequest(BaseModel):
    prompt: str


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, current_user: User = Depends(get_current_user)):
    """Ask Titan with streaming - requires auth"""
    prompt = request.prompt
    
    def event_stream():
        try:
            resp = requests.post(
                "http://192.168.0.247:8402/v1/chat/completions",
                json={"model": "qwen3.5-35b", "messages": [{"role": "user", "content": prompt}]},
                stream=True,
                timeout=120
            )
            
            for chunk in resp.iter_lines():
                if chunk:
                    line = chunk.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data and data != '[DONE]':
                            yield f"data: {data}\n\n"
        except Exception as e:
            yield f"data: {str(e)}\n\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/register")
def register(form_data: OAuth2PasswordRequestForm = Depends(), db = Depends(get_db)):
    # Registration disabled - only allow specific users
    # Set ALLOWED_EMAILS env var to add users
    allowed_emails = os.environ.get("ALLOWED_EMAILS", "").split(",") if os.environ.get("ALLOWED_EMAILS") else []
    email = form_data.username
    if allowed_emails and email not in allowed_emails:
        raise HTTPException(status_code=403, detail="Registration not allowed")
    
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email exists")
    user = User(email=email, hashed_password=get_password_hash(form_data.password))
    db.add(user)
    db.commit()
    return {"id": user.id, "email": user.email}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401)
    return {"access_token": create_access_token({"sub": user.id}), "token_type": "bearer"}

@app.post("/tasks/")
def create_task(title: str, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    task = Task(title=title, owner_id=current_user.id)
    db.add(task)
    db.commit()
    return {"id": task.id, "title": task.title, "is_completed": task.is_completed}

@app.get("/tasks/")
def get_tasks(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    tasks = db.query(Task).filter(Task.owner_id == current_user.id).all()
    return [{"id": t.id, "title": t.title, "is_completed": t.is_completed} for t in tasks]

@app.patch("/tasks/{task_id}")
def update_task(task_id: int, is_completed: bool, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404)
    task.is_completed = is_completed
    db.commit()
    return {"id": task.id, "is_completed": task.is_completed}

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404)
    db.delete(task)
    db.commit()
    return {"deleted": True}
