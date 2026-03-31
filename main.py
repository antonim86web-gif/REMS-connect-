import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide", page_icon="🏥")

# CSS Esteso per mantenere la grafica professionale e i quadranti
st.markdown("""
<style>
    .stTabs [data-baseweb="tab"] { font-size: 1.1rem; font-weight: bold; }
    .report-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 15px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 10px; text-align: left; }
    .report-table td { padding: 8px; border-bottom: 1px solid #e2e8f0; }
    .stMetric { background-color: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; }
    .footer { position: fixed; bottom: 10px; width: 100%; text-align: center; color: #94a3b8; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ENGINE ---
DB_NAME = "rems_clinical_v25.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        # Creazione tabelle complete
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- GESTIONE ACCESSO DIVISA ---
if 'u_data' not in st.session_state: st.session_state.u_data = None

if not st.session_state.u_data:
    st.title("🏥 REMS CONNECT - GESTIONE DIARIO")
    col_login, col_reg = st.columns(2)
    
    with col_login:
        st.subheader("🔐 LOGIN")
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, hash_pw(p)))
                if res: 
                    st.session_state.u_data = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Credenziali non corrette")
                
    with col_reg:
        st.subheader("📝 REGISTRAZIONE")
        with st.form("reg_form"):
            nu = st.text_input("Nuovo User")
            np = st.text_input("Nuova Pass", type="password")
            nn = st.text_input("Nome")
            nc = st.text_input("Cognome")
            nq = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                if nu and np:
                    db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True)
                    st.success("Operatore registrato!")
    st.stop()

# --- CORE APPLICATION ---
usr = st.session_state.u_data
firma = f"{usr['nome']} {usr['cognome']} ({usr['ruolo']})"

# Caricamento Pazienti
p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
if not p_lista:
    st.warning("Archivio pazienti vuoto.")
    nome_p = st.text_input("Inserisci Nome Paziente")
    if st.button("SALVA"):
        db_run("INSERT INTO pazienti (nome) VALUES (?)", (nome_p.upper(),), True)
        st.rerun()
    st.stop()

# Sidebar
st.sidebar.title("🏥 DASHBOARD")
p_sel = st.sidebar.selectbox("PAZIENTE SELEZIONATO", [p[1] for p in p_lista])
p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
st.sidebar.write("---")
st.sidebar.write(f"Operatore: **{firma}**")
if st.sidebar.button("LOGOUT"):
    st.session_state.u_data = None
    st.rerun()

# Funzione Reportistica
def mostra_report(ruolo_filtro=None):
    if ruolo_filtro:
        dati = db_run("SELECT data, op, nota FROM eventi WHERE id=? AND ruolo=? ORDER BY id_u DESC", (p_id, ruolo_filtro))
        colonne = ["Data/Ora", "Operatore", "Nota"]
    else:
        dati = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 20", (p_id,))
        colonne = ["Data/Ora", "Ruolo", "Operatore", "Descrizione"]
    
    if dati:
        df = pd.DataFrame(dati, columns=colonne)
        st.table(df)

# --- SEZIONI OPERATIVE ---

if usr['ruolo'] == "Psichiatra":
    t1, t2 = st.tabs(["💊 Terapie", "📓 Diario Psichiatrico"])
    with t1:
        with st.form("psi_ter"):
            st.subheader("Prescrizione Farmacologica")
            f = st.text_input("Farmaco"); d = st.text_input("Dosaggio")
            c1, c2, c3 = st.columns(3)
            m = c1.number_input("Mattina", 0); p = c2.number_input("Pomeriggio", 0); n = c3.number_input("Notte", 0)
            if st.form_submit_button("CONFERMA"):
                db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, m, p, n, firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💊 Prescritto: {f} {d}", "Psichiatra", firma), True); st.rerun()
    with t2:
        mostra_report("Psichiatra")

elif usr['ruolo'] == "Infermiere":
    t1, t2, t3 = st.tabs(["💊 Somministrazione", "📊 Parametri", "📝 Consegne"])
    with t1:
        st.subheader("Terapie da Somministrare")
        terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
        for tid, fa, do, m, p, n in terapie:
            c1, c2, c3 = st.columns([3,1,1])
            c1.write(f"**{fa}** ({do}) - [{m}-{p}-{n}]")
            if c2.button("✅ OK", key=f"ok_{tid}"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrato: {fa}", "Infermiere", firma), True); st.rerun()
            if c3.button("❌ NO", key=f"no_{tid}"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"❌ Rifiuto: {fa}", "Infermiere", firma), True); st.rerun()
    with t2:
        with st.form("par_f"):
            c1, c2, c3, c4 = st.columns(4)
            mx = c1.number_input("MAX", value=120); mn = c2.number_input("MIN", value=80)
            fc = c3.number_input("FC", value=70); sp = c4.number_input("SpO2", value=98)
            if st.form_submit_button("SALVA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA: {mx}/{mn} | FC: {fc} | SpO2: {sp}%", "Infermiere", firma), True); st.rerun()
    with t3:
        txt = st.text_area("Consegna Turno")
        if st.button("REGISTRA"):
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 {txt}", "Infermiere", firma), True); st.rerun()
    mostra_report("Infermiere")

elif usr['ruolo'] == "Educatore":
    t1, t2 = st.tabs(["💰 Cassa", "🎨 Attività"])
    with t1:
        movs = db_run("SELECT data, causale, importo, tipo FROM cassa WHERE p_id=?", (p_id,))
        saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
        st.metric("SALDO", f"€ {saldo:.2f}")
        with st.form("cassa_f"):
            tipo = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
            imp = st.number_input("Euro", value=0.0); cau = st.text_input("Causale")
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m"), cau, imp, tipo, firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {tipo}: €{imp:.2f} ({cau})", "Educatore", firma), True); st.rerun()
        if movs:
            df_c = pd.DataFrame(movs, columns=["Data", "Causale", "Euro", "Tipo"])
            df_c["Euro"] = df_c["Euro"].map('{:.2f}'.format)
            st.table(df_c)
    with t2:
        nota_e = st.text_area("Nota Attività")
        if st.button("SALVA NOTA"):
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🎭 {nota_e}", "Educatore", firma), True); st.rerun()
    mostra_report("Educatore")

elif usr['ruolo'] == "OSS":
    mansioni = st.multiselect("Azioni", ["Igiene", "Riordino", "Accompagnamento", "Pasto"])
    if st.button("REGISTRA"):
        testo = ", ".join(mansioni)
        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🛠️ {testo}", "OSS", firma), True); st.rerun()
    mostra_report("OSS")

st.divider()
st.subheader("📋 DIARIO CLINICO INTEGRALE")
mostra_report()
