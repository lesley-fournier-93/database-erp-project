"""
Router fuer Verkauf (Gruppe C).
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, model_validator
from typing import Optional, List, Literal
from datetime import date
from backend.dependencies import get_verkauf_service

router = APIRouter()

ERLAUBTE_STATUS = {
    "entwurf", "offen", "angenommen", "abgelehnt",
    "teilgeliefert", "abgeschlossen", "storniert",
}


class BelegResponse(BaseModel):
    id:           int
    belegnummer:  str
    belegart:     str
    kunde_id:     int
    beleg_datum:  date
    status:       str
    nettobetrag:  float
    bruttobetrag: float
    bezahlt_am:   Optional[date] = None
    kunde_name:   Optional[str]  = None
    kundennummer: Optional[str]  = None


class OffeneRechnungResponse(BaseModel):
    id:                int
    belegnummer:       str
    beleg_datum:       date
    alter_tage:        int
    kundennummer:      Optional[str] = None
    kunde:             str
    faellig_am:        Optional[date] = None
    tage_ueberfaellig: int
    bruttobetrag:      float


class PositionResponse(BaseModel):
    id:             int
    position:       int
    artikel_id:     Optional[int] = None
    bezeichnung:    str
    menge:          float
    einheit:        str
    einzelpreis:    float
    rabatt_prozent: float
    mwst_satz:      float
    nettobetrag:    float
    artikelnummer:  Optional[str] = None


class BelegAnlegen(BaseModel):
    kunde_id:             int
    belegart:             str = "ANG"
    zahlungsbedingung_id: Optional[int] = None
    notizen:              Optional[str] = None


class StatusAendern(BaseModel):
    status: str

    @model_validator(mode="after")
    def status_gueltig(self):
        if self.status not in ERLAUBTE_STATUS:
            raise ValueError(f"Ungültiger Status. Erlaubt: {ERLAUBTE_STATUS}")
        return self


@router.get("/belege", response_model=List[BelegResponse])
def alle_belege(
    belegart:  Optional[str] = None,
    status:    Optional[str] = None,
    kunde_id:  Optional[int] = None,
    service=Depends(get_verkauf_service),
):
    return service.belege_laden(
        belegart=belegart, status=status, kunde_id=kunde_id
    )


@router.get("/rechnungen/offen", response_model=List[OffeneRechnungResponse])
def offene_rechnungen(service=Depends(get_verkauf_service)):
    """Alle offenen Rechnungen aus der View."""
    return service.offene_rechnungen_laden()


@router.get("/belege/{beleg_id}", response_model=BelegResponse)
def beleg_detail(beleg_id: int, service=Depends(get_verkauf_service)):
    try:
        return service.beleg_laden(beleg_id)
    except KeyError as e:
        raise HTTPException(404, detail=str(e))


@router.get("/belege/{beleg_id}/positionen", response_model=List[PositionResponse])
def beleg_positionen(beleg_id: int, service=Depends(get_verkauf_service)):
    try:
        return service.positionen_laden(beleg_id)
    except KeyError as e:
        raise HTTPException(404, detail=str(e))


@router.post("/belege", response_model=BelegResponse, status_code=201)
def beleg_anlegen(daten: BelegAnlegen, service=Depends(get_verkauf_service)):
    try:
        return service.beleg_anlegen(
            kunde_id=daten.kunde_id,
            belegart=daten.belegart,
            zahlungsbedingung_id=daten.zahlungsbedingung_id,
            notizen=daten.notizen,
        )
    except Exception as e:
        raise HTTPException(400, detail=str(e))


@router.patch("/belege/{beleg_id}/status", response_model=BelegResponse)
def status_setzen(
    beleg_id: int,
    daten: StatusAendern,
    service=Depends(get_verkauf_service),
):
    try:
        return service.status_setzen(beleg_id, daten.status)
    except KeyError as e:
        raise HTTPException(404, detail=str(e))
    except ValueError as e:
        raise HTTPException(422, detail=str(e))
