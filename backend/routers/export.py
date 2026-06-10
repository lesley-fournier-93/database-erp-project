"""
Export-Router: Daten als Dateien herunterladen.
JSON, XML und CSV fuer externe Systeme.
"""
import json
import csv
import io
import decimal
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import date, datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import psycopg2.extras
from backend.database import verbinden

router = APIRouter()
RDC    = psycopg2.extras.RealDictCursor


def json_serial(obj):
    """Wandelt Typen die json.dumps nicht kennt in serialisierbare Werte."""
    if isinstance(obj, (date, datetime)): return obj.isoformat()
    if isinstance(obj, decimal.Decimal):  return float(obj)
    raise TypeError(f"Nicht serialisierbar: {type(obj)}")


@router.get("/personen.json", summary="Personenstammdaten als JSON")
def personen_json():
    """Exportiert alle aktiven Personen als JSON-Datei."""
    with verbinden() as conn:
        with conn.cursor(cursor_factory=RDC) as cur:
            cur.execute("""
                SELECT p.id, p.typ, p.kundennummer, p.lieferantennummer,
                       p.firma, p.vorname, p.nachname, p.email, p.telefon,
                       z.bezeichnung AS zahlungsbedingung
                FROM stammdaten.personen p
                LEFT JOIN stammdaten.zahlungsbedingungen z
                    ON p.zahlungsbedingung_id = z.id
                WHERE p.aktiv = TRUE
                ORDER BY COALESCE(p.firma, p.nachname);
            """)
            personen = [dict(z) for z in cur.fetchall()]

    daten = {
        "exportiert_am": datetime.now().isoformat(),
        "version":       "1.0",
        "anzahl":        len(personen),
        "personen":      personen,
    }
    inhalt    = json.dumps(daten, default=json_serial, ensure_ascii=False, indent=2)
    dateiname = f"personen_{date.today()}.json"
    return Response(
        content=inhalt,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{dateiname}"'},
    )


@router.get("/artikel.csv", summary="Artikelstammdaten als CSV")
def artikel_csv():
    """Exportiert alle aktiven Artikel als CSV (Semikolon, UTF-8 BOM fuer Excel)."""
    with verbinden() as conn:
        with conn.cursor(cursor_factory=RDC) as cur:
            cur.execute("""
                SELECT a.artikelnummer, a.bezeichnung,
                       g.bezeichnung AS gruppe,
                       a.einheit, a.vk_preis::float, a.ek_preis::float,
                       a.mwst_satz::float, a.lagerbestand, a.mindestbestand,
                       (a.lagerbestand <= a.mindestbestand) AS nachbestellung
                FROM stammdaten.artikel a
                LEFT JOIN stammdaten.artikelgruppen g ON a.artikelgruppe_id = g.id
                WHERE a.aktiv = TRUE
                ORDER BY a.artikelnummer;
            """)
            zeilen = [dict(z) for z in cur.fetchall()]

    if not zeilen:
        raise HTTPException(404, detail="Keine Artikel gefunden.")

    ausgabe = io.StringIO()
    writer  = csv.DictWriter(
        ausgabe,
        fieldnames=list(zeilen[0].keys()),
        delimiter=";",
        quoting=csv.QUOTE_MINIMAL,
    )
    writer.writeheader()
    writer.writerows(zeilen)

    dateiname = f"artikel_{date.today()}.csv"
    return Response(
        content=ausgabe.getvalue().encode("utf-8-sig"),  # BOM fuer Excel
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{dateiname}"'},
    )


@router.get("/rechnung/{beleg_id}.xml", summary="Einzelne Rechnung als XML")
def rechnung_xml(beleg_id: int):
    """Exportiert eine einzelne Rechnung als XML fuer Buchhaltungssoftware."""
    with verbinden() as conn:
        with conn.cursor(cursor_factory=RDC) as cur:
            cur.execute("""
                SELECT b.id, b.belegnummer, b.belegart, b.beleg_datum,
                       b.status,
                       b.nettobetrag::float, b.mwst_betrag::float,
                       b.bruttobetrag::float,
                       COALESCE(p.firma,
                           p.vorname || ' ' || p.nachname) AS kunde_name,
                       p.email AS kunde_email
                FROM verkauf.belege b
                JOIN stammdaten.personen p ON b.kunde_id = p.id
                WHERE b.id = %s AND b.belegart = 'REC';
            """, (beleg_id,))
            beleg = cur.fetchone()
            if beleg is None:
                raise HTTPException(404, detail=f"Rechnung #{beleg_id} nicht gefunden.")
            beleg = dict(beleg)

            cur.execute("""
                SELECT position, bezeichnung, menge::float, einheit,
                       einzelpreis::float, rabatt_prozent::float,
                       mwst_satz::float, nettobetrag::float
                FROM verkauf.positionen
                WHERE beleg_id = %s ORDER BY position;
            """, (beleg_id,))
            positionen = [dict(z) for z in cur.fetchall()]

    wurzel = ET.Element("Rechnung")
    wurzel.set("xmlns", "urn:enders-erp:rechnung:1.0")
    wurzel.set("version", "1.0")
    for feld in ["belegnummer", "belegart", "beleg_datum", "status"]:
        ET.SubElement(wurzel, feld).text = str(beleg.get(feld) or "")
    betraege = ET.SubElement(wurzel, "Betraege")
    betraege.set("waehrung", "EUR")
    ET.SubElement(betraege, "netto").text  = f"{beleg['nettobetrag']:.2f}"
    ET.SubElement(betraege, "mwst").text   = f"{beleg['mwst_betrag']:.2f}"
    ET.SubElement(betraege, "brutto").text = f"{beleg['bruttobetrag']:.2f}"
    kunde_elem = ET.SubElement(wurzel, "Kunde")
    ET.SubElement(kunde_elem, "name").text  = beleg.get("kunde_name", "")
    ET.SubElement(kunde_elem, "email").text = beleg.get("kunde_email", "")
    pos_container = ET.SubElement(wurzel, "Positionen")
    for pos in positionen:
        pe = ET.SubElement(pos_container, "Position")
        pe.set("nr", str(pos["position"]))
        ET.SubElement(pe, "bezeichnung").text = pos["bezeichnung"]
        ET.SubElement(pe, "menge").text       = str(pos["menge"])
        ET.SubElement(pe, "einzelpreis").text = f"{pos['einzelpreis']:.4f}"
        ET.SubElement(pe, "nettobetrag").text = f"{pos['nettobetrag']:.2f}"

    roh = ET.tostring(wurzel, encoding="unicode")
    xml = minidom.parseString(roh).toprettyxml(indent="  ")
    dateiname = f"{beleg['belegnummer']}.xml"
    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{dateiname}"'},
    )


@router.get("/bestellungen.json", summary="Offene Bestellungen als JSON")
def bestellungen_json():
    """Exportiert alle offenen Bestellungen mit Positionen."""
    with verbinden() as conn:
        with conn.cursor(cursor_factory=RDC) as cur:
            cur.execute("""
                SELECT b.id, b.belegnummer, b.beleg_datum, b.status,
                       b.nettobetrag::float, b.bruttobetrag::float,
                       COALESCE(p.firma,
                           p.vorname || ' ' || p.nachname) AS lieferant
                FROM einkauf.belege b
                JOIN stammdaten.personen p ON b.lieferant_id = p.id
                WHERE b.belegart = 'BES' AND b.status = 'offen'
                ORDER BY b.beleg_datum;
            """)
            belege = [dict(z) for z in cur.fetchall()]
            for b in belege:
                cur.execute("""
                    SELECT position, bezeichnung, menge::float,
                           einheit, einzelpreis::float, nettobetrag::float
                    FROM einkauf.positionen
                    WHERE beleg_id = %s ORDER BY position;
                """, (b["id"],))
                b["positionen"] = [dict(z) for z in cur.fetchall()]

    daten = {
        "exportiert_am":      datetime.now().isoformat(),
        "anzahl":             len(belege),
        "offene_bestellungen": belege,
    }
    inhalt    = json.dumps(daten, default=json_serial, ensure_ascii=False, indent=2)
    dateiname = f"bestellungen_{date.today()}.json"
    return Response(
        content=inhalt,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{dateiname}"'},
    )
