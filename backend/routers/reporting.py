"""
Reporting-Router: analytische Abfragen fuer das Dashboard.
Alle Abfragen nutzen CTEs und Window Functions direkt in SQL.
"""
from fastapi import APIRouter, Query
import psycopg2.extras
from backend.database import verbinden

router = APIRouter()
RDC    = psycopg2.extras.RealDictCursor


@router.get("/umsatz/monatlich")
def umsatz_monatlich(
    monate: int = Query(12, ge=1, le=60, description="Anzahl Monate zurueck"),
):
    """Monatsumsatz der letzten N Monate mit Wachstum zum Vormonat."""
    with verbinden() as conn:
        with conn.cursor(cursor_factory=RDC) as cur:
            cur.execute("""
                WITH monatsumsatz AS (
                    SELECT
                        TO_CHAR(beleg_datum, 'YYYY-MM') AS monat,
                        SUM(bruttobetrag)::float         AS umsatz
                    FROM verkauf.belege
                    WHERE belegart = 'REC'
                      AND beleg_datum >= CURRENT_DATE - (%s || ' months')::interval
                    GROUP BY TO_CHAR(beleg_datum, 'YYYY-MM')
                )
                SELECT
                    monat, umsatz,
                    LAG(umsatz) OVER (ORDER BY monat)    AS vormonat,
                    ROUND(
                        ((umsatz - LAG(umsatz) OVER (ORDER BY monat))
                        / NULLIF(LAG(umsatz) OVER (ORDER BY monat), 0)
                        * 100)::numeric, 1
                    )                                    AS wachstum_proz,
                    SUM(umsatz) OVER (ORDER BY monat)   AS kumuliert
                FROM monatsumsatz
                ORDER BY monat;
            """, (monate,))
            return cur.fetchall()


@router.get("/kunden/top")
def kunden_top(limit: int = Query(10, ge=1, le=50)):
    """Top-Kunden nach Umsatz mit Segment (A/B/C/D)."""
    with verbinden() as conn:
        with conn.cursor(cursor_factory=RDC) as cur:
            cur.execute("""
                WITH umsatz AS (
                    SELECT kunde_id, SUM(bruttobetrag)::float AS umsatz
                    FROM verkauf.belege WHERE belegart = 'REC'
                    GROUP BY kunde_id
                )
                SELECT
                    COALESCE(p.firma,
                        p.vorname || ' ' || p.nachname)  AS kunde,
                    p.kundennummer,
                    u.umsatz,
                    CASE
                        WHEN u.umsatz >= 10000 THEN 'A'
                        WHEN u.umsatz >=  3000 THEN 'B'
                        WHEN u.umsatz >=   500 THEN 'C'
                        ELSE 'D'
                    END  AS segment,
                    RANK() OVER (ORDER BY u.umsatz DESC) AS rang
                FROM umsatz u
                JOIN stammdaten.personen p ON p.id = u.kunde_id
                ORDER BY u.umsatz DESC
                LIMIT %s;
            """, (limit,))
            return cur.fetchall()


@router.get("/artikel/topverkauf")
def artikel_topverkauf(limit: int = Query(10, ge=1, le=50)):
    """Meist verkaufte Artikel nach Umsatz."""
    with verbinden() as conn:
        with conn.cursor(cursor_factory=RDC) as cur:
            cur.execute("""
                SELECT
                    a.artikelnummer,
                    a.bezeichnung                       AS artikel,
                    g.bezeichnung                       AS gruppe,
                    SUM(vp.menge)::float                AS menge_gesamt,
                    SUM(vp.nettobetrag)::float          AS umsatz_netto,
                    RANK() OVER
                        (ORDER BY SUM(vp.nettobetrag) DESC) AS rang
                FROM verkauf.positionen         vp
                JOIN stammdaten.artikel          a  ON vp.artikel_id = a.id
                JOIN stammdaten.artikelgruppen   g  ON a.artikelgruppe_id = g.id
                JOIN verkauf.belege              vb ON vp.beleg_id = vb.id
                WHERE vb.belegart IN ('REC', 'AUF')
                GROUP BY a.id, a.artikelnummer, a.bezeichnung, g.bezeichnung
                ORDER BY umsatz_netto DESC
                LIMIT %s;
            """, (limit,))
            return cur.fetchall()


@router.get("/lager/warnung")
def lager_warnung():
    """Artikel unter Mindestbestand, sortiert nach Dringlichkeit."""
    with verbinden() as conn:
        with conn.cursor(cursor_factory=RDC) as cur:
            cur.execute("""
                SELECT
                    a.artikelnummer,
                    a.bezeichnung,
                    g.bezeichnung                         AS gruppe,
                    a.lagerbestand,
                    a.mindestbestand,
                    a.mindestbestand - a.lagerbestand     AS fehlmenge,
                    ROUND((a.mindestbestand - a.lagerbestand)
                          * a.ek_preis::numeric, 2)       AS bestellwert_eur,
                    CASE
                        WHEN a.lagerbestand = 0
                            THEN 'KRITISCH'
                        WHEN a.lagerbestand < a.mindestbestand / 2
                            THEN 'HOCH'
                        ELSE 'NORMAL'
                    END AS dringlichkeit
                FROM stammdaten.artikel       a
                JOIN stammdaten.artikelgruppen g ON a.artikelgruppe_id = g.id
                WHERE a.aktiv = TRUE
                  AND a.lagerbestand <= a.mindestbestand
                  AND a.mindestbestand > 0
                ORDER BY fehlmenge DESC;
            """)
            return cur.fetchall()


@router.get("/lieferanten/volumen")
def lieferanten_volumen():
    """Einkaufsvolumen pro Lieferant."""
    with verbinden() as conn:
        with conn.cursor(cursor_factory=RDC) as cur:
            cur.execute("""
                SELECT
                    COALESCE(p.firma,
                        p.vorname || ' ' || p.nachname)  AS lieferant,
                    p.lieferantennummer,
                    COUNT(b.id)                           AS bestellungen,
                    SUM(b.bruttobetrag)::float            AS gesamtvolumen,
                    ROUND(
                        (SUM(b.bruttobetrag) /
                        SUM(SUM(b.bruttobetrag)) OVER () * 100)::numeric, 1
                    )                                     AS anteil_proz
                FROM einkauf.belege b
                JOIN stammdaten.personen p ON b.lieferant_id = p.id
                WHERE b.belegart = 'BES'
                GROUP BY p.id, p.firma, p.vorname, p.nachname, p.lieferantennummer
                ORDER BY gesamtvolumen DESC;
            """)
            return cur.fetchall()
