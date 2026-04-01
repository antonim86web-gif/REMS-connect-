import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import os

# --- CONFIGURAZIONE INTEGRALE v29.0 (NESSUNA SEMPLIFICAZIONE) ---
st.set_page_config(page_title="SISTEMA GESTIONALE REMS - ENTERPRISE", layout="wide", page_icon="🏥")

# --- MOTORE DATABASE ORIGINALE (STRUTTURA BLINDATA) ---
def init_db():
    conn = sqlite3.connect('rems_final_v12.db', check_same_thread=False)
    c = conn.cursor()
    # Tabella Utenti originale (Username, Password, Ruolo, Data)
    c.execute('''CREATE TABLE IF NOT EXISTS utenti 
                 (username TEXT PRIMARY KEY, password TEXT, ruolo TEXT, data_creazione TEXT)''')
    # Tabella Diario originale + colonna categoria e criticita per OPSI
    c.execute('''CREATE TABLE IF NOT EXISTS diario 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  data TEXT, 
                  paziente TEXT, 
                  nota TEXT, 
                  autore TEXT, 
                  ruolo_autore TEXT, 
                  categoria TEXT,
                  criticita TEXT)''')
    # Tabella Stanze con note e data aggiornamento
    c.execute('''CREATE TABLE IF NOT EXISTS stanze 
                 (paziente TEXT PRIMARY KEY, stanza TEXT, letto TEXT, note_spostamento TEXT, data_agg TEXT)''')
    # Tabella Appuntamenti completa
    c.execute('''CREATE TABLE IF NOT EXISTS appuntamenti 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ora TEXT, paziente TEXT, impegno TEXT, esito TEXT)''')
    # Tabella Cassa complessa
    c.execute('''CREATE TABLE IF NOT EXISTS cassa 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, paziente TEXT, operazione TEXT, importo REAL, causale TEXT, operatore TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- UTILITIES DI SICUREZZA (HASHING SHA256) ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text: return hashed_text
    return False

# --- LOGICA DI SESSIONE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.ruolo = ""

# --- INTERFACCIA DI ACCESSO (LOGIN & REGISTRAZIONE ORIGINALE) ---
if not st.session_state.logged_in:
    st.title("🏥 REMS CONNECT v29.0")
    st.markdown("### Portale Gestionale Sanitario")
    
    tab_log, tab_reg = st.tabs(["🔐 LOGIN OPERATORE", "📝 REGISTRAZIONE NUOVO PROFILO"])

    with tab_log:
        u = st.text_input("Username", key="login_user")
        p = st.text_input("Password", type="password", key="login_pass")
        if st.button("ACCEDI AL SISTEMA", use_container_width=True):
            c = conn.cursor()
            # La query che causava l'errore negli screenshot è stata ripristinata alla forma corretta
            c.execute("SELECT password, ruolo FROM utenti WHERE username = ?", (u,))
            result = c.fetchone()
            if result and check_hashes(p, result[0]):
                st.session_state.logged_in = True
                st.session_state.username = u
                st.session_state.ruolo = result[1]
                st.rerun()
            else:
                st.error("Accesso negato: Verificare Username e Password.")

    with tab_reg:
        nu = st.text_input("Scegli Username", key="reg_user")
        np = st.text_input("Scegli Password", type="password", key="reg_pass")
        nr = st.selectbox("Ruolo Professionale", 
                         ["Medico", "Infermiere", "OSS", "Educatore", "Psicologo", "Assistente Sociale", "OPSI", "Admin"])
        cod_sicurezza = st.text_input("Codice Autorizzazione Reparto", type="password")
        if st.button("CREA ACCOUNT", use_container_width=True):
            if cod_sicurezza == "REMS2024":
                try:
                    c = conn.cursor()
                    now_reg = datetime.now().strftime("%d/%m/%Y %H:%M")
                    c.execute("INSERT INTO utenti (username, password, ruolo, data_creazione) VALUES (?,?,?,?)", 
                             (nu, make_hashes(np), nr, now_reg))
                    conn.commit()
                    st.success("Account creato con successo! Effettua il login.")
                except sqlite3.IntegrityError:
                    st.error("Errore: Username già in uso.")
            else:
                st.error("Codice di sicurezza non valido.")
    st.stop()

# --- DASHBOARD OPERATIVA ---
st.sidebar.markdown(f"### 👤 {st.session_state.username}")
st.sidebar.markdown(f"**Ruolo:** {st.session_state.ruolo}")
st.sidebar.divider()

menu = st.sidebar.radio("NAVIGAZIONE MODULI", 
    ["📊 MAPPA VISIVA POSTI LETTO", "📑 DIARIO CLINICO INTEGRATO", "📅 AGENDA APPUNTAMENTI", "💰 GESTIONE CASSA", "⚙️ AREA ADMIN & BACKUP"])

if st.sidebar.button("LOGOUT / ESCI"):
    st.session_state.logged_in = False
    st.rerun()

lista_pazienti = ["Rossi Mario", "Bianchi Luigi", "Verdi Giuseppe", "Esposito Ciro", "Russo Antonio", "Costa Elena", "Gallo Paolo"]

# --- 1. MODULO MAPPA VISIVA (STRUTTURA COMPLESSA) ---
if menu == "📊 MAPPA VISIVA POSTI LETTO":
    st.header("📍 Mappa Posti Letto e Gestione Stanze")
    
    with st.expander("🔄 SPOSTAMENTO PAZIENTE / ASSEGNAZIONE", expanded=True):
        col1, col2, col3 = st.columns(3)
        p_sel = col1.selectbox("Paziente", lista_pazienti)
        s_sel = col2.selectbox("Stanza", [f"Stanza {i}" for i in range(101, 115)])
        l_sel = col3.selectbox("Letto", ["Letto A (Sx)", "Letto B (Dx)"])
        note_sp = st.text_area("Note sullo spostamento (es. necessità clinica, isolamento)")
        
        if st.button("SALVA SPOSTAMENTO IN DATABASE"):
            now_sp = datetime.now().strftime("%d/%m/%Y %H:%M")
            conn.execute("INSERT OR REPLACE INTO stanze VALUES (?,?,?,?,?)", (p_sel, s_sel, l_sel, note_sp, now_sp))
            conn.commit()
            st.success(f"Posizione aggiornata per {p_sel}")

    # Visualizzazione Grafica Avanzata con Plotly
    df_stanze = pd.read_sql("SELECT * FROM stanze", conn)
    if not df_stanze.empty:
        fig = px.scatter(df_stanze, x="stanza", y="letto", text="paziente", color="stanza",
                         title="Visualizzazione Occupazione Real-Time", height=500)
        fig.update_traces(textposition='top center', marker=dict(size=35, symbol='square-dot'))
        fig.update_layout(xaxis_title="Numero Stanza", yaxis_title="Posizione Letto")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nessun dato di occupazione presente. Utilizzare il modulo sopra per assegnare i pazienti.")

# --- 2. DIARIO CLINICO (INTEGRAZIONE 3 FIGURE) ---
elif menu == "📑 DIARIO CLINICO INTEGRATO":
    st.header("📖 Registro Diario Clinico Multidisciplinare")

    # --- INNESTO DINAMICO: AREA PSICOLOGO ---
    if st.session_state.ruolo in ["Psicologo", "Admin"]:
        with st.expander("🧠 MODULO PSICOLOGIA - Note e Valutazioni", expanded=(st.session_state.ruolo == "Psicologo")):
            c_p1, c_p2 = st.columns(2)
            p_ps = c_p1.selectbox("Paziente", lista_pazienti, key="ps_p")
            t_ps = c_p2.selectbox("Tipo Attività", ["Colloquio Clinico", "Somministrazione Test", "Valutazione Cognitiva", "Colloquio Familiare"])
            n_ps = st.text_area("Annotazioni dello Psicologo", height=150)
            if st.button("REGISTRA NOTA PSICOLOGICA"):
                conn.execute("INSERT INTO diario (data, paziente, nota, autore, ruolo_autore, categoria) VALUES (?,?,?,?,?,?)",
                             (datetime.now().strftime("%d/%m/%Y %H:%M"), p_ps, f"[{t_ps}] {n_ps}", st.session_state.username, "Psicologo", "PSICOLOGIA"))
                conn.commit()
                st.success("Nota salvata.")

    # --- INNESTO DINAMICO: AREA ASSISTENTE SOCIALE ---
    if st.session_state.ruolo in ["Assistente Sociale", "Admin"]:
        with st.expander("🤝 MODULO SOCIALE - Territorio e Famiglia", expanded=(st.session_state.ruolo == "Assistente Sociale")):
            c_s1, c_s2 = st.columns(2)
            p_soc = c_s1.selectbox("Paziente", lista_pazienti, key="so_p")
            e_soc = c_s2.text_input("Enti Coinvolti (es. UEPE, Comune, Tribunale)")
            n_soc = st.text_area("Relazione Sociale", height=150)
            if st.button("REGISTRA NOTA SOCIALE"):
                conn.execute("INSERT INTO diario (data, paziente, nota, autore, ruolo_autore, categoria) VALUES (?,?,?,?,?,?)",
                             (datetime.now().strftime("%d/%m/%Y %H:%M"), p_soc, f"Enti: {e_soc} | {n_soc}", st.session_state.username, "Assistente Sociale", "SOCIALE"))
                conn.commit()
                st.success("Intervento sociale registrato.")

    # --- INNESTO DINAMICO: AREA OPSI ---
    if st.session_state.ruolo in ["OPSI", "Admin"]:
        with st.expander("🛡️ MODULO SICUREZZA INTERNA (OPSI)", expanded=(st.session_state.ruolo == "OPSI")):
            c_o1, c_o2 = st.columns(2)
            p_opsi = c_o1.selectbox("Paziente", ["Generale"] + lista_pazienti, key="ops_p")
            t_opsi = c_o2.selectbox("Attività", ["Ronda", "Ispezione Stanza", "Rapporto Disciplinare", "Controllo Perimetrale"])
            criticita = st.select_slider("Livello di Criticità/Allerta", options=["BASSO", "MEDIO", "ALTO", "CRITICO"])
            n_opsi = st.text_area("Report di Sicurezza", height=150)
            if st.button("INVIA REPORT OPSI"):
                conn.execute("INSERT INTO diario (data, paziente, nota, autore, ruolo_autore, categoria, criticita) VALUES (?,?,?,?,?,?,?)",
                             (datetime.now().strftime("%d/%m/%Y %H:%M"), p_opsi, f"[{t_opsi}] {n_opsi}", st.session_state.username, "OPSI", "SICUREZZA", criticita))
                conn.commit()
                st.warning("Report di sicurezza archiviato.")

    st.divider()
    st.subheader("📋 Storico Diario Unificato")
    # Filtri avanzati
    f_paz = st.selectbox("Filtra per Paziente", ["TUTTI"] + lista_pazienti)
    f_cat = st.multiselect("Filtra per Categoria", ["PSICOLOGIA", "SOCIALE", "SICUREZZA", "MEDICA", "INFERMIERISTICA"], default=["PSICOLOGIA", "SOCIALE", "SICUREZZA"])
    
    query = "SELECT data, paziente, categoria, nota, ruolo_autore, criticita FROM diario"
    # Logica di filtraggio per la query
    df_diario = pd.read_sql(query, conn).sort_values(by="data", ascending=False)
    if f_paz != "TUTTI":
        df_diario = df_diario[df_diario['paziente'] == f_paz]
    
    st.dataframe(df_diario, use_container_width=True)

# --- 3. AGENDA APPUNTAMENTI (STRUTTURA ORIGINALE) ---
elif menu == "📅 AGENDA APPUNTAMENTI":
    st.header("📅 Gestione Appuntamenti e Scadenze")
    with st.form("nuovo_app_form"):
        col_a1, col_a2 = st.columns(2)
        d_a = col_a1.date_input("Data Evento")
        o_a = col_a1.time_input("Ora")
        p_a = col_a2.selectbox("Paziente", lista_pazienti)
        i_a = col_a2.text_input("Causale (es. Visita, Udienza, Colloquio)")
        if st.form_submit_button("REGISTRA IN AGENDA"):
            conn.execute("INSERT INTO appuntamenti (data, ora, paziente, impegno) VALUES (?,?,?,?)", (str(d_a), str(o_a), p_a, i_a))
            conn.commit()
            st.success("Evento registrato correttamente.")
    
    st.subheader("Primi Appuntamenti in Scadenza")
    df_app = pd.read_sql("SELECT data, ora, paziente, impegno FROM appuntamenti ORDER BY data, ora", conn)
    st.table(df_app)

# --- 4. GESTIONE CASSA (STRUTTURA COMPLESSA) ---
elif menu == "💰 GESTIONE CASSA":
    st.header("💰 Cassa Personale Pazienti")
    with st.container():
        p_c = st.selectbox("Paziente", lista_pazienti, key="cassa_pax")
        col_c1, col_c2 = st.columns(2)
        op = col_c1.radio("Operazione", ["DEPOSITO", "PRELIEVO"])
        valore = col_c1.number_input("Somma (€)", min_value=0.0, step=1.0)
        caus = col_c2.text_area("Causale Movimento")
        
        if st.button("ESEGUI MOVIMENTO CASSA"):
            segno = valore if op == "DEPOSITO" else -valore
            now_c = datetime.now().strftime("%d/%m/%Y")
            conn.execute("INSERT INTO cassa (data, paziente, operazione, importo, causale, operatore) VALUES (?,?,?,?,?,?)",
                         (now_c, p_c, op, segno, caus, st.session_state.username))
            conn.commit()
            st.success("Operazione di cassa registrata.")

    st.subheader("Estratto Conto Recente")
    df_cassa = pd.read_sql("SELECT * FROM cassa ORDER BY id DESC LIMIT 10", conn)
    st.dataframe(df_cassa, use_container_width=True)

# --- 5. AREA ADMIN & BACKUP (INVARIATO) ---
elif menu == "⚙️ AREA ADMIN & BACKUP":
    if st.session_state.ruolo == "Admin":
        st.header("⚙️ Pannello di Controllo Amministratore")
        tab1, tab2 = st.tabs(["📊 Analisi Dati", "🔐 Gestione Utenti"])
        
        with tab1:
            st.subheader("Statistiche Attività")
            df_stat = pd.read_sql("SELECT ruolo_autore, COUNT(*) as interventi FROM diario GROUP BY ruolo_autore", conn)
            fig_stat = px.pie(df_stat, values='interventi', names='ruolo_autore', title="Distribuzione Lavoro per Figura")
            st.plotly_chart(fig_stat)
            
        with tab2:
            st.subheader("Operatori Registrati")
            df_u = pd.read_sql("SELECT username, ruolo, data_creazione FROM utenti", conn)
            st.table(df_u)
    else:
        st.error("Accesso negato: Solo l'Amministratore può accedere a questo modulo.")

st.sidebar.divider()
st.sidebar.caption("REMS CONNECT v29.0 - Edizione Sicurezza & Salute")
