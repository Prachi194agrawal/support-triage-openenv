---
title: Support Triage OpenEnv
emoji: 🎫
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
tags:
  - openenv
---

# Support Triage OpenEnv

## Overview
A real-world customer support triage environment built for the OpenEnv RL Challenge.
An agent reads a customer ticket and must classify priority, route to the correct team,
draft a compliant response, and escalate when the situation requires it.

## Tasks

| ID | Difficulty | Objective |
|----|-----------|-----------|
| easy | 🟢 Easy | Set correct ticket priority |
| medium | 🟡 Medium | Set priority + route to correct team |
| hard | 🔴 Hard | Priority + route + draft + escalate |

## Observation Space
Fields: `task_id`, `instruction`, `ticket_id`, `customer_message`,
`allowed_actions`, `progress`, `last_action_error`, `reward`, `done`

## Action Space
`action_type`: `analyze` | `set_priority` | `route` | `draft_reply` | `escalate` | `finish`
`value`: string (e.g. priority level, team name, or reply text)

## Reward Design
- Correct priority: +0.15
- Correct routing: +0.20
- Safe draft reply (keyword hit): up to +0.25
- Correct escalation decision: +0.20
- Unsafe promise in reply: -0.10 penalty
- Step overflow: -0.30 penalty

## Setup
```bash
pip install -r requirements.txt
python -m server.app
```

## Docker
```bash
docker build -t support-triage-openenv .
docker run -p 8000:8000 support-triage-openenv
```

## Inference
```bash
export HF_TOKEN="your_api_key"
export API_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
export MODEL_NAME="gemini-2.0-flash"
python inference.py
```

## Baseline Scores (Gemini 2.0 Flash)
| Task | Score |
|------|-------|
| easy | ~0.75 |
| medium | ~0.75 |
| hard | ~1.00 |