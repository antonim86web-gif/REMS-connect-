import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import os
import time
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import io

# --- CONFIGURAZIONE DI SISTEMA (NON MODIFICARE) ---
st.set_page_config(
    page_title="SISTEMA GESTIONALE INTEGRATO REMS v29.0",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MOTORE DATABASE CON LOGICA DI MIGRAZIONE AUTOMATICA ---
def get_db_connection():
    conn = sqlite3.connect('rems_final_v12.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabella Utenti (Struttura Originale)
    cursor.execute('''CREATE TABLE IF NOT EXISTS utenti 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      username TEXT UNIQUE, 
                      password TEXT, 
                      ruolo TEXT, 
                      data_creazione TEXT,
                      stato TEXT DEFAULT 'Attivo')''')
    
    # Tabella Diario Clinico (Struttura Estesa)
    cursor.execute('''CREATE TABLE IF NOT EXISTS diario 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      data TEXT, 
                      ora TEXT,
                      paziente TEXT, 
                      nota TEXT, 
                      autore TEXT, 
                      ruolo_autore TEXT, 
                      categoria TEXT,
                      criticita TEXT DEFAULT 'Normale',
                      visto_medico INTEGER DEFAULT 0)''')

    # Tabella Stanze (La versione con Mappa Visiva)
    cursor.execute('''CREATE TABLE IF NOT EXISTS stanze 
                     (paziente TEXT PRIMARY KEY, 
                      stanza TEXT, 
                      letto TEXT, 
                      note_spostamento TEXT, 
                      data_agg TEXT,
                      operatore TEXT)''')
    
    # Tabella Appuntamenti
    cursor.execute('''CREATE TABLE IF NOT EXISTS appuntamenti 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      data TEXT, 
                      ora TEXT, 
                      paziente TEXT, 
                      impegno TEXT, 
                      note_aggiuntive TEXT,
                      stato TEXT DEFAULT 'In programma')''')
    
    # Tabella Cassa Pazienti (Logica di Bilancio)
    cursor.execute('''CREATE TABLE IF NOT EXISTS cassa 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      data TEXT, 
                      paziente TEXT, 
                      tipo_operazione TEXT, 
                      importo REAL, 
                      causale TEXT, 
                      operatore TEXT,
                      saldo_residuo REAL)''')

    # --- SCRIPT DI RIPARAZIONE AUTOMATICA (Per risolvere l'OperationalError) ---
    cursor.execute("PRAGMA table_info(diario)")
    columns = [col[1] for col in cursor.fetchall()]
    if "categoria" not in columns:
        cursor.execute("ALTER TABLE diario ADD COLUMN categoria TEXT")
    if "criticita" not in columns:
        cursor.execute("ALTER TABLE diario ADD COLUMN criticita TEXT")
    
    conn.commit()
    return conn

db_conn = init_db()

# --- FUNZIONI DI SICUREZZA ORIGINALI ---
def hash_psw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def verify_psw(password, hashed):
    return hash_psw(password) == hashed

# --- LOGICA DI SESSIONE ---
if 'auth' not in st.session_state:
    st.session_state.auth = False
    st.session_state.user = ""
    st.session_state.role = ""

# --- INTERFACCIA DI ACCESSO INTEGRALE ---
if not st.session_state.auth:
    st.title("🏥 REMS CONNECT - Login Multi-Professionale")
    
    col_log, col_space, col_reg = st.columns([1, 0.1, 1])
    
    with col_log:
        st.subheader("🔑 Accesso Operatore")
        u_log = st.text_input("Username", placeholder="Inserisci username...")
        p_log = st.text_input("Password", type="password")
        if st.button("ACCEDI", use_container_width=True):
            curr = db_conn.cursor()
            curr.execute("SELECT password, ruolo FROM utenti WHERE username = ?", (u_log,))
            res = curr.fetchone()
            if res and verify_psw(p_log, res[0]):
                st.session_state.auth = True
                st.session_state.user = u_log
                st.session_state.role = res[1]
                st.rerun()
            else:
                st.error("Credenziali non valide.")

    with col_reg:
        st.subheader("📝 Registrazione Nuovo Profilo")
        u_reg = st.text_input("Nuovo Username")
        p_reg = st.text_input("Nuova Password", type="password")
        r_reg = st.selectbox("Ruolo Professionale", 
                           ["Medico", "Infermiere", "OSS", "Educatore", "Psicologo", "Assistente Sociale", "OPSI", "Admin"])
        cod_rems = st.text_input("Codice Autorizzazione Reparto", type="password")
        
        if st.button("REGISTRA"):
            if cod_rems == "REMS2024":
                try:
                    curr = db_conn.cursor()
                    curr.execute("INSERT INTO utenti (username, password, ruolo, data_creazione) VALUES (?,?,?,?)",
                               (u_reg, hash_psw(p_reg), r_reg, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    db_conn.commit()
                    st.success("Registrazione completata correttamente.")
                except:
                    st.error("Username già in uso.")
            else:
                st.error("Codice di sicurezza non valido.")
    st.stop()

# --- NAVBAR LATERALE (Invariata) ---
st.sidebar.markdown(f"### 👤 {st.session_state.user}")
st.sidebar.markdown(f"**Qualifica:** {st.session_state.role}")
st.sidebar.divider()

nav = st.sidebar.radio("NAVIGAZIONE MODULI", 
    ["🏠 DASHBOARD", "📍 MAPPA VISIVA STANZE", "📑 DIARIO CLINICO INTEGRATO", "📅 AGENDA APPUNTAMENTI", "💰 CASSA E CONTABILITÀ", "⚙️ AMMINISTRAZIONE"])

if st.sidebar.button("LOGOUT"):
    st.session_state.auth = False
    st.rerun()

# --- DATI PAZIENTI ---
PAZIENTI = ["Rossi Mario", "Bianchi Luigi", "Verdi Giuseppe", "Esposito Ciro", "Russo Antonio", "Costa Elena", "Gallo Paolo"]

# --- 1. MODULO MAPPA VISIVA (LOGICA AVANZATA) ---
if nav == "📍 MAPPA VISIVA STANZE":
    st.header("📍 Gestione e Monitoraggio Posti Letto")
    
    with st.expander("🔄 ESEGUI SPOSTAMENTO O ASSEGNAZIONE", expanded=True):
        c1, c2, c3 = st.columns(3)
        p_name = c1.selectbox("Seleziona Paziente", PAZIENTI)
        st_num = c2.selectbox("Stanza", [f"Stanza {i}" for i in range(101, 116)])
        lt_pos = c3.selectbox("Letto", ["Letto A (Sinistra)", "Letto B (Destra)"])
        not_sp = st.text_area("Note Tecniche (es. Riparazione letto, Necessità clinica)")
        
        if st.button("CONFERMA SPOSTAMENTO"):
            now_agg = datetime.now().strftime("%d/%m/%Y %H:%M")
            db_conn.execute("INSERT OR REPLACE INTO stanze VALUES (?,?,?,?,?,?)", 
                          (p_name, st_num, lt_pos, not_sp, now_agg, st.session_state.user))
            db_conn.commit()
            st.success(f"Paziente {p_name} correttamente assegnato alla {st_num}")

    st.subheader("Visualizzazione Spaziale Reparto")
    df_stz = pd.read_sql("SELECT * FROM stanze", db_conn)
    if not df_stz.empty:
        fig = px.scatter(df_stz, x="stanza", y="letto", text="paziente", color="stanza",
                         height=600, title="Occupazione Letti Real-Time")
        fig.update_traces(textposition='top center', marker=dict(size=40, symbol='square'))
        st.plotly_chart(fig, use_container_width=True)

# --- 2. DIARIO CLINICO INTEGRATO (AGGIUNTA 3 FIGURE PROFESSIONALI) ---
elif nav == "📑 DIARIO CLINICO INTEGRATO":
    st.header("📖 Registro Unificato Multidisciplinare")

    # --- INNESTO: AREA PSICOLOGO ---
    if st.session_state.role in ["Psicologo", "Admin"]:
        with st.expander("🧠 MODULO PSICOLOGIA - Note Cliniche", expanded=(st.session_state.role=="Psicologo")):
            cp1, cp2 = st.columns(2)
            ps_pax = cp1.selectbox("Paziente", PAZIENTI, key="ps_p")
            ps_tipo = cp2.selectbox("Attività", ["Colloquio Supporto", "Valutazione Diagnostica", "Test MMPI-2", "Relazione Clinica"])
            ps_nota = st.text_area("Annotazioni Cliniche Dettagliate", height=200)
            if st.button("SALVA NOTA PSICOLOGICA"):
                db_conn.execute("INSERT INTO diario (data, ora, paziente, nota, autore, ruolo_autore, categoria) VALUES (?,?,?,?,?,?,?)",
                              (date.today().strftime("%d/%m/%Y"), datetime.now().strftime("%H:%M"), ps_pax, f"[{ps_tipo}] {ps_nota}", st.session_state.user, "Psicologo", "PSICOLOGIA"))
                db_conn.commit()
                st.success("Nota Psicologica salvata.")

    # --- INNESTO: AREA ASSISTENTE SOCIALE ---
    if st.session_state.role in ["Assistente Sociale", "Admin"]:
        with st.expander("🤝 MODULO SOCIALE - Progetti e Territorio", expanded=(st.session_state.role=="Assistente Sociale")):
            cs1, cs2 = st.columns(2)
            so_pax = cs1.selectbox("Paziente", PAZIENTI, key="so_p")
            so_ente = cs2.text_input("Ente di Riferimento (Tribunale/UEPE/Comune)")
            so_nota = st.text_area("Resoconto Intervento Sociale", height=200)
            if st.button("SALVA NOTA SOCIALE"):
                db_conn.execute("INSERT INTO diario (data, ora, paziente, nota, autore, ruolo_autore, categoria) VALUES (?,?,?,?,?,?,?)",
                              (date.today().strftime("%d/%m/%Y"), datetime.now().strftime("%H:%M"), so_pax, f"Rif: {so_ente} | {so_nota}", st.session_state.user, "Assistente Sociale", "SOCIALE"))
                db_conn.commit()
                st.success("Intervento sociale registrato.")

    # --- INNESTO: AREA OPSI (SICUREZZA INTERNA) ---
    if st.session_state.role in ["OPSI", "Admin"]:
        with st.expander("🛡️ MODULO SICUREZZA INTERNA (OPSI)", expanded=(st.session_state.role=="OPSI")):
            co1, co2 = st.columns(2)
            op_pax = co1.selectbox("Paziente Coinvolto", ["Generale/Reparto"] + PAZIENTI, key="op_p")
            op_att = co2.selectbox("Tipo Controllo", ["Ronda Perimetrale", "Ispezione Camera", "Rapporto Disciplinare", "Controllo Barriere"])
            op_crit = st.select_slider("Livello Criticità Rilevata", options=["VERDE", "GIALLO", "ARANCIO", "ROSSO"])
            op_nota = st.text_area("Report di Sicurezza", height=200)
            if st.button("REGISTRA REPORT OPSI"):
                db_conn.execute("INSERT INTO diario (data, ora, paziente, nota, autore, ruolo_autore, categoria, criticita) VALUES (?,?,?,?,?,?,?,?)",
                              (date.today().strftime("%d/%m/%Y"), datetime.now().strftime("%H:%M"), op_pax, f"[{op_att}] {op_nota}", st.session_state.user, "OPSI", "SICUREZZA", op_crit))
                db_conn.commit()
                st.warning("Report di sicurezza archiviato.")

    st.divider()
    st.subheader("📋 Cronologia Interventi del Reparto")
    # Filtro Dinamico
    filt_pax = st.selectbox("Filtra per Paziente", ["TUTTI"] + PAZIENTI)
    df_diario = pd.read_sql("SELECT data, ora, paziente, categoria, nota, ruolo_autore, criticita FROM diario", db_conn)
    df_diario = df_diario.sort_values(by=["data", "ora"], ascending=False)
    if filt_pax != "TUTTI":
        df_diario = df_diario[df_diario['paziente'] == filt_pax]
    st.dataframe(df_diario, use_container_width=True, height=500)

# --- 3. AGENDA APPUNTAMENTI (LOGICA ORIGINALE) ---
elif nav == "📅 AGENDA APPUNTAMENTI":
    st.header("📅 Gestione Eventi e Appuntamenti")
    with st.form("form_app"):
        col_a, col_b = st.columns(2)
        dt = col_a.date_input("Giorno")
        tm = col_a.time_input("Orario")
        px = col_b.selectbox("Paziente", PAZIENTI)
        mg = col_b.text_input("Oggetto dell'Impegno")
        if st.form_submit_button("REGISTRA APPUNTAMENTO"):
            db_conn.execute("INSERT INTO appuntamenti (data, ora, paziente, impegno) VALUES (?,?,?,?)", 
                          (str(dt), str(tm), px, mg))
            db_conn.commit()
            st.success("Inserito correttamente.")

    df_app = pd.read_sql("SELECT data, ora, paziente, impegno FROM appuntamenti ORDER BY data ASC", db_conn)
    st.table(df_app)

# --- 4. CASSA E CONTABILITÀ (LOGICA BILANCIO ORIGINALE) ---
elif nav == "💰 CASSA E CONTABILITÀ":
    st.header("💰 Gestione Cassa Personale Pazienti")
    p_cassa = st.selectbox("Paziente", PAZIENTI)
    col1_c, col2_c = st.columns(2)
    with col1_c:
        op_c = st.radio("Tipo Operazione", ["DEPOSITO", "PRELIEVO"])
        val_c = st.number_input("Importo (€)", min_value=0.0, step=1.0)
    with col2_c:
        cau_c = st.text_area("Causale")
        if st.button("ESEGUI MOVIMENTO"):
            importo_reale = val_c if op_c == "DEPOSITO" else -val_c
            db_conn.execute("INSERT INTO cassa (data, paziente, tipo_operazione, importo, causale, operatore) VALUES (?,?,?,?,?,?)",
                          (datetime.now().strftime("%Y-%m-%d"), p_cassa, op_c, importo_reale, cau_c, st.session_state.user))
            db_conn.commit()
            st.success("Operazione registrata.")
    
    st.subheader("Saldo Attuale")
    df_cassa = pd.read_sql(f"SELECT SUM(importo) as saldo FROM cassa WHERE paziente = '{p_cassa}'", db_conn)
    saldo = df_cassa['saldo'][0] if df_cassa['saldo'][0] else 0.0
    st.metric(label=f"Fondi disponibili per {p_cassa}", value=f"{saldo} €")

# --- 5. AMMINISTRAZIONE (Logica Invariata) ---
elif nav == "⚙️ AMMINISTRAZIONE":
    if st.session_state.role == "Admin":
        st.header("⚙️ Pannello di Controllo Amministratore")
        st.table(pd.read_sql("SELECT username, ruolo, data_creazione FROM utenti", db_conn))
    else:
        st.error("Accesso riservato.")

st.sidebar.markdown("---")
st.sidebar.caption("SISTEMA GESTIONALE REMS v29.0 - Codice Integrale Certificato")
