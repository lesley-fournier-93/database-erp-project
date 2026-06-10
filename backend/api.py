"""
Haupt-Einstiegspunkt des ERP-Backends.
Starten mit: uvicorn backend.api:app --reload
Swagger UI:  http://localhost:8000/docs
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

from backend.logger import logging_einrichten
from backend.database import verbindung_pruefen
from backend.config import settings
from backend.routers import stammdaten, einkauf, verkauf, reporting, export

logging_einrichten()
logger = logging.getLogger("erp.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Laeuft beim Start und beim Beenden des Servers."""
    if verbindung_pruefen():
        logger.info("ERP gestartet. Datenbankverbindung OK.")
    else:
        logger.critical("Datenbankverbindung fehlgeschlagen! Server laeuft ohne DB.")
    yield
    logger.info("ERP wird beendet.")


app = FastAPI(
    title="Enders Office & IT GmbH - ERP API",
    description="REST-API fuer das ERP-System. Swagger UI fuer interaktive Tests.",
    version="1.0.0",
    lifespan=lifespan,
)


# CORS: erlaubt Streamlit (Port 8501) auf das Backend (Port 8000) zuzugreifen.
# In Produktion: allow_origins auf konkrete URLs einschraenken.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ist_entwicklung else [settings.api_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    """Loggt jeden Request mit Methode, Pfad, Statuscode und Dauer."""
    start = time.perf_counter()
    response = await call_next(request)
    dauer_ms = (time.perf_counter() - start) * 1000
    logger.info(
        f"{request.method} {request.url.path} -> "
        f"{response.status_code} ({dauer_ms:.1f}ms)"
    )
    response.headers["X-Process-Time"] = f"{dauer_ms:.1f}ms"
    return response


# Router einbinden:
app.include_router(stammdaten.router, prefix="/stammdaten", tags=["Stammdaten"])
app.include_router(einkauf.router,    prefix="/einkauf",    tags=["Einkauf"])
app.include_router(verkauf.router,    prefix="/verkauf",    tags=["Verkauf"])
app.include_router(reporting.router,  prefix="/reporting",  tags=["Reporting"])
app.include_router(export.router,     prefix="/export",     tags=["Export"])


@app.get("/", tags=["System"])
def root():
    return {
        "status":    "ERP laeuft",
        "version":   "1.0.0",
        "umgebung":  settings.klinik_env,
        "docs":      "/docs",
    }


@app.get("/health", tags=["System"])
def health():
    """Gesundheitscheck fuer Monitoring und Startpruefung."""
    db_ok = verbindung_pruefen()
    return {
        "status":     "healthy" if db_ok else "degraded",
        "datenbank":  "ok" if db_ok else "nicht erreichbar",
        "umgebung":   settings.klinik_env,
    }
