import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import calendar
from datetime import datetime

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
    
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        hashed_pw = hashlib.sha256("perito2026".encode()).hexdigest()
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

# 4. INTERFACCIA CSS (FIX SIDEBAR, FLOATING E POST-IT)
st.markdown("""
<style>
    /* SFONDO GENERALE ARDESIA */
    .stApp { background-color: #1e293b !important; color: #f1f5f9 !important; }
    
    /* SIDEBAR NERA CON BORDO AZZURRO */
    [data-testid="stSidebar"] { 
        background-color: #000000 !important; 
        border-right: 2px solid #00d4ff !important; 
    }
    
    /* FIX TESTO SIDEBAR: FORZA VISIBILITÀ AZZURRA */
    [data-testid="stSidebar"] * { 
        color: #00d4ff !important; 
        font-weight: 700 !important; 
        visibility: visible !important;
    }

    /* BOTTONI SIDEBAR FLOATING E RIMOZIONE PALLINI BIANCHI */
    div[role="radiogroup"] label {
        background: rgba(0, 212, 255, 0.05) !important;
        border: 1px solid #00d4ff !important;
        border-radius: 12px !important;
        padding: 10px !important;
        margin-bottom: 10px !important;
        transition: 0.3s ease-in-out !important;
        display: flex !important;
        align-items: center !important;
    }
    
    /* Nasconde il cerchietto radio standard */
    div[role="radiogroup"] [data-testid="stWidgetLabel"] div:first-child { display: none !important; }
    
    /* Effetto quando selezionato */
    div[role="radiogroup"] label:has(input:checked) {
        transform: translateY(-8px) !important;
        background: rgba(0, 212, 255, 0.25) !important;
        box-shadow: 0 10px 20px rgba(0, 212, 255, 0.4) !important;
    }
    div[role="radiogroup"] label:has(input:checked) p { color: #ffffff !important; }

    /* STANZE TABELLONE: EFFETTO BOX FLOATING */
    .stanza-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        transition: 0.3s;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .stanza-card:hover {
        transform: translateY(-8px);
        border-color: #00d4ff;
        box-shadow: 0 12px 25px rgba(0, 212, 255, 0.2);
    }

    /* CALENDARIO: EFFETTO POST-IT GIALLO */
    .postit-note {
        background: #fff9c4 !important;
        color: #1a1a1a !important;
        padding: 8px;
        border-left: 6px solid #fbc02d;
        margin: 4px 0;
        font-size: 13px !important;
        border-radius: 2px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
        font-weight: 600;
    }

    /* BOTTONE LOGOUT ROSSO */
    .stButton > button {
        border: 2px solid #ff4b4b !important;
        color: #ff4b4b !important;
        background: transparent !important;
        font-weight: bold !important;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# 5. SCHERMATA LOGIN
if not st.session_state.logged_in:
    _, col2, _ = st.columns([1,2,1])
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
                st.error("Credenziali errate") #
    st.stop()

# 6. SIDEBAR
with st.sidebar:
    st.markdown("### Rems-connect")
    st.markdown(f"● {st.session_state.user_data[2]}")
    st.warning("⚠️ 1 SCADENZE OGGI")
    
    st.divider()
    menu = st.radio("NAVIGAZIONE", 
                   ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Posti Letto", "⚙️ Admin"])
    
    st.divider()
    if st.button("LOGOUT"):
        st.session_state.logged_in = False
        st.rerun()
    
    st.write("")
    st.write("**Antony**")
    st.caption("Webmaster ver. 28.9 Elite")

# 7. LOGICA MODULI
if menu == "📊 Monitoraggio":
    st.title("📊 Monitoraggio Operativo")
    st.info("Benvenuto nel pannello di controllo.")

elif menu == "👥 Modulo Equipe":
    st.title("👥 Modulo Operativo Equipe")
    figura = st.selectbox("Simula Figura:", ["Psichiatra", "Infermiere", "OSS"])
    st.selectbox("Seleziona Paziente", ["PIPPO ROSSI", "MARIO BIANCHI"])
    
    tab1, tab2, tab3 = st.tabs(["📝 Nuova Prescrizione", "💊 Gestione Terapie", "🩺 Diario Clinico"])
    with tab1:
        st.text_input("Farmaco")
        st.text_input("Dose")
    with tab3:
        with st.expander("📁 SCHEDA PAZIENTE: PIPPO ROSSI"):
            st.write("Diario clinico aggiornato.")

elif menu == "📅 Agenda Dinamica":
    st.title("📅 Agenda Dinamica REMS")
    
    # Navigazione Mesi
    c1, c2, c3 = st.columns([1,2,1])
    with c2: st.subheader("Aprile 2026")
    
    # Griglia Calendario
    cal = calendar.monthcalendar(2026, 4)
    cols = st.columns(7)
    days = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    for i, d in enumerate(days): cols[i].write(f"**{d}**")
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                with cols[i]:
                    st.write(day)
                    if day == 4: # Esempio PIPPO ROSSI
                        st.markdown('<div class="postit-note">🚗 PIPPO ROSSI<br>Uscita Esterna<br>⏰ 19:16</div>', unsafe_allow_html=True)

elif menu == "🗺️ Mappa Posti Letto":
    st.title("🗺️ Tabellone Visivo Posti Letto")
    st.subheader("Reparto A")
    
    cols = st.columns(3)
    for i in range(1, 4):
        with cols[i-1]:
            st.markdown(f"""
            <div class="stanza-card">
                <h3 style="color:#00d4ff; margin:0;">🛏️ A{i} STANDARD</h3>
                <hr style="border:0.5px solid rgba(0,212,255,0.2); margin:10px 0;">
                <p><b>L1:</b> Libero</p>
                <p><b>L2:</b> Libero</p>
            </div>
            """, unsafe_allow_html=True)

elif menu == "⚙️ Admin":
    st.title("⚙️ Pannello Amministrazione")
    st.tabs(["UTENTI", "PAZIENTI ATTIVI", "ARCHIVIO"])

conn.close()
