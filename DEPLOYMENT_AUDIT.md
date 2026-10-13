# NextGenPathashala — Deployment Audit and Remediation Status

**Updated:** 11 October 2026  
**Scope:** Current working tree: Flask application factory, SQLAlchemy models, API and web routes, templates, JavaScript, PWA assets, migrations, Render Blueprint and tests.

## Executive summary

The current working tree resolves several issues identified in the earlier audit: PostgreSQL URLs are normalized for psycopg 3, the initial schema is explicitly declared in Alembic rather than delegated to `metadata.create_all()`, the timezone fallback is centralized, the dashboard count reflects all matching assignments, a misleading staff-side overdue indicator has been removed, and cancelled-session reactivation rechecks scheduling conflicts. Basic rate limits, a public pilot-information page, lead intake, in-app feedback and tester instructions have also been added.

**This is not yet a fully runtime-verified production release.** The full Flask test suite must pass in an environment with all requirements installed, and PostgreSQL integration and security/recovery tests remain necessary.

## Remediations in this version

### Resolved in source

1. **PostgreSQL driver normalization.** `config.py` maps `postgres://` and `postgresql://` to `postgresql+psycopg://`, matching `psycopg[binary]` in `requirements.txt`. A regression test covers the URL transformation.
2. **Migration safety.** `0001_initial_schema.py` explicitly creates its tables/indexes, and its downgrade enumerates only its own tables. `0002_pilot_feedback_and_class_teachers.py` adds teacher assignments and feedback/pilot inquiry tables with its own scoped downgrade. The migration chain was exercised using SQLAlchemy/Alembic with SQLite. If a shared database already has migration history, back up and inspect its revision before changing anything; never reset a database containing data.
3. **Production secret guard.** The app refuses production startup with the known development secret, a weak secret, or non-secure session cookies.
4. **Database readiness.** `/health` reports liveness; `/ready` checks a trivial database query and returns 503 on a SQLAlchemy database error.
5. **Timezone robustness.** Invalid stored timezone identifiers fall back to `Asia/Kolkata` for date-bound calculations and datetime serialization.
6. **Timetable status change.** Reactivating a cancelled session rechecks class/teacher/room overlaps and returns 409 when it would conflict. This remains application-level conflict checking; database-level concurrency protection is still recommended before scaling.
7. **Dashboard assignment totals.** The stats endpoint counts all relevant assignments rather than the dashboard preview limit. Staff cards do not claim an assignment is overdue without submission aggregates.
8. **Public pilot conversion and feedback.** The landing page explains the four first-release workflows and invites users to create a test workspace or request a pilot conversation. Pilot requests are stored in a configured owner-only inbox; signed-in testers can submit feedback and their workspace administrator can review it.
9. **Abuse controls.** Basic Flask-Limiter rate limits protect login, registration and the public inquiry route. The default `memory://` backend is suitable only for a small single-worker pilot; configure shared Redis-backed storage before running multiple workers/instances.
10. **Static release check.** `scripts/check_release.py` checks Python compilation, Jinja syntax, PWA manifest/icon integrity and JavaScript syntax when Node is available.

## Verification status

- Python syntax compilation: passed.
- JavaScript syntax check: passed in the available Node environment.
- Migration upgrade/downgrade checks on SQLite: passed in the available SQLAlchemy/Alembic environment.
- Full Flask/pytest execution: **not run successfully** because Flask and Flask extensions are unavailable in the current environment and package downloads were blocked. This must be completed locally or in CI after installing `requirements-dev.txt`.
- PostgreSQL runtime integration: not yet verified.
- Live Render deployment and browser/PWA installation: not performed from this workspace. The source bundle can be deployed by the repository owner, but no live website is being claimed here.

## Remaining blockers before using real student data

- Run `pip install -r requirements-dev.txt`, `python scripts/check_release.py` and `pytest -q` in a clean virtual environment.
- Apply migrations to a disposable PostgreSQL instance and exercise registration, roles, classes, session conflict checks, attendance, homework, notices, feedback and institution isolation.
- Add database-level protection for concurrent timetable booking if multi-worker/scale usage is planned.
- Configure shared rate-limit storage before scaling beyond a single worker.
- Add email verification, password reset, secure invitation flows, file/object storage, parent accounts and notifications as needed by the selected pilot institution.
- Configure backups, restoration drills, monitoring, operational support and data retention/consent procedures.
- Keep the existing official registers as the source of truth during the early pilot, and use fictional or properly authorized test data.

## Release command sequence

```powershell
pip install -r requirements-dev.txt
python scripts/check_release.py
pytest -q
flask --app app db upgrade
python app.py
```

For production, verify the PostgreSQL URL, `SECRET_KEY`, `APP_ENV=production`, `SESSION_COOKIE_SECURE=true`, and `PILOT_ADMIN_EMAIL`. Render uses `/ready` as its deployment health check. The current Render start command applies migrations before Gunicorn, which is a temporary compromise for a simple single-instance MVP; use a controlled pre-deploy/one-off migration step when supported by the selected hosting plan.
