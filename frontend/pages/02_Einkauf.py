"""
Streamlit-Seite fuer Einkauf.
Uebersicht, Filter, Neuanlage und Statusverwaltung fuer Einkaufsbelege.
"""
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from frontend.utils import daten_laden, api_get, api_post, api_patch, seiten_kopf


# ------------------------------------------------------------
# Session State
# ------------------------------------------------------------
if "einkauf_ansicht" not in st.session_state:
    st.session_state.einkauf_ansicht = "liste"

if "einkauf_beleg_id" not in st.session_state:
    st.session_state.einkauf_beleg_id = None

if "einkauf_erfolg" not in st.session_state:
    st.session_state.einkauf_erfolg = None


seiten_kopf("Einkauf", "Bestellungen und Lieferantenbelege")


# ------------------------------------------------------------
# LISTENANSICHT
# ------------------------------------------------------------
if st.session_state.einkauf_ansicht == "liste":

    c_neu, c_status, _, c_reload = st.columns([1, 1, 4, 1])

    if c_neu.button("Neu", use_container_width=True):
        st.session_state.einkauf_ansicht = "anlegen"
        st.rerun()

    # Wichtig:
    # Der Button wird erst nach der Tabellenauswahl in diesen Platzhalter gesetzt.
    # Sonst bleibt er ausgegraut, obwohl unten schon ein Beleg ausgewählt wurde.
    status_button_placeholder = c_status.empty()

    if c_reload.button("Aktualisieren", use_container_width=True):
        st.cache_data.clear()
        st.session_state.einkauf_beleg_id = None
        st.rerun()

    st.divider()

    # --------------------------------------------------------
    # FILTER
    # --------------------------------------------------------
    f1, f2, f3 = st.columns(3)

    belegart_auswahl = f1.selectbox(
        "Belegart",
        ["Alle", "Bestellung", "Wareneingang", "Eingangsrechnung"],
    )

    status_auswahl = f2.selectbox(
        "Status",
        ["Alle", "entwurf", "offen", "teilgeliefert", "abgeschlossen", "storniert"],
    )

    lieferanten = daten_laden("/stammdaten/personen", typ="lieferant")

    lieferant_optionen = {"Alle": None}

    if not lieferanten.empty:
        for _, row in lieferanten.iterrows():
            name = row.get("firma") or f"{row.get('vorname', '')} {row.get('nachname', '')}".strip()
            lieferant_optionen[f"{name} #{row['id']}"] = int(row["id"])

    lieferant_auswahl = f3.selectbox(
        "Lieferant",
        list(lieferant_optionen.keys()),
    )

    params = {}

    if belegart_auswahl == "Bestellung":
        params["belegart"] = "BES"
    elif belegart_auswahl == "Wareneingang":
        params["belegart"] = "WEI"
    elif belegart_auswahl == "Eingangsrechnung":
        params["belegart"] = "ERE"

    if status_auswahl != "Alle":
        params["status"] = status_auswahl

    lieferant_id = lieferant_optionen.get(lieferant_auswahl)

    if lieferant_id:
        params["lieferant_id"] = lieferant_id

    df = daten_laden("/einkauf/belege", **params)

    # --------------------------------------------------------
    # BELEGLISTE
    # --------------------------------------------------------
    if not df.empty:
        m1, m2, m3 = st.columns(3)

        m1.metric("Belege gesamt", len(df))

        if "status" in df.columns:
            m2.metric("Offen", int((df["status"] == "offen").sum()))
        else:
            m2.metric("Offen", "-")

        if "bruttobetrag" in df.columns:
            m3.metric("Bruttosumme", f"{df['bruttobetrag'].sum():,.2f} €")
        else:
            m3.metric("Bruttosumme", "-")

        spalten = [
            s for s in [
                "id",
                "belegnummer",
                "belegart",
                "lieferant_name",
                "beleg_datum",
                "status",
                "nettobetrag",
                "bruttobetrag",
                "lieferanten_belegnr",
            ]
            if s in df.columns
        ]

        auswahl = st.dataframe(
            df[spalten],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
        )

        if auswahl.selection.rows:
            st.session_state.einkauf_beleg_id = int(
                df.iloc[auswahl.selection.rows[0]]["id"]
            )
        else:
            st.session_state.einkauf_beleg_id = None

        beleg_ausgewaehlt = st.session_state.einkauf_beleg_id is not None

        # Status-Button wird jetzt NACH der Auswahl gerendert.
        with status_button_placeholder:
            if st.button(
                "Status ändern",
                disabled=not beleg_ausgewaehlt,
                use_container_width=True,
            ):
                st.session_state.einkauf_ansicht = "status"
                st.rerun()

        # ----------------------------------------------------
        # POSITIONEN ZUM AUSGEWÄHLTEN BELEG
        # ----------------------------------------------------
        if st.session_state.einkauf_beleg_id:
            beleg_id = st.session_state.einkauf_beleg_id

            st.caption(f"Ausgewählt: Einkaufsbeleg #{beleg_id}")

            positionen = daten_laden(f"/einkauf/belege/{beleg_id}/positionen")

            st.subheader("Positionen")

            if not positionen.empty:
                pos_spalten = [
                    s for s in [
                        "position",
                        "artikelnummer",
                        "bezeichnung",
                        "menge",
                        "einheit",
                        "einzelpreis",
                        "rabatt_prozent",
                        "nettobetrag",
                    ]
                    if s in positionen.columns
                ]

                st.dataframe(
                    positionen[pos_spalten],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Zu diesem Beleg gibt es keine Positionen.")

    else:
        with status_button_placeholder:
            st.button(
                "Status ändern",
                disabled=True,
                use_container_width=True,
            )

        st.info("Keine Einkaufsbelege gefunden.")

    if st.session_state.einkauf_erfolg:
        st.success(st.session_state.einkauf_erfolg)
        st.session_state.einkauf_erfolg = None


# ------------------------------------------------------------
# BELEG ANLEGEN
# ------------------------------------------------------------
elif st.session_state.einkauf_ansicht == "anlegen":

    if st.button("Zurück"):
        st.session_state.einkauf_ansicht = "liste"
        st.rerun()

    st.subheader("Neuen Einkaufsbeleg anlegen")

    lieferanten = daten_laden("/stammdaten/personen", typ="lieferant")

    if lieferanten.empty:
        st.warning("Es sind keine Lieferanten vorhanden.")
    else:
        lieferant_optionen = {}

        for _, row in lieferanten.iterrows():
            name = row.get("firma") or f"{row.get('vorname', '')} {row.get('nachname', '')}".strip()
            lieferant_optionen[f"{name} #{row['id']}"] = int(row["id"])

        with st.form("einkauf_beleg_anlegen"):
            belegart_label = st.selectbox(
                "Belegart",
                ["Bestellung", "Wareneingang", "Eingangsrechnung"],
            )

            lieferant_label = st.selectbox(
                "Lieferant",
                list(lieferant_optionen.keys()),
            )

            notizen = st.text_area("Notizen")

            abschicken = st.form_submit_button("Speichern", type="primary")

        if abschicken:
            belegart_map = {
                "Bestellung": "BES",
                "Wareneingang": "WEI",
                "Eingangsrechnung": "ERE",
            }

            daten = {
                "lieferant_id": lieferant_optionen[lieferant_label],
                "belegart": belegart_map[belegart_label],
            }

            if notizen:
                daten["notizen"] = notizen

            ergebnis = api_post("/einkauf/belege", daten)

            if ergebnis:
                st.cache_data.clear()
                st.session_state.einkauf_ansicht = "liste"
                st.session_state.einkauf_beleg_id = None
                st.session_state.einkauf_erfolg = (
                    f"Einkaufsbeleg {ergebnis.get('belegnummer')} wurde angelegt."
                )
                st.rerun()


# ------------------------------------------------------------
# STATUS ÄNDERN
# ------------------------------------------------------------
elif st.session_state.einkauf_ansicht == "status":

    beleg_id = st.session_state.einkauf_beleg_id

    if st.button("Zurück"):
        st.session_state.einkauf_ansicht = "liste"
        st.rerun()

    if not beleg_id:
        st.warning("Bitte zuerst einen Einkaufsbeleg auswählen.")
        st.session_state.einkauf_ansicht = "liste"
        st.rerun()

    beleg = api_get(f"/einkauf/belege/{beleg_id}")

    if not beleg:
        st.error("Der ausgewählte Einkaufsbeleg konnte nicht geladen werden.")
        st.session_state.einkauf_ansicht = "liste"
        st.rerun()

    st.subheader(f"Status ändern für Beleg {beleg.get('belegnummer')}")

    col1, col2, col3 = st.columns(3)

    col1.metric("Belegart", beleg.get("belegart", "-"))
    col2.metric("Aktueller Status", beleg.get("status", "-"))

    if beleg.get("bruttobetrag") is not None:
        col3.metric("Bruttobetrag", f"{beleg.get('bruttobetrag'):,.2f} €")
    else:
        col3.metric("Bruttobetrag", "-")

    aktueller_status = beleg.get("status", "offen")

    status_liste = [
        "entwurf",
        "offen",
        "teilgeliefert",
        "abgeschlossen",
        "storniert",
    ]

    neuer_status = st.selectbox(
        "Neuer Status",
        status_liste,
        index=status_liste.index(aktueller_status)
        if aktueller_status in status_liste
        else 1,
    )

    if st.button("Status speichern", type="primary"):
        ergebnis = api_patch(
            f"/einkauf/belege/{beleg_id}/status",
            {"status": neuer_status},
        )

        if ergebnis:
            st.cache_data.clear()
            st.session_state.einkauf_ansicht = "liste"
            st.session_state.einkauf_beleg_id = None
            st.session_state.einkauf_erfolg = "Status wurde geändert."
            st.rerun()