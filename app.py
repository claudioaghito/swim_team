import os
import click
from flask import Flask, redirect, url_for
from flask_login import login_required, current_user
from markupsafe import Markup
from sqlalchemy import inspect, text

from config import Config
from extensions import db, login_manager
from models import User


def _migra_schema(app):
    """Aggiunge le tabelle nuove e le colonne introdotte dopo la creazione
    iniziale del database, senza perdere i dati gia' presenti (non c'e' Alembic)."""
    with app.app_context():
        inspector = inspect(db.engine)
        if "users" not in inspector.get_table_names():
            return  # db non ancora inizializzato: ci pensa "flask init-db"
        colonne_users = {c["name"] for c in inspector.get_columns("users")}
        if "sesso" not in colonne_users:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN sesso VARCHAR(1)"))
        if "certificato_medico_scadenza" not in colonne_users:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN certificato_medico_scadenza DATE"))
        if "gare" in inspector.get_table_names():
            colonne_gare = {c["name"] for c in inspector.get_columns("gare")}
            if "modalita_pagamento" not in colonne_gare:
                with db.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE gare ADD COLUMN modalita_pagamento TEXT"))
        db.create_all()  # crea le tabelle introdotte da nuove funzionalita', lascia intatte le altre


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    _migra_schema(app)

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

    @app.context_processor
    def inject_icon_helper():
        def icon(name, cls="icon"):
            src = url_for("static", filename=f"icons/{name}.svg")
            return Markup(f'<img src="{src}" class="{cls}" alt="">')
        return dict(icon=icon)

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
    app.run(debug=True, host="0.0.0.0")
