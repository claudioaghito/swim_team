import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # In produzione, imposta SECRET_KEY come variabile d'ambiente (non lasciarla hardcoded)
    SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-questa-chiave-in-produzione")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'squadra.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "instance", "uploads")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB limite upload
    ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
    ALLOWED_PDF_EXT = {"pdf"}
    ALLOWED_CERTIFICATO_EXT = ALLOWED_PDF_EXT | ALLOWED_IMAGE_EXT
