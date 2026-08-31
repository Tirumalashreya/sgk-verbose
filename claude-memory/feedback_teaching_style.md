---
name: Teaching style — guided learning only
description: Guide for agentic AI/backend; build directly for frontend
type: feedback
---

Guide and ask user to write code ONLY for the agentic AI / backend / LangGraph / Python side — that is what the user is learning.

For frontend (React Native / Expo), just build it directly without asking them to write it.

**Exception:** When the user explicitly says "you write the code" or "just fix it" for backend/agent code — write it directly. Do not keep asking them to write it when they've clearly said they want you to do it.

**Why:** User explicitly said "frontend is not what I'm learning." They are building Verba Pravachana AI to learn agentic AI systems. Writing frontend code themselves is not valuable to them.

**How to apply:**
- React Native / Expo / UI screens / styling → write the code yourself
- LangGraph agents / orchestration / FastAPI / ChromaDB / AI pipelines → guided teaching mode:
  1. Explain the concept
  2. Describe the pipeline/steps
  3. Ask user to write it
  4. Correct mistakes and explain every line
  5. Only reveal full solution as last resort
- If user says "you write it / just fix it" → write it directly

