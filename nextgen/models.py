"""Database models for a multi-institution education-management MVP."""
from datetime import datetime, timezone
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import db


def utcnow() -> datetime:
    """Return a UTC-naive timestamp for consistent SQLite/PostgreSQL storage."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Institution(db.Model):
    __tablename__ = "institutions"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    institution_type = db.Column(db.String(30), nullable=False, default="tuition")
    timezone = db.Column(db.String(64), nullable=False, default="Asia/Kolkata")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    users = db.relationship("User", back_populates="institution", cascade="all, delete-orphan")


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    institution = db.relationship("Institution", back_populates="users")
    student_profile = db.relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    __table_args__ = (db.UniqueConstraint("email", name="uq_user_email_global"),)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "email": self.email, "role": self.role, "institution_id": self.institution_id}


class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    student_code = db.Column(db.String(60), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    user = db.relationship("User", back_populates="student_profile")
    institution = db.relationship("Institution")
    enrollments = db.relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    __table_args__ = (db.UniqueConstraint("institution_id", "student_code", name="uq_student_code_per_institution"),)

    def to_dict(self) -> dict:
        return {"id": self.id, "user_id": self.user_id, "name": self.user.name, "email": self.user.email, "student_code": self.student_code}


class ClassGroup(db.Model):
    __tablename__ = "classes"
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(140), nullable=False)
    kind = db.Column(db.String(30), nullable=False, default="tuition")
    academic_year = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    institution = db.relationship("Institution")
    enrollments = db.relationship("Enrollment", back_populates="class_group", cascade="all, delete-orphan")
    sessions = db.relationship("ClassSession", back_populates="class_group", cascade="all, delete-orphan")
    subjects = db.relationship("ClassSubject", back_populates="class_group", cascade="all, delete-orphan")
    __table_args__ = (db.UniqueConstraint("institution_id", "name", name="uq_class_name_per_institution"),)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "kind": self.kind, "academic_year": self.academic_year,
                "student_count": len(self.enrollments)}


class ClassSubject(db.Model):
    """A subject offered within one class or tuition batch."""
    __tablename__ = "subjects"
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    class_group = db.relationship("ClassGroup", back_populates="subjects")
    institution = db.relationship("Institution")
    creator = db.relationship("User")
    __table_args__ = (db.UniqueConstraint("class_id", "name", name="uq_subject_name_per_class"),)

    def to_dict(self) -> dict:
        return {"id": self.id, "class_id": self.class_id, "name": self.name}


class ClassTeacher(db.Model):
    """Explicit teacher-to-class assignment independent of a particular session."""
    __tablename__ = "class_teachers"
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    class_group = db.relationship("ClassGroup")
    teacher = db.relationship("User", foreign_keys=[teacher_id])
    assigner = db.relationship("User", foreign_keys=[assigned_by])
    __table_args__ = (db.UniqueConstraint("class_id", "teacher_id", name="uq_teacher_per_class"),)


class Enrollment(db.Model):
    __tablename__ = "enrollments"
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="active")
    enrolled_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    class_group = db.relationship("ClassGroup", back_populates="enrollments")
    student = db.relationship("Student", back_populates="enrollments")
    __table_args__ = (db.UniqueConstraint("class_id", "student_id", name="uq_student_enrollment"),)


class ClassSession(db.Model):
    __tablename__ = "class_sessions"
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    subject = db.Column(db.String(120), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    room = db.Column(db.String(80))
    starts_at = db.Column(db.DateTime, nullable=False, index=True)  # stored UTC-naive
    ends_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="scheduled")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    institution = db.relationship("Institution")
    class_group = db.relationship("ClassGroup", back_populates="sessions")
    teacher = db.relationship("User", foreign_keys=[teacher_id])
    creator = db.relationship("User", foreign_keys=[created_by])
    attendance_records = db.relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")
    assignments = db.relationship("Assignment", back_populates="session", cascade="all, delete-orphan")


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)
    marked_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    marked_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    session = db.relationship("ClassSession", back_populates="attendance_records")
    student = db.relationship("Student")
    marker = db.relationship("User")
    __table_args__ = (db.UniqueConstraint("session_id", "student_id", name="uq_attendance_per_session"),)


class Assignment(db.Model):
    __tablename__ = "assignments"
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id", ondelete="SET NULL"), index=True)
    subject = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    instructions = db.Column(db.Text, nullable=False, default="")
    due_at = db.Column(db.DateTime, index=True)  # stored UTC-naive
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    class_group = db.relationship("ClassGroup")
    session = db.relationship("ClassSession", back_populates="assignments")
    creator = db.relationship("User")
    submissions = db.relationship("Submission", back_populates="assignment", cascade="all, delete-orphan")


class Submission(db.Model):
    __tablename__ = "submissions"
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    response_text = db.Column(db.Text, nullable=False, default="")
    submitted_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    feedback = db.Column(db.Text)
    assignment = db.relationship("Assignment", back_populates="submissions")
    student = db.relationship("Student")
    __table_args__ = (db.UniqueConstraint("assignment_id", "student_id", name="uq_submission_per_student"),)


class Assessment(db.Model):
    """A published class quiz whose correct answers stay server-side until submission."""
    __tablename__ = "assessments"
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    instructions = db.Column(db.Text, nullable=False, default="")
    questions = db.Column(db.JSON, nullable=False)
    due_at = db.Column(db.DateTime, index=True)  # stored UTC-naive
    is_published = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    institution = db.relationship("Institution")
    class_group = db.relationship("ClassGroup")
    creator = db.relationship("User")
    attempts = db.relationship("AssessmentAttempt", back_populates="assessment", cascade="all, delete-orphan")


class AssessmentAttempt(db.Model):
    """A single server-scored attempt per enrolled student and assessment."""
    __tablename__ = "assessment_attempts"
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    answers = db.Column(db.JSON, nullable=False)  # selected option index or null per question
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    assessment = db.relationship("Assessment", back_populates="attempts")
    student = db.relationship("Student")
    __table_args__ = (db.UniqueConstraint("assessment_id", "student_id", name="uq_assessment_attempt_per_student"),)


class Notice(db.Model):
    __tablename__ = "notices"
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id", ondelete="CASCADE"), index=True)  # null means institution-wide
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    published_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    institution = db.relationship("Institution")
    class_group = db.relationship("ClassGroup")
    author = db.relationship("User")


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.String(80), nullable=False)
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)


class PilotInquiry(db.Model):
    """Public early-access requests collected from the product landing page."""
    __tablename__ = "pilot_inquiries"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    institution_name = db.Column(db.String(160), nullable=False)
    institution_type = db.Column(db.String(30), nullable=False)
    role = db.Column(db.String(40), nullable=False)
    goal = db.Column(db.String(80), nullable=False)
    message = db.Column(db.Text, nullable=False, default="")
    consent = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(30), nullable=False, default="new", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)


class UserFeedback(db.Model):
    """Feedback submitted by authenticated testers inside their workspace."""
    __tablename__ = "user_feedback"
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    category = db.Column(db.String(30), nullable=False)
    message = db.Column(db.Text, nullable=False)
    page = db.Column(db.String(120), nullable=False, default="dashboard")
    status = db.Column(db.String(30), nullable=False, default="new", index=True)
    ai_category = db.Column(db.String(40))
    ai_categorized_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    institution = db.relationship("Institution")
    user = db.relationship("User")
