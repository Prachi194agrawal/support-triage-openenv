from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from models import TicketAction, TicketObservation, TicketState
from server.support_environment import SupportTriageEnvironment, TASKS
import uvicorn

app = FastAPI(title="Support Triage OpenEnv", version="0.1.0")

envs: dict = {}  # episode_id -> env  (supports concurrent episodes)

class ResetRequest(BaseModel):
    task_id: str = "easy"

class StepRequest(BaseModel):
    episode_id: str
    action: TicketAction

@app.get("/")
def root():
    return {"name": "support-triage-openenv", "tasks": list(TASKS.keys()), "status": "ok"}

@app.post("/reset")
def reset(req: ResetRequest):
    if req.task_id not in TASKS:
        raise HTTPException(400, f"Invalid task_id: {req.task_id}. Must be one of {list(TASKS.keys())}")
    env = SupportTriageEnvironment(task_id=req.task_id)
    obs = env.reset()
    envs[env.state().episode_id] = env
    return {"episode_id": env.state().episode_id, "observation": obs.model_dump()}

@app.post("/step")
def step(req: StepRequest):
    env = envs.get(req.episode_id)
    if env is None:
        raise HTTPException(404, "Episode not found. Call /reset first.")
    obs, reward, done, info = env.step(req.action)
    if done:
        envs.pop(req.episode_id, None)
    return {"observation": obs.model_dump(), "reward": reward, "done": done, "info": info}

@app.get("/state/{episode_id}")
def state(episode_id: str):
    env = envs.get(episode_id)
    if env is None:
        raise HTTPException(404, "Episode not found.")
    return env.state().model_dump()

def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()