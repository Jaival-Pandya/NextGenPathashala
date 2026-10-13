# Changelog

## Updated early-access build — 11 October 2026

### Product and tester experience
- Replaced the patent-search homepage with a public NextGenPathashala landing page.
- Explained the four current workflows: timetable, attendance, homework and notices.
- Added a pilot inquiry form and a private inbox for the configured product-owner account.
- Added in-app tester feedback and a workspace-admin review panel.
- Added an early-tester guide and a tailored invitation/demo script for schools, colleges and tuition institutes.

### Reliability and code quality
- Normalized PostgreSQL URLs to SQLAlchemy's psycopg 3 dialect.
- Replaced dynamic initial-schema create/drop calls with explicit migration operations.
- Added `/ready` for a basic database-readiness check, separate from `/health`.
- Added a safe timezone fallback for invalid institution timezone values.
- Centralized scheduling conflict checks and revalidated them when reactivating a cancelled session.
- Corrected assignment count semantics and removed misleading staff overdue badges.
- Added basic route-level rate limits for login, workspace registration and public pilot requests.
- Added `scripts/check_release.py` for Python syntax, Jinja, PWA manifest/icon and optional Node syntax checks.
- Added regression coverage for timezone fallback, database URL normalization, user feedback, public pilot intake and cancelled-session conflict checks.

### Still not production-complete
- Runtime Flask tests and PostgreSQL integration must pass in a clean environment; the current workspace could not download missing dependencies.
- Add shared rate-limit storage before scaling beyond a small single-worker pilot.
- Email verification, password reset, invitations, file attachments, parent accounts, native push notifications and full offline writes remain future work.
- Run a privacy/security review, configure backups and prove restoration before using real student data.

### Lovable UI and feature consolidation — 11 October 2026
- Adopted the supplied Lovable UI stylesheet as a design layer for the Flask dashboard: typography, indigo/mint theme, card treatments, light/dark mode and mobile bottom navigation.
- Kept the existing Flask/Jinja routes and element IDs as the canonical app instead of loading the prototype SPA alongside it.
- Ported the prototype's CSV/XLS/XLSX student-import idea into the authenticated Flask API with preview, row validation, duplicate handling, class enrollment, one-time server-generated temporary credentials and a downloadable CSV response.
- Added a class-scoped subject catalog, migrated existing session subjects into it, wired subject suggestions into session/homework forms, and added explicit class-to-teacher assignments.
- Added regression tests for successful/partial import and student-role denial, plus subject catalog/teacher assignment flows.
- Bumped the service-worker cache and added the merged UI stylesheet to the offline app shell cache.
- Fixed a missing `SQLAlchemyError` import in the student-import commit-failure handler.
- Documented the prototype's shared Supabase state and browser-side password handling so they are not accidentally re-enabled in the production path.

## 2026-10-12 — Registration reliability patch
- Added early validation for malformed email addresses, overlong names, and passwords longer than 128 characters.
- Detects an existing global login email before attempting to create an institution, and gives the user a clear sign-in/use-another-email next step.
- Handles concurrent duplicate-email registration safely via `IntegrityError` rollback.
- Improved the generic database-failure message without exposing SQL or database internals.
- Added regression tests for duplicate email, invalid email, and overlong passwords. Run these with `pytest` in an environment where `requirements-dev.txt` is installed.

## 2026-10-13 — Study Lab and tester remediation
- Added Study Lab navigation and in-app study helper, topic-based MCQ practice and mixed mock test with immediate explanations.
- Added device-local score history; scores are not synced to the server.
- Bumped service-worker cache version for updated Study Lab assets.
- Expanded static release checks for Study Lab UI/handlers and service-worker cache revision.
- Added `TEST_REPORT_AND_REMEDIATION.md` with verified checks, blocked runtime tests, feature inventory, risks and acceptance plan.


## 2026-10-13 — Assessment workflow, note retrieval and regression coverage

- Fixed a course-note removal bug: list APIs now return the opaque 16-character document ID expected by the delete endpoint, and the original filename (including extension) is preserved for display.
- Added per-user course-note quotas (20 documents and 12 MiB extracted text) in addition to the existing per-file request size limit.
- Reworked course-note retrieval to use overlapping chunks, Unicode-aware terms, bounded context size and better matches from long single-paragraph notes.
- Moved uploaded note excerpts into the user-role message so they are treated as untrusted reference data rather than being concatenated into the system-role content.
- Added teacher-created classroom MCQ assessments, server-side scoring, one submission per student, due-date checks, student feedback with explanations, and class-scoped teacher result review. Added migration `0004_classroom_assessments`.
- Expanded local practice questions to eight topic areas (Python, machine learning, NLP, statistics, mathematics, science, English and commerce), with five questions per topic. Fixed an ambiguous mean question that had two mathematically correct choices.
- Added automated test cases for note upload/delete and isolation, chat validation/configuration, and the assessment author → student submit → teacher review workflow. Added dependency-free unit tests for note metadata and retrieval.
- Fixed teacher class listing so current scheduled-teacher assignments work alongside explicit class-teacher assignments. Bumped the PWA shell cache for the new assets.
- Verification in this environment: dependency-free unit tests pass; Python compilation, template parsing, JavaScript syntax, PWA assets and release checks pass. Full Flask/DB integration tests remain unrun because the environment cannot download Flask dependencies.
