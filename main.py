import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect PRO v20", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    .stTabs [data-baseweb="tab"] { font-size: 1.1rem; font-weight: bold; }
    .report-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 15px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 8px; text-align: left; }
    .report-table td { padding: 6px; border-bottom: 1px solid #e2e8f0; }
    .val-box { background: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #cbd5e1; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE (v20 - Struttura Definitiva) ---
DB_NAME = "rems_pro_v20.db"

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

# --- LOGIN ---
if 'u_data' not in st.session_state: st.session_state.u_data = None

if not st.session_state.u_data:
    st.title("🏥 REMS CONNECT PRO v20")
    c1, c2 = st.columns(2)
    with c1:
        with st.form("login"):
            u, p = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, hash_pw(p)))
                if res: st.session_state.u_data = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}; st.rerun()
    with c2:
        with st.form("reg"):
            nu, np = st.text_input("Nuovo User"), st.text_input("Pass", type="password")
            nn, nc, nq = st.text_input("Nome"), st.text_input("Cognome"), st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("Ok!")
    st.stop()

# --- DASHBOARD ---
usr = st.session_state.u_data
firma = f"{usr['nome']} {usr['cognome']} ({usr['ruolo']})"

p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
if not p_lista:
    st.warning("Aggiungi un paziente in Gestione.")
    if st.button("Vai a Gestione"): st.session_state.page = "Gestione"
    st.stop()

p_sel = st.sidebar.selectbox("PAZIENTE", [p[1] for p in p_lista])
p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

st.title(f"🏥 AREA {usr['ruolo'].upper()}")
st.sidebar.write(f"Operatore: **{firma}**")
if st.sidebar.button("LOGOUT"): st.session_state.u_data = None; st.rerun()

# --- FUNZIONI REPORT ---
def mostra_report(ruolo_filtro=None):
    if ruolo_filtro:
        data = db_run("SELECT data, op, nota FROM eventi WHERE id=? AND ruolo=? ORDER BY id_u DESC LIMIT 10", (p_id, ruolo_filtro))
    else:
        data = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 20", (p_id,))
    if data:
        df = pd.DataFrame(data)
        df.columns = ["Data", "Firma", "Nota"] if ruolo_filtro else ["Data", "Ruolo", "Firma", "Nota"]
        st.markdown("#### 📋 Report Ultime Attività")
        st.table(df)

# --- BLOCCHI PER RUOLO ---

# 🔴 PSICHIATRA
if usr['ruolo'] == "Psichiatra":
    t1, t2 = st.tabs(["💊 Prescrizione", "📂 Storico Terapie"])
    with t1:
        with st.form("psi_f"):
            f, d = st.text_input("Farmaco"), st.text_input("Dose")
            c1,c2,c3 = st.columns(3); m = c1.number_input("M",0); p = c2.number_input("P",0); n = c3.number_input("N",0)
            if st.form_submit_button("CONFERMA PRESCRIZIONE"):
                db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, m, p, n, firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 Prescritta: {f} {d}", "Psichiatra", firma), True); st.rerun()
    with t2:
        for tid, fa, do, m1, p1, n1 in db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,)):
            st.write(f"**{fa}** {do} ({m1}-{p1}-{n1})")
            if st.button("Elimina", key=f"del_{tid}"): db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True); st.rerun()
    mostra_report("Psichiatra")

# 🔵 INFERMIERE
elif usr['ruolo'] == "Infermiere":
    t1, t2, t3 = st.tabs(["💊 Terapia", "📊 Parametri", "📝 Consegne"])
    with t1:
        for tid, fa, do in db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,)):
            c1, c2, c3 = st.columns([3,1,1])
            c1.write(f"**{fa}** ({do})")
            if c2.button("✅", key=f"ok_{tid}"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrato: {fa}", "Infermiere", firma), True); st.success("OK")
            if c3.button("❌", key=f"no_{tid}"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"❌ RIFIUTATO: {fa}", "Infermiere", firma), True); st.warning("Rifiuto")
    with t2:
        with st.form("par_f"):
            # Nessun limite min_value per evitare blocchi su valori bassi
            ca, cb, cc, cd = st.columns(4)
            mx = ca.number_input("MAX", value=120); mn = cb.number_input("MIN", value=80)
            fc = cc.number_input("FC", value=70); sp = cd.number_input("SpO2", value=98)
            if st.form_submit_button("REGISTRA PARAMETRI"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA:{mx}/{mn} FC:{fc} SpO2:{sp}", "Infermiere", firma), True); st.rerun()
    with t3:
        fascia = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
        testo = st.text_area("Nota Consegna")
        if st.button("SALVA CONSEGNA"):
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 {fascia}: {testo}", "Infermiere", firma), True); st.rerun()
    mostra_report("Infermiere")

# 🟢 EDUCATORI
elif usr['ruolo'] == "Educatore":
    t1, t2 = st.tabs(["💰 Cassa", "📝 Attività"])
    with t1:
        movs = db_run("SELECT data, causale, importo, tipo FROM cassa WHERE p_id=?", (p_id,))
        saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
        st.metric("SALDO ATTUALE", f"€ {saldo:.2f}")
        with st.form("cassa_f"):
            tipo = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
            euro = st.number_input("Euro", value=0.0); caus = st.text_input("Causale")
            if st.form_submit_button("REGISTRA MOVIMENTO"):
                db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m"), caus, euro, tipo, firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {tipo}: €{euro:.2f} ({caus})", "Educatore", firma), True); st.rerun()
        if movs:
            df_c = pd.DataFrame(movs, columns=["Data", "Causale", "Importo", "Tipo"])
            df_c["Importo"] = df_c["Importo"].map('{:.2f}'.format) # Corregge troppi zeri
            st.table(df_c)
    with t2:
        att = st.text_area("Nota Attività Educativa")
        if st.button("SALVA ATTIVITÀ"):
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🎭 {att}", "Educatore", firma), True); st.rerun()
    mostra_report("Educatore")

# 🟠 OSS
elif usr['ruolo'] == "OSS":
    st.subheader("🛠️ Mansioni Giornaliere")
    mans = st.selectbox("Mansione", ["Pulizia Camera", "Pulizia Refettorio", "Sale Fumo", "Cortile", "Lavatrice", "Igiene"])
    nota_oss = st.text_area("Dettagli (opzionale)")
    if st.button("REGISTRA"):
        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🛠️ {mans}: {nota_oss}", "OSS", firma), True); st.rerun()
    mostra_report("OSS")

# --- GESTIONE ANAGRAFICA ---
st.sidebar.divider()
if st.sidebar.checkbox("⚙️ Gestione Pazienti"):
    st.divider()
    st.subheader("Gestione Anagrafica")
    new_p = st.text_input("Nuovo Paziente")
    if st.button("SALVA"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (new_p.upper(),), True); st.rerun()
    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        if st.button(f"Elimina {n}", key=f"p_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()

# --- DIARIO CLINICO INTEGRALE (IN FONDO A TUTTO) ---
st.divider()
st.subheader("📋 DIARIO CLINICO GENERALE")
mostra_report()
