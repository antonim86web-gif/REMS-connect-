import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS CONNECT PERFECT", layout="wide", page_icon="🏥")

# --- STILE ORIGINALE (Quadranti e Accesso) ---
st.markdown("""
<style>
    .access-box { padding: 30px; border-radius: 15px; border: 2px solid #e2e8f0; background-color: #f8fafc; min-height: 400px; }
    .sector-box { padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #cbd5e1; min-height: 480px; background: white; }
    .h-red { color: #dc2626; border-bottom: 2px solid #dc2626; padding-bottom: 5px; }
    .h-blue { color: #2563eb; border-bottom: 2px solid #2563eb; padding-bottom: 5px; }
    .h-green { color: #059669; border-bottom: 2px solid #059669; padding-bottom: 5px; }
    .h-orange { color: #d97706; border-bottom: 2px solid #d97706; padding-bottom: 5px; }
    .stTable { font-size: 0.85rem !important; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ---
DB_NAME = "rems_perfect_stable.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 1. ACCESSO DIVISO IN DUE ---
if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    st.title("🏥 REMS CONNECT - ACCESSO DIARIO")
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown('<div class="access-box">', unsafe_allow_html=True)
        st.subheader("🔐 LOGIN")
        with st.form("login_f"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("ENTRA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, hash_pw(p)))
                if res: 
                    st.session_state.user = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Accesso negato")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_r:
        st.markdown('<div class="access-box">', unsafe_allow_html=True)
        st.subheader("📝 REGISTRAZIONE")
        with st.form("reg_f"):
            nu = st.text_input("Username scelto")
            np = st.text_input("Password scelta", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("CREA ACCOUNT"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True)
                st.success("Registrato!")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 2. DASHBOARD A 4 SETTORI FISSI ---
usr = st.session_state.user
firma = f"{usr['nome']} {usr['cognome']} ({usr['ruolo']})"

p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
if not p_lista:
    st.warning("Inserisci il primo paziente.")
    np = st.text_input("Nome Paziente")
    if st.button("Salva"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    st.stop()

p_sel = st.sidebar.selectbox("PAZIENTE", [p[1] for p in p_lista])
p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
if st.sidebar.button("LOGOUT"): st.session_state.user = None; st.rerun()

st.title(f"🏥 {p_sel} - Gestione REMS")

c_sx, c_dx = st.columns(2)

# QUADRANTE 1: TERAPIA (PSICHIATRA)
with c_sx:
    st.markdown('<div class="sector-box"><h3 class="h-red">🔴 AREA PSICHIATRA</h3>', unsafe_allow_html=True)
    if usr['ruolo'] == "Psichiatra":
        with st.form("psi_f"):
            f, d = st.text_input("Farmaco"), st.text_input("Dosaggio")
            if st.form_submit_button("PRESCRIVI"):
                db_run("INSERT INTO terapie (p_id, farmaco, dose) VALUES (?,?,?)", (p_id, f, d), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💊 Prescritto: {f}", "Psichiatra", firma), True); st.rerun()
    st.write("**Terapie in corso:**")
    for t in db_run("SELECT farmaco, dose FROM terapie WHERE p_id=?", (p_id,)):
        st.write(f"- {t[0]} ({t[1]})")
    st.markdown('</div>', unsafe_allow_html=True)

# QUADRANTE 2: PARAMETRI (INFERMIERE)
with c_dx:
    st.markdown('<div class="sector-box"><h3 class="h-blue">🔵 AREA INFERMIERE</h3>', unsafe_allow_html=True)
    if usr['ruolo'] == "Infermiere":
        with st.form("inf_f"):
            st.write("Registra Parametri:")
            p1, p2 = st.columns(2)
            pa = p1.text_input("Pressione"); fc = p2.number_input("Freq. Cardiaca", value=70)
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA: {pa} FC: {fc}", "Infermiere", firma), True); st.rerun()
    st.write("**Ultime somministrazioni:**")
    for e in db_run("SELECT data, nota FROM eventi WHERE id=? AND ruolo='Infermiere' ORDER BY id_u DESC LIMIT 3", (p_id,)):
        st.caption(f"{e[0]}: {e[1]}")
    st.markdown('</div>', unsafe_allow_html=True)

# QUADRANTE 3: CASSA (EDUCATORE)
with c_sx:
    st.markdown('<div class="sector-box"><h3 class="h-green">🟢 AREA EDUCATORI</h3>', unsafe_allow_html=True)
    movs = db_run("SELECT data, causale, importo, tipo FROM cassa WHERE p_id=?", (p_id,))
    saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
    st.subheader(f"Saldo Cassa: € {saldo:.2f}")
    if usr['ruolo'] == "Educatore":
        with st.form("edu_f"):
            t = st.radio("Operazione", ["Entrata", "Uscita"], horizontal=True)
            i = st.number_input("Euro", value=0.0); c = st.text_input("Causale")
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m"), c, i, t, firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {t}: €{i:.2f} ({c})", "Educatore", firma), True); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# QUADRANTE 4: DIARIO (TUTTI)
with c_dx:
    st.markdown('<div class="sector-box"><h3 class="h-orange">🟠 DIARIO CLINICO INTEGRALE</h3>', unsafe_allow_html=True)
    dati = db_run("SELECT data, ruolo, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 15", (p_id,))
    if dati:
        df = pd.DataFrame(dati, columns=["Data/Ora", "Ruolo", "Nota"])
        st.table(df)
    st.markdown('</div>', unsafe_allow_html=True)
