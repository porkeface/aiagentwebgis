# Task 4.3: Agent Chat SSE API

**Files:**
- Create: `backend/app/api/v1/agent.py`
- Create: `backend/agent/checkpointer.py`
- Test: `backend/tests/test_api/test_agent_api.py`

**Steps:**
1. checkpointer.py: get_checkpointer() returns MemorySaver (dev) or PostgresSaver (prod)
2. agent.py: POST /api/v1/agent/chat with SSE response
   - Accept {session_id, message}
   - Build graph, invoke with state, stream SSE events from structured_plan
   - Each event: `event: message\ndata: {type, content}\n\n`
   - Final event: `event: done\ndata: {}\n\n`
3. Write API test verifying SSE stream
4. Commit: `feat: Agent chat API with SSE streaming`
