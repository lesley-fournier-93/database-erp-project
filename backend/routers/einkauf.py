"""
Router fuer Einkauf (Gruppe B).
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, model_validator
from typing import Optional, List
from datetime import date
from backend.dependencies import get_einkauf_service

router = APIRouter()


class BelegResponse(BaseModel):
    id:               int
    belegnummer:      str
    belegart:         str
    lieferant_id:     int
    beleg_datum:      date
    status:           str
    nettobetrag:      float
    bruttobetrag:     float
    bezahlt_am:       Optional[date] = None
    lieferanten_belegnr: Optional[str] = None
    lieferant_name:   Optional[str] = None


class PositionResponse(BaseModel):
    id:             int
    position:       int
    artikel_id:     Optional[int] = None
    bezeichnung:    str
    menge:          float
    einheit:        str
    einzelpreis:    float
    rabatt_prozent: float
    nettobetrag:    float
    artikelnummer:  Optional[str] = None


class BelegAnlegen(BaseModel):
    lieferant_id:        int
    belegart:            str = "BES"
    notizen:             Optional[str] = None
    zahlungsbedingung_id: Optional[int] = None


class StatusAendern(BaseModel):
    status: str

    @model_validator(mode="after")
    def status_gueltig(self):
        erlaubt = {"entwurf", "offen", "teilgeliefert", "abgeschlossen", "storniert"}
        if self.status not in erlaubt:
            raise ValueError(f"Ungültiger Status. Erlaubt: {erlaubt}")
        return self


@router.get("/belege", response_model=List[BelegResponse])
def alle_belege(
    belegart: Optional[str] = None,
    status:   Optional[str] = None,
    lieferant_id: Optional[int] = None,
    service=Depends(get_einkauf_service),
):
    return service.belege_laden(
        belegart=belegart, status=status, lieferant_id=lieferant_id
    )


@router.get("/belege/offen", response_model=List[BelegResponse])
def offene_bestellungen(service=Depends(get_einkauf_service)):
    """Alle offenen Bestellungen."""
    return service.offene_bestellungen_laden()


@router.get("/belege/{beleg_id}", response_model=BelegResponse)
def beleg_detail(beleg_id: int, service=Depends(get_einkauf_service)):
    try:
        return service.beleg_laden(beleg_id)
    except KeyError as e:
        raise HTTPException(404, detail=str(e))


@router.get("/belege/{beleg_id}/positionen", response_model=List[PositionResponse])
def beleg_positionen(beleg_id: int, service=Depends(get_einkauf_service)):
    try:
        return service.positionen_laden(beleg_id)
    except KeyError as e:
        raise HTTPException(404, detail=str(e))


@router.post("/belege", response_model=BelegResponse, status_code=201)
def beleg_anlegen(daten: BelegAnlegen, service=Depends(get_einkauf_service)):
    try:
        return service.beleg_anlegen(
            lieferant_id=daten.lieferant_id,
            belegart=daten.belegart,
            notizen=daten.notizen,
            zahlungsbedingung_id=daten.zahlungsbedingung_id,
        )
    except Exception as e:
        raise HTTPException(400, detail=str(e))


@router.patch("/belege/{beleg_id}/status", response_model=BelegResponse)
def status_setzen(
    beleg_id: int,
    daten: StatusAendern,
    service=Depends(get_einkauf_service),
):
    try:
        return service.status_setzen(beleg_id, daten.status)
    except KeyError as e:
        raise HTTPException(404, detail=str(e))
    except ValueError as e:
        raise HTTPException(422, detail=str(e))
