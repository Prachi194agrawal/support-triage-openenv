from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from models import TicketAction, TicketObservation, TicketState
from server.support_environment import SupportTriageEnvironment, TASKS
import uvicorn

app = FastAPI(
    title="Support Triage OpenEnv",
    description="Real-world customer support triage environment for OpenEnv RL Challenge",
    version="0.1.0",
)

_episodes: dict = {}

class ResetRequest(BaseModel):
    task_id: str = "easy"

class StepRequest(BaseModel):
    episode_id: str
    action: TicketAction

@app.get("/")
def root():
    return {
        "name": "support-triage-openenv",
        "version": "0.1.0",
        "tasks": list(TASKS.keys()),
        "status": "ok",
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/reset")
def reset(req: ResetRequest = None):
    # Accept empty body — default to "easy"
    task_id = (req.task_id if req else None) or "easy"
    if task_id not in TASKS:
        raise HTTPException(400, f"Unknown task_id '{task_id}'. Choose from: {list(TASKS.keys())}")
    env = SupportTriageEnvironment(task_id=task_id)
    obs = env.reset()
    eid = env.state().episode_id
    _episodes[eid] = env
    return {"episode_id": eid, "observation": obs.model_dump()}

@app.post("/step")
def step(req: StepRequest):
    env = _episodes.get(req.episode_id)
    if env is None:
        raise HTTPException(404, "Episode not found. Call /reset first.")
    obs, reward, done, info = env.step(req.action)
    if done:
        _episodes.pop(req.episode_id, None)
    return {
        "observation": obs.model_dump(),
        "reward": round(reward, 2),
        "done": done,
        "info": info,
    }

@app.get("/state/{episode_id}")
def state(episode_id: str):
    env = _episodes.get(episode_id)
    if env is None:
        raise HTTPException(404, "Episode not found or already finished.")
    return env.state().model_dump()

def main():
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860, reload=False)

if __name__ == "__main__":
    main()