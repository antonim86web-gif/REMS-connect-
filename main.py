import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v12.5 ---
st.set_page_config(page_title="REMS Connect ELITE PRO", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 2px solid #334155; }
    .sidebar-title { color: #f8fafc !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; padding: 25px 0; border-bottom: 1px solid #334155; }
    .section-banner { background: linear-gradient(90deg, #1e3a8a 0%, #1e40af 100%); color: white !important; padding: 30px; border-radius: 15px; margin-bottom: 25px; text-align: center; }
    .section-banner h2 { color: white !important; margin: 0; text-transform: uppercase; font-weight: 900; }
    .report-table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 12px; text-align: left; }
    .report-table td { padding: 10px; border: 1px solid #e2e8f0; font-size: 0.85rem; }
    .therapy-card { background: white; border-left: 6px solid #1e3a8a; padding: 15px; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

# --- ENGINE DATABASE ---
DB_NAME = "rems_enterprise_v12.db"

def db_init():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, data_ingresso TEXT, stato TEXT DEFAULT 'ATTIVO')")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, categoria TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (id_t INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, stato TEXT DEFAULT 'ATTIVO')")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (id_c INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (id_a INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, categoria TEXT, evento TEXT)")
        conn.commit()

def db_query(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

db_init()
def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = None

if not st.session_state.auth:
    st.markdown("<div class='section-banner'><h2>REMS CONNECT ELITE PRO</h2><p>Accesso Sistema Informativo</p></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        with st.form("login"):
            u_in, p_in = st.text_input("User"), st.text_input("Password", type="password")
            if st.form_submit_button("LOGIN"):
                res = db_query("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res:
                    st.session_state.auth = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
    with c2:
        with st.form("reg"):
            nu, np = st.text_input("Nuovo User"), st.text_input("Nuova PWD", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_query("INSERT INTO utenti (user, pwd, nome, cognome, qualifica) VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True)
    st.stop()

u = st.session_state.auth
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
nav = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "💊 Terapie", "📝 Diario", "💰 Cassa", "📅 Agenda", "⚙️ Sistema"])
if st.sidebar.button("LOGOUT"): st.session_state.auth = None; st.rerun()

# --- 1. MONITORAGGIO ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>SITUAZIONE REPARTO</h2></div>", unsafe_allow_html=True)
    pax = db_query("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
    for pid, nome in pax:
        with st.expander(f"📁 CARTELLA: {nome}"):
            evs = db_query("SELECT data, op, nota FROM eventi WHERE p_id=? ORDER BY id_u DESC LIMIT 10", (pid,))
            if evs:
                st.table(pd.DataFrame(evs, columns=["Data", "Operatore", "Nota"]))

# --- 2. TERAPIE ---
elif nav == "💊 Terapie":
    st.markdown("<div class='section-banner'><h2>GESTIONE FARMACI</h2></div>", unsafe_allow_html=True)
    if u['ruolo'] == "Psichiatra":
        with st.form("presc"):
            p_sel = st.selectbox("Paziente", [p[1] for p in db_query("SELECT id, nome FROM pazienti")])
            pid = [p[0] for p in db_query("SELECT id, nome FROM pazienti") if p[1] == p_sel][0]
            f, d = st.text_input("Farmaco"), st.text_input("Dose")
            c1,c2,c3 = st.columns(3); m=c1.checkbox("MAT"); p=c2.checkbox("POM"); n=c3.checkbox("NOTT")
            if st.form_submit_button("PRESCRIVI"):
                db_query("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (pid, f, d, int(m), int(p), int(n), firma), True)
                st.success("Prescrizione salvata")
    
    elif u['ruolo'] == "Infermiere":
        turno = st.radio("Turno:", ["MAT", "POM", "NOTT"], horizontal=True)
        t_col = turno.lower() if turno != "NOTT" else "nott"
        data_t = db_query(f"SELECT p.nome, t.farmaco, t.dose, t.id_t, t.p_id FROM terapie t JOIN pazienti p ON t.p_id = p.id WHERE t.{t_col}=1 AND t.stato='ATTIVO'")
        for nome, farm, dose, tid, pid in data_t:
            st.markdown(f"<div class='therapy-card'><b>{nome}</b>: {farm} ({dose})</div>", unsafe_allow_html=True)
            if st.button("FIRMA SOMMINISTRAZIONE", key=f"f_{tid}"):
                db_query("INSERT INTO eventi (p_id, data, nota, ruolo, op, categoria) VALUES (?,?,?,?,?,?)", (pid, datetime.now().strftime("%d/%m %H:%M"), f"SOMM: {farm} ({turno})", u['ruolo'], firma, "Terapia"), True)
                st.rerun()

# --- 3. DIARIO ---
elif nav == "📝 Diario":
    st.markdown("<div class='section-banner'><h2>DIARIO MULTIDISCIPLINARE</h2></div>", unsafe_allow_html=True)
    p_sel = st.selectbox("Paziente", [p[1] for p in db_query("SELECT id, nome FROM pazienti")])
    pid = [p[0] for p in db_query("SELECT id, nome FROM pazienti") if p[1] == p_sel][0]
    with st.form("diario"):
        nota = st.text_area("Inserisci nota")
        if st.form_submit_button("SALVA"):
            db_query("INSERT INTO eventi (p_id, data, nota, ruolo, op, categoria) VALUES (?,?,?,?,?,?)", (pid, datetime.now().strftime("%d/%m/%Y %H:%M"), nota, u['ruolo'], firma, "Diario"), True)
            st.success("Nota salvata")

# --- 4. CASSA ---
elif nav == "💰 Cassa":
    st.markdown("<div class='section-banner'><h2>CONTABILITÀ PAZIENTI</h2></div>", unsafe_allow_html=True)
    p_sel = st.selectbox("Paziente", [p[1] for p in db_query("SELECT id, nome FROM pazienti")])
    pid = [p[0] for p in db_query("SELECT id, nome FROM pazienti") if p[1] == p_sel][0]
    movs = db_query("SELECT importo, tipo FROM cassa WHERE p_id=?", (pid,))
    saldo = sum([m[0] if m[1] == "Entrata" else -m[0] for m in movs])
    st.metric("Saldo attuale", f"€ {saldo:.2f}")
    with st.form("cassa"):
        t = st.radio("Tipo", ["Entrata", "Uscita"]); i = st.number_input("Euro"); c = st.text_input("Causale")
        if st.form_submit_button("REGISTRA"):
            db_query("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (pid, date.today().strftime("%d/%m/%Y"), c, i, t, firma), True)
            st.rerun()

# --- 5. AGENDA ---
elif nav == "📅 Agenda":
    st.markdown("<div class='section-banner'><h2>APPUNTAMENTI E UDIENZE</h2></div>", unsafe_allow_html=True)
    with st.form("agenda"):
        p_sel = st.selectbox("Paziente", [p[1] for p in db_query("SELECT id, nome FROM pazienti")])
        pid = [p[0] for p in db_query("SELECT id, nome FROM pazienti") if p[1] == p_sel][0]
        d = st.date_input("Data"); o = st.text_input("Ora"); cat = st.selectbox("Tipo", ["Udienza", "Visita", "Permesso"]); ev = st.text_area("Note")
        if st.form_submit_button("AGGIUNGI"):
            db_query("INSERT INTO agenda (p_id, data, ora, categoria, evento) VALUES (?,?,?,?,?)", (pid, d.strftime("%d/%m/%Y"), o, cat, ev), True)
            st.success("Pianificato")

# --- 6. SISTEMA ---
elif nav == "⚙️ Sistema":
    st.markdown("### GESTIONE ANAGRAFICA")
    with st.form("paz"):
        nome = st.text_input("Nuovo Paziente")
        if st.form_submit_button("REGISTRA"):
            db_query("INSERT INTO pazienti (nome, data_ingresso) VALUES (?,?)", (nome.upper(), date.today().strftime("%d/%m/%Y")), True)
            st.success("Inserito")
