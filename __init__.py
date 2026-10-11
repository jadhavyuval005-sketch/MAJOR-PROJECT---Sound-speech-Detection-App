import logging
import os

from flask import Flask, jsonify, send_from_directory

from .config import Config
from .extensions import bcrypt, cors, db, jwt
from .storage import make_storage


def setup_logging(app):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    group = app.config.get("CLOUDWATCH_LOG_GROUP")
    if group:
        import boto3
        from watchtower import CloudWatchLogHandler

        client = boto3.client("logs", region_name=app.config["AWS_REGION"])
        app.logger.addHandler(CloudWatchLogHandler(log_group_name=group, boto3_client=client))
        app.logger.info("CloudWatch logging enabled (%s)", group)


def create_app(config=Config):
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config)
    if not app.testing and app.config["JWT_SECRET_KEY"] == "dev-only-change-me" and not app.debug:
        app.logger.warning("JWT_SECRET_KEY is the development default; set a real secret in production")

    setup_logging(app)
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    app.extensions["audio_storage"] = make_storage(app.config)

    from .routes import api

    app.register_blueprint(api)

    @jwt.unauthorized_loader
    @jwt.invalid_token_loader
    def _bad_token(reason):
        return jsonify(error="Please sign in again"), 401

    @jwt.expired_token_loader
    def _expired(_h, _p):
        return jsonify(error="Session expired, please sign in again"), 401

    @app.errorhandler(413)
    def _too_large(_e):
        return jsonify(error="Recording is too large"), 413

    @app.errorhandler(500)
    def _server_error(e):
        app.logger.exception("Unhandled error: %s", e)
        return jsonify(error="Something went wrong on our side"), 500

    # Plain HTML/CSS/JS sign-in page (login-page/), available at /login/
    login_dir = app.config["LOGIN_PAGE_DIR"]

    @app.get("/login/")
    def login_page():
        return send_from_directory(login_dir, "login.html")

    @app.get("/login/<path:name>")
    def login_asset(name):
        return send_from_directory(login_dir, name)

    # Serve the built React app so one process can host the whole thing.
    dist = app.config["FRONTEND_DIST"]

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def spa(path):
        if path.startswith("api/"):
            return jsonify(error="Not found"), 404
        if os.path.isdir(dist):
            target = os.path.join(dist, path)
            if path and os.path.isfile(target):
                return send_from_directory(dist, path)
            return send_from_directory(dist, "index.html")
        return jsonify(message="API running. Build the frontend (npm run build) to serve the UI here."), 200

    with app.app_context():
        db.create_all()  # simple bootstrap; use Flask-Migrate for schema changes later
    return app
