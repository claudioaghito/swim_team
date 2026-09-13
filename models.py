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
    cartellino_file = db.Column(db.String(255))  # nome file immagine tesserino, in UPLOAD_FOLDER/cartellini
    certificato_medico_file = db.Column(db.String(255))  # nome file PDF, in UPLOAD_FOLDER/certificati

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

    def saldo_attuale(self):
        totale = db.session.query(db.func.sum(MovimentoContabile.importo)).filter_by(
            atleta_id=self.id
        ).scalar()
        return totale or 0

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

    @property
    def is_comunicazione_generale(self):
        return self.destinatario_id is None
