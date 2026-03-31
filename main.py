import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS CONNECT PERFECT", layout="wide", page_icon="🏥")

# --- STILE ORIGINALE ---
st.markdown("""
<style>
    .access-box { padding: 30px; border-radius: 15px; border: 2px solid #e2e8f0; background-color: #f8fafc; min-height: 400px; }
    .sector-box { padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #cbd5e1; min-height: 450px; background: white; }
    .h-red { color: #dc2626; border-bottom: 2px solid #dc2626; }
    .h-blue { color: #2563eb; border-bottom: 2px solid #2563eb; }
    .h-green { color: #059669; border-bottom: 2px solid #059669; }
    .h-orange { color: #d97706; border-bottom: 2px solid #d97706; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE (Nuovo nome per evitare conflitti con versioni vecchie) ---
DB_NAME = "rems_stable_final.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat TEXT, pom TEXT, not TEXT, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 1. ACCESSO DIVISO IN DUE ---
if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    st.title("🏥 REMS CONNECT - ACCESSO")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="access-box">', unsafe_allow_html=True)
        st.subheader("🔐 LOGIN")
        with st.form("login_f"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, hash_pw(p)))
                if res: st.session_state.user = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}; st.rerun()
                else: st.error("Errore credenziali")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="access-box">', unsafe_allow_html=True)
        st.subheader("📝 REGISTRAZIONE")
        with st.form("reg_f"):
            nu = st.text_input("Nuovo User")
            np = st.text_input("Password", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("Fatto!")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 2. DASHBOARD A 4 SETTORI ---
usr = st.session_state.user
firma = f"{usr['nome']} {usr['cognome']} ({usr['ruolo']})"

p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
if not p_lista:
    st.warning("Aggiungi un paziente.")
    np = st.text_input("Nome Paziente")
    if st.button("Salva"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    st.stop()

p_sel = st.sidebar.selectbox("PAZIENTE SELEZIONATO", [p[1] for p in p_lista])
p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
if st.sidebar.button("ESCI"): st.session_state.user = None; st.rerun()

st.title(f"🏥 Diario REMS: {p_sel}")

c_sx, c_dx = st.columns(2)

# SETTORE 1: PSICHIATRIA
with c_sx:
    st.markdown('<div class="sector-box"><h3 class="h-red">🔴 AREA PSICHIATRA</h3>', unsafe_allow_html=True)
    if usr['ruolo'] == "Psichiatra":
        with st.form("f_psi"):
            f, d = st.text_input("Farmaco"), st.text_input("Dose")
            if st.form_submit_button("PRESCRIVI"):
                db_run("INSERT INTO terapie (p_id, farmaco, dose) VALUES (?,?,?)", (p_id, f, d), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 Prescritto: {f}", "Psichiatra", firma), True); st.rerun()
    for tid, fa, do in db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,)):
        st.write(f"💊 **{fa}** {do}")
    st.markdown('</div>', unsafe_allow_html=True)

# SETTORE 2: INFERMIERISTICA (Somministrazione e Parametri)
with c_dx:
    st.markdown('<div class="sector-box"><h3 class="h-blue">🔵 AREA INFERMIERE</h3>', unsafe_allow_html=True)
    if usr['ruolo'] == "Infermiere":
        with st.expander("Somministra Farmaci"):
            for tid, fa, do in db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,)):
                if st.button(f"OK {fa}", key=f"s_{tid}"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrato: {fa}", "Infermiere", firma), True); st.rerun()
        with st.form("f_inf"):
            p1, p2 = st.columns(2)
            pa = p1.text_input("PA"); fc = p2.number_input("FC", value=70)
            if st.form_submit_button("SALVA PARAMETRI"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA: {pa} FC: {fc}", "Infermiere", firma), True); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# SETTORE 3: EDUCATORE (Cassa)
with c_sx:
    st.markdown('<div class="sector-box"><h3 class="h-green">🟢 AREA EDUCATORI</h3>', unsafe_allow_html=True)
    movs = db_run("SELECT data, causale, importo, tipo FROM cassa WHERE p_id=?", (p_id,))
    saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
    st.metric("SALDO CASSA", f"€ {saldo:.2f}")
    if usr['ruolo'] == "Educatore":
        with st.form("f_edu"):
            t = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
            i = st.number_input("Importo", value=0.0); c = st.text_input("Causale")
            if st.form_submit_button("REGISTRA MOVIMENTO"):
                db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m"), c, i, t, firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {t}: €{i:.2f} ({c})", "Educatore", firma), True); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# SETTORE 4: OSS (Diario Storico)
with c_dx:
    st.markdown('<div class="sector-box"><h3 class="h-orange">🟠 DIARIO CLINICO</h3>', unsafe_allow_html=True)
    dati = db_run("SELECT data, ruolo, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 10", (p_id,))
    if dati:
        df = pd.DataFrame(dati, columns=["Data", "Ruolo", "Nota"])
        st.table(df)
    st.markdown('</div>', unsafe_allow_html=True)
