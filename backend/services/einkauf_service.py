"""
Service-Klasse fuer Einkauf (Gruppe B).
Kapselt alle SQL-Operationen fuer Einkaufsbelege und Positionen.
"""
import logging
import psycopg2
import psycopg2.extras
from typing import Optional
from backend.database import verbinden

logger = logging.getLogger(__name__)
RDC    = psycopg2.extras.RealDictCursor


class EinkaufService:

    def belege_laden(
        self,
        belegart: Optional[str] = None,
        status: Optional[str] = None,
        lieferant_id: Optional[int] = None,
    ) -> list[dict]:
        """Laedt Einkaufsbelege, optional gefiltert."""
        bedingungen, params = [], []
        if belegart:
            bedingungen.append("b.belegart = %s")
            params.append(belegart)
        if status:
            bedingungen.append("b.status = %s")
            params.append(status)
        if lieferant_id:
            bedingungen.append("b.lieferant_id = %s")
            params.append(lieferant_id)
        where = ("WHERE " + " AND ".join(bedingungen)) if bedingungen else ""

        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute(f"""
                    SELECT
                        b.id, b.belegnummer, b.belegart,
                        b.lieferant_id, b.beleg_datum, b.status,
                        b.nettobetrag::float,
                        b.mwst_betrag::float,
                        b.bruttobetrag::float,
                        b.bezahlt_am,
                        b.lieferanten_belegnr,
                        COALESCE(p.firma,
                            p.vorname || ' ' || p.nachname) AS lieferant_name
                    FROM einkauf.belege b
                    LEFT JOIN stammdaten.personen p ON b.lieferant_id = p.id
                    {where}
                    ORDER BY b.beleg_datum DESC;
                """, params)
                return [dict(z) for z in cur.fetchall()]

    def beleg_laden(self, beleg_id: int) -> dict:
        """Laedt einen einzelnen Einkaufsbeleg."""
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute("""
                    SELECT
                        b.id, b.belegnummer, b.belegart,
                        b.lieferant_id, b.beleg_datum, b.status,
                        b.nettobetrag::float, b.mwst_betrag::float,
                        b.bruttobetrag::float, b.bezahlt_am,
                        b.lieferanten_belegnr,
                        COALESCE(p.firma,
                            p.vorname || ' ' || p.nachname) AS lieferant_name
                    FROM einkauf.belege b
                    LEFT JOIN stammdaten.personen p ON b.lieferant_id = p.id
                    WHERE b.id = %s;
                """, (beleg_id,))
                b = cur.fetchone()
        if b is None:
            raise KeyError(f"Einkaufsbeleg {beleg_id} nicht gefunden.")
        return dict(b)

    def positionen_laden(self, beleg_id: int) -> list[dict]:
        """Laedt alle Positionen eines Einkaufsbelegs."""
        self.beleg_laden(beleg_id)  # 404-Check
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute("""
                    SELECT
                        p.id, p.position, p.artikel_id,
                        p.bezeichnung, p.menge::float, p.einheit,
                        p.einzelpreis::float, p.rabatt_prozent::float,
                        p.nettobetrag::float,
                        a.artikelnummer
                    FROM einkauf.positionen p
                    LEFT JOIN stammdaten.artikel a ON p.artikel_id = a.id
                    WHERE p.beleg_id = %s
                    ORDER BY p.position;
                """, (beleg_id,))
                return [dict(z) for z in cur.fetchall()]

    def beleg_anlegen(
        self,
        lieferant_id: int,
        belegart: str = "BES",
        notizen: Optional[str] = None,
        zahlungsbedingung_id: Optional[int] = None,
    ) -> dict:
        """Legt einen neuen Einkaufsbeleg an."""
        from datetime import date
        # Naechste Belegnummer:
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute("""
                    SELECT COALESCE(
                        MAX(CAST(SPLIT_PART(belegnummer, '-', 3) AS INTEGER)), 0
                    ) + 1 AS naechste
                    FROM einkauf.belege
                    WHERE belegart = %s
                      AND belegnummer ~ '^' || %s || '-[0-9]{4}-[0-9]+$';
                """, (belegart, belegart))
                naechste   = cur.fetchone()["naechste"]
                belegnummer = f"{belegart}-{date.today().year}-{naechste:04d}"

                cur.execute("""
                    INSERT INTO einkauf.belege
                        (belegnummer, belegart, lieferant_id, beleg_datum,
                         status, zahlungsbedingung_id)
                    VALUES (%s, %s, %s, CURRENT_DATE, 'offen', %s)
                    RETURNING
                        id, belegnummer, belegart, lieferant_id,
                        beleg_datum, status,
                        nettobetrag::float, bruttobetrag::float;
                """, (belegnummer, belegart, lieferant_id, zahlungsbedingung_id))
                b = dict(cur.fetchone())
        logger.info(f"Einkaufsbeleg angelegt: {belegnummer}.")
        return b

    def status_setzen(self, beleg_id: int, status: str) -> dict:
        """Setzt den Status eines Einkaufsbelegs."""
        erlaubt = {"entwurf", "offen", "teilgeliefert", "abgeschlossen", "storniert"}
        if status not in erlaubt:
            raise ValueError(f"Ungültiger Status. Erlaubt: {erlaubt}")
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute("""
                    UPDATE einkauf.belege SET status = %s
                    WHERE id = %s
                    RETURNING
                        id, belegnummer, belegart, lieferant_id,
                        beleg_datum, status,
                        nettobetrag::float, bruttobetrag::float, bezahlt_am;
                """, (status, beleg_id))
                b = cur.fetchone()
        if b is None:
            raise KeyError(f"Einkaufsbeleg {beleg_id} nicht gefunden.")
        logger.info(f"Einkaufsbeleg {beleg_id} Status -> {status}.")
        return dict(b)

    def offene_bestellungen_laden(self) -> list[dict]:
        """Alle offenen Bestellungen sortiert nach Datum."""
        return self.belege_laden(belegart="BES", status="offen")
