---
title: Support Triage OpenEnv
emoji: 🎫
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
tags:
  - openenv
---

# Support Triage OpenEnv

## Overview & Motivation
Customer support triage is a real, high-stakes task performed by humans daily.
An agent must read a ticket, assign priority, route to the right team, draft
a safe reply, and escalate when necessary.

## Observation Space
| Field | Type | Description |
|-------|------|-------------|
| task_id | str | Current task identifier |
| instruction | str | What the agent must accomplish |
| ticket_id | str | Support ticket ID |
| customer_message | str | The customer message |
| allowed_actions | List[str] | Valid action types |
| progress | float | Running grader estimate 0-1 |
| last_action_error | str | Error from last action or null |
| reward | float | Reward from last step |
| done | bool | Whether episode is finished |

## Action Space
| action_type | value | Effect |
|-------------|-------|--------|
| analyze | "" | Inspect ticket +0.05 |
| set_priority | low/medium/high | Set ticket priority |
| route | billing/technical/security/general | Route to team |
| draft_reply | reply text | Draft customer reply |
| escalate | team | Escalate to specialist |
| finish | "" | End episode trigger grader |

## Tasks
| ID | Difficulty | Objective |
|----|-----------|-----------|
| easy | Easy | Set correct ticket priority |
| medium | Medium | Set priority and route to correct team |
| hard | Hard | Priority route safe draft and escalate |

## Reward Design
- Correct priority +0.15 wrong -0.05
- Correct routing +0.20 wrong -0.08
- Draft reply per keyword hit +0.07 max +0.25
- Correct escalation +0.20
- Per step cost -0.02
- Step overflow -0.30

## Setup
```bash
pip install -r requirements.txt
python -m server.app
```

## Docker
```bash
docker build -t support-triage-openenv .
docker run -p 7860:7860 support-triage-openenv
```

## Inference
```bash
export HF_TOKEN="your_hf_token"
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
python inference.py
```

## Baseline Scores
| Task | Score |
|------|-------|
| easy | 0.75 |
| medium | 0.75 |
| hard | 1.00 |