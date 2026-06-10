"""
ERP-Startseite: Kennzahlen-Dashboard.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
from frontend.utils import daten_laden, seiten_sidebar

st.set_page_config(
    page_title="Compu-Global-Hyper-Meganet - ERP",
    layout="wide",
    initial_sidebar_state="expanded",
)

seiten_sidebar()

st.markdown(
    """
    <div style="
        border-left: 5px solid #1E3D59;
        padding: 8px 0 8px 16px;
        margin-bottom: 20px;
    ">
        <div style="font-size: 24px; font-weight: 700; color: #1E3D59;">
            Kennzahlen-Übersicht
        </div>
        <div style="font-size: 13px; color: #666; margin-top: 2px;">
            Compu-Global-Hyper-Meganet - ERP
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


c1, c2, c3, c4, c5 = st.columns(5)

df_p = daten_laden("/stammdaten/personen")
if not df_p.empty:
    kunden    = df_p["typ"].isin(["kunde","beide"]).sum() if "typ" in df_p else 0
    lieferant = df_p["typ"].isin(["lieferant","beide"]).sum() if "typ" in df_p else 0
    c1.metric("Kunden",      kunden)
    c2.metric("Lieferanten", lieferant)

df_e = daten_laden("/einkauf/belege", belegart="BES", status="offen")
if not df_e.empty:
    c3.metric("Offene Bestellungen", len(df_e))

df_r = daten_laden("/verkauf/rechnungen/offen")
if not df_r.empty:
    ueberfaellig = (df_r["tage_ueberfaellig"] > 0).sum() if "tage_ueberfaellig" in df_r.columns else 0
    summe        = df_r["bruttobetrag"].sum()             if "bruttobetrag"       in df_r.columns else 0
    c4.metric("Offene Rechnungen",  len(df_r))
    c5.metric("Davon überfällig",   int(ueberfaellig))

st.divider()

df_a = daten_laden("/stammdaten/artikel/nachbestellung")
if not df_a.empty:
    st.warning(f"{len(df_a)} Artikel benötigen Nachbestellung.")
    spalten = [s for s in ["artikelnummer","bezeichnung","gruppe",
                            "lagerbestand","mindestbestand","fehlmenge"]
               if s in df_a.columns]
    st.dataframe(df_a[spalten], hide_index=True, use_container_width=True)

if st.button("Daten aktualisieren"):
    st.cache_data.clear()
    st.rerun()
