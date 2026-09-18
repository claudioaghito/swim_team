import json
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nome = db.Column(db.String(64), nullable=False)
    cognome = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120))
    ruolo = db.Column(db.String(20), nullable=False, default="atleta")  # "admin" o "atleta"
    attivo = db.Column(db.Boolean, default=True)
    creato_il = db.Column(db.DateTime, default=datetime.utcnow)

    data_nascita = db.Column(db.Date, nullable=True)
    sesso = db.Column(db.String(1))  # "M" o "F", serve anche per comporre le staffette
    cartellino_file = db.Column(db.String(255))  # nome file immagine tesserino, in UPLOAD_FOLDER/cartellini
    certificato_medico_file = db.Column(db.String(255))  # nome file PDF, in UPLOAD_FOLDER/certificati
    certificato_medico_scadenza = db.Column(db.Date)

    # Relazioni
    presenze = db.relationship("Presenza", backref="atleta", lazy=True, cascade="all, delete-orphan")
    iscrizioni = db.relationship("IscrizioneGara", backref="atleta", lazy=True, cascade="all, delete-orphan")
    movimenti = db.relationship(
        "MovimentoContabile", backref="atleta", lazy=True,
        foreign_keys="MovimentoContabile.atleta_id", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.ruolo == "admin"

    @property
    def nome_completo(self):
        return f"{self.nome} {self.cognome}"

    @property
    def eta(self):
        if not self.data_nascita:
            return None
        oggi = datetime.utcnow().date()
        return oggi.year - self.data_nascita.year - (
            (oggi.month, oggi.day) < (self.data_nascita.month, self.data_nascita.day)
        )

    @property
    def certificato_medico_valido(self):
        """True/False in base alla scadenza impostata dall'admin; None se non impostata
        (nessuna scadenza registrata, es. certificato non ancora caricato)."""
        if not self.certificato_medico_scadenza:
            return None
        return self.certificato_medico_scadenza >= datetime.utcnow().date()

    @property
    def certificato_medico_giorni_alla_scadenza(self):
        """Giorni mancanti alla scadenza (negativo se gia' scaduto); None se non impostata."""
        if not self.certificato_medico_scadenza:
            return None
        return (self.certificato_medico_scadenza - datetime.utcnow().date()).days

    @property
    def certificato_medico_in_scadenza(self):
        """True se il certificato e' ancora valido ma scade entro 30 giorni."""
        giorni = self.certificato_medico_giorni_alla_scadenza
        return giorni is not None and 0 <= giorni <= 30

    def saldo_attuale(self):
        totale = db.session.query(db.func.sum(MovimentoContabile.importo)).filter_by(
            atleta_id=self.id
        ).scalar()
        return totale or 0

    def categoria_master(self, anno_stagione):
        """Categoria Master FIN: eta agonistica = anno di fine stagione - anno di nascita,
        arrotondata per difetto al multiplo di 5 piu' vicino (minimo M20)."""
        if not self.data_nascita:
            return None
        eta_agonistica = anno_stagione - self.data_nascita.year
        if eta_agonistica < 20:
            return None
        fascia = (eta_agonistica // 5) * 5
        return f"M{fascia}"

    def __repr__(self):
        return f"<User {self.username} ({self.ruolo})>"


class Allenamento(db.Model):
    __tablename__ = "allenamenti"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    ora_inizio = db.Column(db.Time, nullable=True)
    ora_fine = db.Column(db.Time, nullable=True)
    gruppo = db.Column(db.String(64))  # es. "Esordienti", "Agonisti"
    sede = db.Column(db.String(120))
    descrizione = db.Column(db.Text)

    presenze = db.relationship("Presenza", backref="allenamento", lazy=True, cascade="all, delete-orphan")
    nascosto_da = db.relationship(
        "AllenamentoNascosto", backref="allenamento", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def passato(self):
        return self.data < datetime.utcnow().date()

    def __repr__(self):
        return f"<Allenamento {self.data} {self.gruppo}>"


class Presenza(db.Model):
    __tablename__ = "presenze"

    id = db.Column(db.Integer, primary_key=True)
    atleta_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    allenamento_id = db.Column(db.Integer, db.ForeignKey("allenamenti.id"), nullable=False)
    presente = db.Column(db.Boolean, default=False)
    note = db.Column(db.String(255))

    __table_args__ = (db.UniqueConstraint("atleta_id", "allenamento_id", name="uq_presenza"),)


class Gara(db.Model):
    __tablename__ = "gare"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    data = db.Column(db.Date, nullable=False)
    luogo = db.Column(db.String(120))
    quota_gara = db.Column(db.Numeric(8, 2), default=0)
    quota_staffetta = db.Column(db.Numeric(8, 2), default=0)
    scadenza_iscrizione = db.Column(db.Date)
    note = db.Column(db.Text)
    tipologie_gara = db.Column(db.Text)  # tipi di gara offerti, separati da virgola (es. "50 SL,100 DO")
    programma_gare_file = db.Column(db.String(255))  # nome file PDF, in UPLOAD_FOLDER/programmi_gare

    iscrizioni = db.relationship("IscrizioneGara", backref="gara", lazy=True, cascade="all, delete-orphan")

    @property
    def lista_tipologie(self):
        if not self.tipologie_gara:
            return []
        return [t.strip() for t in self.tipologie_gara.split(",") if t.strip()]

    @property
    def iscrizioni_aperte(self):
        if not self.scadenza_iscrizione:
            return True
        return datetime.utcnow().date() <= self.scadenza_iscrizione

    @property
    def scadenza_vicina(self):
        """True se le iscrizioni sono ancora aperte ma scadono entro 3 giorni."""
        if not self.scadenza_iscrizione or not self.iscrizioni_aperte:
            return False
        return (self.scadenza_iscrizione - datetime.utcnow().date()).days <= 3

    def iscrizioni_per_atleta(self):
        raggruppate = {}
        for iscrizione in self.iscrizioni:
            raggruppate.setdefault(iscrizione.atleta, []).append(iscrizione)
        return dict(sorted(raggruppate.items(), key=lambda kv: (kv[0].cognome, kv[0].nome)))

    def calcola_quota(self, iscrizioni):
        """Quota gara moltiplicata per il numero di gare scelte; le gare la cui
        descrizione contiene "staffetta" usano la quota_staffetta al posto della quota_gara."""
        quota_gara = float(self.quota_gara or 0)
        quota_staffetta = float(self.quota_staffetta or 0)
        totale = 0.0
        for iscrizione in iscrizioni:
            if iscrizione.stile and "staffetta" in iscrizione.stile.lower():
                totale += quota_staffetta
            else:
                totale += quota_gara
        return totale

    def __repr__(self):
        return f"<Gara {self.nome} {self.data}>"


class IscrizioneGara(db.Model):
    __tablename__ = "iscrizioni_gare"

    id = db.Column(db.Integer, primary_key=True)
    atleta_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    gara_id = db.Column(db.Integer, db.ForeignKey("gare.id"), nullable=False)
    stile = db.Column(db.String(64))  # es. "100 stile libero"
    tempo_ottenuto = db.Column(db.String(20))  # es. "01:02.35" - stringa per semplicità
    confermata = db.Column(db.Boolean, default=False)

    __table_args__ = (db.UniqueConstraint("atleta_id", "gara_id", "stile", name="uq_iscrizione"),)


class MovimentoContabile(db.Model):
    __tablename__ = "movimenti_contabili"

    id = db.Column(db.Integer, primary_key=True)
    atleta_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    data = db.Column(db.Date, default=datetime.utcnow)
    importo = db.Column(db.Numeric(8, 2), nullable=False)  # positivo = credito, negativo = debito
    causale = db.Column(db.String(255), nullable=False)
    registrato_da_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    def __repr__(self):
        return f"<Movimento {self.atleta_id} {self.importo}>"


class QuotaTorneo(db.Model):
    """Quota gara addebitata a un singolo atleta per un torneo: crea/aggiorna un
    MovimentoContabile in negativo quando l'admin la conferma."""
    __tablename__ = "quote_torneo"

    id = db.Column(db.Integer, primary_key=True)
    atleta_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    gara_id = db.Column(db.Integer, db.ForeignKey("gare.id"), nullable=False)
    importo = db.Column(db.Numeric(8, 2))
    movimento_id = db.Column(db.Integer, db.ForeignKey("movimenti_contabili.id"))

    atleta = db.relationship("User", foreign_keys=[atleta_id])
    movimento = db.relationship("MovimentoContabile", foreign_keys=[movimento_id])

    __table_args__ = (db.UniqueConstraint("atleta_id", "gara_id", name="uq_quota_torneo"),)


class Messaggio(db.Model):
    __tablename__ = "messaggi"

    id = db.Column(db.Integer, primary_key=True)
    mittente_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # destinatario_id NULL = comunicazione a tutta la squadra
    destinatario_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    testo = db.Column(db.Text, nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    letto = db.Column(db.Boolean, default=False)

    mittente = db.relationship("User", foreign_keys=[mittente_id])
    destinatario = db.relationship("User", foreign_keys=[destinatario_id])
    nascosto_da = db.relationship(
        "MessaggioNascosto", backref="messaggio", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def is_comunicazione_generale(self):
        return self.destinatario_id is None


class MessaggioNascosto(db.Model):
    """Traccia quali messaggi un atleta ha eliminato dalla propria vista (comunicazioni
    generali o messaggi diretti): non tocca la riga condivisa, quindi non ha effetto
    sul mittente ne' sugli altri destinatari."""
    __tablename__ = "messaggi_nascosti"

    id = db.Column(db.Integer, primary_key=True)
    messaggio_id = db.Column(db.Integer, db.ForeignKey("messaggi.id"), nullable=False)
    atleta_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("messaggio_id", "atleta_id", name="uq_messaggio_nascosto"),
    )


class AllenamentoNascosto(db.Model):
    """Traccia quali allenamenti passati un atleta ha rimosso dal proprio archivio
    personale: non elimina l'allenamento (resta visibile agli altri e all'admin)."""
    __tablename__ = "allenamenti_nascosti"

    id = db.Column(db.Integer, primary_key=True)
    allenamento_id = db.Column(db.Integer, db.ForeignKey("allenamenti.id"), nullable=False)
    atleta_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("allenamento_id", "atleta_id", name="uq_allenamento_nascosto"),
    )


class Configurazione(db.Model):
    """Impostazioni globali dell'app (riga singola), gestite solo dall'amministratore."""
    __tablename__ = "configurazione"

    id = db.Column(db.Integer, primary_key=True)
    anno_stagione = db.Column(db.Integer, nullable=False, default=lambda: datetime.utcnow().year)
    modalita_pagamento = db.Column(db.Text)  # testo libero, uguale per tutti i tornei, visibile agli atleti

    @classmethod
    def ottieni(cls):
        config = cls.query.first()
        if not config:
            config = cls(anno_stagione=datetime.utcnow().year)
            db.session.add(config)
            db.session.commit()
        return config


class RecordSocietario(db.Model):
    """Record sociale di nuoto: un record per combinazione sesso/vasca/stile/distanza/categoria
    (vedi records.py per l'elenco fisso di stili, distanze e categorie ammesse)."""
    __tablename__ = "record_societari"

    id = db.Column(db.Integer, primary_key=True)
    sesso = db.Column(db.String(1), nullable=False)  # "M" o "F"
    vasca = db.Column(db.Integer, nullable=False, default=25)  # metri (25 o 50)
    stile = db.Column(db.String(2), nullable=False)  # SL, DF, DO, RA, MX
    distanza = db.Column(db.Integer, nullable=False)  # metri
    categoria = db.Column(db.String(4), nullable=False)  # es. "M40"
    tempo = db.Column(db.String(20), nullable=False)  # es. 24"51 o 1'55"55, testo libero
    nome = db.Column(db.String(120), nullable=False)
    data = db.Column(db.Date)

    __table_args__ = (
        db.UniqueConstraint("sesso", "vasca", "stile", "distanza", "categoria", name="uq_record_societario"),
    )

    def __repr__(self):
        return f"<RecordSocietario {self.sesso} {self.vasca} {self.stile}{self.distanza} {self.categoria}>"


class FormazioneStaffetta(db.Model):
    """Formazione staffetta calcolata e salvata dall'admin per un torneo/tipologia/categoria."""
    __tablename__ = "formazioni_staffetta"

    id = db.Column(db.Integer, primary_key=True)
    gara_id = db.Column(db.Integer, db.ForeignKey("gare.id"), nullable=False)
    tipo = db.Column(db.String(120), nullable=False)  # es. "STAFFETTA 4X50 SL M/F"
    categoria = db.Column(db.String(10), nullable=False)  # es. "160"
    fascia_eta = db.Column(db.String(20))  # es. "160-199"
    strategia = db.Column(db.String(30), nullable=False)
    somma_eta = db.Column(db.Integer, nullable=False)
    tempo_totale = db.Column(db.String(20), nullable=False)  # es. "01:53.20"
    frazioni_json = db.Column(db.Text, nullable=False)  # lista di {"nome","sesso","prova","tempo"}
    creata_il = db.Column(db.DateTime, default=datetime.utcnow)

    gara = db.relationship("Gara", backref=db.backref("formazioni_staffetta", cascade="all, delete-orphan"))

    __table_args__ = (
        db.UniqueConstraint("gara_id", "tipo", "categoria", name="uq_formazione_staffetta"),
    )

    @property
    def frazioni(self):
        return json.loads(self.frazioni_json)
