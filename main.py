import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib

# --- CONFIGURAZIONE ELITE PRO v13.0 ---
st.set_page_config(page_title="REMS Connect ELITE", layout="wide", page_icon="🏥")

# CSS Ottimizzato per Mobile (per evitare scritte NULL e disallineamenti)
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0f172a !important; }
    .main { background-color: #f8fafc; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .therapy-row { 
        background: white; padding: 15px; border-radius: 10px; 
        margin-bottom: 10px; border-left: 5px solid #1e3a8a;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .paziente-header { color: #1e3a8a; font-size: 1.1rem; font-weight: 800; margin-bottom: 5px; }
    .farmaco-txt { font-size: 1rem; color: #334155; }
</style>
""", unsafe_allow_html=True)

DB_NAME = "rems_professional.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (id_t INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, stato TEXT DEFAULT 'ATTIVO')")
        try:
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- LOGIN ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.title("🏥 REMS Connect Login")
    with st.form("login_mobile"):
        u_in = st.text_input("Username")
        p_in = st.text_input("Password", type="password")
        if st.form_submit_button("ACCEDI"):
            res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
            if res:
                st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                st.rerun()
            else: st.error("Credenziali errate")
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR ---
st.sidebar.title("REMS Connect")
nav = st.sidebar.radio("Menu", ["Somministrazione", "Diario Clinico", "Configurazione"])
if st.sidebar.button("Logout"): st.session_state.user_session = None; st.rerun()

# --- 1. SOMMINISTRAZIONE TERAPIA (TABELLA DINAMICA MOBILE) ---
if nav == "Somministrazione":
    st.subheader("💊 Somministrazione Turno")
    turno = st.radio("Seleziona Turno:", ["MAT", "POM", "NOTT"], horizontal=True)
    
    label_db = turno.lower() if turno != "NOTT" else "nott"
    query = f"SELECT p.nome, t.farmaco, t.dose, t.id_t, t.p_id FROM terapie t JOIN pazienti p ON t.p_id = p.id WHERE t.{label_db} = 1 AND t.stato='ATTIVO'"
    terapie = db_run(query)

    if terapie:
        for nome_p, farmaco, dose, tid, pid in terapie:
            st.markdown(f"""
            <div class="therapy-row">
                <div class="paziente-header">{nome_p}</div>
                <div class="farmaco-txt"><b>{farmaco}</b> — {dose}</div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button("✅ FIRMA", key=f"ok_{tid}"):
                db_run("INSERT INTO eventi (p_id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                       (pid, datetime.now().strftime("%d/%m %H:%M"), f"SOMM: {farmaco} ({turno})", u['ruolo'], firma), True)
                st.success(f"Fatto: {farmaco}")
            
            if c2.button("❌ RIFIUTO", key=f"no_{tid}"):
                st.session_state[f"rif_{tid}"] = True
            
            if st.session_state.get(f"rif_{tid}"):
                motivo = st.text_input("Motivo rifiuto:", key=f"mot_{tid}")
                if st.button("Conferma Rifiuto", key=f"btn_rif_{tid}"):
                    db_run("INSERT INTO eventi (p_id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                           (pid, datetime.now().strftime("%d/%m %H:%M"), f"RIFIUTO: {farmaco} ({turno}) - {motivo}", u['ruolo'], firma), True)
                    st.session_state[f"rif_{tid}"] = False
                    st.rerun()
    else:
        st.info("Nessuna terapia per questo turno.")

# --- 2. DIARIO CLINICO ---
elif nav == "Diario Clinico":
    st.subheader("📝 Diario Multidisciplinare")
    pax = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if pax:
        nomi = [p[1] for p in pax]
        sel_p = st.selectbox("Paziente", nomi)
        pid = [p[0] for p in pax if p[1] == sel_p][0]
        
        with st.form("diario_form"):
            testo = st.text_area("Nota clinica")
            # RISOLTO: Qui c'è il pulsante che mancava nello screenshot
            if st.form_submit_button("SALVA NOTA"):
                db_run("INSERT INTO eventi (p_id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                       (pid, datetime.now().strftime("%d/%m/%Y %H:%M"), testo, u['ruolo'], firma), True)
                st.success("Registrato")
        
        st.divider()
        st.write("### Ultime registrazioni")
        cronologia = db_run("SELECT data, op, nota FROM eventi WHERE p_id=? ORDER BY id_u DESC LIMIT 10", (pid,))
        for d, op, nt in cronologia:
            st.write(f"**{d}** - {op}")
            st.info(nt)

# --- 3. CONFIGURAZIONE ---
elif nav == "Configurazione":
    t1, t2 = st.tabs(["Pazienti", "Prescrizione Medico"])
    
    with t1:
        with st.form("nuovo_paz"):
            np = st.text_input("Nome Cognome Paziente")
            if st.form_submit_button("AGGIUNGI PAZIENTE"):
                db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True)
                st.success("Inserito")
    
    with t2:
        if u['ruolo'] == "Psichiatra":
            with st.form("nuova_ter"):
                pax = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
                sel_p = st.selectbox("Paziente", [p[1] for p in pax])
                pid = [p[0] for p in pax if p[1] == sel_p][0]
                f = st.text_input("Farmaco")
                d = st.text_input("Dose")
                c1,c2,c3 = st.columns(3)
                m = c1.checkbox("MAT"); p = c2.checkbox("POM"); n = c3.checkbox("NOTT")
                if st.form_submit_button("PRESCRIZIONE"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)",
                           (pid, f, d, int(m), int(p), int(n), firma), True)
                    st.success("Prescritto")
        else:
            st.warning("Funzione riservata ai Medici.")
