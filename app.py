import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# IMPORTANTE: En un entorno de producción, la variable de entorno SESSION_SECRET DEBE ser configurada
# con un valor largo, aleatorio y único. NO usar un valor por defecto en producción.
# Por ejemplo: app.secret_key = os.urandom(24)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///trading_bot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize extensions
db.init_app(app)

# Import routes only (no websockets for optimized performance)
from routes import *

with app.app_context():
    # Import models to create tables
    import models
    db.create_all()