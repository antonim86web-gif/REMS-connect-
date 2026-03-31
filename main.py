import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12.5", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* SIDEBAR BLU ISTITUZIONALE - TESTI BIANCHI */
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    
    .sidebar-title { 
        color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; 
        text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; 
    }

    /* TASTO LOGOUT ROSSO */
    .stButton > button[kind="secondary"] {
        background-color: #dc2626 !important;
        color: white !important;
        border: none !important;
        width: 100%;
        font-weight: bold !important;
    }

    .sidebar-footer { 
        position: fixed; bottom: 10px; left: 10px; color: #ffffff99 !important; 
        font-size: 0.75rem !important; line-height: 1.2; z-index: 100; 
    }
    
    .section-banner { 
        background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; 
        margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); 
    }

    /* --- STILE POST-IT DIARIO CLINICO --- */
    .postit {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        border-left: 10px solid;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        color: #1e293b;
    }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .postit-body { font-size: 1rem; line-height: 1.4; }
    
    /* COLORI PER RUOLO */
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } /* Rosso */
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } /* Blu */
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  /* Verde */
    .role-oss { background-color: #f8fafc; border-color: #64748b; }        /* Grigio */
    .role-default { background-color: #fffbeb; border-color: #d97706; }    /* Arancio */

    /* TABELLE PROFESSIONALI (Per altre sezioni) */
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; margin-top: 20px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 12px; text-align: left; border: 1px solid #cbd5e1; font-weight: 700; }
    .report-table td { padding: 10px; border: 1px solid #cbd5e1; color: #1e293b; font-size: 0.9rem; }
    
    /* CARD TERAPIA */
    .therapy-container {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 15px; margin-bottom: 15px; border-left: 8px solid #1e3a8a;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
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
            st.error(f"Errore: {e}")
            return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>REMS CONNECT LOGIN</h2></div>", unsafe_allow_html=True)
    with st.form("login_form"):
        u_in, p_in = st.text_input("Username"), st.text_input("Password", type="password")
        if st.form_submit_button("ACCEDI"):
            res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
            if res:
                st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                st.rerun()
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"**Operatore:** {u['nome']} {u['cognome']}")
nav = st.sidebar.radio("MODULI OPERATIVI", ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Appuntamenti", "⚙️ Sistema"])

if st.sidebar.button("LOGOUT SICURO"):
    st.session_state.user_session = None
    st.rerun()

st.sidebar.markdown(f"<div class='sidebar-footer'>REMS CONNECT v12.5<br>Core Architecture: <b>AntonioWebMaster</b></div>", unsafe_allow_html=True)

# --- LOGICA NAVIGAZIONE ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>MONITORAGGIO GENERALE</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"📁 CARTELLA CLINICA: {nome}"):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                for d, r, o, nt in evs:
                    # Assegnazione classe colore in base al ruolo
                    r_low = r.lower()
                    if 'psichiatra' in r_low: cls = "role-psichiatra"
                    elif 'infermiere' in r_low: cls = "role-infermiere"
                    elif 'educatore' in r_low: cls = "role-educatore"
                    elif 'oss' in r_low: cls = "role-oss"
                    else: cls = "role-default"
                    
                    st.markdown(f"""
                    <div class="postit {cls}">
                        <div class="postit-header">
                            <span>👤 {o} ({r})</span>
                            <span>📅 {d}</span>
                        </div>
                        <div class="postit-body">{nt}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Nessun evento registrato per questo paziente.")

elif nav == "👥 Modulo Equipe":
    st.markdown(f"<div class='section-banner'><h2>AREA {u['ruolo'].upper()}</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        if u['ruolo'] == "Infermiere":
            t_somm, t_cons, t_pv = st.tabs(["💊 SOMMINISTRAZIONE", "📝 CONSEGNE", "📊 PARAMETRI"])
            with t_somm:
                st.write("### 🏥 Dashboard Somministrazione")
                oggi = datetime.now().strftime("%d/%m/%Y")
                ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                
                def render_card(tid, farm, dos, turn, css_color, icon):
                    check = db_run("SELECT id_u FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%✔️ SOMM ({turn}): {farm}%", f"{oggi}%"))
                    if not check:
                        st.markdown(f"<div class='therapy-container'><div class='turn-header'>{icon} {turn}</div><div class='farmaco-title'>{farm}</div><div class='dose-subtitle'>{dos}</div></div>", unsafe_allow_html=True)
                        c1, c2 = st.columns(2)
                        if c1.button("✅ ASSUNTO", key=f"ok_{tid}_{turn}"):
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({turn}): {farm}", "Infermiere", firma), True); st.rerun()
                        if c2.button("❌ RIFIUTATO", key=f"no_{tid}_{turn}"):
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"⚠️ RIFIUTO ({turn}): {farm}", "Infermiere", firma), True); st.rerun()

                col1, col2, col3 = st.columns(3)
                with col1: 
                    st.write("☀️ **MAT**")
                    for t in ter: 
                        if t[3]: render_card(t[0], t[1], t[2], "MAT", "mat-style", "☀️")
                with col2: 
                    st.write("🌤️ **POM**")
                    for t in ter: 
                        if t[4]: render_card(t[0], t[1], t[2], "POM", "pom-style", "🌤️")
                with col3: 
                    st.write("🌙 **NOT**")
                    for t in ter: 
                        if t[5]: render_card(t[0], t[1], t[2], "NOT", "not-style", "🌙")

            with t_cons:
                nota_c = st.text_area("Nota Consegna")
                if st.button("SALVA CONSEGNA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota_c, "Infermiere", firma), True); st.rerun()

            with t_pv:
                with st.form("pv_form"):
                    pa = st.text_input("Pressione Arteriosa (es. 120/80)"); fc = st.text_input("Frequenza Cardiaca")
                    if st.form_submit_button("REGISTRA PV"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"Parametri Vitali - PA: {pa}, FC: {fc}", "Infermiere", firma), True); st.rerun()

        elif u['ruolo'] == "Psichiatra":
            with st.form("presc"):
                f = st.text_input("Farmaco"); d = st.text_input("Dose"); c1,c2,c3 = st.columns(3)
                m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                if st.form_submit_button("REGISTRA TERAPIA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True); st.rerun()

elif nav == "⚙️ Sistema":
    st.markdown("<div class='section-banner'><h2>SISTEMA</h2></div>", unsafe_allow_html=True)
    with st.form("paz"):
        np = st.text_input("Nome Nuovo Paziente")
        if st.form_submit_button("AGGIUNGI"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
