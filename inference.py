import os, json, sys
from openai import OpenAI
from models import TicketAction
from server.support_environment import SupportTriageEnvironment

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "gpt-4.1-mini")
HF_TOKEN     = os.getenv("HF_TOKEN")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

TASKS = ["easy", "medium", "hard"]

SYSTEM_PROMPT = """You are an expert customer support agent solving a triage task step by step.
Available action_types: analyze, set_priority, route, draft_reply, escalate, finish
Teams: billing, technical, security, general
Priorities: low, medium, high
Reply ONLY with valid JSON. No markdown. No explanation.
Example: {"action_type":"set_priority","value":"high","notes":"urgent billing issue"}
"""

def choose_action(obs, history: list) -> TicketAction:
    hist_str = json.dumps(history[-4:], indent=2) if history else "none yet"
    prompt = f"""Task: {obs.instruction}
Ticket [{obs.ticket_id}]: {obs.customer_message}
Recent history: {hist_str}
Progress so far: {obs.progress}

What is your next single action? Reply with JSON only."""
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0,
    )
    raw = resp.choices[0].message.content.strip()
    raw = raw.replace("```json","").replace("```","").strip()
    data = json.loads(raw)
    return TicketAction(**data)

def _strict_score(s: float) -> float:
    """Clamp to strictly open interval (0, 1) — never 0.0 or 1.0."""
    s = round(float(s), 4)
    if s <= 0.0:
        return 0.01
    if s >= 1.0:
        return 0.99
    return s

def run_task(task_name: str):
    env = SupportTriageEnvironment(task_id=task_name)
    obs = env.reset()
    history = []
    rewards = []
    success = False
    steps   = 0
    score   = 0.01  # default: strictly > 0

    print(f"[START] task={task_name} env=support-triage-openenv model={MODEL_NAME}", flush=True)

    try:
        for step_i in range(1, 11):
            action = choose_action(obs, history)
            obs, reward, done, info = env.step(action)
            steps = step_i
            reward = _strict_score(reward)
            rewards.append(f"{reward:.4f}")
            err = f'"{obs.last_action_error}"' if obs.last_action_error else "null"
            act_str = f"{action.action_type}('{action.value}')"
            print(f"[STEP] step={step_i} action={act_str} reward={reward:.4f} done={str(done).lower()} error={err}", flush=True)
            history.append({"action": action.action_type, "value": action.value})
            if done:
                raw_score = info.get("grader_score", reward)
                score = _strict_score(raw_score)
                success = score >= 0.5
                break
        else:
            # hit max steps without finish action — use grader directly
            raw_score = env._grader()
            score = _strict_score(raw_score)
            success = score >= 0.5
    except Exception as e:
        print(f"[STEP] step={max(steps,1)} action=exception reward=0.0100 done=true error=\"{str(e)}\"", flush=True)
        score = 0.01
        success = False
    finally:
        rw_str = ",".join(rewards) if rewards else "0.0100"
        print(f"[END] success={str(success).lower()} steps={steps} score={score:.4f} rewards={rw_str}", flush=True)

if __name__ == "__main__":
    for t in TASKS:
        run_task(t)
        print()
