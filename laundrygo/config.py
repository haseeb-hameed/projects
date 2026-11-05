import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "laundrygo-ktu-mca-mini-project-2026")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    # Default: SQLite (works immediately). For MySQL set DATABASE_URL, e.g.
    # mysql+pymysql://root:password@localhost/laundrygo
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "laundrygo.db"),
    )
