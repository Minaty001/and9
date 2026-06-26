# 📋 JARVIS PCOS — Integration Test Results

| Input | Expected Output | Actual Output | Result (Passed/Failed) | Problem Faced | Solution |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /api/health` | Status 200 | Status 200 (['status'] keys) | **Passed** | None | None |
| `POST /api/understanding/analyze ({'query': 'hello ji'})` | Status 200 | Status 200 (['intent', 'emotion', 'emotion_intensity'] keys) | **Passed** | None | None |
| `POST /api/understanding/analyze ({'query': 'note down my name is Saif'})` | Status 200 | Status 200 (['intent', 'emotion', 'emotion_intensity'] keys) | **Passed** | None | None |
| `POST /api/and9 ({'query': 'alarm tomorrow 7 am'})` | Status 200 | Status 200 (['response', 'action', 'payload'] keys) | **Passed** | None | None |
| `POST /api/and9 ({'query': 'remind me after 5 min to drink water'})` | Status 200 | Status 200 (['response', 'action', 'payload'] keys) | **Passed** | None | None |
| `POST /api/and9 ({'query': 'set reminder for after 5 seconds'})` | Status 200 | Status 200 (['response', 'action', 'payload'] keys) | **Passed** | None | None |
| `POST /api/and9 ({'query': 'what is the time in delhi?'})` | Status 200 | Status 200 (['response', 'action', 'payload'] keys) | **Passed** | None | None |
| `GET /api/memory/cache/stats` | Status 200 | Status 200 (['hits', 'misses', 'size'] keys) | **Passed** | None | None |
| `GET /api/memory/sessions` | Status 200 | Status 200 (['sessions', 'count'] keys) | **Passed** | None | None |
