import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS CONNECT ULTIMATE", layout="wide", page_icon="🏥")

# --- STILE PROFESSIONALE (Quadranti e Accesso) ---
st.markdown("""
<style>
    .access-box { padding: 30px; border-radius: 15px; border: 2px solid #e2e8f0; background-color: #f8fafc; min-height: 400px; }
    .sector-box { padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #cbd5e1; min-height: 450px; background: white; }
    .h-red { color: #dc2626; border-bottom: 2px solid #dc2626; }
    .h-blue { color: #2563eb; border-bottom: 2px solid #2563eb; }
    .h-green { color: #059669; border-bottom: 2px solid #059669; }
    .h-orange { color: #d97706; border-bottom: 2px solid #d97706; }
    .report-mini { font-size: 0.85rem; background: #f1f5f9; padding: 8px; border-radius: 5px; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ---
DB_NAME = "rems_perfect_v24.db"

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

# --- 1. ACCESSO DIVISO IN DUE BLOCCHI ---
if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    st.title("🏥 REMS CONNECT - ACCESSO DIARIO")
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown('<div class="access-box">', unsafe_allow_html=True)
        st.subheader("🔐 LOGIN")
        with st.form("login_form"):
            u, p = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, hash_pw(p)))
                if res: st.session_state.user = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}; st.rerun()
                else: st.error("Dati errati")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_r:
        st.markdown('<div class="access-box">', unsafe_allow_html=True)
        st.subheader("📝 REGISTRAZIONE")
        with st.form("reg_form"):
            nu, np = st.text_input("Nuovo User"), st.text_input("Nuova Pass", type="password")
            nn, nc, nq = st.text_input("Nome"), st.text_input("Cognome"), st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("CREA ACCOUNT"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("Registrato!")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 2. DASHBOARD A 4 SETTORI FISSI ---
usr = st.session_state.user
firma = f"{usr['nome']} {usr['cognome']} ({usr['ruolo']})"

p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
if not p_lista:
    st.warning("Aggiungi un paziente per iniziare.")
    np = st.text_input("Nuovo Paziente")
    if st.button("Salva"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    st.stop()

p_sel = st.sidebar.selectbox("PAZIENTE ATTIVO", [p[1] for p in p_lista])
p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
st.sidebar.button("LOGOUT", on_click=lambda: st.session_state.update({"user": None}))

st.title(f"🏥 Gestione REMS: {p_sel}")

col1, col2 = st.columns(2)

# --- SETTORE 1: PSICHIATRA ---
with col1:
    st.markdown('<div class="sector-box"><h3 class="h-red">🔴 AREA PSICHIATRA</h3>', unsafe_allow_html=True)
    if usr['ruolo'] == "Psichiatra":
        with st.form("psi_f", clear_on_submit=True):
            f, d = st.text_input("Farmaco"), st.text_input("Dose")
            if st.form_submit_button("AGGIUNGI"):
                db_run("INSERT INTO terapie (p_id, farmaco, dose) VALUES (?,?,?)", (p_id, f, d), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 Prescr.: {f} {d}", "Psichiatra", firma), True); st.rerun()
    
    st.write("**Terapie Attive:**")
    for tid, fa, do in db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,)):
        st.markdown(f"💊 `{fa} {do}`")
    st.markdown('</div>', unsafe_allow_html=True)

# --- SETTORE 2: INFERMIERE ---
with col2:
    st.markdown('<div class="sector-box"><h3 class="h-blue">🔵 AREA INFERMIERE</h3>', unsafe_allow_html=True)
    if usr['ruolo'] == "Infermiere":
        with st.expander("Somministrazione"):
            for tid, fa, do in db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,)):
                if st.button(f"Somministra {fa}", key=f"s_{tid}"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrato: {fa}", "Infermiere", firma), True); st.rerun()
        
        with st.form("par_f", clear_on_submit=True):
            st.write("**Parametri (Senza Blocchi)**")
            c1, c2 = st.columns(2)
            pa = c1.text_input("PA (es. 120/80)"); fc = c2.number_input("FC", value=70)
            if st.form_submit_button("SALVA PARAMETRI"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA: {pa} | FC: {fc}", "Infermiere", firma), True); st.rerun()
    
    for d, n in db_run("SELECT data, nota FROM eventi WHERE id=? AND ruolo='Infermiere' ORDER BY id_u DESC LIMIT 3", (p_id,)):
        st.markdown(f"<div class='report-mini'><b>{d}</b>: {n}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

col3, col4 = st.columns(2)

# --- SETTORE 3: EDUCATORI ---
with col3:
    st.markdown('<div class="sector-box"><h3 class="h-green">🟢 AREA EDUCATORI</h3>', unsafe_allow_html=True)
    movs = db_run("SELECT data, causale, importo, tipo FROM cassa WHERE p_id=?", (p_id,))
    saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
    st.subheader(f"Cassa: € {saldo:.2f}")
    
    if usr['ruolo'] == "Educatore":
        with st.form("cas_f", clear_on_submit=True):
            tp = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
            im = st.number_input("Euro", value=0.0); ca = st.text_input("Causale")
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m"), ca, im, tp, firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {tp}: €{im:.2f} ({ca})", "Educatore", firma), True); st.rerun()
    
    for d, c, i, t in movs[-3:]: st.caption(f"💰 {d}: {t} €{i:.2f} ({c})")
    st.markdown('</div>', unsafe_allow_html=True)

# --- SETTORE 4: DIARIO INTEGRALE ---
with col4:
    st.markdown('<div class="sector-box"><h3 class="h-orange">🟠 DIARIO GENERALE</h3>', unsafe_allow_html=True)
    eventi = db_run("SELECT data, ruolo, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 10", (p_id,))
    if eventi:
        df = pd.DataFrame(eventi, columns=["Data/Ora", "Ruolo", "Evento"])
        st.table(df)
    st.markdown('</div>', unsafe_allow_html=True)
