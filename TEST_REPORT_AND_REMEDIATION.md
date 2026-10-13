# NextGenPathashala — QA and Remediation Report

**Build reviewed:** `NextGenPathashala_Study_Buddy_Course_Notes.zip` plus this iteration's changes  
**Date:** 13 October 2026  
**Review type:** Source audit, static validation, dependency-free unit tests, and added integration-test coverage. This was not a browser-driven live test.

## Executive summary

The source review found four concrete quality issues and fixed them in this iteration:

1. The course-note list returned a filename-derived ID, but the delete endpoint required a 16-character opaque ID. This made removing notes fail. The list now returns the matching ID and preserves the uploaded filename/extension.
2. Course-note retrieval split only at blank paragraphs, which made long single-paragraph notes hard to retrieve. Retrieval now uses overlapping chunks, Unicode-aware terms and a bounded context window.
3. Teacher class lists only used explicit class-teacher assignments even though other API authorization logic supported teachers assigned through existing scheduled sessions. The class query now supports both paths.
4. The statistics practice bank had two mathematically correct answer choices for a mean question, and each subject initially contained too few questions for the advertised five-question practice. The choice was corrected and the bank expanded to 40 MCQs across eight topics.

The build now also includes classroom MCQ assessments: teachers/admins publish tests to a class, students enrolled in that class can submit one attempt, the server computes the score, students receive explanations after submission, and teachers can see submitted results.

## Existing feature inventory

The codebase includes workspace registration/login/logout, tenant-scoped classes, staff/student account creation, enrollment, class/teacher assignments, subjects, timetable and application-level schedule conflict checks, attendance, homework text submissions, notices, feedback, student CSV/XLS/XLSX import, pilot inquiries, a PWA shell/offline page, health/readiness endpoints, session security settings, CSRF protection and request rate limits.

## Changes in this iteration

- Fixed course-note delete/list ID agreement and original filename display.
- Added per-account course-note limits: 20 files and 12 MiB of extracted text, in addition to the 5 MiB per-upload limit.
- Added overlapping text chunking, Unicode-aware retrieval terms, source labels and a 6,000-character context cap.
- Moved uploaded excerpts from the provider's system-role message into the user-role message and explicitly identified them as untrusted reference content.
- Added a classroom assessment model, single-attempt model, migration `0004_classroom_assessments.py`, API endpoints and frontend author/submit/review flows.
- Student API payloads do not include correct answer indexes before submission. Scoring is computed server-side; a uniqueness constraint limits each student to one attempt per assessment.
- Expanded local study practice to 40 MCQs: Python, machine learning, NLP, statistics, mathematics, science, English and commerce (five per topic).
- Fixed local score history to use a per-user browser key instead of a shared device-wide key.
- Added regression tests for course-note upload/removal/isolation/storage limits, AI chat input and configured-provider behavior, teacher assessment creation, student submission and teacher results.
- Added dependency-free tests for note metadata and retrieval. Added a Node question-bank check to the release checker and bumped the PWA cache version.

## Verification performed

| Check | Result | Detail |
|---|---|---|
| `python scripts/check_release.py` | **PASS** | Source compilation, template parse, PWA manifest/icons, referenced assets, migration markers, Study Lab/assessment wiring, unit tests, JavaScript syntax and question bank |
| Python `compileall` | **PASS** | App, configuration, helper module, application package, tests and migrations compile |
| Jinja template parse | **PASS** | All 8 templates parse |
| `node --check nextgen/static/js/app.js` | **PASS** | No JavaScript syntax error |
| Course-note helper unit tests | **PASS — 5 tests** | Stored filename metadata, malformed names, long note chunk/retrieval, Unicode terms, context limit and empty query |
| MCQ bank validation | **PASS — 40 questions** | 8 topics × 5 questions; unique IDs/options and valid answer indexes |
| Flask integration test suite | **BLOCKED** | Test collection stops with `ModuleNotFoundError: No module named 'flask'` |
| Dependency installation | **BLOCKED** | `pip install -r requirements-dev.txt` could not resolve package index DNS/network in this environment |
| SQLite migration + live API tests | **NOT RUN** | Requires Flask and installed project dependencies |
| PostgreSQL migration/runtime | **NOT RUN** | Requires a disposable PostgreSQL database and installed drivers |
| Browser/mobile/accessibility test | **NOT RUN** | No interactive browser session to exercise the live interface was available |
| Live generative AI response | **NOT RUN** | Requires the administrator's provider key and network access to the selected provider |

Note: the Flask integration tests have been added/extended, but their assertions have **not** been observed passing yet because the framework dependency is missing. They are not reported as passed.

## Feature test plan and status

| Area | Test coverage in source | Runtime verification status |
|---|---|---|
| Registration/login and duplicate emails | Existing tests | Not run in this environment |
| Classes, users, enrollment, timetable and conflicts | Existing tests | Not run in this environment |
| Teacher/student permissions and tenant isolation | Existing tests; assessment isolation tests added | Not run in this environment |
| Attendance, homework, notices and feedback | Existing tests | Not run in this environment |
| Bulk student import | Existing tests | Not run in this environment |
| Study-note upload/validation/list/delete/isolation | New regression tests | Not run in this environment; pure metadata/retrieval helpers passed unit tests |
| AI chat input, configuration and notes prompt context | New mock-provider regression test | Not run in this environment |
| Classroom assessment creation/attempt/scoring/results | New integration tests | Not run in this environment |
| Practice question bank | Node validator | Passed the 40-question static validation |
| Desktop/mobile UI, keyboard navigation and offline behavior | Manual test required | Not run |

## Remaining gaps before using real student data

- Run `python -m pip install -r requirements-dev.txt` in a network-enabled environment, then `python scripts/check_release.py` and `python -m pytest -v`.
- Apply migration `0004_classroom_assessments` against disposable SQLite and staging PostgreSQL databases; test upgrade and backup/restore procedures. Do not reset a database with data to try a migration.
- Exercise the entire admin → teacher → student journey in a browser and verify CSRF/session behavior, mobile layout and browser-console/network errors.
- Configure a server-only `STUDY_AI_API_KEY`, then test correct, ambiguous, adversarial and notes-grounded questions. The system cannot guarantee every AI answer is correct.
- Classroom assessments are MCQ-only and permit one submission; time-limit enforcement, draft/regrade workflows, essays and a full gradebook are not implemented.
- Password-reset emails, email verification, invitations, parent accounts, shared rate-limit storage, push notifications and reliable offline write synchronization remain gaps.
- Uploaded notes are stored on the server filesystem. Production use requires persistent/private storage, backups, retention/deletion policy and a privacy review.

## Release recommendation

This is a stronger development/pilot build with concrete bug fixes and broader learning/assessment workflows. It is **not certified production-ready or a verified 5/5 release yet** because the full Flask suite, database migrations, live AI call and browser workflows remain untested. Use fictional data until those gates pass.
