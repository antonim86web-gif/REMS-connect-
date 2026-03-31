import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12.5", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* SIDEBAR BLU */
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .sidebar-footer { position: fixed; bottom: 10px; left: 10px; color: #ffffff99 !important; font-size: 0.75rem !important; line-height: 1.2; z-index: 100; }
    
    /* BANNER SEZIONE */
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
    .section-banner h2 { color: white !important; margin: 0; font-weight: 800; text-transform: uppercase; }
    .section-banner p { margin: 8px 0 0 0; opacity: 0.9; font-size: 1.1rem; font-style: italic; }

    /* MENU LATERALE BIANCO */
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] .stRadio label { color: #ffffff !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] button { background-color: #dc2626 !important; color: white !important; font-weight: 800 !important; border: 2px solid #ffffff !important; border-radius: 10px !important; width: 100% !important; margin-top: 20px; }
    
    /* TABELLE DI RIEPILOGO */
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; margin-top: 20px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 12px; text-align: left; border: 1px solid #cbd5e1; }
    .report-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; color: #1e293b; font-size: 0.9rem; border: 1px solid #cbd5e1; }
    
    /* MINI CARD SOMMINISTRAZIONE */
    .mini-therapy { 
        background: #f8fafc; padding: 5px 10px; border-radius: 6px; 
        border-left: 3px solid #1e3a8a; margin-bottom: 5px;
        display: flex; justify-content: space-between; align-items: center;
        font-size: 0.85rem;
    }
    
    .cat-badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; color: white; }
    .cat-udienza { background-color: #dc2626; } 
    .cat-medica { background-color: #2563eb; }  
    .cat-uscita { background-color: #059669; }  
    .cat-parenti { background-color: #d97706; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ---
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
        except: return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def mostra_tabella_dati(query, params, titoli):
    res = db_run(query, params)
    if res:
        h = f"<table class='report-table'><thead><tr>"
        for t in titoli: h += f"<th>{t}</th>"
        h += "</tr></thead><tbody>"
        for row in res:
            h += "<tr>"
            for cell in row: h += f"<td>{cell}</td>"
            h += "</tr>"
        st.markdown(h + "</tbody></table>", unsafe_allow_html=True)
    else: st.info("Nessun dato registrato per questa sezione.")

# --- LOGIN ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>REMS CONNECT ELITE PRO</h2><p>Accesso Riservato Staff Sanitario</p></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Login", "📝 Registrazione"])
    with t1:
        with st.form("l"):
            u_in, p_in = st.text_input("User"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res: st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}; st.rerun()
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"### 👤 {u['nome']} {u['cognome']}")
nav = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio Generale", "👥 Modulo Equipe", "📅 Agenda Appuntamenti", "⚙️ Gestione Sistema"])
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()
st.sidebar.markdown(f"<div class='sidebar-footer'>v12.5.0 ELITE PRO<br>Created by: <b>AntonioWebMaster</b></div>", unsafe_allow_html=True)

# --- 1. MONITORAGGIO ---
if nav == "📊 Monitoraggio Generale":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO INTEGRATO</h2><p>Visualizzazione universale eventi clinici</p></div>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"📁 CARTELLA: {nome.upper()}"):
            mostra_tabella_dati("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,), ["Data", "Ruolo", "Operatore", "Evento"])

# --- 2. MODULO EQUIPE ---
elif nav == "👥 Modulo Equipe":
    st.markdown(f"<div class='section-banner'><h2>AREA OPERATIVA: {u['ruolo'].upper()}</h2><p>Gestione clinica e assistenziale in tempo reale</p></div>", unsafe_allow_html=True)
    pax = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if pax:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in pax])
        p_id = [p[0] for p in pax if p[1] == p_sel][0]

        if u['ruolo'] == "Psichiatra":
            with st.form("ps"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1,c2,c3 = st.columns(3); m=c1.checkbox("MAT"); p=c2.checkbox("POM"); n=c3.checkbox("NOT")
                if st.form_submit_button("PRESCRIVI"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📝 Prescritta: {f}", "Psichiatra", firma), True); st.rerun()
            st.write("### 💊 Terapie Attive")
            mostra_tabella_dati("SELECT farmaco, dose, medico FROM terapie WHERE p_id=?", (p_id,), ["Farmaco", "Dose", "Medico"])

        elif u['ruolo'] == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 Somministrazione", "📝 Consegne", "📊 Parametri"])
            with t1:
                st.write("### ⏱️ Piano Rapido per Turno")
                col1, col2, col3 = st.columns(3)
                ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                
                def render_mini_card(tid, fa, do, t):
                    with st.container():
                        c_info, c_actions = st.columns([2, 1])
                        c_info.markdown(f"<small><b>{fa}</b> ({do})</small>", unsafe_allow_html=True)
                        c_ok, c_no = c_actions.columns(2)
                        if c_ok.button("✅", key=f"ok_{tid}_{t}", help="Somministrato"): 
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({t}): {fa}", "Infermiere", firma), True); st.rerun()
                        if c_no.button("❌", key=f"no_{tid}_{t}", help="Rifiutato"): 
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"⚠️ RIFIUTO ({t}): {fa}", "Infermiere", firma), True); st.rerun()

                with col1: st.markdown("☀️ **MAT**"); [render_mini_card(x[0], x[1], x[2], "MAT") for x in ter if x[3]]
                with col2: st.markdown("🌤️ **POM**"); [render_mini_card(x[0], x[1], x[2], "POM") for x in ter if x[4]]
                with col3: st.markdown("🌙 **NOT**"); [render_mini_card(x[0], x[1], x[2], "NOT") for x in ter if x[5]]
                
                st.write("### 📜 Log Operazioni Terapia")
                mostra_tabella_dati("SELECT data, op, nota FROM eventi WHERE id=? AND ruolo='Infermiere' AND (nota LIKE '%SOMM%' OR nota LIKE '%RIFIUTO%') ORDER BY id_u DESC LIMIT 5", (p_id,), ["Data", "Operatore", "Esito"])
            
            with t2:
                with st.form("con"):
                    nt = st.text_area("Nuova Consegna")
                    if st.form_submit_button("SALVA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nt, "Infermiere", firma), True); st.rerun()
                mostra_tabella_dati("SELECT data, op, nota FROM eventi WHERE id=? AND ruolo='Infermiere' AND nota NOT LIKE '%SOMM%' AND nota NOT LIKE '%RIFIUTO%' AND nota NOT LIKE '📊%' ORDER BY id_u DESC", (p_id,), ["Data", "Operatore", "Nota"])
            
            with t3:
                with st.form("pv"):
                    c1,c2,c3 = st.columns(3); mx=c1.number_input("PA MAX"); mn=c2.number_input("PA MIN"); fc=c3.number_input("FC")
                    if st.form_submit_button("SALVA PARAMETRI"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📊 PA:{mx}/{mn} FC:{fc}", "Infermiere", firma), True); st.rerun()
                mostra_tabella_dati("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '📊%' ORDER BY id_u DESC", (p_id,), ["Data", "Parametri"])

        elif u['ruolo'] == "Educatore":
            tc, te = st.tabs(["💰 Cassa", "📝 Diario"])
            with tc:
                saldo = sum([m[0] if m[1] == 'Entrata' else -m[0] for m in db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))])
                st.metric("SALDO ATTUALE", f"€ {saldo:.2f}")
                with st.form("ca"):
                    tipo=st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True); imp=st.number_input("Euro"); cau=st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"): 
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), cau, imp, tipo, firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"💰 {tipo}: €{imp} ({cau})", "Educatore", firma), True); st.rerun()
                mostra_tabella_dati("SELECT data, causale, importo, tipo, op FROM cassa WHERE p_id=? ORDER BY id_u DESC", (p_id,), ["Data", "Causale", "Importo", "Tipo", "Operatore"])
            with te:
                nt_e = st.text_area("Diario Educativo")
                if st.button("SALVA NOTA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nt_e, "Educatore", firma), True); st.rerun()
                mostra_tabella_dati("SELECT data, op, nota FROM eventi WHERE id=? AND ruolo='Educatore' AND nota NOT LIKE '💰%' ORDER BY id_u DESC", (p_id,), ["Data", "Operatore", "Nota"])

        elif u['ruolo'] == "OSS":
            with st.form("oss"):
                m_s = st.selectbox("Attività", ["Igiene", "Pasti", "Sanificazione", "Controllo"]); nt_o = st.text_area("Note")
                if st.form_submit_button("REGISTRA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"🛠️ {m_s}: {nt_o}", "OSS", firma), True); st.rerun()
            mostra_tabella_dati("SELECT data, op, nota FROM eventi WHERE id=? AND ruolo='OSS' ORDER BY id_u DESC", (p_id,), ["Data", "Operatore", "Dettaglio Attività"])

# --- 3. AGENDA ---
elif nav == "📅 Agenda Appuntamenti":
    st.markdown("<div class='section-banner'><h2>AGENDA REMS</h2><p>Pianificazione udienze e visite</p></div>", unsafe_allow_html=True)
    with st.form("ag"):
        p_sel = st.selectbox("Paziente", [p[1] for p in db_run("SELECT id, nome FROM pazienti")])
        pid = [p[0] for p in db_run("SELECT id, nome FROM pazienti") if p[1] == p_sel][0]
        c1, c2, c3 = st.columns(3); d_app, o_app, cat = c1.date_input("Data"), c2.text_input("Ora"), c3.selectbox("Tipo", ["Uscita", "Visita Medica", "Udienza", "Parenti"])
        desc = st.text_area("Dettagli")
        if st.form_submit_button("SALVA"): db_run("INSERT INTO agenda (p_id, data, ora, categoria, evento) VALUES (?,?,?,?,?)", (pid, d_app.strftime("%d/%m/%Y"), o_app, cat, desc), True); st.rerun()
    mostra_tabella_dati("SELECT a.data, a.ora, p.nome, a.categoria, a.evento FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY a.data ASC", (), ["Data", "Ora", "Paziente", "Tipo", "Evento"])

# --- 4. GESTIONE ---
elif nav == "⚙️ Gestione Sistema":
    st.markdown("<div class='section-banner'><h2>GESTIONE ANAGRAFICA</h2><p>Pazienti Attivi</p></div>", unsafe_allow_html=True)
    np = st.text_input("Nome e Cognome Nuovo Paziente")
    if st.button("AGGIUNGI"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    mostra_tabella_dati("SELECT id, nome FROM pazienti ORDER BY nome", (), ["ID", "Nome Paziente"])
