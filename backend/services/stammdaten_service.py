"""
Service-Klasse fuer Stammdaten (Gruppe A).
Kapselt alle SQL-Operationen fuer Personen und Artikel.
Der Router kennt kein SQL. Der Service kennt kein FastAPI.
"""
import logging
import psycopg2
import psycopg2.extras
from typing import Optional
from backend.database import verbinden

logger = logging.getLogger(__name__)
RDC    = psycopg2.extras.RealDictCursor


class StammdatenService:

    # ---- Personen ----

    def personen_laden(
        self,
        typ: Optional[str] = None,
        nur_aktive: bool = True,
    ) -> list[dict]:
        """Laedt alle Personen. Optional nach Typ und Aktivitaet filtern."""
        bedingungen, params = ["TRUE"], []
        if nur_aktive:
            bedingungen.append("aktiv = TRUE")
        if typ:
            bedingungen.append("typ = %s")
            params.append(typ)
        where = " AND ".join(bedingungen)

        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute(f"""
                    SELECT
                        id, typ, kundennummer, lieferantennummer,
                        firma, vorname, nachname, email,
                        telefon, aktiv, kreditlimit
                    FROM stammdaten.personen
                    WHERE {where}
                    ORDER BY COALESCE(firma, nachname || ' ' || vorname);
                """, params)
                ergebnis = [dict(z) for z in cur.fetchall()]
        logger.info(f"{len(ergebnis)} Personen geladen (typ={typ!r}, aktiv={nur_aktive}).")
        return ergebnis

    def person_laden(self, personen_id: int) -> dict:
        """Laedt eine einzelne Person. Wirft KeyError wenn nicht gefunden."""
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute("""
                    SELECT
                        id, typ, kundennummer, lieferantennummer,
                        firma, vorname, nachname, email,
                        telefon, aktiv, kreditlimit,
                        zahlungsbedingung_id
                    FROM stammdaten.personen
                    WHERE id = %s;
                """, (personen_id,))
                p = cur.fetchone()
        if p is None:
            raise KeyError(f"Person {personen_id} nicht gefunden.")
        return dict(p)

    def person_anlegen(
        self,
        typ: str,
        email: str,
        firma: Optional[str] = None,
        vorname: Optional[str] = None,
        nachname: Optional[str] = None,
        telefon: Optional[str] = None,
        kreditlimit: float = 5000.0,
        zahlungsbedingung_id: Optional[int] = None,
    ) -> dict:
        """Legt eine neue Person an und vergibt automatisch Kunden-/Lieferantennummer."""
        # Duplikatpruefung:
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute(
                    "SELECT id FROM stammdaten.personen WHERE email = %s;",
                    (email.lower().strip(),)
                )
                if cur.fetchone():
                    raise ValueError(f"E-Mail {email!r} ist bereits vergeben.")

                # Einfuegen:
                cur.execute("""
                    INSERT INTO stammdaten.personen
                        (typ, firma, vorname, nachname, email, telefon,
                         kreditlimit, zahlungsbedingung_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING
                        id, typ, kundennummer, lieferantennummer,
                        firma, vorname, nachname, email,
                        telefon, aktiv, kreditlimit;
                """, (typ, firma, vorname, nachname,
                      email.lower().strip(), telefon,
                      kreditlimit, zahlungsbedingung_id))
                p = dict(cur.fetchone())

        logger.info(f"Person angelegt: ID {p['id']}, {email}, Typ {typ}.")
        return p

    def person_aktualisieren(
        self,
        personen_id: int,
        felder: dict,
    ) -> dict:
        """Aktualisiert einzelne Felder einer Person. felder = geaenderte Werte."""
        self.person_laden(personen_id)  # 404-Check
        if not felder:
            raise ValueError("Mindestens ein Feld muss angegeben werden.")

        set_k = ", ".join(f"{k} = %s" for k in felder)
        werte = list(felder.values()) + [personen_id]

        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute(f"""
                    UPDATE stammdaten.personen
                    SET {set_k}
                    WHERE id = %s
                    RETURNING
                        id, typ, kundennummer, lieferantennummer,
                        firma, vorname, nachname, email,
                        telefon, aktiv, kreditlimit;
                """, werte)
                p = dict(cur.fetchone())

        logger.info(f"Person {personen_id} aktualisiert: {list(felder.keys())}.")
        return p

    def person_deaktivieren(self, personen_id: int) -> None:
        """Setzt aktiv = FALSE (Soft Delete). Daten bleiben erhalten."""
        with verbinden() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE stammdaten.personen
                    SET aktiv = FALSE
                    WHERE id = %s AND aktiv = TRUE
                    RETURNING id;
                """, (personen_id,))
                if cur.fetchone() is None:
                    raise KeyError(
                        f"Person {personen_id} nicht gefunden oder bereits archiviert."
                    )
        logger.info(f"Person {personen_id} deaktiviert.")

    def person_reaktivieren(self, personen_id: int) -> dict:
        """Setzt aktiv = TRUE fuer eine archivierte Person."""
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute("""
                    UPDATE stammdaten.personen
                    SET aktiv = TRUE
                    WHERE id = %s AND aktiv = FALSE
                    RETURNING
                        id, typ, firma, vorname, nachname, email, aktiv;
                """, (personen_id,))
                p = cur.fetchone()
        if p is None:
            raise KeyError(
                f"Person {personen_id} nicht gefunden oder bereits aktiv."
            )
        logger.info(f"Person {personen_id} reaktiviert.")
        return dict(p)

    def personen_suchen(self, suchbegriff: str) -> list[dict]:
        """Volltext-Suche in Firma, Vorname, Nachname und E-Mail."""
        muster = f"%{suchbegriff.lower()}%"
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute("""
                    SELECT
                        id, typ, firma, vorname, nachname, email, aktiv
                    FROM stammdaten.personen
                    WHERE aktiv = TRUE
                      AND (
                          LOWER(firma)    LIKE %s OR
                          LOWER(vorname)  LIKE %s OR
                          LOWER(nachname) LIKE %s OR
                          LOWER(email)    LIKE %s
                      )
                    ORDER BY COALESCE(firma, nachname)
                    LIMIT 50;
                """, (muster, muster, muster, muster))
                return [dict(z) for z in cur.fetchall()]

    # ---- Artikel ----

    def artikel_laden(self, nur_aktive: bool = True) -> list[dict]:
        """Laedt alle Artikel."""
        bedingung = "WHERE a.aktiv = TRUE" if nur_aktive else ""
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute(f"""
                    SELECT
                        a.id, a.artikelnummer, a.bezeichnung,
                        g.bezeichnung       AS gruppe,
                        a.einheit,
                        a.vk_preis::float,
                        a.ek_preis::float,
                        a.mwst_satz::float,
                        a.lagerbestand,
                        a.mindestbestand,
                        a.aktiv,
                        (a.lagerbestand <= a.mindestbestand
                         AND a.mindestbestand > 0) AS nachbestellung
                    FROM stammdaten.artikel          a
                    LEFT JOIN stammdaten.artikelgruppen g
                        ON a.artikelgruppe_id = g.id
                    {bedingung}
                    ORDER BY a.artikelnummer;
                """)
                return [dict(z) for z in cur.fetchall()]

    def artikel_laden_einzeln(self, artikel_id: int) -> dict:
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute("""
                    SELECT
                        a.id, a.artikelnummer, a.bezeichnung,
                        g.bezeichnung AS gruppe,
                        a.einheit, a.vk_preis::float, a.ek_preis::float,
                        a.mwst_satz::float, a.lagerbestand,
                        a.mindestbestand, a.aktiv
                    FROM stammdaten.artikel a
                    LEFT JOIN stammdaten.artikelgruppen g
                        ON a.artikelgruppe_id = g.id
                    WHERE a.id = %s;
                """, (artikel_id,))
                a = cur.fetchone()
        if a is None:
            raise KeyError(f"Artikel {artikel_id} nicht gefunden.")
        return dict(a)

    def artikel_aktualisieren(self, artikel_id: int, felder: dict) -> dict:
        self.artikel_laden_einzeln(artikel_id)
        if not felder:
            raise ValueError("Mindestens ein Feld muss angegeben werden.")
        set_k = ", ".join(f"{k} = %s" for k in felder)
        werte = list(felder.values()) + [artikel_id]
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute(f"""
                    UPDATE stammdaten.artikel SET {set_k}
                    WHERE id = %s
                    RETURNING
                        id, artikelnummer, bezeichnung,
                        einheit, vk_preis::float, ek_preis::float,
                        mwst_satz::float, lagerbestand, mindestbestand, aktiv;
                """, werte)
                return dict(cur.fetchone())

    def nachbestellung_laden(self) -> list[dict]:
        """Artikel deren Lagerbestand den Mindestbestand unterschreitet."""
        with verbinden() as conn:
            with conn.cursor(cursor_factory=RDC) as cur:
                cur.execute("""
                    SELECT
                        a.id,
                        a.artikelnummer,
                        a.bezeichnung,
                        g.bezeichnung AS gruppe,
                        a.einheit,
                        a.vk_preis::float,
                        a.ek_preis::float,
                        a.mwst_satz::float,
                        a.lagerbestand,
                        a.mindestbestand,
                        a.aktiv,
                        TRUE AS nachbestellung,
                        (a.mindestbestand - a.lagerbestand) AS fehlmenge
                    FROM stammdaten.artikel a
                    LEFT JOIN stammdaten.artikelgruppen g
                        ON a.artikelgruppe_id = g.id
                    WHERE a.aktiv = TRUE
                      AND a.lagerbestand <= a.mindestbestand
                      AND a.mindestbestand > 0
                    ORDER BY (a.mindestbestand - a.lagerbestand) DESC;
                """)
                return [dict(z) for z in cur.fetchall()]
