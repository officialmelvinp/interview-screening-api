# Interview Screening API

## Scope, inspection, and uncertainty

This documentation was derived only from `interviews/models.py`,
`serializers.py`, `views.py`, `permissions.py`, `urls.py`, and `utils.py`.
The routes below are those declared in `interviews/urls.py`; a project-level
prefix is not claimed because project configuration was intentionally excluded.

Authentication transport is not defined in the inspected files. Thus,
“authenticated” means the request resolves to an authenticated Django user.
Role authorization is exact: `recruiter` or `candidate`. Examples are JSON;
timestamps are Django ISO-8601 datetimes and identifiers are integers.

## `POST /auth/register/`

Role: public (`AllowAny`), so there is no role-denied case.

Required request fields are `username`, `password`, and `role`; role must be
`recruiter` or `candidate`. Password is write-only.

```json
{"username":"ada","password":"a-strong-password","role":"candidate"}
```

Success — `201 Created`:

```json
{"id":12,"username":"ada","role":"candidate"}
```

Validation failure — `400 Bad Request`, for example:

```json
{"role":["\"manager\" is not a valid choice."]}
```

## `GET /interviews/templates/`

Role: authenticated recruiter. Candidates and unauthenticated callers are
denied (`403 Forbidden`):

```json
{"detail":"You do not have permission to perform this action."}
```

It lists only templates owned by the current recruiter. Nested questions are
ordered by `order`.

Success — `200 OK`:

```json
[{"id":7,"title":"Backend screen","created_at":"2026-09-14T00:00:00Z","questions":[{"id":31,"text":"Describe a REST API.","order":0}]}]
```

## `POST /interviews/templates/`

Role: authenticated recruiter. Candidates and unauthenticated callers receive
the same `403` JSON above.

Required fields: `title`, `candidate_username`, and `questions`. `questions`
must be a list of 3–5 strings. `candidate_username` must be an existing user
with candidate role. A successful request creates the template (owned by the
current recruiter), questions ordered from zero, and one assigned session for
the candidate.

```json
{"title":"Backend screen","candidate_username":"ada","questions":["What is REST?","How do you test an API?","Explain indexes."]}
```

Success — `201 Created` (write-only fields are omitted):

```json
{"id":7,"title":"Backend screen"}
```

Unknown/non-candidate username — `400 Bad Request`:

```json
{"candidate_username":["No candidate found with that username."]}
```

## `GET /interviews/my/`

Role: authenticated candidate. Recruiters and unauthenticated callers receive
the `403` JSON above. It returns the candidate’s most recently-created session,
regardless of status.

Success — `200 OK`:

```json
{"id":19,"template_title":"Backend screen","status":"assigned","questions":[{"id":31,"text":"What is REST?","order":0}]}
```

No assigned session — `404 Not Found`:

```json
{"detail":"No interview assigned."}
```

## `POST /interviews/{session_id}/submit/`

Role: authenticated candidate. Recruiters and unauthenticated callers receive
the `403` JSON above. `session_id` is an integer and must belong to the current
candidate. The `answers` list and each item’s integer `question_id` and string
`text` are required. Every question must be in that session’s template.

```json
{"answers":[{"question_id":31,"text":"REST models resources and uses standard HTTP methods with clear status codes."}]}
```

Success — `201 Created`:

```json
{"detail":"Answers submitted successfully."}
```

Missing/not-owned session — `404 Not Found`:

```json
{"detail":"Interview session not found."}
```

Completed session — `400 Bad Request`:

```json
{"detail":"Interview already submitted."}
```

Foreign question — `400 Bad Request` (the id is interpolated):

```json
{"detail":"Question 99 does not belong to this interview."}
```

Safe-change detail: the implementation does not require every template
question to be answered. It upserts each supplied `(session, question)` answer,
then completes the session. Scores are `3.0` for text length <=50; otherwise
`round(min(7 + length / 100, 10), 2)`. Feedback is “Too brief or lacking
detail” below 6, “Adequate answer” from 6 through <8, otherwise “Good detail
and structure.”

## `GET /interviews/{session_id}/results/`

Role: authenticated recruiter. Candidates and unauthenticated callers receive
the `403` JSON above. The session must be under a template owned by the current
recruiter; non-existent and other-recruiter sessions both return `404`.

Success — `200 OK`:

```json
{"id":19,"candidate_username":"ada","status":"completed","answers":[{"question_text":"What is REST?","text":"REST models resources and uses standard HTTP methods.","score":7.53,"feedback":"Adequate answer"}]}
```

Not found/not owned — `404 Not Found`:

```json
{"detail":"Session not found."}
```

## Model constraints relevant to changes

- User deletion cascades to templates and candidate sessions; template deletion
  cascades to questions and sessions; session deletion cascades to answers.
- `(session, question)` is unique, so a session has at most one answer per
  question.
- Session status is `assigned` or `completed`, defaulting to `assigned`.
- `score` and `feedback` allow null/blank at model level, though submission
  always provides both.
