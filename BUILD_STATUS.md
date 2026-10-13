# Build and verification status

## Implemented in the current working tree

- Public product landing page with honest early-access messaging, segment-specific explanations, test-workspace CTA and pilot inquiry form.
- Private pilot inquiry inbox restricted to the configured `PILOT_ADMIN_EMAIL` workspace administrator.
- In-app feedback for authenticated users, plus an administrator review panel for feedback from the same workspace.
- Flask application factory, modular web/API Blueprints and PostgreSQL-ready SQLAlchemy models.
- PostgreSQL URL normalization to the installed psycopg 3 dialect.
- Production configuration guard for weak/missing session secret and non-secure session cookies.
- Login, registration and public pilot-request route rate limits. Default rate-limit storage is in-memory and is only suitable for a small single-worker pilot.
- Institution-scoped user and record queries, password hashing, CSRF protection, security headers, liveness and database-readiness endpoints.
- Class and batch management, enrollment, teacher-class assignments, scheduled sessions and application-level clash checks. Reactivating a cancelled session now rechecks for conflicts.
- Attendance marking/history/reporting, assignment creation/text submission, class-targeted and institution-wide notices.
- Corrected default-date fallback for invalid stored timezone names and dashboard assignment count semantics.
- Added a private AI Study Buddy backed by an OpenAI-compatible API configuration, private course-note upload and lexical RAG retrieval with storage limits.
- Added classroom MCQ assessments with server-side scoring, one submission per student, deadline checks, review explanations and teacher result views.
- Added 40 local practice questions across eight topic areas, with five questions per topic and per-account local score-history separation.
- Responsive dashboard and marketing landing page, integrated Lovable-inspired design layer, light/dark theme and mobile bottom navigation; PWA manifest/icons and privacy-first service-worker fallback (merged stylesheet included in app-shell cache).
- Protected CSV/XLS/XLSX student import with preview, server-side validation, partial success reporting, class enrollment and one-time temporary credentials; tests added for admin success/partial import and student-role denial.
- Added a class-scoped subject catalog with a migration that seeds subjects from existing session rows, subject suggestions for scheduling/homework, and explicit teacher-to-class assignment endpoints/UI.
- Explicit Alembic migrations with scoped downgrade operations, plus a migration for teacher-class assignments and feedback/pilot intake.
- Tester guide, shareable pilot invitation copy, deployment audit and a dependency-light static release-check script.
- Regression tests covering key workflows, institution isolation, timezone/URL handling, pilot inquiry intake, feedback and cancelled-session reactivation conflicts.

## Checks performed

- Python compileall syntax check: passed.
- JavaScript `node --check`: passed.
- Service-worker cache list updated and static asset verification confirms `lovable-ui.css` is present.
- Python and JavaScript syntax/static checks re-run after adding subject, staff assignment, AI Study Buddy and classroom assessment workflows.
- Fixed a missing `SQLAlchemyError` import referenced by the student-import database error handler.
- Jinja template parsing: passed (8 templates).
- PWA manifest/icon validation and required static asset checks: passed.
- Dependency-free course-note unit tests: 5 passed. MCQ bank checker: 40 questions across 8 topics passed. Alembic revision links pass structural validation.
- Render YAML parsed successfully.
- SQLite migration chain through revision 0002 (upgrade, downgrade of revision 0002, and full downgrade): passed in an earlier available SQLAlchemy/Alembic environment. Migrations 0003 subject-catalog and 0004 classroom assessments have not been runtime-tested in this environment.

## Runtime verification still required

Full Flask application tests (including the newly added import, subject and teacher-assignment tests) could not be executed in the current workspace because Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-WTF and Flask-Limiter are not installed, and package downloads are unavailable. Run `pip install -r requirements-dev.txt`, `python scripts/check_release.py`, and `pytest -q` in a clean environment. Then test the same migration/API workflows against PostgreSQL before a public pilot.

## Remaining production limitations

- No email verification, password reset or expiring account-invitation workflow.
- No private object storage/file attachments, parent/guardian accounts, fee management or examination management.
- No native push notification delivery or complete offline write/synchronization system.
- Timetable conflict detection is application-level; add database-level concurrency protection before multi-instance/high-volume scheduling.
- In-memory rate-limit storage is not shared among app instances. Configure Redis or an equivalent shared store before scaling.
- Pilot inquiries are stored for manual follow-up; no confirmation email is sent automatically.
- Do not use real student records or replace official attendance registers until runtime verification, privacy review, backup recovery testing and operational support arrangements are complete.

## QA remediation update — 13 October 2026

- Fixed Study Material list/delete ID mismatch and preserved source filename extensions.
- Improved long-document and Unicode note retrieval, added per-account upload quotas, and treated uploaded note excerpts as untrusted context in the AI request.
- Added teacher-created classroom MCQ assessments and end-to-end regression-test cases for publishing, student submission, scoring, result review, role permissions and institution isolation.
- Fixed the teacher class listing compatibility path and corrected/expanded the practice question bank.
- Static release checks and five dependency-free helper tests pass. Full Flask integration tests still cannot collect because Flask is missing and package download DNS is unavailable; PostgreSQL, browser and live AI tests remain outstanding. See `TEST_REPORT_AND_REMEDIATION.md` for the test matrix and release gates.
