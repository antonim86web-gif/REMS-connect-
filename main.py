import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12.5", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* SIDEBAR BLU ISTITUZIONALE */
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    .sidebar-title { 
        color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; 
        text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; 
    }
    
    /* BANNER SEZIONI */
    .section-banner { 
        background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; 
        margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); 
    }
    .section-banner h2 { color: white !important; margin: 0; font-weight: 800; text-transform: uppercase; }

    /* TABELLE */
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; margin-top: 20px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 12px; text-align: left; border: 1px solid #cbd5e1; }
    .report-table td { padding: 10px; border: 1px solid #cbd5e1; color: #1e293b; font-size: 0.9rem; }
    
    /* GRAFICA TERAPIA INFERMIERE */
    .therapy-container {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 15px; margin-bottom: 15px; border-left: 8px solid #1e3a8a;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .turn-header { font-weight: 800; font-size: 0.9rem; text-transform: uppercase; margin-bottom: 10px; }
    .mat-style { color: #d97706; } .pom-style { color: #2563eb; } .not-style { color: #4338ca; }
    .farmaco-title { font-size: 1.2rem; font-weight: 900; color: #1e293b; margin: 0; }
    .dose-subtitle { font-size: 1rem; color: #64748b; font-weight: 600; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- MOTORE DATABASE ---
DB_NAME = "rems_final_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, categoria TEXT, evento TEXT, stato TEXT)")
        try:
            if query: cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore Database: {e}")
            return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- GESTIONE ACCESSO ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>REMS CONNECT LOGIN</h2></div>", unsafe_allow_html=True)
    with st.form("login_form"):
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
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.write(f"👤 **{u['nome']} {u['cognome']}**")
nav = st.sidebar.radio("MENU DI SISTEMA", ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Appuntamenti", "⚙️ Gestione Sistema"])
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()

# --- 1. MONITORAGGIO ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO UNIVERSALE</h2></div>", unsafe_allow_html=True)
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in pazienti:
        with st.expander(f"📁 CARTELLA: {nome}"):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                h = "<table class='report-table'><thead><tr><th>Data</th><th>Qualifica</th><th>Operatore</th><th>Nota</th></tr></thead><tbody>"
                for d, r, o, nt in evs: h += f"<tr><td>{d}</td><td>{r}</td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- 2. MODULO EQUIPE ---
elif nav == "👥 Modulo Equipe":
    st.markdown(f"<div class='section-banner'><h2>OPERATIVO {u['ruolo'].upper()}</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        # PSICHIATRA
        if u['ruolo'] == "Psichiatra":
            t1, t2 = st.tabs(["➕ Prescrizione", "❌ Sospensione"])
            with t1:
                with st.form("form_presc"):
                    f = st.text_input("Farmaco")
                    d = st.text_input("Dosaggio")
                    c1, c2, c3 = st.columns(3)
                    m, p, n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"Prescritto: {f}", "Psichiatra", firma), True); st.rerun()
            with t2:
                attivi = db_run("SELECT id_u, farmaco FROM terapie WHERE p_id=?", (p_id,))
                for fid, fn in attivi:
                    if st.button(f"Sospendi {fn}", key=f"s_{fid}"):
                        db_run("DELETE FROM terapie WHERE id_u=?", (fid,), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"Sospeso: {fn}", "Psichiatra", firma), True); st.rerun()

        # INFERMIERE
        elif u['ruolo'] == "Infermiere":
            st.write("### 💊 Dashboard Somministrazioni")
            oggi = datetime.now().strftime("%d/%m/%Y")
            ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            
            def render_nurse_card(tid, farm, dos, turn, color, icon):
                # Scompare solo se confermato (✔️ SOMM), se rifiutato (⚠️ RIFIUTO) resta visibile
                check_ok = db_run("SELECT id_u FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%✔️ SOMM ({turn}): {farm}%", f"{oggi}%"))
                if not check_ok:
                    st.markdown(f"<div class='therapy-container'><div class='turn-header {color}'>{icon} {turn}</div><div class='farmaco-title'>{farm}</div><div class='dose-subtitle'>{dos}</div></div>", unsafe_allow_html=True)
                    c_ok, c_no = st.columns(2)
                    if c_ok.button("✅ ASSUNTO", key=f"ok_{tid}_{turn}", use_container_width=True):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({turn}): {farm}", "Infermiere", firma), True); st.rerun()
                    if c_no.button("❌ RIFIUTATO", key=f"no_{tid}_{turn}", use_container_width=True):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"⚠️ RIFIUTO ({turn}): {farm}", "Infermiere", firma), True); st.rerun()

            c1, c2, c3 = st.columns(3)
            with c1: 
                st.write("☀️ MAT")
                for t in ter: 
                    if t[3]: render_nurse_card(t[0], t[1], t[2], "MAT", "mat-style", "☀️")
            with c2: 
                st.write("🌤️ POM")
                for t in ter: 
                    if t[4]: render_nurse_card(t[0], t[1], t[2], "POM", "pom-style", "🌤️")
            with c3: 
                st.write("🌙 NOT")
                for t in ter: 
                    if t[5]: render_nurse_card(t[0], t[1], t[2], "NOT", "not-style", "🌙")

# --- ALTRE SEZIONI (Educatore/OSS/Gestione) ---
elif nav == "⚙️ Gestione Sistema":
    st.markdown("<div class='section-banner'><h2>ANAGRAFICA</h2></div>", unsafe_allow_html=True)
    with st.form("new_paz"):
        np = st.text_input("Nuovo Paziente")
        if st.form_submit_button("REGISTRA"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
