"""
Extension instances live here, uninitialized, and get bound to the app
in the application factory (app.py). This avoids circular imports:
models and routes can `from app.extensions import db` without importing
the app factory itself.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)
