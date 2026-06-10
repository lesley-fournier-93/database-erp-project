"""
Streamlit-Seite fuer Verkauf.
Uebersicht, Filter, Neuanlage und Statusverwaltung fuer Verkaufsbelege.
"""
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from frontend.utils import daten_laden, api_get, api_post, api_patch, seiten_kopf


# ------------------------------------------------------------
# Session State
# ------------------------------------------------------------
if "verkauf_ansicht" not in st.session_state:
    st.session_state.verkauf_ansicht = "liste"

if "verkauf_beleg_id" not in st.session_state:
    st.session_state.verkauf_beleg_id = None

if "verkauf_erfolg" not in st.session_state:
    st.session_state.verkauf_erfolg = None


seiten_kopf("Verkauf", "Angebote, Aufträge und Rechnungen")


# ------------------------------------------------------------
# LISTENANSICHT
# ------------------------------------------------------------
if st.session_state.verkauf_ansicht == "liste":

    c_neu, c_status, _, c_reload = st.columns([1, 1, 4, 1])

    if c_neu.button("Neu", use_container_width=True):
        st.session_state.verkauf_ansicht = "anlegen"
        st.rerun()

    # Wird nach der Tabellenauswahl befüllt,
    # damit der Button nicht fälschlich ausgegraut bleibt.
    status_button_placeholder = c_status.empty()

    if c_reload.button("Aktualisieren", use_container_width=True):
        st.cache_data.clear()
        st.session_state.verkauf_beleg_id = None
        st.rerun()

    st.divider()

    tab_belege, tab_rechnungen = st.tabs(["Verkaufsbelege", "Offene Rechnungen"])

    # --------------------------------------------------------
    # TAB: VERKAUFSBELEGE
    # --------------------------------------------------------
    with tab_belege:

        f1, f2, f3 = st.columns(3)

        belegart_auswahl = f1.selectbox(
            "Belegart",
            ["Alle", "Angebot", "Auftrag", "Rechnung"],
        )

        status_auswahl = f2.selectbox(
            "Status",
            [
                "Alle",
                "entwurf",
                "offen",
                "angenommen",
                "abgelehnt",
                "teilgeliefert",
                "abgeschlossen",
                "storniert",
            ],
        )

        kunden = daten_laden("/stammdaten/personen", typ="kunde")

        kunden_optionen = {"Alle": None}

        if not kunden.empty:
            for _, row in kunden.iterrows():
                name = row.get("firma") or f"{row.get('vorname', '')} {row.get('nachname', '')}".strip()
                kunden_optionen[f"{name} #{row['id']}"] = int(row["id"])

        kunde_auswahl = f3.selectbox(
            "Kunde",
            list(kunden_optionen.keys()),
        )

        params = {}

        if belegart_auswahl == "Angebot":
            params["belegart"] = "ANG"
        elif belegart_auswahl == "Auftrag":
            params["belegart"] = "AUF"
        elif belegart_auswahl == "Rechnung":
            params["belegart"] = "REC"

        if status_auswahl != "Alle":
            params["status"] = status_auswahl

        kunde_id = kunden_optionen.get(kunde_auswahl)

        if kunde_id:
            params["kunde_id"] = kunde_id

        df = daten_laden("/verkauf/belege", **params)

        # ----------------------------------------------------
        # BELEGLISTE
        # ----------------------------------------------------
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
                    "kunde_name",
                    "kundennummer",
                    "beleg_datum",
                    "status",
                    "nettobetrag",
                    "bruttobetrag",
                    "bezahlt_am",
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
                st.session_state.verkauf_beleg_id = int(
                    df.iloc[auswahl.selection.rows[0]]["id"]
                )
            else:
                st.session_state.verkauf_beleg_id = None

            beleg_ausgewaehlt = st.session_state.verkauf_beleg_id is not None

            # Status-Button wird jetzt NACH der Auswahl gerendert.
            with status_button_placeholder:
                if st.button(
                    "Status ändern",
                    disabled=not beleg_ausgewaehlt,
                    use_container_width=True,
                ):
                    st.session_state.verkauf_ansicht = "status"
                    st.rerun()

            # ------------------------------------------------
            # POSITIONEN ZUM AUSGEWÄHLTEN BELEG
            # ------------------------------------------------
            if st.session_state.verkauf_beleg_id:
                beleg_id = st.session_state.verkauf_beleg_id

                st.caption(f"Ausgewählt: Verkaufsbeleg #{beleg_id}")

                positionen = daten_laden(f"/verkauf/belege/{beleg_id}/positionen")

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
                            "mwst_satz",
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

            st.info("Keine Verkaufsbelege gefunden.")

    # --------------------------------------------------------
    # TAB: OFFENE RECHNUNGEN
    # --------------------------------------------------------
    with tab_rechnungen:

        offene_rechnungen = daten_laden("/verkauf/rechnungen/offen")

        if not offene_rechnungen.empty:
            r1, r2, r3 = st.columns(3)

            r1.metric("Offene Rechnungen", len(offene_rechnungen))

            if "bruttobetrag" in offene_rechnungen.columns:
                r2.metric(
                    "Offene Summe",
                    f"{offene_rechnungen['bruttobetrag'].sum():,.2f} €",
                )
            else:
                r2.metric("Offene Summe", "-")

            if "tage_ueberfaellig" in offene_rechnungen.columns:
                r3.metric(
                    "Überfällig",
                    int((offene_rechnungen["tage_ueberfaellig"] > 0).sum()),
                )
            else:
                r3.metric("Überfällig", "-")

            spalten_rechnung = [
                s for s in [
                    "id",
                    "belegnummer",
                    "beleg_datum",
                    "kundennummer",
                    "kunde",
                    "faellig_am",
                    "tage_ueberfaellig",
                    "bruttobetrag",
                ]
                if s in offene_rechnungen.columns
            ]

            st.dataframe(
                offene_rechnungen[spalten_rechnung],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("Es gibt aktuell keine offenen Rechnungen.")

    if st.session_state.verkauf_erfolg:
        st.success(st.session_state.verkauf_erfolg)
        st.session_state.verkauf_erfolg = None


# ------------------------------------------------------------
# BELEG ANLEGEN
# ------------------------------------------------------------
elif st.session_state.verkauf_ansicht == "anlegen":

    if st.button("Zurück"):
        st.session_state.verkauf_ansicht = "liste"
        st.rerun()

    st.subheader("Neuen Verkaufsbeleg anlegen")

    kunden = daten_laden("/stammdaten/personen", typ="kunde")

    if kunden.empty:
        st.warning("Es sind keine Kunden vorhanden.")
    else:
        kunden_optionen = {}

        for _, row in kunden.iterrows():
            name = row.get("firma") or f"{row.get('vorname', '')} {row.get('nachname', '')}".strip()
            kunden_optionen[f"{name} #{row['id']}"] = int(row["id"])

        with st.form("verkauf_beleg_anlegen"):
            belegart_label = st.selectbox(
                "Belegart",
                ["Angebot", "Auftrag", "Rechnung"],
            )

            kunde_label = st.selectbox(
                "Kunde",
                list(kunden_optionen.keys()),
            )

            notizen = st.text_area("Notizen")

            abschicken = st.form_submit_button("Speichern", type="primary")

        if abschicken:
            belegart_map = {
                "Angebot": "ANG",
                "Auftrag": "AUF",
                "Rechnung": "REC",
            }

            daten = {
                "kunde_id": kunden_optionen[kunde_label],
                "belegart": belegart_map[belegart_label],
            }

            if notizen:
                daten["notizen"] = notizen

            ergebnis = api_post("/verkauf/belege", daten)

            if ergebnis:
                st.cache_data.clear()
                st.session_state.verkauf_ansicht = "liste"
                st.session_state.verkauf_beleg_id = None
                st.session_state.verkauf_erfolg = (
                    f"Verkaufsbeleg {ergebnis.get('belegnummer')} wurde angelegt."
                )
                st.rerun()


# ------------------------------------------------------------
# STATUS ÄNDERN
# ------------------------------------------------------------
elif st.session_state.verkauf_ansicht == "status":

    beleg_id = st.session_state.verkauf_beleg_id

    if st.button("Zurück"):
        st.session_state.verkauf_ansicht = "liste"
        st.rerun()

    if not beleg_id:
        st.warning("Bitte zuerst einen Verkaufsbeleg auswählen.")
        st.session_state.verkauf_ansicht = "liste"
        st.rerun()

    beleg = api_get(f"/verkauf/belege/{beleg_id}")

    if not beleg:
        st.error("Der ausgewählte Verkaufsbeleg konnte nicht geladen werden.")
        st.session_state.verkauf_ansicht = "liste"
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
        "angenommen",
        "abgelehnt",
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
            f"/verkauf/belege/{beleg_id}/status",
            {"status": neuer_status},
        )

        if ergebnis:
            st.cache_data.clear()
            st.session_state.verkauf_ansicht = "liste"
            st.session_state.verkauf_beleg_id = None
            st.session_state.verkauf_erfolg = "Status wurde geändert."
            st.rerun()