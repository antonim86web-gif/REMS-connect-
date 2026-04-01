import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import plotly.express as px

# --- CONFIGURAZIONE PROFESSIONALE ---
st.set_page_config(page_title="SISTEMA GESTIONALE REMS v29.0", layout="wide", page_icon="🏥")

# --- MOTORE DATABASE (STRUTTURA ORIGINALE INTEGRATA) ---
def init_db():
    conn = sqlite3.connect('rems_final_v12.db', check_same_thread=False)
    c = conn.cursor()
    # Tabella Utenti (Per Login e Registrazione come all'inizio)
    c.execute('''CREATE TABLE IF NOT EXISTS utenti 
                 (username TEXT PRIMARY KEY, password TEXT, ruolo TEXT)''')
    # Tabella Diario
    c.execute('''CREATE TABLE IF NOT EXISTS diario 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, paziente TEXT, nota TEXT, autore TEXT, ruolo_autore TEXT, categoria TEXT)''')
    # Tabella Stanze
    c.execute('''CREATE TABLE IF NOT EXISTS stanze 
                 (paziente TEXT PRIMARY KEY, stanza TEXT, letto TEXT, data_aggiornamento TEXT)''')
    # Tabella Appuntamenti
    c.execute('''CREATE TABLE IF NOT EXISTS appuntamenti 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ora TEXT, paziente TEXT, impegno TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- FUNZIONI DI SICUREZZA ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# --- LOGICA DI ACCESSO (LOGIN / REGISTRAZIONE) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = ""
    st.session_state.ruolo = ""

if not st.session_state.logged_in:
    st.title("🔐 Portale di Accesso REMS")
    tab_log, tab_reg = st.tabs(["Login", "Nuova Registrazione"])

    with tab_log:
        user = st.text_input("Username")
        psw = st.text_input("Password", type="password")
        if st.button("Accedi"):
            c = conn.cursor()
            c.execute("SELECT password, ruolo FROM utenti WHERE username = ?", (user,))
            data = c.fetchone()
            if data and check_hashes(psw, data[0]):
                st.session_state.logged_in = True
                st.session_state.user = user
                st.session_state.ruolo = data[1]
                st.success(f"Benvenuto {user} ({data[1]})")
                st.rerun()
            else:
                st.error("Username o Password errati")

    with tab_reg:
        new_user = st.text_input("Scegli Username")
        new_psw = st.text_input("Scegli Password", type="password")
        new_ruolo = st.selectbox("Seleziona il tuo Ruolo", 
                                ["Medico", "Infermiere", "OSS", "Educatore", "Psicologo", "Assistente Sociale", "OPSI", "Admin"])
        if st.button("Registrati"):
            try:
                c = conn.cursor()
                c.execute("INSERT INTO utenti (username, password, ruolo) VALUES (?,?,?)", 
                          (new_user, make_hashes(new_psw), new_ruolo))
                conn.commit()
                st.success("Registrazione completata! Ora puoi effettuare il Login.")
            except sqlite3.IntegrityError:
                st.error("Questo Username esiste già.")
    st.stop()

# --- INTERFACCIA POST-LOGIN ---
st.sidebar.title(f"👤 {st.session_state.user}")
st.sidebar.info(f"Ruolo: {st.session_state.ruolo}")
menu = st.sidebar.radio("Vai a:", ["Mappa Stanze", "Diario Clinico", "Appuntamenti", "Cassa Pazienti", "Area Personale"])

if st.sidebar.button("Log Out"):
    st.session_state.logged_in = False
    st.rerun()

lista_pazienti = ["Rossi Mario", "Bianchi Luigi", "Verdi Giuseppe", "Esposito Ciro", "Russo Antonio"]

# --- 1. MODULO MAPPA STANZE (TUTTI OPERATIVI) ---
if menu == "Mappa Stanze":
    st.header("📍 Mappa Posti Letto")
    with st.expander("🔄 Gestisci Posizione Paziente"):
        c1, c2, c3 = st.columns(3)
        pax = c1.selectbox("Paziente", lista_pazienti)
        stz = c2.selectbox("Stanza", [f"Stanza {i}" for i in range(101, 110)])
        letto = c3.selectbox("Letto", ["A", "B"])
        if st.button("Aggiorna Database"):
            now = datetime.now().strftime("%d/%m/%Y %H:%M")
            conn.execute("INSERT OR REPLACE INTO stanze (paziente, stanza, letto, data_aggiornamento) VALUES (?,?,?,?)", (pax, stz, letto, now))
            conn.commit()
            st.success("Posizione aggiornata.")

    df_s = pd.read_sql("SELECT * FROM stanze", conn)
    if not df_s.empty:
        fig = px.scatter(df_s, x="stanza", y="letto", text="paziente", title="Mappa Visiva REMS", color="stanza")
        fig.update_traces(textposition='top center', marker=dict(size=25))
        st.plotly_chart(fig, use_container_width=True)

# --- 2. DIARIO CLINICO CON LE 3 NUOVE AREE ---
elif menu == "Diario Clinico":
    st.header("📖 Diario Clinico e Specialistico")

    # Logica per Psicologo e Admin
    if st.session_state.ruolo in ['Psicologo', 'Admin']:
        with st.expander("🧠 AREA PSICOLOGICA", expanded=(st.session_state.ruolo == 'Psicologo')):
            p_pax = st.selectbox("Paziente", lista_pazienti, key="p1")
            p_nota = st.text_area("Note Cliniche / Test", key="n1")
            if st.button("Salva Nota"):
                conn.execute("INSERT INTO diario (data, paziente, nota, autore, ruolo_autore, categoria) VALUES (?,?,?,?,?,?)",
                             (datetime.now().strftime("%d/%m/%Y %H:%M"), p_pax, p_nota, st.session_state.user, st.session_state.ruolo, "PSICOLOGIA"))
                conn.commit()
                st.success("Archiviata.")

    # Logica per Assistente Sociale e Admin
    if st.session_state.ruolo in ['Assistente Sociale', 'Admin']:
        with st.expander("🤝 AREA SOCIALE", expanded=(st.session_state.ruolo == 'Assistente Sociale')):
            s_pax = st.selectbox("Paziente", lista_pazienti, key="s1")
            s_nota = st.text_area("Relazione Sociale / Territorio", key="sn1")
            if st.button("Registra Attività Sociale"):
                conn.execute("INSERT INTO diario (data, paziente, nota, autore, ruolo_autore, categoria) VALUES (?,?,?,?,?,?)",
                             (datetime.now().strftime("%d/%m/%Y %H:%M"), s_pax, s_nota, st.session_state.user, st.session_state.ruolo, "SOCIALE"))
                conn.commit()
                st.success("Registrato.")

    # Logica per OPSI e Admin
    if st.session_state.ruolo in ['OPSI', 'Admin']:
        with st.expander("🛡️ AREA SICUREZZA (OPSI)", expanded=(st.session_state.ruolo == 'OPSI')):
            o_pax = st.selectbox("Paziente", ["Generale"] + lista_pazienti, key="o1")
            o_nota = st.text_area("Report Sicurezza / Ispezione", key="on1")
            if st.button("Invia Report OPSI"):
                conn.execute("INSERT INTO diario (data, paziente, nota, autore, ruolo_autore, categoria) VALUES (?,?,?,?,?,?)",
                             (datetime.now().strftime("%d/%m/%Y %H:%M"), o_pax, o_nota, st.session_state.user, st.session_state.ruolo, "SICUREZZA"))
                conn.commit()
                st.warning("Report di sicurezza salvato.")

    st.divider()
    st.subheader("📜 Cronologia")
    df_d = pd.read_sql("SELECT data, paziente, categoria, nota, ruolo_autore FROM diario ORDER BY id DESC", conn)
    st.table(df_d)

# --- 3. APPUNTAMENTI (MODIFICA APERTA A TUTTI) ---
elif menu == "Appuntamenti":
    st.header("📅 Agenda Appuntamenti")
    with st.form("app_form"):
        col1, col2 = st.columns(2)
        d = col1.date_input("Giorno")
        o = col1.time_input("Ora")
        p = col2.selectbox("Paziente", lista_pazienti)
        i = col2.text_input("Impegno")
        if st.form_submit_button("Fissa Appuntamento"):
            conn.execute("INSERT INTO appuntamenti (data, ora, paziente, impegno) VALUES (?,?,?,?)", (str(d), str(o), p, i))
            conn.commit()
            st.success("Inserito.")
    
    st.table(pd.read_sql("SELECT * FROM appuntamenti ORDER BY data, ora", conn))

# --- 4. PANNELLO ADMIN ---
elif menu == "Area Personale":
    if st.session_state.ruolo == "Admin":
        st.header("⚙️ Pannello Admin")
        st.write("Utenti registrati nel sistema:")
        st.table(pd.read_sql("SELECT username, ruolo FROM utenti", conn))
    else:
        st.error("Riservato ad Admin.")
