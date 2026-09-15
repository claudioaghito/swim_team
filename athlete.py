from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from extensions import db
from models import (
    Allenamento, Gara, MovimentoContabile, Messaggio, Presenza, IscrizioneGara, MessaggioNascosto,
    Configurazione,
)
from utils import min_sec_a_secondi, secondi_a_tempo, tempo_stringa_a_min_sec_str

athlete_bp = Blueprint("athlete", __name__, url_prefix="/atleta")


def _messaggi_visibili_query():
    nascosti = db.session.query(MessaggioNascosto.messaggio_id).filter_by(atleta_id=current_user.id)
    return Messaggio.query.filter(
        (Messaggio.destinatario_id == current_user.id) | (Messaggio.destinatario_id.is_(None))
    ).filter(~Messaggio.id.in_(nascosti))


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
    ).order_by(MovimentoContabile.data.desc()).limit(5).all()

    messaggi = _messaggi_visibili_query().order_by(Messaggio.data.desc()).limit(10).all()

    anno_stagione = Configurazione.ottieni().anno_stagione
    categoria = current_user.categoria_master(anno_stagione)

    return render_template(
        "athlete/dashboard.html",
        prossimi_allenamenti=prossimi_allenamenti,
        prossime_gare=prossime_gare,
        movimenti=movimenti,
        saldo=current_user.saldo_attuale(),
        messaggi=messaggi,
        categoria=categoria,
    )


@athlete_bp.route("/messaggi")
@login_required
def lista_messaggi():
    messaggi = _messaggi_visibili_query().order_by(Messaggio.data.desc()).all()
    return render_template("athlete/lista_messaggi.html", messaggi=messaggi)


@athlete_bp.route("/messaggi/<int:messaggio_id>/elimina", methods=["POST"])
@login_required
def elimina_messaggio(messaggio_id):
    messaggio = Messaggio.query.get_or_404(messaggio_id)
    if messaggio.destinatario_id not in (None, current_user.id):
        abort(403)

    if messaggio.destinatario_id == current_user.id:
        db.session.delete(messaggio)
    elif not MessaggioNascosto.query.filter_by(
        messaggio_id=messaggio.id, atleta_id=current_user.id
    ).first():
        db.session.add(MessaggioNascosto(messaggio_id=messaggio.id, atleta_id=current_user.id))

    db.session.commit()
    flash("Messaggio eliminato.", "success")
    next_url = request.form.get("next") or url_for("athlete.dashboard")
    return redirect(next_url)


@athlete_bp.route("/movimenti")
@login_required
def lista_movimenti():
    movimenti = MovimentoContabile.query.filter_by(
        atleta_id=current_user.id
    ).order_by(MovimentoContabile.data.desc()).all()
    return render_template(
        "athlete/lista_movimenti.html", movimenti=movimenti, saldo=current_user.saldo_attuale()
    )


@athlete_bp.route("/allenamenti")
@login_required
def lista_allenamenti():
    q = request.args.get("q", "").strip()
    query = Allenamento.query
    if q:
        like = f"%{q}%"
        query = query.filter((Allenamento.gruppo.ilike(like)) | (Allenamento.sede.ilike(like)))
    allenamenti = query.order_by(Allenamento.data.desc()).all()
    return render_template("athlete/lista_allenamenti.html", allenamenti=allenamenti, q=q)


@athlete_bp.route("/allenamenti/<int:allenamento_id>")
@login_required
def dettaglio_allenamento(allenamento_id):
    allenamento = Allenamento.query.get_or_404(allenamento_id)
    presenza = Presenza.query.filter_by(
        atleta_id=current_user.id, allenamento_id=allenamento.id
    ).first()
    return render_template(
        "athlete/dettaglio_allenamento.html", allenamento=allenamento, presenza=presenza
    )


@athlete_bp.route("/gare")
@login_required
def lista_gare():
    q = request.args.get("q", "").strip()
    query = Gara.query
    if q:
        like = f"%{q}%"
        query = query.filter((Gara.nome.ilike(like)) | (Gara.luogo.ilike(like)))
    gare = query.order_by(Gara.data.desc()).all()
    return render_template("athlete/lista_gare.html", gare=gare, q=q)


@athlete_bp.route("/gare/<int:gara_id>/iscrizione", methods=["GET", "POST"])
@login_required
def iscrizione_gara(gara_id):
    gara = Gara.query.get_or_404(gara_id)

    iscrizioni_correnti = {
        i.stile: i
        for i in IscrizioneGara.query.filter_by(atleta_id=current_user.id, gara_id=gara.id).all()
    }

    if request.method == "POST":
        if not gara.iscrizioni_aperte:
            flash("Le iscrizioni a questo torneo sono chiuse.", "warning")
            return redirect(url_for("athlete.iscrizione_gara", gara_id=gara.id))

        scelte = set(request.form.getlist("tipologie"))

        for tipo, iscrizione in list(iscrizioni_correnti.items()):
            if tipo not in scelte:
                db.session.delete(iscrizione)

        for tipo in scelte:
            secondi = min_sec_a_secondi(
                request.form.get(f"tempo_{tipo}_min"), request.form.get(f"tempo_{tipo}_sec")
            )
            tempo = secondi_a_tempo(secondi) if secondi is not None else None
            if tipo in iscrizioni_correnti:
                iscrizioni_correnti[tipo].tempo_ottenuto = tempo
            else:
                db.session.add(IscrizioneGara(
                    atleta_id=current_user.id, gara_id=gara.id, stile=tipo, tempo_ottenuto=tempo
                ))

        db.session.commit()
        flash("Iscrizione aggiornata.", "success")
        return redirect(url_for("athlete.dashboard"))

    scelte_per_atleta = gara.iscrizioni_per_atleta()
    tempi_min_sec = {
        tipo: tempo_stringa_a_min_sec_str(iscrizione.tempo_ottenuto)
        for tipo, iscrizione in iscrizioni_correnti.items()
    }

    return render_template(
        "athlete/iscrizione_gara.html",
        gara=gara,
        iscrizioni_correnti=iscrizioni_correnti,
        scelte_per_atleta=scelte_per_atleta,
        tempi_min_sec=tempi_min_sec,
    )
