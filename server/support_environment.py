import uuid
from typing import Dict, Tuple
from models import TicketAction, TicketObservation, TicketState

TASKS = {
    "easy": {
        "instruction": "Classify the ticket priority correctly. Use set_priority then finish.",
        "ticket": {
            "ticket_id": "T-100",
            "message": "My payment failed twice and my order is still not confirmed. I need this fixed today.",
            "target_priority": "high",
            "target_team": "billing",
            "draft_keywords": ["payment", "sorry", "billing"],
            "must_escalate": False,
        },
    },
    "medium": {
        "instruction": "Set priority and route to the correct team. Use set_priority, route, then finish.",
        "ticket": {
            "ticket_id": "T-200",
            "message": "The mobile app crashes every time I upload a profile photo after the latest update.",
            "target_priority": "medium",
            "target_team": "technical",
            "draft_keywords": ["app", "update", "technical"],
            "must_escalate": False,
        },
    },
    "hard": {
        "instruction": "Set priority, route to correct team, draft a safe reply, and escalate. Then finish.",
        "ticket": {
            "ticket_id": "T-300",
            "message": "I was charged after canceling. Also I think someone accessed my account. Please lock it immediately.",
            "target_priority": "high",
            "target_team": "security",
            "draft_keywords": ["sorry", "secur", "account", "lock"],
            "must_escalate": True,
        },
    },
}

class SupportTriageEnvironment:
    def __init__(self, task_id: str = "easy", max_steps: int = 10):
        assert task_id in TASKS, f"Unknown task: {task_id}"
        self.task_id  = task_id
        self.max_steps = max_steps
        self._state   = None
        self._last_error = None

    def reset(self) -> TicketObservation:
        task = TASKS[self.task_id]
        self._state = TicketState(
            episode_id=str(uuid.uuid4()),
            task_id=self.task_id,
            current_ticket=task["ticket"],
        )
        self._last_error = None
        return self._obs(0.0, False)

    def state(self) -> TicketState:
        return self._state

    def _obs(self, reward: float, done: bool) -> TicketObservation:
        t = self._state.current_ticket
        return TicketObservation(
            task_id=self.task_id,
            instruction=TASKS[self.task_id]["instruction"],
            ticket_id=t["ticket_id"],
            customer_message=t["message"],
            allowed_actions=["analyze","set_priority","route","draft_reply","escalate","finish"],
            progress=round(self._state.progress_score, 2),
            last_action_error=self._last_error,
            reward=round(reward, 2),
            done=done,
        )

    def _grader(self) -> float:
        t   = self._state.current_ticket
        h   = self._state.history
        score = 0.0
        priority = next((x["value"] for x in h if x["action"] == "set_priority"), None)
        team     = next((x["value"] for x in h if x["action"] == "route"),        None)
        draft    = next((x["value"] for x in h if x["action"] == "draft_reply"), "")
        escalated = any(x["action"] == "escalate" for x in h)

        if priority == t["target_priority"]:  score += 0.25
        if team     == t["target_team"]:      score += 0.25
        if all(k in draft.lower() for k in t["draft_keywords"]): score += 0.25
        if escalated == t["must_escalate"]:   score += 0.25
        # Phase-2 requires strict range: 0 < score < 1
        score = round(score, 2)
        if score <= 0.0:
            return 0.01
        if score >= 1.0:
            return 0.99
        return score

    def step(self, action: TicketAction) -> Tuple[TicketObservation, float, bool, Dict]:
        self._last_error = None
        self._state.step_count += 1
        info = {"task_id": self.task_id}

        # Penalise step overflow
        if self._state.step_count > self.max_steps:
            self._last_error = "max_steps_exceeded"
            self._state.finished = True
            final = 0.01
            info["grader_score"] = final
            self._state.progress_score = final
            obs = self._obs(final, True)
            return obs, final, True, info

        # Record action
        self._state.history.append({
            "action": action.action_type,
            "value":  action.value,
            "notes":  action.notes,
        })

        t = self._state.current_ticket
        reward = -0.02  # small step cost

        if action.action_type == "analyze":
            reward = 0.05

        elif action.action_type == "set_priority":
            reward = 0.15 if action.value == t["target_priority"] else -0.05

        elif action.action_type == "route":
            reward = 0.20 if action.value == t["target_team"] else -0.08

        elif action.action_type == "draft_reply":
            hits   = sum(1 for k in t["draft_keywords"] if k in action.value.lower())
            reward = round(min(0.25, 0.07 * hits), 2)
            if "refund guaranteed" in action.value.lower():
                reward -= 0.10
                self._last_error = "unsafe_promise"

        elif action.action_type == "escalate":
            reward = 0.20 if t["must_escalate"] else -0.05

        elif action.action_type == "finish":
            final = self._grader()
            reward = final
            self._state.finished = True
            info["grader_score"] = final
            self._state.progress_score = final
            obs = self._obs(reward, True)
            return obs, reward, True, info

        # Update running progress estimate
        self._state.progress_score = max(
            self._state.progress_score,
            min(1.0, self._grader())
        )
        obs = self._obs(reward, False)
        return obs, reward, False, info