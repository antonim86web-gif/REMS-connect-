import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURAZIONE & CSS ---
st.set_page_config(page_title="REMS Connect PRO", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
    html, body, [class*="css"] { font-size: 19px !important; background-color: #f1f5f9; }
    .rems-header {
        text-align: center; color: #1e3a8a; font-family: 'Orbitron', sans-serif;
        font-size: 3rem !important; font-weight: 700; margin-bottom: 20px;
        text-transform: uppercase; letter-spacing: 4px; text-shadow: 0 0 10px rgba(37, 99, 235, 0.2);
    }
    .stButton>button { 
        height: 3.5rem !important; font-size: 1.1rem !important; border-radius: 12px !important; 
        background-color: #2563eb !important; color: white !important; font-weight: bold !important; 
        width: 100%; font-family: 'Orbitron', sans-serif;
    }
    .nota-card { padding: 12px; margin-bottom: 8px; border-radius: 8px; color: #1e293b; border-left: 6px solid #cbd5e1; background-color: #f8fafc; }
    .agenda-card { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 10px; border-top: 4px solid #2563eb; }
    .nota-Psichiatra { border-left-color: #ef4444 !important; }
    .nota-Infermiere { border-left-color: #3b82f6 !important; }
    .nota-OSS { border-left-color: #8b5cf6 !important; }
    .nota-Psicologo { border-left-color: #10b981 !important; }
    .nota-Educatore { border-left-color: #f59e0b !important; }
    .allerta-agitato { background-color: #fee2e2 !important; border: 2px solid #dc2626 !important; animation: blinker 2s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.8; } }
    div[data-testid="stRadio"] > div { flex-direction: row !important; gap: 10px; }
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
def db_query(query, params=(), commit=False):
    conn = sqlite3.connect("rems_connect_v1.db", check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER PRIMARY KEY, p_id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, operatore TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY, p_id INTEGER, tipo TEXT, data_ora TEXT, note TEXT, operatore_rif TEXT)")
    cur.execute(query, params)
    res = cur.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'role' not in st.session_state: st.session_state.role = "user"
if 'menu_val' not in st.session_state: st.session_state.menu_val = "📊 Monitoraggio"

# --- 4. LOGIN ---
if not st.session_state.auth:
    st.markdown('<h1 class="rems-header">REMS CONNECT</h1>', unsafe_allow_html=True)
    pwd = st.text_input("Codice Identificativo", type="password")
    if st.button("ENTRA"):
        if pwd == "rems2026": st.session_state.auth = True; st.session_state.role = "user"; st.rerun()
        elif pwd == "admin2026": st.session_state.auth = True; st.session_state.role = "admin"; st.rerun()
        else: st.error("Codice errato")
    st.stop()

# --- 5. INTERFACCIA ---
st.markdown('<h1 class="rems-header">REMS CONNECT</h1>', unsafe_allow_html=True)

c_nav1, c_nav2, c_nav3 = st.columns(3)
with c_nav1:
    if st.button("📊 Monitoraggio"): st.session_state.menu_val = "📊 Monitoraggio"; st.rerun()
with c_nav2:
    if st.button("📅 Agenda & Uscite"): st.session_state.menu_val = "📅 Agenda"; st.rerun()
with c_nav3:
    if st.session_state.role == "admin":
        if st.button("⚙️ Gestione"): st.session_state.menu_val = "⚙️ Gestione"; st.rerun()
    else: st.button("⚙️ Gestione (Admin)", disabled=True)

# --- 6. LOGICA MENU ---
if st.session_state.menu_val == "📊 Monitoraggio":
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            if f"v_{p_id}" not in st.session_state: st.session_state[f"v_{p_id}"] = 0
            c1, c2 = st.columns(2)
            with c1: ruolo = st.selectbox("Ruolo:", ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"], key=f"r_{p_id}_{st.session_state[f'v_{p_id}']}")
            with c2: operatore = st.text_input("Firma:", key=f"f_{p_id}_{st.session_state[f'v_{p_id}']}")
            umore = st.radio("Stato", ["🟢 Stabile", "🟡 Cupo", "🟠 Deflesso", "🔴 Agitato"], key=f"u_{p_id}_{st.session_state[f'v_{p_id}']}", horizontal=True)
            nota = st.text_area("Nota:", key=f"n_{p_id}_{st.session_state[f'
