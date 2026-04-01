import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image

# --- CONFIGURAZIONE INTEGRALE v29.0 (NESSUNA SEMPLIFICAZIONE) ---
st.set_page_config(page_title="SISTEMA GESTIONALE REMS - INTEGRALE", layout="wide", page_icon="🏥")

# --- MOTORE DATABASE ORIGINALE ---
def init_db():
    conn = sqlite3.connect('rems_final_v12.db', check_same_thread=False)
    c = conn.cursor()
    # Struttura utenti originale
    c.execute('''CREATE TABLE IF NOT EXISTS utenti 
                 (username TEXT PRIMARY KEY, password TEXT, ruolo TEXT, data_creazione TEXT)''')
    # Struttura diario completa (con colonne per le nuove figure)
    c.execute('''CREATE TABLE IF NOT EXISTS diario 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  data TEXT, 
                  paziente TEXT, 
                  nota TEXT, 
                  autore TEXT, 
                  ruolo_autore TEXT, 
                  categoria TEXT,
                  criticita TEXT)''')
    # Tabella stanze originale
    c.execute('''CREATE TABLE IF NOT EXISTS stanze 
                 (paziente TEXT PRIMARY KEY, stanza TEXT, letto TEXT, note_spostamento TEXT, data_agg TEXT)''')
    # Tabella appuntamenti originale
    c.execute('''CREATE TABLE IF NOT EXISTS appuntamenti 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ora TEXT, paziente TEXT, impegno TEXT, esito TEXT)''')
    # Tabella Cassa originale
    c.execute('''CREATE TABLE IF NOT EXISTS cassa 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, paziente TEXT, operazione TEXT, importo REAL, causale TEXT, operatore TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- UTILITIES DI SICUREZZA ORIGINALI ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text: return hashed_text
    return False

# --- LOGICA DI ACCESSO INTEGRALE (LOGIN/REGISTRAZIONE) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.ruolo = ""

if not st.session_state.logged_in:
    st.title("🏥 REMS Connect - Sistema Certificato")
    tab_log, tab_reg = st.tabs(["🔐 LOGIN OPERATORE", "📝 NUOVA REGISTRAZIONE"])

    with tab_log:
        with st.container():
            u = st.text_input("Username", key="log_u")
            p = st.text_input("Password", type="password", key="log_p")
            if st.button("ACCEDI AL SISTEMA", use_container_width=True):
                c = conn.cursor()
                c.execute("SELECT password, ruolo FROM utenti WHERE username = ?", (u,))
                res = c.fetchone()
                if res and check_hashes(p, res[0]):
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    st.session_state.ruolo = res[1]
                    st.rerun()
                else:
                    st.error("Credenziali non valide o utente non registrato.")

    with tab_reg:
        with st.container():
            nu = st.text_input("Scegli Username", key="reg_u")
            np = st.text_input("Scegli Password", type="password", key="reg_p")
            nr = st.selectbox("Seleziona Ruolo Professionale", 
                             ["Medico", "Infermiere", "OSS", "Educatore", "Psicologo", "Assistente Sociale", "OPSI", "Admin"])
            codice_h = st.text_input("Codice Autorizzazione Struttura", type="password")
            if st.button("REGISTRA NUOVO OPERATORE", use_container_width=True):
                if codice_h == "REMS2024": # Codice di sicurezza per evitare registrazioni esterne
                    try:
                        c = conn.cursor()
                        now_c = datetime.now().strftime("%d/%m/%Y %H:%M")
                        c.execute("INSERT INTO utenti VALUES (?,?,?,?)", (nu, make_hashes(np), nr, now_c))
                        conn.commit()
                        st.success("Registrazione effettuata. Passa alla scheda Login.")
                    except:
                        st.error("Username già occupato.")
                else:
                    st.error("Codice Autorizzazione Errato.")
    st.stop()

# --- DASHBOARD PRINCIPALE (v28.1 COMPLETA) ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/6840/6840438.png", width=100)
st.sidebar.title(f"Operatore: {st.session_state.username}")
st.sidebar.subheader(f"Ruolo: {st.session_state.ruolo}")

menu = st.sidebar.radio("MODULI DI GESTIONE", 
    ["MAPPA POSTI LETTO", "DIARIO CLINICO & SPECIALISTICO", "AGENDA APPUNTAMENTI", "CASSA PAZIENTI", "BACKUP & ADMIN"])

if st.sidebar.button("CHIUDI SESSIONE (LOGOUT)"):
    st.session_state.logged_in = False
    st.rerun()

# --- DATI PAZIENTI (MANTENUTI ORIGINALI) ---
lista_pazienti = ["Rossi Mario", "Bianchi Luigi", "Verdi Giuseppe", "Esposito Ciro", "Russo Antonio", "Costa Elena"]

# --- 1. MODULO MAPPA POSTI LETTO (INVARIATO) ---
if menu == "MAPPA POSTI LETTO":
    st.header("📍 Monitoraggio Occupazione Stanze")
    with st.expander("🔄 AZIONI SPOSTAMENTO (Abilitato per tutti i ruoli)"):
        c1, c2, c3 = st.columns(3)
        p_sel = c1.selectbox("Paziente", lista_pazienti)
        s_sel = c2.selectbox("Stanza", [f"Stanza {i}" for i in range(101, 115)])
        l_sel = c3.selectbox("Letto", ["A", "B"])
        nota_s = st.text_input("Motivazione dello spostamento")
        if st.button("ESEGUI SPOSTAMENTO"):
            now_s = datetime.now().strftime("%d/%m/%Y %H:%M")
            conn.execute("INSERT OR REPLACE INTO stanze VALUES (?,?,?,?,?)", (p_sel, s_sel, l_sel, nota_s, now_s))
            conn.commit()
            st.success(f"Paziente {p_sel} riposizionato con successo.")

    # Visualizzazione Mappa Grafica
    df_s = pd.read_sql("SELECT * FROM stanze", conn)
    if not df_s.empty:
        fig = px.scatter(df_s, x="stanza", y="letto", text="paziente", color="stanza", height=500, title="Visualizzazione Spaziale Reparto")
        fig.update_traces(textposition='top center', marker=dict(size=30, symbol='square'))
        st.plotly_chart(fig, use_container_width=True)

# --- 2. DIARIO CLINICO & SPECIALISTICO (INNESTO DELLE 3 FIGURE) ---
elif menu == "DIARIO CLINICO & SPECIALISTICO":
    st.header("📖 Registro Unificato Interventi")
    
    # --- INNESTO: AREA PSICOLOGO ---
    if st.session_state.ruolo in ["Psicologo", "Admin"]:
        with st.expander("🧠 AREA PSICOLOGIA (Modifica Abilitata)", expanded=(st.session_state.ruolo == "Psicologo")):
            cp1, cp2 = st.columns(2)
            p_psic = cp1.selectbox("Paziente", lista_pazienti, key="ps_1")
            t_psic = cp2.selectbox("Tipo Attività", ["Colloquio", "Test Valutazione", "Sostegno", "Relazione"], key="ps_2")
            n_psic = st.text_area("Annotazioni Cliniche", height=100)
            if st.button("ARCHIVIA NOTA PSICOLOGO"):
                conn.execute("INSERT INTO diario (data, paziente, nota, autore, ruolo_autore, categoria) VALUES (?,?,?,?,?,?)",
                             (datetime.now().strftime("%d/%m/%Y %H:%M"), p_psic, f"[{t_psic}] {n_psic}", st.session_state.username, "Psicologo", "PSICOLOGIA"))
                conn.commit()
                st.success("Nota salvata.")

    # --- INNESTO: AREA ASSISTENTE SOCIALE ---
    if st.session_state.ruolo in ["Assistente Sociale", "Admin"]:
        with st.expander("🤝 AREA ASSISTENTE SOCIALE (Modifica Abilitata)", expanded=(st.session_state.ruolo == "Assistente Sociale")):
            cs1, cs2 = st.columns(2)
            p_soc = cs1.selectbox("Paziente", lista_pazienti, key="so_1")
            e_soc = cs2.text_input("Ente/Famiglia di riferimento", key="so_2")
            n_soc = st.text_area("Relazione Sociale e Progettuale", height=100)
            if st.button("ARCHIVIA NOTA SOCIALE"):
                conn.execute("INSERT INTO diario (data, paziente, nota, autore, ruolo_autore, categoria) VALUES (?,?,?,?,?,?)",
                             (datetime.now().strftime("%d/%m/%Y %H:%M"), p_soc, f"Rif: {e_soc} | {n_soc}", st.session_state.username, "Assistente Sociale", "SOCIALE"))
                conn.commit()
                st.success("Dati sociali registrati.")

    # --- INNESTO: AREA OPSI (SICUREZZA INTERNA) ---
    if st.session_state.ruolo in ["OPSI", "Admin"]:
        with st.expander("🛡️ AREA OPSI - SICUREZZA (Modifica Abilitata)", expanded=(st.session_state.ruolo == "OPSI")):
            co1, co2 = st.columns(2)
            p_opsi = co1.selectbox("Paziente Coinvolto", ["Nessuno/Generale"] + lista_pazienti, key="op_1")
            t_opsi = co2.selectbox("Attività Sicurezza", ["Ispezione Camere", "Ronda", "Evento Critico", "Sequestro Oggetti"], key="op_2")
            crit_opsi = st.select_slider("Livello Allerta", options=["VERDE", "GIALLO", "ARANCIO", "ROSSO"])
            n_opsi = st.text_area("Report di Sicurezza", height=100)
            if st.button("INVIA REPORT OPSI"):
                conn.execute("INSERT INTO diario (data, paziente, nota, autore, ruolo_autore, categoria, criticita) VALUES (?,?,?,?,?,?,?)",
                             (datetime.now().strftime("%d/%m/%Y %H:%M"), p_opsi, f"[{t_opsi}] {n_opsi}", st.session_state.username, "OPSI", "SICUREZZA", crit_opsi))
                conn.commit()
                st.warning("Report di sicurezza archiviato.")

    st.markdown("---")
    # Visualizzazione Cronologia Completa (Per tutti in lettura)
    st.subheader("📋 Cronologia Diario Integrata")
    filtro_p = st.selectbox("Filtra per Paziente", ["TUTTI"] + lista_pazienti)
    
    query = "SELECT data, paziente, categoria, nota, ruolo_autore, criticita FROM diario"
    if filtro_p != "TUTTI": query += f" WHERE paziente = '{filtro_p}'"
    query += " ORDER BY id DESC"
    
    df_d = pd.read_sql(query, conn)
    st.dataframe(df_d, use_container_width=True, height=400)

# --- 3. AGENDA APPUNTAMENTI (INVARIATO) ---
elif menu == "AGENDA APPUNTAMENTI":
    st.header("📅 Gestione Appuntamenti ed Eventi")
    with st.form("new_app"):
        col1, col2, col3 = st.columns(3)
        data_a = col1.date_input("Data")
        ora_a = col2.time_input("Ora")
        pax_a = col3.selectbox("Paziente", lista_pazienti)
        imp_a = st.text_input("Oggetto dell'impegno")
        if st.form_submit_button("REGISTRA APPUNTAMENTO"):
            conn.execute("INSERT INTO appuntamenti (data, ora, paziente, impegno) VALUES (?,?,?,?)", (str(data_a), str(ora_a), pax_a, imp_a))
            conn.commit()
            st.success("Inserito in agenda.")
    
    df_app = pd.read_sql("SELECT data, ora, paziente, impegno FROM appuntamenti ORDER BY data ASC", conn)
    st.table(df_app)

# --- 4. CASSA PAZIENTI (INVARIATO) ---
elif menu == "CASSA PAZIENTI":
    st.header("💰 Gestione Cassa Personale Pazienti")
    # Logica di deposito/prelievo complessa come nella v28.1
    c_pax = st.selectbox("Seleziona Paziente", lista_pazienti, key="cassa_p")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        operazione = st.radio("Operazione", ["DEPOSITO", "PRELIEVO"])
        importo = st.number_input("Importo (€)", min_value=0.0, step=0.5)
    with col_c2:
        causale = st.text_input("Causale")
        if st.button("REGISTRA MOVIMENTO CASSA"):
            val = importo if operazione == "DEPOSITO" else -importo
            conn.execute("INSERT INTO cassa (data, paziente, operazione, importo, causale, operatore) VALUES (?,?,?,?,?,?)",
                         (datetime.now().strftime("%d/%m/%Y"), c_pax, operazione, val, causale, st.session_state.username))
            conn.commit()
            st.success("Movimento registrato.")

# --- 5. BACKUP & ADMIN (INVARIATO) ---
elif menu == "BACKUP & ADMIN":
    if st.session_state.ruolo == "Admin":
        st.header("⚙️ Pannello di Controllo Amministratore")
        tab1, tab2 = st.tabs(["📊 Statistiche", "🔐 Gestione Utenti"])
        with tab1:
            st.subheader("Analisi Interventi per Ruolo")
            df_stat = pd.read_sql("SELECT ruolo_autore, COUNT(*) as conteggio FROM diario GROUP BY ruolo_autore", conn)
            st.bar_chart(df_stat.set_index("ruolo_autore"))
        with tab2:
            st.subheader("Elenco Operatori Registrati")
            st.table(pd.read_sql("SELECT username, ruolo, data_creazione FROM utenti", conn))
    else:
        st.error("Accesso riservato agli Amministratori.")

# --- FINE CODICE v29.0 ---
