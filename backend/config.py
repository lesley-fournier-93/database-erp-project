"""
Zentrale Konfiguration des ERP-Systems.
Alle Werte kommen aus der .env-Datei.
Kein anderes Modul liest .env direkt - immer nur ueber settings importieren.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal
import os


class Settings(BaseSettings):
    # Datenbankverbindung:
    db_host:     str = "localhost"
    db_port:     int = 5432
    db_name:     str = "erp"
    db_user:     str = "postgres"
    db_password: str = "passwort"

    # Anwendung:
    api_host:    str = "localhost"
    api_port:    int = 8000
    api_url:     str = "http://localhost:8000"

    # Umgebung: development, testing, production
    klinik_env:  Literal["development", "testing", "production"] = "development"

    # Feature-Flags:
    feature_archiv:        bool = True
    feature_wechselkurse:  bool = True
    feature_xml_export:    bool = True

    # Logging:
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('KLINIK_ENV', 'development')}",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def db_verbindung(self) -> dict:
        """Datenbankverbindungsparameter als Dictionary fuer psycopg2."""
        return {
            "host":     self.db_host,
            "port":     self.db_port,
            "dbname":   self.db_name,
            "user":     self.db_user,
            "password": self.db_password,
        }

    @property
    def ist_entwicklung(self) -> bool:
        return self.klinik_env == "development"

    @property
    def ist_test(self) -> bool:
        return self.klinik_env == "testing"


# Singleton: einmal laden, ueberall importieren
settings = Settings()
