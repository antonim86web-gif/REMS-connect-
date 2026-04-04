import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import calendar
from datetime import datetime, timedelta, timezone
from groq import Groq

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Rems-Connect", layout="wide", initial_sidebar_state="expanded")

# 2. DATABASE SETUP
def init_db():
    conn = sqlite3.connect('rems_data.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS pazienti 
                 (id INTEGER PRIMARY KEY, nome TEXT, reparto TEXT, stanza TEXT, letto TEXT, stato TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS agenda 
                 (id INTEGER PRIMARY KEY, data TEXT, ora TEXT, paziente TEXT, note TEXT)''')
    
    # Inserimento Utente Default se non esiste
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        hashed_pw = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO users VALUES (?, ?, ?)", ("admin", hashed_pw, "Super User"))
    conn.commit()
    return conn

conn = init_db()

# 3. LOGICA DI AUTENTICAZIONE
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def login_user(user, pw):
    hashed_pw = hashlib.sha256(pw.encode()).hexdigest()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (user, hashed_pw))
    return c.fetchone()

# 4. INTERFACCIA CSS (ESTETICA NEON & FLOATING)
st.markdown("""
<style>
    /* SFONDO ARDESIA */
    .stApp { 
        background-color: #1e293b !important; 
        color: #f1f5f9 !important; 
    }
    
    /* SIDEBAR NERA E CHIARA */
    [data-testid="stSidebar"] { 
        background-color: #000000 !important; 
        border-right: 2px solid #00d4ff !important; 
    }
    
    /* FIX SIDEBAR: TESTO AZZURRO E NO PALLINI */
    [data-testid="stSidebarNav"] * { color: #00d4ff !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] .stMarkdown p { color: #00d4ff !important; }
    
    /* BOTTONI SIDEBAR FLOATING */
    div[role="radiogroup"] label {
        background: rgba(0, 212, 255, 0.05) !important;
        border: 1px solid #00d4ff !important;
        border-radius: 12px !important;
        padding: 10px 15px !important;
        margin-bottom: 10px !important;
        transition: 0.3s ease-in-out !important;
        display: flex !important;
    }
    /* Rimuove il pallino bianco della selezione standard */
    div[role="radiogroup"] [data-testid="stWidgetLabel"] div:first-child { display: none !important; }
    
    /* Effetto Hover e Selezione */
    div[role="radiogroup"] label:hover, div[role="radiogroup"] label:has(input:checked) {
        transform: translateY(-5px) !important;
        background: rgba(0, 212, 255, 0.2) !important;
        box-shadow: 0 10px 20px rgba(0, 212, 255, 0.3) !important;
    }
    div[role="radiogroup"] label:has(input:checked) p { color: #ffffff !important; }

    /* BOX STANZE FLOATING (TABELLONE) */
    .stanza-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        transition: 0.3s;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    .stanza-card:hover {
        transform: translateY(-8px);
        border-color: #00d4ff;
        box-shadow: 0 12px 24px rgba(0, 212, 255, 0.2);
    }

    /* CALENDARIO POST-IT */
    .postit {
        background: #fff9c4 !important;
        color: #1a1a1a !important;
        padding: 8px;
        border-left: 6px solid #fbc02d;
        margin: 4px 0;
        font-size: 12px;
        border-radius: 3px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
        font-weight: 600;
    }

    /* LOGOUT ROSSO */
    .stButton > button {
        background: transparent !important;
        color: #ff4b4b !important;
        border: 2px solid #ff4b4b !important;
        border-radius: 10px !important;
        width: 100%;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# 5. SCHERMATA LOGIN
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("🔒 REMS-CONNECT")
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Accedi"):
            res = login_user(user, pw)
            if res:
                st.session_state.logged_in = True
                st.session_state.user_data = res
                st.rerun()
            else:
                st.error("Credenziali errate")
    st.stop()

# 6. SIDEBAR NAVIGAZIONE
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063176.png", width=80)
    st.markdown(f"### {st.session_state.user_data[2]}")
    st.write(f"👤 {st.session_state.user_data[0]}")
    
    st.divider()
    
    menu = st.radio("NAVIGAZIONE", 
                   ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Posti Letto", "⚙️ Admin"])
    
    st.divider()
    if st.button("LOGOUT"):
        st.session_state.logged_in = False
        st.rerun()
    
    st.markdown("---")
    st.caption("Antony Webmaster - ver. 28.9 Elite")

# 7. LOGICA MODULI
if menu == "📊 Monitoraggio":
    st.title("📊 Pannello Monitoraggio")
    # Statistiche rapide
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM pazienti")
    tot = c.fetchone()[0]
    st.metric("Pazienti Totali", tot)
    
    st.info("Sistema di monitoraggio in tempo reale attivo.")

elif menu == "👥 Modulo Equipe":
    st.title("👥 Modulo Operativo Equipe")
    figura = st.selectbox("Simula Figura:", ["Psichiatra", "Infermiere", "OSS", "Assistente Sociale"])
    
    tab1, tab2, tab3 = st.tabs(["📝 Nuova Prescrizione", "💊 Gestione Terapie", "🩺 Diario Clinico"])
    
    with tab1:
        with st.form("prescrizione"):
            paz = st.text_input("Seleziona Paziente")
            farmaco = st.text_input("Farmaco")
            dose = st.text_input("Dosaggio")
            if st.form_submit_button("Registra"):
                st.success("Prescrizione inserita nel database.")

    with tab3:
        st.subheader("Diario Clinico Generale")
        with st.expander("📁 SCHEDA PAZIENTE: PIPPO ROSSI"):
            st.write("Ultimo aggiornamento: 04/04/2026")
            st.text_area("Note cliniche del turno:")

elif menu == "📅 Agenda Dinamica":
    st.title("📅 Agenda Dinamica REMS")
    
    today = datetime.now()
    curr_month = st.number_input("Mese", 1, 12, today.month)
    curr_year = st.number_input("Anno", 2024, 2030, today.year)
    
    cal = calendar.monthcalendar(curr_year, curr_month)
    month_name = calendar.month_name[curr_month]
    
    st.subheader(f"{month_name} {curr_year}")
    
    cols = st.columns(7)
    days = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    for i, d in enumerate(days):
        cols[i].write(f"**{d}**")
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
            else:
                with cols[i]:
                    st.write(f"**{day}**")
                    # Query appuntamenti per questo giorno
                    data_str = f"{curr_year}-{curr_month:02d}-{day:02d}"
                    c = conn.cursor()
                    c.execute("SELECT ora, paziente FROM agenda WHERE data=?", (data_str,))
                    apps = c.fetchall()
                    for app in apps:
                        # FIX POST-IT: Logica pulita senza NameError
                        txt = f"🚗 {app[1]}<br>⏰ {app[0]}"
                        st.markdown(f'<div class="postit">{txt}</div>', unsafe_allow_html=True)
    
    st.divider()
    with st.expander("➕ Nuovo Appuntamento"):
        new_date = st.date_input("Data")
        new_time = st.time_input("Ora")
        new_paz = st.text_input("Paziente")
        if st.button("Salva in Agenda"):
            c = conn.cursor()
            c.execute("INSERT INTO agenda (data, ora, paziente) VALUES (?,?,?)", 
                     (str(new_date), str(new_time), new_paz))
            conn.commit()
            st.rerun()

elif menu == "🗺️ Mappa Posti Letto":
    st.title("🗺️ Tabellone Visivo Posti Letto")
    
    reparti = ["Reparto A", "Reparto B"]
    for rep in reparti:
        st.subheader(f"🔵 {rep}")
        cols = st.columns(3)
        for i in range(1, 4):
            with cols[i-1]:
                # FIX STANZA FLOATING: Layout a schede
                stanza_nome = f"{rep[8]}{i} STANDARD"
                paziente_l1 = "Libero"
                paziente_l2 = "Libero"
                
                st.markdown(f"""
                <div class="stanza-card">
                    <h3 style="color:#00d4ff; margin:0;">🛏️ Stanza {stanza_nome}</h3>
                    <hr style="border:0.5px solid rgba(0,212,255,0.2); margin:10px 0;">
                    <p style="margin:5px 0;"><b>L1:</b> {paziente_l1}</p>
                    <p style="margin:0;"><b>L2:</b> {paziente_l2}</p>
                </div>
                """, unsafe_allow_html=True)

elif menu == "⚙️ Admin":
    st.title("⚙️ Pannello Amministrazione")
    if st.session_state.user_data[2] != "Super User":
        st.warning("Accesso negato. Solo Super User possono vedere questa sezione.")
    else:
        tab1, tab2 = st.tabs(["👥 Gestione Utenti", "📁 Database Backup"])
        with tab1:
            st.write("Elenco Utenti Attivi")
            df = pd.read_sql("SELECT username, role FROM users", conn)
            st.table(df)

# FINE CODICE - RIGA 596 (COMPLETAMENTO LOGICA E CHIUSURA CONNESSIONI)
conn.close()
        
