"""
Gemeinsame Hilfsfunktionen fuer alle Streamlit-Seiten.
Alle API-Aufrufe laufen ueber diese Datei.
"""
import os
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API = os.getenv("API_URL", "http://localhost:8000")


def api_get(pfad: str, params: dict = None):
    """GET-Anfrage an das Backend. Gibt geparste JSON-Daten zurueck."""
    try:
        antwort = requests.get(f"{API}{pfad}", params=params, timeout=5)
        antwort.raise_for_status()
        return antwort.json()
    except requests.ConnectionError:
        st.error("Backend nicht erreichbar. uvicorn backend.api:app --reload starten.")
        return None
    except requests.HTTPError as e:
        detail = e.response.json().get("detail", str(e)) if e.response else str(e)
        st.error(f"Fehler {e.response.status_code}: {detail}")
        return None


def api_post(pfad: str, daten: dict):
    """POST-Anfrage an das Backend."""
    try:
        antwort = requests.post(f"{API}{pfad}", json=daten, timeout=5)
        antwort.raise_for_status()
        return antwort.json()
    except requests.HTTPError as e:
        detail = e.response.json().get("detail", str(e)) if e.response else str(e)
        st.error(f"Fehler {e.response.status_code}: {detail}")
        return None


def api_put(pfad: str, daten: dict):
    """PUT-Anfrage an das Backend."""
    try:
        antwort = requests.put(f"{API}{pfad}", json=daten, timeout=5)
        antwort.raise_for_status()
        return antwort.json()
    except requests.HTTPError as e:
        detail = e.response.json().get("detail", str(e)) if e.response else str(e)
        st.error(f"Fehler {e.response.status_code}: {detail}")
        return None


def api_patch(pfad: str, daten: dict):
    """PATCH-Anfrage an das Backend."""
    try:
        antwort = requests.patch(f"{API}{pfad}", json=daten, timeout=5)
        antwort.raise_for_status()
        return antwort.json()
    except requests.HTTPError as e:
        detail = e.response.json().get("detail", str(e)) if e.response else str(e)
        st.error(f"Fehler {e.response.status_code}: {detail}")
        return None


def api_delete(pfad: str) -> bool:
    """DELETE-Anfrage an das Backend. Gibt True zurueck wenn 204."""
    try:
        antwort = requests.delete(f"{API}{pfad}", timeout=5)
        return antwort.status_code == 204
    except Exception as e:
        st.error(f"Fehler: {e}")
        return False


@st.cache_data(ttl=300)
def daten_laden(pfad: str, **params) -> pd.DataFrame:
    """Laedt Daten vom Backend und gibt einen DataFrame zurueck. 5 Minuten Cache."""
    ergebnis = api_get(pfad, params=params if params else None)
    return pd.DataFrame(ergebnis) if ergebnis else pd.DataFrame()


def seiten_sidebar():
    """Einheitliche Sidebar mit Unternehmensbranding."""
    with st.sidebar:
        st.markdown(
            """
            <div style="
                background-color: #1E3D59;
                padding: 16px 12px 12px 12px;
                border-radius: 6px;
                margin-bottom: 8px;
            ">
                <div style="color: #FFFFFF; font-size: 15px; font-weight: 700;
                            letter-spacing: 0.3px; line-height: 1.3;">
                    Compu-Global-Hyper-Meganet - ERP
                </div>
                <div style="color: #8FB8D8; font-size: 11px; margin-top: 4px;">
                    ERP-System v1.0
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("---")


def seiten_kopf(titel: str, untertitel: str = ""):
    seiten_sidebar()
    untertitel_html = (
        f'<div style="font-size: 13px; color: #666; margin-top: 2px;">{untertitel}</div>'
        if untertitel else ""
    )
    st.markdown(
        f"""
        <div style="
            border-left: 5px solid #1E3D59;
            padding: 8px 0 8px 16px;
            margin-bottom: 20px;
        ">
            <div style="font-size: 24px; font-weight: 700; color: #1E3D59;">{titel}</div>
            {untertitel_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def download_button(label: str, pfad: str, dateiname: str, mime: str):
    """Laedt eine Datei vom Backend und bietet sie als Download an."""
    try:
        antwort = requests.get(f"{API}{pfad}", timeout=15)
        antwort.raise_for_status()
        st.download_button(
            label=label,
            data=antwort.content,
            file_name=dateiname,
            mime=mime,
            type="primary",
        )
    except Exception as e:
        st.error(f"Export fehlgeschlagen: {e}")
