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


# -----------------------------------------------------------------------------
# Modernes UI / Branding
# -----------------------------------------------------------------------------
def apply_modern_theme():
    """Zentrales Styling fuer ein modernes, vorzeigbares Streamlit-Frontend."""
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

            :root {
                --bg: #f6f8fb;
                --card: #ffffff;
                --ink: #0f172a;
                --muted: #64748b;
                --line: #e2e8f0;
                --brand: #0f3d56;
                --brand-2: #0ea5e9;
                --brand-soft: #e0f2fe;
                --success-soft: #ecfdf5;
                --warning-soft: #fffbeb;
                --shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
            }

            html, body, [class*="css"] {
                font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            }

            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(14, 165, 233, 0.12), transparent 34rem),
                    linear-gradient(180deg, #f8fafc 0%, #f6f8fb 100%);
                color: var(--ink);
            }

            .block-container {
                max-width: 1240px;
                padding-top: 2.5rem;
                padding-bottom: 4rem;
            }

            section[data-testid="stSidebar"] {
                background: linear-gradient(180deg, #f8fafc 0%, #eef4fb 100%);
                border-right: 1px solid rgba(148, 163, 184, 0.24);
            }

            section[data-testid="stSidebar"] > div {
                padding-top: 1.2rem;
            }

            /* Native Streamlit-Seitennavigation ausblenden, damit die Sidebar sauber gebrandet ist. */
            [data-testid="stSidebarNav"] {
                display: none;
            }

            .erp-sidebar-brand {
                background: linear-gradient(135deg, #0f3d56 0%, #0f766e 100%);
                color: white;
                padding: 18px 16px;
                border-radius: 18px;
                box-shadow: 0 18px 40px rgba(15, 61, 86, 0.22);
                margin-bottom: 18px;
            }

            .erp-sidebar-logo {
                width: 42px;
                height: 42px;
                display: grid;
                place-items: center;
                border-radius: 14px;
                background: rgba(255, 255, 255, 0.16);
                border: 1px solid rgba(255, 255, 255, 0.18);
                font-size: 22px;
                margin-bottom: 14px;
            }

            .erp-sidebar-title {
                font-size: 15px;
                font-weight: 800;
                letter-spacing: -0.01em;
                line-height: 1.25;
            }

            .erp-sidebar-subtitle {
                color: rgba(255, 255, 255, 0.72);
                font-size: 12px;
                font-weight: 500;
                margin-top: 5px;
            }

            .erp-nav-label {
                color: #64748b;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: .12em;
                text-transform: uppercase;
                margin: 6px 0 8px 4px;
            }

            [data-testid="stSidebar"] [data-testid="stPageLink"] a {
                border-radius: 13px;
                padding: 0.55rem 0.75rem;
                color: #0f172a;
                font-weight: 700;
                text-decoration: none;
                transition: all .16s ease;
            }

            [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
                background: rgba(14, 165, 233, 0.12);
                transform: translateX(2px);
            }

            .erp-hero {
                background:
                    linear-gradient(135deg, rgba(15, 61, 86, 0.97) 0%, rgba(14, 116, 144, 0.94) 52%, rgba(14, 165, 233, 0.92) 100%);
                color: white;
                border-radius: 28px;
                padding: 30px 34px;
                margin-bottom: 26px;
                box-shadow: var(--shadow);
                overflow: hidden;
                position: relative;
            }

            .erp-hero:after {
                content: "";
                position: absolute;
                width: 260px;
                height: 260px;
                right: -85px;
                top: -110px;
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.14);
            }

            .erp-eyebrow {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 7px 11px;
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.14);
                border: 1px solid rgba(255, 255, 255, 0.16);
                font-size: 12px;
                font-weight: 800;
                letter-spacing: .08em;
                text-transform: uppercase;
                margin-bottom: 14px;
            }

            .erp-hero h1 {
                color: white !important;
                font-size: clamp(30px, 4vw, 46px);
                line-height: 1.04;
                letter-spacing: -0.04em;
                margin: 0;
                font-weight: 800;
            }

            .erp-hero p {
                color: rgba(255, 255, 255, 0.78);
                font-size: 15px;
                margin: 10px 0 0 0;
                max-width: 720px;
            }

            div[data-testid="stMetric"] {
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid rgba(226, 232, 240, 0.9);
                border-radius: 20px;
                padding: 18px 18px;
                box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
            }

            div[data-testid="stMetricLabel"] p {
                color: var(--muted);
                font-weight: 700;
                font-size: 13px;
            }

            div[data-testid="stMetricValue"] {
                color: var(--ink);
                font-weight: 800;
                letter-spacing: -0.03em;
            }

            .stButton > button,
            .stDownloadButton > button,
            button[kind="primary"] {
                border-radius: 13px !important;
                font-weight: 800 !important;
                border: 1px solid rgba(15, 61, 86, .16) !important;
                box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
                transition: all .15s ease;
            }

            .stButton > button:hover,
            .stDownloadButton > button:hover {
                transform: translateY(-1px);
                box-shadow: 0 12px 24px rgba(15, 23, 42, 0.10);
            }

            div[data-testid="stDataFrame"] {
                border-radius: 18px;
                overflow: hidden;
                border: 1px solid rgba(226, 232, 240, 0.95);
                box-shadow: 0 10px 25px rgba(15, 23, 42, 0.045);
            }

            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
                background: rgba(255,255,255,.75);
                padding: 7px;
                border-radius: 16px;
                border: 1px solid rgba(226, 232, 240, .9);
            }

            .stTabs [data-baseweb="tab"] {
                border-radius: 12px;
                font-weight: 800;
                padding: 8px 14px;
            }

            .stTextInput input,
            .stSelectbox div[data-baseweb="select"] > div,
            .stNumberInput input,
            .stTextArea textarea {
                border-radius: 12px !important;
                border-color: rgba(148, 163, 184, .35) !important;
            }

            hr {
                margin: 1.7rem 0;
                border-color: rgba(226, 232, 240, .9);
            }

            h2, h3 {
                letter-spacing: -0.02em;
                color: #0f172a;
            }

            .erp-page-note {
                background: rgba(255, 255, 255, .84);
                border: 1px solid rgba(226, 232, 240, .9);
                border-radius: 18px;
                padding: 16px 18px;
                color: #475569;
                box-shadow: 0 10px 25px rgba(15, 23, 42, .04);
            }

            .erp-stack-card {
                margin-top: 18px;
                padding: 14px;
                border-radius: 18px;
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(226, 232, 240, 0.95);
                box-shadow: 0 12px 26px rgba(15, 23, 42, 0.045);
            }

            .erp-stack-title {
                display: flex;
                align-items: center;
                justify-content: space-between;
                color: #0f172a;
                font-size: 12px;
                font-weight: 850;
                letter-spacing: .02em;
                margin-bottom: 10px;
            }

            .erp-status-dot {
                width: 8px;
                height: 8px;
                border-radius: 999px;
                background: #22c55e;
                box-shadow: 0 0 0 5px rgba(34, 197, 94, .13);
            }

            .erp-stack-grid {
                display: flex;
                flex-wrap: wrap;
                gap: 7px;
            }

            .erp-stack-pill {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 7px 9px;
                border-radius: 999px;
                background: #f8fafc;
                border: 1px solid rgba(226, 232, 240, 0.95);
                color: #334155;
                font-size: 11px;
                font-weight: 750;
                white-space: nowrap;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
    """Einheitliche Sidebar mit Unternehmensbranding und eigener Navigation."""
    apply_modern_theme()
    with st.sidebar:
        st.markdown(
            """
            <div class="erp-sidebar-brand">
                <div class="erp-sidebar-logo">⚡</div>
                <div class="erp-sidebar-title">Compu-Global-Hyper-Meganet</div>
                <div class="erp-sidebar-subtitle">ERP-System v1.0 · Portfolio Project</div>
            </div>
            <div class="erp-nav-label">Navigation</div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link("streamlit_app.py", label="Home", icon="🏠")
        st.page_link("pages/01_Stammdaten.py", label="Stammdaten", icon="👥")
        st.page_link("pages/02_Einkauf.py", label="Einkauf", icon="🛒")
        st.page_link("pages/03_Verkauf.py", label="Verkauf", icon="🧾")
        st.page_link("pages/04_Export.py", label="Export", icon="📤")
        st.page_link("pages/05_Reporting.py", label="Reporting", icon="📊")
        st.markdown(
            """
            <div class="erp-stack-card">
                <div class="erp-stack-title">
                    <span>Systemstack</span>
                    <span class="erp-status-dot"></span>
                </div>
                <div class="erp-stack-grid">
                    <span class="erp-stack-pill">🐍 Python</span>
                    <span class="erp-stack-pill">⚙️ FastAPI</span>
                    <span class="erp-stack-pill">🐘 PostgreSQL</span>
                    <span class="erp-stack-pill">✨ Streamlit</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def seiten_kopf(titel: str, untertitel: str = ""):
    seiten_sidebar()
    untertitel_html = f"<p>{untertitel}</p>" if untertitel else ""
    st.markdown(
        f"""
        <div class="erp-hero">
            <div class="erp-eyebrow">ERP Dashboard</div>
            <h1>{titel}</h1>
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
