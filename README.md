# Enders Office & IT GmbH - ERP

ERP-System entwickelt im Kurs Python-Softwareentwicklung bei Enders Training.

## Gruppenaufteilung

| Gruppe | Modul | Schema | Branch |
|---|---|---|---|
| A | Stammdaten: Personen + Artikel | `stammdaten` | `feature/gruppe-a-stammdaten` |
| B | Einkauf: Bestellungen | `einkauf` | `feature/gruppe-b-einkauf` |
| C | Verkauf: Rechnungen | `verkauf` | `feature/gruppe-c-verkauf` |

## Schnellstart

```bash
# 1. Repository klonen:
git clone https://github.com/DEIN-REPO/klinik-erp.git
cd klinik-erp

# 2. Konfiguration einrichten:
cp .env.example .env.development
# .env.development oeffnen und DB_PASSWORD eintragen

# 3. Pakete installieren:
pip install -r requirements.txt

# 4. Datenbank einrichten (einmalig):
psql -U postgres -f erp_setup.sql

# 5. Backend starten:
uvicorn backend.api:app --reload
# Swagger UI: http://localhost:8000/docs
```

## Git-Workflow

```bash
# Feature-Branch anlegen (jede Gruppe einmal):
git switch -c feature/gruppe-a-stammdaten

# Aenderungen committen:
git add backend/routers/stammdaten.py
git commit -m "feat(stammdaten): GET /personen Endpunkt"

# Branch auf GitHub pushen:
git push origin feature/gruppe-a-stammdaten
```

## Projektstruktur

```
klinik-erp/
├── backend/
│   ├── api.py          <- FastAPI-App, bindet Router ein
│   ├── config.py       <- Konfiguration aus .env
│   ├── database.py     <- verbinden()-Funktion
│   ├── routers/        <- Gruppen-Router (werden per Branch hinzugefuegt)
│   └── services/       <- Service-Klassen (spaeter)
├── frontend/           <- Streamlit (spaeter)
├── tests/              <- pytest (spaeter)
├── erp_setup.sql       <- Datenbankschema + Testdaten
├── .env.example        <- Vorlage (kein Passwort!)
└── requirements.txt
```
