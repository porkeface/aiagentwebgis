# Task 6.3: Error Handling

**Phase:** Integration
**Category:** Fallback + graceful degradation

---

## Steps

1. **LLM timeout:** retry once, then graceful error message
2. **Amap API failure:** fallback to local DB data
3. **DB connection failure:** retry with backoff
4. **Frontend:** show error notifications, retry buttons
5. **Commit:** `feat: error handling and graceful degradation`

---

## Context

- **Plan file:** `docs/superpowers/plans/2026-06-29-ai-travel-planner.md`
- **Global constraints:**
  - All API responses use envelope: `{"success": bool, "data": any, "error": str|null}`
  - All async endpoints use `async/await`
  - No hardcoded secrets, env vars only
  - LLM temperature: 0.3
- **Key files involved:**
  - `backend/agent/llm/` — LLM adapter layer (timeout/retry)
  - `backend/app/services/amap_service.py` — Amap API (fallback to DB)
  - `backend/app/database.py` — DB session (retry with backoff)
  - `frontend/src/components/` — UI error notifications, retry buttons
  - `frontend/src/stores/` — SSE error handling in chat store
