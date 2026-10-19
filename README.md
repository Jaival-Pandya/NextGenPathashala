# NextGenPathashala — Early-access education management PWA

NextGenPathashala is an early-access web application for schools, colleges and tuition/coaching institutes. It brings the first four daily workflows into one workspace: timetable, attendance, homework and notices. The public home page explains the product, lets visitors request a pilot conversation, and points interested teams to their own isolated test workspace.

> **Pilot safety:** The application is an MVP that still needs full runtime and security verification. Use fictional or otherwise authorized test data only. Do not replace an institution's official registers or upload sensitive student records until reliability, privacy, backups and recovery have been reviewed and tested.

## What is included

- Public landing page with institution-specific value propositions and a guided early-access request form.
- Institution workspace registration, login/logout and server-side sessions.
- Self-service password changes for signed-in users, with current-password verification.
- Role-aware administrator, teacher and student workflows.
- Class and batch management, class-scoped subject catalog (seeded from existing scheduled subjects), explicit class-to-teacher assignments, student enrollment, session scheduling and basic conflict checks.
- Teacher-created classroom MCQ assessments, server-side scoring, one submission per student, answer explanations, deadlines and class-scoped result review.
- Attendance register, student attendance history, and attendance reports.
- Homework creation and text submissions.
- Institution-wide and class-targeted notices.
- In-app feedback submitted by testers; workspace administrators can review feedback from their own institution.
- Optional platform-owner pilot inbox and usage/feedback dashboard, gated by `PILOT_ADMIN_EMAIL`.
- Responsive PWA shell with a manifest, icons, static asset caching, and an offline fallback that does not cache private dashboard or API data.
- PostgreSQL support using psycopg 3, versioned migrations, liveness/readiness endpoints and Render configuration.
- Basic rate limits on login, registration and the public pilot request form; memory storage is only for a small single-worker pilot.
- A dependency-light `scripts/check_release.py` for syntax/template/PWA asset checks.

## Technology

- Python 3.11 or later
- Flask, Flask-SQLAlchemy, Flask-Migrate and Flask-WTF
- SQLAlchemy + PostgreSQL (`psycopg` 3); SQLite is used locally by default
- Vanilla JavaScript, HTML and CSS
- Gunicorn for the production WSGI process

## Run locally (Windows PowerShell)

Run these commands from the project root, the folder containing `app.py` and `requirements.txt`. In this downloaded workspace, if your terminal is at the outer `NextGenPathashala_QA_Fixed_Assessments` folder, first run:

```powershell
Set-Location 'D:\Downloads\NextGenPathashala_QA_Fixed_Assessments\NextGenPathashala\NextGenPathashala'
```

Confirm the location with `Test-Path .\app.py` (it should return `True`). Then continue:

```powershell
if (-not (Test-Path .\.venv\Scripts\python.exe)) { py -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `.env` and replace the placeholder `SECRET_KEY` with a random value. Set `PILOT_ADMIN_EMAIL` to the email address you will use for your owner/admin account. For example, generate a secret with:

```powershell
& .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then create the local schema and start the app:

```powershell
& .\.venv\Scripts\python.exe scripts/check_release.py
& .\.venv\Scripts\python.exe -m flask --app app db upgrade
& .\.venv\Scripts\python.exe -m pytest -v
& .\.venv\Scripts\python.exe app.py
```

Keep the terminal running `app.py` open while using the app. To run it again later, open PowerShell, change to the project root with `Set-Location 'D:\Downloads\NextGenPathashala_QA_Fixed_Assessments\NextGenPathashala\NextGenPathashala'`, then run `& .\.venv\Scripts\python.exe app.py`.

Open `http://127.0.0.1:5000`. The landing page has two paths:

- **Create a test workspace** — register an administrator account to try the actual workflows.

- **Request a pilot conversation** — submit the public form if you want to speak with the product owner before testing.

If PowerShell blocks environment activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` for the current terminal only, or activate `.venv\Scripts\activate.bat` from Command Prompt.

## Run locally (macOS/Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
if [ ! -f .env ]; then cp .env.example .env; fi
# Edit .env and replace SECRET_KEY with a random value.
```

If `.env` already exists, keep it and edit it rather than copying over it. Set `PILOT_ADMIN_EMAIL` to your owner/admin account email. Then run:

```bash
python scripts/check_release.py
python -m flask --app app db upgrade
python app.py
```

## Ten-minute tester workflow

1. Register a **test workspace** with a unique email.
2. Open **Classes & people** and create one class/batch.
3. Add one teacher and one fictional student account.
4. Enroll the student into the class.
5. Open **Timetable** and schedule one session, assigning the teacher.
6. Sign out and sign in as the teacher in a separate browser profile; open Attendance and mark the sample student.
7. Publish one homework assignment and one class-targeted notice.
8. Sign in as the student and confirm that the timetable, attendance, homework and notice are visible.
9. Open **Study Lab**. A teacher/admin can create a class MCQ assessment, publish it and review submissions; a student in that class can take it once and view explanations after submitting.
10. Open **Practice MCQs** and confirm five questions are available in each topic: Python, ML, NLP, statistics, mathematics, science, English and commerce.
11. Open **Study Buddy** to ask a study question or upload a disposable TXT note. Verify it appears with its extension, ask a question using terms from the note, then remove it and confirm it disappears.
12. Open **Feedback** and report any bug, confusing control or missing workflow. Sign in as the workspace administrator and review feedback submitted by your test users.

Use fictional names and email addresses whenever possible. Never test using real children’s records without the institution's authorization and an appropriate privacy/safeguarding process.

## Pilot request inbox for the product owner

The landing page saves requests to the `pilot_inquiries` table. To see the private inbox:

1. Set `PILOT_ADMIN_EMAIL` to the email address you will use for your own workspace administrator.
2. Register/sign in using that same email.
3. Open the workspace dashboard. A **Pilot inquiries** link will appear in the footer.
4. Update each inquiry's status as you contact the person, invite them to a pilot, or close the request.

See `PILOT_INVITE.md` for short invitation copy, a tailored demo script, discovery questions and answers to common objections. `TESTER_GUIDE.md` gives a step-by-step test flow. The form intentionally does not collect student data. This MVP does not automatically send confirmation emails; the inbox displays contact email links so follow-up can be handled manually. Login, registration and pilot-request routes have basic IP rate limits. The default `memory://` limiter is appropriate only for a small single-worker pilot; verify client IP detection behind the hosting proxy, use shared Redis-backed storage, and add bot monitoring before scaling or running a larger public campaign.

The same configured owner account sees **Owner analytics** in the dashboard footer. It shows 14-day recorded workflow actions, daily and 7-day active users, and feedback grouped by AI-assigned category. Activity counts come from audit events; sign-ins and page views are not currently tracked. AI feedback categorization is started manually and requires confirmation. It sends feedback text, but not reporter names, emails or institution details, to the configured Study Buddy provider; review reports before approving processing. Apply the latest migration with `python -m flask --app app db upgrade` before opening the dashboard.

## Verify the project before deployment

Run these commands in PowerShell from the project root, the folder containing `app.py`. If your terminal is at the outer `NextGenPathashala_QA_Fixed_Assessments` folder, first run the `Set-Location` command below. These commands explicitly use the project virtual environment so Flask extensions are loaded from the same environment as the app.

```powershell
Set-Location 'D:\Downloads\NextGenPathashala_QA_Fixed_Assessments\NextGenPathashala\NextGenPathashala'
.\.venv\Scripts\Activate.ps1
Test-Path .\app.py
& .\.venv\Scripts\python.exe -m compileall -q app.py config.py extensions.py nextgen tests migrations
node --check nextgen/static/js/app.js
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m flask --app app db upgrade
```

The integration tests require packages in `requirements-dev.txt` and should be run in a virtual environment. Test migrations against a disposable SQLite database and, before production, also validate the PostgreSQL URL/driver and run the suite against PostgreSQL. A syntax pass is not proof that requests, migrations or database constraints work in a live runtime.

### Database driver behavior

`requirements.txt` installs psycopg 3. The configuration normalizes Render's `postgres://` and `postgresql://` URLs to SQLAlchemy's `postgresql+psycopg://` dialect. Never log the complete database URL because it can contain credentials.

### Migration caution

The included `0001_initial_schema` is an explicit baseline and `0002_pilot_feedback_and_class_teachers` adds teacher-class assignments and tester feedback tables. This package assumes no production data has been placed in this project yet. If a database has been shared or used beyond disposable testing, back it up and inspect its current Alembic revision before changing or rolling back migrations. Never use a blanket database reset on a shared database.

## Render deployment

1. Commit and push the project to a private or public Git repository of your choice.
2. Create a Render Blueprint from `render.yaml` or set up the web service and managed PostgreSQL database manually.
3. Ensure `DATABASE_URL` points to that PostgreSQL database. The Blueprint generates `SECRET_KEY`, enables secure session cookies, sets `APP_ENV=production`, uses `/ready` for deployment readiness, and prompts for `PILOT_ADMIN_EMAIL`.
4. Set `PILOT_ADMIN_EMAIL` to your own workspace administrator's email if you want to use the private pilot-inquiry inbox.
5. The current MVP start command applies migrations and then starts Gunicorn. For multiple instances or more complex rollouts, use a controlled pre-deploy/one-off migration step supported by your hosting plan, and do not allow multiple workers to race to run migrations.
6. Check `/health` for process liveness and `/ready` for database readiness.
7. Test registration, sign-in, all four daily workflows, cross-institution access restrictions, feedback submission, pilot inquiry intake and PWA installation before inviting external testers.

For production use, select the actual service plan in your hosting dashboard, configure automated database backups and retention, test restoration, add monitoring/alerts and document who responds to urgent issues. Public registration and lead intake now have basic route-level rate limits. Configure shared Redis-backed limiter storage, monitoring and bot protection before scaling beyond a small single-worker pilot.

## Known MVP limitations

- No email verification, email-based password recovery or expiring invitation flow. Signed-in users can change their password from the Account section.
- No private file/object storage for attachment uploads; assignments currently use text responses.
- No native push notification delivery or complete offline write/synchronization system. The service worker caches the merged UI CSS and app shell; it never caches private API responses or authenticated dashboard HTML.
- No parent/guardian accounts, fee management, full gradebook, essay grading, timed attempt start/stop enforcement or recurring weekly timetable generator. Classroom assessments currently support multiple-choice questions only and allow one submission per student.
- Timetable conflict checks are application-level MVP checks; strict concurrent scheduling needs additional database-level enforcement.
- Usage analytics count recorded workflow actions, not sign-ins or page views, so they do not represent every visit.
- The public pilot request form stores submissions in the database and does not automatically send email.
- Runtime tests and full PostgreSQL integration still must pass in an environment with dependencies installed before production use.

## Project structure

```text
app.py                                  # WSGI entry point
config.py                               # environment config + PostgreSQL driver URL normalization
extensions.py                           # SQLAlchemy, migrations, CSRF
nextgen/__init__.py                     # app factory, security headers, health/readiness
nextgen/models.py                       # institutions, users, classes, timetable, feedback models
nextgen/web.py                          # landing, pilot intake, login and workspace pages
nextgen/api.py                          # authenticated versioned API
nextgen/templates/home.html             # public explainer and pilot form
nextgen/templates/dashboard.html        # authenticated classroom dashboard
nextgen/templates/pilot_inquiries.html  # configured owner-only intake inbox
nextgen/static/css/                     # responsive dashboard + public landing + merged Lovable UI CSS
nextgen/static/js/app.js                # API-connected user workflows + protected student import
nextgen/static/manifest.webmanifest     # PWA metadata
nextgen/static/sw.js                    # privacy-first app shell cache
migrations/versions/                    # schema migrations, subject catalog backfill and classroom assessments
study_content.py                         # dependency-free chunking and course-note retrieval helpers
scripts/check_release.py                # syntax, template and PWA-asset checks
tests/                                  # automated integration tests
```


## AI Study Buddy configuration

The Study Buddy supports open-ended questions through an OpenAI-compatible chat-completions API, including local Ollama. Configure these environment variables in your **server/hosting dashboard** (not in frontend JavaScript):

- `STUDY_AI_PROVIDER` — defaults to `openai`; set to `ollama` to use a local Ollama server.
- `STUDY_AI_API_KEY` — secret provider API key; optional for Ollama.
- `STUDY_AI_BASE_URL` — defaults to `https://api.openai.com/v1`, or `http://localhost:11434/v1` for Ollama.
- `STUDY_AI_MODEL` — defaults to `gpt-4o-mini`, or `llama3.2:3b` for Ollama.
- `STUDY_AI_TIMEOUT_SECONDS` — defaults to `25`.
- `STUDY_WEB_SEARCH_API_KEY` — optional Brave Search API key. Web search runs only when private uploaded-note retrieval finds no match.
- `STUDY_WEB_SEARCH_TIMEOUT_SECONDS` — defaults to `5`; a failed or timed-out search does not prevent a general AI answer.

For Ollama, install and run Ollama on the same machine/network accessible to the app server, then pull the configured model (for example, `ollama pull llama3.2:3b`). `localhost` means the machine running the Flask app, not an individual student's device. Restart/redeploy the server after setting configuration. Never commit a real API key or place it in HTML/JavaScript. The chat endpoint requires a signed-in user, CSRF validation, a 2,000-character question limit and a rate limit. Hosted provider usage may incur charges. AI can make mistakes; students should verify course-specific answers with their instructors and notes.

## Study Buddy: ask questions from your own course notes

The Study Buddy page supports private course-note uploads for TXT, Markdown (`.md`), and text-based PDF files (up to 5 MB each). Uploaded material is stored under the current user's institution and user ID in the Flask `instance/study_materials/` directory; another user cannot list or retrieve those files through the API. PDF text extraction requires `pypdf`, included in `requirements.txt`. Scanned/image-only PDFs are not OCR'd and should be converted to searchable PDFs or text first.

After signing in, open **Study Buddy → Ask from your course notes**, upload notes, then ask a question referencing the chapter or topic. Study Buddy first uses keyword-overlap retrieval to attach up to two relevant note sections (3,200 characters total) to the AI prompt. If no note section matches and `STUDY_WEB_SEARCH_API_KEY` is configured, it searches Brave and passes at most three short result snippets (2,600 characters total) to the AI. Web search is optional; without the key, the assistant answers from its model as before. This is a lightweight RAG implementation, not a semantic vector database; if retrieval misses a relevant section, rephrase the question with terms used in the notes. The question is sent to Brave only on the no-note-match fallback, so avoid including sensitive information. Configure keys on the server; never put provider secrets in frontend code or ask students to enter them.

Uploaded notes may contain copyrighted or sensitive content. Upload only material the institution/student is permitted to use. Files live on the server filesystem, so persistent production hosting needs a persistent disk or a future object-storage integration. Add backups and a retention policy before a real student pilot.
