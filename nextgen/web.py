"""HTML routes for registration and the authenticated dashboard."""
from urllib.parse import urlparse
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from extensions import db, limiter
from nextgen.models import Institution, PilotInquiry, Student, User

web_bp = Blueprint("web", __name__)


def _safe_internal_next(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or not value.startswith("/") or value.startswith("//"):
        return None
    return value


@web_bp.get("/")
def home():
    """Explain the product before asking a visitor to create a workspace."""
    user_id = session.get("user_id")
    if user_id:
        user = db.session.get(User, user_id)
        if user and user.is_active and user.institution and user.institution.is_active:
            return redirect(url_for("web.dashboard"))
        session.clear()
    return render_template("home.html")


@web_bp.post("/pilot-request")
@limiter.limit("10 per hour")
def pilot_request():
    """Collect early-access requests with CSRF protection and basic bot checks."""
    # Honeypot input is hidden from humans; low-effort bots often fill every field.
    if request.form.get("company_website", "").strip():
        flash("Thanks for your interest. Your request has been recorded.", "success")
        return redirect(url_for("web.home"))

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    institution_name = request.form.get("institution_name", "").strip()
    institution_type = request.form.get("institution_type", "").strip().lower()
    role = request.form.get("role", "").strip().lower()
    goal = request.form.get("goal", "").strip().lower()
    message = request.form.get("message", "").strip()
    consent = request.form.get("consent") == "yes"

    allowed_types = {"school", "college", "tuition"}
    allowed_roles = {"owner", "principal", "college_admin", "teacher", "other"}
    allowed_goals = {"attendance", "timetable", "homework", "notices", "all_in_one", "other"}
    valid_email = "@" in email and "." in email.rsplit("@", 1)[-1] and not any(ch.isspace() for ch in email)
    if (not name or len(name) > 120 or not valid_email or len(email) > 255
            or not institution_name or len(institution_name) > 160
            or institution_type not in allowed_types or role not in allowed_roles
            or goal not in allowed_goals or len(message) > 2000 or not consent):
        flash("Please check the required fields and consent, then submit again.", "error")
        return redirect(url_for("web.home"))

    try:
        inquiry = PilotInquiry(
            name=name, email=email, institution_name=institution_name,
            institution_type=institution_type, role=role, goal=goal,
            message=message, consent=True, status="new"
        )
        db.session.add(inquiry)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not save a pilot inquiry")
        flash("We couldn't save your request just now. Please try again.", "error")
        return redirect(url_for("web.home"))

    flash("Thank you! Your pilot request is saved. Please avoid sending any real student records during early testing.", "success")
    return redirect(url_for("web.home"))


@web_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if session.get("user_id"):
        existing = db.session.get(User, session.get("user_id"))
        if existing and existing.is_active and existing.institution and existing.institution.is_active:
            return redirect(url_for("web.dashboard"))
        session.clear()
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        institution_name = request.form.get("institution", "").strip()
        query = User.query.join(Institution).filter(func.lower(User.email) == email)
        if institution_name:
            query = query.filter(func.lower(Institution.name) == institution_name.lower())
        users = query.filter(User.is_active.is_(True), Institution.is_active.is_(True)).limit(2).all()
        user = next((item for item in users if item.check_password(password)), None)
        if user:
            session.clear()
            session["user_id"] = user.id
            session.permanent = True
            flash("Welcome back!", "success")
            return redirect(_safe_internal_next(request.args.get("next")) or url_for("web.dashboard"))
        flash("We couldn't sign you in with those details.", "error")
    return render_template("login.html")


@web_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("20 per hour", methods=["POST"])
def register():
    if session.get("user_id"):
        existing = db.session.get(User, session.get("user_id"))
        if existing and existing.is_active and existing.institution and existing.institution.is_active:
            return redirect(url_for("web.dashboard"))
        session.clear()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        institution_name = request.form.get("institution_name", "").strip()
        institution_type = request.form.get("institution_type", "tuition").strip().lower()
        valid_email = (
            len(email) <= 255
            and "@" in email
            and "." in email.rsplit("@", 1)[-1]
            and not any(character.isspace() for character in email)
        )
        if not name or not institution_name:
            flash("Please enter your name and institution name.", "error")
        elif len(name) > 120 or len(institution_name) > 160:
            flash("Your name must be 120 characters or fewer and your institution name 160 or fewer.", "error")
        elif not valid_email:
            flash("Enter a valid email address.", "error")
        elif len(password) < 10:
            flash("Use a password with at least 10 characters.", "error")
        elif len(password) > 128:
            flash("Use a password with no more than 128 characters.", "error")
        elif institution_type not in {"school", "college", "tuition"}:
            flash("Choose a valid institution type.", "error")
        elif User.query.filter(func.lower(User.email) == email).first() is not None:
            # Emails are globally unique because login identifies users by email.
            # Catch this before creating an institution so the user gets a useful next step.
            flash("An account already uses this email. Sign in with that account or use a different email to create a new workspace.", "error")
        else:
            try:
                institution = Institution(name=institution_name, institution_type=institution_type, timezone="Asia/Kolkata")
                db.session.add(institution)
                db.session.flush()
                user = User(institution_id=institution.id, name=name, email=email, role="admin")
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                session.clear()
                session["user_id"] = user.id
                session.permanent = True
                flash("Your workspace is ready. Add your first class to get started.", "success")
                return redirect(url_for("web.dashboard"))
            except IntegrityError:
                db.session.rollback()
                # A concurrent registration can pass the pre-check; handle the unique constraint too.
                current_app.logger.info("Workspace registration rejected by a uniqueness constraint")
                flash("An account may already use this email. Sign in or try a different email address.", "error")
            except SQLAlchemyError:
                db.session.rollback()
                current_app.logger.exception("Workspace registration failed")
                flash("We couldn't save your workspace because of a database error. Please try again. If this continues, check the server log.", "error")
    return render_template("register.html")


def _is_configured_pilot_owner(user: User | None) -> bool:
    """Only the explicitly configured pilot contact may view public inquiries."""
    configured_email = current_app.config.get("PILOT_ADMIN_EMAIL", "").strip().lower()
    return bool(user and user.is_active and user.role == "admin" and configured_email and user.email.lower() == configured_email)


@web_bp.get("/owner/pilot-inquiries")
def pilot_inquiries():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    if not user or not user.is_active or not user.institution or not user.institution.is_active:
        session.clear()
        return redirect(url_for("web.login", next=url_for("web.pilot_inquiries")))
    if not _is_configured_pilot_owner(user):
        abort(404)
    items = PilotInquiry.query.order_by(PilotInquiry.created_at.desc()).limit(200).all()
    return render_template("pilot_inquiries.html", inquiries=items)


@web_bp.post("/owner/pilot-inquiries/<int:inquiry_id>/status")
def update_pilot_inquiry_status(inquiry_id):
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    if not user or not user.is_active or not user.institution or not user.institution.is_active:
        session.clear()
        return redirect(url_for("web.login", next=url_for("web.pilot_inquiries")))
    if not _is_configured_pilot_owner(user):
        abort(404)
    inquiry = db.session.get(PilotInquiry, inquiry_id)
    if inquiry is None:
        abort(404)
    status = request.form.get("status", "").strip().lower()
    if status not in {"new", "contacted", "pilot_invited", "closed"}:
        flash("Choose a valid inquiry status.", "error")
    else:
        inquiry.status = status
        db.session.commit()
        flash("Inquiry status updated.", "success")
    return redirect(url_for("web.pilot_inquiries"))


@web_bp.get("/dashboard")
def dashboard():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    if not user or not user.is_active or not user.institution or not user.institution.is_active:
        session.clear()
        return redirect(url_for("web.login", next=url_for("web.dashboard")))
    return render_template("dashboard.html", institution=user.institution)


@web_bp.get("/offline")
def offline():
    return render_template("offline.html")


@web_bp.post("/logout")
def logout():
    session.clear()
    flash("You have signed out.", "success")
    return redirect(url_for("web.login"))


@web_bp.get("/sw.js")
def service_worker():
    """Serve the worker at the site root so its scope can cover the PWA routes."""
    response = send_from_directory(current_app.static_folder, "sw.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response
