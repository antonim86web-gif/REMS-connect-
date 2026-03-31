import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12.5", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .sidebar-footer { position: fixed; bottom: 10px; left: 10px; color: #ffffff99 !important; font-size: 0.75rem !important; line-height: 1.2; z-index: 100; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
    .section-banner h2 { color: white !important; margin: 0; font-weight: 800; text-transform: uppercase; }
    .section-banner p { margin: 8px 0 0 0; opacity: 0.9; font-size: 1.1rem; font-style: italic; }
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] .stRadio label { color: #ffffff !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] button { background-color: #dc2626 !important; color: white !important; font-weight: 800 !important; border: 2px solid #ffffff !important; border-radius: 10px !important; width: 100% !important; margin-top: 20px; }
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 12px; text-align: left; }
    .report-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; color: #1e293b; font-size: 0.9rem; }
    .therapy-card { background: #f1f5f9; padding: 10px; border-radius: 8px; border-left: 4px solid #1e3a8a; margin-bottom: 10px; }
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
        except Exception as e:
            st.error(f"Errore DB: {e}")
            return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- LOGICA ACCESSO ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>REMS CONNECT ELITE PRO</h2><p>Accesso Operatori</p></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Login", "📝 Registrazione"])
    with t1:
        with st.form("login"):
            u_in, p_in = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res: st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}; st.rerun()
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# SIDEBAR
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"### 👤 {u['nome']} {u['cognome']}")
nav = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio Generale", "👥 Modulo Equipe", "📅 Agenda Appuntamenti", "⚙️ Gestione Sistema"])
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()
st.sidebar.markdown(f"<div class='sidebar-footer'>v12.5.0 ELITE PRO<br>Created by: <b>AntonioWebMaster</b></div>", unsafe_allow_html=True)

# --- 1. MONITORAGGIO ---
if nav == "📊 Monitoraggio Generale":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO INTEGRATO</h2><p>Storico completo eventi pazienti</p></div>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"📁 CARTELLA: {nome.upper()}"):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                h = "<table class='report-table'><thead><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Evento</th></tr></thead><tbody>"
                for d, r, o, nt in evs: h += f"<tr><td>{d}</td><td>{r}</td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- 2. MODULO EQUIPE ---
elif nav == "👥 Modulo Equipe":
    st.markdown(f"<div class='section-banner'><h2>AREA OPERATIVA: {u['ruolo'].upper()}</h2><p>Gestione attività di reparto</p></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        if u['ruolo'] == "Psichiatra":
            with st.form("psic"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1,c2,c3 = st.columns(3); m=c1.checkbox("MATTINA"); p=c2.checkbox("POMERIGGIO"); n=c3.checkbox("NOTTE")
                if st.form_submit_button("PRESCRIVI"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📝 Prescritta terapia: {f} {d}", "Psichiatra", firma), True); st.rerun()

        elif u['ruolo'] == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 SOMMINISTRAZIONE", "📝 CONSEGNE", "📊 PARAMETRI"])
            with t1:
                st.write("### 📋 Piano Terapeutico Diviso per Turni")
                col_m, col_p, col_n = st.columns(3)
                
                terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                
                def render_card(tid, fa, do, turno_label):
                    st.markdown(f"<div class='therapy-card'><b>{fa}</b><br><small>{do}</small></div>", unsafe_allow_html=True)
                    c_ok, c_no = st.columns(2)
                    if c_ok.button("✅ SOMM.", key=f"ok_{tid}_{turno_label}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMMINISTRATO ({turno_label}): {fa}", "Infermiere", firma), True); st.rerun()
                    if c_no.button("❌ RIFIUTO", key=f"no_{tid}_{turno_label}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"⚠️ RIFIUTATA ({turno_label}): {fa}", "Infermiere", firma), True); st.rerun()

                with col_m:
                    st.subheader("☀️ MATTINA")
                    for tid, fa, do, m, p, n in terapie:
                        if m: render_card(tid, fa, do, "Mattina")
                with col_p:
                    st.subheader("🌤️ POMERIGGIO")
                    for tid, fa, do, m, p, n in terapie:
                        if p: render_card(tid, fa, do, "Pomeriggio")
                with col_n:
                    st.subheader("🌙 NOTTE")
                    for tid, fa, do, m, p, n in terapie:
                        if n: render_card(tid, fa, do, "Notte")

            with t2:
                nota = st.text_area("Nota Consegne")
                if st.button("SALVA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota, "Infermiere", firma), True); st.rerun()
            with t3:
                with st.form("pv"):
                    c1,c2 = st.columns(2); mx=c1.number_input("MAX"); mn=c2.number_input("MIN")
                    if st.form_submit_button("SALVA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📊 PA:{mx}/{mn}", "Infermiere", firma), True); st.rerun()

        elif u['ruolo'] == "Educatore":
            tc, te = st.tabs(["💰 CASSA", "📝 DIARIO"])
            with tc:
                movs = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum([m[0] if m[1] == 'Entrata' else -m[0] for m in movs])
                st.metric("DISPONIBILITÀ", f"€ {saldo:.2f}")
                with st.form("c"):
                    tipo=st.radio("Movimento", ["Entrata", "Uscita"]); imp=st.number_input("Euro"); cau=st.text_input("Causa")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), cau, imp, tipo, firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"💰 {tipo}: €{imp}", "Educatore", firma), True); st.rerun()
            with te:
                nota = st.text_area("Nota Educativa")
                if st.button("SALVA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota, "Educatore", firma), True); st.rerun()

        elif u['ruolo'] == "OSS":
            act = st.selectbox("Attività", ["Igiene", "Pasti", "Sanificazione"])
            if st.button("SALVA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"🛠️ {act}", "OSS", firma), True); st.rerun()

# --- 3. AGENDA ---
elif nav == "📅 Agenda Appuntamenti":
    st.markdown("<div class='section-banner'><h2>AGENDA E SCADENZIARIO</h2><p>Pianificazione udienze e visite</p></div>", unsafe_allow_html=True)
    with st.form("ag"):
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        p_sel = st.selectbox("Paziente", [p[1] for p in p_lista])
        pid = [p[0] for p in p_lista if p[1] == p_sel][0]
        c1, c2, c3 = st.columns(3)
        d_app, o_app, cat = c1.date_input("Data"), c2.text_input("Ora"), st.selectbox("Tipo", ["Uscita", "Visita Medica", "Udienza", "Parenti"])
        desc = st.text_area("Dettagli")
        if st.form_submit_button("INSERISCI"): db_run("INSERT INTO agenda (p_id, data, ora, categoria, evento) VALUES (?,?,?,?,?)", (pid, d_app.strftime("%d/%m/%Y"), o_app, cat, desc), True); st.rerun()
    
    apps = db_run("SELECT a.data, a.ora, a.categoria, p.nome, a.evento FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY a.data ASC")
    if apps:
        h = "<table class='report-table'><thead><tr><th>Data</th><th>Paziente</th><th>Tipo</th><th>Dettagli</th></tr></thead><tbody>"
        for d, o, c, n, e in apps:
            cls = "cat-uscita" if c == "Uscita" else "cat-medica" if c == "Visita Medica" else "cat-udienza" if c == "Udienza" else "cat-parenti"
            h += f"<tr><td>{d} {o}</td><td>{n}</td><td><span class='cat-badge {cls}'>{c}</span></td><td>{e}</td></tr>"
        st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- 4. GESTIONE ---
elif nav == "⚙️ Gestione Sistema":
    st.markdown("<div class='section-banner'><h2>GESTIONE ANAGRAFICA</h2><p>Manutenzione dati</p></div>", unsafe_allow_html=True)
    np = st.text_input("Nuovo Paziente")
    if st.button("AGGIUNGI"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        c1, c2 = st.columns([5,1])
        c1.write(f"👤 {n}")
        if c2.button("🗑️", key=f"del_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
