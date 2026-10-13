# Lovable source review and merge decisions

The uploaded `index(4).html`, `styles.css`, `app(1).js`, and `features.js` were reviewed as the UI/feature reference for this consolidated project.

## Integrated from the supplied UI

- Inter / Space Grotesk / JetBrains Mono typography and indigo/mint visual language.
- Soft translucent panels, rounded controls, compact sidebar navigation, mobile bottom navigation and theme switching.
- Student spreadsheet import concept from `features.js`, reimplemented against the Flask API for CSV/XLS/XLSX files.
- The per-class subject catalog and teacher/class assignment concepts from the prototype management screen, implemented as persistent Flask models and APIs with migration-backed data. It previews rows, validates headers, limits a batch to 300 records, generates random temporary passwords server-side, stores only password hashes, enrolls imported students into the selected class and returns credentials once for secure distribution.

## Preserved from the Flask MVP

- Server-side session authentication and password hashing.
- CSRF-protected API writes and server-side role checks.
- Institution-scoped records and per-resource authorization.
- PostgreSQL-ready SQLAlchemy models and versioned migrations.
- Timetable, attendance, homework, notices, workspace feedback, pilot intake and PWA shell.

## Why the original `app(1).js` is not loaded in production

The supplied prototype reads and writes one shared `app_state` row with ID `default`, performs account login and role decisions inside the browser, and mirrors a `password` property into a Supabase `users` row. The supplied source does not establish that RLS rules isolate every institution and operation. Simply loading this file beside the Flask backend would create two competing data/authentication systems and could expose passwords or cross-organization data. The consolidated application therefore uses the Lovable file as a visual and feature reference, not as a live second persistence layer.

## Deferred feature modules from the prototype

The supplied prototype also has notes, syllabus topics/PDFs, test building and quizzes, viva sessions, weak-topic insights, voice input, AI-assist functions, staff invites and extra study dashboards. These are not represented in the current Flask database/API. They should be added as database-backed modules with explicit authorization and tests rather than re-enabled by copying the shared client-state mechanism.
