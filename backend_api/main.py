from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os

# Add the parent directory to sys.path so we can import env
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from env.environment import VulnArenaEnv

app = FastAPI(title="VulnArena AI Backend")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

env = VulnArenaEnv()

class ResetRequest(BaseModel):
    task_name: str = "easy"

from typing import Optional, List

class StepRequest(BaseModel):
    action: str
    report_text: Optional[str] = None
    logs: Optional[list] = None
    code_snippet: Optional[str] = None

@app.post("/reset")
def reset_endpoint(req: ResetRequest = None):
    task_name = req.task_name if req and req.task_name else "easy"
    return env.reset(task_name)

@app.post("/step")
def step_endpoint(req: StepRequest):
    state_dict, reward, done, info = env.step(req.action, custom_req=req)
    return {
        "observation": state_dict,
        "reward": reward,
        "done": done,
        "info": info
    }

@app.get("/state")
def state_endpoint():
    return {"state": env.state()}

@app.get("/")
def root():
    return {"status": "ok", "message": "VulnArena AI Backend is running"}
