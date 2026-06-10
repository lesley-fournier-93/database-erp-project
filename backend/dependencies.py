"""
Dependency Injection fuer FastAPI.
Service-Instanzen werden einmal angelegt und wiederverwendet.
"""
from functools import lru_cache


@lru_cache(maxsize=1)
def get_stammdaten_service():
    from backend.services.stammdaten_service import StammdatenService
    return StammdatenService()


@lru_cache(maxsize=1)
def get_einkauf_service():
    from backend.services.einkauf_service import EinkaufService
    return EinkaufService()


@lru_cache(maxsize=1)
def get_verkauf_service():
    from backend.services.verkauf_service import VerkaufService
    return VerkaufService()
