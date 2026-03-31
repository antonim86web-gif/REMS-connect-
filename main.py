import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="REMS Connect PRO v23", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* Stile per i blocchi divisi (Accesso e Settori) */
    .access-box { padding: 30px; border-radius: 15px; border: 2px solid #e2e8f0; background-color: #f8fafc; min-height: 450px; }
    .stTabs [data-baseweb="tab"] { font-size: 1.1rem; font-weight: bold; }
    .report-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 10px; text-align: left; }
    .report-table td { padding: 8px; border-bottom: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ---
DB_NAME = "rems_v23_final.db"

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

# --- SCHERMATA DI ACCESSO DIVISA ---
if 'u_data' not in st.session_state: st.session_state.u_data = None

if not st.session_state.u_data:
    st.title("🏥 REMS CONNECT PRO - ACCESSO DIVISO")
    st.write("---")
    
    col_login, col_reg = st.columns(2)
    
    with col_login:
        st.markdown('<div class="access-box">', unsafe_allow_html=True)
        st.subheader("🔐 LOGIN OPERATORE")
        st.write("Inserisci le tue credenziali per accedere al diario.")
        with st.form("form_login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI AL SISTEMA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, hash_pw(p)))
                if res: 
                    st.session_state.u_data = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Credenziali errate")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_reg:
        st.markdown('<div class="access-box">', unsafe_allow_html=True)
        st.subheader("📝 REGISTRAZIONE NUOVO PROFILO")
        st.write("Crea un nuovo account operatore.")
        with st.form("form_reg"):
            nu = st.text_input("Scegli Username")
            np = st.text_input("Scegli Password", type="password")
            nn = st.text_input("Nome")
            nc = st.text_input("Cognome")
            nq = st.selectbox("Qualifica/Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA PROFILO"):
                if nu and np and nn:
                    db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True)
                    st.success("Registrazione completata! Ora puoi accedere.")
                else: st.warning("Compila tutti i campi")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- LOGICA APPLICATIVO ---
usr = st.session_state.u_data
firma = f"{usr['nome']} {usr['cognome']} ({usr['ruolo']})"

# Gestione Pazienti
p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
if not p_lista:
    st.warning("Nessun paziente in archivio.")
    with st.expander("Aggiungi Paziente"):
        np = st.text_input("Nome e Cognome")
        if st.button("Salva"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    st.stop()

# Sidebar
p_sel = st.sidebar.selectbox("PAZIENTE SELEZIONATO", [p[1] for p in p_lista])
p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
st.sidebar.write(f"Operatore: **{firma}**")
if st.sidebar.button("LOGOUT"): st.session_state.u_data = None; st.rerun()

st.title(f"🏥 AREA OPERATIVA: {usr['ruolo'].upper()}")

# --- DASHBOARD A SCHEDE E REPORT ---
t1, t2, t3 = st.tabs(["💊 Operazioni / Terapia", "📊 Parametri e Cassa", "📝 Diario Completo"])

with t1:
    # Azioni specifiche per ruolo
    if usr['ruolo'] == "Psichiatra":
        with st.form("psi_t"):
            st.subheader("Prescrizione Medica")
            f, d = st.text_input("Farmaco"), st.text_input("Dosaggio")
            c1,c2,c3 = st.columns(3); m=c1.number_input("M",0); p=c2.number_input("P",0); n=c3.number_input("N",0)
            if st.form_submit_button("SALVA TERAPIA"):
                db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, m, p, n, firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💊 Prescritto: {f} {d}", "Psichiatra", firma), True); st.rerun()
    
    elif usr['ruolo'] == "Infermiere":
        st.subheader("Somministrazione")
        for tid, fa, do in db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,)):
            ca, cb, cc = st.columns([3,1,1])
            ca.write(f"**{fa}** ({do})")
            if cb.button("✅", key=f"ok_{tid}"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrato: {fa}", "Infermiere", firma), True); st.rerun()
            if cc.button("❌", key=f"no_{tid}"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"❌ Rifiutato: {fa}", "Infermiere", firma), True); st.rerun()

    elif usr['ruolo'] in ["Educatore", "OSS"]:
        st.subheader("Nota di Servizio")
        nota_att = st.text_area("Descrizione attività svolta")
        if st.button("REGISTRA ATTIVITÀ"):
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), nota_att, usr['ruolo'], firma), True); st.rerun()

    st.divider()
    st.markdown("#### 📋 Ultime note di questo settore")
    d_ruolo = db_run("SELECT data, op, nota FROM eventi WHERE id=? AND ruolo=? ORDER BY id_u DESC LIMIT 5", (p_id, usr['ruolo']))
    if d_ruolo: st.table(pd.DataFrame(d_ruolo, columns=["Data", "Firma", "Nota"]))

with t2:
    if usr['ruolo'] == "Infermiere":
        st.subheader("Parametri Vitali")
        with st.form("p_form"):
            c1,c2,c3,c4 = st.columns(4)
            mx = c1.number_input("MAX", value=120); mn = c2.number_input("MIN", value=80)
            fc = c3.number_input("FC", value=70); sp = c4.number_input("SpO2", value=98)
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA:{mx}/{mn} FC:{fc} SpO2:{sp}", "Infermiere", firma), True); st.rerun()

    elif usr['ruolo'] == "Educatore":
        st.subheader("Gestione Cassa")
        movs = db_run("SELECT data, causale, importo, tipo FROM cassa WHERE p_id=?", (p_id,))
        saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
        st.metric("SALDO", f"€ {saldo:.2f}")
        with st.form("c_form"):
            t = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
            i = st.number_input("Euro", value=0.0); c = st.text_input("Causale")
            if st.form_submit_button("SALVA MOVIMENTO"):
                db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m"), c, i, t, firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {t}: €{i:.2f} ({c})", "Educatore", firma), True); st.rerun()
        if movs:
            df_c = pd.DataFrame(movs, columns=["Data", "Causale", "Importo", "Tipo"])
            df_c["Importo"] = df_c["Importo"].map('{:.2f}'.format)
            st.table(df_c)
    else:
        st.info("Accesso limitato a Infermieri ed Educatori per questa sezione.")

with t3:
    st.subheader("📋 DIARIO CLINICO INTEGRALE")
    d_all = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (p_id,))
    if d_all:
        st.table(pd.DataFrame(d_all, columns=["Data", "Ruolo", "Operatore", "Nota"]))
