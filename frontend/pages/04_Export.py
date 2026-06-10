"""
Streamlit-Seite fuer Export.
Exportiert Stammdaten, offene Bestellungen und einzelne Rechnungen.
"""
import streamlit as st
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from frontend.utils import daten_laden, seiten_kopf, download_button


seiten_kopf("Export", "Datenexport für externe Systeme")

st.write(
    "Hier können Stammdaten, offene Bestellungen und Rechnungen "
    "als JSON, CSV oder XML exportiert werden."
)

st.divider()


# ------------------------------------------------------------
# STAMMDATEN EXPORT
# ------------------------------------------------------------
st.subheader("Stammdaten exportieren")

c1, c2 = st.columns(2)

with c1:
    st.markdown("**Personenstammdaten**")
    st.caption("Exportiert alle aktiven Kunden und Lieferanten als JSON-Datei.")

    download_button(
        label="Personen als JSON exportieren",
        pfad="/export/personen.json",
        dateiname=f"personen_{date.today()}.json",
        mime="application/json",
    )

with c2:
    st.markdown("**Artikelstammdaten**")
    st.caption("Exportiert alle aktiven Artikel als CSV-Datei für Excel.")

    download_button(
        label="Artikel als CSV exportieren",
        pfad="/export/artikel.csv",
        dateiname=f"artikel_{date.today()}.csv",
        mime="text/csv",
    )


st.divider()


# ------------------------------------------------------------
# EINKAUF EXPORT
# ------------------------------------------------------------
st.subheader("Einkauf exportieren")

st.markdown("**Offene Bestellungen**")
st.caption("Exportiert alle offenen Einkaufsbestellungen inklusive Positionen als JSON-Datei.")

download_button(
    label="Offene Bestellungen als JSON exportieren",
    pfad="/export/bestellungen.json",
    dateiname=f"bestellungen_{date.today()}.json",
    mime="application/json",
)


st.divider()


# ------------------------------------------------------------
# RECHNUNG EXPORT
# ------------------------------------------------------------
st.subheader("Rechnung als XML exportieren")

st.caption(
    "Wähle eine Verkaufsrechnung aus und exportiere sie als XML-Datei "
    "für externe Buchhaltungssoftware."
)

# Wichtig: Backend verwendet fuer Rechnungen wahrscheinlich REC.
rechnungen = daten_laden("/verkauf/belege", belegart="REC")

# Fallback, falls eure Gruppe stattdessen RE verwendet hat.
if rechnungen.empty:
    rechnungen = daten_laden("/verkauf/belege", belegart="RE")

if rechnungen.empty:
    st.info("Es wurden keine Rechnungen gefunden.")
else:
    optionen = {}

    for _, row in rechnungen.iterrows():
        kunde = row.get("kunde_name", "")
        belegnummer = row.get("belegnummer", "")
        brutto = row.get("bruttobetrag", 0)

        label = f"{belegnummer} | {kunde} | {brutto:,.2f} €"
        optionen[label] = int(row["id"])

    auswahl = st.selectbox(
        "Rechnung auswählen",
        list(optionen.keys())
    )

    beleg_id = optionen[auswahl]

    download_button(
        label="Ausgewählte Rechnung als XML exportieren",
        pfad=f"/export/rechnung/{beleg_id}.xml",
        dateiname=f"rechnung_{beleg_id}.xml",
        mime="application/xml",
    )