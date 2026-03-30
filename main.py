import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect", layout="wide")

# CSS ultra-compatto per tasti piccoli
st.markdown("<style>.stButton>button {width:100%; border-radius:10px; height:45px !important; background-color:white !important; color:#1e3a8a !important; border:1px solid #e2e8f0; font-size:0.9rem !important; font-weight:600;} .active-btn button {background-color:#1e3a8a !important; color:white !important; box-shadow:0 4px 8px rgba(30,58,138,0.15);} .card {padding:12px; margin:8px 0; border-radius:10px; background:white; border-left:5px solid #64748b; box-shadow:0 2px 4px rgba(0,0,0,0.05);} .nota-header {font-size:0.75rem; color:#64748b; border-bottom:1px solid #f1f5f9; margin-bottom:5px;} .agitato {border-left-color:#ef4444 !important; background-color:#fef2f2 !important;} #MainMenu, footer, header {visibility:hidden;}</style>", unsafe_allow_html=True)

# --- 2. FUNZIONI DATABASE ---
def db_run(query, params=(), commit=False):
    with sqlite3.connect("rems_final.db", check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (p_id INTEGER, tipo TEXT, d_ora TEXT, note TEXT, rif TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. SESSIONE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'menu' not in st.session_state: st.session_state.menu = "Monitoraggio"
for k in ['v_g', 'v_a']: 
    if k not in st.session_state: st.session_state[k] = 0

# --- 4. LOGIN ---
if not st.session_state.auth:
    st.title("REMS CONNECT")
    pwd = st.text_input("Codice", type="password")
    if st.button("ACCEDI"):
        if pwd in ["rems2026", "admin2026"]:
            st.session_state.auth = True
            st.session_state.role = "admin" if "admin" in pwd else "user"
            st.rerun()
    st.stop()

# --- 5. NAVIGAZIONE ---
st.markdown("<h3 style='text-align:center; color:#1e3a8a;'>REMS CONNECT</h3>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f'<div class="{"active-btn" if st.session_state.menu=="Monitoraggio" else ""}">', unsafe_allow_html=True)
    if st.button("📊 Monitoraggio"): st.session_state.menu = "Monitoraggio"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="{"active-btn" if st.session_state.menu=="Agenda" else ""}">', unsafe_allow_html=True)
    if st.button("📅 Agenda"): st.session_state.menu = "Agenda"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with c3:
    if st.session_state.role == "admin":
        st.markdown(f'<div class="{"active-btn" if st.session_state.menu=="Gestione" else ""}">', unsafe_allow_html=True)
        if st.button("⚙️ Gestione"): st.session_state.menu = "Gestione"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- 6. MODULI ---
if st.session_state.menu == "Monitoraggio":
    ruoli = ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"]
    filtro = st.selectbox("Filtra per figura:", ["TUTTI"] + ruoli)
    for p_id, nome in db_run("SELECT * FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}"):
            vi = st.session_state.get(f"v_{p_id}", 0)
            c_a, c_b = st.columns(2)
            r = c_a.selectbox("Ruolo", ruoli, key=f"r{p_id}{vi}")
            o = c_b.text_input("Firma", key=f"f{p_id}{vi}")
            u = st
