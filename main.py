import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import calendar

# --- 1. MOTORE DI SICUREZZA E TEMPO (ZONA PERITO) ---
def get_now_it():
    # Riferimento orario REMS Italia (UTC+2)
    return datetime.now(timezone.utc) + timedelta(hours=2)

def hash_pw(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- 2. CONFIGURAZIONE INTERFACCIA ELITE PRO v28.8 ---
st.set_page_config(page_title="REMS Connect ELITE PRO v28.8", layout="wide", page_icon="🏥")

# CSS ARCHITETTURALE - IL TOCCO "GIOIELLINO"
st.markdown("""
<style>
    /* Sidebar Professionale */
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; min-width: 320px !important; border-right: 4px solid #00ff00; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 2.2rem !important; font-weight: 900 !important; text-align: center; text-shadow: 2px 2px #000; }
    .version-tag { text-align: center; font-size: 0.8rem; color: #00ff00 !important; margin-bottom: 20px; font-family: monospace; }
    .user-logged { background: rgba(0,255,0,0.1); padding: 15px; border-radius: 12px; text-align: center; border: 1px solid #00ff00; color: #00ff00 !important; font-weight: 800; }
    
    /* Alert Agenda Dinamico */
    .alert-badge { background: linear-gradient(45deg, #ef4444, #991b1b); color: white; padding: 12px; border-radius: 10px; text-align: center; font-weight: 900; margin: 15px 0; border: 2px solid #fff; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0% {transform: scale(1);} 50% {transform: scale(1.03);} 100% {transform: scale(1);} }

    /* Griglia Calendario Elite */
    .cal-container { background: #ffffff; border-radius: 20px; padding: 25px; box-shadow: 0 15px 40px rgba(0,0,0,0.2); border: 1px solid #e2e8f0; }
    .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 10px; }
    .cal-header-day { font-weight: 900; color: #1e3a8a; background: #f1f5f9; padding: 10px; border-radius: 8px; text-align: center; }
    .cal-cell { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 12px; min-height: 140px; padding: 10px; transition: 0.2s; position: relative; }
    .cal-cell:hover { border-color: #2563eb; transform: translateY(-3px); }
    .cal-today { border: 3px solid #00ff00 !important; background: #f0fff4 !important; }
    .day-num { font-size: 1.3rem; font-weight: 900; color: #1e3a8a; }
    
    /* Eventi in Agenda */
    .event-item { font-size: 0.7rem; padding: 4px; border-radius: 5px; margin-top: 4px; font-weight: 700; display: block; border-left: 4px solid; }
    .ev-attivo { background: #dbeafe; color: #1e40af; border-left-color: #2563eb; }
    .ev-archiviato { background: #f1f5f9; color: #94a3b8; border-left-color: #cbd5e1; text-decoration: line-through; opacity: 0.6; }

    /* Banner Sezioni */
    .section-banner { background: linear-gradient(90deg, #1e3a8a, #3b82f6); color: white; padding: 20px; border-radius: 15px; margin-bottom: 25px; border-left: 10px solid #00ff00; }
</style>
""", unsafe_allow_html=True)

# --- 3. DATABASE MULTI-TABELLA (NESSUNA OMISSIONE) ---
DB_NAME = "rems_final_v28_8.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        # Sicurezza e Anagrafica
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, reparto TEXT)")
        # Clinica e Parametri
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (p_id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS parametri (p_id INTEGER, data TEXT, pa TEXT, fc TEXT, sat TEXT, temp TEXT, op TEXT)")
        # Cassa e Logistica
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT)")
        # AGENDA DINAMICA ANNUALE
        cur.execute("""CREATE TABLE IF NOT EXISTS appuntamenti (
            id_u INTEGER PRIMARY KEY AUTOINCREMENT, 
            p_id INTEGER, 
            data TEXT, 
            ora TEXT, 
            nota TEXT, 
            stato TEXT, 
            autore TEXT
        )""")
        
        # Admin Account Default
        if cur.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
            cur.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("perito2026"), "SUPER", "USER", "Admin"))
        conn.commit()

init_db()

def db_query(q, p=(), commit=False):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(q, p)
        if commit: conn.commit()
        return cur.fetchall()

# --- 4. GESTIONE SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if 'cal_month' not in st.session_state: st.session_state.cal_month = get_now_it().month
if 'cal_year' not in st.session_state: st.session_state.cal_year = get_now_it().year

if not st.session_state.user_session:
    _, col_login, _ = st.columns([1,2,1])
    with col_login:
        st.markdown("<h1 style='text-align:center;'>🏥 REMS CONNECT LOGIN</h1>", unsafe_allow_html=True)
        with st.form("login_gate"):
            u_in = st.text_input("Username")
            p_in = st.text_input("Password", type="password")
            if st.form_submit_button("SBLOCCA SISTEMA"):
                res = db_query("SELECT * FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res:
                    st.session_state.user_session = {"user": res[0][0], "nome": res[0][2], "cognome": res[0][3], "ruolo": res[0][4]}
                    st.rerun()
                else: st.error("Accesso Negato.")
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- 5. SIDEBAR DINAMICA (ANTONY WEBMASTER STYLE) ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown("<div class='version-tag'>ELITE PRO v28.8 | WHITE EDITION</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-logged'>● {u['nome']} {u['cognome']}</div>", unsafe_allow_html=True)

# Alert Notifiche Agenda
oggi_str = get_now_it().strftime("%Y-%m-%d")
count_oggi = db_query("SELECT COUNT(*) FROM appuntamenti WHERE data=? AND stato='ATTIVO'", (oggi_str,))[0][0]
if count_oggi > 0:
    st.sidebar.markdown(f"<div class='alert-badge'>⚠️ {count_oggi} IMPEGNI OGGI</div>", unsafe_allow_html=True)

menu = ["📊 Dashboard", "📅 Agenda Pro Dinamica", "💊 Gestione Terapie", "💰 Cassa Pazienti", "🗺️ Mappa Letti"]
if u['ruolo'] == "Admin": menu.append("⚙️ Pannello Admin")
choice = st.sidebar.radio("MODULI ATTIVI", menu)

if st.sidebar.button("LOGOUT"):
    st.session_state.user_session = None
    st.rerun()
st.sidebar.markdown(f"<br><br><div style='text-align:center; font-size:0.8rem;'>System by:<br><b>Antony Webmaster</b></div>", unsafe_allow_html=True)

# --- 6. MODULO AGENDA DINAMICA (LOGICA INTEGRALE) ---
if choice == "📅 Agenda Pro Dinamica":
    st.markdown("<div class='section-banner'><h1>📅 AGENDA DINAMICA ANNUALE</h1><p>Pianificazione e Archiviazione Storica</p></div>", unsafe_allow_html=True)
    
    # Navigazione Mese/Anno
    nav1, nav2, nav3 = st.columns([1,2,1])
    with nav1:
        if st.button("⬅️ Mese Prec."):
            st.session_state.cal_month -= 1
            if st.session_state.cal_month < 1: st.session_state.cal_month = 12; st.session_state.cal_year -= 1
            st.rerun()
    with nav2:
        mesi = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]
        st.markdown(f"<h2 style='text-align:center;'>{mesi[st.session_state.cal_month-1]} {st.session_state.cal_year}</h2>", unsafe_allow_html=True)
    with nav3:
        if st.button("Mese Succ. ➡️"):
            st.session_state.cal_month += 1
            if st.session_state.cal_month > 12: st.session_state.cal_month = 1; st.session_state.cal_year += 1
            st.rerun()

    c_cal, c_form = st.columns([3, 1])
    
    with c_cal:
        st.markdown("<div class='cal-container'><div class='cal-grid'>", unsafe_allow_html=True)
        for d in ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]:
            st.markdown(f"<div class='cal-header-day'>{d}</div>", unsafe_allow_html=True)
        
        cal_engine = calendar.Calendar(firstweekday=0)
        weeks = cal_engine.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month)
        
        for week in weeks:
            for day in week:
                if day == 0: st.markdown("<div></div>", unsafe_allow_html=True)
                else:
                    d_iso = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-{day:02d}"
                    cls_today = "cal-today" if d_iso == oggi_str else ""
                    # Query appuntamenti del giorno
                    evs = db_query("SELECT a.ora, p.nome, a.stato FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.data=?", (d_iso,))
                    st.markdown(f"<div class='cal-cell {cls_today}'><span class='day-num'>{day}</span>", unsafe_allow_html=True)
                    for e_ora, e_paz, e_sta in evs:
                        e_cls = "ev-attivo" if e_sta == "ATTIVO" else "ev-archiviato"
                        st.markdown(f"<span class='event-item {e_cls}'>{e_ora} - {e_paz}</span>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div></div>", unsafe_allow_html=True)

    with c_form:
        st.subheader("➕ Nuovo Impegno")
        p_list = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
        with st.form("new_app_form"):
            p_sel = st.selectbox("Paziente", [p[1] for p in p_list]) if p_list else st.info("Inserire pazienti in Admin")
            d_sel = st.date_input("Data")
            o_sel = st.time_input("Orario")
            n_sel = st.text_input("Nota/Causale")
            if st.form_submit_button("REGISTRA"):
                p_id = [p[0] for p in p_list if p[1] == p_sel][0]
                db_query("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore) VALUES (?,?,?,?,'ATTIVO',?)", 
                         (p_id, str(d_sel), str(o_sel)[:5], n_sel, firma_op), commit=True)
                st.rerun()
        
        st.divider()
        st.subheader("📂 Gestione")
        active_apps = db_query("SELECT a.id_u, a.data, p.nome FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.stato='ATTIVO' ORDER BY a.data ASC")
        if active_apps:
            to_arch = st.selectbox("Seleziona da Archiviare:", [f"{x[1]} - {x[2]}" for x in active_apps])
            t_id = [x[0] for x in active_apps if f"{x[1]} - {x[2]}" == to_arch][0]
            if st.button("✅ ARCHIVIA"):
                db_query("UPDATE appuntamenti SET stato='ARCHIVIATO' WHERE id_u=?", (t_id,), commit=True)
                st.rerun()

# --- 7. MODULO CASSA (LOGICA INTEGRALE) ---
elif choice == "💰 Cassa Pazienti":
    st.markdown("<div class='section-banner'><h1>💰 CASSA PAZIENTI</h1></div>", unsafe_allow_html=True)
    p_data = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Nuovo Movimento")
        with st.form("cassa_f"):
            p_c = st.selectbox("Paziente", [p[1] for p in p_data])
            t_m = st.radio("Tipo", ["ENTRATA", "USCITA"])
            val = st.number_input("Euro", min_value=0.0)
            cau = st.text_input("Causale")
            if st.form_submit_button("ESEGUI"):
                pid = [p[0] for p in p_data if p[1] == p_c][0]
                db_query("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)",
                         (pid, oggi_str, cau, val, t_m, firma_op), commit=True)
                st.success("Operazione registrata.")
                st.rerun()
    with c2:
        st.subheader("Saldo Corrente")
        p_s = st.selectbox("Saldo di:", [p[1] for p in p_data])
        sid = [p[0] for p in p_data if p[1] == p_s][0]
        ent = db_query("SELECT SUM(importo) FROM cassa WHERE p_id=? AND tipo='ENTRATA'", (sid,))[0][0] or 0
        usc = db_query("SELECT SUM(importo) FROM cassa WHERE p_id=? AND tipo='USCITA'", (sid,))[0][0] or 0
        st.metric("DISPONIBILITÀ", f"{ent - usc:.2f} €")

# --- 8. PANNELLO ADMIN (CONTROLLO TOTALE) ---
elif choice == "⚙️ Pannello Admin":
    st.markdown("<h1>⚙️ AMMINISTRAZIONE ELITE</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["Personale", "Anagrafica Pazienti"])
    with t1:
        with st.form("admin_staff"):
            st.subheader("Nuovo Operatore")
            nu, np, nn, nc, nq = st.text_input("User"), st.text_input("Pass"), st.text_input("Nome"), st.text_input("Cognome"), st.selectbox("Ruolo", ["Medico", "Infermiere", "Educatore", "OPSI", "OSS", "Psicologo", "Assistente Sociale"])
            if st.form_submit_button("ATTIVA ACCOUNT"):
                db_query("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), commit=True)
                st.success("Account Operativo.")
    with t2:
        with st.form("admin_pax"):
            st.subheader("Inserimento Paziente")
            p_n = st.text_input("Nome Cognome")
            p_r = st.selectbox("Reparto", ["REMS A", "REMS B", "MODULO TRANSITO"])
            if st.form_submit_button("REGISTRA"):
                db_query("INSERT INTO pazienti (nome, reparto) VALUES (?,?)", (p_n, p_r), commit=True)
                st.success("Paziente inserito nel database.")
