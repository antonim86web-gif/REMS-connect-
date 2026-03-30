import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE MOBILE-FIRST (Ingrandita) ---
st.set_page_config(page_title="REMS Connect", page_icon="🏥", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Ingrandisce il testo base e lo sfondo */
    html, body, [class*="css"] {
        font-size: 18px !important; /* Testo più grande del 20% */
        background-color: #f8fafc;
    }

    /* Ingrandisce i titoli */
    h1 { font-size: 2.2rem !important; }
    h2 { font-size: 1.8rem !important; }
    h3 { font-size: 1.5rem !important; }

    /* Ingrandisce i PULSANTI (fondamentale per smartphone) */
    .stButton>button {
        height: 3.5rem !important; /* Tasti più alti */
        font-size: 1.2rem !important;
        border-radius: 12px !important;
        background-color: #2563eb !important;
        font-weight: bold !important;
        margin-top: 10px;
    }

    /* Ingrandisce i campi di TESTO e AREE DI TESTO */
    input, textarea, .stSelectbox, .stSlider {
        font-size: 1.1rem !important;
    }
    
    /* Rende le card dei pazienti più robuste */
    .stExpander {
        border: 2px solid #e2e8f0 !important;
        border-radius: 15px !important;
        margin-bottom: 15px !important;
        background-color: white !important;
    }

    /* Stile delle note storiche (Diario) */
    .nota-card {
        background-color: #ffffff;
        padding: 15px;
        border-left: 6px solid #2563eb;
        margin-bottom: 12px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        font-size: 1rem;
    }

    /* Nasconde elementi superflui per risparmiare spazio */
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
    pwd = st.text_input("Codice Accesso", type="password")
    if st.button("ACCEDI"):
        if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. MENU SIDEBAR (Compatto) ---
st.sidebar.title("MENU")
menu = st.sidebar.radio("Seleziona:", ["📊 DASHBOARD", "⚙️ IMPOSTAZIONI"])

# --- 5. DASHBOARD & DIARIO (Layout ottimizzato) ---
if menu == "📊 DASHBOARD":
    st.title("Monitoraggio")
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    
    if not pazienti:
        st.info("Nessun paziente. Vai in 'Impostazioni' per aggiungerne uno.")
    
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}"):
            st.subheader("Nuova Nota")
            # Slider umore più grande
            umore = st.select_slider("Stato Attuale", options=["Cupo", "Deflesso", "Stabile"], value="Stabile", key=f"u_{p_id}")
            
            # Area di nota con altezza fissa per mobile
            nota = st.text_area("Cosa è successo?", key=f"n_{p_id}", height=150, placeholder="Inserisci qui il diario clinico...")
            
            if st.button("SALVA AGGIORNAMENTO", key=f"b_{p_id}"):
                data_ora = datetime.now().strftime("%d/%m/%Y %H:%M")
                db_query("INSERT INTO eventi (p_id, data, umore, nota) VALUES (?,?,?,?)", (p_id, data_ora, umore, nota), commit=True)
                st.success("Nota salvata correttamente!")
                st.rerun()
            
            st.divider()
            
            st.subheader("Diario Recente")
            eventi = db_query("SELECT data, umore, nota FROM eventi WHERE p_id=? ORDER BY id DESC LIMIT 10", (p_id,))
            for e in eventi:
                st.markdown(f"""
                <div class="nota-card">
                    <b style="color:#2563eb;">{e[0]}</b> | Stato: <b>{e[1]}</b><br>
                    <div style="margin-top:8px;">{e[2]}</div>
                </div>
                """, unsafe_allow_html=True)

# --- 6. IMPOSTAZIONI ---
elif menu == "⚙️ IMPOSTAZIONI":
    st.title("Archivio")
    
    with st.expander("➕ AGGIUNGI PAZIENTE"):
        nuovo = st.text_input("Nome e Cognome")
        if st.button("REGISTRA NUOVO"):
            if nuovo:
                db_query("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), commit=True)
                st.rerun()

    st.divider()
    
    pazienti_raw = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if pazienti_raw:
        st.subheader("Elimina record")
        opzioni = {f"{p[1]}": p[0] for p in pazienti_raw}
        scelta = st.selectbox("Seleziona da rimuovere", list(opzioni.keys()))
        if st.button("🗑️ ELIMINA DEFINITIVAMENTE"):
            db_query("DELETE FROM pazienti WHERE id=?", (opzioni[scelta],), commit=True)
            db_query("DELETE FROM eventi WHERE p_id=?", (opzioni[scelta],), commit=True)
            st.rerun()
