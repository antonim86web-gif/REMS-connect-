import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect GOLD", layout="wide", page_icon="🏥")

# --- STILE ORIGINALE (Pulito e ordinato) ---
st.markdown("""
<style>
    .stTabs [data-baseweb="tab"] { font-size: 1.1rem; font-weight: bold; }
    .report-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 15px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 10px; text-align: left; }
    .report-table td { padding: 8px; border-bottom: 1px solid #e2e8f0; }
    .stNumberInput input { font-size: 1.1rem !important; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE (Versione Stabile) ---
DB_NAME = "rems_gold_stable.db"

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

# --- GESTIONE ACCESSO ---
if 'u_data' not in st.session_state: st.session_state.u_data = None

if not st.session_state.u_data:
    st.title("🏥 REMS CONNECT - ACCESSO")
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
    st.warning("Inserisci un paziente in anagrafica.")
    np = st.text_input("Nome Paziente")
    if st.button("Salva"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    st.stop()

p_sel = st.sidebar.selectbox("SELEZIONA PAZIENTE", [p[1] for p in p_lista])
p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

st.title(f"🏥 Area {usr['ruolo']}")
st.sidebar.write(f"Operatore: **{firma}**")
if st.sidebar.button("LOGOUT"): st.session_state.u_data = None; st.rerun()

# --- FUNZIONE REPORT ---
def mostra_report(filtro=None):
    query = "SELECT data, op, nota FROM eventi WHERE id=? AND ruolo=? ORDER BY id_u DESC" if filtro else "SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC"
    params = (p_id, filtro) if filtro else (p_id,)
    dati = db_run(query, params)
    if dati:
        df = pd.DataFrame(dati, columns=["Data", "Firma", "Nota"] if filtro else ["Data", "Ruolo", "Firma", "Nota"])
        st.table(df)

# --- INTERFACCIA A SCHEDE ---
t1, t2, t3 = st.tabs(["💊 Operazioni", "📊 Parametri / Cassa", "📝 Diario Completo"])

with t1:
    # AZIONI PER PSICHIATRA
    if usr['ruolo'] == "Psichiatra":
        with st.form("psi_form"):
            f, d = st.text_input("Farmaco"), st.text_input("Dosaggio")
            c1,c2,c3 = st.columns(3); m = c1.number_input("M",0); p = c2.number_input("P",0); n = c3.number_input("N",0)
            if st.form_submit_button("AGGIUNGI TERAPIA"):
                db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, m, p, n, firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💊 Prescrizione: {f} {d}", "Psichiatra", firma), True); st.rerun()
    
    # AZIONI PER INFERMIERE
    elif usr['ruolo'] == "Infermiere":
        st.subheader("Somministrazione Terapia")
        for tid, fa, do in db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,)):
            ca, cb, cc = st.columns([3,1,1])
            ca.write(f"**{fa}** ({do})")
            if cb.button("✅", key=f"ok_{tid}"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrato: {fa}", "Infermiere", firma), True); st.rerun()
            if cc.button("❌", key=f"no_{tid}"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"❌ Rifiutato: {fa}", "Infermiere", firma), True); st.rerun()

    # AZIONI PER EDUCATORI / OSS
    elif usr['ruolo'] in ["Educatore", "OSS"]:
        st.subheader(f"Registrazione Attività {usr['ruolo']}")
        testo_libero = st.text_area("Descrizione attività")
        if st.button("SALVA ATTIVITÀ"):
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), testo_libero, usr['ruolo'], firma), True); st.rerun()

    st.divider()
    mostra_report(usr['ruolo'])

with t2:
    # PARAMETRI (Infermiere)
    if usr['ruolo'] == "Infermiere":
        with st.form("par"):
            c1,c2,c3,c4 = st.columns(4)
            mx = c1.number_input("MAX", value=120); mn = c2.number_input("MIN", value=80)
            fc = c3.number_input("FC", value=70); sp = c4.number_input("SpO2", value=98)
            if st.form_submit_button("REGISTRA PARAMETRI"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA:{mx}/{mn} FC:{fc} SpO2:{sp}", "Infermiere", firma), True); st.rerun()
    
    # CASSA (Educatore)
    elif usr['ruolo'] == "Educatore":
        movs = db_run("SELECT data, causale, importo, tipo FROM cassa WHERE p_id=?", (p_id,))
        saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
        st.metric("SALDO ATTUALE", f"€ {saldo:.2f}")
        with st.form("cas"):
            tipo = st.radio("Cassa", ["Entrata", "Uscita"], horizontal=True)
            imp = st.number_input("Importo", value=0.0); cau = st.text_input("Causale")
            if st.form_submit_button("SALVA MOVIMENTO"):
                db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m"), cau, imp, tipo, firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {tipo}: €{imp:.2f} ({cau})", "Educatore", firma), True); st.rerun()
        if movs:
            df_c = pd.DataFrame(movs, columns=["Data", "Causale", "Euro", "Tipo"])
            df_c["Euro"] = df_c["Euro"].map('{:.2f}'.format)
            st.table(df_c)
    else:
        st.info("Questa sezione è riservata a Infermieri (Parametri) ed Educatori (Cassa).")

with t3:
    st.subheader("Diario Clinico Integrale")
    mostra_report()

# --- SIDEBAR GESTIONE ---
if st.sidebar.checkbox("⚙️ Anagrafica Pazienti"):
    st.divider()
    n_p = st.text_input("Nome e Cognome Paziente")
    if st.button("AGGIUNGI"):
        db_run("INSERT INTO pazienti (nome) VALUES (?)", (n_p.upper(),), True); st.rerun()
