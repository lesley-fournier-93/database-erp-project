"""
Streamlit-Seite fuer Stammdaten (Gruppe A).
Vollstaendiges CRUD fuer Personen und Artikeluebersicht.
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from frontend.utils import daten_laden, api_get, api_post, api_put, api_delete, seiten_kopf

if "ansicht"        not in st.session_state: st.session_state.ansicht        = "liste"
if "ausgewaehlt_id" not in st.session_state: st.session_state.ausgewaehlt_id = None

seiten_kopf("Stammdaten", "Personen und Artikel")
tab_p, tab_a = st.tabs(["Personen", "Artikel"])


# ================================================================
# TAB: PERSONEN
# ================================================================
with tab_p:

    if st.session_state.ansicht == "liste":

        c_neu, c_bear, c_deak, _, c_rel = st.columns([1,1,1,4,1])
        if c_neu.button("Neu", use_container_width=True):
            st.session_state.ansicht = "anlegen"
            st.rerun()
        aktiv = st.session_state.ausgewaehlt_id is not None
        if c_bear.button("Bearbeiten",  disabled=not aktiv, use_container_width=True):
            st.session_state.ansicht = "bearbeiten"
            st.rerun()
        if c_deak.button("Deaktivieren", disabled=not aktiv, use_container_width=True):
            st.session_state.ansicht = "deaktivieren"
            st.rerun()
        if c_rel.button("Aktualisieren", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        c1, c2, c3 = st.columns([3,1,1])
        suche = c1.text_input("Suche:", placeholder="Firma oder Name")
        typ   = c2.selectbox("Typ:", ["Alle","Kunden","Lieferanten"])
        st.write("")

        params = {}
        if typ == "Kunden":       params["typ"] = "kunde"
        elif typ == "Lieferanten": params["typ"] = "lieferant"

        if suche and len(suche.strip()) >= 2:
            df = daten_laden("/stammdaten/personen/suche", q=suche.strip())
        else:
            df = daten_laden("/stammdaten/personen", **params)

        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Gesamt", len(df))
            if "typ" in df.columns:
                c2.metric("Kunden",      df["typ"].isin(["kunde","beide"]).sum())
                c3.metric("Lieferanten", df["typ"].isin(["lieferant","beide"]).sum())

            spalten = [s for s in ["id","typ","kundennummer","lieferantennummer",
                                    "firma","nachname","vorname","email","telefon"]
                       if s in df.columns]
            auswahl = st.dataframe(
                df[spalten], use_container_width=True, hide_index=True,
                on_select="rerun", selection_mode="single-row",
            )
            if auswahl.selection.rows:
                st.session_state.ausgewaehlt_id = int(df.iloc[auswahl.selection.rows[0]]["id"])
            else:
                st.session_state.ausgewaehlt_id = None

            if st.session_state.ausgewaehlt_id:
                st.caption(f"Ausgewaehlt: Person #{st.session_state.ausgewaehlt_id}")
        else:
            st.info("Keine Personen gefunden.")

        if "erfolgsmeldung" in st.session_state:
            st.success(st.session_state.pop("erfolgsmeldung"))

    # ANLEGEN
    elif st.session_state.ansicht == "anlegen":
        if st.button("Zurück"):
            st.session_state.ansicht = "liste"
            st.rerun()
        st.subheader("Neue Person anlegen")
        with st.form("anlegen"):
            typ = st.selectbox("Typ *", ["kunde","lieferant","beide"])
            c1, c2 = st.columns(2)
            firma    = c1.text_input("Firma")
            email    = c2.text_input("E-Mail *")
            vorname  = c1.text_input("Vorname")
            nachname = c2.text_input("Nachname")
            telefon  = c1.text_input("Telefon")
            kreditlimit = c2.number_input("Kreditlimit (EUR)", min_value=0.0,
                                           value=5000.0, step=500.0)
            abschicken = st.form_submit_button("Speichern", type="primary")
        if abschicken:
            fehler = []
            if not email: fehler.append("E-Mail ist erforderlich.")
            if not firma and not (vorname and nachname):
                fehler.append("Firma oder Vorname + Nachname angeben.")
            if fehler:
                for f in fehler: st.error(f)
            else:
                daten = {"typ": typ, "email": email, "kreditlimit": kreditlimit}
                if firma:    daten["firma"]    = firma
                if vorname:  daten["vorname"]  = vorname
                if nachname: daten["nachname"] = nachname
                if telefon:  daten["telefon"]  = telefon
                ergebnis = api_post("/stammdaten/personen", daten)
                if ergebnis:
                    st.cache_data.clear()
                    st.session_state.ansicht = "liste"
                    st.session_state.erfolgsmeldung = f"Person angelegt (ID {ergebnis['id']})."
                    st.rerun()

    # BEARBEITEN
    elif st.session_state.ansicht == "bearbeiten":
        pid = st.session_state.ausgewaehlt_id
        if st.button("Zurück"):
            st.session_state.ansicht = "liste"
            st.rerun()
        daten = api_get(f"/stammdaten/personen/{pid}")
        if not daten:
            st.session_state.ansicht = "liste"
            st.rerun()
        st.subheader(f"Person #{pid} bearbeiten")
        with st.form("bearbeiten"):
            c1, c2 = st.columns(2)
            firma    = c1.text_input("Firma",    value=daten.get("firma","")    or "")
            email    = c2.text_input("E-Mail",   value=daten.get("email","")    or "")
            vorname  = c1.text_input("Vorname",  value=daten.get("vorname","")  or "")
            nachname = c2.text_input("Nachname", value=daten.get("nachname","") or "")
            telefon  = c1.text_input("Telefon",  value=daten.get("telefon","")  or "")
            abschicken = st.form_submit_button("Speichern", type="primary")
        if abschicken:
            aenderungen = {}
            if firma    != (daten.get("firma","")    or ""): aenderungen["firma"]    = firma or None
            if email    != (daten.get("email","")    or ""): aenderungen["email"]    = email
            if vorname  != (daten.get("vorname","")  or ""): aenderungen["vorname"]  = vorname or None
            if nachname != (daten.get("nachname","") or ""): aenderungen["nachname"] = nachname or None
            if telefon  != (daten.get("telefon","")  or ""): aenderungen["telefon"]  = telefon or None
            if not aenderungen:
                st.info("Keine Änderungen vorgenommen.")
            else:
                ergebnis = api_put(f"/stammdaten/personen/{pid}", aenderungen)
                if ergebnis:
                    st.cache_data.clear()
                    st.session_state.ansicht = "liste"
                    st.session_state.erfolgsmeldung = "Aenderungen gespeichert."
                    st.rerun()

    # DEAKTIVIEREN
    elif st.session_state.ansicht == "deaktivieren":
        pid   = st.session_state.ausgewaehlt_id
        daten = api_get(f"/stammdaten/personen/{pid}")
        name  = (daten.get("firma") or
                 f"{daten.get('vorname','')} {daten.get('nachname','')}".strip()
                 ) if daten else f"#{pid}"
        if st.button("Abbrechen"):
            st.session_state.ansicht = "liste"
            st.rerun()
        st.warning(f"Person '{name}' (#{pid}) deaktivieren? Daten bleiben erhalten.")
        if st.button("Ja, deaktivieren", type="primary"):
            if api_delete(f"/stammdaten/personen/{pid}"):
                st.cache_data.clear()
                st.session_state.ansicht          = "liste"
                st.session_state.ausgewaehlt_id   = None
                st.session_state.erfolgsmeldung   = f"Person '{name}' deaktiviert."
                st.rerun()


# ================================================================
# TAB: ARTIKEL
# ================================================================
with tab_a:
    c1, c2, _ = st.columns([1,1,3])
    nur_aktive = c1.checkbox("Nur aktive", value=True)
    if c2.button("Aktualisieren", key="art_reload"):
        st.cache_data.clear()
        st.rerun()

    df_a = daten_laden("/stammdaten/artikel", nur_aktive=str(nur_aktive).lower())
    if not df_a.empty:
        if "lagerbestand" in df_a.columns and "mindestbestand" in df_a.columns:
            nachbest = (df_a["lagerbestand"] <= df_a["mindestbestand"]).sum()
            c1, c2 = st.columns(2)
            c1.metric("Artikel gesamt",      len(df_a))
            c2.metric("Nachbestellung noetig", int(nachbest))

        spalten = [s for s in ["artikelnummer","bezeichnung","gruppe","einheit",
                                "vk_preis","ek_preis","lagerbestand","mindestbestand"]
                   if s in df_a.columns]
        st.dataframe(df_a[spalten], hide_index=True, use_container_width=True)
    else:
        st.info("Keine Artikel gefunden.")
