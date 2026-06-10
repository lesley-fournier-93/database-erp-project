"""
Streamlit-Seite fuer Reporting.
Zeigt Umsatz, Top-Kunden, Top-Artikel, Lagerwarnungen und Lieferantenvolumen.
"""
import streamlit as st
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from frontend.utils import daten_laden, seiten_kopf


seiten_kopf("Reporting", "Kennzahlen, Auswertungen und Diagramme")


# ------------------------------------------------------------
# FILTER
# ------------------------------------------------------------
with st.sidebar:
    st.subheader("Filter")

    monate = st.slider(
        "Zeitraum für Umsatz",
        min_value=1,
        max_value=60,
        value=12,
        step=1
    )

    limit = st.slider(
        "Anzahl Top-Einträge",
        min_value=3,
        max_value=20,
        value=10,
        step=1
    )


if st.button("Daten aktualisieren"):
    st.cache_data.clear()
    st.rerun()


st.divider()


# ------------------------------------------------------------
# DATEN LADEN
# ------------------------------------------------------------
umsatz = daten_laden("/reporting/umsatz/monatlich", monate=monate)
kunden = daten_laden("/reporting/kunden/top", limit=limit)
artikel = daten_laden("/reporting/artikel/topverkauf", limit=limit)
lager = daten_laden("/reporting/lager/warnung")
lieferanten = daten_laden("/reporting/lieferanten/volumen")


# ------------------------------------------------------------
# KPI-KARTEN
# ------------------------------------------------------------
st.subheader("Kennzahlen-Übersicht")

k1, k2, k3, k4 = st.columns(4)

gesamtumsatz = 0
wachstum = None
offene_lagerwarnungen = 0
lieferanten_volumen = 0

if not umsatz.empty and "umsatz" in umsatz.columns:
    gesamtumsatz = umsatz["umsatz"].sum()

    if "wachstum_proz" in umsatz.columns:
        wachstum_werte = umsatz["wachstum_proz"].dropna()
        if not wachstum_werte.empty:
            wachstum = wachstum_werte.iloc[-1]

if not lager.empty:
    offene_lagerwarnungen = len(lager)

if not lieferanten.empty and "gesamtvolumen" in lieferanten.columns:
    lieferanten_volumen = lieferanten["gesamtvolumen"].sum()

k1.metric("Umsatz gesamt", f"{gesamtumsatz:,.2f} €")

if wachstum is not None:
    k2.metric("Wachstum letzter Monat", f"{wachstum:.1f} %")
else:
    k2.metric("Wachstum letzter Monat", "-")

k3.metric("Lagerwarnungen", offene_lagerwarnungen)
k4.metric("Einkaufsvolumen", f"{lieferanten_volumen:,.2f} €")


st.divider()


# ------------------------------------------------------------
# UMSATZ REPORTING
# ------------------------------------------------------------
st.subheader("Monatlicher Umsatz")

if umsatz.empty:
    st.info("Keine Umsatzdaten vorhanden.")
else:
    df_umsatz = umsatz.copy()

    if "monat" in df_umsatz.columns:
        df_umsatz = df_umsatz.set_index("monat")

    chart_spalten = [s for s in ["umsatz", "kumuliert"] if s in df_umsatz.columns]

    if chart_spalten:
        st.bar_chart(df_umsatz[chart_spalten])

    anzeigen = [
        s for s in [
            "monat",
            "umsatz",
            "vormonat",
            "wachstum_proz",
            "kumuliert",
        ]
        if s in umsatz.columns
    ]

    st.dataframe(
        umsatz[anzeigen],
        use_container_width=True,
        hide_index=True
    )


st.divider()


# ------------------------------------------------------------
# TOP-KUNDEN UND TOP-ARTIKEL
# ------------------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("Top-Kunden")

    if kunden.empty:
        st.info("Keine Kundendaten vorhanden.")
    else:
        df_kunden = kunden.copy()

        if "kunde" in df_kunden.columns and "umsatz" in df_kunden.columns:
            st.bar_chart(df_kunden.set_index("kunde")["umsatz"])

        anzeigen = [
            s for s in [
                "rang",
                "kunde",
                "kundennummer",
                "segment",
                "umsatz",
            ]
            if s in kunden.columns
        ]

        st.dataframe(
            kunden[anzeigen],
            use_container_width=True,
            hide_index=True
        )

with c2:
    st.subheader("Top-Artikel")

    if artikel.empty:
        st.info("Keine Artikeldaten vorhanden.")
    else:
        df_artikel = artikel.copy()

        if "artikel" in df_artikel.columns and "umsatz_netto" in df_artikel.columns:
            st.bar_chart(df_artikel.set_index("artikel")["umsatz_netto"])

        anzeigen = [
            s for s in [
                "rang",
                "artikelnummer",
                "artikel",
                "gruppe",
                "menge_gesamt",
                "umsatz_netto",
            ]
            if s in artikel.columns
        ]

        st.dataframe(
            artikel[anzeigen],
            use_container_width=True,
            hide_index=True
        )


st.divider()


# ------------------------------------------------------------
# LAGERWARNUNGEN
# ------------------------------------------------------------
st.subheader("Lagerwarnungen")

if lager.empty:
    st.success("Es gibt aktuell keine Lagerwarnungen.")
else:
    dringlichkeit_reihenfolge = {
        "KRITISCH": 1,
        "HOCH": 2,
        "NORMAL": 3,
    }

    lager_sortiert = lager.copy()

    if "dringlichkeit" in lager_sortiert.columns:
        lager_sortiert["sortierung"] = lager_sortiert["dringlichkeit"].map(
            dringlichkeit_reihenfolge
        ).fillna(99)

        lager_sortiert = lager_sortiert.sort_values(
            by=["sortierung", "fehlmenge"],
            ascending=[True, False]
        )

    anzeigen = [
        s for s in [
            "artikelnummer",
            "bezeichnung",
            "gruppe",
            "lagerbestand",
            "mindestbestand",
            "fehlmenge",
            "bestellwert_eur",
            "dringlichkeit",
        ]
        if s in lager_sortiert.columns
    ]

    st.dataframe(
        lager_sortiert[anzeigen],
        use_container_width=True,
        hide_index=True
    )


st.divider()


# ------------------------------------------------------------
# LIEFERANTENVOLUMEN
# ------------------------------------------------------------
st.subheader("Lieferantenvolumen")

if lieferanten.empty:
    st.info("Keine Lieferantendaten vorhanden.")
else:
    df_lieferanten = lieferanten.copy()

    if "lieferant" in df_lieferanten.columns and "gesamtvolumen" in df_lieferanten.columns:
        st.bar_chart(df_lieferanten.set_index("lieferant")["gesamtvolumen"])

    anzeigen = [
        s for s in [
            "lieferant",
            "lieferantennummer",
            "bestellungen",
            "gesamtvolumen",
            "anteil_proz",
        ]
        if s in lieferanten.columns
    ]

    st.dataframe(
        lieferanten[anzeigen],
        use_container_width=True,
        hide_index=True
    )