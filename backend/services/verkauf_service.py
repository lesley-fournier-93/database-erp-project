"""
Service-Klasse fuer Verkauf (Gruppe C).
Kapselt alle SQL-Operationen fuer Verkaufsbelege und Positionen.
"""
import logging
import psycopg2
import psycopg2.extras
from typing import Optional
from backend.database import verbinden

logger = logging.getLogger(__name__)
RDC    = psycopg2.extras.RealDictCursor

ERLAUBTE_STATUS = {
    "entwurf", "offen", "angenommen", "abgelehnt",
    "teilgeliefert", "abgeschlossen", "storniert",
}


class VerkaufService:

    def belege_laden(
        self,
        belegart: Optional[str] = None,
        status: Optional[str] = None,
        kunde_id: Optional[int] = None,
    ) -> list[dict]:
        """Laedt Verkaufsbelege, optional gefiltert."""
        bedingungen, params = [], []
        if belegart:
            bedingungen.append("b.belegart = %s")
            params.append(belegart)
        if status:
            bedingungen.append("b.status = %s")
            params.append(status)
        if kunde_id:
            bedingungen.append("b.kunde_id = %s")
            params.append(kunde_id)
        where = ("WHERE " + " AND ".join(bedingungen)) if bedingungen else ""

        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute(f"""
                    SELECT
                        b.id, b.belegnummer, b.belegart,
                        b.kunde_id, b.beleg_datum, b.status,
                        b.nettobetrag::float,
                        b.mwst_betrag::float,
                        b.bruttobetrag::float,
                        b.bezahlt_am,
                        COALESCE(p.firma,
                            p.vorname || ' ' || p.nachname) AS kunde_name,
                        p.kundennummer
                    FROM verkauf.belege b
                    LEFT JOIN stammdaten.personen p ON b.kunde_id = p.id
                    {where}
                    ORDER BY b.beleg_datum DESC;
                """, params)
                return [dict(z) for z in cur.fetchall()]

    def beleg_laden(self, beleg_id: int) -> dict:
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute("""
                    SELECT
                        b.id, b.belegnummer, b.belegart,
                        b.kunde_id, b.beleg_datum, b.status,
                        b.nettobetrag::float, b.mwst_betrag::float,
                        b.bruttobetrag::float, b.bezahlt_am,
                        COALESCE(p.firma,
                            p.vorname || ' ' || p.nachname) AS kunde_name
                    FROM verkauf.belege b
                    LEFT JOIN stammdaten.personen p ON b.kunde_id = p.id
                    WHERE b.id = %s;
                """, (beleg_id,))
                b = cur.fetchone()
        if b is None:
            raise KeyError(f"Verkaufsbeleg {beleg_id} nicht gefunden.")
        return dict(b)

    def positionen_laden(self, beleg_id: int) -> list[dict]:
        self.beleg_laden(beleg_id)
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute("""
                    SELECT
                        p.id, p.position, p.artikel_id,
                        p.bezeichnung, p.menge::float, p.einheit,
                        p.einzelpreis::float, p.rabatt_prozent::float,
                        p.mwst_satz::float, p.nettobetrag::float,
                        a.artikelnummer
                    FROM verkauf.positionen p
                    LEFT JOIN stammdaten.artikel a ON p.artikel_id = a.id
                    WHERE p.beleg_id = %s
                    ORDER BY p.position;
                """, (beleg_id,))
                return [dict(z) for z in cur.fetchall()]

    def beleg_anlegen(
        self,
        kunde_id: int,
        belegart: str = "ANG",
        zahlungsbedingung_id: Optional[int] = None,
        notizen: Optional[str] = None,
    ) -> dict:
        """Legt einen neuen Verkaufsbeleg an."""
        from datetime import date
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute("""
                    SELECT COALESCE(
                        MAX(CAST(SPLIT_PART(belegnummer, '-', 3) AS INTEGER)), 0
                    ) + 1 AS naechste
                    FROM verkauf.belege
                    WHERE belegart = %s
                      AND belegnummer ~ '^' || %s || '-[0-9]{4}-[0-9]+$';
                """, (belegart, belegart))
                naechste   = cur.fetchone()["naechste"]
                belegnummer = f"{belegart}-{date.today().year}-{naechste:04d}"

                cur.execute("""
                    INSERT INTO verkauf.belege
                        (belegnummer, belegart, kunde_id, beleg_datum,
                         status, zahlungsbedingung_id)
                    VALUES (%s, %s, %s, CURRENT_DATE, 'offen', %s)
                    RETURNING
                        id, belegnummer, belegart, kunde_id,
                        beleg_datum, status,
                        nettobetrag::float, bruttobetrag::float;
                """, (belegnummer, belegart, kunde_id, zahlungsbedingung_id))
                b = dict(cur.fetchone())
        logger.info(f"Verkaufsbeleg angelegt: {belegnummer}.")
        return b

    def status_setzen(self, beleg_id: int, status: str) -> dict:
        """Setzt den Status eines Verkaufsbelegs."""
        if status not in ERLAUBTE_STATUS:
            raise ValueError(f"Ungültiger Status. Erlaubt: {ERLAUBTE_STATUS}")
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute("""
                    UPDATE verkauf.belege SET status = %s
                    WHERE id = %s
                    RETURNING
                        id, belegnummer, belegart, kunde_id,
                        beleg_datum, status,
                        nettobetrag::float, bruttobetrag::float, bezahlt_am;
                """, (status, beleg_id))
                b = cur.fetchone()
        if b is None:
            raise KeyError(f"Verkaufsbeleg {beleg_id} nicht gefunden.")
        logger.info(f"Verkaufsbeleg {beleg_id} Status -> {status}.")
        return dict(b)

    def offene_rechnungen_laden(self) -> list[dict]:
        """Alle offenen Rechnungen aus der View."""
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute("""
                    SELECT
                        id, belegnummer, beleg_datum,
                        alter_tage::int,
                        kundennummer, kunde,
                        faellig_am,
                        tage_ueberfaellig::int,
                        bruttobetrag::float
                    FROM verkauf.offene_rechnungen
                    ORDER BY tage_ueberfaellig DESC;
                """)
                return [dict(z) for z in cur.fetchall()]
