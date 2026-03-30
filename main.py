import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE MOBILE-FIRST & MENU FORZATO ---
st.set_page_config(
    page_title="REMS Connect", 
    page_icon="🏥", 
    layout="wide", 
    initial_sidebar_state="expanded" # Forza l'apertura del menu all'avvio
)

st.markdown("""
    <style>
    /* Forza la visibilità del pulsante Menu (☰) in alto a sinistra */
    .st-emotion-cache-15497gn {
        display: block !important;
        background-color: #2563eb !important;
        color: white !important;
        border-radius: 50%;
    }

    /* SFONDO E TESTI GRANDI PER SMARTPHONE */
    html, body, [class*="css"] {
        font-size: 19px !important; /* Testo leggibile senza zoom */
        background-color: #f1f5f9;
    }

    /* SIDEBAR (MENU LATERALE) STILE REPLIT DARK */
    [data-testid="stSidebar"] {
        background-color: #1e293b !important;
        color: white !important;
        min-width: 260px !important;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* PULSANTI GIGANTI A PROVA DI DITA */
    .stButton>button {
        height: 4rem !important;
        font-size: 1.3rem !important;
        border-radius: 15px !important;
        background-color: #2563eb !important;
        color: white !important;
        font-weight: bold !important;
        width: 100% !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* CARD PAZIENTI (EXPANDER) */
    .stExpander {
        border: 2px solid #cbd5e1 !important;
        border-radius: 15px !important;
        background-color: white !important;
        margin-bottom: 15px !important;
    }

    /* DIARIO STORICO (BOX NOTE) */
    .nota-card {
        background-color: #f8fafc;
        padding: 15px;
        border-left: 6px solid #2563eb;
        margin-bottom: 12px;
        border-radius: 8px;
        box-shadow: 0 2px
