import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v12.5 ---
st.set_page_config(page_title="REMS Connect ELITE PRO", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; border-bottom: 2px solid #ffffff33; padding: 10px 0; }
    .sidebar-footer { position: fixed; bottom: 10px; left: 10px; color: #ffffff99 !important; font-size: 0.75rem !important; z-index: 100; }
    
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 20px; border-radius: 12px; margin-bottom: 25px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
    .section-banner h2 { color: white !important; margin: 0; text-transform: uppercase; font-weight: 800; }

    /* TABELLE DI ALTA PRECISIONE */
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; margin-top: 15px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 10px; text-align: left; font-size: 0.85rem; border: 1px solid #cbd5e1; }
    .report-table td { padding: 8px; border-bottom: 1px solid #f1f5f9; color: #1e293b; font-size: 0.85rem; border: 1px solid #cbd5e1; }
    
    /* CARD TERAPIA DINAMICA */
    .therapy-card { 
        background: #fdfdfd; border: 1px solid #cbd5e1; padding: 12px; border-radius: 8px; 
        margin-bottom: 10px; border-left: 6px solid #1e3a8a; transition: 0.3s;
    }
    .therapy-card:hover { border-left-color: #dc2626; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    
    /* BADGE STATO */
    .status-badge { padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; color: white; }
    .bg-prescritto { background-color: #2563eb; }
    .bg-somm { background-color: #16a34a; }
    .bg-rif { background-color: #dc2626; }
</style>
""", unsafe_allow_html=True)

# --- ENGINE DATABASE ---
DB_NAME = "rems_pro_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, stato TEXT DEFAULT 'ATTIVO', id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, categoria TEXT, evento TEXT)")
        try:
            if query: cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore: {e}")
            return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- AUTENTICAZIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>REMS CONNECT ELITE PRO</h2><p>Accesso Riservato Operatori</p></div>", unsafe_allow_html=True)
    with st.form("login"):
        u_in = st.text_input("Username")
        p_in = st.text_input("Password", type="password")
        if st.form_submit_button("ENTRA NEL SISTEMA"):
            res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
            if res:
                st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                st.rerun()
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
nav = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda", "⚙️ Sistema"])
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()
st.sidebar.markdown(f"<div class='sidebar-footer'>Power by: <b>AntonioWebMaster</b></div>", unsafe_allow_html=True)

# --- 1. MONITORAGGIO ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>CRUSCOTTO CLINICO</h2></div>", unsafe_allow_html=True)
    pax = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in pax:
        with st.expander(f"👤 {nome.upper()}"):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 20", (pid,))
            if evs:
                h = "<table class='report-table'><thead><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Nota</th></tr></thead><tbody>"
                for d, r, o, nt in evs: h += f"<tr><td>{d}</td><td>{r}</td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- 2. MODULO EQUIPE ---
elif nav == "👥 Modulo Equipe":
    pax = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if pax:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in pax])
        p_id = [p[0] for p in pax if p[1] == p_sel][0]

        if u['ruolo'] == "Psichiatra":
            t_nuova, t_storico = st.tabs(["📝 Nuova Prescrizione", "📜 Storico Terapie"])
            with t_nuova:
                with st.form("f_p"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3); m=c1.checkbox("MAT"); p=c2.checkbox("POM"); n=c3.checkbox("NOT")
                    if st.form_submit_button("INVIA PRESCRIZIONE"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📝 Prescritto: {f} {d}", "Psichiatra", firma), True); st.rerun()
            with t_storico:
                res_t = db_run("SELECT farmaco, dose, medico, stato FROM terapie WHERE p_id=?", (p_id,))
                if res_t: st.table(res_t)

        elif u['ruolo'] == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 SOMMINISTRAZIONE", "📝 CONSEGNE", "📊 PARAMETRI"])
            with t1:
                st.markdown("### 🗓️ Piano di Somministrazione")
                ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=? AND stato='ATTIVO'", (p_id,))
                col_m, col_p, col_n = st.columns(3)
                
                def render_somm(tid, farm, dos, turno):
                    st.markdown(f"<div class='therapy-card'><b>{farm}</b><br><small>{dos}</small></div>", unsafe_allow_html=True)
                    b1, b2 = st.columns(2)
                    if b1.button("✅", key=f"y{tid}{turno}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({turno}): {farm}", "Infermiere", firma), True); st.rerun()
                    if b2.button("❌", key=f"n{tid}{turno}"):
                        motivo = st.text_input("Motivo rifiuto", key=f"mot_{tid}{turno}")
                        if st.button("Conferma Rifiuto", key=f"btn_rif_{tid}{turno}"):
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"⚠️ RIFIUTO ({turno}): {farm} - Motivo: {motivo}", "Infermiere", firma), True); st.rerun()

                with col_m: st.subheader("☀️ MAT"); [render_somm(t[0], t[1], t[2], "MAT") for t in ter if t[3]]
                with col_p: st.subheader("🌤️ POM"); [render_somm(t[0], t[1], t[2], "POM") for t in ter if t[4]]
                with col_n: st.subheader("🌙 NOT"); [render_somm(t[0], t[1], t[2], "NOT") for t in ter if t[5]]

            with t2:
                nota = st.text_area("Scrivi consegna...")
                if st.button("SALVA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota, "Infermiere", firma), True); st.rerun()
            
            with t3:
                with st.form("pv"):
                    c1,c2,c3 = st.columns(3); mx=c1.number_input("Max"); mn=c2.number_input("Min"); fc=c3.number_input("FC")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📊 PV: {mx}/{mn} - FC: {fc}", "Infermiere", firma), True); st.rerun()

        elif u['ruolo'] == "Educatore":
            t_c, t_d = st.tabs(["💰 CASSA", "📝 DIARIO"])
            with t_c:
                movs = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum([m[0] if m[1] == "Entrata" else -m[0] for m in movs])
                st.metric("DISPONIBILITÀ", f"€ {saldo:.2f}")
                with st.form("c"):
                    tm = st.radio("Tipo", ["Entrata", "Uscita"]); im = st.number_input("Euro"); cm = st.text_input("Causale")
                    if st.form_submit_button("REGISTRA MOVIMENTO"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), cm, im, tm, firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"💰 {tm}: €{im} ({cm})", "Educatore", firma), True); st.rerun()

        elif u['ruolo'] == "OSS":
            with st.form("oss"):
                act = st.selectbox("Attività", ["Igiene Personale", "Pasto", "Sanificazione", "Vigilanza"]); obs = st.text_area("Note")
                if st.form_submit_button("SALVA ATTIVITÀ"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"🛠️ {act}: {obs}", "OSS", firma), True); st.rerun()

# --- 3. AGENDA ---
elif nav == "📅 Agenda":
    with st.form("ag"):
        p_sel = st.selectbox("Paziente", [p[1] for p in db_run("SELECT id, nome FROM pazienti")])
        pid = [p[0] for p in db_run("SELECT id, nome FROM pazienti") if p[1] == p_sel][0]
        c1, c2 = st.columns(2); d_ag = c1.date_input("Data"); o_ag = c2.text_input("Ora"); cat = st.selectbox("Tipo", ["Udienza", "Visita", "Permesso", "Incontro"]); desc = st.text_area("Dettaglio")
        if st.form_submit_button("PIANIFICA"):
            db_run("INSERT INTO agenda (p_id, data, ora, categoria, evento) VALUES (?,?,?,?,?)", (pid, d_ag.strftime("%d/%m/%Y"), o_ag, cat, desc), True); st.rerun()
    st.write("### 📅 Programmazione")
    res_a = db_run("SELECT a.data, a.ora, p.nome, a.categoria, a.evento FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY a.data ASC")
    if res_a: st.table(res_a)

# --- 4. SISTEMA ---
elif nav == "⚙️ Sistema":
    st.markdown("### GESTIONE ANAGRAFICA")
    np = st.text_input("Nome Paziente")
    if st.button("REGISTRA"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    st.write("### Lista Pazienti")
    for pid, nome in db_run("SELECT id, nome FROM pazienti"):
        st.write(f"ID: {pid} - **{nome}**")
