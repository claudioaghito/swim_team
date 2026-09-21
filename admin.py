import csv
import io
import json
import os
import shutil
import zipfile
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort,
    current_app, send_from_directory, send_file, Response,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import (
    User, Allenamento, Gara, MovimentoContabile, Messaggio, Presenza, QuotaTorneo, Configurazione,
    FormazioneStaffetta, IscrizioneGara, RecordSocietario,
)
from piani_allenamento import FASI_TIPI, FASI_TIPI_CODICI
from records import STILI_RECORD, STILI_CODICI, STILI_NOMI, CATEGORIE_RECORD, griglia_record
from relay_master import Nuotatore, RELAY_BRACKETS, tutte_le_formazioni_possibili
from utils import (
    tempo_a_secondi as _tempo_a_secondi, secondi_a_tempo as _secondi_a_tempo,
    min_sec_a_secondi, tempo_stringa_a_min_sec_str,
)

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


def _parsa_data(valore):
    return datetime.strptime(valore, "%Y-%m-%d").date() if valore else None


def _intero_o_none(valore):
    try:
        return int(valore)
    except (TypeError, ValueError):
        return None


def _pulisci_piano(raw_json):
    """Valida e normalizza il piano JSON inviato dal form del builder; scarta blocchi/fasi
    vuoti e ignora l'input se non e' JSON valido. Ritorna None se non c'e' alcun piano da
    salvare. Ogni fase ha 'blocchi': [{ripetizioni, righe:[{serie,esercizio,recupero,
    ripartenza}]}] — un blocco raggruppa le serie che vanno ripetute insieme (es. "x2")."""
    if not raw_json:
        return None
    try:
        fasi = json.loads(raw_json)
    except ValueError:
        return None
    if not isinstance(fasi, list):
        return None

    pulite = []
    for fase in fasi:
        if not isinstance(fase, dict):
            continue

        blocchi_puliti = []
        for blocco in fase.get("blocchi") or []:
            if not isinstance(blocco, dict):
                continue
            righe_pulite = []
            for riga in blocco.get("righe") or []:
                if not isinstance(riga, dict):
                    continue
                riga_pulita = {
                    campo: (riga.get(campo) or "").strip()
                    for campo in ("serie", "esercizio", "recupero", "ripartenza")
                }
                if any(riga_pulita.values()):
                    righe_pulite.append(riga_pulita)
            if righe_pulite:
                blocchi_puliti.append({
                    "ripetizioni": (blocco.get("ripetizioni") or "").strip(),
                    "righe": righe_pulite,
                })

        nome = (fase.get("nome") or "").strip()
        if not nome and not blocchi_puliti:
            continue

        pulite.append({
            "tipo": fase.get("tipo") if fase.get("tipo") in FASI_TIPI_CODICI else "altro",
            "nome": nome,
            "durata_min": _intero_o_none(fase.get("durata_min")),
            "metri": _intero_o_none(fase.get("metri")),
            "sottotitolo": (fase.get("sottotitolo") or "").strip(),
            "nota": (fase.get("nota") or "").strip(),
            "blocchi": blocchi_puliti,
        })

    return json.dumps(pulite) if pulite else None


def _prove_staffetta(tipo):
    """Deduce le 4 prove/frazioni di una staffetta dal nome della tipologia."""
    if "misti" in tipo.lower():
        return ["DO", "RA", "FA", "SL"]
    return ["SL", "SL", "SL", "SL"]


def _tipo_squadra_da_tipo(tipo):
    """Deduce il vincolo di composizione (M / F / MISTA) dal nome della tipologia,
    che termina con "M", "F" o "M/F" (es. "STAFFETTA 4X100 SL M/F")."""
    t = tipo.strip().upper()
    if t.endswith("M/F"):
        return "MISTA"
    if t.endswith(" M"):
        return "M"
    if t.endswith(" F"):
        return "F"
    return None


TIPI_GARA_BASE = [
    "50 SL", "100 SL", "200 SL", "400 SL", "800 SL", "1500 SL",
    "50 DO", "100 DO", "200 DO",
    "50 RA", "100 RA", "200 RA",
    "50 FA", "100 FA", "200 FA",
    "100 MISTO", "200 MISTO", "400 MISTO",
    "STAFFETTA 4X50 SL M", "STAFFETTA 4X50 SL F", "STAFFETTA 4X50 SL M/F",
    "STAFFETTA 4X100 SL M", "STAFFETTA 4X100 SL F", "STAFFETTA 4X100 SL M/F",
    "STAFFETTA 4X200 SL M", "STAFFETTA 4X200 SL F", "STAFFETTA 4X200 SL M/F",
    "STAFFETTA 4X50 MISTI M", "STAFFETTA 4X50 MISTI F", "STAFFETTA 4X50 MISTI M/F",
    "STAFFETTA 4X100 MISTI M", "STAFFETTA 4X100 MISTI F", "STAFFETTA 4X100 MISTI M/F",
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

    # Certificati medici scaduti o in scadenza entro 30 giorni
    atleti_certificato_scaduto = [a for a in atleti if a.certificato_medico_valido is False]
    atleti_certificato_in_scadenza = [a for a in atleti if a.certificato_medico_in_scadenza]

    # Presenze agli ultimi allenamenti svolti, per il grafico in dashboard
    ultimi_allenamenti = Allenamento.query.filter(
        Allenamento.data <= datetime.utcnow().date()
    ).order_by(Allenamento.data.desc()).limit(8).all()
    ultimi_allenamenti.reverse()
    grafico_presenze = {
        "etichette": [al.data.strftime("%d/%m") for al in ultimi_allenamenti],
        "valori": [
            Presenza.query.filter_by(allenamento_id=al.id, presente=True).count()
            for al in ultimi_allenamenti
        ],
    }

    return render_template(
        "admin/dashboard.html",
        atleti=atleti,
        prossimi_allenamenti=prossimi_allenamenti,
        prossime_gare=prossime_gare,
        grafico_presenze=grafico_presenze,
        atleti_in_debito=atleti_in_debito,
        atleti_certificato_scaduto=atleti_certificato_scaduto,
        atleti_certificato_in_scadenza=atleti_certificato_in_scadenza,
    )


@admin_bp.route("/cerca")
@login_required
@admin_required
def ricerca():
    q = request.args.get("q", "").strip()
    risultati = {"atleti": [], "tornei": [], "allenamenti": [], "movimenti": []}

    if q:
        like = f"%{q}%"
        risultati["atleti"] = User.query.filter_by(ruolo="atleta").filter(
            (User.nome.ilike(like)) | (User.cognome.ilike(like)) | (User.username.ilike(like))
        ).order_by(User.cognome, User.nome).all()

        risultati["tornei"] = Gara.query.filter(
            (Gara.nome.ilike(like)) | (Gara.luogo.ilike(like))
        ).order_by(Gara.data.desc()).all()

        risultati["allenamenti"] = Allenamento.query.filter(
            Allenamento.descrizione.ilike(like)
        ).order_by(Allenamento.data.desc()).all()

        risultati["movimenti"] = MovimentoContabile.query.join(User, MovimentoContabile.atleta_id == User.id).filter(
            (MovimentoContabile.causale.ilike(like)) | (User.nome.ilike(like)) | (User.cognome.ilike(like))
        ).order_by(MovimentoContabile.data.desc()).all()

    totale = sum(len(v) for v in risultati.values())
    return render_template("admin/ricerca.html", q=q, risultati=risultati, totale=totale)


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


@admin_bp.route("/impostazioni", methods=["GET", "POST"])
@login_required
@admin_required
def impostazioni():
    config = Configurazione.ottieni()

    if request.method == "POST":
        try:
            anno = int(request.form["anno_stagione"])
        except (KeyError, ValueError):
            flash("Anno stagione non valido.", "danger")
            return redirect(url_for("admin.impostazioni"))

        config.anno_stagione = anno
        config.modalita_pagamento = request.form.get("modalita_pagamento", "").strip()
        db.session.commit()
        flash("Impostazioni aggiornate.", "success")
        return redirect(url_for("admin.impostazioni"))

    return render_template("admin/impostazioni.html", config=config)


def _percorso_db():
    """Percorso assoluto del file .db, o None se non si tratta di SQLite."""
    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    prefisso = "sqlite:///"
    if not uri.startswith(prefisso):
        return None
    percorso = uri[len(prefisso):]
    if not os.path.isabs(percorso):
        percorso = os.path.join(current_app.root_path, percorso)
    return percorso


def _crea_zip_backup():
    """Zip in memoria con database + cartella uploads (foto, certificati). None se non SQLite.

    Il file .db viene copiato per intero: include automaticamente ogni tabella (record
    personali compresi), senza bisogno di elencarle qui una per una."""
    percorso_db = _percorso_db()
    if not percorso_db or not os.path.exists(percorso_db):
        return None

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(percorso_db, "squadra.db")
        cartella_uploads = current_app.config["UPLOAD_FOLDER"]
        for radice, _dirs, nomi_file in os.walk(cartella_uploads):
            for nome in nomi_file:
                assoluto = os.path.join(radice, nome)
                relativo = os.path.join("uploads", os.path.relpath(assoluto, cartella_uploads))
                zf.write(assoluto, relativo)
    buffer.seek(0)
    return buffer


@admin_bp.route("/backup")
@login_required
@admin_required
def backup():
    """Scarica il solo file del database SQLite (senza foto/certificati)."""
    percorso_db = _percorso_db()
    if not percorso_db:
        abort(404)  # backup diretto disponibile solo per SQLite
    nome_file = f"backup_squadra_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
    return send_file(percorso_db, as_attachment=True, download_name=nome_file)


@admin_bp.route("/backup/completo")
@login_required
@admin_required
def backup_completo():
    """Scarica un archivio zip con database + tutte le foto/certificati caricati."""
    buffer = _crea_zip_backup()
    if buffer is None:
        abort(404)
    nome_file = f"backup_completo_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
    return send_file(buffer, as_attachment=True, download_name=nome_file, mimetype="application/zip")


@admin_bp.route("/backup/ripristina", methods=["POST"])
@login_required
@admin_required
def ripristina_backup():
    """Sovrascrive database (e, se presenti nello zip, i file caricati) con un backup precedente."""
    password_attuale = request.form.get("password_attuale", "")
    if not current_user.check_password(password_attuale):
        flash("Password non corretta: ripristino annullato.", "danger")
        return redirect(url_for("admin.impostazioni"))

    file_caricato = request.files.get("file_backup")
    if not file_caricato or not file_caricato.filename:
        flash("Seleziona un file di backup da caricare.", "danger")
        return redirect(url_for("admin.impostazioni"))

    estensione = _estensione(file_caricato.filename)
    if estensione not in {"zip", "db"}:
        flash("Formato file non valido: carica un backup .zip o .db.", "danger")
        return redirect(url_for("admin.impostazioni"))

    percorso_db = _percorso_db()
    if not percorso_db:
        abort(404)

    if estensione == "zip":
        try:
            zf = zipfile.ZipFile(file_caricato.stream)
        except zipfile.BadZipFile:
            flash("Il file caricato non è un archivio zip valido.", "danger")
            return redirect(url_for("admin.impostazioni"))

        nomi = zf.namelist()
        if "squadra.db" not in nomi:
            flash("Lo zip non contiene 'squadra.db': ripristino annullato.", "danger")
            return redirect(url_for("admin.impostazioni"))

        for nome in nomi:
            normalizzato = os.path.normpath(nome)
            if normalizzato.startswith("..") or os.path.isabs(normalizzato):
                flash("Archivio non valido (percorso sospetto): ripristino annullato.", "danger")
                return redirect(url_for("admin.impostazioni"))

    # Copia di sicurezza dei dati attuali, prima di sovrascrivere qualsiasi cosa
    cartella_backups = os.path.join(current_app.instance_path, "backups")
    os.makedirs(cartella_backups, exist_ok=True)
    buffer_sicurezza = _crea_zip_backup()
    if buffer_sicurezza:
        nome_sicurezza = f"pre_ripristino_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
        with open(os.path.join(cartella_backups, nome_sicurezza), "wb") as f:
            f.write(buffer_sicurezza.getvalue())

    # Il file sta per essere sostituito sotto ai piedi delle connessioni aperte: le chiudiamo prima
    db.session.remove()
    db.engine.dispose()

    if estensione == "db":
        file_caricato.save(percorso_db)
    else:
        with zf.open("squadra.db") as origine, open(percorso_db, "wb") as destinazione:
            shutil.copyfileobj(origine, destinazione)

        cartella_uploads = current_app.config["UPLOAD_FOLDER"]
        voci_uploads = [n for n in nomi if n.startswith("uploads/") and not n.endswith("/")]
        if voci_uploads:
            shutil.rmtree(cartella_uploads, ignore_errors=True)
            os.makedirs(cartella_uploads, exist_ok=True)
            for nome in voci_uploads:
                destino = os.path.join(cartella_uploads, os.path.relpath(nome, "uploads"))
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                with zf.open(nome) as origine, open(destino, "wb") as f_out:
                    shutil.copyfileobj(origine, f_out)
        zf.close()

    flash(
        "Ripristino completato. Se l'app non mostra subito i nuovi dati, ricarica la web app "
        "(su PythonAnywhere: pagina Web → Reload).",
        "success",
    )
    return redirect(url_for("admin.impostazioni"))


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
    anno_stagione = Configurazione.ottieni().anno_stagione
    return render_template("admin/lista_atleti.html", atleti=atleti, q=q, anno_stagione=anno_stagione)


@admin_bp.route("/atleti/esporta")
@login_required
@admin_required
def esporta_atleti():
    atleti = User.query.filter_by(ruolo="atleta").order_by(User.cognome, User.nome).all()
    anno_stagione = Configurazione.ottieni().anno_stagione

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Nome", "Cognome", "Utente", "Sesso", "Email", "Data di nascita", "Categoria", "Saldo (€)"])
    for a in atleti:
        writer.writerow([
            a.nome,
            a.cognome,
            a.username,
            a.sesso or "",
            a.email or "",
            a.data_nascita.strftime("%d/%m/%Y") if a.data_nascita else "",
            a.categoria_master(anno_stagione) or "",
            f"{a.saldo_attuale():.2f}",
        ])

    resp = Response("\N{ZERO WIDTH NO-BREAK SPACE}" + output.getvalue(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=atleti.csv"
    return resp


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
            data_nascita=_parsa_data(request.form.get("data_nascita")),
            sesso=request.form.get("sesso") or None,
            certificato_medico_scadenza=_parsa_data(request.form.get("certificato_medico_scadenza")),
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
                current_app.config["ALLOWED_CERTIFICATO_EXT"],
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
    anno_stagione = Configurazione.ottieni().anno_stagione
    return render_template(
        "admin/dettaglio_atleta.html", atleta=atleta, movimenti=movimenti, anno_stagione=anno_stagione
    )


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
        atleta.data_nascita = _parsa_data(request.form.get("data_nascita"))
        atleta.sesso = request.form.get("sesso") or None
        atleta.certificato_medico_scadenza = _parsa_data(request.form.get("certificato_medico_scadenza"))

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
                current_app.config["ALLOWED_CERTIFICATO_EXT"],
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
        descrizione = request.form.get("descrizione", "").strip()
        if not descrizione:
            flash("Inserisci una descrizione per poter salvare l'allenamento.", "danger")
            return redirect(url_for("admin.nuovo_allenamento"))

        allenamento = Allenamento(
            data=datetime.strptime(request.form["data"], "%Y-%m-%d").date(),
            descrizione=descrizione,
            piano_json=_pulisci_piano(request.form.get("piano_json")),
        )
        db.session.add(allenamento)
        db.session.commit()
        flash("Allenamento creato.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/nuovo_allenamento.html", fasi_tipi=FASI_TIPI)


@admin_bp.route("/allenamenti")
@login_required
@admin_required
def lista_allenamenti():
    q = request.args.get("q", "").strip()
    vista = request.args.get("vista", "prossimi")
    oggi = datetime.utcnow().date()

    query = Allenamento.query
    if vista == "archivio":
        query = query.filter(Allenamento.data < oggi)
    elif vista == "prossimi":
        query = query.filter(Allenamento.data >= oggi)
    # vista == "tutti": nessun filtro sulla data

    if q:
        like = f"%{q}%"
        query = query.filter(Allenamento.descrizione.ilike(like))
    allenamenti = query.order_by(Allenamento.data.desc()).all()
    return render_template("admin/lista_allenamenti.html", allenamenti=allenamenti, q=q, vista=vista)


@admin_bp.route("/allenamenti/statistiche")
@login_required
@admin_required
def statistiche_presenze():
    oggi = datetime.utcnow().date()
    totale_allenamenti = Allenamento.query.filter(Allenamento.data <= oggi).count()

    atleti = User.query.filter_by(ruolo="atleta").order_by(User.cognome, User.nome).all()
    statistiche = []
    for atleta in atleti:
        presenze = Presenza.query.filter_by(atleta_id=atleta.id, presente=True).join(
            Allenamento, Presenza.allenamento_id == Allenamento.id
        ).filter(Allenamento.data <= oggi).count()
        percentuale = (presenze / totale_allenamenti * 100) if totale_allenamenti else 0
        statistiche.append({"atleta": atleta, "presenze": presenze, "percentuale": percentuale})

    statistiche.sort(key=lambda s: s["percentuale"], reverse=True)

    return render_template(
        "admin/statistiche_presenze.html",
        statistiche=statistiche,
        totale_allenamenti=totale_allenamenti,
    )


@admin_bp.route("/allenamenti/<int:allenamento_id>")
@login_required
@admin_required
def dettaglio_allenamento(allenamento_id):
    allenamento = Allenamento.query.get_or_404(allenamento_id)
    atleti = User.query.filter_by(ruolo="atleta").order_by(User.cognome, User.nome).all()
    presenze_per_atleta = {
        p.atleta_id: p for p in Presenza.query.filter_by(allenamento_id=allenamento.id).all()
    }
    return render_template(
        "admin/dettaglio_allenamento.html",
        allenamento=allenamento,
        atleti=atleti,
        presenze_per_atleta=presenze_per_atleta,
    )


@admin_bp.route("/allenamenti/<int:allenamento_id>/presenze", methods=["POST"])
@login_required
@admin_required
def salva_presenze(allenamento_id):
    allenamento = Allenamento.query.get_or_404(allenamento_id)
    atleti = User.query.filter_by(ruolo="atleta").all()
    presenti_ids = set(request.form.getlist("presenti"))

    for atleta in atleti:
        presenza = Presenza.query.filter_by(atleta_id=atleta.id, allenamento_id=allenamento.id).first()
        presente = str(atleta.id) in presenti_ids
        if not presenza:
            if not presente:
                continue
            presenza = Presenza(atleta_id=atleta.id, allenamento_id=allenamento.id)
            db.session.add(presenza)
        presenza.presente = presente

    db.session.commit()
    flash("Presenze salvate.", "success")
    return redirect(url_for("admin.dettaglio_allenamento", allenamento_id=allenamento.id))


@admin_bp.route("/allenamenti/<int:allenamento_id>/modifica", methods=["GET", "POST"])
@login_required
@admin_required
def modifica_allenamento(allenamento_id):
    allenamento = Allenamento.query.get_or_404(allenamento_id)

    if request.method == "POST":
        descrizione = request.form.get("descrizione", "").strip()
        if not descrizione:
            flash(
                "Inserisci una descrizione per poter salvare le modifiche: puoi solo "
                "eliminare l'allenamento o annullare senza salvare.",
                "danger",
            )
            return redirect(url_for("admin.modifica_allenamento", allenamento_id=allenamento.id))

        allenamento.data = datetime.strptime(request.form["data"], "%Y-%m-%d").date()
        allenamento.descrizione = descrizione
        allenamento.piano_json = _pulisci_piano(request.form.get("piano_json"))
        db.session.commit()
        flash("Allenamento aggiornato.", "success")
        return redirect(url_for("admin.dettaglio_allenamento", allenamento_id=allenamento.id))

    return render_template("admin/modifica_allenamento.html", allenamento=allenamento, fasi_tipi=FASI_TIPI)


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

        if not tipologie:
            flash("Seleziona almeno una tipologia di gara per poter salvare il torneo.", "danger")
            return redirect(url_for("admin.nuova_gara"))

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
    q = request.args.get("q", "").strip()
    query = Gara.query
    if q:
        like = f"%{q}%"
        query = query.filter((Gara.nome.ilike(like)) | (Gara.luogo.ilike(like)))
    gare = query.order_by(Gara.data.desc()).all()
    return render_template("admin/lista_gare.html", gare=gare, q=q)


@admin_bp.route("/gare/<int:gara_id>")
@login_required
@admin_required
def dettaglio_gara(gara_id):
    gara = Gara.query.get_or_404(gara_id)
    scelte_per_atleta = gara.iscrizioni_per_atleta()

    quote_per_atleta = {
        q.atleta_id: q
        for q in QuotaTorneo.query.filter_by(gara_id=gara.id).all()
    }

    tipi_staffetta = [t for t in gara.lista_tipologie if "staffetta" in t.lower()]

    # Le staffette hanno una sezione dedicata (formazioni salvate): non vanno duplicate
    # nell'elenco/PDF delle gare individuali, che pero' continua a usare tutte le
    # iscrizioni (staffette incluse) per il calcolo corretto della quota.
    scelte_gare_individuali = {
        atleta: [i for i in iscrizioni if "staffetta" not in (i.stile or "").lower()]
        for atleta, iscrizioni in scelte_per_atleta.items()
    }

    config = Configurazione.ottieni()
    anno_stagione = config.anno_stagione

    # Totale costo torneo: somma delle quote calcolate per ciascun atleta iscritto
    # (gara + staffetta secondo il tipo di iscrizione), e quanto gia' addebitato.
    totale_calcolato = sum(gara.calcola_quota(iscrizioni) for iscrizioni in scelte_per_atleta.values())
    totale_addebitato = sum(
        float(q.importo) for q in quote_per_atleta.values() if q.movimento_id and q.importo
    )

    return render_template(
        "admin/dettaglio_gara.html",
        gara=gara,
        modalita_pagamento=config.modalita_pagamento,
        scelte_per_atleta=scelte_per_atleta,
        scelte_gare_individuali=scelte_gare_individuali,
        quote_per_atleta=quote_per_atleta,
        tipi_staffetta=tipi_staffetta,
        anno_stagione=anno_stagione,
        totale_calcolato=totale_calcolato,
        totale_addebitato=totale_addebitato,
    )


@admin_bp.route("/gare/<int:gara_id>/staffetta/<path:tipo>", methods=["GET", "POST"])
@login_required
@admin_required
def formazione_staffetta(gara_id, tipo):
    """Strumento admin per scegliere la formazione migliore di una staffetta,
    a partire dagli atleti che si sono iscritti a quella tipologia di gara."""
    gara = Gara.query.get_or_404(gara_id)
    if tipo not in gara.lista_tipologie or "staffetta" not in tipo.lower():
        abort(404)

    iscritti = sorted(
        {i.atleta for i in gara.iscrizioni if i.stile == tipo},
        key=lambda a: (a.cognome, a.nome),
    )
    tempo_registrato = {
        i.atleta_id: i.tempo_ottenuto
        for i in gara.iscrizioni if i.stile == tipo
    }
    tempo_registrato_min_sec = {
        atleta_id: tempo_stringa_a_min_sec_str(tempo) for atleta_id, tempo in tempo_registrato.items()
    }
    prove = _prove_staffetta(tipo)
    prove_uniche = list(dict.fromkeys(prove))  # per la staffetta SL basta un campo tempo per atleta
    anno_stagione = Configurazione.ottieni().anno_stagione
    tipo_squadra = _tipo_squadra_da_tipo(tipo)
    senza_sesso = [a.nome_completo for a in iscritti if not a.sesso] if tipo_squadra else []

    id_iscritti = {a.id for a in iscritti}
    atleti_convocabili = sorted(
        (a for a in User.query.filter_by(ruolo="atleta").all() if a.id not in id_iscritti),
        key=lambda a: (a.cognome, a.nome),
    )

    risultati = None
    errore = None
    valori_form = {}
    strategia = "tempo_minimo"

    if request.method == "POST":
        strategia = request.form.get("strategia", "tempo_minimo")
        valori_form = request.form

        candidati = []
        for atleta in iscritti:
            if not atleta.data_nascita:
                continue
            if tipo_squadra and not atleta.sesso:
                continue
            eta = anno_stagione - atleta.data_nascita.year
            tempi = {}
            for prova in prove_uniche:
                secondi = min_sec_a_secondi(
                    request.form.get(f"tempo_{atleta.id}_{prova}_min"),
                    request.form.get(f"tempo_{atleta.id}_{prova}_sec"),
                )
                if secondi is not None:
                    tempi[prova] = secondi
            candidati.append(Nuotatore(nome=atleta.nome_completo, eta=eta, sesso=atleta.sesso, tempi=tempi))

        if len(candidati) < 4:
            errore = (
                "Servono almeno 4 atleti con eta' inserita (e sesso, se richiesto dalla composizione) "
                "per calcolare una formazione. Il tempo e' obbligatorio solo con la strategia 'tempo minimo'."
            )
        else:
            formazioni_per_categoria = tutte_le_formazioni_possibili(
                candidati, prove, tipo_squadra=tipo_squadra, strategia=strategia
            )
            risultati = []
            for categoria, (eta_min, eta_max) in RELAY_BRACKETS.items():
                formazione = formazioni_per_categoria.get(categoria)
                fascia = f"{eta_min}+" if eta_max is None else f"{eta_min}-{eta_max}"
                if formazione:
                    righe = [
                        {
                            "nome": n.nome, "prova": p, "sesso": n.sesso,
                            "tempo": _secondi_a_tempo(n.tempi[p]) if p in n.tempi else "n/d",
                        }
                        for n, p in formazione.frazioni
                    ]
                    tempo_totale_fmt = (
                        _secondi_a_tempo(formazione.tempo_totale)
                        if formazione.tempo_totale is not None else "n/d"
                    )
                else:
                    righe = None
                    tempo_totale_fmt = None
                risultati.append({
                    "categoria": categoria,
                    "fascia": fascia,
                    "righe": righe,
                    "tempo_totale": tempo_totale_fmt,
                    "somma_eta": formazione.somma_eta if formazione else None,
                })

                if formazione:
                    salvata = FormazioneStaffetta.query.filter_by(
                        gara_id=gara.id, tipo=tipo, categoria=categoria
                    ).first()
                    if not salvata:
                        salvata = FormazioneStaffetta(gara_id=gara.id, tipo=tipo, categoria=categoria)
                        db.session.add(salvata)
                    salvata.fascia_eta = fascia
                    salvata.strategia = strategia
                    salvata.somma_eta = formazione.somma_eta
                    salvata.tempo_totale = tempo_totale_fmt
                    salvata.frazioni_json = json.dumps(righe)
                    salvata.creata_il = datetime.utcnow()

            if not formazioni_per_categoria:
                errore = (
                    "Nessuna combinazione di 4 atleti tra quelli inseriti rispetta la composizione "
                    "richiesta (" + (tipo_squadra or "libera") + ") in nessuna categoria."
                )
            else:
                db.session.commit()
                flash(
                    f"{len(formazioni_per_categoria)} formazione/i salvata/e nell'elenco staffette.",
                    "success",
                )

    return render_template(
        "admin/formazione_staffetta.html",
        gara=gara,
        tipo=tipo,
        iscritti=iscritti,
        atleti_convocabili=atleti_convocabili,
        tempo_registrato_min_sec=tempo_registrato_min_sec,
        prove_uniche=prove_uniche,
        anno_stagione=anno_stagione,
        tipo_squadra=tipo_squadra,
        senza_sesso=senza_sesso,
        strategia=strategia,
        valori_form=valori_form,
        risultati=risultati,
        errore=errore,
    )


@admin_bp.route("/gare/<int:gara_id>/staffetta/<path:tipo>/convoca", methods=["POST"])
@login_required
@admin_required
def convoca_atleti_staffetta(gara_id, tipo):
    """Convoca manualmente altri atleti per una staffetta, anche se non si sono
    auto-iscritti: crea l'iscrizione (senza tempo) cosi' compaiono tra i candidati."""
    gara = Gara.query.get_or_404(gara_id)
    if tipo not in gara.lista_tipologie or "staffetta" not in tipo.lower():
        abort(404)

    atleta_ids = request.form.getlist("atleta_ids")
    if not atleta_ids:
        flash("Seleziona almeno un atleta da convocare.", "warning")
        return redirect(url_for("admin.formazione_staffetta", gara_id=gara.id, tipo=tipo))

    gia_iscritti = {
        i.atleta_id for i in gara.iscrizioni if i.stile == tipo
    }
    convocati = 0
    for atleta_id in atleta_ids:
        atleta_id = int(atleta_id)
        if atleta_id in gia_iscritti:
            continue
        db.session.add(IscrizioneGara(atleta_id=atleta_id, gara_id=gara.id, stile=tipo))
        convocati += 1

    db.session.commit()
    flash(f"{convocati} atleta/i convocato/i per \"{tipo}\".", "success")
    return redirect(url_for("admin.formazione_staffetta", gara_id=gara.id, tipo=tipo))


@admin_bp.route("/staffette")
@login_required
@admin_required
def elenco_formazioni_staffetta():
    formazioni = (
        FormazioneStaffetta.query.join(Gara)
        .order_by(Gara.data.desc(), FormazioneStaffetta.tipo, FormazioneStaffetta.categoria)
        .all()
    )
    gara_id_provenienza = request.args.get("gara_id", type=int)
    gara_provenienza = Gara.query.get(gara_id_provenienza) if gara_id_provenienza else None
    return render_template(
        "admin/elenco_formazioni_staffetta.html", formazioni=formazioni, gara_provenienza=gara_provenienza
    )


@admin_bp.route("/staffette/<int:formazione_id>/ordine", methods=["GET", "POST"])
@login_required
@admin_required
def ordina_formazione_staffetta(formazione_id):
    formazione = FormazioneStaffetta.query.get_or_404(formazione_id)
    frazioni = formazione.frazioni

    if request.method == "POST":
        posizioni = [request.form.get(f"posizione_{i}", type=int) for i in range(len(frazioni))]
        if None in posizioni or sorted(posizioni) != list(range(1, len(frazioni) + 1)):
            flash("Ordine non valido: assegna a ciascun atleta una posizione diversa da 1 a 4.", "danger")
            return redirect(url_for("admin.ordina_formazione_staffetta", formazione_id=formazione.id))

        riordinate = [fr for _, fr in sorted(zip(posizioni, frazioni), key=lambda x: x[0])]
        formazione.frazioni_json = json.dumps(riordinate)
        db.session.commit()
        flash("Ordine di partenza aggiornato.", "success")
        return redirect(url_for("admin.elenco_formazioni_staffetta", gara_id=formazione.gara_id))

    return render_template(
        "admin/ordina_formazione_staffetta.html", formazione=formazione, frazioni=frazioni
    )


@admin_bp.route("/staffette/elimina", methods=["POST"])
@login_required
@admin_required
def elimina_formazioni_staffetta():
    ids = request.form.getlist("formazione_ids")
    next_url = request.form.get("next") or url_for("admin.elenco_formazioni_staffetta")
    if not ids:
        flash("Nessuna formazione selezionata.", "warning")
        return redirect(next_url)

    eliminate = FormazioneStaffetta.query.filter(FormazioneStaffetta.id.in_(ids)).delete(
        synchronize_session=False
    )
    db.session.commit()
    flash(f"{eliminate} formazione/i eliminata/e.", "success")
    return redirect(next_url)


@admin_bp.route("/staffette/elimina-tutte", methods=["POST"])
@login_required
@admin_required
def elimina_tutte_formazioni_staffetta():
    next_url = request.form.get("next") or url_for("admin.elenco_formazioni_staffetta")
    eliminate = FormazioneStaffetta.query.delete()
    db.session.commit()
    flash(f"{eliminate} formazione/i eliminata/e.", "success")
    return redirect(next_url)


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


@admin_bp.route("/gare/<int:gara_id>/quota/<int:atleta_id>/annulla", methods=["POST"])
@login_required
@admin_required
def annulla_quota_gara(gara_id, atleta_id):
    gara = Gara.query.get_or_404(gara_id)
    quota = QuotaTorneo.query.filter_by(atleta_id=atleta_id, gara_id=gara.id).first_or_404()

    if quota.movimento_id:
        movimento = MovimentoContabile.query.get(quota.movimento_id)
        if movimento:
            db.session.delete(movimento)

    db.session.delete(quota)
    db.session.commit()
    flash("Quota gara annullata: il movimento contabile è stato rimosso.", "success")
    return redirect(url_for("admin.dettaglio_gara", gara_id=gara.id))


@admin_bp.route("/gare/<int:gara_id>/quota/conferma-tutte", methods=["POST"])
@login_required
@admin_required
def conferma_tutte_quote(gara_id):
    gara = Gara.query.get_or_404(gara_id)

    scelte_per_atleta = gara.iscrizioni_per_atleta()
    quote_esistenti = {
        q.atleta_id: q for q in QuotaTorneo.query.filter_by(gara_id=gara.id).all()
    }

    contatore = 0
    for atleta, iscrizioni in scelte_per_atleta.items():
        quota = quote_esistenti.get(atleta.id)
        if quota and quota.movimento_id:
            continue  # già addebitata, non toccarla

        importo = gara.calcola_quota(iscrizioni)

        if not quota:
            quota = QuotaTorneo(atleta_id=atleta.id, gara_id=gara.id)
            db.session.add(quota)

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
        contatore += 1

    db.session.commit()
    if contatore:
        flash(f"{contatore} quota/e addebitata/e in base alle gare scelte da ciascun atleta.", "success")
    else:
        flash("Nessuna quota da addebitare: tutti gli atleti hanno già una quota confermata.", "info")
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

        if not tipologie:
            flash("Seleziona almeno una tipologia di gara per poter salvare il torneo.", "danger")
            return redirect(url_for("admin.modifica_gara", gara_id=gara.id))

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


@admin_bp.route("/gare/<int:gara_id>/elimina", methods=["POST"])
@login_required
@admin_required
def elimina_gara(gara_id):
    gara = Gara.query.get_or_404(gara_id)

    _elimina_file("programmi_gare", gara.programma_gare_file)
    QuotaTorneo.query.filter_by(gara_id=gara.id).delete()

    nome = gara.nome
    db.session.delete(gara)
    db.session.commit()
    flash(f"Torneo {nome} eliminato.", "success")
    return redirect(url_for("admin.lista_gare"))


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
    q = request.args.get("q", "").strip()
    query = MovimentoContabile.query.join(User, MovimentoContabile.atleta_id == User.id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (MovimentoContabile.causale.ilike(like))
            | (User.nome.ilike(like))
            | (User.cognome.ilike(like))
        )
    movimenti = query.order_by(MovimentoContabile.data).all()
    return render_template("admin/lista_movimenti.html", movimenti=movimenti, q=q)


@admin_bp.route("/movimenti/esporta")
@login_required
@admin_required
def esporta_movimenti():
    movimenti = MovimentoContabile.query.order_by(MovimentoContabile.data).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Data", "Atleta", "Causale", "Importo (€)"])
    for m in movimenti:
        writer.writerow([
            m.data.strftime("%d/%m/%Y"),
            m.atleta.nome_completo,
            m.causale,
            f"{m.importo:.2f}",
        ])

    resp = Response("\N{ZERO WIDTH NO-BREAK SPACE}" + output.getvalue(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=movimenti.csv"
    return resp


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
    q = request.args.get("q", "").strip()
    query = Messaggio.query
    if q:
        like = f"%{q}%"
        query = query.filter(Messaggio.testo.ilike(like))
    messaggi = query.order_by(Messaggio.data.desc()).all()
    return render_template("admin/lista_messaggi.html", messaggi=messaggi, q=q)


@admin_bp.route("/messaggi/<int:messaggio_id>/elimina", methods=["POST"])
@login_required
@admin_required
def elimina_messaggio(messaggio_id):
    messaggio = Messaggio.query.get_or_404(messaggio_id)
    db.session.delete(messaggio)
    db.session.commit()
    flash("Messaggio eliminato.", "success")
    return redirect(url_for("admin.lista_messaggi"))


@admin_bp.route("/record")
@login_required
@admin_required
def lista_record():
    sesso = request.args.get("sesso", "M")
    if sesso not in ("M", "F"):
        sesso = "M"
    vasca = 25
    records = RecordSocietario.query.filter_by(sesso=sesso, vasca=vasca).all()
    griglia = griglia_record(records)
    return render_template("admin/record.html", griglia=griglia, sesso=sesso, vasca=vasca)


@admin_bp.route("/record/<sesso>/<int:vasca>/<stile>/<int:distanza>/<categoria>/modifica", methods=["GET", "POST"])
@login_required
@admin_required
def modifica_record(sesso, vasca, stile, distanza, categoria):
    if sesso not in ("M", "F") or stile not in STILI_CODICI or categoria not in CATEGORIE_RECORD:
        abort(404)

    record = RecordSocietario.query.filter_by(
        sesso=sesso, vasca=vasca, stile=stile, distanza=distanza, categoria=categoria
    ).first()

    if request.method == "POST":
        tempo = (request.form.get("tempo") or "").strip()
        nome = (request.form.get("nome") or "").strip()
        data_valore = _parsa_data(request.form.get("data"))

        if not tempo or not nome:
            flash("Inserisci sia il tempo che il nome per salvare il record.", "danger")
            return redirect(url_for(
                "admin.modifica_record", sesso=sesso, vasca=vasca, stile=stile,
                distanza=distanza, categoria=categoria,
            ))

        if record:
            record.tempo = tempo
            record.nome = nome
            record.data = data_valore
        else:
            db.session.add(RecordSocietario(
                sesso=sesso, vasca=vasca, stile=stile, distanza=distanza, categoria=categoria,
                tempo=tempo, nome=nome, data=data_valore,
            ))
        db.session.commit()
        flash("Record salvato.", "success")
        return redirect(url_for("admin.lista_record", sesso=sesso))

    return render_template(
        "admin/modifica_record.html", record=record, sesso=sesso, vasca=vasca,
        stile=stile, stile_nome=STILI_NOMI[stile], distanza=distanza, categoria=categoria,
    )


@admin_bp.route("/record/<sesso>/<int:vasca>/<stile>/<int:distanza>/<categoria>/elimina", methods=["POST"])
@login_required
@admin_required
def elimina_record(sesso, vasca, stile, distanza, categoria):
    record = RecordSocietario.query.filter_by(
        sesso=sesso, vasca=vasca, stile=stile, distanza=distanza, categoria=categoria
    ).first_or_404()
    db.session.delete(record)
    db.session.commit()
    flash("Record eliminato.", "success")
    return redirect(url_for("admin.lista_record", sesso=sesso))
