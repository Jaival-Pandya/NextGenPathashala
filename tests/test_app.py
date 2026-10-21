from datetime import datetime, timedelta
import json

import pytest

from nextgen import create_app
from extensions import db
from config import normalize_database_url
from nextgen.api import local_day_bounds
from nextgen.models import AttendanceRecord, AuditLog, ClassSession, Institution, PilotInquiry, UserFeedback, utcnow


@pytest.fixture()
def app():
    app = create_app({
        "APP_ENV": "testing",
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "AUTO_CREATE_DB": False,
        "SESSION_COOKIE_SECURE": False,
        "RATELIMIT_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def register(client, email="admin@example.com", institution="Example Academy"):
    return client.post("/register", data={
        "name": "Alex Admin",
        "email": email,
        "institution_name": institution,
        "institution_type": "college",
        "password": "A-long-test-password-123",
    }, follow_redirects=True)


def api_post(client, path, payload):
    return client.post(path, json=payload)


def test_health_and_registration(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.headers.get("X-Content-Type-Options") == "nosniff"
    assert health.headers.get("X-Frame-Options") == "DENY"
    assert health.json["service"] == "NextGenPathashala"
    response = register(client)
    assert response.status_code == 200
    assert b"Your day" not in response.data  # dashboard loads data client-side
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json["user"]["role"] == "admin"
    assert me.json["user"]["id"] is not None
    assert me.json["institution"]["name"] == "Example Academy"


def test_student_can_change_password_and_old_password_stops_working(client):
    register(client)
    created = api_post(client, "/api/v1/users", {
        "name": "Sam Student", "email": "student@example.com", "role": "student",
        "password": "Student-password-123",
    })
    assert created.status_code == 201
    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": "student@example.com", "password": "Student-password-123"})

    wrong_current = api_post(client, "/api/v1/auth/change-password", {
        "current_password": "incorrect-password", "new_password": "Student-password-456",
    })
    assert wrong_current.status_code == 400
    weak_new = api_post(client, "/api/v1/auth/change-password", {
        "current_password": "Student-password-123", "new_password": "short",
    })
    assert weak_new.status_code == 400

    changed = api_post(client, "/api/v1/auth/change-password", {
        "current_password": "Student-password-123", "new_password": "Student-password-456",
    })
    assert changed.status_code == 200
    assert changed.json["message"] == "Password changed successfully."

    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": "student@example.com", "password": "Student-password-123"})
    assert client.get("/api/v1/auth/me").status_code == 401
    client.post("/login", data={"email": "student@example.com", "password": "Student-password-456"})
    student_me = client.get("/api/v1/auth/me").json["user"]
    assert student_me["role"] == "student"
    assert student_me["student_id"] is not None
    assert student_me["student_code"].startswith("STU-")


def test_switch_account_logout_returns_to_login(client):
    register(client)
    response = client.post("/logout", data={"action": "switch"}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login?switch=1")
    assert client.get("/api/v1/auth/me").status_code == 401



def test_duplicate_workspace_email_shows_actionable_message(client):
    first = register(client, email="same-admin@example.com", institution="First Academy")
    assert first.status_code == 200
    # Sign out before attempting to register the same global login email.
    client.post("/logout", follow_redirects=True)
    duplicate = client.post("/register", data={
        "name": "Another Admin",
        "email": "SAME-ADMIN@example.com",
        "institution_name": "Second Academy",
        "institution_type": "college",
        "password": "A-long-test-password-456",
    }, follow_redirects=True)
    assert duplicate.status_code == 200
    assert b"An account already uses this email" in duplicate.data
    assert b"Sign in" in duplicate.data


def test_registration_rejects_invalid_email_and_long_password(client):
    invalid_email = client.post("/register", data={
        "name": "Alex Admin", "email": "not-an-email", "institution_name": "Example Academy",
        "institution_type": "college", "password": "A-long-test-password-123",
    }, follow_redirects=True)
    assert b"Enter a valid email address" in invalid_email.data
    long_password = client.post("/register", data={
        "name": "Alex Admin", "email": "admin2@example.com", "institution_name": "Example Academy",
        "institution_type": "college", "password": "x" * 129,
    }, follow_redirects=True)
    assert b"no more than 128 characters" in long_password.data

def build_test_scenario(client):
    register(client)
    created_class = api_post(client, "/api/v1/classes", {"name": "BSc AI A", "kind": "college", "academic_year": "2026-27"})
    assert created_class.status_code == 201
    class_id = created_class.json["class"]["id"]
    teacher_response = api_post(client, "/api/v1/users", {
        "name": "Taylor Teacher", "email": "teacher@example.com", "role": "teacher", "password": "Teacher-password-123"
    })
    assert teacher_response.status_code == 201
    teacher_id = teacher_response.json["user"]["id"]
    student_response = api_post(client, "/api/v1/users", {
        "name": "Sam Student", "email": "student@example.com", "role": "student", "password": "Student-password-123"
    })
    assert student_response.status_code == 201
    student_id = student_response.json["student"]["id"]
    assert api_post(client, f"/api/v1/classes/{class_id}/enrollments", {"student_id": student_id}).status_code == 201

    # Create a session several days away in the institution's local timezone.
    starts = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=3)
    ends = starts + timedelta(hours=1)
    session_response = api_post(client, "/api/v1/sessions", {
        "class_id": class_id, "subject": "Natural Language Processing", "teacher_id": teacher_id,
        "room": "Lab 1", "starts_at": starts.isoformat(timespec="minutes"), "ends_at": ends.isoformat(timespec="minutes")
    })
    assert session_response.status_code == 201, session_response.json
    session_id = session_response.json["session"]["id"]
    assert session_response.json["session"]["subject"] == "Natural Language Processing"

    conflict = api_post(client, "/api/v1/sessions", {
        "class_id": class_id, "subject": "Another class", "teacher_id": teacher_id,
        "room": "Room 2", "starts_at": starts.isoformat(timespec="minutes"), "ends_at": ends.isoformat(timespec="minutes")
    })
    assert conflict.status_code == 409

    # Admin can create assignments and notices for the selected class.
    assignment = api_post(client, "/api/v1/assignments", {
        "class_id": class_id, "subject": "NLP", "title": "Tokenizer exercise", "instructions": "Compare three tokenizers."
    })
    assert assignment.status_code == 201
    notice = api_post(client, "/api/v1/notices", {"title": "Lab update", "body": "Bring your laptop.", "class_id": str(class_id)})
    assert notice.status_code == 201
    return {"class_id": class_id, "teacher_id": teacher_id, "student_id": student_id,
            "session_id": session_id, "starts_at": starts.isoformat(timespec="minutes"),
            "ends_at": ends.isoformat(timespec="minutes"),
            "assignment_id": assignment.json["assignment"]["id"]}


def test_classes_users_enrollment_and_timetable(client):
    ids = build_test_scenario(client)
    assert ids["class_id"] and ids["session_id"] and ids["assignment_id"]


def test_role_permissions_attendance_submission_and_notice(client):
    ids = build_test_scenario(client)
    client.post("/logout", follow_redirects=True)
    login = client.post("/login", data={"email": "teacher@example.com", "password": "Teacher-password-123"}, follow_redirects=True)
    assert login.status_code == 200
    roster = client.get(f"/api/v1/sessions/{ids['session_id']}/attendance")
    assert roster.status_code == 200
    assert len(roster.json["students"]) == 1
    save = client.put(f"/api/v1/sessions/{ids['session_id']}/attendance", json={"records": [{"student_id": ids['student_id'], "status": "present"}]})
    assert save.status_code == 200
    # Teachers cannot create accounts or manage sessions outside their authorized role.
    assert api_post(client, "/api/v1/users", {"name": "Bad", "email": "bad@example.com", "role": "admin", "password": "Long-enough-password"}).status_code == 403
    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": "student@example.com", "password": "Student-password-123"}, follow_redirects=True)
    attendance = client.get("/api/v1/attendance/mine")
    assert attendance.status_code == 200
    assert attendance.json["records"][0]["status"] == "present"
    notices = client.get("/api/v1/notices")
    assert notices.status_code == 200
    assert any(item["title"] == "Lab update" for item in notices.json["notices"])
    submission = api_post(client, f"/api/v1/assignments/{ids['assignment_id']}/submissions", {"response_text": "Tokenizer comparison complete."})
    assert submission.status_code == 200
    assert client.get(f"/api/v1/sessions/{ids['session_id']}/attendance").status_code == 403


def test_qr_attendance_checkin_is_short_lived_and_reviewable(client, app):
    ids = build_test_scenario(client)
    with app.app_context():
        item = db.session.get(ClassSession, ids["session_id"])
        item.starts_at = utcnow() - timedelta(minutes=10)
        item.ends_at = utcnow() + timedelta(minutes=50)
        db.session.commit()

    first_qr = client.post(f"/api/v1/sessions/{ids['session_id']}/attendance/qr")
    assert first_qr.status_code == 200
    assert first_qr.json["qr_image"].startswith("data:image/svg+xml;base64,")
    assert first_qr.json["expires_in"] == 60
    with app.app_context():
        old_token = db.session.get(ClassSession, ids["session_id"]).attendance_qr_token

    rotated_qr = client.post(f"/api/v1/sessions/{ids['session_id']}/attendance/qr")
    assert rotated_qr.status_code == 200
    with app.app_context():
        token = db.session.get(ClassSession, ids["session_id"]).attendance_qr_token
    assert token != old_token

    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": "student@example.com", "password": "Student-password-123"})
    checkin_path = f"/attendance/check-in/{ids['session_id']}?token={token}"
    assert client.get(f"/attendance/check-in/{ids['session_id']}?token={old_token}").status_code == 410
    page = client.get(checkin_path)
    assert page.status_code == 200
    assert b"Confirm check-in" in page.data
    assert client.post(checkin_path, follow_redirects=True).status_code == 200
    with app.app_context():
        record = AttendanceRecord.query.filter_by(
            session_id=ids["session_id"], student_id=ids["student_id"],
        ).one()
        assert record.status == "present"
        assert record.recorded_via == "qr"
    client.post(checkin_path, follow_redirects=True)
    with app.app_context():
        assert AttendanceRecord.query.filter_by(session_id=ids["session_id"]).count() == 1

    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": "admin@example.com", "password": "A-long-test-password-123"})
    roster = client.get(f"/api/v1/sessions/{ids['session_id']}/attendance")
    assert roster.status_code == 200
    student = next(row for row in roster.json["students"] if row["student_id"] == ids["student_id"])
    assert student["recorded_via"] == "qr"


def test_institution_isolation(client):
    ids = build_test_scenario(client)
    client.post("/logout", follow_redirects=True)
    register(client, email="other-admin@example.com", institution="Other Academy")
    classes = client.get("/api/v1/classes")
    assert classes.status_code == 200
    assert all(item["name"] != "BSc AI A" for item in classes.json["classes"])
    session_response = client.get(f"/api/v1/sessions/{ids['session_id']}/attendance")
    assert session_response.status_code == 404


def test_public_landing_and_pilot_request(client, app):
    page = client.get("/")
    assert page.status_code == 200
    assert b"Less time coordinating" in page.data
    assert b"Create a test workspace" in page.data

    response = client.post("/pilot-request", data={
        "name": "Pat Owner",
        "email": "pat@example.com",
        "institution_name": "Pat's Tuition",
        "institution_type": "tuition",
        "role": "owner",
        "goal": "attendance",
        "message": "We want to test daily attendance.",
        "consent": "yes",
        "company_website": "",
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        inquiry = PilotInquiry.query.filter_by(email="pat@example.com").one()
        assert inquiry.status == "new"
        assert inquiry.consent is True


def test_workspace_feedback_can_be_submitted_and_reviewed(client, app):
    register(client)
    response = api_post(client, "/api/v1/feedback", {
        "category": "usability",
        "page": "Attendance",
        "message": "The attendance flow was easy to understand.",
    })
    assert response.status_code == 201
    assert response.json["feedback_id"]

    inbox = client.get("/api/v1/feedback")
    assert inbox.status_code == 200
    assert inbox.json["feedback"][0]["category"] == "usability"

    with app.app_context():
        assert UserFeedback.query.count() == 1


def test_admin_can_import_students_and_receive_one_time_credentials(client, app):
    register(client)
    class_response = api_post(client, "/api/v1/classes", {
        "name": "Import Test Batch", "kind": "tuition", "academic_year": "2026-27"
    })
    assert class_response.status_code == 201
    class_id = class_response.json["class"]["id"]

    response = api_post(client, f"/api/v1/classes/{class_id}/students/import", {
        "students": [
            {"name": "Student One", "email": "one.import@example.com", "student_code": "IMP-001"},
            {"name": "Student Two", "email": "two.import@example.com", "student_code": "IMP-002"},
            {"name": "Duplicate Email", "email": "one.import@example.com", "student_code": "IMP-003"},
            {"name": "Missing Email", "email": "", "student_code": "IMP-004"},
        ]
    })
    assert response.status_code == 201, response.json
    assert response.json["imported_count"] == 2
    assert response.json["skipped_count"] == 2
    credentials = response.json["credentials"]
    assert len(credentials) == 2
    assert all(len(item["temporary_password"]) >= 10 for item in credentials)
    assert all("password" not in user for user in client.get("/api/v1/users").json["users"])

    # Every imported account is connected to the chosen class; verify in the ORM.
    from nextgen.models import Enrollment, Student
    with app.app_context():
        assert Enrollment.query.filter_by(class_id=class_id).count() == 2
        assert Student.query.filter_by(institution_id=1).count() == 2


def test_student_cannot_use_bulk_import_endpoint(client):
    ids = build_test_scenario(client)
    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": "student@example.com", "password": "Student-password-123"}, follow_redirects=True)
    response = api_post(client, f"/api/v1/classes/{ids['class_id']}/students/import", {
        "students": [{"name": "Not Allowed", "email": "not-allowed@example.com"}]
    })
    assert response.status_code == 403


def test_timezone_fallback_and_database_url_normalization():
    institution = Institution(name="Test", institution_type="college", timezone="not/a-real-zone")
    chosen, start, end = local_day_bounds("2026-10-11", institution)
    assert chosen.isoformat() == "2026-10-11"
    assert end > start
    assert normalize_database_url("postgres://user:pass@host/db").startswith("postgresql+psycopg://")
    assert normalize_database_url("postgresql://user:pass@host/db").startswith("postgresql+psycopg://")
    assert normalize_database_url("sqlite:///local.db") == "sqlite:///local.db"


def test_pilot_inquiry_inbox_requires_configured_owner(client, app):
    assert client.get("/owner/pilot-inquiries").status_code == 404
    assert client.post("/owner/pilot-inquiries/1/status", data={"status": "closed"}).status_code == 404

    register(client)
    response = client.get("/owner/pilot-inquiries")
    assert response.status_code == 404

    app.config["PILOT_ADMIN_EMAIL"] = "admin@example.com"
    response = client.get("/owner/pilot-inquiries")
    assert response.status_code == 200
    assert b"Pilot requests" in response.data


def test_owner_analytics_is_private_and_shows_platform_metrics(client, app):
    assert client.get("/owner/admin").status_code == 404
    register(client)
    app.config["PILOT_ADMIN_EMAIL"] = "admin@example.com"
    with app.app_context():
        institution = Institution.query.filter_by(name="Example Academy").first()
        actor = institution.users[0]
        db.session.add(AuditLog(
            institution_id=institution.id, actor_id=actor.id,
            action="feedback.submitted", entity_type="user_feedback", entity_id="1",
        ))
        db.session.add(UserFeedback(
            institution_id=institution.id, user_id=actor.id, category="idea",
            message="Please add a way to export attendance.", page="attendance",
        ))
        db.session.commit()

    response = client.get("/owner/admin")
    assert response.status_code == 200
    assert b"Active users today" in response.data
    assert b"Feedback by AI category" in response.data
    assert b"Please add a way to export attendance." in response.data


def test_owner_can_opt_in_to_ai_feedback_categories(client, app, monkeypatch):
    register(client)
    app.config.update({
        "PILOT_ADMIN_EMAIL": "admin@example.com",
        "STUDY_AI_PROVIDER": "ollama",
        "STUDY_AI_API_KEY": "should-not-be-sent",
        "STUDY_AI_BASE_URL": "http://localhost:11434/v1",
    })
    with app.app_context():
        institution = Institution.query.filter_by(name="Example Academy").first()
        actor = institution.users[0]
        item = UserFeedback(
            institution_id=institution.id, user_id=actor.id, category="idea",
            message="Please add a way to export attendance.", page="attendance",
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            response = {"choices": [{"message": {"content": json.dumps([
                {"id": item_id, "category": "feature_request"}
            ])}}]}
            return json.dumps(response).encode("utf-8")

    captured = {}

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        return FakeResponse()

    monkeypatch.setattr("nextgen.web.urlopen", fake_urlopen)
    missing_confirmation = client.post("/owner/admin/categorize-feedback", data={})
    assert missing_confirmation.status_code == 302
    with app.app_context():
        assert db.session.get(UserFeedback, item_id).ai_category is None

    categorized = client.post(
        "/owner/admin/categorize-feedback",
        data={"confirm_ai_processing": "yes"}, follow_redirects=True,
    )
    assert categorized.status_code == 200
    assert captured["authorization"] is None
    assert b"AI categorized 1 feedback item" in categorized.data
    with app.app_context():
        assert db.session.get(UserFeedback, item_id).ai_category == "feature_request"


def test_reactivating_cancelled_session_checks_conflicts(client):
    ids = build_test_scenario(client)

    # Cancel the original session, then schedule the same teacher at the same time
    # for another class. Reactivating the original must be rejected.
    cancel = client.patch(f"/api/v1/sessions/{ids['session_id']}", json={"status": "cancelled"})
    assert cancel.status_code == 200

    other_class = api_post(client, "/api/v1/classes", {
        "name": "BSc AI B", "kind": "college", "academic_year": "2026-27"
    })
    assert other_class.status_code == 201
    overlap = api_post(client, "/api/v1/sessions", {
        "class_id": other_class.json["class"]["id"],
        "subject": "Overlapping lab", "teacher_id": ids["teacher_id"],
        "room": "Room 2", "starts_at": ids["starts_at"], "ends_at": ids["ends_at"]
    })
    assert overlap.status_code == 201, overlap.json

    reactivate = client.patch(f"/api/v1/sessions/{ids['session_id']}", json={"status": "scheduled"})
    assert reactivate.status_code == 409
    assert "teacher already has a class" in reactivate.json["error"]


def test_admin_can_manage_class_subjects_and_assign_teachers(client):
    register(client)
    class_response = api_post(client, "/api/v1/classes", {
        "name": "Subject Test Batch", "kind": "tuition", "academic_year": "2026-27"
    })
    assert class_response.status_code == 201
    class_id = class_response.json["class"]["id"]

    subject_response = api_post(client, f"/api/v1/classes/{class_id}/subjects", {
        "name": "Mathematics"
    })
    assert subject_response.status_code == 201
    assert subject_response.json["subject"]["name"] == "Mathematics"
    assert client.get(f"/api/v1/classes/{class_id}/subjects").json["subjects"][0]["name"] == "Mathematics"

    duplicate_subject = api_post(client, f"/api/v1/classes/{class_id}/subjects", {
        "name": "  mathematics  "
    })
    assert duplicate_subject.status_code == 409

    teacher_response = api_post(client, "/api/v1/users", {
        "name": "Subject Teacher", "email": "subject.teacher@example.com",
        "role": "teacher", "password": "Teacher-password-123"
    })
    assert teacher_response.status_code == 201
    teacher_id = teacher_response.json["user"]["id"]
    assignment = api_post(client, f"/api/v1/classes/{class_id}/teachers", {
        "teacher_id": teacher_id
    })
    assert assignment.status_code == 201
    assert client.get(f"/api/v1/classes/{class_id}/teachers").json["teachers"][0]["id"] == teacher_id
    duplicate_assignment = api_post(client, f"/api/v1/classes/{class_id}/teachers", {
        "teacher_id": teacher_id
    })
    assert duplicate_assignment.status_code == 409


def test_study_material_upload_delete_and_user_isolation(client, app, tmp_path):
    import io
    import re

    app.instance_path = str(tmp_path)
    register(client)
    uploaded = client.post(
        "/api/v1/study-materials",
        data={"file": (io.BytesIO(b"NLP tokenization splits text into smaller units for language processing."), "NLP-chapter.txt")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 201, uploaded.json
    doc_id = uploaded.json["material"]["id"]
    assert re.fullmatch(r"[a-f0-9]{16}", doc_id)

    listing = client.get("/api/v1/study-materials")
    assert listing.status_code == 200
    assert listing.json["materials"][0]["id"] == doc_id
    assert listing.json["materials"][0]["name"] == "NLP-chapter.txt"

    # A separate institution must neither list nor delete the first user's notes.
    client.post("/logout", follow_redirects=True)
    register(client, email="other-admin@example.com", institution="Other Academy")
    assert client.get("/api/v1/study-materials").json["materials"] == []
    assert client.delete(f"/api/v1/study-materials/{doc_id}").status_code == 404

    # The original owner can still remove the file; the ID returned by list matches delete's API.
    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": "admin@example.com", "password": "A-long-test-password-123"}, follow_redirects=True)
    deleted = client.delete(f"/api/v1/study-materials/{doc_id}")
    assert deleted.status_code == 200, deleted.json
    assert client.get("/api/v1/study-materials").json["materials"] == []


def test_study_material_validation_and_storage_limits(client, app, tmp_path):
    import io

    app.instance_path = str(tmp_path)
    register(client)
    missing = client.post("/api/v1/study-materials", data={}, content_type="multipart/form-data")
    assert missing.status_code == 400

    unsupported = client.post(
        "/api/v1/study-materials",
        data={"file": (io.BytesIO(b"not a document"), "notes.exe")},
        content_type="multipart/form-data",
    )
    assert unsupported.status_code == 400

    empty = client.post(
        "/api/v1/study-materials",
        data={"file": (io.BytesIO(b"  \n"), "empty.txt")},
        content_type="multipart/form-data",
    )
    assert empty.status_code == 400

    # An account cannot fill unbounded server storage with unlimited small uploads.
    for index in range(20):
        response = client.post(
            "/api/v1/study-materials",
            data={"file": (io.BytesIO(f"Chapter {index}: course notes on scientific study methods.".encode()), f"chapter-{index}.txt")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 201, response.json
    over_limit = client.post(
        "/api/v1/study-materials",
        data={"file": (io.BytesIO(b"another small note"), "chapter-21.txt")},
        content_type="multipart/form-data",
    )
    assert over_limit.status_code == 409


def test_study_chat_requires_question_and_configured_provider(client, app):
    app.config.update(STUDY_AI_PROVIDER="openai", STUDY_AI_API_KEY="")
    register(client)
    blank = api_post(client, "/api/v1/study-chat", {"question": "   "})
    assert blank.status_code == 400
    too_long = api_post(client, "/api/v1/study-chat", {"question": "x" * 2001})
    assert too_long.status_code == 400
    not_configured = api_post(client, "/api/v1/study-chat", {"question": "Explain photosynthesis."})
    assert not_configured.status_code == 503
    assert "STUDY_AI_API_KEY" in not_configured.json["error"]


def test_teacher_publishes_assessment_student_submits_and_teacher_sees_results(client):
    ids = build_test_scenario(client)
    questions = [
        {"prompt": "What is 2 + 2?", "options": ["3", "4", "5", "6"], "correct_index": 1, "explanation": "Two plus two equals four."},
        {"prompt": "Which structure stores key-value pairs in Python?", "options": ["list", "tuple", "dictionary", "set"], "correct_index": 2, "explanation": "A dictionary maps keys to values."},
    ]
    created = api_post(client, "/api/v1/assessments", {
        "class_id": ids["class_id"], "title": "Unit revision test",
        "instructions": "Choose one answer for each question.", "questions": questions,
    })
    assert created.status_code == 201, created.json
    assessment_id = created.json["assessment"]["id"]

    # Teachers can inspect the answer key and class results.
    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": "teacher@example.com", "password": "Teacher-password-123"}, follow_redirects=True)
    visible_classes = client.get("/api/v1/classes")
    assert any(item["id"] == ids["class_id"] for item in visible_classes.json["classes"])
    teacher_detail = client.get(f"/api/v1/assessments/{assessment_id}")
    assert teacher_detail.status_code == 200
    assert teacher_detail.json["questions"][0]["correct_index"] == 1

    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": "student@example.com", "password": "Student-password-123"}, follow_redirects=True)
    student_list = client.get("/api/v1/assessments")
    assert any(item["id"] == assessment_id for item in student_list.json["assessments"])
    student_detail = client.get(f"/api/v1/assessments/{assessment_id}")
    assert student_detail.status_code == 200
    assert "correct_index" not in student_detail.json["questions"][0]
    assert "explanation" not in student_detail.json["questions"][0]

    submitted = api_post(client, f"/api/v1/assessments/{assessment_id}/attempts", {"answers": [1, 0]})
    assert submitted.status_code == 201, submitted.json
    assert submitted.json["score"] == 1
    assert submitted.json["total"] == 2
    assert submitted.json["percent"] == 50
    assert submitted.json["results"][0]["correct"] is True
    assert submitted.json["results"][1]["correct"] is False
    assert client.post(f"/api/v1/assessments/{assessment_id}/attempts", json={"answers": [1, 2]}).status_code == 409
    assert client.get(f"/api/v1/assessments/{assessment_id}/results").status_code == 403

    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": "teacher@example.com", "password": "Teacher-password-123"}, follow_redirects=True)
    results = client.get(f"/api/v1/assessments/{assessment_id}/results")
    assert results.status_code == 200
    assert results.json["results"][0]["student_name"] == "Sam Student"
    assert results.json["results"][0]["score"] == 1


def test_assessment_validation_role_permissions_and_institution_isolation(client):
    ids = build_test_scenario(client)
    invalid = api_post(client, "/api/v1/assessments", {
        "class_id": ids["class_id"], "title": "Invalid quiz",
        "questions": [{"prompt": "Question", "options": ["A", "B"], "correct_index": 4}],
    })
    assert invalid.status_code == 400
    created = api_post(client, "/api/v1/assessments", {
        "class_id": ids["class_id"], "title": "Isolation check",
        "questions": [{"prompt": "Question?", "options": ["A", "B"], "correct_index": 0}],
    })
    assert created.status_code == 201
    existing_assessment_id = created.json["assessment"]["id"]

    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": "student@example.com", "password": "Student-password-123"}, follow_redirects=True)
    forbidden = api_post(client, "/api/v1/assessments", {
        "class_id": ids["class_id"], "title": "Student-made quiz",
        "questions": [{"prompt": "Question?", "options": ["A", "B"], "correct_index": 0}],
    })
    assert forbidden.status_code == 403

    client.post("/logout", follow_redirects=True)
    register(client, email="other-admin@example.com", institution="Other Academy")
    assert client.get(f"/api/v1/assessments/{existing_assessment_id}").status_code == 404
    assert client.get("/api/v1/assessments").json["assessments"] == []


def test_assessment_rejects_bad_answer_payload(client):
    ids = build_test_scenario(client)
    created = api_post(client, "/api/v1/assessments", {
        "class_id": ids["class_id"], "title": "Payload test",
        "questions": [{"prompt": "Question?", "options": ["A", "B"], "correct_index": 1}],
    })
    assert created.status_code == 201
    assessment_id = created.json["assessment"]["id"]
    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": "student@example.com", "password": "Student-password-123"}, follow_redirects=True)
    assert api_post(client, f"/api/v1/assessments/{assessment_id}/attempts", {"answers": ["1"]}).status_code == 400
    assert api_post(client, f"/api/v1/assessments/{assessment_id}/attempts", {"answers": []}).status_code == 400



def test_practice_quiz_uses_only_selected_course_notes(client, app, tmp_path, monkeypatch):
    import io
    import json

    app.instance_path = str(tmp_path)
    app.config.update(STUDY_AI_PROVIDER="openai", STUDY_AI_API_KEY="test-only-key")
    register(client)
    selected = client.post(
        "/api/v1/study-materials",
        data={"file": (io.BytesIO(b"Photosynthesis converts light into chemical energy."), "biology.txt")},
        content_type="multipart/form-data",
    )
    unselected = client.post(
        "/api/v1/study-materials",
        data={"file": (io.BytesIO(b"Fractions represent parts of a whole."), "maths.txt")},
        content_type="multipart/form-data",
    )
    selected_too = client.post(
        "/api/v1/study-materials",
        data={"file": (io.BytesIO(b"Chlorophyll captures energy from sunlight."), "plant-cells.txt")},
        content_type="multipart/form-data",
    )
    selected_id = selected.json["material"]["id"]
    unselected_id = unselected.json["material"]["id"]
    selected_too_id = selected_too.json["material"]["id"]
    questions = [
        {"question": f"Question {index}?", "options": ["A", "B", "C", "D"], "answer": 0, "explanation": "From the notes."}
        for index in range(5)
    ]
    captured = {}

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self):
            content = json.dumps({"questions": questions})
            return json.dumps({"choices": [{"message": {"content": content}}]}).encode()

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        captured["payload"] = json.loads(request.data.decode())
        return FakeResponse()

    monkeypatch.setattr("nextgen.api.urlopen", fake_urlopen)
    unavailable = api_post(client, "/api/v1/study-materials/practice-quiz", {"material_ids": ["0" * 16]})
    assert unavailable.status_code == 404

    response = api_post(client, "/api/v1/study-materials/practice-quiz", {"material_ids": [selected_id, selected_too_id]})
    assert response.status_code == 200, response.json
    assert len(response.json["questions"]) == 5
    assert response.json["questions"][0]["q"] == "Question 0?"
    assert captured["authorization"] == "Bearer test-only-key"
    note_prompt = captured["payload"]["messages"][1]["content"]
    assert "Photosynthesis converts light" in note_prompt
    assert "Chlorophyll captures energy" in note_prompt
    assert "Fractions represent" not in note_prompt
    assert unselected_id not in note_prompt

    app.config.update(
        STUDY_AI_PROVIDER="ollama",
        STUDY_AI_BASE_URL="http://localhost:11434/v1",
        STUDY_AI_MODEL="llama3.2:3b",
    )
    ollama_response = api_post(client, "/api/v1/study-materials/practice-quiz", {"material_ids": [selected_id]})
    assert ollama_response.status_code == 200, ollama_response.json
    assert captured["authorization"] is None


def test_study_chat_uses_server_key_and_note_context_in_untrusted_user_message(client, app, tmp_path, monkeypatch):
    import io
    import json
    from io import BytesIO

    app.instance_path = str(tmp_path)
    app.config.update(
        STUDY_AI_PROVIDER="openai",
        STUDY_AI_API_KEY="test-only-key",
        STUDY_AI_BASE_URL="https://api.openai.com/v1",
        STUDY_WEB_SEARCH_API_KEY="test-search-key",
    )
    register(client)
    uploaded = client.post(
        "/api/v1/study-materials",
        data={"file": (io.BytesIO(b"TF-IDF combines term frequency with inverse document frequency."), "nlp.txt")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 201
    captured = {}
    requests = []

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "TF-IDF weights terms by relevance."}}]}).encode()

    def fake_urlopen(request, timeout):
        requests.append(request)
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["authorization"] = request.get_header("Authorization")
        captured["payload"] = json.loads(request.data.decode())
        return FakeResponse()

    monkeypatch.setattr("nextgen.api.urlopen", fake_urlopen)
    answer = api_post(client, "/api/v1/study-chat", {"question": "Explain TF-IDF frequency"})
    assert answer.status_code == 200, answer.json
    assert answer.json["answer"] == "TF-IDF weights terms by relevance."
    assert captured["authorization"] == "Bearer test-only-key"
    assert "UNTRUSTED COURSE-NOTE EXCERPTS" in captured["payload"]["messages"][1]["content"]
    assert "TF-IDF" in captured["payload"]["messages"][1]["content"]
    assert "STUDENT COURSE NOTES" not in captured["payload"]["messages"][0]["content"]
    assert len(requests) == 1
    assert requests[0].get_method() == "POST"


def test_study_chat_searches_web_only_when_note_retrieval_has_no_match(client, app, monkeypatch):
    import json

    app.config.update(
        STUDY_AI_PROVIDER="openai",
        STUDY_AI_API_KEY="test-only-key",
        STUDY_AI_BASE_URL="https://api.openai.com/v1",
        STUDY_WEB_SEARCH_API_KEY="test-search-key",
    )
    register(client)
    requests = []

    class FakeResponse:
        def __init__(self, body): self.body = body
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self): return json.dumps(self.body).encode()

    def fake_urlopen(request, timeout):
        requests.append(request)
        if request.get_method() == "GET":
            assert request.get_header("X-subscription-token") == "test-search-key"
            return FakeResponse({"web": {"results": [{
                "title": "Newton's laws",
                "url": "https://example.test/newton",
                "description": "Newton's second law states that force equals mass times acceleration.",
            }]}})
        return FakeResponse({"choices": [{"message": {"content": "Force equals mass times acceleration."}}]})

    monkeypatch.setattr("nextgen.api.urlopen", fake_urlopen)
    answer = api_post(client, "/api/v1/study-chat", {"question": "Explain Newton's second law"})

    assert answer.status_code == 200, answer.json
    assert len(requests) == 2
    prompt = json.loads(requests[1].data.decode())["messages"][1]["content"]
    assert "UNTRUSTED WEB SEARCH RESULTS" in prompt
    assert "https://example.test/newton" in prompt


def test_study_chat_omits_api_key_for_ollama_and_includes_uploaded_notes(client, app, tmp_path, monkeypatch):
    import io
    import json

    app.instance_path = str(tmp_path)
    app.config.update(
        STUDY_AI_PROVIDER="ollama",
        STUDY_AI_API_KEY="should-not-be-sent",
        STUDY_AI_BASE_URL="http://localhost:11434/v1",
        STUDY_AI_MODEL="llama3.2:3b",
    )
    register(client)
    uploaded = client.post(
        "/api/v1/study-materials",
        data={"file": (io.BytesIO(b"Photosynthesis converts light energy into chemical energy in plants."), "biology.txt")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 201
    captured = {}

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "Plants store light energy as chemical energy."}}]}).encode()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["payload"] = json.loads(request.data.decode())
        return FakeResponse()

    monkeypatch.setattr("nextgen.api.urlopen", fake_urlopen)
    answer = api_post(client, "/api/v1/study-chat", {"question": "Explain photosynthesis"})
    assert answer.status_code == 200, answer.json
    assert answer.json["model"] == "llama3.2:3b"
    assert captured["url"] == "http://localhost:11434/v1/chat/completions"
    assert captured["authorization"] is None
    assert "Photosynthesis converts light energy" in captured["payload"]["messages"][1]["content"]


def _provider_http_error(url, status, body, headers=None):
    import io
    from urllib.error import HTTPError

    return HTTPError(url, status, "Provider error", headers or {}, io.BytesIO(json.dumps(body).encode()))


def test_study_chat_reports_provider_quota_exhaustion(client, app, monkeypatch):
    app.config.update(
        STUDY_AI_PROVIDER="openai",
        STUDY_AI_API_KEY="test-only-key",
        STUDY_AI_BASE_URL="https://api.openai.com/v1",
    )
    register(client)
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        raise _provider_http_error(request.full_url, 429, {"error": {
            "type": "insufficient_quota",
            "code": "credit_balance_exhausted",
            "message": "You have no credits remaining. Add credits to continue using the API.",
        }})

    monkeypatch.setattr("nextgen.api.urlopen", fake_urlopen)
    response = api_post(client, "/api/v1/study-chat", {"question": "Explain photosynthesis"})

    assert response.status_code == 502
    assert "credits" in response.json["error"].lower()
    assert "billing" in response.json["error"].lower()
    assert "wait a little" not in response.json["error"].lower()
    # Quota exhaustion is permanent until an administrator acts, so it must not be retried.
    assert len(calls) == 1


def test_study_chat_reports_openrouter_credit_exhaustion(client, app, monkeypatch):
    app.config.update(
        STUDY_AI_PROVIDER="openrouter",
        STUDY_AI_API_KEY="test-only-key",
        STUDY_AI_BASE_URL="https://openrouter.ai/api/v1",
        STUDY_AI_MODEL="openrouter/free",
    )
    register(client)
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        raise _provider_http_error(request.full_url, 402, {"error": {
            "code": 402,
            "message": "Insufficient credits. Add credits to continue.",
            "metadata": {"error_type": "insufficient_credits"},
        }})

    monkeypatch.setattr("nextgen.api.urlopen", fake_urlopen)
    response = api_post(client, "/api/v1/study-chat", {"question": "Explain photosynthesis"})

    assert response.status_code == 502
    assert "credits" in response.json["error"].lower()
    assert "billing" in response.json["error"].lower()
    assert len(calls) == 1


def test_study_chat_reports_provider_rate_limit_with_retry_after(client, app, monkeypatch):
    app.config.update(
        STUDY_AI_PROVIDER="openai",
        STUDY_AI_API_KEY="test-only-key",
        STUDY_AI_BASE_URL="https://api.openai.com/v1",
    )
    register(client)
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        raise _provider_http_error(request.full_url, 429, {"error": {
            "type": "rate_limit_exceeded",
            "code": "rate_limit_exceeded",
            "message": "Rate limit reached for requests per minute.",
        }}, headers={"Retry-After": "3"})

    monkeypatch.setattr("nextgen.api.urlopen", fake_urlopen)
    response = api_post(client, "/api/v1/study-chat", {"question": "Explain photosynthesis"})

    assert response.status_code == 502
    assert "rate limit" in response.json["error"].lower()
    assert "3 seconds" in response.json["error"]
    # A wait longer than the retry window is surfaced to the student instead of blocking the request.
    assert len(calls) == 1


def test_study_chat_retries_one_transient_provider_rate_limit(client, app, monkeypatch):
    app.config.update(
        STUDY_AI_PROVIDER="openai",
        STUDY_AI_API_KEY="test-only-key",
        STUDY_AI_BASE_URL="https://api.openai.com/v1",
    )
    register(client)
    calls = []
    sleeps = []

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "A retried answer."}}]}).encode()

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise _provider_http_error(request.full_url, 429, {"error": {
                "type": "rate_limit_exceeded",
                "code": "rate_limit_exceeded",
                "message": "Rate limit reached for requests per minute.",
            }})
        return FakeResponse()

    monkeypatch.setattr("nextgen.api.urlopen", fake_urlopen)
    monkeypatch.setattr("nextgen.api._time.sleep", sleeps.append)
    response = api_post(client, "/api/v1/study-chat", {"question": "Explain photosynthesis"})

    assert response.status_code == 200, response.json
    assert response.json["answer"] == "A retried answer."
    assert len(calls) == 2
    assert sleeps == [0.25]
