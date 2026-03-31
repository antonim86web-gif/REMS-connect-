import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect PRO v21", layout="wide", page_icon="🏥")

# --- STILE INTEGRATO ---
st.markdown("""
<style>
    .stTabs [data-baseweb="tab"] { font-size: 1.1rem; font-weight: bold; }
    .report-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 15px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 8px; text-align: left; }
    .report-table td { padding: 6px; border-bottom: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE (v21 - Pulizia totale) ---
DB_NAME = "rems_pro_v21.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- LOGIN (Come 22495.jpg) ---
if 'u_data' not in st.session_state: st.session_state.u_data = None

if not st.session_state.u_data:
    st.title("REMS CONNECT V21")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Accedi")
        with st.form("login"):
            u, p = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, hash_pw(p)))
                if res: st.session_state.u_data = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}; st.rerun()
    with c2:
        st.subheader("Registrati")
        with st.form("reg"):
            nu, np = st.text_input("Nuovo User"), st.text_input("Pass", type="password")
            nn, nc, nq = st.text_input("Nome"), st.text_input("Cognome"), st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("Ok!")
    st.stop()

# --- DASHBOARD PRINCIPALE ---
usr = st.session_state.u_data
firma = f"{usr['nome']} {usr['cognome']} ({usr['ruolo']})"

p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
if not p_lista:
    st.warning("Aggiungi un paziente.")
    new_p = st.text_input("Nome Paziente")
    if st.button("Salva"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (new_p.upper(),), True); st.rerun()
    st.stop()

p_sel = st.sidebar.selectbox("PAZIENTE", [p[1] for p in p_lista])
p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

st.header(f"🏥 Area {usr['ruolo']}")
st.sidebar.write(f"Operatore: **{firma}**")
if st.sidebar.button("LOGOUT"): st.session_state.u_data = None; st.rerun()

# --- FUNZIONE REPORT AUTOMATICO ---
def mostra_tabella_report(ruolo_filtro=None):
    if ruolo_filtro:
        dati = db_run("SELECT data, op, nota FROM eventi WHERE id=? AND ruolo=? ORDER BY id_u DESC", (p_id, ruolo_filtro))
        colonne = ["Data", "Operatore", "Descrizione"]
    else:
        dati = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (p_id,))
        colonne = ["Data", "Ruolo", "Operatore", "Nota"]
    
    if dati:
        st.markdown("### 📊 Report Attività")
        st.table(pd.DataFrame(dati, columns=colonne))

# --- STRUTTURA A SCHEDE PER TUTTI (STILE 22475.jpg) ---

# 1. PSICHIATRA
if usr['ruolo'] == "Psichiatra":
    t1, t2 = st.tabs(["💊 Terapia", "📝 Diario"])
    with t1:
        with st.form("psi_ter"):
            f, d = st.text_input("Farmaco"), st.text_input("Dosaggio")
            c1,c2,c3 = st.columns(3)
            m, p, n = c1.number_input("Mattina", 0), c2.number_input("Pomeriggio", 0), c3.number_input("Notte", 0)
            if st.form_submit_button("AGGIUNGI TERAPIA"):
                db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, m, p, n, firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💊 Prescrizione: {f} {d}", "Psichiatra", firma), True); st.rerun()
        mostra_tabella_report("Psichiatra")

# 2. INFERMIERE
elif usr['ruolo'] == "Infermiere":
    t1, t2, t3 = st.tabs(["💊 Terapia", "📊 Parametri", "📝 Consegne"])
    with t1:
        for tid, fa, do in db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,)):
            ca, cb, cc = st.columns([3,1,1])
            ca.write(f"**{fa}** ({do})")
            if cb.button("✅", key=f"ok_{tid}"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrazione: {fa}", "Infermiere", firma), True); st.rerun()
            if cc.button("❌", key=f"no_{tid}"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"❌ Rifiuto: {fa}", "Infermiere", firma), True); st.rerun()
    with t2:
        with st.form("inf_par"):
            c_a, c_b, c_c, c_d = st.columns(4)
            # Rimosse validazioni 'min_value' per evitare blocchi come in 22493.jpg
            mx = c_a.number_input("MAX", value=120); mn = c_b.number_input("MIN", value=80)
            fc = c_c.number_input("FC", value=70); sp = c_d.number_input("SpO2", value=98)
            if st.form_submit_button("REGISTRA PARAMETRI"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA:{mx}/{mn} FC:{fc} SpO2:{sp}", "Infermiere", firma), True); st.rerun()
    with t3:
        turno = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
        testo = st.text_area("Testo Consegna")
        if st.button("SALVA CONSEGNA"):
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 {turno}: {testo}", "Infermiere", firma), True); st.rerun()
    mostra_tabella_report("Infermiere")

# 3. EDUCATORI
elif usr['ruolo'] == "Educatore":
    t1, t2 = st.tabs(["💰 Cassa", "📝 Diario"])
    with t1:
        movs = db_run("SELECT data, causale, importo, tipo, op FROM cassa WHERE p_id=?", (p_id,))
        saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
        st.metric("Saldo Attuale", f"€ {saldo:.2f}")
        with st.form("edu_cassa"):
            tp = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
            im = st.number_input("Importo", value=0.0); cs = st.text_input("Causale")
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m"), cs, im, tp, firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {tp}: €{im:.2f} ({cs})", "Educatore", firma), True); st.rerun()
        if movs:
            df_c = pd.DataFrame(movs, columns=["Data", "Causale", "Importo", "Tipo", "Operatore"])
            # Formattazione per eliminare gli zeri superflui (500.00 invece di 500.0000)
            df_c["Importo"] = df_c["Importo"].map('{:.2f}'.format)
            st.table(df_c)
    with t2:
        txt = st.text_area("Nota Educativa")
        if st.button("SALVA NOTA"):
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🎭 {txt}", "Educatore", firma), True); st.rerun()
        mostra_tabella_report("Educatore")

# 4. OSS
elif usr['ruolo'] == "OSS":
    t1, t2 = st.tabs(["🛠️ Mansioni", "📝 Diario"])
    with t1:
        m_sel = st.selectbox("Attività", ["Pulizia Camera", "Lavatrice", "Sale Fumo", "Igiene", "Accompagnamento"])
        if st.button("REGISTRA ATTIVITÀ"):
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🛠️ {m_sel}", "OSS", firma), True); st.rerun()
    with t2:
        mostra_tabella_report("OSS")

# --- DIARIO CLINICO INTEGRALE (VISIBILE A TUTTI) ---
st.divider()
st.subheader("📋 Diario Clinico Generale")
mostra_tabella_report()
