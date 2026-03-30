import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

# CSS per la Tabella Clinica e le etichette (Badge)
st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; margin-bottom: 20px; font-weight: bold; font-family: sans-serif;}
    
    /* Stile Tabella Clinica Professionale */
    .clinica-table {width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 0.9rem; margin-top: 10px; background-color: white;}
    .clinica-table th {background-color: #1e3a8a; color: white; padding: 12px; text-align: left; border: 1px solid #e2e8f0;}
    .clinica-table td {padding: 10px; border: 1px solid #e2e8f0; vertical-align: top;}
    
    /* Righe Colorate */
    .row-agitato {background-color: #fef2f2 !important; font-weight: bold; border-left: 5px solid #ef4444 !important;}
    .row-stabile {background-color: #ffffff;}
    .row-log {background-color: #fffbeb !important; font-style: italic; color: #92400e; border-left: 5px solid #f59e0b !important;}
    
    /* Badge Stati */
    .badge-agitato {background-color: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; display: inline-block;}
    .badge-stabile {background-color: #10b981; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; display: inline-block;}
    .badge-altri {background-color: #64748b; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; display: inline-block;}

    /* Card standard per Agenda */
    .card {padding: 12px; margin: 5px 0; border-radius: 8px; background: #f8fafc; border-left: 5px solid #64748b; box-shadow: 0 1px 3px rgba(0,0,0,0.1);}
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (p_id INTEGER, tipo TEXT, d_ora TEXT, note TEXT, rif TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, data TEXT, medico TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS documenti (p_id INTEGER, nome_doc TEXT, file_blob BLOB, data TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)
    with st.form("login_form"):
        pwd = st.text_input("Inserire Codice Accesso", type="password")
        if st.form_submit_button("ACCEDI"):
            if pwd in ["rems2026", "admin2026"]:
                st.session_state.auth = True
                st.session_state.role = "admin" if pwd == "admin2026" else "user"
                st.rerun()
            else:
                st.error("Codice Errato")
    st.stop()

# Header principale
st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)

# --- 4. SIDEBAR ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Agenda", "Terapie", "Documenti", "Gestione"])
ruoli_lista = ["Tutti", "Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore", "SISTEMA"]

# --- 5. MONITORAGGIO
