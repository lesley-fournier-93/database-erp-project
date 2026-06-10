"""
Zentrales Logging-Setup.
Einmalig aufrufen: logging_einrichten()
Danach in jedem Modul: logger = logging.getLogger(__name__)
"""
import logging
import sys
from pathlib import Path
from backend.config import settings


def logging_einrichten():
    """Richtet Logging fuer die gesamte Anwendung ein."""
    log_pfad = Path("logs/erp.log")
    log_pfad.parent.mkdir(exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s | %(name)-35s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Konsole: INFO und hoeher
    konsole = logging.StreamHandler(sys.stdout)
    konsole.setLevel(logging.INFO)
    konsole.setFormatter(fmt)

    # Datei: DEBUG und hoeher
    datei = logging.FileHandler(log_pfad, encoding="utf-8")
    datei.setLevel(logging.DEBUG)
    datei.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(konsole)
    root.addHandler(datei)

    # Uvicorn-Logs nicht doppelt ausgeben:
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").propagate = False

    logging.getLogger("erp").info(
        f"Logging eingerichtet. Umgebung: {settings.klinik_env}"
    )
