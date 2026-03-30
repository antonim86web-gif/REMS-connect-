import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 19px !important; background-color: #f1f5f9; }
    .stButton>button { height: 4rem !important; font-size: 1.2rem !important; border-radius: 12px !important; background-color: #2563eb !important; color: white !important; font-weight: bold !important; width: 100%; }
    .nota-card { padding: 12px; margin-bottom: 10px; border-radius: 8px; color: #1e293b; border-left: 6px solid #cbd5e1; background-color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .nota-Psichiatra { border-left-color: #ef4444 !important; background-color: #fef2f2 !important; }
    .nota-Infermiere { border-left-color: #3b82f6 !important; background-color: #eff6ff !important; }
    .nota-OSS { border-left-color: #8b5cf6 !important; background-color: #f5f3ff !important; }
    .nota-Psicologo { border-left-color: #10b981 !important; background-color: #ecfdf5 !important; }
    .nota-Educatore { border-left-color: #f59e0b !important; background-color: #fffbeb !important; }
    .date-header { background-color: #e2e8f0; padding: 5px 15px; border-radius: 20px; font-weight: bold; color: #475569; margin: 15px 0 10px 0; display: inline-block; font-size: 0.85rem; }
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
def db_query(query, params=(), commit=False):
    conn = sqlite3.connect("rems_connect_v1.db", check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER PRIMARY KEY, p_id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, operatore TEXT)")
    columns = [info[1] for info in cur.execute("PRAGMA table_info(eventi)").fetchall()]
    if "ruolo" not in columns: cur.execute("ALTER TABLE eventi ADD COLUMN ruolo TEXT DEFAULT 'Nota'")
    if "operatore" not in columns: cur.execute("ALTER TABLE eventi ADD COLUMN operatore TEXT DEFAULT 'Anonimo'")
    cur.execute(query, params)
    res = cur.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- 3. ACCESSO ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🏥 REMS Connect")
    pwd = st.text_input("Codice", type="password")
    if st.button("ENTRA"):
        if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
if 'menu_val' not in st.session_state: st.session_state.menu_val = "📊 Monitoraggio"

col_nav1, col_nav2 = st.columns(2)
with col_nav1:
