import sqlite3
import streamlit as st
from datetime import datetime
import hashlib

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect ENTERPRISE v15.0", layout="wide", page_icon="🏦")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0f172a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; border-bottom: 2px solid #334155; padding-bottom: 10px; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 20px; border-radius: 12px; margin-bottom: 25px; text-align: center; }
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); background-color: #ffffff; color: #1e293b; }
    .role-admin { background-color: #f8fafc; border-color: #0f172a; }
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    .saldo-txt { font-size: 1.8rem; font-weight: 900; color: #166534; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ---
DB_NAME = "rems_enterprise.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        try:
            if query: cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e: return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def render_postits(p_id=None, limit=20):
    query = "SELECT data, ruolo, op, nota FROM eventi"
    params = []
    if p_id:
        query += " WHERE id=?"
        params.append(p_id)
    query += " ORDER BY id_u DESC LIMIT ?"
    params.append(limit)
    res = db_run(query, tuple(params))
    for d, r, o, nt in res:
        cls = f"role-{r.lower()}"
        st.markdown(f'<div class="postit {cls}"><b>{o} ({r})</b> - {d}<br>{nt}</div>', unsafe_allow_html=True)

# --- LOGIN ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    # Creazione primo admin se non esiste
    if not db_run("SELECT * FROM utenti WHERE user='admin'"):
        db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("admin123"), "Super", "User", "Admin"), True)
    
    st.markdown("<div class='section-banner'><h2>REMS CONNECT LOGIN</h2></div>", unsafe_allow_html=True)
    with st.form("login"):
        u_in, p_in = st.text_input("Username"), st.text_input("Password", type="password")
        if st.form_submit_button("ACCEDI"):
            res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
            if res: st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}; st.rerun()
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems Connect</div>", unsafe_allow_html=True)
st.sidebar.write(f"👤 {firma}")
nav = st.sidebar.radio("MENU", ["📊 Monitoraggio", "👥 Modulo Equipe", "⚙️ Pannello Admin" if u['ruolo'] == "Admin" else "⚙️ Sistema"])
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()

# --- NAVIGAZIONE ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"📁 CARTELLA: {nome}"): render_postits(pid)

elif nav == "⚙️ Pannello Admin" and u['ruolo'] == "Admin":
    t_utenti, t_paz, t_global = st.tabs(["👤 UTENTI", "🏥 PAZIENTI", "🌍 LOG GLOBALE"])
    with t_utenti:
        with st.form("new_user"):
            st.write("Registra Nuovo Operatore")
            c1, c2 = st.columns(2)
            nu, np = c1.text_input("Username"), c2.text_input("Password", type="password")
            nn, nc = c1.text_input("Nome"), c2.text_input("Cognome")
            nq = st.selectbox("Qualifica", ["Admin", "Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("Utente creato")
    with t_paz:
        with st.form("new_p"):
            nome_p = st.text_input("Nome Paziente")
            if st.form_submit_button("AGGIUNGI PAZIENTE"):
                db_run("INSERT INTO pazienti (nome) VALUES (?)", (nome_p.upper(),), True); st.rerun()
    with t_global:
        st.write("### Ultime 50 attività nel centro")
        render_postits(limit=50)

elif nav == "👥 Modulo Equipe":
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        # --- PSICHIATRA: SOSPENSIONE GRANULARE ---
        if u['ruolo'] == "Psichiatra":
            t1, t2 = st.tabs(["💊 PRESCRIZIONE", "🚫 GESTIONE ORARI"])
            with t1:
                with st.form("p_f"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True); st.rerun()
            with t2:
                ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                for tid, farm, dos, mat, pom, nott in ter:
                    with st.container():
                        c_f, c_m, c_p, c_n = st.columns([3, 1, 1, 1])
                        c_f.write(f"**{farm}** ({dos})")
                        # Switch per sospendere orari singoli
                        if c_m.checkbox("MAT", value=bool(mat), key=f"m_{tid}") != bool(mat):
                            db_run("UPDATE terapie SET mat=? WHERE id_u=?", (int(not mat), tid), True); st.rerun()
                        if c_p.checkbox("POM", value=bool(pom), key=f"p_{tid}") != bool(pom):
                            db_run("UPDATE terapie SET pom=? WHERE id_u=?", (int(not pom), tid), True); st.rerun()
                        if c_n.checkbox("NOT", value=bool(nott), key=f"n_{tid}") != bool(nott):
                            db_run("UPDATE terapie SET nott=? WHERE id_u=?", (int(not nott), tid), True); st.rerun()
                        st.divider()

        # --- INFERMIERE ---
        elif u['ruolo'] == "Infermiere":
            t1, t2 = st.tabs(["💊 SOMMINISTRAZIONE", "📝 CONSEGNE"])
            with t1:
                ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                c1,c2,c3 = st.columns(3)
                def som_btn(tid, f, turn, icon, col):
                    if col.button(f"{icon} {turn}: {f}", key=f"b_{tid}_{turn}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM {turn}: {f}", "Infermiere", firma), True); st.rerun()
                for t in ter:
                    if t[3]: som_btn(t[0], t[1], "MAT", "☀️", c1)
                    if t[4]: som_btn(t[0], t[1], "POM", "🌤️", c2)
                    if t[5]: som_btn(t[0], t[1], "NOT", "🌙", c3)

        # --- EDUCATORE (CASSA) ---
        elif u['ruolo'] == "Educatore":
            t1, t2 = st.tabs(["📝 NOTE", "💰 CASSA"])
            with t2:
                mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum(m[0] if m[1] == "ENTRATA" else -m[0] for m in mov)
                st.markdown(f"<div class='cassa-card'>SALDO: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
                with st.form("cash"):
                    tipo = st.selectbox("Tipo", ["ENTRATA", "USCITA"]); imp = st.number_input("Euro"); cau = st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), cau, imp, tipo, firma), True); st.rerun()

        # --- OSS (MANSIONI) ---
        elif u['ruolo'] == "OSS":
            with st.form("oss_f"):
                st.write("### Check-list Mansioni")
                m1, m2, m3 = st.checkbox("Pulizia Camera"), st.checkbox("Sala Fumo"), st.checkbox("Sala Caffè")
                m4, m5, m6 = st.checkbox("Refettorio"), st.checkbox("Cortile"), st.checkbox("Lavatrice")
                if st.form_submit_button("SALVA ATTIVITÀ"):
                    sel = [k for k,v in {"Camera":m1, "S.Fumo":m2, "S.Caffè":m3, "Refettorio":m4, "Cortile":m5, "Lavatrice":m6}.items() if v]
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "🧹 "+", ".join(sel), "OSS", firma), True); st.rerun()
