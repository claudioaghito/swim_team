import os
from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort,
    current_app, send_from_directory,
)
from flask_login import login_required, current_user

from extensions import db
from models import (
    Allenamento, Gara, MovimentoContabile, Messaggio, Presenza, IscrizioneGara, MessaggioNascosto,
    Configurazione, AllenamentoNascosto, RecordSocietario, RecordPersonale,
)
from records import griglia_record
from utils import min_sec_a_secondi, secondi_a_tempo, tempo_stringa_a_min_sec_str

# Stessa lista di tipologie di gara usata per i tornei (vedi admin.py), riusata qui
# per il menu a tendina del tipo di gara nei record personali.
from admin import TIPI_GARA_BASE

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

    config = Configurazione.ottieni()
    categoria = current_user.categoria_master(config.anno_stagione)

    return render_template(
        "athlete/dashboard.html",
        prossimi_allenamenti=prossimi_allenamenti,
        prossime_gare=prossime_gare,
        movimenti=movimenti,
        saldo=current_user.saldo_attuale(),
        messaggi=messaggi,
        categoria=categoria,
        modalita_pagamento=config.modalita_pagamento,
    )


@athlete_bp.route("/messaggi")
@login_required
def lista_messaggi():
    messaggi = _messaggi_visibili_query().order_by(Messaggio.data.desc()).all()
    return render_template("athlete/lista_messaggi.html", messaggi=messaggi)


@athlete_bp.route("/messaggi/<int:messaggio_id>/elimina", methods=["POST"])
@login_required
def elimina_messaggio(messaggio_id):
    """L'atleta elimina un messaggio solo dalla propria vista: non tocca mai la riga
    condivisa, ne' per i messaggi diretti ne' per le comunicazioni a tutta la squadra,
    cosi' la cancellazione non ha effetto per il mittente o per gli altri destinatari."""
    messaggio = Messaggio.query.get_or_404(messaggio_id)
    if messaggio.destinatario_id not in (None, current_user.id):
        abort(403)

    if not MessaggioNascosto.query.filter_by(
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
    oggi = datetime.utcnow().date()
    query = Allenamento.query.filter(Allenamento.data >= oggi)
    if q:
        like = f"%{q}%"
        query = query.filter(Allenamento.descrizione.ilike(like))
    allenamenti = query.order_by(Allenamento.data.desc()).all()
    return render_template("athlete/lista_allenamenti.html", allenamenti=allenamenti, q=q)


@athlete_bp.route("/allenamenti/archivio")
@login_required
def archivio_allenamenti():
    """Allenamenti passati, esclusi quelli che l'atleta ha rimosso dal proprio archivio."""
    q = request.args.get("q", "").strip()
    oggi = datetime.utcnow().date()
    nascosti = db.session.query(AllenamentoNascosto.allenamento_id).filter_by(atleta_id=current_user.id)
    query = Allenamento.query.filter(
        Allenamento.data < oggi, ~Allenamento.id.in_(nascosti)
    )
    if q:
        like = f"%{q}%"
        query = query.filter(Allenamento.descrizione.ilike(like))
    allenamenti = query.order_by(Allenamento.data.desc()).all()
    return render_template("athlete/archivio_allenamenti.html", allenamenti=allenamenti, q=q)


@athlete_bp.route("/allenamenti/<int:allenamento_id>/nascondi", methods=["POST"])
@login_required
def nascondi_allenamento(allenamento_id):
    """Rimuove un allenamento passato dal proprio archivio personale (non lo elimina:
    resta visibile agli altri atleti e all'amministratore)."""
    allenamento = Allenamento.query.get_or_404(allenamento_id)
    if not allenamento.passato:
        abort(400)
    if not AllenamentoNascosto.query.filter_by(
        allenamento_id=allenamento.id, atleta_id=current_user.id
    ).first():
        db.session.add(AllenamentoNascosto(allenamento_id=allenamento.id, atleta_id=current_user.id))
        db.session.commit()
    flash("Allenamento rimosso dal tuo archivio.", "success")
    return redirect(url_for("athlete.archivio_allenamenti"))


@athlete_bp.route("/allenamenti/archivio/svuota", methods=["POST"])
@login_required
def svuota_archivio_allenamenti():
    """Rimuove dal proprio archivio tutti gli allenamenti passati non ancora nascosti."""
    oggi = datetime.utcnow().date()
    gia_nascosti = {
        r[0] for r in db.session.query(AllenamentoNascosto.allenamento_id).filter_by(
            atleta_id=current_user.id
        ).all()
    }
    passati = Allenamento.query.filter(Allenamento.data < oggi).all()
    aggiunti = 0
    for al in passati:
        if al.id not in gia_nascosti:
            db.session.add(AllenamentoNascosto(allenamento_id=al.id, atleta_id=current_user.id))
            aggiunti += 1
    db.session.commit()
    flash(f"Archivio svuotato ({aggiunti} allenamento/i rimosso/i dalla tua vista).", "success")
    return redirect(url_for("athlete.archivio_allenamenti"))


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


@athlete_bp.route("/documenti")
@login_required
def documenti():
    """Cartellino e certificato medico dell'atleta loggato: solo visualizzazione/stampa,
    il caricamento e la modifica restano riservati all'amministratore."""
    return render_template("athlete/documenti.html")


@athlete_bp.route("/documenti/cartellino")
@login_required
def cartellino():
    if not current_user.cartellino_file:
        abort(404)
    cartella = os.path.join(current_app.config["UPLOAD_FOLDER"], "cartellini")
    return send_from_directory(cartella, current_user.cartellino_file)


@athlete_bp.route("/documenti/certificato")
@login_required
def certificato():
    if not current_user.certificato_medico_file:
        abort(404)
    cartella = os.path.join(current_app.config["UPLOAD_FOLDER"], "certificati")
    return send_from_directory(cartella, current_user.certificato_medico_file)


@athlete_bp.route("/record")
@login_required
def lista_record():
    """Record societari: solo visualizzazione e stampa/esportazione PDF, la modifica
    resta riservata all'amministratore."""
    sesso = request.args.get("sesso", "M")
    if sesso not in ("M", "F"):
        sesso = "M"
    vasca = 25
    records = RecordSocietario.query.filter_by(sesso=sesso, vasca=vasca).all()
    griglia = griglia_record(records)
    return render_template("athlete/record.html", griglia=griglia, sesso=sesso, vasca=vasca)


@athlete_bp.route("/record-personali")
@login_required
def record_personali():
    """Record personali: sezione riservata all'atleta, che gestisce da solo i propri
    tempi (a differenza dei record societari, qui non c'e' alcun ruolo dell'admin)."""
    record_list = RecordPersonale.query.filter_by(atleta_id=current_user.id).order_by(
        RecordPersonale.data.desc()
    ).all()
    return render_template("athlete/record_personali.html", record_list=record_list)


@athlete_bp.route("/record-personali/nuovo", methods=["GET", "POST"])
@login_required
def nuovo_record_personale():
    if request.method == "POST":
        secondi = min_sec_a_secondi(request.form.get("tempo_min"), request.form.get("tempo_sec"))
        if secondi is None:
            flash("Indica il tempo ottenuto.", "danger")
            return redirect(url_for("athlete.nuovo_record_personale"))

        config = Configurazione.ottieni()
        record = RecordPersonale(
            atleta_id=current_user.id,
            torneo=request.form["torneo"].strip(),
            tipo_gara=request.form["tipo_gara"],
            vasca=int(request.form["vasca"]),
            tempo=secondi_a_tempo(secondi),
            data=datetime.strptime(request.form["data"], "%Y-%m-%d").date(),
            categoria=current_user.categoria_master(config.anno_stagione),
        )
        db.session.add(record)
        db.session.commit()
        flash("Record aggiunto.", "success")
        return redirect(url_for("athlete.record_personali"))

    return render_template("athlete/nuovo_record_personale.html", tipi_gara=TIPI_GARA_BASE)


@athlete_bp.route("/record-personali/<int:record_id>/modifica", methods=["GET", "POST"])
@login_required
def modifica_record_personale(record_id):
    record = RecordPersonale.query.get_or_404(record_id)
    if record.atleta_id != current_user.id:
        abort(403)

    if request.method == "POST":
        secondi = min_sec_a_secondi(request.form.get("tempo_min"), request.form.get("tempo_sec"))
        if secondi is None:
            flash("Indica il tempo ottenuto.", "danger")
            return redirect(url_for("athlete.modifica_record_personale", record_id=record.id))

        config = Configurazione.ottieni()
        record.torneo = request.form["torneo"].strip()
        record.tipo_gara = request.form["tipo_gara"]
        record.vasca = int(request.form["vasca"])
        record.tempo = secondi_a_tempo(secondi)
        record.data = datetime.strptime(request.form["data"], "%Y-%m-%d").date()
        record.categoria = current_user.categoria_master(config.anno_stagione)
        db.session.commit()
        flash("Record aggiornato.", "success")
        return redirect(url_for("athlete.record_personali"))

    tempo_min, tempo_sec = tempo_stringa_a_min_sec_str(record.tempo)
    return render_template(
        "athlete/modifica_record_personale.html", record=record, tipi_gara=TIPI_GARA_BASE,
        tempo_min=tempo_min, tempo_sec=tempo_sec,
    )


@athlete_bp.route("/record-personali/<int:record_id>/elimina", methods=["POST"])
@login_required
def elimina_record_personale(record_id):
    record = RecordPersonale.query.get_or_404(record_id)
    if record.atleta_id != current_user.id:
        abort(403)
    db.session.delete(record)
    db.session.commit()
    flash("Record eliminato.", "success")
    return redirect(url_for("athlete.record_personali"))
