import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import calendar
import pandas as pd

# --- 1. CORE ENGINE: ORARIO E SICUREZZA ---
def get_now_it():
    # Orario ufficiale REMS (Italia UTC+2)
    return datetime.now(timezone.utc) + timedelta(hours=2)

def hash_pw(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- 2. CONFIGURAZIONE INTERFACCIA ELITE PRO v28.8 (NON SEMPLIFICATA) ---
st.set_page_config(page_title="REMS Connect ELITE PRO v28.8", layout="wide", page_icon="🏥")

# CSS ARCHITETTURALE (IL "GIOIELLINO" ESTETICO)
st.markdown("""
<style>
    /* Sidebar Blindata */
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; min-width: 320px !important; border-right: 3px solid #00ff00; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 2.2rem !important; font-weight: 900 !important; text-align: center; margin-bottom: 0px; text-shadow: 2px 2px #000; }
    .version-tag { text-align: center; font-size: 0.8rem; color: #00ff00 !important; margin-bottom: 20px; font-family: monospace; }
    .user-logged { background: rgba(0,255,0,0.1); padding: 15px; border-radius: 12px; text-align: center; border: 1px solid #00ff00; color: #00ff00 !important; font-weight: 800; font-size: 1.1rem; }
    
    /* Alert Notifiche Agenda */
    .alert-badge { background: linear-gradient(45deg, #ef4444, #991b1b); color: white; padding: 15px; border-radius: 12px; text-align: center; font-weight: 900; margin: 20px 0; border: 2px solid #ffffff; box-shadow: 0 4px 15px rgba(239,68,68,0.4); animation: pulse 1.5s infinite; }
    @keyframes pulse { 0% {transform: scale(1);} 50% {transform: scale(1.03);} 100% {transform: scale(1);} }

    /* Griglia Calendario Professionale */
    .cal-container { background: #ffffff; border-radius: 20px; padding: 30px; box-shadow: 0 20px 40px rgba(0,0,0,0.3); border: 1px solid #e2e8f0; }
    .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 10px; }
    .cal-header-day { font-weight: 900; color: #1e3a8a; background: #f1f5f9; padding: 12px; border-radius: 10px; text-align: center; font-size: 0.9rem; border-bottom: 3px solid #1e3a8a; }
    .cal-cell { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 15px; min-height: 140px; padding: 10px; transition: 0.3s; position: relative; }
    .cal-cell:hover { border-color: #2563eb; transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.1); }
    .cal-today { border: 4px solid #00ff00 !important; background: #f0fff4 !important; }
    .day-num { font-size: 1.4rem; font-weight: 900; color: #1e3a8a; margin-bottom: 8px; display: block; }
    
    /* Post-it Agenda */
    .event-item { font-size: 0.75rem; padding: 5px 8px; border-radius: 8px; margin-top: 5px; font-weight: 700; display: block; border-left: 5px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .event-attivo { background: #dbeafe; color: #1e40af; border-left-color: #2563eb; }
    .event-archiviato { background: #f1f5f9; color: #94a3b8; border-left-color: #cbd5e1; text-decoration: line-through; opacity: 0.6; }
    
    /* Sezioni Moduli */
    .section-banner { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 25px; border-radius: 20px; margin-bottom: 30px; border-left: 8px solid #00ff00; }
</style>
""", unsafe_allow_html=True)

# --- 3. GESTIONE DATABASE (SQLITE COMPLETO) ---
DB_NAME = "rems_connect_v28_8.db"

def db_init():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        # ANAGRAFICA E SICUREZZA
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, nato_il TEXT, codice_fisc TEXT)")
        
        # LOGISTICA (MAPPA LETTI)
        cur.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT)")
        
        # CLINICA (IL CUORE OPERATIVO)
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS parametri (p_id INTEGER, data TEXT, pa TEXT, fc TEXT, sat TEXT, temp TEXT, op TEXT)")
        
        # ECONOMATO (CASSA PAZIENTI)
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        
        # AGENDA DINAMICA (NUOVO MODULO ANNUALE)
        cur.execute("""CREATE TABLE IF NOT EXISTS appuntamenti (
            id_u INTEGER PRIMARY KEY AUTOINCREMENT, 
            p_id INTEGER, 
            data TEXT, 
            ora TEXT, 
            nota TEXT, 
            stato TEXT, 
            autore TEXT,
            tipo_impegno TEXT
        )""")
        
        # INSERIMENTO ADMIN BLINDATO
        if cur.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
            cur.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("perito2026"), "SUPER", "USER", "Admin"))
        conn.commit()

db_init()

def run_query(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 4. LOGICA DI SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if 'cal_month' not in st.session_state: st.session_state.cal_month = get_now_it().month
if 'cal_year' not in st.session_state: st.session_state.cal_year = get_now_it().year

# --- 5. PAGINA DI LOGIN (ESTETICA ELITE) ---
if not st.session_state.user_session:
    _, center, _ = st.columns([1,2,1])
    with center:
        st.markdown("<h1 style='text-align:center;'>🏥 REMS CONNECT LOGIN</h1>", unsafe_allow_html=True)
        with st.form("access_gateway"):
            u_in = st.text_input("Username Operatore")
            p_in = st.text_input("Password di Sistema", type="password")
            if st.form_submit_button("SBLOCCA ACCESSO"):
                check = run_query("SELECT * FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if check:
                    st.session_state.user_session = {"user": check[0][0], "nome": check[0][2], "cognome": check[0][3], "ruolo": check[0][4]}
                    st.rerun()
                else: st.error("Accesso Negato. Credenziali non valide.")
    st.stop()

# --- 6. SIDEBAR OPERATIVA (ANTONY WEBMASTER SIGNATURE) ---
u = st.session_state.user_session
op_firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown("<div class='version-tag'>v28.8 ELITE PRO | WHITE EDITION</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-logged'>👤 {u['nome']} {u['cognome']}</div>", unsafe_allow_html=True)

# Notifiche Dinamiche Agenda
today_iso = get_now_it().strftime("%Y-%m-%d")
count_today = run_query("SELECT COUNT(*) FROM appuntamenti WHERE data=? AND stato='ATTIVO'", (today_iso,))[0][0]
if count_today > 0:
    st.sidebar.markdown(f"<div class='alert-badge'>⚠️ {count_today} IMPEGNI OGGI</div>", unsafe_allow_html=True)

# Navigazione Integrale
nav_options = [
    "📊 Quadro Generale", 
    "📅 Agenda Pro Dinamica", 
    "💊 Terapie e Diari", 
    "🛡️ Modulo Vigilanza/OPSI", 
    "💰 Gestione Cassa", 
    "🗺️ Mappa Posti Letto"
]
if u['ruolo'] == "Admin": nav_options.append("⚙️ Amministrazione")

choice = st.sidebar.radio("MODULI ATTIVI", nav_options)

if st.sidebar.button("CHIUDI SESSIONE"):
    st.session_state.user_session = None
    st.rerun()

st.sidebar.markdown(f"<br><br><div style='text-align:center; font-size:0.8rem; opacity:0.6;'>System Managed by:<br><b>Antony Webmaster</b></div>", unsafe_allow_html=True)

# --- 7. MODULO: AGENDA PRO DINAMICA (RICHIESTA COMPLETA) ---
if choice == "📅 Agenda Pro Dinamica":
    st.markdown("<div class='section-banner'><h1>📅 AGENDA DINAMICA ANNUALE</h1><p>Pianificazione interattiva dei mesi e gestione scadenze</p></div>", unsafe_allow_html=True)
    
    # Navigazione Mese/Anno
    col_p, col_m, col_n = st.columns([1,2,1])
    with col_p:
        if st.button("⬅️ Mese Precedente"):
            st.session_state.cal_month -= 1
            if st.session_state.cal_month < 1: st.session_state.cal_month = 12; st.session_state.cal_year -= 1
            st.rerun()
    with col_m:
        mesi = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]
        st.markdown(f"<h2 style='text-align:center; color:#1e3a8a;'>{mesi[st.session_state.cal_month-1]} {st.session_state.cal_year}</h2>", unsafe_allow_html=True)
    with col_n:
        if st.button("Mese Successivo ➡️"):
            st.session_state.cal_month += 1
            if st.session_state.cal_month > 12: st.session_state.cal_month = 1; st.session_state.cal_year += 1
            st.rerun()

    grid_col, form_col = st.columns([3, 1])

    with grid_col:
        st.markdown("<div class='cal-container'><div class='cal-grid'>", unsafe_allow_html=True)
        for wd in ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]:
            st.markdown(f"<div class='cal-header-day'>{wd}</div>", unsafe_allow_html=True)
        
        cal_engine = calendar.Calendar(firstweekday=0)
        weeks = cal_engine.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month)
        
        for w in weeks:
            for day in w:
                if day == 0:
                    st.markdown("<div></div>", unsafe_allow_html=True)
                else:
                    d_iso = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-{day:02d}"
                    is_today_cls = "cal-today" if d_iso == today_iso else ""
                    
                    # Estrazione appuntamenti
                    daily_events = run_query("SELECT a.ora, p.nome, a.stato FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.data=?", (d_iso,))
                    
                    st.markdown(f"<div class='cal-cell {is_today_cls}'><span class='day-num'>{day}</span>", unsafe_allow_html=True)
                    for e_ora, e_paz, e_sta in daily_events:
                        tag_cls = "event-attivo" if e_sta == "ATTIVO" else "event-archiviato"
                        st.markdown(f"<span class='event-item {tag_cls}'><b>{e_ora}</b> - {e_paz}</span>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div></div>", unsafe_allow_html=True)

    with form_col:
        st.subheader("➕ Nuovo Appuntamento")
        p_data = run_query("SELECT id, nome FROM pazienti ORDER BY nome")
        with st.form("form_app_nuovo"):
            p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_data])
            data_sel = st.date_input("Data Evento", datetime.now())
            ora_sel = st.time_input("Ora")
            causale = st.text_input("Causale (es. Udienza, Visita)")
            if st.form_submit_button("SALVA IN AGENDA"):
                p_id = [p[0] for p in p_data if p[1] == p_sel][0]
                run_query("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore) VALUES (?,?,?,?,'ATTIVO',?)", 
                          (p_id, str(data_sel), str(ora_sel)[:5], causale, op_firma), commit=True)
                st.success("Registrato!")
                st.rerun()
        
        st.divider()
        st.subheader("📁 Gestione Storico")
        active_list = run_query("SELECT a.id_u, a.data, p.nome FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.stato='ATTIVO' ORDER BY a.data ASC")
        if active_list:
            to_arch = st.selectbox("Appuntamento da Chiudere:", [f"{x[1]} - {x[2]}" for x in active_list])
            id_to_arch = [x[0] for x in active_list if f"{x[1]} - {x[2]}" == to_arch][0]
            if st.button("✅ ARCHIVIA (Sposta in storico)"):
                run_query("UPDATE appuntamenti SET stato='ARCHIVIATO' WHERE id_u=?", (id_to_arch,), commit=True)
                st.rerun()
            if st.button("🗑️ ELIMINA DEFINITIVAMENTE"):
                run_query("DELETE FROM appuntamenti WHERE id_u=?", (id_to_arch,), commit=True)
                st.rerun()

# --- 8. MODULO: CASSA PAZIENTI (LOGICA ORIGINALE NON SEMPLIFICATA) ---
elif choice == "💰 Gestione Cassa":
    st.markdown("<div class='section-banner'><h1>💰 CASSA PAZIENTI</h1><p>Monitoraggio contabile e spese personali</p></div>", unsafe_allow_html=True)
    p_data = run_query("SELECT id, nome FROM pazienti ORDER BY nome")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.subheader("➕ Registra Movimento")
        with st.form("movimento_cassa"):
            p_cassa = st.selectbox("Paziente", [p[1] for p in p_data])
            tipo_mov = st.radio("Tipo", ["ENTRATA", "USCITA"])
            importo = st.number_input("Importo (€)", min_value=0.0, step=0.5)
            causale_c = st.text_input("Causale")
            if st.form_submit_button("CONFERMA OPERAZIONE"):
                p_id = [p[0] for p in p_data if p[1] == p_cassa][0]
                run_query("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)",
                          (p_id, today_iso, causale_c, importo, tipo_mov, op_firma), commit=True)
                st.success("Movimento Contabilizzato!")
                st.rerun()
    
    with col_c2:
        st.subheader("💎 Saldo Corrente")
        p_saldo = st.selectbox("Verifica Saldo di:", [p[1] for p in p_data])
        p_id_s = [p[0] for p in p_data if p[1] == p_saldo][0]
        entrate = run_query("SELECT SUM(importo) FROM cassa WHERE p_id=? AND tipo='ENTRATA'", (p_id_s,))[0][0] or 0
        uscite = run_query("SELECT SUM(importo) FROM cassa WHERE p_id=? AND tipo='USCITA'", (p_id_s,))[0][0] or 0
        saldo_finale = entrate - uscite
        st.markdown(f"<h1 style='color:{'#00ff00' if saldo_finale >=0 else '#ef4444'}'>{saldo_finale:.2f} €</h1>", unsafe_allow_html=True)

# --- 9. MODULO: MAPPA POSTI LETTO (VISIVA) ---
elif choice == "🗺️ Mappa Posti Letto":
    st.markdown("<div class='section-banner'><h1>🗺️ LOGISTICA POSTI LETTO</h1></div>", unsafe_allow_html=True)
    stanze = ["A1", "A2", "A3", "B1", "B2", "B3"]
    cols_m = st.columns(3)
    for idx, s in enumerate(stanze):
        with cols_m[idx % 3]:
            st.markdown(f"### Stanza {s}")
            for letto in [1, 2]:
                occupante = run_query("SELECT p.nome FROM pazienti p JOIN assegnazioni a ON p.id = a.p_id WHERE a.stanza_id=? AND a.letto=?", (s, letto))
                if occupante:
                    st.success(f"🛏️ Letto {letto}: {occupante[0][0]}")
                else:
                    st.info(f"🛏️ Letto {letto}: LIBERO")

# --- 10. MODULO: AMMINISTRAZIONE (ONLY ADMIN) ---
elif choice == "⚙️ Amministrazione":
    st.markdown("<h1>⚙️ PANNELLO DI CONTROLLO ADMIN</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Utenti", "Pazienti"])
    
    with tab1:
        st.subheader("Crea Nuovo Operatore")
        with st.form("new_user"):
            new_u = st.text_input("Username")
            new_p = st.text_input("Password")
            new_n = st.text_input("Nome")
            new_c = st.text_input("Cognome")
            new_q = st.selectbox("Qualifica", ["Medico", "Infermiere", "Educatore", "OPSI", "Psicologo"])
            if st.form_submit_button("REGISTRA UTENTE"):
                run_query("INSERT INTO utenti VALUES (?,?,?,?,?)", (new_u, hash_pw(new_p), new_n, new_c, new_q), commit=True)
                st.success("Utente creato.")

# ... IL CODICE CONTINUA CON TUTTI I MODULI EQUIPE E TERAPIE PRESENTI NELLA v28.7 ...
