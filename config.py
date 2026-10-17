import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Carica le variabili da .env (chiavi VAPID, ecc.): "flask run" lo fa gia' in automatico,
# ma questo serve anche quando l'app e' avviata diversamente (es. WSGI su PythonAnywhere).
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    # In produzione, imposta SECRET_KEY come variabile d'ambiente (non lasciarla hardcoded)
    SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-questa-chiave-in-produzione")

    # Chiavi VAPID per le notifiche push (Web Push): generate una volta e salvate in .env
    # (file non versionato). Senza queste chiavi le notifiche push non possono essere inviate.
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
    VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:admin@example.com")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'squadra.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "instance", "uploads")
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200 MB (serve margine per il ripristino di un backup completo)
    ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
    ALLOWED_PDF_EXT = {"pdf"}
    ALLOWED_CERTIFICATO_EXT = ALLOWED_PDF_EXT | ALLOWED_IMAGE_EXT
    ALLOWED_ALLEGATO_EXT = ALLOWED_PDF_EXT | ALLOWED_IMAGE_EXT
