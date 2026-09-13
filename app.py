import os
import click
from flask import Flask, redirect, url_for
from flask_login import login_required, current_user

from config import Config
from extensions import db, login_manager
from models import User


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "cartellini"), exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "certificati"), exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "programmi_gare"), exist_ok=True)

    from auth import auth_bp
    from admin import admin_bp
    from athlete import athlete_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(athlete_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    @app.route("/dashboard")
    @login_required
    def dashboard_redirect():
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("athlete.dashboard"))

    register_cli(app)

    return app


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Crea le tabelle del database. Uso: flask init-db"""
        db.create_all()
        click.echo("Database inizializzato.")

    @app.cli.command("create-admin")
    @click.argument("username")
    @click.argument("password")
    @click.option("--nome", default="Admin")
    @click.option("--cognome", default="Squadra")
    def create_admin(username, password, nome, cognome):
        """Crea un utente amministratore. Uso: flask create-admin username password"""
        if User.query.filter_by(username=username).first():
            click.echo("Utente già esistente.")
            return
        admin = User(username=username, nome=nome, cognome=cognome, ruolo="admin")
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Amministratore '{username}' creato correttamente.")


app = create_app()

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        import webbrowser
        webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True)
