# Course Notes Q&A — implementation and test notes

## Added
- Authenticated endpoints to upload, list, and delete personal study materials.
- TXT, Markdown and text-based PDF extraction; 5 MB per-file limit and 180,000-character extracted-text cap.
- Per-user/per-institution filesystem storage beneath `instance/study_materials/`.
- Lightweight keyword-overlap retrieval that adds up to three relevant note sections to the AI system prompt.
- UI to upload/remove notes in Study Lab.
- `FormData` support in the shared API helper without incorrectly forcing JSON Content-Type.
- `pypdf` dependency for PDF extraction.

## Important limitations
- Scanned PDFs need OCR outside this app; no OCR is performed.
- Retrieval is lexical rather than embedding/vector-based, so questions should use terminology found in the notes.
- Notes are private to the uploading account; they are not shared across students/teachers. Shared course libraries require an explicit permission model before implementation.
- Full Flask/database/AI-provider integration tests require local dependencies, a configured database, and an AI provider key. Static syntax checks alone do not prove runtime correctness.
- Production filesystem persistence and backup/retention should be configured before launch.

## Manual acceptance test
1. Sign in and upload a short TXT/MD file with a distinctive fact.
2. Ask Study Buddy a question using terms in that file; confirm the answer refers to the uploaded note.
3. Upload a text-based PDF and repeat.
4. Try a file larger than 5 MB and an unsupported extension; both should be rejected with a clear message.
5. Sign in as another user and confirm the first user's files do not appear.
6. Delete a file and confirm it disappears from the list.
7. Test without `STUDY_AI_API_KEY`; the app should show the existing administrator-configuration message.
