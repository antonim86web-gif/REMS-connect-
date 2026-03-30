import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURAZIONE GRAFICA REPLIT MODERN ---
st.set_page_config(
    page_title="REMS Connect",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded" # <--- MENU ORA SEMPRE APERTO
)

st.markdown("""
    <style>
    /* Sfondo grigio scuro Replit (non nero) */
    .stApp {
        background-color: #1c2333; 
        color: #f5f9fc;
    }
    
    /* Sidebar più chiara per staccare dal fondo */
    [data-testid="stSidebar"] {
        background-color: #2d3548;
        border-right: 1px solid #3d475c;
    }

    /* Testi e Sidebar Menu */
    .st-emotion-cache-10trblm, p, .stMarkdown {
        color: #f5f9fc !important;
    }

    /* Titoli in Azzurro Vivace */
    h1, h2, h3 {
        color: #38bdf8 !important;
    }

    /* Bottoni stile Replit (Arrotondati e Blu) */
    .stButton>button {
        background-color: #0073e6;
        color: white;
        border-radius: 12px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }

    /* Expander (Card pazienti) */
    .stDetails {
        background-color: #2d3548 !important;
        border: 1px solid #3d475c !important;
        border-radius: 12px;
    }

    /* Nasconde loghi Streamlit per pulizia */
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

# --- 3. LOGICA DI ACCESSO ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🏥 REMS Connect")
    st.write("Area Riservata - Accesso Protetto")
    pwd = st.text_input("Codice Identificativo", type="password")
    if st.button("Accedi"):
        if pwd == "rems2026":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Codice non valido")
    st.stop()

# --- 4. INTERFACCIA PRINCIPALE ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2966/2966327.png", width=80)
st.sidebar.title("REMS Connect")
menu = st.sidebar.radio("Navigazione", ["📊 Dashboard Umore", "📝 Gestione Pazienti"])

if menu == "📊 Dashboard Umore":
    st.title("Stato Attuale")
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    
    if not pazienti:
        st.info("Benvenuto! Vai nel menu 'Gestione Pazienti' per aggiungere il primo record.")
    
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome}"):
            col1, col2 = st.columns([1, 2])
            with col1:
                umore = st.select_slider(f"Stato", options=["Cupo", "Deflesso", "Stabile"], value="Stabile", key=f"u_{p_id}")
            with col2:
                nota = st.text_area("Nota clinica", key=f"n_{p_id}", placeholder="Scrivi qui l'andamento...")
                if st.button("Aggiorna Diario", key=f"b_{p_id}"):
                    data_ora = datetime.now().strftime("%d/%m/%Y %H:%M")
                    db_query("INSERT INTO eventi (p_id, data, umore, nota) VALUES (?,?,?,?)", 
                             (p_id, data_ora, umore, nota), commit=True)
                    st.success(f"Dato salvato per {nome}")

elif menu == "📝 Gestione Pazienti":
    st.title("Archivio Anagrafico")
    
    # Aggiunta
    with st.expander("➕ Inserisci Nuovo Paziente"):
        nuovo_n = st.text_input("Nome e Cognome")
        if st.button("Registra"):
            if nuovo_n:
                db_query("INSERT INTO pazienti (nome) VALUES (?)", (nuovo_n,), commit=True)
                st.success("Paziente registrato!")
                st.rerun()

    st.divider()
    
    # Storico e Modifiche
    pazienti_raw = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if pazienti_raw:
        opzioni = {f"{p[1]}": p[0] for p in pazienti_raw}
        scelta = st.selectbox("Seleziona Paziente", list(opzioni.keys()))
        p_id_scelto = opzioni[scelta]
        
        if st.button("🗑️ Elimina Paziente (Azione Irreversibile)"):
            db_query("DELETE FROM pazienti WHERE id=?", (p_id_scelto,), commit=True)
            db_query("DELETE FROM eventi WHERE p_id=?", (p_id_scelto,), commit=True)
            st.rerun()
            
        st.subheader("Diario Storico")
        eventi = db_query("SELECT data, umore, nota FROM eventi WHERE p_id=? ORDER BY id DESC", (p_id_scelto,))
        if not eventi:
            st.write("Nessuna nota presente.")
        for e in eventi:
            st.info(f"📅 **{e[0]}** | Stato: **{e[1]}**")
            st.write(f"_{e[2]}_")
            st.divider()
