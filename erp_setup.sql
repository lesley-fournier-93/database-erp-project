-- ============================================================
-- ERP-Datenbank Setup
-- Enders Training | Python-Softwareentwicklung Kurs
-- Unternehmen: Enders Office & IT GmbH (fiktiv)
-- Branche: IT-Zubehör und Bürobedarf, Handel + Dienstleistungen
--
-- Ausführen mit: psql -U postgres -f erp_setup.sql
-- ============================================================

\echo '>>> Starte Setup der ERP-Datenbank...'

-- Alte Datenbank löschen falls vorhanden
DROP DATABASE IF EXISTS erp;

CREATE DATABASE erp
    WITH ENCODING = 'UTF8'
    TEMPLATE = template0
    LC_COLLATE = 'German_Germany.1252'
    LC_CTYPE   = 'German_Germany.1252';

\echo '>>> Datenbank angelegt'
\c erp

REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- Schemas anlegen:
-- stammdaten: Personen, Adressen, Artikel
-- einkauf:    Lieferantenbelege, Bestellungen, Wareneingänge
-- verkauf:    Kundenbelege, Angebote, Aufträge, Rechnungen
-- protokoll:  Änderungshistorie
CREATE SCHEMA stammdaten;
CREATE SCHEMA einkauf;
CREATE SCHEMA verkauf;
CREATE SCHEMA protokoll;

\echo '>>> Schemas angelegt'

-- ============================================================
-- Rollen und Benutzer
-- ============================================================

CREATE ROLE stammdaten_rolle;
CREATE ROLE einkauf_rolle;
CREATE ROLE verkauf_rolle;
CREATE ROLE erp_admin_rolle;

DROP USER IF EXISTS hans_meier;
DROP USER IF EXISTS petra_schmidt;
DROP USER IF EXISTS thomas_mueller;
DROP USER IF EXISTS erp_admin;

CREATE USER hans_meier    WITH PASSWORD 'HansPass2026!'    INHERIT;
CREATE USER petra_schmidt WITH PASSWORD 'PetraPass2026!'   INHERIT;
CREATE USER thomas_mueller WITH PASSWORD 'ThomasPass2026!' INHERIT;
CREATE USER erp_admin     WITH PASSWORD 'AdminPass2026!'   INHERIT BYPASSRLS;

GRANT stammdaten_rolle TO hans_meier;
GRANT einkauf_rolle    TO petra_schmidt;
GRANT verkauf_rolle    TO thomas_mueller;
GRANT erp_admin_rolle  TO erp_admin;

-- Admin bekommt alle Rollen:
GRANT stammdaten_rolle TO erp_admin;
GRANT einkauf_rolle    TO erp_admin;
GRANT verkauf_rolle    TO erp_admin;

\echo '>>> Rollen und Benutzer angelegt'

-- ============================================================
-- Stammdaten-Tabellen
-- ============================================================

CREATE TABLE stammdaten.laender (
    id        SERIAL PRIMARY KEY,
    iso_code  CHAR(2)      NOT NULL UNIQUE,
    bezeichnung VARCHAR(80) NOT NULL
);

CREATE TABLE stammdaten.zahlungsbedingungen (
    id              SERIAL PRIMARY KEY,
    bezeichnung     VARCHAR(80) NOT NULL,
    tage_netto      INTEGER NOT NULL DEFAULT 30,
    tage_skonto     INTEGER,
    skonto_prozent  NUMERIC(5,2),
    beschreibung    TEXT
);

CREATE TABLE stammdaten.artikelgruppen (
    id           SERIAL PRIMARY KEY,
    bezeichnung  VARCHAR(80) NOT NULL,
    beschreibung TEXT
);

CREATE TABLE stammdaten.personen (
    id               SERIAL PRIMARY KEY,
    typ              VARCHAR(12) NOT NULL
                     CHECK (typ IN ('kunde', 'lieferant', 'beide')),
    kundennummer     VARCHAR(20) UNIQUE,
    lieferantennummer VARCHAR(20) UNIQUE,
    firma            VARCHAR(120),
    vorname          VARCHAR(80),
    nachname         VARCHAR(80),
    email            VARCHAR(200) NOT NULL UNIQUE,
    telefon          VARCHAR(40),
    ust_id           VARCHAR(20),
    zahlungsbedingung_id INTEGER REFERENCES stammdaten.zahlungsbedingungen(id),
    kreditlimit      NUMERIC(12,2) DEFAULT 5000.00,
    aktiv            BOOLEAN NOT NULL DEFAULT TRUE,
    notizen          TEXT,
    angelegt_am      TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT personen_firma_oder_name CHECK (
        firma IS NOT NULL OR (vorname IS NOT NULL AND nachname IS NOT NULL)
    )
);

CREATE TABLE stammdaten.adressen (
    id          SERIAL PRIMARY KEY,
    personen_id INTEGER NOT NULL REFERENCES stammdaten.personen(id)
                ON DELETE CASCADE,
    adresstyp   VARCHAR(12) NOT NULL
                CHECK (adresstyp IN ('rechnung', 'lieferung', 'beide')),
    strasse     VARCHAR(120) NOT NULL,
    hausnummer  VARCHAR(10)  NOT NULL,
    plz         VARCHAR(10)  NOT NULL,
    ort         VARCHAR(80)  NOT NULL,
    land_id     INTEGER NOT NULL REFERENCES stammdaten.laender(id),
    ist_standard BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE stammdaten.artikel (
    id              SERIAL PRIMARY KEY,
    artikelnummer   VARCHAR(20) NOT NULL UNIQUE,
    bezeichnung     VARCHAR(120) NOT NULL,
    beschreibung    TEXT,
    artikelgruppe_id INTEGER REFERENCES stammdaten.artikelgruppen(id),
    einheit         VARCHAR(20) NOT NULL DEFAULT 'Stk',
    vk_preis        NUMERIC(12,4) NOT NULL DEFAULT 0,
    ek_preis        NUMERIC(12,4) NOT NULL DEFAULT 0,
    mwst_satz       NUMERIC(5,2)  NOT NULL DEFAULT 19.00,
    lagerbestand    INTEGER NOT NULL DEFAULT 0,
    mindestbestand  INTEGER NOT NULL DEFAULT 0,
    aktiv           BOOLEAN NOT NULL DEFAULT TRUE
);

-- Indizes Stammdaten:
CREATE INDEX idx_personen_typ       ON stammdaten.personen (typ);
CREATE INDEX idx_personen_aktiv     ON stammdaten.personen (aktiv);
CREATE INDEX idx_adressen_person    ON stammdaten.adressen (personen_id);
CREATE INDEX idx_artikel_gruppe     ON stammdaten.artikel (artikelgruppe_id);
CREATE INDEX idx_artikel_aktiv      ON stammdaten.artikel (aktiv);

\echo '>>> Stammdaten-Tabellen angelegt'

-- ============================================================
-- Belegstruktur (gemeinsam für Einkauf und Verkauf)
-- ============================================================

CREATE TABLE stammdaten.belegarten (
    id              SERIAL PRIMARY KEY,
    bezeichnung     VARCHAR(80)  NOT NULL,
    kuerzel         CHAR(3)      NOT NULL UNIQUE,
    bereich         VARCHAR(10)  NOT NULL CHECK (bereich IN ('einkauf', 'verkauf')),
    nummernkreis    VARCHAR(10)  NOT NULL,  -- Prefix für Belegnummern
    folge_kuerzel   CHAR(3)      REFERENCES stammdaten.belegarten(kuerzel)
);

-- ============================================================
-- Einkauf-Tabellen
-- ============================================================

CREATE TABLE einkauf.belege (
    id                   SERIAL PRIMARY KEY,
    belegnummer          VARCHAR(20) NOT NULL UNIQUE,
    belegart             CHAR(3)     NOT NULL REFERENCES stammdaten.belegarten(kuerzel),
    lieferant_id         INTEGER     NOT NULL REFERENCES stammdaten.personen(id),
    lieferad_id          INTEGER     REFERENCES stammdaten.adressen(id),
    beleg_datum          DATE        NOT NULL DEFAULT CURRENT_DATE,
    liefer_datum         DATE,
    zahlungsbedingung_id INTEGER     REFERENCES stammdaten.zahlungsbedingungen(id),
    status               VARCHAR(20) NOT NULL DEFAULT 'offen'
                         CHECK (status IN ('entwurf','offen','teilgeliefert',
                                           'abgeschlossen','storniert')),
    nettobetrag          NUMERIC(12,2) NOT NULL DEFAULT 0,
    mwst_betrag          NUMERIC(12,2) NOT NULL DEFAULT 0,
    bruttobetrag         NUMERIC(12,2) NOT NULL DEFAULT 0,
    bezahlt_am           DATE,
    lieferanten_belegnr  VARCHAR(40),
    notizen              TEXT,
    angelegt_am          TIMESTAMP NOT NULL DEFAULT NOW(),
    angelegt_von         TEXT NOT NULL DEFAULT current_user,
    vorgaenger_id        INTEGER REFERENCES einkauf.belege(id)
);

CREATE TABLE einkauf.positionen (
    id               SERIAL PRIMARY KEY,
    beleg_id         INTEGER       NOT NULL REFERENCES einkauf.belege(id)
                     ON DELETE CASCADE,
    position         INTEGER       NOT NULL,
    artikel_id       INTEGER       REFERENCES stammdaten.artikel(id),
    bezeichnung      VARCHAR(120)  NOT NULL,
    menge            NUMERIC(12,3) NOT NULL,
    einheit          VARCHAR(20)   NOT NULL DEFAULT 'Stk',
    einzelpreis      NUMERIC(12,4) NOT NULL,
    rabatt_prozent   NUMERIC(5,2)  NOT NULL DEFAULT 0,
    mwst_satz        NUMERIC(5,2)  NOT NULL DEFAULT 19.00,
    nettobetrag      NUMERIC(12,2) NOT NULL,
    UNIQUE (beleg_id, position)
);

CREATE INDEX idx_ek_belege_lieferant ON einkauf.belege (lieferant_id);
CREATE INDEX idx_ek_belege_status    ON einkauf.belege (status);
CREATE INDEX idx_ek_belege_datum     ON einkauf.belege (beleg_datum);
CREATE INDEX idx_ek_positionen_beleg ON einkauf.positionen (beleg_id);
CREATE INDEX idx_ek_positionen_art   ON einkauf.positionen (artikel_id);

\echo '>>> Einkauf-Tabellen angelegt'

-- ============================================================
-- Verkauf-Tabellen
-- ============================================================

CREATE TABLE verkauf.belege (
    id                   SERIAL PRIMARY KEY,
    belegnummer          VARCHAR(20) NOT NULL UNIQUE,
    belegart             CHAR(3)     NOT NULL REFERENCES stammdaten.belegarten(kuerzel),
    kunde_id             INTEGER     NOT NULL REFERENCES stammdaten.personen(id),
    lieferad_id          INTEGER     REFERENCES stammdaten.adressen(id),
    beleg_datum          DATE        NOT NULL DEFAULT CURRENT_DATE,
    liefer_datum         DATE,
    zahlungsbedingung_id INTEGER     REFERENCES stammdaten.zahlungsbedingungen(id),
    status               VARCHAR(20) NOT NULL DEFAULT 'offen'
                         CHECK (status IN ('entwurf','offen','angenommen','abgelehnt',
                                           'teilgeliefert','abgeschlossen','storniert')),
    nettobetrag          NUMERIC(12,2) NOT NULL DEFAULT 0,
    mwst_betrag          NUMERIC(12,2) NOT NULL DEFAULT 0,
    bruttobetrag         NUMERIC(12,2) NOT NULL DEFAULT 0,
    bezahlt_am           DATE,
    notizen              TEXT,
    angelegt_am          TIMESTAMP NOT NULL DEFAULT NOW(),
    angelegt_von         TEXT NOT NULL DEFAULT current_user,
    vorgaenger_id        INTEGER REFERENCES verkauf.belege(id)
);

CREATE TABLE verkauf.positionen (
    id               SERIAL PRIMARY KEY,
    beleg_id         INTEGER       NOT NULL REFERENCES verkauf.belege(id)
                     ON DELETE CASCADE,
    position         INTEGER       NOT NULL,
    artikel_id       INTEGER       REFERENCES stammdaten.artikel(id),
    bezeichnung      VARCHAR(120)  NOT NULL,
    menge            NUMERIC(12,3) NOT NULL,
    einheit          VARCHAR(20)   NOT NULL DEFAULT 'Stk',
    einzelpreis      NUMERIC(12,4) NOT NULL,
    rabatt_prozent   NUMERIC(5,2)  NOT NULL DEFAULT 0,
    mwst_satz        NUMERIC(5,2)  NOT NULL DEFAULT 19.00,
    nettobetrag      NUMERIC(12,2) NOT NULL,
    UNIQUE (beleg_id, position)
);

CREATE INDEX idx_vk_belege_kunde    ON verkauf.belege (kunde_id);
CREATE INDEX idx_vk_belege_status   ON verkauf.belege (status);
CREATE INDEX idx_vk_belege_datum    ON verkauf.belege (beleg_datum);
CREATE INDEX idx_vk_positionen_bel  ON verkauf.positionen (beleg_id);
CREATE INDEX idx_vk_positionen_art  ON verkauf.positionen (artikel_id);

\echo '>>> Verkauf-Tabellen angelegt'

-- ============================================================
-- Protokoll-Tabellen
-- ============================================================

CREATE TABLE protokoll.aenderungen (
    id           SERIAL PRIMARY KEY,
    zeitstempel  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    benutzer     TEXT NOT NULL DEFAULT current_user,
    schema_name  TEXT NOT NULL,
    tabelle      TEXT NOT NULL,
    datensatz_id INTEGER NOT NULL,
    aktion       CHAR(1) NOT NULL CHECK (aktion IN ('I','U','D')),
    alte_werte   JSONB,
    neue_werte   JSONB
);

CREATE TABLE protokoll.api_log (
    id          SERIAL PRIMARY KEY,
    zeitstempel TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    benutzer    TEXT,
    methode     TEXT NOT NULL,
    pfad        TEXT NOT NULL,
    statuscode  INTEGER,
    dauer_ms    NUMERIC(10,2)
);

CREATE INDEX idx_proto_aend_tabelle ON protokoll.aenderungen (schema_name, tabelle);
CREATE INDEX idx_proto_aend_datum   ON protokoll.aenderungen (zeitstempel);

\echo '>>> Protokoll-Tabellen angelegt'

-- ============================================================
-- Rechte vergeben
-- ============================================================

GRANT CONNECT ON DATABASE erp
    TO stammdaten_rolle, einkauf_rolle, verkauf_rolle, erp_admin_rolle;

GRANT USAGE ON SCHEMA stammdaten TO
    stammdaten_rolle, einkauf_rolle, verkauf_rolle, erp_admin_rolle;
GRANT USAGE ON SCHEMA einkauf    TO einkauf_rolle, erp_admin_rolle;
GRANT USAGE ON SCHEMA verkauf    TO verkauf_rolle, erp_admin_rolle;
GRANT USAGE ON SCHEMA protokoll  TO erp_admin_rolle;

-- stammdaten_rolle: Stammdaten lesen und schreiben
GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA stammdaten TO stammdaten_rolle;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA stammdaten TO stammdaten_rolle;
-- Lesen dürfen alle:
GRANT SELECT ON ALL TABLES IN SCHEMA stammdaten
    TO einkauf_rolle, verkauf_rolle;

-- einkauf_rolle: Einkaufsdaten vollständig, Stammdaten nur lesen
GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA einkauf TO einkauf_rolle;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA einkauf TO einkauf_rolle;

-- verkauf_rolle: Verkaufsdaten vollständig, Stammdaten nur lesen
GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA verkauf TO verkauf_rolle;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA verkauf TO verkauf_rolle;

-- erp_admin_rolle: alles
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA einkauf   TO erp_admin_rolle;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA verkauf   TO erp_admin_rolle;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA protokoll TO erp_admin_rolle;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA einkauf   TO erp_admin_rolle;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA verkauf   TO erp_admin_rolle;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA protokoll TO erp_admin_rolle;

-- Default Privileges für zukünftige Tabellen:
ALTER DEFAULT PRIVILEGES IN SCHEMA stammdaten
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO stammdaten_rolle;
ALTER DEFAULT PRIVILEGES IN SCHEMA stammdaten
    GRANT SELECT ON TABLES TO einkauf_rolle, verkauf_rolle;
ALTER DEFAULT PRIVILEGES IN SCHEMA einkauf
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO einkauf_rolle;
ALTER DEFAULT PRIVILEGES IN SCHEMA verkauf
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO verkauf_rolle;

\echo '>>> Rechte vergeben'

-- ============================================================
-- Testdaten
-- ============================================================

-- Länder
INSERT INTO stammdaten.laender (id, iso_code, bezeichnung) VALUES
    (1,  'DE', 'Deutschland'),
    (2,  'AT', 'Österreich'),
    (3,  'CH', 'Schweiz'),
    (4,  'NL', 'Niederlande'),
    (5,  'FR', 'Frankreich'),
    (6,  'IT', 'Italien'),
    (7,  'PL', 'Polen'),
    (8,  'CZ', 'Tschechien'),
    (9,  'GB', 'Vereinigtes Königreich'),
    (10, 'US', 'Vereinigte Staaten');
SELECT setval('stammdaten.laender_id_seq', 10);

-- Zahlungsbedingungen
INSERT INTO stammdaten.zahlungsbedingungen
    (id, bezeichnung, tage_netto, tage_skonto, skonto_prozent, beschreibung) VALUES
    (1, 'Sofort netto',          0,  NULL, NULL,  'Sofort zahlbar ohne Abzug'),
    (2, '14 Tage 2% Skonto',     30, 14,   2.00,  'Innerhalb 14 Tagen 2% Skonto, 30 Tage netto'),
    (3, '30 Tage netto',         30, NULL, NULL,  '30 Tage netto ohne Abzug'),
    (4, '30/10 Tage 3% Skonto',  30, 10,   3.00,  'Innerhalb 10 Tagen 3% Skonto, 30 Tage netto'),
    (5, '60 Tage netto',         60, NULL, NULL,  '60 Tage netto ohne Abzug'),
    (6, 'Vorkasse',               0, NULL, NULL,  'Zahlung vor Lieferung');
SELECT setval('stammdaten.zahlungsbedingungen_id_seq', 6);

-- Belegarten
INSERT INTO stammdaten.belegarten
    (id, bezeichnung, kuerzel, bereich, nummernkreis, folge_kuerzel) VALUES
    (1, 'Anfrage',           'ANF', 'einkauf', 'ANF', 'BES'),
    (2, 'Bestellung',        'BES', 'einkauf', 'BES', 'WEI'),
    (3, 'Wareneingang',      'WEI', 'einkauf', 'WEI', 'ERE'),
    (4, 'Eingangsrechnung',  'ERE', 'einkauf', 'ERE', NULL),
    (5, 'Angebot',           'ANG', 'verkauf', 'ANG', 'AUF'),
    (6, 'Auftrag',           'AUF', 'verkauf', 'AUF', 'LIE'),
    (7, 'Lieferschein',      'LIE', 'verkauf', 'LIE', 'REC'),
    (8, 'Rechnung',          'REC', 'verkauf', 'REC', 'GUT'),
    (9, 'Gutschrift',        'GUT', 'verkauf', 'GUT', NULL);
SELECT setval('stammdaten.belegarten_id_seq', 9);

-- Artikelgruppen
INSERT INTO stammdaten.artikelgruppen (id, bezeichnung, beschreibung) VALUES
    (1, 'Notebooks & Tablets',   'Tragbare Computer, Tablets, 2-in-1-Geräte'),
    (2, 'Peripherie',            'Mäuse, Tastaturen, Monitore, Headsets'),
    (3, 'Netzwerk & Zubehör',    'Router, Switches, Kabel, USB-Hubs'),
    (4, 'Bürobedarf',            'Papier, Stifte, Ordner, Druckerverbrauchsmaterial'),
    (5, 'Software & Lizenzen',   'Office-Pakete, Antivirensoftware, Betriebssysteme'),
    (6, 'Drucker & Scanner',     'Tintenstrahler, Laserdrucker, Multifunktionsgeräte'),
    (7, 'Dienstleistungen',      'Installation, Wartung, Schulungen, Support');
SELECT setval('stammdaten.artikelgruppen_id_seq', 7);

\echo '>>> Basisdaten angelegt'

-- ============================================================
-- Artikel (40 Stück)
-- ============================================================
\echo '>>> Füge Artikel ein...'

INSERT INTO stammdaten.artikel
    (id, artikelnummer, bezeichnung, beschreibung, artikelgruppe_id,
     einheit, vk_preis, ek_preis, mwst_satz, lagerbestand, mindestbestand) VALUES
-- Notebooks & Tablets (1-8)
    (1,  'NB-001', 'Notebook Business 14"',
         '14 Zoll, Intel Core i5, 16 GB RAM, 512 GB SSD, Windows 11 Pro',
         1, 'Stk', 899.00, 620.00, 19.00, 12, 3),
    (2,  'NB-002', 'Notebook Business 15"',
         '15,6 Zoll, Intel Core i7, 32 GB RAM, 1 TB SSD, Windows 11 Pro',
         1, 'Stk', 1299.00, 890.00, 19.00, 8, 2),
    (3,  'NB-003', 'Notebook Einsteiger 15"',
         '15,6 Zoll, Intel Core i3, 8 GB RAM, 256 GB SSD, Windows 11 Home',
         1, 'Stk', 549.00, 370.00, 19.00, 15, 5),
    (4,  'TB-001', 'Tablet 10,4 Zoll',
         '10,4 Zoll, 4 GB RAM, 64 GB, WLAN, Android 14',
         1, 'Stk', 279.00, 185.00, 19.00, 20, 5),
    (5,  'TB-002', 'Tablet 12,4 Zoll Pro',
         '12,4 Zoll, 8 GB RAM, 256 GB, WLAN + LTE, Android 14',
         1, 'Stk', 489.00, 330.00, 19.00, 10, 3),
    (6,  'NB-004', 'Notebook Convertible 13"',
         '13,3 Zoll, Intel Core i5, 16 GB RAM, 512 GB SSD, Touch, 360°',
         1, 'Stk', 999.00, 680.00, 19.00, 6, 2),
    (7,  'NB-005', 'Notebook Gaming 17"',
         '17,3 Zoll, Intel Core i7, 32 GB RAM, 1 TB SSD, RTX 4060',
         1, 'Stk', 1599.00, 1120.00, 19.00, 4, 1),
    (8,  'NB-006', 'Notebook Ultraslim 13"',
         '13,3 Zoll, Intel Core i5, 16 GB RAM, 512 GB SSD, 1,2 kg',
         1, 'Stk', 1099.00, 750.00, 19.00, 7, 2),
-- Peripherie (9-18)
    (9,  'PE-001', 'Maus kabellos ergonomisch',
         'Optisch, 2,4 GHz, 6 Tasten, DPI einstellbar',
         2, 'Stk', 29.90, 14.50, 19.00, 45, 10),
    (10, 'PE-002', 'Tastatur kabellos DE',
         'Tastatur DE-Layout, 2,4 GHz, Multimedia-Tasten',
         2, 'Stk', 39.90, 19.00, 19.00, 38, 10),
    (11, 'PE-003', 'Set Tastatur + Maus kabellos',
         'Kombi-Set DE-Layout, 2,4 GHz, ein USB-Empfänger',
         2, 'Stk', 59.90, 30.00, 19.00, 22, 5),
    (12, 'PE-004', 'Monitor 24" Full HD',
         '24 Zoll, 1920x1080, IPS, HDMI+DP, höhenverstellbar',
         2, 'Stk', 199.00, 128.00, 19.00, 14, 4),
    (13, 'PE-005', 'Monitor 27" QHD',
         '27 Zoll, 2560x1440, IPS, HDMI+DP+USB-C, höhenverstellbar',
         2, 'Stk', 349.00, 228.00, 19.00, 9, 3),
    (14, 'PE-006', 'Headset USB Stereo',
         'USB, Stereolautsprecher, Mikrofon mit Stummschaltung',
         2, 'Stk', 49.90, 25.00, 19.00, 30, 8),
    (15, 'PE-007', 'Webcam Full HD',
         '1080p, Autofokus, eingebautes Mikrofon, USB-A',
         2, 'Stk', 69.90, 38.00, 19.00, 18, 5),
    (16, 'PE-008', 'Dockingstation USB-C',
         'USB-C, 2x HDMI, 4x USB-A, RJ45, SD-Karte, 100W PD',
         2, 'Stk', 119.00, 72.00, 19.00, 12, 4),
    (17, 'PE-009', 'Mauspad XL',
         'Extra groß 800x350mm, rutschfeste Unterseite',
         2, 'Stk', 14.90, 5.50, 19.00, 60, 15),
    (18, 'PE-010', 'Notebookständer verstellbar',
         'Aluminium, 6 Höhenstufen, Belüftungsöffnungen',
         2, 'Stk', 34.90, 16.00, 19.00, 25, 8),
-- Netzwerk & Zubehör (19-24)
    (19, 'NW-001', 'WLAN-Router AX1800',
         'WiFi 6, Dual-Band, 4x Gigabit LAN, USB 3.0',
         3, 'Stk', 79.90, 45.00, 19.00, 16, 4),
    (20, 'NW-002', 'Switch 8-Port Gigabit',
         '8x 1000 Mbit/s, unmanaged, lüfterlos',
         3, 'Stk', 39.90, 20.00, 19.00, 20, 5),
    (21, 'NW-003', 'Netzwerkkabel Cat.6 5m',
         'Cat.6 U/UTP, 5 Meter, grau',
         3, 'Stk', 4.90, 1.80, 19.00, 100, 20),
    (22, 'NW-004', 'USB-Hub 7-Port',
         '7x USB-A 3.0, externer Netzteilanschluss',
         3, 'Stk', 24.90, 11.00, 19.00, 35, 10),
    (23, 'NW-005', 'USB-C Hub 6-in-1',
         'USB-C, 2x USB-A 3.0, HDMI, SD, microSD, USB-C PD 60W',
         3, 'Stk', 32.90, 15.00, 19.00, 28, 8),
    (24, 'NW-006', 'Netzwerkkabel Cat.6 10m',
         'Cat.6 U/UTP, 10 Meter, grau',
         3, 'Stk', 7.90, 2.80, 19.00, 80, 15),
-- Bürobedarf (25-30)
    (25, 'BB-001', 'Druckerpapier A4 80g 500 Bl.',
         'A4, 80g/m², holzfrei weiß, 500 Blatt pro Packung',
         4, 'Pck', 5.90, 3.20, 19.00, 200, 50),
    (26, 'BB-002', 'Druckerpapier A4 80g Karton',
         'A4, 80g/m², holzfrei weiß, 5 Packungen à 500 Blatt',
         4, 'Kar', 27.90, 15.50, 19.00, 40, 10),
    (27, 'BB-003', 'Toner schwarz kompatibel',
         'Kompatibel zu gängigen Laserdruckern, ca. 3.000 Seiten',
         4, 'Stk', 24.90, 12.00, 19.00, 30, 8),
    (28, 'BB-004', 'Ordner A4 8cm breit',
         'A4, 80mm, PP-Deckel, Hebelmechanik, sortiert',
         4, 'Stk', 3.90, 1.60, 19.00, 150, 30),
    (29, 'BB-005', 'Kugelschreiber Blau 10er',
         'Mittlere Strichstärke, 10 Stück im Set',
         4, 'Set', 3.50, 1.20, 19.00, 80, 20),
    (30, 'BB-006', 'Haftnotizen 76x76mm gelb',
         '76x76mm, gelb, 100 Blatt pro Block, 6 Blöcke',
         4, 'Pck', 4.90, 2.10, 19.00, 70, 20),
-- Software & Lizenzen (31-34)
    (31, 'SW-001', 'Office Paket Jahresabo',
         'Word, Excel, PowerPoint, Outlook - 1 Nutzer, 1 Jahr',
         5, 'Liz', 89.00, 55.00, 19.00, 999, 0),
    (32, 'SW-002', 'Antivirensoftware 1 Jahr',
         'Virenschutz + Firewall, 1 Gerät, 1 Jahr',
         5, 'Liz', 29.90, 14.00, 19.00, 999, 0),
    (33, 'SW-003', 'Betriebssystem Home',
         'Windows 11 Home, OEM-Lizenz, 64-Bit',
         5, 'Liz', 119.00, 78.00, 19.00, 50, 10),
    (34, 'SW-004', 'Betriebssystem Pro',
         'Windows 11 Pro, OEM-Lizenz, 64-Bit',
         5, 'Liz', 179.00, 118.00, 19.00, 35, 5),
-- Drucker & Scanner (35-37)
    (35, 'DR-001', 'Laserdrucker Mono A4',
         'Monolaser, 30 Seiten/Min, Duplex, USB + LAN + WLAN',
         6, 'Stk', 199.00, 128.00, 19.00, 8, 2),
    (36, 'DR-002', 'Multifunktionsgerät Farbe A4',
         'Farblaser, Drucken/Kopieren/Scannen/Faxen, Duplex',
         6, 'Stk', 349.00, 225.00, 19.00, 5, 1),
    (37, 'DR-003', 'Scanner Dokumentenscanner',
         'ADF 50 Blatt, Duplex, 600 dpi, USB + WLAN',
         6, 'Stk', 249.00, 162.00, 19.00, 4, 1),
-- Dienstleistungen (38-40)
    (38, 'DL-001', 'IT-Installation vor Ort',
         'Einrichtung Gerät, Software-Installation, 1 Stunde',
         7, 'Std', 95.00, 0.00, 19.00, 0, 0),
    (39, 'DL-002', 'IT-Wartungsvertrag Basis',
         'Monatliche Fernwartung, Reaktionszeit 4h, pro Monat',
         7, 'Mon', 49.00, 0.00, 19.00, 0, 0),
    (40, 'DL-003', 'Schulung IT-Grundlagen',
         'Halbtagesschulung vor Ort, bis 8 Teilnehmer',
         7, 'Tag', 490.00, 0.00, 19.00, 0, 0);

SELECT setval('stammdaten.artikel_id_seq', 40);

\echo '>>> Artikel angelegt'

-- ============================================================
-- Personen: 8 Lieferanten, 25 Kunden, 2 beides
-- ============================================================
\echo '>>> Füge Personen ein...'

INSERT INTO stammdaten.personen
    (id, typ, kundennummer, lieferantennummer, firma, vorname, nachname,
     email, telefon, ust_id, zahlungsbedingung_id, kreditlimit, aktiv) VALUES
-- Lieferanten (1-8)
    (1,  'lieferant', NULL, 'L-0001', 'TechDistri GmbH',
         NULL, NULL, 'einkauf@techdistri.de', '030 12345-0',
         'DE123456789', 2, 50000.00, TRUE),
    (2,  'lieferant', NULL, 'L-0002', 'OfficeSupply AG',
         NULL, NULL, 'bestellung@officesupply.de', '040 98765-0',
         'DE234567890', 3, 25000.00, TRUE),
    (3,  'lieferant', NULL, 'L-0003', 'Notebook Import GmbH',
         NULL, NULL, 'orders@notebook-import.de', '089 11111-0',
         'DE345678901', 4, 75000.00, TRUE),
    (4,  'lieferant', NULL, 'L-0004', 'Peripherals Europe BV',
         NULL, NULL, 'sales@peripherals-eu.nl', '+31 20 555 1234',
         'NL123456789B01', 2, 30000.00, TRUE),
    (5,  'lieferant', NULL, 'L-0005', 'SoftwareLizenz.de GmbH',
         NULL, NULL, 'lizenzen@softwarelizenz.de', '0800 765-0000',
         'DE456789012', 6, 15000.00, TRUE),
    (6,  'lieferant', NULL, 'L-0006', 'PrinterWorld GmbH',
         NULL, NULL, 'order@printerworld.de', '0221 333-4444',
         'DE567890123', 3, 20000.00, TRUE),
    (7,  'lieferant', NULL, 'L-0007', 'Network Components GmbH',
         NULL, NULL, 'sales@networkcomp.de', '0511 777-8888',
         'DE678901234', 2, 18000.00, TRUE),
    (8,  'lieferant', NULL, 'L-0008', 'Büromaterial Großhandel KG',
         NULL, NULL, 'bestellung@buerogroß.de', '0711 222-3333',
         'DE789012345', 3, 10000.00, TRUE),
-- Kunden (9-33)
    (9,  'kunde', 'K-0001', NULL, 'Muster AG',
         NULL, NULL, 'einkauf@muster-ag.de', '030 4444-0',
         'DE100001001', 2, 15000.00, TRUE),
    (10, 'kunde', 'K-0002', NULL, 'Schmidt & Partner GbR',
         NULL, NULL, 'buero@schmidt-partner.de', '040 5555-0',
         NULL, 3, 8000.00, TRUE),
    (11, 'kunde', 'K-0003', NULL, 'Innovatech GmbH',
         NULL, NULL, 'it@innovatech.de', '089 6666-0',
         'DE100002002', 4, 25000.00, TRUE),
    (12, 'kunde', 'K-0004', NULL, 'Bauunternehmen Richter GmbH',
         NULL, NULL, 'verwaltung@richter-bau.de', '0211 7777-0',
         'DE100003003', 3, 10000.00, TRUE),
    (13, 'kunde', 'K-0005', NULL, 'Steuerkanzlei Hoffmann',
         NULL, NULL, 'buero@stk-hoffmann.de', '0221 8888-0',
         'DE100004004', 2, 6000.00, TRUE),
    (14, 'kunde', 'K-0006', NULL, NULL,
         'Markus', 'Brandt', 'markus.brandt@email.de', '0176 12345678',
         NULL, 3, 2000.00, TRUE),
    (15, 'kunde', 'K-0007', NULL, 'Gasthaus Zur Linde GmbH',
         NULL, NULL, 'info@zur-linde.de', '09131 22222',
         'DE100005005', 3, 3000.00, TRUE),
    (16, 'kunde', 'K-0008', NULL, 'Arztpraxis Dr. Müller',
         NULL, NULL, 'praxis@dr-mueller.de', '069 33333-0',
         'DE100006006', 2, 8000.00, TRUE),
    (17, 'kunde', 'K-0009', NULL, 'Handwerksbetrieb Schneider',
         NULL, NULL, 'buero@hw-schneider.de', '0341 44444',
         NULL, 3, 4000.00, TRUE),
    (18, 'kunde', 'K-0010', NULL, 'Versicherungsbüro Weber GmbH',
         NULL, NULL, 'einkauf@vb-weber.de', '0721 55555-0',
         'DE100007007', 2, 12000.00, TRUE),
    (19, 'kunde', 'K-0011', NULL, 'Logistik Fischer GmbH & Co. KG',
         NULL, NULL, 'it@fischer-log.de', '0611 66666-0',
         'DE100008008', 4, 20000.00, TRUE),
    (20, 'kunde', 'K-0012', NULL, NULL,
         'Sandra', 'Klein', 'sandra.klein@web.de', '0157 87654321',
         NULL, 3, 1500.00, TRUE),
    (21, 'kunde', 'K-0013', NULL, 'Photoatelier Bauer',
         NULL, NULL, 'foto@atelier-bauer.de', '0421 77777',
         NULL, 3, 3500.00, TRUE),
    (22, 'kunde', 'K-0014', NULL, 'Zahnarztpraxis Meier & Koch',
         NULL, NULL, 'praxis@meier-koch-zahnarzt.de', '0431 88888-0',
         'DE100009009', 2, 6000.00, TRUE),
    (23, 'kunde', 'K-0015', NULL, 'Hotel Stadtblick GmbH',
         NULL, NULL, 'direktion@hotel-stadtblick.de', '0951 99999-0',
         'DE100010010', 3, 15000.00, TRUE),
    (24, 'kunde', 'K-0016', NULL, 'Fitnessstudio Aktiv GmbH',
         NULL, NULL, 'buero@aktiv-studio.de', '0821 11111-0',
         'DE100011011', 3, 4000.00, TRUE),
    (25, 'kunde', 'K-0017', NULL, NULL,
         'Thomas', 'Wagner', 't.wagner@gmail.com', '0162 11223344',
         NULL, 3, 1000.00, TRUE),
    (26, 'kunde', 'K-0018', NULL, 'Sprachschule Lingua GmbH',
         NULL, NULL, 'verwaltung@lingua-schule.de', '0731 22222-0',
         'DE100012012', 2, 7000.00, TRUE),
    (27, 'kunde', 'K-0019', NULL, 'Werbeagentur Kreativ GmbH',
         NULL, NULL, 'it@kreativ-agentur.de', '0621 33333-0',
         'DE100013013', 4, 18000.00, TRUE),
    (28, 'kunde', 'K-0020', NULL, 'Physiopraxis Gesund GbR',
         NULL, NULL, 'empfang@physio-gesund.de', '0911 44444',
         NULL, 3, 3000.00, TRUE),
    (29, 'kunde', 'K-0021', NULL, 'Autowerkstatt Schnell GmbH',
         NULL, NULL, 'buero@aw-schnell.de', '0521 55555',
         'DE100014014', 3, 5000.00, TRUE),
    (30, 'kunde', 'K-0022', NULL, 'Elektroinstallation Blitz GmbH',
         NULL, NULL, 'buero@blitz-elektro.de', '0231 66666-0',
         'DE100015015', 2, 6000.00, TRUE),
    (31, 'kunde', 'K-0023', NULL, NULL,
         'Anna', 'Schulz', 'anna.schulz@outlook.de', '0170 99887766',
         NULL, 3, 2000.00, TRUE),
    (32, 'kunde', 'K-0024', NULL, 'Reinigungsdienst Sauber GmbH',
         NULL, NULL, 'buero@sauber-reinigung.de', '0461 77777',
         NULL, 3, 2500.00, FALSE),  -- inaktiver Kunde
    (33, 'kunde', 'K-0025', NULL, 'Akademie für Weiterbildung e.V.',
         NULL, NULL, 'verwaltung@afb-weiterbildung.de', '0391 88888-0',
         'DE100016016', 3, 10000.00, TRUE),
-- Person die beides ist: Lieferant und Kunde (34-35)
    (34, 'beide',   'K-0026', 'L-0009', 'Druckerei Buntdruck GmbH',
         NULL, NULL, 'buero@buntdruck.de', '0351 44444-0',
         'DE100017017', 2, 8000.00, TRUE),
    (35, 'beide',   'K-0027', 'L-0010', 'IT-Service Profi GmbH',
         NULL, NULL, 'buero@it-service-profi.de', '0381 55555-0',
         'DE100018018', 3, 12000.00, TRUE);

SELECT setval('stammdaten.personen_id_seq', 35);

\echo '>>> Personen angelegt'

-- ============================================================
-- Adressen
-- ============================================================
\echo '>>> Füge Adressen ein...'

INSERT INTO stammdaten.adressen
    (id, personen_id, adresstyp, strasse, hausnummer, plz, ort, land_id, ist_standard) VALUES
-- Lieferanten-Adressen
    (1,  1,  'beide',     'Berliner Allee',       '42',  '10115', 'Berlin',      1, TRUE),
    (2,  2,  'beide',     'Speicherstraße',        '7',   '20095', 'Hamburg',     1, TRUE),
    (3,  3,  'beide',     'Maximilianstraße',      '15',  '80539', 'München',     1, TRUE),
    (4,  4,  'beide',     'Keizersgracht',         '123', '1017',  'Amsterdam',   4, TRUE),
    (5,  5,  'beide',     'Stuttgarter Str.',      '88',  '70173', 'Stuttgart',   1, TRUE),
    (6,  6,  'beide',     'Rheinufer',             '33',  '50668', 'Köln',        1, TRUE),
    (7,  7,  'beide',     'Hannoversche Str.',     '12',  '30159', 'Hannover',    1, TRUE),
    (8,  8,  'beide',     'Königstraße',           '5',   '70173', 'Stuttgart',   1, TRUE),
-- Kunden-Adressen
    (9,  9,  'beide',     'Unter den Linden',      '10',  '10117', 'Berlin',      1, TRUE),
    (10, 10, 'beide',     'Hauptstraße',           '22',  '22765', 'Hamburg',     1, TRUE),
    (11, 11, 'beide',     'Leopoldstraße',         '80',  '80804', 'München',     1, TRUE),
    (12, 11, 'lieferung', 'Lager Ost',             '1',   '81929', 'München',     1, FALSE),
    (13, 12, 'beide',     'Düsseldorfer Allee',    '44',  '40210', 'Düsseldorf',  1, TRUE),
    (14, 13, 'beide',     'Hohenzollernring',      '21',  '50672', 'Köln',        1, TRUE),
    (15, 14, 'beide',     'Parkweg',               '3',   '60311', 'Frankfurt',   1, TRUE),
    (16, 15, 'beide',     'Dorfstraße',            '16',  '91054', 'Erlangen',    1, TRUE),
    (17, 16, 'beide',     'Goethestraße',          '55',  '60313', 'Frankfurt',   1, TRUE),
    (18, 17, 'beide',     'Messeweg',              '7',   '04103', 'Leipzig',     1, TRUE),
    (19, 18, 'beide',     'Kaiserstraße',          '14',  '76133', 'Karlsruhe',   1, TRUE),
    (20, 19, 'beide',     'Industriestraße',       '90',  '65189', 'Wiesbaden',   1, TRUE),
    (21, 20, 'beide',     'Birkenweg',             '4',   '28195', 'Bremen',      1, TRUE),
    (22, 21, 'beide',     'Schlachte',             '28',  '28195', 'Bremen',      1, TRUE),
    (23, 22, 'beide',     'Holstenwall',           '13',  '24103', 'Kiel',        1, TRUE),
    (24, 23, 'beide',     'Dom-Residenz-Str.',     '9',   '96047', 'Bamberg',     1, TRUE),
    (25, 24, 'beide',     'Inninger Straße',       '71',  '86159', 'Augsburg',    1, TRUE),
    (26, 25, 'beide',     'Am Stadtpark',          '2',   '86150', 'Augsburg',    1, TRUE),
    (27, 26, 'beide',     'Kirchplatz',            '11',  '89073', 'Ulm',         1, TRUE),
    (28, 27, 'beide',     'Augustaanlage',         '35',  '68165', 'Mannheim',    1, TRUE),
    (29, 28, 'beide',     'Nürnberger Straße',     '42',  '90403', 'Nürnberg',    1, TRUE),
    (30, 29, 'beide',     'Detmolder Straße',      '88',  '33602', 'Bielefeld',   1, TRUE),
    (31, 30, 'beide',     'Westenhellweg',         '17',  '44137', 'Dortmund',    1, TRUE),
    (32, 31, 'beide',     'Schloßstraße',          '5',   '01067', 'Dresden',     1, TRUE),
    (33, 32, 'beide',     'Rathausplatz',          '1',   '24937', 'Flensburg',   1, TRUE),
    (34, 33, 'beide',     'Breiter Weg',           '228', '39104', 'Magdeburg',   1, TRUE),
    (35, 34, 'beide',     'Prager Straße',         '6',   '01069', 'Dresden',     1, TRUE),
    (36, 35, 'beide',     'Wismarsche Straße',     '14',  '18057', 'Rostock',     1, TRUE);

SELECT setval('stammdaten.adressen_id_seq', 36);

\echo '>>> Adressen angelegt'

-- ============================================================
-- Einkaufsbelege: 12 Belege (Bestellungen + Eingangsr.)
-- ============================================================
\echo '>>> Füge Einkaufsbelege ein...'

INSERT INTO einkauf.belege
    (id, belegnummer, belegart, lieferant_id, lieferad_id, beleg_datum,
     liefer_datum, zahlungsbedingung_id, status,
     nettobetrag, mwst_betrag, bruttobetrag, bezahlt_am,
     lieferanten_belegnr, notizen, angelegt_von) VALUES
    (1,  'BES-2026-0001', 'BES', 1, NULL, '2026-01-08', '2026-01-15', 2,
         'abgeschlossen', 4340.00, 824.60, 5164.60, NULL,
         'ORD-TDG-2026-0089', NULL, 'petra_schmidt'),
    (2,  'WEI-2026-0001', 'WEI', 1, NULL, '2026-01-15', NULL, 2,
         'abgeschlossen', 4340.00, 824.60, 5164.60, NULL,
         NULL, 'Vollständig eingegangen', 'petra_schmidt'),
    (3,  'ERE-2026-0001', 'ERE', 1, NULL, '2026-01-16', NULL, 2,
         'abgeschlossen', 4340.00, 824.60, 5164.60, '2026-01-28',
         'RE-TDG-2026-0112', NULL, 'petra_schmidt'),
    (4,  'BES-2026-0002', 'BES', 2, NULL, '2026-01-20', '2026-01-27', 3,
         'abgeschlossen', 1248.50, 237.22, 1485.72, NULL,
         NULL, NULL, 'petra_schmidt'),
    (5,  'ERE-2026-0002', 'ERE', 2, NULL, '2026-01-28', NULL, 3,
         'abgeschlossen', 1248.50, 237.22, 1485.72, '2026-02-25',
         'OS-RE-2026-0034', NULL, 'petra_schmidt'),
    (6,  'BES-2026-0003', 'BES', 3, NULL, '2026-02-03', '2026-02-10', 4,
         'abgeschlossen', 8920.00, 1694.80, 10614.80, NULL,
         NULL, 'Notebooks für Kundenauftrag K-0011', 'petra_schmidt'),
    (7,  'WEI-2026-0002', 'WEI', 3, NULL, '2026-02-11', NULL, 4,
         'abgeschlossen', 8920.00, 1694.80, 10614.80, NULL,
         NULL, NULL, 'petra_schmidt'),
    (8,  'ERE-2026-0003', 'ERE', 3, NULL, '2026-02-12', NULL, 4,
         'abgeschlossen', 8920.00, 1694.80, 10614.80, '2026-02-21',
         'NI-RE-2026-0205', NULL, 'petra_schmidt'),
    (9,  'BES-2026-0004', 'BES', 4, NULL, '2026-02-15', '2026-02-22', 2,
         'abgeschlossen', 1560.00, 296.40, 1856.40, NULL,
         NULL, NULL, 'petra_schmidt'),
    (10, 'ERE-2026-0004', 'ERE', 4, NULL, '2026-02-24', NULL, 2,
         'abgeschlossen', 1560.00, 296.40, 1856.40, '2026-03-09',
         'PE-INV-2026-0441', NULL, 'petra_schmidt'),
    (11, 'BES-2026-0005', 'BES', 7, NULL, '2026-03-01', '2026-03-08', 2,
         'abgeschlossen', 980.00, 186.20, 1166.20, NULL,
         NULL, 'Lagerbestand Netzwerkzubehör auffüllen', 'petra_schmidt'),
    (12, 'BES-2026-0006', 'BES', 1, NULL, '2026-03-10', '2026-03-20', 2,
         'offen', 6580.00, 1250.20, 7830.20, NULL,
         NULL, NULL, 'petra_schmidt');

SELECT setval('einkauf.belege_id_seq', 12);

-- Einkaufs-Positionen
INSERT INTO einkauf.positionen
    (id, beleg_id, position, artikel_id, bezeichnung, menge, einheit,
     einzelpreis, rabatt_prozent, mwst_satz, nettobetrag) VALUES
-- BES-2026-0001
    (1,  1, 1, 1,  'Notebook Business 14"',       4,  'Stk', 620.00, 0, 19, 2480.00),
    (2,  1, 2, 9,  'Maus kabellos ergonomisch',   20, 'Stk',  14.50, 0, 19,  290.00),
    (3,  1, 3, 10, 'Tastatur kabellos DE',        20, 'Stk',  19.00, 0, 19,  380.00),
    (4,  1, 4, 14, 'Headset USB Stereo',          10, 'Stk',  25.00, 0, 19,  250.00),
    (5,  1, 5, 17, 'Mauspad XL',                 20, 'Stk',   5.50, 0, 19,  110.00),
    (6,  1, 6, 21, 'Netzwerkkabel Cat.6 5m',      20, 'Stk',   1.80, 0, 19,   36.00),
    (7,  1, 7, 22, 'USB-Hub 7-Port',             10, 'Stk',  11.00, 0, 19,  110.00),
    (8,  1, 8, 18, 'Notebookständer verstellbar', 5, 'Stk',  16.00, 0, 19,   80.00),
    (9,  1, 9, 15, 'Webcam Full HD',              5, 'Stk',  38.00, 0, 19,  190.00),
    (10, 1,10, 16, 'Dockingstation USB-C',        3, 'Stk',  72.00, 0, 19,  216.00),
-- WEI-2026-0001 (identisch mit BES)
    (11, 2, 1, 1,  'Notebook Business 14"',       4,  'Stk', 620.00, 0, 19, 2480.00),
    (12, 2, 2, 9,  'Maus kabellos ergonomisch',  20,  'Stk',  14.50, 0, 19,  290.00),
    (13, 2, 3, 10, 'Tastatur kabellos DE',       20,  'Stk',  19.00, 0, 19,  380.00),
    (14, 2, 4, 14, 'Headset USB Stereo',         10,  'Stk',  25.00, 0, 19,  250.00),
    (15, 2, 5, 17, 'Mauspad XL',                20,  'Stk',   5.50, 0, 19,  110.00),
    (16, 2, 6, 21, 'Netzwerkkabel Cat.6 5m',    20,  'Stk',   1.80, 0, 19,   36.00),
    (17, 2, 7, 22, 'USB-Hub 7-Port',            10,  'Stk',  11.00, 0, 19,  110.00),
    (18, 2, 8, 18, 'Notebookständer verstellbar',5,  'Stk',  16.00, 0, 19,   80.00),
    (19, 2, 9, 15, 'Webcam Full HD',             5,  'Stk',  38.00, 0, 19,  190.00),
    (20, 2,10, 16, 'Dockingstation USB-C',       3,  'Stk',  72.00, 0, 19,  216.00),
-- ERE-2026-0001 (identisch)
    (21, 3, 1, 1,  'Notebook Business 14"',       4, 'Stk', 620.00, 0, 19, 2480.00),
    (22, 3, 2, 9,  'Maus kabellos ergonomisch',  20, 'Stk',  14.50, 0, 19,  290.00),
    (23, 3, 3, 10, 'Tastatur kabellos DE',       20, 'Stk',  19.00, 0, 19,  380.00),
    (24, 3, 4, 14, 'Headset USB Stereo',         10, 'Stk',  25.00, 0, 19,  250.00),
    (25, 3, 5, 17, 'Mauspad XL',                20, 'Stk',   5.50, 0, 19,  110.00),
    (26, 3, 6, 21, 'Netzwerkkabel Cat.6 5m',    20, 'Stk',   1.80, 0, 19,   36.00),
    (27, 3, 7, 22, 'USB-Hub 7-Port',            10, 'Stk',  11.00, 0, 19,  110.00),
    (28, 3, 8, 18, 'Notebookständer verstellbar',5, 'Stk',  16.00, 0, 19,   80.00),
    (29, 3, 9, 15, 'Webcam Full HD',             5, 'Stk',  38.00, 0, 19,  190.00),
    (30, 3,10, 16, 'Dockingstation USB-C',       3, 'Stk',  72.00, 0, 19,  216.00),
-- BES-2026-0002 Bürobedarf
    (31, 4, 1, 25, 'Druckerpapier A4 500 Bl.',  50, 'Pck',   3.20, 0, 19,  160.00),
    (32, 4, 2, 26, 'Druckerpapier A4 Karton',   20, 'Kar',  15.50, 0, 19,  310.00),
    (33, 4, 3, 27, 'Toner schwarz kompatibel',  20, 'Stk',  12.00, 0, 19,  240.00),
    (34, 4, 4, 28, 'Ordner A4 8cm',             80, 'Stk',   1.60, 0, 19,  128.00),
    (35, 4, 5, 29, 'Kugelschreiber Blau 10er',  30, 'Set',   1.20, 0, 19,   36.00),
    (36, 4, 6, 30, 'Haftnotizen 76x76mm',       20, 'Pck',   2.10, 0, 19,   42.00),
-- ERE-2026-0002
    (37, 5, 1, 25, 'Druckerpapier A4 500 Bl.',  50, 'Pck',   3.20, 0, 19,  160.00),
    (38, 5, 2, 26, 'Druckerpapier A4 Karton',   20, 'Kar',  15.50, 0, 19,  310.00),
    (39, 5, 3, 27, 'Toner schwarz kompatibel',  20, 'Stk',  12.00, 0, 19,  240.00),
    (40, 5, 4, 28, 'Ordner A4 8cm',             80, 'Stk',   1.60, 0, 19,  128.00),
    (41, 5, 5, 29, 'Kugelschreiber Blau 10er',  30, 'Set',   1.20, 0, 19,   36.00),
    (42, 5, 6, 30, 'Haftnotizen 76x76mm',       20, 'Pck',   2.10, 0, 19,   42.00),
-- BES-2026-0003 Notebooks für Großauftrag
    (43, 6, 1, 2, 'Notebook Business 15"',      5,  'Stk', 890.00, 0, 19, 4450.00),
    (44, 6, 2, 1, 'Notebook Business 14"',      7,  'Stk', 620.00, 0, 19, 4340.00),
    (45, 7, 1, 2, 'Notebook Business 15"',      5,  'Stk', 890.00, 0, 19, 4450.00),
    (46, 7, 2, 1, 'Notebook Business 14"',      7,  'Stk', 620.00, 0, 19, 4340.00),
    (47, 8, 1, 2, 'Notebook Business 15"',      5,  'Stk', 890.00, 0, 19, 4450.00),
    (48, 8, 2, 1, 'Notebook Business 14"',      7,  'Stk', 620.00, 0, 19, 4340.00),
-- BES-2026-0004 Peripherie
    (49, 9, 1, 12, 'Monitor 24" Full HD',       8,  'Stk', 128.00, 0, 19, 1024.00),
    (50, 9, 2, 11, 'Set Tastatur + Maus kabellos',12,'Stk',  30.00, 0, 19,  360.00),
    (51, 9, 3, 16, 'Dockingstation USB-C',       2,  'Stk',  72.00, 0, 19,  144.00),
    (52,10, 1, 12, 'Monitor 24" Full HD',        8,  'Stk', 128.00, 0, 19, 1024.00),
    (53,10, 2, 11, 'Set Tastatur + Maus kabellos',12,'Stk',  30.00, 0, 19,  360.00),
    (54,10, 3, 16, 'Dockingstation USB-C',        2, 'Stk',  72.00, 0, 19,  144.00),
-- BES-2026-0005 Netzwerk
    (55,11, 1, 20, 'Switch 8-Port Gigabit',     10,  'Stk',  20.00, 0, 19,  200.00),
    (56,11, 2, 21, 'Netzwerkkabel Cat.6 5m',    50,  'Stk',   1.80, 0, 19,   90.00),
    (57,11, 3, 24, 'Netzwerkkabel Cat.6 10m',   50,  'Stk',   2.80, 0, 19,  140.00),
    (58,11, 4, 23, 'USB-C Hub 6-in-1',          10,  'Stk',  15.00, 0, 19,  150.00),
    (59,11, 5, 19, 'WLAN-Router AX1800',         5,  'Stk',  45.00, 0, 19,  225.00),
    (60,11, 6, 22, 'USB-Hub 7-Port',            10,  'Stk',  11.00, 0, 19,  110.00),
-- BES-2026-0006 (offen)
    (61,12, 1, 1, 'Notebook Business 14"',       5,  'Stk', 620.00, 0, 19, 3100.00),
    (62,12, 2, 2, 'Notebook Business 15"',       2,  'Stk', 890.00, 0, 19, 1780.00),
    (63,12, 3, 7, 'Notebook Gaming 17"',         1,  'Stk',1120.00, 0, 19, 1120.00),
    (64,12, 4, 12,'Monitor 24" Full HD',         3,  'Stk', 128.00, 0, 19,  384.00),
    (65,12, 5, 13,'Monitor 27" QHD',             1,  'Stk', 228.00, 0, 19,  228.00);

SELECT setval('einkauf.positionen_id_seq', 65);

\echo '>>> Einkaufsbelege angelegt'

-- ============================================================
-- Verkaufsbelege: 18 Belege
-- ============================================================
\echo '>>> Füge Verkaufsbelege ein...'

INSERT INTO verkauf.belege
    (id, belegnummer, belegart, kunde_id, lieferad_id, beleg_datum,
     liefer_datum, zahlungsbedingung_id, status,
     nettobetrag, mwst_betrag, bruttobetrag, bezahlt_am,
     notizen, angelegt_von) VALUES
-- Angebote
    (1,  'ANG-2026-0001', 'ANG', 9,  9,  '2026-01-05', NULL,        2, 'angenommen',
         2656.80, 504.79, 3161.59, NULL, NULL, 'thomas_mueller'),
    (2,  'ANG-2026-0002', 'ANG', 27, 28, '2026-01-12', NULL,        4, 'angenommen',
         6892.00, 1309.48, 8201.48, NULL, 'Komplettausstattung neues Büro', 'thomas_mueller'),
    (3,  'ANG-2026-0003', 'ANG', 16, 17, '2026-02-01', NULL,        2, 'abgelehnt',
         1198.00, 227.62, 1425.62, NULL, NULL, 'thomas_mueller'),
    (4,  'ANG-2026-0004', 'ANG', 33, 34, '2026-02-10', NULL,        3, 'offen',
         3490.00, 663.10, 4153.10, NULL, 'Schulungsausstattung', 'thomas_mueller'),
-- Aufträge (aus Angeboten)
    (5,  'AUF-2026-0001', 'AUF', 9,  9,  '2026-01-10', '2026-01-17', 2, 'abgeschlossen',
         2656.80, 504.79, 3161.59, NULL, NULL, 'thomas_mueller'),
    (6,  'AUF-2026-0002', 'AUF', 27, 28, '2026-01-15', '2026-01-30', 4, 'abgeschlossen',
         6892.00, 1309.48, 8201.48, NULL, 'Komplettausstattung neues Büro', 'thomas_mueller'),
    (7,  'AUF-2026-0003', 'AUF', 11, 11, '2026-02-05', '2026-02-20', 4, 'abgeschlossen',
         11985.00, 2277.15, 14262.15, NULL, 'Notebook-Fleet 10 Stk + Zubehör', 'thomas_mueller'),
    (8,  'AUF-2026-0004', 'AUF', 18, 19, '2026-02-20', '2026-03-05', 2, 'abgeschlossen',
         1198.10, 227.64, 1425.74, NULL, NULL, 'thomas_mueller'),
    (9,  'AUF-2026-0005', 'AUF', 23, 24, '2026-03-01', '2026-03-10', 3, 'abgeschlossen',
         3248.50, 617.22, 3865.72, NULL, 'Hotel-IT Erstausstattung', 'thomas_mueller'),
    (10, 'AUF-2026-0006', 'AUF', 26, 27, '2026-03-05', '2026-03-15', 2, 'offen',
         1588.00, 301.72, 1889.72, NULL, NULL, 'thomas_mueller'),
-- Rechnungen (aus Aufträgen)
    (11, 'REC-2026-0001', 'REC', 9,  9,  '2026-01-17', NULL, 2, 'abgeschlossen',
         2656.80, 504.79, 3161.59, '2026-01-28', NULL, 'thomas_mueller'),
    (12, 'REC-2026-0002', 'REC', 27, 28, '2026-01-30', NULL, 4, 'abgeschlossen',
         6892.00, 1309.48, 8201.48, '2026-02-08', 'Komplettausstattung neues Büro', 'thomas_mueller'),
    (13, 'REC-2026-0003', 'REC', 11, 11, '2026-02-20', NULL, 4, 'abgeschlossen',
         11985.00, 2277.15, 14262.15, '2026-02-28', NULL, 'thomas_mueller'),
    (14, 'REC-2026-0004', 'REC', 18, 19, '2026-03-05', NULL, 2, 'abgeschlossen',
         1198.10, 227.64, 1425.74, '2026-03-18', NULL, 'thomas_mueller'),
    (15, 'REC-2026-0005', 'REC', 23, 24, '2026-03-10', NULL, 3, 'offen',
         3248.50, 617.22, 3865.72, NULL, NULL, 'thomas_mueller'),
    (16, 'REC-2026-0006', 'REC', 14, 15, '2026-03-12', NULL, 3, 'offen',
          597.10, 113.45,  710.55, NULL, NULL, 'thomas_mueller'),
    (17, 'REC-2026-0007', 'REC', 22, 23, '2026-03-15', NULL, 2, 'offen',
          298.70,  56.75,  355.45, NULL, NULL, 'thomas_mueller'),
    -- Überfällige Rechnung:
    (18, 'REC-2026-0008', 'REC', 13, 14, '2026-01-20', NULL, 3, 'offen',
         1597.10, 303.45, 1900.55, NULL, 'Zahlung trotz Mahnung ausstehend', 'thomas_mueller');

SELECT setval('verkauf.belege_id_seq', 18);

-- Verkaufs-Positionen
INSERT INTO verkauf.positionen
    (id, beleg_id, position, artikel_id, bezeichnung, menge, einheit,
     einzelpreis, rabatt_prozent, mwst_satz, nettobetrag) VALUES
-- ANG-2026-0001
    (1,  1, 1,  1,  'Notebook Business 14"',      2, 'Stk', 899.00, 5.0, 19, 1708.10),
    (2,  1, 2, 11,  'Set Tastatur + Maus kabellos',2, 'Stk',  59.90, 0,   19,  119.80),
    (3,  1, 3, 14,  'Headset USB Stereo',          2, 'Stk',  49.90, 0,   19,   99.80),
    (4,  1, 4, 16,  'Dockingstation USB-C',        2, 'Stk', 119.00, 0,   19,  238.00),
    (5,  1, 5, 38,  'IT-Installation vor Ort',     5, 'Std',  95.00, 0,   19,  475.00),
    (6,  1, 6, 17,  'Mauspad XL',                 2, 'Stk',  14.90, 0,   19,   16.10),
-- AUF-2026-0001 (identisch mit Angebot)
    (7,  5, 1,  1,  'Notebook Business 14"',       2, 'Stk', 899.00, 5.0, 19, 1708.10),
    (8,  5, 2, 11,  'Set Tastatur + Maus kabellos',2, 'Stk',  59.90, 0,   19,  119.80),
    (9,  5, 3, 14,  'Headset USB Stereo',          2, 'Stk',  49.90, 0,   19,   99.80),
    (10, 5, 4, 16,  'Dockingstation USB-C',        2, 'Stk', 119.00, 0,   19,  238.00),
    (11, 5, 5, 38,  'IT-Installation vor Ort',     5, 'Std',  95.00, 0,   19,  475.00),
    (12, 5, 6, 17,  'Mauspad XL',                 2, 'Stk',  14.90, 0,   19,   16.10),
-- REC-2026-0001
    (13,11, 1,  1,  'Notebook Business 14"',       2, 'Stk', 899.00, 5.0, 19, 1708.10),
    (14,11, 2, 11,  'Set Tastatur + Maus kabellos',2, 'Stk',  59.90, 0,   19,  119.80),
    (15,11, 3, 14,  'Headset USB Stereo',          2, 'Stk',  49.90, 0,   19,   99.80),
    (16,11, 4, 16,  'Dockingstation USB-C',        2, 'Stk', 119.00, 0,   19,  238.00),
    (17,11, 5, 38,  'IT-Installation vor Ort',     5, 'Std',  95.00, 0,   19,  475.00),
    (18,11, 6, 17,  'Mauspad XL',                 2, 'Stk',  14.90, 0,   19,   16.10),
-- ANG/AUF-2026-0002 Büroausstattung Werbeagentur
    (19, 2, 1,  2,  'Notebook Business 15"',       5, 'Stk',1299.00, 5,   19, 6170.25),
    (20, 2, 2, 13,  'Monitor 27" QHD',             5, 'Stk', 349.00, 0,   19, 1745.00),
    (21, 2, 3, 11,  'Set Tastatur + Maus kabellos',5, 'Stk',  59.90, 0,   19,  299.50),
    (22, 2, 4, 38,  'IT-Installation vor Ort',     7, 'Std',  95.00, 0,   19,  665.00),
    (23, 6, 1,  2,  'Notebook Business 15"',       5, 'Stk',1299.00, 5,   19, 6170.25),
    (24, 6, 2, 13,  'Monitor 27" QHD',             5, 'Stk', 349.00, 0,   19, 1745.00),
    (25, 6, 3, 11,  'Set Tastatur + Maus kabellos',5, 'Stk',  59.90, 0,   19,  299.50),
    (26, 6, 4, 38,  'IT-Installation vor Ort',     7, 'Std',  95.00, 0,   19,  665.00),
    (27,12, 1,  2,  'Notebook Business 15"',       5, 'Stk',1299.00, 5,   19, 6170.25),
    (28,12, 2, 13,  'Monitor 27" QHD',             5, 'Stk', 349.00, 0,   19, 1745.00),
    (29,12, 3, 11,  'Set Tastatur + Maus kabellos',5, 'Stk',  59.90, 0,   19,  299.50),
    (30,12, 4, 38,  'IT-Installation vor Ort',     7, 'Std',  95.00, 0,   19,  665.00),
-- AUF/REC-2026-0003 Notebooks Innovatech
    (31, 7, 1,  1,  'Notebook Business 14"',       7, 'Stk', 899.00,10,   19, 5673.30),
    (32, 7, 2,  2,  'Notebook Business 15"',       3, 'Stk',1299.00,10,   19, 3507.30),
    (33, 7, 3, 16,  'Dockingstation USB-C',       10, 'Stk', 119.00, 0,   19, 1190.00),
    (34, 7, 4, 38,  'IT-Installation vor Ort',    12, 'Std',  95.00, 0,   19, 1140.00),
    (35, 7, 5, 32,  'Antivirensoftware 1 Jahr',   10, 'Liz',  29.90, 0,   19,  299.00),
    (36, 7, 6, 31,  'Office Paket Jahresabo',     10, 'Liz',  89.00, 0,   19,  890.00),
    (37,13, 1,  1,  'Notebook Business 14"',       7, 'Stk', 899.00,10,   19, 5673.30),
    (38,13, 2,  2,  'Notebook Business 15"',       3, 'Stk',1299.00,10,   19, 3507.30),
    (39,13, 3, 16,  'Dockingstation USB-C',       10, 'Stk', 119.00, 0,   19, 1190.00),
    (40,13, 4, 38,  'IT-Installation vor Ort',    12, 'Std',  95.00, 0,   19, 1140.00),
    (41,13, 5, 32,  'Antivirensoftware 1 Jahr',   10, 'Liz',  29.90, 0,   19,  299.00),
    (42,13, 6, 31,  'Office Paket Jahresabo',     10, 'Liz',  89.00, 0,   19,  890.00),
-- AUF/REC-2026-0004 Versicherungsbüro
    (43, 8, 1, 12,  'Monitor 24" Full HD',         2, 'Stk', 199.00, 0,   19,  398.00),
    (44, 8, 2,  9,  'Maus kabellos ergonomisch',   2, 'Stk',  29.90, 0,   19,   59.80),
    (45, 8, 3, 10,  'Tastatur kabellos DE',         2, 'Stk',  39.90, 0,   19,   79.80),
    (46, 8, 4, 38,  'IT-Installation vor Ort',     7, 'Std',  95.00, 0,   19,  665.00),
    (47,14, 1, 12,  'Monitor 24" Full HD',          2, 'Stk', 199.00, 0,   19,  398.00),
    (48,14, 2,  9,  'Maus kabellos ergonomisch',    2, 'Stk',  29.90, 0,   19,   59.80),
    (49,14, 3, 10,  'Tastatur kabellos DE',          2, 'Stk',  39.90, 0,   19,   79.80),
    (50,14, 4, 38,  'IT-Installation vor Ort',      7, 'Std',  95.00, 0,   19,  665.00),
-- AUF/REC-2026-0005 Hotel
    (51, 9, 1,  1,  'Notebook Business 14"',        2, 'Stk', 899.00, 0,   19, 1798.00),
    (52, 9, 2, 12,  'Monitor 24" Full HD',           3, 'Stk', 199.00, 0,   19,  597.00),
    (53, 9, 3, 19,  'WLAN-Router AX1800',            2, 'Stk',  79.90, 0,   19,  159.80),
    (54, 9, 4, 20,  'Switch 8-Port Gigabit',         2, 'Stk',  39.90, 0,   19,   79.80),
    (55, 9, 5, 38,  'IT-Installation vor Ort',       6, 'Std',  95.00, 0,   19,  570.00),
    (56, 9, 6, 31,  'Office Paket Jahresabo',        3, 'Liz',  89.00, 0,   19,  267.00),
    (57,15, 1,  1,  'Notebook Business 14"',         2, 'Stk', 899.00, 0,   19, 1798.00),
    (58,15, 2, 12,  'Monitor 24" Full HD',            3, 'Stk', 199.00, 0,   19,  597.00),
    (59,15, 3, 19,  'WLAN-Router AX1800',             2, 'Stk',  79.90, 0,   19,  159.80),
    (60,15, 4, 20,  'Switch 8-Port Gigabit',          2, 'Stk',  39.90, 0,   19,   79.80),
    (61,15, 5, 38,  'IT-Installation vor Ort',        6, 'Std',  95.00, 0,   19,  570.00),
    (62,15, 6, 31,  'Office Paket Jahresabo',         3, 'Liz',  89.00, 0,   19,  267.00),
-- REC-2026-0006 Einzelkunde Markus Brandt
    (63,16, 1,  3, 'Notebook Einsteiger 15"',         1, 'Stk', 549.00, 0,   19,  549.00),
    (64,16, 2, 32, 'Antivirensoftware 1 Jahr',        1, 'Liz',  29.90, 0,   19,   29.90),
    (65,16, 3, 38, 'IT-Installation vor Ort',         1.5,'Std',  95.00, 0,   19,  142.50),
-- REC-2026-0007 Zahnarztpraxis
    (66,17, 1, 27, 'Toner schwarz kompatibel',        4, 'Stk',  24.90, 0,   19,   99.60),
    (67,17, 2, 25, 'Druckerpapier A4 500 Bl.',       10, 'Pck',   5.90, 0,   19,   59.00),
    (68,17, 3, 30, 'Haftnotizen 76x76mm',             5, 'Pck',   4.90, 0,   19,   24.50),
    (69,17, 4, 29, 'Kugelschreiber Blau 10er',        4, 'Set',   3.50, 0,   19,   14.00),
    (70,17, 5, 28, 'Ordner A4 8cm',                  12, 'Stk',   3.90, 0,   19,   46.80),
-- AUF-2026-0006 Sprachschule (offen)
    (71,10, 1,  3, 'Notebook Einsteiger 15"',         2, 'Stk', 549.00, 0,   19, 1098.00),
    (72,10, 2, 31, 'Office Paket Jahresabo',          2, 'Liz',  89.00, 0,   19,  178.00),
    (73,10, 3, 38, 'IT-Installation vor Ort',         3, 'Std',  95.00, 0,   19,  285.00),
    (74,10, 4, 32, 'Antivirensoftware 1 Jahr',        2, 'Liz',  29.90, 0,   19,   59.80),
-- REC-2026-0008 überfällig (Steuerkanzlei)
    (75,18, 1,  1, 'Notebook Business 14"',           1, 'Stk', 899.00, 0,   19,  899.00),
    (76,18, 2, 12, 'Monitor 24" Full HD',              1, 'Stk', 199.00, 0,   19,  199.00),
    (77,18, 3, 11, 'Set Tastatur + Maus kabellos',     1, 'Stk',  59.90, 0,   19,   59.90),
    (78,18, 4, 38, 'IT-Installation vor Ort',          4, 'Std',  95.00, 0,   19,  380.00),
    (79,18, 5, 31, 'Office Paket Jahresabo',           3, 'Liz',  89.00, 0,   19,  267.00),
    -- ANG-2026-0003 (abgelehnt)
    (80, 3, 1, 35, 'Laserdrucker Mono A4',             1, 'Stk', 199.00, 0,   19,  199.00),
    (81, 3, 2, 27, 'Toner schwarz kompatibel',         5, 'Stk',  24.90, 0,   19,  124.50),
    (82, 3, 3, 38, 'IT-Installation vor Ort',          9, 'Std',  95.00, 0,   19,  855.00),
    (83, 3, 4, 25, 'Druckerpapier A4 500 Bl.',        10, 'Pck',   5.90, 0,   19,   59.00),
    -- ANG-2026-0004 (offen)
    (84, 4, 1,  3, 'Notebook Einsteiger 15"',          5, 'Stk', 549.00, 0,   19, 2745.00),
    (85, 4, 2, 40, 'Schulung IT-Grundlagen',           1, 'Tag', 490.00, 0,   19,  490.00),
    (86, 4, 3, 31, 'Office Paket Jahresabo',           5, 'Liz',  89.00, 0,   19,  445.00),
    (87, 4, 4, 39, 'IT-Wartungsvertrag Basis',         1, 'Mon',  49.00, 0,   19,   49.00);

SELECT setval('verkauf.positionen_id_seq', 87);

\echo '>>> Verkaufsbelege angelegt'

-- ============================================================
-- Views
-- ============================================================
\echo '>>> Lege Views an...'

CREATE VIEW stammdaten.kunden AS
    SELECT p.id, p.kundennummer, p.firma, p.vorname, p.nachname, p.email,
           p.telefon, p.ust_id, p.aktiv, p.kreditlimit,
           z.bezeichnung AS zahlungsbedingung
    FROM   stammdaten.personen p
    LEFT JOIN stammdaten.zahlungsbedingungen z ON p.zahlungsbedingung_id = z.id
    WHERE  p.typ IN ('kunde', 'beide');

CREATE VIEW stammdaten.lieferanten AS
    SELECT p.id, p.lieferantennummer, p.firma, p.vorname, p.nachname, p.email,
           p.telefon, p.ust_id, p.aktiv,
           z.bezeichnung AS zahlungsbedingung
    FROM   stammdaten.personen p
    LEFT JOIN stammdaten.zahlungsbedingungen z ON p.zahlungsbedingung_id = z.id
    WHERE  p.typ IN ('lieferant', 'beide');

CREATE VIEW stammdaten.artikel_bestand AS
    SELECT a.id, a.artikelnummer, a.bezeichnung, g.bezeichnung AS gruppe,
           a.einheit, a.vk_preis, a.ek_preis,
           a.lagerbestand, a.mindestbestand,
           (a.lagerbestand - a.mindestbestand)  AS bestand_spielraum,
           CASE WHEN a.lagerbestand <= a.mindestbestand
                THEN TRUE ELSE FALSE END        AS nachbestellung_noetig,
           a.aktiv
    FROM   stammdaten.artikel       a
    LEFT JOIN stammdaten.artikelgruppen g ON a.artikelgruppe_id = g.id;

CREATE VIEW verkauf.offene_rechnungen AS
    SELECT b.id, b.belegnummer, b.beleg_datum,
           CURRENT_DATE - b.beleg_datum   AS alter_tage,
           p.kundennummer, COALESCE(p.firma, p.vorname || ' ' || p.nachname) AS kunde,
           z.tage_netto,
           b.beleg_datum + z.tage_netto   AS faellig_am,
           GREATEST(0, (CURRENT_DATE - (b.beleg_datum + z.tage_netto)))
                                          AS tage_ueberfaellig,
           b.bruttobetrag,
           b.notizen
    FROM   verkauf.belege b
    JOIN   stammdaten.personen          p ON b.kunde_id  = p.id
    LEFT JOIN stammdaten.zahlungsbedingungen z ON b.zahlungsbedingung_id = z.id
    WHERE  b.belegart = 'REC'
      AND  b.status   = 'offen'
    ORDER  BY faellig_am;

CREATE VIEW einkauf.bestelluebersicht AS
    SELECT b.id, b.belegnummer, b.belegart, b.beleg_datum, b.status,
           COALESCE(p.firma, p.vorname || ' ' || p.nachname) AS lieferant,
           b.bruttobetrag, b.bezahlt_am,
           b.lieferanten_belegnr
    FROM   einkauf.belege   b
    JOIN   stammdaten.personen p ON b.lieferant_id = p.id
    ORDER  BY b.beleg_datum DESC;

GRANT SELECT ON stammdaten.kunden          TO stammdaten_rolle, verkauf_rolle;
GRANT SELECT ON stammdaten.lieferanten     TO stammdaten_rolle, einkauf_rolle;
GRANT SELECT ON stammdaten.artikel_bestand TO stammdaten_rolle, einkauf_rolle, verkauf_rolle;
GRANT SELECT ON verkauf.offene_rechnungen  TO verkauf_rolle, erp_admin_rolle;
GRANT SELECT ON einkauf.bestelluebersicht  TO einkauf_rolle, erp_admin_rolle;

\echo '>>> Views angelegt'

-- ============================================================
-- Abschlussprüfung
-- ============================================================

\echo ''
\echo '=== ERP-Datenbank Setup abgeschlossen! ==='
\echo ''
SELECT 'Laender:             ' || COUNT(*)::TEXT FROM stammdaten.laender
UNION ALL
SELECT 'Zahlungsbedingungen: ' || COUNT(*) FROM stammdaten.zahlungsbedingungen
UNION ALL
SELECT 'Artikelgruppen:      ' || COUNT(*) FROM stammdaten.artikelgruppen
UNION ALL
SELECT 'Artikel:             ' || COUNT(*) FROM stammdaten.artikel
UNION ALL
SELECT 'Personen gesamt:     ' || COUNT(*) FROM stammdaten.personen
UNION ALL
SELECT '  davon Kunden:      ' || COUNT(*) FROM stammdaten.personen WHERE typ IN ('kunde','beide')
UNION ALL
SELECT '  davon Lieferanten: ' || COUNT(*) FROM stammdaten.personen WHERE typ IN ('lieferant','beide')
UNION ALL
SELECT 'Adressen:            ' || COUNT(*) FROM stammdaten.adressen
UNION ALL
SELECT 'EK-Belege:           ' || COUNT(*) FROM einkauf.belege
UNION ALL
SELECT 'EK-Positionen:       ' || COUNT(*) FROM einkauf.positionen
UNION ALL
SELECT 'VK-Belege:           ' || COUNT(*) FROM verkauf.belege
UNION ALL
SELECT 'VK-Positionen:       ' || COUNT(*) FROM verkauf.positionen;
\echo ''
\echo 'Benutzer und Passwörter:'
\echo '  hans_meier     -> HansPass2026!    (Stammdaten)'
\echo '  petra_schmidt  -> PetraPass2026!   (Einkauf)'
\echo '  thomas_mueller -> ThomasPass2026!  (Verkauf)'
\echo '  erp_admin      -> AdminPass2026!   (Administrator)'
\echo ''
\echo 'Im Notebook: VERBINDUNG["password"] anpassen!'
\echo ''
\echo 'Neue Gruppen-Aufteilung:'
\echo '  Gruppe A: Stammdaten (Personen, Artikel, Artikelgruppen)'
\echo '  Gruppe B: Einkauf    (Lieferanten, Bestellungen, Wareneingänge)'
\echo '  Gruppe C: Verkauf    (Kunden, Angebote, Rechnungen, Reports)'
