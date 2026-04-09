# Running Support Triage OpenEnv on Google Colab with GPU

This guide explains how to run the OpenEnv environment and inference script on Google Colab with GPU acceleration.

## Step 1: Create a Colab Notebook

1. Go to [Google Colab](https://colab.research.google.com)
2. Create a new notebook
3. Go to **Runtime** → **Change runtime type** → Select **GPU** (e.g., T4, L4, or A100 if available)

## Step 2: Clone and Install the Repository

```python
# Install dependencies
!pip install -q fastapi uvicorn pydantic openai pyyaml requests

# Clone the repository
!git clone https://github.com/Prachi194agrawal/support-triage-openenv.git
%cd support-triage-openenv
```

## Step 3: Set Environment Variables

```python
import os

# Set your HuggingFace token (Get from https://huggingface.co/settings/tokens)
os.environ["HF_TOKEN"] = "hf_YOUR_TOKEN_HERE"

# Option 1: Use Google Gemini API (recommended for free tier)
os.environ["API_BASE_URL"] = "https://generativelanguage.googleapis.com/v1beta/openai/"
os.environ["MODEL_NAME"] = "gemini-2.0-flash"
os.environ["HF_TOKEN"] = "YOUR_GOOGLE_API_KEY"  # Get from https://aistudio.google.com/app/apikey

# Option 2: Use OpenAI API
os.environ["API_BASE_URL"] = "https://api.openai.com/v1"
os.environ["MODEL_NAME"] = "gpt-4-mini"
os.environ["HF_TOKEN"] = "sk_YOUR_OPENAI_KEY"

# Option 3: Use any OpenAI-compatible endpoint (LM Studio, Ollama, etc.)
os.environ["API_BASE_URL"] = "http://localhost:8000/v1"
os.environ["MODEL_NAME"] = "local-model"
```

## Step 4: Run Inference

### Option A: Direct Python Execution (Recommended)

```python
import subprocess
import sys

# Run the inference script
result = subprocess.run(
    [sys.executable, "inference.py"],
    capture_output=True,
    text=True
)

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
```

### Option B: Start FastAPI Server and Test Locally

```python
# Install additional dependencies for async support
!pip install -q httpx

# Start the server in background
import subprocess
import time

# Start server
server_process = subprocess.Popen(
    ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

time.sleep(3)

# Test the API
import httpx

async def test_api():
    async with httpx.AsyncClient() as client:
        # Test root endpoint
        resp = await client.get("http://localhost:8000/")
        print("GET /:", resp.json())
        
        # Test reset
        resp = await client.post("http://localhost:8000/reset", json={"task_id": "easy"})
        data = resp.json()
        episode_id = data["episode_id"]
        print(f"\nReset successful, episode_id: {episode_id}")
        print(f"Observation: {data['observation']}")

import asyncio
await test_api()

# Cleanup
server_process.terminate()
server_process.wait()
```

## Step 5: Run Full Inference Pipeline with LLM

```python
import json
import os
from openai import OpenAI
from models import TicketAction
from server.support_environment import SupportTriageEnvironment

# Configure your API
API_BASE_URL = os.getenv("API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash")
HF_TOKEN = os.getenv("HF_TOKEN")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

# Initialize client
client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

SYSTEM_PROMPT = """You are an expert customer support agent solving a triage task step by step.
Available action_types: analyze, set_priority, route, draft_reply, escalate, finish
Teams: billing, technical, security, general
Priorities: low, medium, high
Reply ONLY with valid JSON. No markdown. No explanation.
Example: {"action_type":"set_priority","value":"high","notes":"urgent billing issue"}
"""

def choose_action(obs, history):
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
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    raw = resp.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    return TicketAction(**data)

def run_task(task_name):
    env = SupportTriageEnvironment(task_id=task_name)
    obs = env.reset()
    history = []
    rewards = []
    success = False
    steps = 0

    print(f"[START] task={task_name} env=support-triage-openenv model={MODEL_NAME}")

    try:
        for step_i in range(1, 11):
            action = choose_action(obs, history)
            obs, reward, done, info = env.step(action)
            steps = step_i
            rewards.append(f"{reward:.2f}")
            err = f'"{obs.last_action_error}"' if obs.last_action_error else "null"
            act_str = f"{action.action_type}('{action.value}')"
            print(f"[STEP] step={step_i} action={act_str} reward={reward:.2f} done={str(done).lower()} error={err}")
            history.append({"action": action.action_type, "value": action.value})
            if done:
                success = info.get("grader_score", reward) >= 0.5
                break
    except Exception as e:
        print(f"[STEP] step={max(steps, 1)} action=exception reward=0.00 done=true error={str(e)}")
        success = False
    finally:
        rw_str = ",".join(rewards) if rewards else "0.00"
        print(f"[END] success={str(success).lower()} steps={steps} rewards={rw_str}")

# Run all tasks
for task in ["easy", "medium", "hard"]:
    run_task(task)
    print()
```

## Step 6: GPU Acceleration Tips

### Monitor GPU Usage
```python
!nvidia-smi  # Check GPU status
!watch -n 1 nvidia-smi  # Continuous monitoring
```

### For Better Performance with Local Models

If you want to run a local model with GPU acceleration:

```python
# Install Ollama or LM Studio on a cloud VM, then connect
# Or use a model with native GPU support

# Example with a quantized model via LM Studio
os.environ["API_BASE_URL"] = "http://lm-studio-server:8000/v1"
```

## Common Issues & Solutions

### Issue: "ModuleNotFoundError: No module named 'fastapi'"
**Solution**: Run the pip install cell first

### Issue: GPU Not Detected
**Solution**: 
```python
import torch
print(torch.cuda.is_available())  # Should print True
print(torch.cuda.get_device_name(0))  # Shows GPU name
```

### Issue: API Rate Limits
**Solution**: Add delays between requests
```python
import time
time.sleep(1)  # Wait 1 second between API calls
```

### Issue: Long Inference Time
**Solution**: Use a faster model like Gemini Flash or GPT-4 Mini instead of full models

## Next Steps

1. Save your notebook with your test results
2. Share the notebook or results
3. To deploy on HF Spaces, use the Docker setup instead (see main README.md)

## References

- [Google Colab Documentation](https://colab.research.google.com/)
- [HuggingFace Spaces Documentation](https://huggingface.co/docs/hub/spaces)
- [OpenAI API Documentation](https://platform.openai.com/docs/)
- [OpenEnv Documentation](https://github.com/meta-pytorch/OpenEnv)
