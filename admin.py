import os
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort,
    current_app, send_from_directory,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import User, Allenamento, Gara, MovimentoContabile, Messaggio, Presenza, QuotaTorneo

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def _estensione(filename):
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def _salva_upload(file_storage, sottocartella, nome_base, estensioni_ammesse):
    """Salva il file caricato come <nome_base>.<ext> in UPLOAD_FOLDER/<sottocartella>.
    Ritorna il nome file salvato, o None se non è stato fornito alcun file."""
    if not file_storage or not file_storage.filename:
        return None

    ext = _estensione(file_storage.filename)
    if ext not in estensioni_ammesse:
        raise ValueError(f"Formato file non ammesso: .{ext}")

    nome_file = secure_filename(f"{nome_base}.{ext}")
    cartella = os.path.join(current_app.config["UPLOAD_FOLDER"], sottocartella)
    file_storage.save(os.path.join(cartella, nome_file))
    return nome_file


def _elimina_file(sottocartella, nome_file):
    if not nome_file:
        return
    percorso = os.path.join(current_app.config["UPLOAD_FOLDER"], sottocartella, nome_file)
    if os.path.exists(percorso):
        os.remove(percorso)


def _parsa_data_nascita(valore):
    return datetime.strptime(valore, "%Y-%m-%d").date() if valore else None


TIPI_GARA_BASE = [
    "50 SL", "50 RA", "50 DE", "50 DO",
    "100 DE", "100 SL", "100 DO", "100 RA", "100 MISTI",
    "200 RA", "200 SL", "200 DO", "200 DE", "200 MISTO",
    "400 SL", "800 SL", "1500 SL",
]


@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    atleti = User.query.filter_by(ruolo="atleta").order_by(User.cognome).all()
    prossimi_allenamenti = Allenamento.query.filter(
        Allenamento.data >= datetime.utcnow().date()
    ).order_by(Allenamento.data).limit(5).all()
    prossime_gare = Gara.query.filter(
        Gara.data >= datetime.utcnow().date()
    ).order_by(Gara.data).limit(5).all()

    # Atleti con saldo negativo, utile a colpo d'occhio
    atleti_in_debito = [a for a in atleti if a.saldo_attuale() < 0]

    return render_template(
        "admin/dashboard.html",
        atleti=atleti,
        prossimi_allenamenti=prossimi_allenamenti,
        prossime_gare=prossime_gare,
        atleti_in_debito=atleti_in_debito,
    )


@admin_bp.route("/profilo", methods=["GET", "POST"])
@login_required
@admin_required
def profilo():
    if request.method == "POST":
        password_attuale = request.form.get("password_attuale", "")
        if not current_user.check_password(password_attuale):
            flash("Password attuale non corretta.", "danger")
            return redirect(url_for("admin.profilo"))

        username = request.form["username"].strip()
        esistente = User.query.filter_by(username=username).first()
        if esistente and esistente.id != current_user.id:
            flash("Nome utente già esistente.", "danger")
            return redirect(url_for("admin.profilo"))

        current_user.username = username
        current_user.nome = request.form["nome"].strip()
        current_user.cognome = request.form["cognome"].strip()

        nuova_password = request.form.get("nuova_password", "").strip()
        if nuova_password:
            current_user.set_password(nuova_password)

        db.session.commit()
        flash("Credenziali aggiornate.", "success")
        return redirect(url_for("admin.profilo"))

    return render_template("admin/profilo.html")


@admin_bp.route("/atleti")
@login_required
@admin_required
def lista_atleti():
    q = request.args.get("q", "").strip()
    query = User.query.filter_by(ruolo="atleta")
    if q:
        like = f"%{q}%"
        query = query.filter(
            (User.nome.ilike(like)) | (User.cognome.ilike(like)) | (User.username.ilike(like))
        )
    atleti = query.order_by(User.cognome, User.nome).all()
    return render_template("admin/lista_atleti.html", atleti=atleti, q=q)


@admin_bp.route("/atleti/nuovo", methods=["GET", "POST"])
@login_required
@admin_required
def nuovo_atleta():
    if request.method == "POST":
        username = request.form["username"].strip()
        if User.query.filter_by(username=username).first():
            flash("Nome utente già esistente.", "danger")
            return redirect(url_for("admin.nuovo_atleta"))

        nuovo = User(
            username=username,
            nome=request.form["nome"].strip(),
            cognome=request.form["cognome"].strip(),
            email=request.form.get("email", "").strip(),
            ruolo=request.form.get("ruolo", "atleta"),
            data_nascita=_parsa_data_nascita(request.form.get("data_nascita")),
        )
        nuovo.set_password(request.form["password"])
        db.session.add(nuovo)
        db.session.flush()  # ottiene nuovo.id prima del commit, serve per i nomi file

        try:
            nuovo.cartellino_file = _salva_upload(
                request.files.get("cartellino"), "cartellini", f"cartellino_{nuovo.id}",
                current_app.config["ALLOWED_IMAGE_EXT"],
            )
            nuovo.certificato_medico_file = _salva_upload(
                request.files.get("certificato_medico"), "certificati", f"certificato_{nuovo.id}",
                current_app.config["ALLOWED_PDF_EXT"],
            )
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "danger")
            return redirect(url_for("admin.nuovo_atleta"))

        db.session.commit()
        flash(f"Utente {nuovo.username} creato correttamente.", "success")
        return redirect(url_for("admin.lista_atleti"))

    return render_template("admin/nuovo_atleta.html")


@admin_bp.route("/atleti/<int:atleta_id>")
@login_required
@admin_required
def dettaglio_atleta(atleta_id):
    atleta = User.query.filter_by(id=atleta_id, ruolo="atleta").first_or_404()
    movimenti = MovimentoContabile.query.filter_by(atleta_id=atleta.id).order_by(
        MovimentoContabile.data
    ).all()
    return render_template("admin/dettaglio_atleta.html", atleta=atleta, movimenti=movimenti)


@admin_bp.route("/atleti/<int:atleta_id>/modifica", methods=["GET", "POST"])
@login_required
@admin_required
def modifica_atleta(atleta_id):
    atleta = User.query.filter_by(id=atleta_id, ruolo="atleta").first_or_404()

    if request.method == "POST":
        username = request.form["username"].strip()
        esistente = User.query.filter_by(username=username).first()
        if esistente and esistente.id != atleta.id:
            flash("Nome utente già esistente.", "danger")
            return redirect(url_for("admin.modifica_atleta", atleta_id=atleta.id))

        atleta.username = username
        atleta.nome = request.form["nome"].strip()
        atleta.cognome = request.form["cognome"].strip()
        atleta.email = request.form.get("email", "").strip()
        atleta.data_nascita = _parsa_data_nascita(request.form.get("data_nascita"))

        nuova_password = request.form.get("password", "").strip()
        if nuova_password:
            atleta.set_password(nuova_password)

        try:
            nuovo_cartellino = _salva_upload(
                request.files.get("cartellino"), "cartellini", f"cartellino_{atleta.id}",
                current_app.config["ALLOWED_IMAGE_EXT"],
            )
            if nuovo_cartellino:
                atleta.cartellino_file = nuovo_cartellino

            nuovo_certificato = _salva_upload(
                request.files.get("certificato_medico"), "certificati", f"certificato_{atleta.id}",
                current_app.config["ALLOWED_PDF_EXT"],
            )
            if nuovo_certificato:
                atleta.certificato_medico_file = nuovo_certificato
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "danger")
            return redirect(url_for("admin.modifica_atleta", atleta_id=atleta.id))

        db.session.commit()
        flash("Dati atleta aggiornati.", "success")
        return redirect(url_for("admin.dettaglio_atleta", atleta_id=atleta.id))

    return render_template("admin/modifica_atleta.html", atleta=atleta)


@admin_bp.route("/atleti/<int:atleta_id>/elimina", methods=["POST"])
@login_required
@admin_required
def elimina_atleta(atleta_id):
    atleta = User.query.filter_by(id=atleta_id, ruolo="atleta").first_or_404()

    _elimina_file("cartellini", atleta.cartellino_file)
    _elimina_file("certificati", atleta.certificato_medico_file)

    nome = atleta.nome_completo
    db.session.delete(atleta)
    db.session.commit()
    flash(f"Atleta {nome} eliminato.", "success")
    return redirect(url_for("admin.lista_atleti"))


@admin_bp.route("/atleti/<int:atleta_id>/cartellino")
@login_required
@admin_required
def cartellino_atleta(atleta_id):
    atleta = User.query.filter_by(id=atleta_id, ruolo="atleta").first_or_404()
    if not atleta.cartellino_file:
        abort(404)
    cartella = os.path.join(current_app.config["UPLOAD_FOLDER"], "cartellini")
    return send_from_directory(cartella, atleta.cartellino_file)


@admin_bp.route("/atleti/<int:atleta_id>/certificato")
@login_required
@admin_required
def certificato_atleta(atleta_id):
    atleta = User.query.filter_by(id=atleta_id, ruolo="atleta").first_or_404()
    if not atleta.certificato_medico_file:
        abort(404)
    cartella = os.path.join(current_app.config["UPLOAD_FOLDER"], "certificati")
    return send_from_directory(cartella, atleta.certificato_medico_file)


@admin_bp.route("/allenamenti/nuovo", methods=["GET", "POST"])
@login_required
@admin_required
def nuovo_allenamento():
    if request.method == "POST":
        allenamento = Allenamento(
            data=datetime.strptime(request.form["data"], "%Y-%m-%d").date(),
            gruppo=request.form.get("gruppo", ""),
            sede=request.form.get("sede", ""),
            descrizione=request.form.get("descrizione", ""),
        )
        db.session.add(allenamento)
        db.session.commit()
        flash("Allenamento creato.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/nuovo_allenamento.html")


@admin_bp.route("/allenamenti")
@login_required
@admin_required
def lista_allenamenti():
    allenamenti = Allenamento.query.order_by(Allenamento.data.desc()).all()
    return render_template("admin/lista_allenamenti.html", allenamenti=allenamenti)


@admin_bp.route("/allenamenti/<int:allenamento_id>")
@login_required
@admin_required
def dettaglio_allenamento(allenamento_id):
    allenamento = Allenamento.query.get_or_404(allenamento_id)
    return render_template("admin/dettaglio_allenamento.html", allenamento=allenamento)


@admin_bp.route("/allenamenti/<int:allenamento_id>/modifica", methods=["GET", "POST"])
@login_required
@admin_required
def modifica_allenamento(allenamento_id):
    allenamento = Allenamento.query.get_or_404(allenamento_id)

    if request.method == "POST":
        allenamento.data = datetime.strptime(request.form["data"], "%Y-%m-%d").date()
        allenamento.gruppo = request.form.get("gruppo", "")
        allenamento.sede = request.form.get("sede", "")
        allenamento.descrizione = request.form.get("descrizione", "")
        db.session.commit()
        flash("Allenamento aggiornato.", "success")
        return redirect(url_for("admin.dettaglio_allenamento", allenamento_id=allenamento.id))

    return render_template("admin/modifica_allenamento.html", allenamento=allenamento)


@admin_bp.route("/allenamenti/<int:allenamento_id>/elimina", methods=["POST"])
@login_required
@admin_required
def elimina_allenamento(allenamento_id):
    allenamento = Allenamento.query.get_or_404(allenamento_id)
    db.session.delete(allenamento)
    db.session.commit()
    flash("Allenamento eliminato.", "success")
    return redirect(url_for("admin.lista_allenamenti"))


@admin_bp.route("/gare/nuova", methods=["GET", "POST"])
@login_required
@admin_required
def nuova_gara():
    if request.method == "POST":
        tipologie = request.form.getlist("tipologie")
        altre = request.form.get("altre_tipologie", "").strip()
        if altre:
            tipologie += [t.strip() for t in altre.split(",") if t.strip()]

        gara = Gara(
            nome=request.form["nome"].strip(),
            data=datetime.strptime(request.form["data"], "%Y-%m-%d").date(),
            luogo=request.form.get("luogo", ""),
            quota_gara=request.form.get("quota_gara", 0) or 0,
            quota_staffetta=request.form.get("quota_staffetta", 0) or 0,
            scadenza_iscrizione=(
                datetime.strptime(request.form["scadenza_iscrizione"], "%Y-%m-%d").date()
                if request.form.get("scadenza_iscrizione") else None
            ),
            tipologie_gara=",".join(tipologie),
            note=request.form.get("note", "").strip(),
        )
        db.session.add(gara)
        db.session.flush()

        try:
            gara.programma_gare_file = _salva_upload(
                request.files.get("programma_gare"), "programmi_gare", f"programma_{gara.id}",
                current_app.config["ALLOWED_PDF_EXT"],
            )
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "danger")
            return redirect(url_for("admin.nuova_gara"))

        db.session.commit()
        flash("Torneo creato.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/nuova_gara.html", tipi_gara_base=TIPI_GARA_BASE)


@admin_bp.route("/gare")
@login_required
@admin_required
def lista_gare():
    gare = Gara.query.order_by(Gara.data.desc()).all()
    return render_template("admin/lista_gare.html", gare=gare)


@admin_bp.route("/gare/<int:gara_id>")
@login_required
@admin_required
def dettaglio_gara(gara_id):
    gara = Gara.query.get_or_404(gara_id)
    scelte_per_atleta = gara.iscrizioni_per_atleta()
    max_gare = max((len(v) for v in scelte_per_atleta.values()), default=0)

    quote_per_atleta = {
        q.atleta_id: q
        for q in QuotaTorneo.query.filter_by(gara_id=gara.id).all()
    }

    return render_template(
        "admin/dettaglio_gara.html",
        gara=gara,
        scelte_per_atleta=scelte_per_atleta,
        max_gare=max_gare,
        quote_per_atleta=quote_per_atleta,
    )


@admin_bp.route("/gare/<int:gara_id>/quota/<int:atleta_id>", methods=["POST"])
@login_required
@admin_required
def conferma_quota_gara(gara_id, atleta_id):
    gara = Gara.query.get_or_404(gara_id)
    atleta = User.query.filter_by(id=atleta_id, ruolo="atleta").first_or_404()

    importo_str = request.form.get("importo", "").strip()
    if not importo_str:
        flash("Inserisci un importo per confermare la quota.", "warning")
        return redirect(url_for("admin.dettaglio_gara", gara_id=gara.id))

    try:
        importo = float(importo_str)
    except ValueError:
        flash("Importo non valido.", "danger")
        return redirect(url_for("admin.dettaglio_gara", gara_id=gara.id))

    quota = QuotaTorneo.query.filter_by(atleta_id=atleta.id, gara_id=gara.id).first()
    if not quota:
        quota = QuotaTorneo(atleta_id=atleta.id, gara_id=gara.id)
        db.session.add(quota)

    if quota.movimento_id:
        movimento = MovimentoContabile.query.get(quota.movimento_id)
        movimento.importo = -importo
        movimento.causale = f"Quota gara: {gara.nome}"
    else:
        movimento = MovimentoContabile(
            atleta_id=atleta.id,
            importo=-importo,
            causale=f"Quota gara: {gara.nome}",
            registrato_da_id=current_user.id,
        )
        db.session.add(movimento)
        db.session.flush()
        quota.movimento_id = movimento.id

    quota.importo = importo
    db.session.commit()
    flash(f"Quota di {importo:.2f} € addebitata a {atleta.nome_completo}.", "success")
    return redirect(url_for("admin.dettaglio_gara", gara_id=gara.id))


@admin_bp.route("/gare/<int:gara_id>/modifica", methods=["GET", "POST"])
@login_required
@admin_required
def modifica_gara(gara_id):
    gara = Gara.query.get_or_404(gara_id)

    if request.method == "POST":
        tipologie = request.form.getlist("tipologie")
        altre = request.form.get("altre_tipologie", "").strip()
        if altre:
            tipologie += [t.strip() for t in altre.split(",") if t.strip()]

        gara.nome = request.form["nome"].strip()
        gara.data = datetime.strptime(request.form["data"], "%Y-%m-%d").date()
        gara.luogo = request.form.get("luogo", "")
        gara.quota_gara = request.form.get("quota_gara", 0) or 0
        gara.quota_staffetta = request.form.get("quota_staffetta", 0) or 0
        gara.scadenza_iscrizione = (
            datetime.strptime(request.form["scadenza_iscrizione"], "%Y-%m-%d").date()
            if request.form.get("scadenza_iscrizione") else None
        )
        gara.tipologie_gara = ",".join(tipologie)
        gara.note = request.form.get("note", "").strip()

        try:
            nuovo_programma = _salva_upload(
                request.files.get("programma_gare"), "programmi_gare", f"programma_{gara.id}",
                current_app.config["ALLOWED_PDF_EXT"],
            )
            if nuovo_programma:
                gara.programma_gare_file = nuovo_programma
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "danger")
            return redirect(url_for("admin.modifica_gara", gara_id=gara.id))

        db.session.commit()
        flash("Torneo aggiornato.", "success")
        return redirect(url_for("admin.dettaglio_gara", gara_id=gara.id))

    tipi_extra = ", ".join(t for t in gara.lista_tipologie if t not in TIPI_GARA_BASE)
    return render_template(
        "admin/modifica_gara.html", gara=gara, tipi_gara_base=TIPI_GARA_BASE, tipi_extra=tipi_extra
    )


@admin_bp.route("/gare/<int:gara_id>/programma")
@login_required
def programma_gara(gara_id):
    gara = Gara.query.get_or_404(gara_id)
    if not gara.programma_gare_file:
        abort(404)
    cartella = os.path.join(current_app.config["UPLOAD_FOLDER"], "programmi_gare")
    return send_from_directory(cartella, gara.programma_gare_file)


@admin_bp.route("/movimenti")
@login_required
@admin_required
def lista_movimenti():
    movimenti = MovimentoContabile.query.order_by(MovimentoContabile.data).all()
    return render_template("admin/lista_movimenti.html", movimenti=movimenti)


@admin_bp.route("/movimenti/nuovo", methods=["GET", "POST"])
@login_required
@admin_required
def nuovo_movimento():
    atleti = User.query.filter_by(ruolo="atleta").order_by(User.cognome).all()

    if request.method == "POST":
        movimento = MovimentoContabile(
            atleta_id=request.form["atleta_id"],
            importo=request.form["importo"],
            causale=request.form["causale"].strip(),
            registrato_da_id=current_user.id,
        )
        db.session.add(movimento)
        db.session.commit()
        flash("Movimento contabile registrato.", "success")
        return redirect(url_for("admin.lista_movimenti"))

    return render_template("admin/nuovo_movimento.html", atleti=atleti)


@admin_bp.route("/movimenti/elimina", methods=["POST"])
@login_required
@admin_required
def elimina_movimenti():
    ids = request.form.getlist("movimento_ids")
    next_url = request.form.get("next") or url_for("admin.lista_movimenti")

    if not ids:
        flash("Nessun movimento selezionato.", "warning")
        return redirect(next_url)

    eliminati = MovimentoContabile.query.filter(MovimentoContabile.id.in_(ids)).delete(
        synchronize_session=False
    )
    db.session.commit()
    flash(f"{eliminati} movimento/i eliminato/i.", "success")
    return redirect(next_url)


@admin_bp.route("/messaggi/nuovo", methods=["GET", "POST"])
@login_required
@admin_required
def nuovo_messaggio():
    atleti = User.query.filter_by(ruolo="atleta").order_by(User.cognome).all()

    if request.method == "POST":
        destinatario_id = request.form.get("destinatario_id") or None
        messaggio = Messaggio(
            mittente_id=current_user.id,
            destinatario_id=destinatario_id,
            testo=request.form["testo"].strip(),
        )
        db.session.add(messaggio)
        db.session.commit()
        flash("Messaggio inviato.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/nuovo_messaggio.html", atleti=atleti)


@admin_bp.route("/messaggi")
@login_required
@admin_required
def lista_messaggi():
    messaggi = Messaggio.query.order_by(Messaggio.data.desc()).all()
    return render_template("admin/lista_messaggi.html", messaggi=messaggi)


@admin_bp.route("/messaggi/<int:messaggio_id>/elimina", methods=["POST"])
@login_required
@admin_required
def elimina_messaggio(messaggio_id):
    messaggio = Messaggio.query.get_or_404(messaggio_id)
    db.session.delete(messaggio)
    db.session.commit()
    flash("Messaggio eliminato.", "success")
    return redirect(url_for("admin.lista_messaggi"))
