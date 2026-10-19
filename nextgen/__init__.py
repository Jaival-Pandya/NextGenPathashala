"""Flask application factory for NextGenPathashala."""
import os
from datetime import datetime, timezone
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException
from extensions import csrf, db, limiter, migrate
from config import Config
from nextgen.models import Institution, User


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    app.config.setdefault("MAX_CONTENT_LENGTH", 6 * 1024 * 1024)
    if test_config:
        app.config.update(test_config)

    # Refuse a known development secret in production instead of silently
    # starting with a predictable session-signing key.
    if app.config.get("APP_ENV") == "production":
        secret = app.config.get("SECRET_KEY", "")
        if not secret or secret == "dev-only-change-me-before-deploying" or len(secret) < 32:
            raise RuntimeError("Configure a random SECRET_KEY of at least 32 characters in production.")
        if not app.config.get("SESSION_COOKIE_SECURE"):
            raise RuntimeError("SESSION_COOKIE_SECURE must be enabled in production.")

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    from nextgen.web import web_bp
    from nextgen.api import api_bp
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    @app.context_processor
    def inject_template_helpers():
        user = None
        user_id = session.get("user_id")
        if user_id:
            user = db.session.get(User, user_id)
            if user and (not user.is_active or not user.institution or not user.institution.is_active):
                session.clear()
                user = None
        pilot_email = app.config.get("PILOT_ADMIN_EMAIL", "").strip().lower()
        is_pilot_owner = bool(user and user.role == "admin" and pilot_email and user.email.lower() == pilot_email)
        return {"current_user": user, "csrf_token_value": _csrf_token_safe(),
                "is_pilot_owner": is_pilot_owner}

    def _csrf_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "CSRF validation failed. Refresh the page and try again."}), 400
        return render_template("error.html", code=400, message="The form expired. Please refresh and try again."), 400

    def _http_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": error.description}), error.code
        return render_template("error.html", code=error.code or 500, message=error.description), error.code or 500

    app.register_error_handler(CSRFError, _csrf_error)
    app.register_error_handler(HTTPException, _http_error)

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.exception("Unhandled application error")
        if request.path.startswith("/api/"):
            return jsonify({"error": "An unexpected server error occurred."}), 500
        return render_template("error.html", code=500, message="Something went wrong. Please try again."), 500

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.path.startswith("/api/") or request.path in {"/login", "/register", "/dashboard", "/logout", "/pilot-request"} or request.path.startswith("/owner/"):
            response.headers["Cache-Control"] = "no-store"
        if request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.get("/health")
    def health():
        """Liveness endpoint: confirms the web process can answer requests."""
        return jsonify({"status": "ok", "service": "NextGenPathashala", "time": datetime.now(timezone.utc).isoformat()})

    @app.get("/ready")
    def ready():
        """Readiness endpoint: also confirms that the configured database responds."""
        from sqlalchemy import text
        from sqlalchemy.exc import SQLAlchemyError
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Database readiness check failed")
            return jsonify({"status": "not_ready"}), 503
        return jsonify({"status": "ready"}), 200

    if app.config.get("AUTO_CREATE_DB"):
        with app.app_context():
            db.create_all()

    return app


def _csrf_token_safe():
    # csrf_token() is supplied by Flask-WTF in template context; no secret is exposed.
    from flask_wtf.csrf import generate_csrf
    try:
        return generate_csrf()
    except RuntimeError:
        return ""
