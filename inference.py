import os, json, sys
from openai import OpenAI
from models import TicketAction
from server.support_environment import SupportTriageEnvironment

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "gpt-4.1-mini")
HF_TOKEN     = os.getenv("HF_TOKEN")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

# Use HF_TOKEN as api_key (works for HF endpoints)
# For Google Gemini, set API_BASE_URL and use GOOGLE_API_KEY as HF_TOKEN
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

def run_task(task_name: str):
    env = SupportTriageEnvironment(task_id=task_name)
    obs = env.reset()
    history = []
    rewards = []
    success = False
    steps   = 0

    print(f"[START] task={task_name} env=support-triage-openenv model={MODEL_NAME}")

    try:
        for step_i in range(1, 11):
            action = choose_action(obs, history)
            obs, reward, done, info = env.step(action)
            steps = step_i
            rewards.append(f"{reward:.2f}")
            err = obs.last_action_error if obs.last_action_error else "null"
            act_str = f"{action.action_type}('{action.value}')"
            print(f"[STEP] step={step_i} action={act_str} reward={reward:.2f} done={str(done).lower()} error={err}")
            history.append({"action": action.action_type, "value": action.value})
            if done:
                success = info.get("grader_score", reward) >= 0.5
                break
    except Exception as e:
        print(f"[STEP] step={max(steps,1)} action=exception reward=0.00 done=true error={str(e)}")
        success = False
    finally:
        rw_str = ",".join(rewards) if rewards else "0.00"
        print(f"[END] success={str(success).lower()} steps={steps} rewards={rw_str}")

if __name__ == "__main__":
    for t in TASKS:
        run_task(t)
        print()