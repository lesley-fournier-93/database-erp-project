"""
Router fuer Stammdaten (Gruppe A).
Validiert Eingaben, ruft Service auf, wandelt Fehler in HTTP-Antworten um.
"""
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, model_validator, field_validator
from typing import Optional, List, Literal
from backend.dependencies import get_stammdaten_service

router = APIRouter()


# ---- Pydantic-Modelle ----

class PersonResponse(BaseModel):
    id:                  int
    typ:                 str
    kundennummer:        Optional[str] = None
    lieferantennummer:   Optional[str] = None
    firma:               Optional[str] = None
    vorname:             Optional[str] = None
    nachname:            Optional[str] = None
    email:               str
    telefon:             Optional[str] = None
    aktiv:               bool
    kreditlimit:         Optional[float] = None


class PersonAnlegen(BaseModel):
    typ:       Literal["kunde", "lieferant", "beide"]
    firma:     Optional[str] = None
    vorname:   Optional[str] = None
    nachname:  Optional[str] = None
    email:     str
    telefon:   Optional[str] = None
    kreditlimit: float = 5000.0
    zahlungsbedingung_id: Optional[int] = None

    @field_validator("email")
    @classmethod
    def email_format(cls, v):
        if "@" not in v:
            raise ValueError("Keine gueltige E-Mail-Adresse.")
        return v.lower().strip()

    @model_validator(mode="after")
    def firma_oder_name(self):
        if not self.firma and not (self.vorname and self.nachname):
            raise ValueError("Entweder Firma oder Vorname + Nachname angeben.")
        return self


class PersonAktualisieren(BaseModel):
    firma:     Optional[str]   = None
    vorname:   Optional[str]   = None
    nachname:  Optional[str]   = None
    email:     Optional[str]   = None
    telefon:   Optional[str]   = None
    kreditlimit: Optional[float] = None

    @model_validator(mode="after")
    def mindestens_ein_feld(self):
        felder = [self.firma, self.vorname, self.nachname,
                  self.email, self.telefon, self.kreditlimit]
        if all(v is None for v in felder):
            raise ValueError("Mindestens ein Feld muss angegeben werden.")
        return self


class ArtikelResponse(BaseModel):
    id:              int
    artikelnummer:   str
    bezeichnung:     str
    gruppe:          Optional[str] = None
    einheit:         str
    vk_preis:        float
    ek_preis:        float
    mwst_satz:       float
    lagerbestand:    int
    mindestbestand:  int
    aktiv:           bool
    nachbestellung:  Optional[bool] = None


class ArtikelAktualisieren(BaseModel):
    bezeichnung:    Optional[str]   = None
    vk_preis:       Optional[float] = None
    ek_preis:       Optional[float] = None
    lagerbestand:   Optional[int]   = None
    mindestbestand: Optional[int]   = None

    @model_validator(mode="after")
    def mindestens_ein_feld(self):
        felder = [self.bezeichnung, self.vk_preis, self.ek_preis,
                  self.lagerbestand, self.mindestbestand]
        if all(v is None for v in felder):
            raise ValueError("Mindestens ein Feld muss angegeben werden.")
        return self


# ---- Personen-Endpunkte ----

@router.get("/personen/suche", response_model=List[PersonResponse])
def personen_suchen(
    q: str,
    service=Depends(get_stammdaten_service),
):
    """Volltext-Suche in Firma, Name und E-Mail. Mindestens 2 Zeichen."""
    if len(q.strip()) < 2:
        raise HTTPException(400, detail="Suchbegriff muss mindestens 2 Zeichen haben.")
    return service.personen_suchen(q.strip())


@router.get("/personen/archiv", response_model=List[PersonResponse])
def personen_archiv(service=Depends(get_stammdaten_service)):
    """Alle deaktivierten Personen."""
    return service.personen_laden(nur_aktive=False)


@router.get("/personen", response_model=List[PersonResponse])
def alle_personen(
    typ: Optional[str] = None,
    nur_aktive: bool = True,
    service=Depends(get_stammdaten_service),
):
    """Alle Personen, optional nach Typ gefiltert (kunde/lieferant/beide)."""
    return service.personen_laden(typ=typ, nur_aktive=nur_aktive)


@router.get("/personen/{personen_id}", response_model=PersonResponse)
def person_detail(
    personen_id: int,
    service=Depends(get_stammdaten_service),
):
    try:
        return service.person_laden(personen_id)
    except KeyError as e:
        raise HTTPException(404, detail=str(e))


@router.post("/personen", response_model=PersonResponse, status_code=201)
def person_anlegen(
    daten: PersonAnlegen,
    service=Depends(get_stammdaten_service),
):
    try:
        return service.person_anlegen(
            typ=daten.typ, email=daten.email,
            firma=daten.firma, vorname=daten.vorname,
            nachname=daten.nachname, telefon=daten.telefon,
            kreditlimit=daten.kreditlimit,
            zahlungsbedingung_id=daten.zahlungsbedingung_id,
        )
    except ValueError as e:
        raise HTTPException(409, detail=str(e))


@router.put("/personen/{personen_id}", response_model=PersonResponse)
def person_aktualisieren(
    personen_id: int,
    daten: PersonAktualisieren,
    service=Depends(get_stammdaten_service),
):
    try:
        return service.person_aktualisieren(
            personen_id, daten.model_dump(exclude_none=True)
        )
    except KeyError as e:
        raise HTTPException(404, detail=str(e))


@router.delete("/personen/{personen_id}", status_code=204)
def person_deaktivieren(
    personen_id: int,
    service=Depends(get_stammdaten_service),
):
    try:
        service.person_deaktivieren(personen_id)
    except KeyError as e:
        raise HTTPException(404, detail=str(e))
    return Response(status_code=204)


@router.post("/personen/{personen_id}/reaktivieren", response_model=PersonResponse)
def person_reaktivieren(
    personen_id: int,
    service=Depends(get_stammdaten_service),
):
    try:
        return service.person_reaktivieren(personen_id)
    except KeyError as e:
        raise HTTPException(404, detail=str(e))


# ---- Artikel-Endpunkte ----

@router.get("/artikel/nachbestellung", response_model=List[ArtikelResponse])
def artikel_nachbestellung(service=Depends(get_stammdaten_service)):
    """Artikel deren Lagerbestand den Mindestbestand unterschreitet."""
    return service.nachbestellung_laden()


@router.get("/artikel", response_model=List[ArtikelResponse])
def alle_artikel(
    nur_aktive: bool = True,
    service=Depends(get_stammdaten_service),
):
    return service.artikel_laden(nur_aktive=nur_aktive)


@router.get("/artikel/{artikel_id}", response_model=ArtikelResponse)
def artikel_detail(
    artikel_id: int,
    service=Depends(get_stammdaten_service),
):
    try:
        return service.artikel_laden_einzeln(artikel_id)
    except KeyError as e:
        raise HTTPException(404, detail=str(e))


@router.put("/artikel/{artikel_id}", response_model=ArtikelResponse)
def artikel_aktualisieren(
    artikel_id: int,
    daten: ArtikelAktualisieren,
    service=Depends(get_stammdaten_service),
):
    try:
        return service.artikel_aktualisieren(
            artikel_id, daten.model_dump(exclude_none=True)
        )
    except KeyError as e:
        raise HTTPException(404, detail=str(e))
