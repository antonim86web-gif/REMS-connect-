import sqlite3
import streamlit as st
from datetime import datetime
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v24.0 ---
st.set_page_config(page_title="REMS Connect ELITE PRO v24.0", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* STILE SIDEBAR */
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    
    /* SCRITTA VERDE FLUO PER OPERATORE */
    .user-logged { color: #00ff00 !important; font-weight: 900; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; text-align: center; }
    
    /* BANNER SUPERIORE */
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 1px solid #ffffff22; }
    
    /* TASTO LOGOUT VERDE */
    .stButton>button[kind="secondary"] { background-color: #22c55e !important; color: white !important; border: none !important; width: 100%; font-weight: 700; }
    
    /* POST-IT */
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    .role-admin { background-color: #f1f5f9; border-color: #1e3a8a; }

    /* APPUNTAMENTI BOX */
    .app-card { background-color: #fffbeb; border: 1px solid #fef3c7; padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 6px solid #d97706; color: #1e293b; }
    
    /* TERAPIA */
    .therapy-container { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px; margin-bottom: 15px; border-left: 8px solid #1e3a8a; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    .turn-header { font-weight: 800; font-size: 0.9rem; text-transform: uppercase; margin-bottom: 10px; }
    .mat-style { color: #d97706; } .pom-style { color: #2563eb; } .not-style { color: #4338ca; }
    
    /* CASSA */
    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2.2rem; font-weight: 900; color: #166534; }
    
    /* FIRMA SIDEBAR */
    .sidebar-footer { color: #ffffff !important; font-size: 0.8rem; margin-top: 50px; border-top: 1px solid #ffffff33; padding-top: 10px; opacity: 0.8; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ENGINE ---
DB_NAME = "rems_final_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT)")
        try:
            if query: cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}"); return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def render_postits(p_id=None, limit=50):
    query = "SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT ?"
    res = db_run(query, (p_id, limit))
    for d, r, o, nt in res:
        cls = f"role-{r.lower()}"
        st.markdown(f'<div class="postit {cls}"><div class="postit-header"><span>👤 {o} ({r})</span><span>📅 {d}</span></div><div>{nt}</div></div>', unsafe_allow_html=True)

# --- LOGIN ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT - ACCESSO PRO</h2></div>", unsafe_allow_html=True)
    with st.form("login_main"):
        u_i, p_i = st.text_input("Username"), st.text_input("Password", type="password")
        if st.form_submit_button("ACCEDI AL SISTEMA"):
            res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
            if res: st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_i}; st.rerun()
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR & NAVIGAZIONE ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-logged'>● {u['nome']} {u['cognome']}</div>", unsafe_allow_html=True)

menu_options = ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Appuntamenti"]
if u['ruolo'] == "Admin":
    menu_options.append("⚙️ Admin")

nav = st.sidebar.radio("NAVIGAZIONE", menu_options)

if st.sidebar.button("CHIUDI SESSIONE (LOGOUT)"): 
    st.session_state.user_session = None; st.rerun()

st.sidebar.markdown(f"<div class='sidebar-footer'>Sviluppato da: AntonioWebMaster<br>Versione: ELITE PRO v24.0<br>Data: {datetime.now().strftime('%Y')}</div>", unsafe_allow_html=True)

# --- MODULI ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO GENERALE</h2></div>", unsafe_allow_html=True)
    
    # Quick View Appuntamenti Oggi
    st.subheader("📅 Scadenze Odierne")
    oggi_db = datetime.now().strftime("%Y-%m-%d")
    apps_today = db_run("SELECT a.ora, p.nome, a.nota FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.data = ? AND a.stato = 'PROGRAMMATO' ORDER BY a.ora", (oggi_db,))
    if apps_today:
        for hr, pn, nt in apps_today:
            st.info(f"⏰ **{hr}** - {pn}: {nt}")
    else: st.write("Nessun appuntamento per oggi.")
    
    st.divider()
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"📁 SCHEDA PAZIENTE: {nome}"): render_postits(pid)

elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO EQUIPE</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        now = datetime.now(); oggi = now.strftime("%d/%m/%Y")

        # Sezioni dinamiche per ruolo
        if u['ruolo'] in ["Psichiatra", "Admin"]:
            st.subheader("⚕️ Area Medica")
            with st.form("f_ps"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                if st.form_submit_button("REGISTRA TERAPIA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma_op), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"➕ Prescritto: {f} {d}", u['ruolo'], firma_op), True); st.rerun()

        if u['ruolo'] in ["Infermiere", "Admin"]:
            st.subheader("💊 Area Infermieristica")
            with st.form("ni"):
                txt = st.text_area("Consegna Clinica / Parametri")
                if st.form_submit_button("SALVA CONSEGNA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), txt, u['ruolo'], firma_op), True); st.rerun()

        if u['ruolo'] in ["OSS", "Admin"]:
            st.subheader("🧹 Area Assistenziale (OSS)")
            with st.form("oss_f"):
                mans = st.multiselect("Mansioni:", ["Igiene", "Cambio Panno", "Letto", "Cortile", "Lavatrice"])
                txt = st.text_area("Note assistenziali")
                if st.form_submit_button("REGISTRA ATTIVITÀ"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧹 {', '.join(mans)} | {txt}", u['ruolo'], firma_op), True); st.rerun()

        st.divider(); render_postits(p_id)

elif nav == "📅 Appuntamenti":
    st.markdown("<div class='section-banner'><h2>GESTIONE APPUNTAMENTI</h2></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["➕ Nuovo Appuntamento", "📋 Visualizza Agenda"])
    
    with t1:
        with st.form("new_app"):
            p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
            p_sel_a = st.selectbox("Paziente", [p[1] for p in p_lista])
            p_id_a = [p[0] for p in p_lista if p[1] == p_sel_a][0]
            d_a = st.date_input("Data Evento")
            h_a = st.time_input("Ora Evento")
            n_a = st.text_input("Descrizione (es. Visita Medica, Uscita, Colloquio)")
            if st.form_submit_button("CONFERMA PROGRAMMAZIONE"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore) VALUES (?,?,?,?,'PROGRAMMATO',?)", (p_id_a, str(d_a), str(h_a)[:5], n_a, firma_op), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id_a, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📅 Programmato: {n_a} per il {d_a}", u['ruolo'], firma_op), True); st.rerun()

    with t2:
        st.subheader("Scadenziario Completo")
        apps = db_run("SELECT a.id_u, a.data, a.ora, p.nome, a.nota, a.autore FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.stato='PROGRAMMATO' ORDER BY a.data, a.ora")
        for aid, adt, ahr, apn, ant, aut in apps:
            st.markdown(f"<div class='app-card'>📅 <b>{adt} alle {ahr}</b> - 👤 <b>{apn}</b><br>{ant}<br><small>Inserito da: {aut}</small></div>", unsafe_allow_html=True)
            if st.button("SEGNA COME SVOLTO", key=f"done_{aid}"):
                db_run("UPDATE appuntamenti SET stato='COMPLETATO' WHERE id_u=?", (aid,), True); st.rerun()

elif nav == "⚙️ Admin":
    st.markdown("<div class='section-banner'><h2>PANNELLO AMMINISTRATIVO</h2></div>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["👥 UTENTI & CREDENZIALI", "👤 GESTIONE PAZIENTI", "🛡️ SICUREZZA LOG"])
    
    with tab1:
        st.subheader("Database Operatori (Password visibili)")
        for u_id, u_pw, u_n, u_c, u_q in db_run("SELECT user, pwd, nome, cognome, qualifica FROM utenti"):
            c_u1, c_u2, c_u3 = st.columns([0.3, 0.5, 0.2])
            c_u1.write(f"**{u_n} {u_c}** ({u_q})")
            c_u2.code(f"USER: {u_id} | PSW: {u_pw}")
            if c_u3.button("ELIMINA", key=f"del_u_{u_id}"):
                if u_id != u['uid']: db_run("DELETE FROM utenti WHERE user=?", (u_id,), True); st.rerun()

    with tab2:
        st.subheader("Anagrafica Pazienti")
        with st.form("new_p"):
            np = st.text_input("Nuovo Paziente")
            if st.form_submit_button("AGGIUNGI"):
                db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
        for pid, pnm in db_run("SELECT id, nome FROM pazienti"):
            ca, cb = st.columns([0.8, 0.2])
            ca.write(pnm)
            if cb.button("🗑️", key=f"dp_{pid}"):
                db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()

    with tab3:
        st.subheader("Cancellazione Puntuale Note")
        for pid, pnm in db_run("SELECT id, nome FROM pazienti"):
            with st.expander(f"Log di {pnm}"):
                voci = db_run("SELECT id_u, data, nota, op FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
                for vid, vdt, vnt, vop in voci:
                    cl1, cl2 = st.columns([0.9, 0.1])
                    cl1.write(f"[{vdt}] {vop}: {vnt}")
                    if cl2.button("❌", key=f"dv_{vid}"):
                        db_run("DELETE FROM eventi WHERE id_u=?", (vid,), True); st.rerun()
