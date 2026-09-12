from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from extensions import db
from models import Allenamento, Gara, MovimentoContabile, Messaggio, Presenza, IscrizioneGara

athlete_bp = Blueprint("athlete", __name__, url_prefix="/atleta")


@athlete_bp.route("/")
@login_required
def dashboard():
    oggi = datetime.utcnow().date()

    prossimi_allenamenti = Allenamento.query.filter(
        Allenamento.data >= oggi
    ).order_by(Allenamento.data).limit(5).all()

    prossime_gare = Gara.query.filter(Gara.data >= oggi).order_by(Gara.data).limit(5).all()

    movimenti = MovimentoContabile.query.filter_by(
        atleta_id=current_user.id
    ).order_by(MovimentoContabile.data.desc()).all()

    messaggi = Messaggio.query.filter(
        (Messaggio.destinatario_id == current_user.id) | (Messaggio.destinatario_id.is_(None))
    ).order_by(Messaggio.data.desc()).limit(10).all()

    return render_template(
        "athlete/dashboard.html",
        prossimi_allenamenti=prossimi_allenamenti,
        prossime_gare=prossime_gare,
        movimenti=movimenti,
        saldo=current_user.saldo_attuale(),
        messaggi=messaggi,
    )


@athlete_bp.route("/gare/<int:gara_id>/iscrizione", methods=["GET", "POST"])
@login_required
def iscrizione_gara(gara_id):
    gara = Gara.query.get_or_404(gara_id)

    if request.method == "POST":
        scelte = set(request.form.getlist("tipologie"))
        esistenti = {
            i.stile
            for i in IscrizioneGara.query.filter_by(atleta_id=current_user.id, gara_id=gara.id).all()
        }

        da_rimuovere = esistenti - scelte
        if da_rimuovere:
            IscrizioneGara.query.filter_by(atleta_id=current_user.id, gara_id=gara.id).filter(
                IscrizioneGara.stile.in_(da_rimuovere)
            ).delete(synchronize_session=False)

        for tipo in scelte - esistenti:
            db.session.add(IscrizioneGara(atleta_id=current_user.id, gara_id=gara.id, stile=tipo))

        db.session.commit()
        flash("Iscrizione aggiornata.", "success")
        return redirect(url_for("athlete.dashboard"))

    scelte_attuali = {
        i.stile
        for i in IscrizioneGara.query.filter_by(atleta_id=current_user.id, gara_id=gara.id).all()
    }
    return render_template("athlete/iscrizione_gara.html", gara=gara, scelte_attuali=scelte_attuali)
