# AI-Assisted Interview Screening & Feedback System

Backend-only API for a minimal interview screening platform. Recruiters create interview
templates and assign a candidate; the candidate submits free-text answers; the backend
generates a score and feedback per answer using a simple heuristic (mocked AI logic).

## Tech Stack

- Python 3.x + Django 6 + Django REST Framework
- SQLite (demo speed — swap to PostgreSQL by changing `DATABASES` in `config/settings.py`)
- JWT auth via `djangorestframework-simplejwt`

## Setup

1. Clone and enter the project:
```bash
   git clone <repo-url>
   cd interview-screening-api
```

2. Create and activate a virtual environment:
```bash
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # macOS/Linux
```

3. Install dependencies:
```bash
   pip install -r requirements.txt
```

4. Run migrations:
```bash
   python manage.py makemigrations
   python manage.py migrate
```

5. (Optional) Create an admin user:
```bash
   python manage.py createsuperuser
```

6. Start the server:
```bash
   python manage.py runserver
```

API is now live at `http://127.0.0.1:8000/api/`.

## Data Model

| Model | Purpose |
|---|---|
| `User` | Custom user with `role` = `recruiter` or `candidate` |
| `InterviewTemplate` | A set of 3–5 questions created by a recruiter |
| `Question` | A single question belonging to a template |
| `InterviewSession` | Links one candidate to one template; tracks `assigned`/`completed` status |
| `Answer` | A candidate's answer to one question, plus generated `score` and `feedback` |

## Scoring Logic

Implemented in `interviews/utils.py`:

- If answer length > 50 characters: `score = min(7 + length/100, 10)`
- Else: `score = 3`
- Feedback: `"Good detail and structure"` (score ≥ 8), `"Adequate answer"` (6–7.99),
  `"Too brief or lacking detail"` (< 6)

## Endpoints

| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/api/auth/register/` | Any | Register as recruiter or candidate |
| POST | `/api/auth/login/` | Any | Obtain JWT access/refresh tokens |
| POST | `/api/auth/refresh/` | Any | Refresh access token |
| POST | `/api/interviews/templates/` | Recruiter | Create a template + assign a candidate |
| GET | `/api/interviews/templates/` | Recruiter | List templates you created |
| GET | `/api/interviews/my/` | Candidate | View your assigned interview |
| POST | `/api/interviews/<session_id>/submit/` | Candidate | Submit answers for a session |
| GET | `/api/interviews/<session_id>/results/` | Recruiter | View a candidate's scored results |

All endpoints except register/login require `Authorization: Bearer <access_token>`.

## Sample Workflow (curl)

```bash
# 1. Register a recruiter
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"recruiter1","password":"pass1234","role":"recruiter"}'

# 2. Register a candidate
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"candidate1","password":"pass1234","role":"candidate"}'

# 3. Login as recruiter
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"recruiter1","password":"pass1234"}'
# -> copy "access" token as RECRUITER_TOKEN

# 4. Recruiter creates a template and assigns candidate1
curl -X POST http://127.0.0.1:8000/api/interviews/templates/ \
  -H "Authorization: Bearer RECRUITER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "title": "Backend Developer Screen",
        "questions": ["Explain REST", "What is a JWT?", "Describe DRF serializers"],
        "candidate_username": "candidate1"
      }'

# 5. Login as candidate1
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"candidate1","password":"pass1234"}'
# -> copy "access" token as CANDIDATE_TOKEN

# 6. Candidate views assigned interview
curl http://127.0.0.1:8000/api/interviews/my/ \
  -H "Authorization: Bearer CANDIDATE_TOKEN"
# -> note the question IDs

# 7. Candidate submits answers
curl -X POST http://127.0.0.1:8000/api/interviews/1/submit/ \
  -H "Authorization: Bearer CANDIDATE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "answers": [
          {"question_id": 1, "text": "REST is an architectural style for building APIs using stateless HTTP requests and standard verbs."},
          {"question_id": 2, "text": "JWT"},
          {"question_id": 3, "text": "DRF serializers convert complex data types into JSON and back, validating input along the way."}
        ]
      }'

# 8. Recruiter views results
curl http://127.0.0.1:8000/api/interviews/1/results/ \
  -H "Authorization: Bearer RECRUITER_TOKEN"
```

## Security Notes

- Role enforcement via custom `IsRecruiter` / `IsCandidate` permission classes.
- Recruiters can only see templates/sessions they own; candidates can only submit to
  their own assigned session — checked with query filters (`recruiter=request.user`,
  `candidate=request.user`), not just role checks.
- Passwords hashed via Django's built-in `set_password`.
- JWT tokens short-lived by default (simplejwt defaults: 5 min access / 1 day refresh).

## Verifying Security (tested manually via Postman)

- A candidate token attempting to create a template correctly returns `403 Forbidden`.
- A recruiter token attempting to submit answers correctly returns `403 Forbidden`.
- A recruiter attempting to view another recruiter's interview results correctly returns
  `404 Not Found` (not `403`) — this avoids confirming to an unauthorized user that the
  resource even exists.

## Possible Improvements

- Rate-limit answer submission to prevent resubmission spam.
- Replace the scoring heuristic with a real LLM call (e.g. Anthropic/OpenAI API) behind
  the same `generate_feedback()` interface — no other code would need to change.
- Add OpenAPI/Swagger docs via `drf-spectacular`.
- Support multiple candidates per template rather than one-to-one.