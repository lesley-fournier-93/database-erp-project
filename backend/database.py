"""
Datenbankverbindung.
Alle Module importieren verbinden() von hier.
"""
import psycopg2
import psycopg2.extras
from backend.config import settings


def verbinden():
    """Oeffnet eine neue Datenbankverbindung und gibt sie zurueck."""
    return psycopg2.connect(**settings.db_verbindung)


def verbindung_pruefen() -> bool:
    """Prueft ob die Datenbank erreichbar ist. True = OK, False = Fehler."""
    try:
        conn = verbinden()
        conn.close()
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Datenbank nicht erreichbar: {e}")
        return False
