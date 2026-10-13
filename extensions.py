"""Shared Flask extensions, initialized by the application factory."""
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()

# Rate limits protect public login, registration, and pilot-request endpoints.
# Configure a shared storage URI (for example Redis) before scaling to multiple workers.
limiter = Limiter(key_func=get_remote_address, default_limits=[])
