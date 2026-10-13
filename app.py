"""WSGI entry point. Render starts this application with `gunicorn app:app`."""
from nextgen import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(__import__("os").environ.get("PORT", "5000")), debug=app.config.get("DEBUG", False))
