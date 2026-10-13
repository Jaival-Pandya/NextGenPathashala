# Feature merge matrix — NextGenPathashala

| Area | Flask MVP | Supplied Lovable prototype | Consolidated choice |
|---|---|---|---|
| Authentication | Server-side accounts, password hashing, sessions, CSRF | Browser-side profiles/password comparisons | Keep Flask authentication; do not use client-side password storage |
| Institution isolation | Institution-scoped models and API checks | Single shared `app_state` row in provided source | Keep Flask's institution-scoped architecture |
| UI | Existing responsive dashboard and landing page | Indigo/mint theme, glass-like cards, theme toggle, mobile bottom navigation | Adopt supplied theme and mobile navigation in dashboard |
| Timetable | API-backed sessions and conflict checks | Rich schedule UI, data currently client-side | Keep Flask sessions; plan recurring timetable rules separately |
| Attendance | Session register, statuses, history, report | Batch register, attendance percentage and invite requests in client state | Keep server-backed attendance; invite flow deferred |
| Student setup | Create users and enroll individually | XLS/XLSX/CSV import helper | Add protected CSV/Excel import via Flask API |
| Subjects and staff | Session assignment creates a teacher/class link; subjects were free text | Per-class subject management and staff assignment | Add class-scoped subject catalog, subject suggestions for session/homework, and explicit teacher assignment APIs |
| Homework | Persistent assignments and text submissions | Tests/submissions are richer, but stored in shared state | Keep MVP assignments; file submissions and grading later |
| Notices | Institution/class notices | Notice board, client-side state | Keep server-backed notices; read receipts and push later |
| Notes / syllabus | Not available yet | Notes, syllabus topics, PDFs | Defer until private attachment storage and server-side models exist |
| Tests / viva / weak topics | Not available yet | MCQ tests, viva sessions, insights, mock quizzes | Defer pending normalized data models, secure authorization and tests |
| AI and voice | Not a core MVP requirement | External AI and voice helpers | Add only through consent-aware, rate-limited backend services; do not expose secrets in browser code |
| Feedback | Pilot intake and authenticated workspace feedback | Limited feedback/reporting in supplied files | Keep Flask feedback as source of truth |

## Current verification status

The integrated project can be statically checked with `python scripts/check_release.py` and JavaScript syntax checked with Node. Run `pytest -q` after installing `requirements-dev.txt`; run the same suite against a disposable PostgreSQL database before inviting real institutions. This environment could not download Python dependencies, so a live Flask runtime test is still required.
