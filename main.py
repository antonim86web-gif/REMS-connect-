import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE ESTETICA PROFESSIONAL ---
st.set_page_config(page_title="REMS Connect", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; color: #1e293b; }
    [data-testid="stSidebar"] { background-color: #1e293b; color: white; }
    h1, h2, h3 { color: #0f172a; }
    .stButton>button { background-color: #2563eb; color: white; border-radius: 8px; width: 100%; border: none; }
    .stExpander { background-color: white !important; border: 1px solid #e2e8f0 !important; border-radius: 12px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    /* Stile per le note storiche nel diario */
    .nota-card { background-color: #f1f5f9; padding: 10px; border-left: 4px solid #3b82f6; margin-bottom: 10px; border-radius: 4px; }
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
    if st.button("Accedi"):
        if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. MENU SIDEBAR ---
st.sidebar.title("REMS Connect")
menu = st.sidebar.radio("Navigazione", ["📊 Dashboard & Diario", "⚙️ Gestione Pazienti"])

# --- 5. DASHBOARD & DIARIO (UNIFICATI) ---
if menu == "📊 Dashboard & Diario":
    st.title("Monitoraggio Pazienti")
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    
    if not pazienti:
        st.info("Nessun paziente in archivio. Vai in 'Gestione Pazienti' per iniziare.")
    
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}"):
            # PARTE ALTA: Inserimento
            st.subheader("Nuovo Aggiornamento")
            c1, c2 = st.columns([1, 2])
            with c1:
                umore = st.select_slider("Stato", options=["Cupo", "Deflesso", "Stabile"], value="Stabile", key=f"u_{p_id}")
            with c2:
                nota = st.text_area("Nota clinica", key=f"n_{p_id}", height=100)
                if st.button("Salva Nota", key=f"b_{p_id}"):
                    data_ora = datetime.now().strftime("%d/%m/%Y %H:%M")
                    db_query("INSERT INTO eventi (p_id, data, umore, nota) VALUES (?,?,?,?)", (p_id, data_ora, umore, nota), commit=True)
                    st.success("Nota salvata!")
                    st.rerun()
            
            st.divider()
            
            # PARTE BASSA: Diario Storico del paziente
            st.subheader("Diario Storico Recente")
            eventi = db_query("SELECT data, umore, nota FROM eventi WHERE p_id=? ORDER BY id DESC", (p_id,))
            if not eventi:
                st.write("Nessun pregresso registrato.")
            for e in eventi:
                st.markdown(f"""
                <div class="nota-card">
                    <small>{e[0]} | Stato: <b>{e[1]}</b></small><br>
                    {e[2]}
                </div>
                """, unsafe_allow_html=True)

# --- 6. GESTIONE PAZIENTI (PULITA) ---
elif menu == "⚙️ Gestione Pazienti":
    st.title("Amministrazione Archivio")
    
    # Aggiungi
    with st.expander("➕ Aggiungi Nuovo Nominativo"):
        nuovo = st.text_input("Nome e Cognome")
        if st.button("Registra"):
            if nuovo:
                db_query("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), commit=True)
                st.rerun()

    # Elimina
    st.divider()
    pazienti_raw = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if pazienti_raw:
        st.subheader("Rimuovi Errori")
        opzioni = {f"{p[1]}": p[0] for p in pazienti_raw}
        scelta = st.selectbox("Seleziona da eliminare", list(opzioni.keys()))
        if st.button("🗑️ ELIMINA DEFINITIVAMENTE"):
            db_query("DELETE FROM pazienti WHERE id=?", (opzioni[scelta],), commit=True)
            db_query("DELETE FROM eventi WHERE p_id=?", (opzioni[scelta],), commit=True)
            st.rerun()
