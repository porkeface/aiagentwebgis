# Task 4.5: JWT Auth

**Files:**
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/api/v1/auth.py`
- Test: `backend/tests/test_api/test_auth_api.py`

**Steps:**
1. auth_service.py: hash_password, verify_password, create_token, decode_token
2. auth.py: POST /register, POST /login (returns JWT)
3. get_current_user dependency for protected endpoints
4. Update trip.py to use real get_current_user instead of placeholder
5. Write tests
6. Commit: `feat: JWT authentication - register, login, token validation`
