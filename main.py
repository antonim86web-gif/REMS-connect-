import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(
    page_title="REMS Connect", 
    page_icon="🏥", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# CSS CORRETTO (Senza errori di virgolette)
st.markdown("""
<style>
    .stApp { background-color: #f1f5f9; color: #1e293b; }
    html, body, [class*="css"] { font-size: 19px !important; }
    [data-testid="stSidebar"] { background-color: #1e293b !important; min-width: 260px !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton>button {
        height: 4rem !important;
        font-size: 1.3rem !important;
        border-radius: 15px !important;
        background-color: #2563eb !important;
        color: white !important;
        font-weight: bold !important;
        width: 100% !important;
        border: none !important;
    }
    .stExpander { border: 2px solid #cbd5e1 !important; border-radius: 15px !important; background-color: white !important; }
    .nota-card { background-color: #f8fafc; padding: 15px; border-left: 6px solid #2563eb; margin-bottom: 12px; border-radius: 8px; color: #1e293b; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
def db_query(query, params=(), commit=False):
    conn = sqlite3.connect("rems_connect_v1.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER PRIMARY KEY, p_id INTEGER, data TEXT, umore TEXT, nota TEXT)")
    cur.execute(query, params)
    res = cur.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🏥 REMS Connect")
    pwd = st.text_input("Codice", type="password")
    if st.button("ACCEDI"):
        if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. MENU ---
st.sidebar.title("REMS Connect")
menu = st.sidebar.radio("VAI A:", ["📊 MONITORAGGIO", "⚙️ IMPOSTAZIONI"])

# --- 5. DASHBOARD ---
if menu == "📊 MONITORAGGIO":
    st.title("Diario Clinico")
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}"):
            umore = st.select_slider("Stato", options=["Cupo", "Deflesso", "Stabile"], value="Stabile", key=f"u_{p_id}")
            nota = st.text_area("Nota", key=f"n_{p_id}", height=120)
            if st.button("SALVA", key=f"b_{p_id}"):
                data_ora = datetime.now().strftime("%d/%m/%Y %H:%M")
                db_query("INSERT INTO eventi (p_id, data, umore, nota) VALUES (?,?,?,?)", (p_id, data_ora, umore, nota), commit=True)
                st.rerun()
            st.markdown("---")
            eventi = db_query("SELECT data, umore, nota FROM eventi WHERE p_id=? ORDER BY id DESC LIMIT 10", (p_id,))
            for e in eventi:
                st.markdown(f'<div class="nota-card"><b>{e[0]}</b> | {e[1]}<br>{e[2]}</div>', unsafe_allow_html=True)

# --- 6. IMPOSTAZIONI ---
elif menu == "⚙️ IMPOSTAZIONI":
    st.title("Gestione")
    nuovo = st.text_input("Nuovo Paziente")
    if st.button("AGGIUNGI"):
        if nuovo: db_query("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), commit=True); st.rerun()
    st.divider()
    pazienti_list = db_query("SELECT id, nome FROM pazienti")
    if pazienti_list:
        p_canc = st.selectbox("Elimina", {p[1]: p[0] for p in pazienti_list})
        if st.button("ELIMINA"):
            db_query("DELETE FROM pazienti WHERE nome=?", (p_canc,), commit=True)
            st.rerun()
