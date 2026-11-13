import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DEBUG = False
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET = os.getenv("JWT_SECRET")


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or "sqlite:///dev.db"


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///test.db"


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError(
            "DATABASE_URL is required in production but was not set."
        )
    if not Config.JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET is required in production but was not set."
        )


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
