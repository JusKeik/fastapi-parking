import os


class Config:
    SQLALCHEMY_DATABASE_URI = (
        os.getenv(
            "DATABASE_URL",
            (
                "postgresql+psycopg://"
                "skillbox_user:skillbox_password"
                "@localhost:5432/skillbox_db"
            ),
        ),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = (False,)
