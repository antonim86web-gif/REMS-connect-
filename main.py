import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd
import io

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v12.5 (FULL) ---
st.set_page_config(
    page_title="REMS Connect ELITE PRO",
    layout="wide",
    page_icon="🏥",
    initial_sidebar_state="expanded"
)

# --- ENGINE CSS ESTESO ---
st.markdown("""
<style>
    /* SIDEBAR PROFESSIONALE */
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 2px solid #334155; }
    .sidebar-title { 
        color: #f8fafc !important; font-size: 1.8rem !important; font-weight: 800 !important; 
        text-align: center; padding: 25px 0; border-bottom: 1px solid #334155;
    }
    .sidebar-footer { 
        position: fixed; bottom: 10px; left: 10px; color: #94a3b8 !important; 
        font-size: 0.75rem !important; line-height: 1.4; z-index: 100;
    }
    
    /* BANNER SEZIONALI */
    .section-banner { 
        background: linear-gradient(90deg, #1e3a8a 0%, #1e40af 100%); 
        color: white !important; padding: 35px; border-radius: 15px; 
        margin-bottom: 30px; text-align: center; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }
    .section-banner h2 { color: white !important; margin: 0; text-transform: uppercase; letter-spacing: 2px; font-weight: 900; }
    .section-banner p { opacity: 0.85; font-style: italic; margin-top: 8px; font-size: 1.1rem; }

    /* TABELLE DINAMICHE */
    .report-table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; margin-top: 10px; }
    .report-table th { background-color: #1e293b; color: #f8fafc !important; padding: 15px; text-align: left; font-size: 0.9rem; border: 1px solid #334155; }
    .report-table td { padding: 12px; border: 1px solid #e2e8f0; color: #1e293b; font-size: 0.85rem; vertical-align: middle; }
    .report-table tr:nth-child(even) { background-color: #f8fafc; }
    
    /* CARD TERAPIA DINAMICA */
    .therapy-card { 
        background: #ffffff; border: 1px solid #cbd5e1; padding: 15px; border-radius: 10px; 
        margin-bottom: 12px; border-left: 6px solid #1e3a8a; transition: all 0.3s ease;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    .therapy-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
    .therapy-card b { color: #1e3a8a; font-size: 1.1rem; }
    
    /* STATI E BADGE */
    .badge { padding: 4px 12px; border-radius: 50px; font-weight: 700; font-size: 0.75rem; text-transform: uppercase; }
    .badge-mat { background-color: #fef3c7; color: #92400e; }
    .badge-pom { background-color: #dbeafe; color: #1e40af; }
    .badge-not { background-color: #e0e7ff; color: #3730a3; }
</style>
""", unsafe_allow_html=True)

# --- MOTORE PERSISTENZA DATI (SQLITE AVANZATO) ---
DB_NAME = "rems_enterprise_v12.db"

def db_init():
    """Inizializzazione completa dello schema database"""
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS utenti (
            user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT, ultimo_log TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS pazienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, data_nascita TEXT, codice_fiscale TEXT, data_ingresso TEXT, stato TEXT DEFAULT 'ATTIVO')""")
        cur.execute("""CREATE TABLE IF NOT EXISTS eventi (
            id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, categoria TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS terapie (
            id_t INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, farmaco TEXT, dose TEXT, 
            mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, data_prescrizione TEXT, stato TEXT DEFAULT 'ATTIVO')""")
        cur.execute("""CREATE TABLE IF NOT EXISTS cassa (
            id_c INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, causale TEXT, 
            importo REAL, tipo TEXT, op TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS agenda (
            id_a INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, 
            categoria TEXT, evento TEXT, esito TEXT DEFAULT 'PROGRAMMATO')""")
        conn.commit()

def db_query(query, params=(), commit=False):
    """Esecutore di query con gestione errori centralizzata"""
    try:
        with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
    except Exception as e:
        st.error(f"Database Error: {str(e)}")
        return []

db_init()

# --- LOGICA DI ACCESSO ---
if 'auth' not in st.session_state: st.session_state.auth = None

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

if not st.session_state.auth:
    st.markdown("<div class='section-banner'><h2>REMS CONNECT ELITE PRO</h2><p>Piattaforma di Gestione Integrata - AntonioWebMaster</p></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔑 Accesso Operatore")
        with st.form("login_form"):
            u_in = st.text_input("Username")
            p_in = st.text_input("Password", type="password")
            if st.form_submit_button("ENTRA"):
                res = db_query("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res:
                    st.session_state.auth = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_in}
                    db_query("UPDATE utenti SET ultimo_log=? WHERE user=?", (datetime.now().strftime("%d/%m/%Y %H:%M"), u_in), True)
                    st.rerun()
                else: st.error("Accesso negato: credenziali errate.")
    with c2:
        st.subheader("📝 Registrazione Staff")
        with st.form("reg_form"):
            nu, np = st.text_input("Scegli Username"), st.text_input("Scegli Password", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Amministrativo"])
            if st.form_submit_button("REGISTRA"):
                db_query("INSERT INTO utenti (user, pwd, nome, cognome, qualifica) VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True)
                st.success("Operatore registrato con successo.")
    st.stop()

# --- AMBIENTE OPERATIVO ---
u = st.session_state.auth
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.info(f"Loggato come:\n**{u['nome']} {u['cognome']}**\n*{u['ruolo']}*")

nav = st.sidebar.radio("NAVIGAZIONE", [
    "📊 Quadro Generale", 
    "💊 Piano Terapeutico", 
    "📝 Diario Multidisciplinare", 
    "💰 Gestione Cassa", 
    "📅 Agenda Udienze", 
    "⚙️ Sistema & Anagrafica"
])

if st.sidebar.button("LOGOUT"):
    st.session_state.auth = None
    st.rerun()

st.sidebar.markdown(f"<div class='sidebar-footer'><b>REMS CONNECT v12.5 FULL</b><br>Architecture by AntonioWebMaster<br>{date.today().year} © Reserved</div>", unsafe_allow_html=True)

# --- 1. QUADRO GENERALE ---
if nav == "📊 Quadro Generale":
    st.markdown("<div class='section-banner'><h2>MONITORAGGIO REPARTO</h2><p>Situazione clinica e amministrativa in tempo reale</p></div>", unsafe_allow_html=True)
    pazienti = db_query("SELECT id, nome, data_ingresso, cella FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    
    if pazienti:
        for pid, nome, ding, cella in pazienti:
            with st.expander(f"👤 PAZIENTE: {nome} (Ingresso: {ding})"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write("**Ultimi Eventi Clinici:**")
                    evs = db_query("SELECT data, op, nota FROM eventi WHERE p_id=? ORDER BY id_u DESC LIMIT 5", (pid,))
                    if evs:
                        for d, op, nt in evs: st.caption(f"_{d} - {op}_: {nt}")
                    else: st.write("Nessuna nota recente.")
                with col2:
                    st.write("**Sintesi Economica:**")
                    c_mov = db_query("SELECT SUM(CASE WHEN tipo='Entrata' THEN importo ELSE -importo END) FROM cassa WHERE p_id=?", (pid,))
                    saldo = c_mov[0][0] if c_mov[0][0] else 0
                    st.metric("Saldo Cassa", f"€ {saldo:.2f}")

# --- 2. PIANO TERAPEUTICO (CORE) ---
elif nav == "💊 Piano Terapeutico":
    st.markdown("<div class='section-banner'><h2>SOMMINISTRAZIONE E PRESCRIZIONE</h2></div>", unsafe_allow_html=True)
    
    tabs = st.tabs(["📋 Foglio Terapie Dinamico", "➕ Nuova Prescrizione Medica"])
    
    with tabs[0]:
        turno = st.radio("Seleziona Turno Attivo:", ["MAT", "POM", "NOTT"], horizontal=True)
        t_label = turno.lower() if turno != "NOTT" else "nott"
        
        # Query complessa per estrazione terapie attive
        terapie = db_query(f"""
            SELECT p.nome, t.farmaco, t.dose, t.id_t, t.p_id 
            FROM terapie t JOIN pazienti p ON t.p_id = p.id 
            WHERE t.{t_label} = 1 AND t.stato='ATTIVO' ORDER BY p.nome
        """)
        
        if terapie:
            for nome_p, farm, dose, tid, pid in terapie:
                st.markdown(f"<div class='therapy-card'><b>{nome_p}</b><br>{farm} - {dose}</div>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns([1,1,2])
                if c1.button("✅ FIRMA", key=f"ok_{tid}"):
                    db_query("INSERT INTO eventi (p_id, data, nota, ruolo, op, categoria) VALUES (?,?,?,?,?,?)",
                             (pid, datetime.now().strftime("%d/%m %H:%M"), f"SOMM: {farm} ({turno})", u['ruolo'], firma, "Terapia"), True)
                    st.success(f"Registrata somministrazione per {nome_p}")
                if c2.button("❌ RIFIUTO", key=f"no_{tid}"):
                    st.session_state[f"rif_{tid}"] = True
                
                if st.session_state.get(f"rif_{tid}"):
                    motivo = c3.text_input("Specifica motivo rifiuto:", key=f"mot_{tid}")
                    if c3.button("Conferma", key=f"btn_c_{tid}"):
                        db_query("INSERT INTO eventi (p_id, data, nota, ruolo, op, categoria) VALUES (?,?,?,?,?,?)",
                                 (pid, datetime.now().strftime("%d/%m %H:%M"), f"RIFIUTO: {farm} ({turno}) - Note: {motivo}", u['ruolo'], firma, "Terapia"), True)
                        st.session_state[f"rif_{tid}"] = False
                        st.rerun()
        else:
            st.info("Nessuna terapia programmata per questo turno.")

    with tabs[1]:
        if u['ruolo'] == "Psichiatra":
            with st.form("presc_f"):
                p_lista = db_query("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
                sel_p = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
                pid = [p[0] for p in p_lista if p[1] == sel_p][0]
                farm = st.text_input("Nome Farmaco"); dos = st.text_input("Dosaggio / Posologia")
                c1,c2,c3 = st.columns(3); m=c1.checkbox("MAT"); p=c2.checkbox("POM"); n=c3.checkbox("NOTT")
                if st.form_submit_button("REGISTRA PRESCRIZIONE"):
                    db_query("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico, data_prescrizione) VALUES (?,?,?,?,?,?,?,?)",
                             (pid, farm, dos, int(m), int(p), int(n), firma, date.today().strftime("%d/%m/%Y")), True)
                    st.success("Terapia inserita correttamente.")
        else:
            st.warning("Funzione limitata al personale Medico.")

# --- 3. DIARIO MULTIDISCIPLINARE ---
elif nav == "📝 Diario Multidisciplinare":
    st.markdown("<div class='section-banner
