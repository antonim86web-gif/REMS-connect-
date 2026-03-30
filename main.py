import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect", layout="wide")

# CSS per tasti più piccoli e compatti
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 55px !important;
        background-color: white !important;
        color: #1e3a8a !important;
        border: 1px solid #e2e8f0 !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        transition: 0.2s;
    }
    .active-btn button {
        background-color: #1e3a8a !important;
        color: white !important;
        border: 1px solid #1e3a8a !important;
        box-shadow: 0 4px 8px rgba(30,58,138,0.15);
    }
    .card {padding: 12px; margin: 8px 0; border-radius: 10px; background: white; border-left: 5px solid #64748b; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    .nota-header {font-size: 0.75rem; color: #64748b; border-bottom: 1px solid #f1f5f9; margin-bottom: 5px;}
    .agitato {border-left-color: #ef4444 !important; background-color: #fef2f2 !important;}
    #MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. FUNZIONI DATABASE ---
def db_run(query, params=(), commit=False):
    with sqlite3.connect("rems_v12.db", check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (p_id INTEGER, tipo TEXT, d_ora TEXT, note TEXT, rif TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT
