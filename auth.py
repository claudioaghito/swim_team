from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_redirect"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("Nome utente o password non corretti.", "danger")
            return redirect(url_for("auth.login"))

        if not user.attivo:
            flash("Questo account è stato disattivato. Contatta l'amministratore.", "warning")
            return redirect(url_for("auth.login"))

        login_user(user)
        return redirect(url_for("dashboard_redirect"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Hai effettuato il logout.", "info")
    return redirect(url_for("auth.login"))
