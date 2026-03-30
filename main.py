import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE E FIX MENU PERMANENTE ---
st.set_page_config(
    page_title="REMS Connect", 
    page_icon="🏥", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* PULSANTE DI EMERGENZA PER IL MENU (Sempre visibile) */
    .st-emotion-cache-15497gn, button[kind="headerNoSpacing"] {
        display: block !important;
        position: fixed !important;
        top: 15px !important;
        left: 15px !important;
        background-color: #2563eb !important;
        color: white !important;
        width: 55px !important;
        height: 55px !important;
        border-radius: 50% !important;
        z-index: 999999 !important;
        border: 2px solid white !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
    }

    /* Ingrandisce l'icona del menu */
    button[kind="headerNoSpacing"] svg {
        width: 30px !important;
        height: 30px !important;
        fill: white !important;
    }

    /* OTTIMIZZAZIONE TESTI E BOTTONI PER MOBILE */
    html, body, [class*="css"] { font-size: 19px !important; background-color: #f1f5f9; }
    
    [data-testid="stSidebar"] { 
        background-color: #1e293b !important; 
        min-width: 280px !important; 
        z-index: 1000000 !important;
    }
    
    [data-testid="stSidebar"] * { color: white !important; }

    .stButton>button {
        height: 4.2rem !important;
        font-size: 1.3rem !important;
        border-radius: 15px !important;
        background-color: #2563eb !important;
        color: white !important;
        font-weight: bold !important;
        width: 100% !important;
    }

    /* CARD PAZIENTI E DIARIO */
    .stExpander { border: 2px solid #cbd5e1 !important; border-radius: 15px !important; background-color: white !important; margin-top: 10px !important; }
    .nota-card { background-color: #f8fafc; padding: 15px; border-left: 6px solid #2563eb; margin-bottom: 12px; border-radius: 8px; color: #1e293b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }

    /* Nasconde header originale che crea problemi */
    header[data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { visibility: hidden; }
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

# --- 3. ACCESSO ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🏥 REMS Connect")
    pwd = st.text_input("Codice Identificativo", type="password")
    if st.button("ACCEDI AL SISTEMA"):
        if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE SIDEBAR ---
st.sidebar.title("REMS Connect")
st.sidebar.markdown("---")
menu = st.sidebar.radio("NAVIGAZIONE:", ["📊 MONITORAGGIO", "⚙️ IMPOSTAZIONI"])

# --- 5. MONITORAGGIO & DIARIO ---
if menu == "📊 MONITORAGGIO":
    st.title("Diario Clinico")
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if not pazienti: st.info("Nessun paziente in archivio.")
    
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}"):
            umore = st.select_slider("Stato", options=["Cupo", "Deflesso", "Stabile"], value="Stabile", key=f"u_{p_id}")
            nota = st.text_area("Note Visita", key=f"n_{p_id}", height=150)
            if st.button("SALVA REGISTRAZIONE", key=f"b_{p_id}"):
                if nota:
                    dt = datetime.now().strftime("%d/%m/%Y %H:%M")
                    db_query("INSERT INTO eventi (p_id, data, umore, nota) VALUES (?,?,?,?)", (p_id, dt, umore, nota), commit=True)
                    st.success("Nota registrata!")
                    st.rerun()
            st.divider()
            st.subheader("Cronologia Note")
            eventi = db_query("SELECT data, umore, nota FROM eventi WHERE p_id=? ORDER BY id DESC LIMIT 10", (p_id,))
            for e in eventi:
                st.markdown(f'<div class="nota-card"><b>{e[0]}</b> | Stato: {e[1]}<br><div style="margin-top:5px;">{e[2]}</div></div>', unsafe_allow_html=True)

# --- 6. IMPOSTAZIONI ---
elif menu == "⚙️ IMPOSTAZIONI":
    st.title("Gestione Database")
    with st.expander("➕ AGGIUNGI NUOVO PAZIENTE"):
        n_paz = st.text_input("Nome e Cognome")
        if st.button("SALVA NUOVO"):
            if n_paz: db_query("INSERT INTO pazienti (nome) VALUES (?)", (n_paz,), commit=True); st.rerun()
    st.divider()
    p_list = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_list:
        p_del = st.selectbox("Elimina record", [p[1] for p in p_list])
        if st.button("ELIMINA DEFINITIVAMENTE"):
            db_query("DELETE FROM pazienti WHERE nome=?", (p_del,), commit=True)
            st.rerun()
