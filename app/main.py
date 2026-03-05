from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from pydantic import BaseModel
import asyncio
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return FileResponse("app/static/index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})

class ChatRequest(BaseModel):
    prompt: str


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, current_user: User = Depends(get_current_user)):
    """Ask Titan with streaming - requires auth"""
    prompt = request.prompt

    async def event_stream():
        try:
            # Use httpx for async HTTP calls
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://192.168.0.247:8402/v1/chat/completions",
                    json={
                        "model": "qwen3.5-35b",
                        "messages": [
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 2000
                    },
                    timeout=120.0
                )
                result = resp.json()
            
            # Extract content from response
            content = ""
            if result.get("choices"):
                msg = result["choices"][0].get("message", {})
                content = msg.get("content", "") or msg.get("reasoning_content", "")
            
            # Stream in chunks (words/lines) instead of character by character
            # Split by whitespace but preserve structure
            import re
            # Split into chunks of ~50 chars to preserve formatting but reduce DOM updates
            chunks = re.findall(r'.{1,50}', content)
            
            for chunk in chunks:
                yield f"data: {{\"data\": {json.dumps(chunk)}}}\n\n"
                await asyncio.sleep(0.05)  # Small delay between chunks
            
            yield "data: {\"data\": \"[DONE]\"}\n\n"
        except Exception as e:
            yield f"data: {{\"data\": \"Error: {str(e)}\"}}\n\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")

class TTSRequest(BaseModel):
    text: str
    speaker: str = "brad"

@app.post("/tts")
async def text_to_speech(request: TTSRequest, current_user: User = Depends(get_current_user)):
    """Convert text to speech using XTTS on Titan"""
    try:
        resp = requests.post(
            "http://192.168.0.247:8189/tts",
            json={"text": request.text, "speaker": request.speaker},
            timeout=30
        )
        return Response(content=resp.content, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

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
