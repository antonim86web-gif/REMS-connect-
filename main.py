import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURAZIONE STILE REPLIT ---
st.set_page_config(
    page_title="REMS Connect",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Iniezione CSS per il tema Dark e font professionale
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&display=swap');
    
    .stApp {
        background-color: #0e1525;
        color: #f5f9fc;
    }
    
    html, body, [class*="css"], .stMarkdown, p {
        font-family: 'Fira Code', monospace !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1c2333;
        border-right: 1px solid #303b4d;
    }

    /* Titoli in Azzurro Replit */
    h1, h2, h3 {
        color: #00adff !important;
        font-weight: 500;
    }

    /* Bottoni */
    .stButton>button {
        background-color: #0053a6;
        color: white;
        border-radius: 8px;
        border: none;
        width: 100%;
    }
    
    /* Input Fields */
    input, textarea {
        background-color: #1c2333 !important;
        color: white !important;
        border: 1px solid #303b4d !important;
    }

    /* Nasconde menu Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGICA DATABASE ---
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
    if st.button("Entra nel Sistema"):
        if pwd == "rems2026":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Codice errato")
    st.stop()

# --- 4. INTERFACCIA PRINCIPALE ---
st.sidebar.title("Menu")
menu = st.sidebar.radio("Vai a:", ["Dashboard Umore", "Anagrafica & Note"])

if menu == "Dashboard Umore":
    st.title("📊 Stato Attuale")
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome}"):
            col1, col2 = st.columns([1, 2])
            with col1:
                umore = st.select_slider(f"Stato per {nome}", options=["Cupo", "Deflesso", "Stabile"], value="Stabile", key=f"u_{p_id}")
            with col2:
                nota = st.text_area("Nota clinica rapida", key=f"n_{p_id}")
                if st.button("Registra Aggiornamento", key=f"b_{p_id}"):
                    data_ora = datetime.now().strftime("%d/%m/%Y %H:%M")
                    db_query("INSERT INTO eventi (p_id, data, umore, nota) VALUES (?,?,?,?)", 
                             (p_id, data_ora, umore, nota), commit=True)
                    st.success("Registrato!")

elif menu == "Anagrafica & Note":
    st.title("📝 Gestione Pazienti")
    
    with st.expander("➕ Aggiungi Nuovo"):
        nuovo_n = st.text_input("Nome e Cognome")
        if st.button("Salva in Archivio"):
            db_query("INSERT INTO pazienti (nome) VALUES (?)", (nuovo_n,), commit=True)
            st.rerun()

    st.divider()
    
    pazienti_raw = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if pazienti_raw:
        opzioni = {f"{p[1]} (ID: {p[0]})": p[0] for p in pazienti_raw}
        scelta = st.selectbox("Seleziona per storico o modifica", list(opzioni.keys()))
        p_id_scelto = opzioni[scelta]
        
        if st.button("Elimina Paziente selezionato"):
            db_query("DELETE FROM pazienti WHERE id=?", (p_id_scelto,), commit=True)
            st.rerun()
            
        st.subheader("Diario Storico")
        eventi = db_query("SELECT data, umore, nota FROM eventi WHERE p_id=? ORDER BY id DESC", (p_id_scelto,))
        for e in eventi:
            st.markdown(f"**{e[0]}** - Stato: `{e[1]}`")
            st.write(e[2])
            st.divider()
