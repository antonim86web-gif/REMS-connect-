import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib

# --- 1. CONFIGURAZIONE E DESIGN ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide", page_icon="🏥", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #ffffff; }
    .main-title { text-align: center; background: linear-gradient(90deg, #1e40af, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; font-size: 2.5rem; margin-bottom: 25px; }
    .section-header { background-color: #1e40af; color: #ffffff; padding: 12px; border-radius: 8px; text-align: center; font-weight: 700; margin-bottom: 20px; font-size: 1.2rem; }
    .report-box { padding: 10px; border-radius: 6px; margin-bottom: 5px; border: 1px solid #e2e8f0; font-size: 0.85rem; }
    .report-psichiatra { background-color: #e0f2fe; border-left: 5px solid #3b82f6; }
    .report-infermiere { background-color: #f0fdf4; border-left: 5px solid #22c55e; }
    .report-oss { background-color: #fffbeb; border-left: 5px solid #f59e0b; }
    .badge { padding: 4px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; color: white !important; display: inline-block; }
    .bg-psichiatra { background: #dc2626; } .bg-infermiere { background: #2563eb; }
    .bg-educatore { background: #059669; } .bg-oss { background: #d97706; }
    .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 5px; border: 1px solid #e2e8f0; }
    .custom-table th { background-color: #1e293b; color: #ffffff !important; padding: 10px; font-size: 0.75rem; text-align: left; }
    .custom-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_database_v3.db"
def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (p_id INTEGER, data TEXT, ora TEXT, tipo TEXT, accompagnatore TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()

# --- 3. LOGIN / REGISTRAZIONE ---
if 'user_data' not in st.session_state: st.session_state.user_data = None
if not st.session_state.user_data:
    st.markdown("<h1 class='main-title'>REMS CONNECT LOGIN</h1>", unsafe_allow_html=True)
    tab_l, tab_r = st.tabs(["🔐 Accedi", "📝 Registrati"])
    with tab_l:
        with st.form("login"):
            u, p = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ENTRA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, make_hashes(p)))
                if res: 
                    st.session_state.user_data = {"user": u, "nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Credenziali errate")
    with tab_r:
        with st.form("reg"):
            nu, np = st.text_input("Scegli Username"), st.text_input("Scegli Password", type="password")
            n, c = st.text_input("Tuo Nome"), st.text_input("Tuo Cognome")
            q = st.selectbox("Qualifica Professionale", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                try:
                    db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, make_hashes(np), n, c, q), True)
                    st.success("Registrazione avvenuta! Accedi ora.")
                except: st.error("Username già esistente.")
    st.stop()

# --- 4. NAVIGAZIONE ---
u_info = st.session_state.user_data
firma = f"{u_info['nome']} {u_info['cognome']}"
st.sidebar.markdown(f"👤 **{firma}**\n⭐ *{u_info['ruolo']}*")
if st.sidebar.button("LOGOUT"): st.session_state.user_data = None; st.rerun()
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "📅 Appuntamenti", "⚙️ Gestione"])

# --- 5. LOGICA ---

if menu == "📊 Monitoraggio":
    st.markdown("<h2 class='main-title'>Diario Clinico Unificato</h2>", unsafe_allow_html=True)
    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {n.upper()}", expanded=False):
            log = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if log:
                h = "<table class='custom-table'><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Evento</th></tr>"
                for d, r, o, nt in log:
                    cls = f"bg-{r.lower()}"
                    h += f"<tr><td>{d}</td><td><span class='badge {cls}'>{r}</span></td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

elif menu == "👥 Equipe":
    ruolo = u_info['ruolo']
    st.markdown(f"<div class='section-header'>MODULO {ruolo.upper()}</div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_n = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista]); p_id = [p[0] for p in p_lista if p[1] == p_n][0]

        # --- SEZIONE PSICHIATRA ---
        if ruolo == "Psichiatra":
            with st.form("ps_form"):
                c1,c2 = st.columns(2); fa, do = c1.text_input("Farmaco"), c2.text_input("Dose")
                m,p,n = st.columns(3); m1, p1, n1 = m.checkbox("M"), p.checkbox("P"), n.checkbox("N")
                if st.form_submit_button("INSERISCI TERAPIA"):
                    tu = ",".join([s for s, b in zip(["M","P","N"], [m1,p1,n1]) if b])
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, fa, do, tu, firma, date.today().strftime("%d/%m/%Y")), True); st.rerun()
            
            st.markdown("### 📋 Storico Terapie Prescritte")
            res_t = db_run("SELECT farmaco, dosaggio, turni, medico, id_u FROM terapie WHERE p_id=?", (p_id,))
            for f, d, t, m, rid in res_t:
                c1, c2 = st.columns([10, 1])
                c1.markdown(f"<div class='report-box report-psichiatra'>💊 <b>{f}</b> - {d} | Turni: {t} | Firma: {m}</div>", unsafe_allow_html=
