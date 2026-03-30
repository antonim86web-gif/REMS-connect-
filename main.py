import streamlit as st
import sqlite3
from datetime import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
    .rems-h { text-align: center; color: #1e3a8a; font-family: 'Orbitron', sans-serif; font-size: 2.5rem; margin-bottom: 20px; }
    .stButton>button { height: 3rem; border-radius: 10px; background-color: #2563eb !important; color: white !important; font-weight: bold; width: 100%; }
    .card { padding: 10px; margin: 5px 0; border-radius: 8px; border-left: 5px solid #cbd5e1; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .agitato { background: #fee2e2 !important; border-left-color: #dc2626 !important; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ---
def query(q, p=(), commit=False):
    with sqlite3.connect("rems_v2.db") as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (p_id INTEGER, tipo TEXT, d_ora TEXT, note TEXT, rif TEXT)")
        cur.execute(q, p)
        if commit: conn.commit()
        return cur.fetchall()

# --- SESSION STATE ---
for k, v in {'auth': False, 'menu': "📊 Monitoraggio", 'v_a': 0}.items():
    if k not in st.session_state: st.session_state[k] = v

# --- LOGIN ---
if not st.session_state.auth:
    st.markdown('<h1 class="rems-h">REMS CONNECT</h1>', unsafe_allow_html=True)
    pwd = st.text_input("Codice", type="password")
    if st.button("ENTRA"):
        if pwd in ["rems2026", "admin2026"]:
            st.session_state.auth = True
            st.session_state.role = "admin" if "admin" in pwd else "user"
            st.rerun()
    st.stop()

# --- NAVIGAZIONE ---
st.markdown('<h1 class="rems-h">REMS CONNECT</h1>', unsafe_allow_html=True)
c1, c
