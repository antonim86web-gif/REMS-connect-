import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGU ---
st.set_page_config(page_title="REMS Connect ELITE PRO
st.markdown("""
<style>
    /* SIDEBAR BLU */
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    
    /* TITOLO PERSONALIZZATO SIDEBAR */
    .sidebar-title {
        color: #ffffff !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        text-align: center;
        margin-bottom: 1rem;
        padding-top: 10px;
        border-bottom: 2px solid #ffffff33;
    }

    /* CREDITI SIDEBAR */
    .sidebar-footer {
        position: fixed;
        bottom: 10px;
        left: 10px;
        color: #ffffff99 !important;
        font-size: 0.7rem !important;
        line-height: 1.2;
    }
    
    /* BANNER SEZIONE (BLU CON SCRITTA BIANCA) */
    .section-banner {
        background-color: #1e3a8a;
        color: white !important;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 25px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .section-banner h2 { color: white !important; margin: 0; font-weight: 800; }
    .section-banner p { margin: 5px 0 0 0; opacity: 0.9; font-size: 1rem; }

    /* FORZA BIANCO NELLA SIDEBAR */
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] .stRadio label {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* TASTO LOGOUT */
    [data-testid="stSidebar"] button {
        background-color: #dc2626 !important;
        color: white !important;
        border: 2px solid #ffffff !important;
        border-radius: 10px !important;
        width: 100% !important;
    }
    
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 10px; text-align: left; }
    .report-table td { padding: 8px; border-bottom: 1px solid #f1f5f9; color: #1e293b; }
    
    .cat-badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; color: white; }
    .cat-udienza { background-color: #dc2626; } 
    .cat-medica { background-color: #2563eb; }  
    .cat-uscita { background-color: #059669; }  
    .cat-parenti { background-color: #d97706; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ---
DB_NAME = "rems_final_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, categoria TEXT, evento TEXT, stato TEXT)")
        try:
            if query: cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except sqlite3.IntegrityError:
            st.error("Dato già esistente.")
            return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- LOGICA ACCESSO ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>ACCESSO AL SISTEMA</h2><p>Inserire le credenziali per operare sulla piattaforma REMS</p></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Login", "📝 Registrazione"])
    with t1:
        with st.form("login"):
            u_in, p_in = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res: 
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# SIDEBAR
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"### 👤 {u['nome']} {u['cognome']}")
nav = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio Generale", "👥 Modulo Equipe", "📅 Agenda Appuntamenti", "⚙️ Gestione Sistema"])
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()
st.sidebar.markdown(f"<div class='sidebar-footer'>v12.5.0 ELITE PRO<br>Created by: <b>AntonioWebMaster</b></div>", unsafe_allow_html=True)

# --- 1. MONITORAGGIO GENERALE / DIARIO CLINICO ---
if nav == "📊 Monitoraggio Generale":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO INTEGRATO</h2><p>Visualizzazione cronologica di tutti gli eventi clinici e assistenziali per paziente</p></div>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 PAZIENTE: {nome.upper()}"):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                h = "<table class='report-table'><thead><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Evento</th></tr></thead><tbody>"
                for d, r, o, nt in evs:
                    h += f"<tr><td>{d}</td><td>{r}</td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- 2. MODULO EQUIPE (Psichiatra, Infermiere, Educatore, OSS) ---
elif nav == "👥 Modulo Equipe":
    # Banner dinamico in base al ruolo
    desc_ruolo = {
        "Psichiatra": "Pannello Medico per la gestione delle terapie farmacologiche e diagnosi.",
        "Infermiere": "Gestione somministrazioni, parametri vitali e consegne cliniche di turno.",
        "Educatore": "Monitoraggio attività riabilitative e gestione contabile della cassa pazienti.",
        "OSS": "Registrazione attività di igiene, comfort e sanificazione ambientale."
    }
    st.markdown(f"<div class='section-banner'><h2>MODULO {u['ruolo'].upper()}</h2><p>{desc_ruolo.get(u['ruolo'], '')}</p></div>", unsafe_allow_html=True)
    
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        if u['ruolo'] == "Psichiatra":
            with st.form("psic"):
                f, d = st.text_input("Farmaco"), st.text_input("Dosaggio")
                if st.form_submit_button("PRESCRIVI"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, medico) VALUES (?,?,?,?)", (p_id, f, d, firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📝 Prescritta: {f}", "Psichiatra", firma), True); st.rerun()

        elif u['ruolo'] == "Infermiere":
            t1, t2 = st.tabs(["💊 Somministrazione", "📊 Parametri"])
            with t1:
                ter = db_run("SELECT id_u, farmaco FROM terapie WHERE p_id=?", (p_id,))
                for tid, fa in ter:
                    if st.button(f"REGISTRA SOMM. {fa}", key=tid):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ Somministrato: {fa}", "Infermiere", firma), True); st.rerun()

        elif u['ruolo'] == "Educatore":
            tc, te = st.tabs(["💰 Cassa", "📝 Diario"])
            with tc:
                movs = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum([m[0] if m[1] == 'Entrata' else -m[0] for m in movs])
                st.metric("SALDO", f"€ {saldo:.2f}")
                with st.form("c"):
                    tipo=st.radio("Tipo", ["Entrata", "Uscita"]); imp=st.number_input("Euro"); cau=st.text_input("Causa")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), cau, imp, tipo, firma), True); st.rerun()

        elif u['ruolo'] == "OSS":
            m_s = st.selectbox("Attività", ["Igiene", "Pasti", "Sanificazione"])
            if st.button("REGISTRA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"🛠️ {m_s}", "OSS", firma), True); st.rerun()

# --- 3. AGENDA APPUNTAMENTI ---
elif nav == "📅 Agenda Appuntamenti":
    st.markdown("<div class='section-banner'><h2>AGENDA E SCADENZIARIO</h2><p>Pianificazione udienze, visite specialistiche e incontri con i familiari</p></div>", unsafe_allow_html=True)
    with st.form("ag"):
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        p_sel = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        c1, c2 = st.columns(2)
        d_app = c1.date_input("Data"); o_app = c2.text_input("Ora")
        cat = st.selectbox("Tipo", ["Uscita", "Visita Medica", "Udienza", "Parenti"])
        desc = st.text_area("Dettagli")
        if st.form_submit_button("INSERISCI"):
            db_run("INSERT INTO agenda (p_id, data, ora, categoria, evento) VALUES (?,?,?,?,?)", (p_id, d_app.strftime("%d/%m/%Y"), o_app, cat, desc), True); st.success("Ok")

# --- 4. GESTIONE SISTEMA ---
elif nav == "⚙️ Gestione Sistema":
    st.markdown("<div class='section-banner'><h2>AMMINISTRAZIONE</h2><p>Configurazione anagrafica pazienti e manutenzione del database di sistema</p></div>", unsafe_allow_html=True)
    np = st.text_input("Nome Nuovo Paziente")
    if st.button("SALVA"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
