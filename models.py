from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict

class TicketAction(BaseModel):
    action_type: Literal["analyze","set_priority","route","draft_reply","escalate","finish"]
    value: str = ""
    notes: str = ""

class TicketObservation(BaseModel):
    task_id: str
    instruction: str
    ticket_id: str
    customer_message: str
    allowed_actions: List[str]
    progress: float = 0.0
    last_action_error: Optional[str] = None
    reward: float = 0.0      # also in observation for OpenEnv dual-mode compatibility
    done: bool = False       # also in observation for OpenEnv dual-mode compatibility

class TicketState(BaseModel):
    episode_id: str
    step_count: int = 0
    task_id: str
    current_ticket: Dict
    progress_score: float = 0.0
    history: List[Dict] = Field(default_factory=list)
    finished: bool = False