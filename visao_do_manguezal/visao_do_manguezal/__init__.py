from flask import Flask
from .extensions import db

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    app.config["SECRET_KEY"] = "super_secreta"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///../instance/database.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    from .routes import main
    app.register_blueprint(main)

    return app