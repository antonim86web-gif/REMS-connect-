import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12.5", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }

    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .postit-body { font-size: 1rem; line-height: 1.4; font-weight: 500; }
    
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    .role-admin { background-color: #f1f5f9; border-color: #0f172a; }

    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2rem; font-weight: 900; color: #166534; }
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
        try:
            if query: cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}"); return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

if not db_run("SELECT * FROM utenti WHERE user='admin'"):
    db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("admin"), "Responsabile", "Centro", "Admin"), True)

def render_postits(p_id=None, limit=20, can_delete=False):
    query = "SELECT data, ruolo, op, nota, id_u FROM eventi"
    params = []
    if p_id: query += " WHERE id=?"; params.append(p_id)
    query += " ORDER BY id_u DESC LIMIT ?"
    res = db_run(query, tuple(params + [limit]))
    for d, r, o, nt, uid in res:
        cls = f"role-{r.lower()}"
        col_p, col_d = st.columns([0.92, 0.08])
        col_p.markdown(f'<div class="postit {cls}"><div class="postit-header"><span>👤 {o} ({r})</span><span>📅 {d}</span></div><div class="postit-body">{nt}</div></div>', unsafe_allow_html=True)
        if can_delete:
            if col_d.button("🗑️", key=f"del_ev_{uid}"):
                db_run("DELETE FROM eventi WHERE id_u=?", (uid,), True); st.rerun()

# --- LOGIN / REGISTRAZIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT - LOGIN</h2></div>", unsafe_allow_html=True)
    t_log, t_reg = st.tabs(["🔐 ACCEDI", "📝 REGISTRATI"])
    with t_log:
        with st.form("l"):
            u_i, p_i = st.text_input("User"), st.text_input("Password", type="password")
            if st.form_submit_button("ENTRA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
                if res: st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}; st.rerun()
    with t_reg:
        with st.form("r"):
            nu, np = st.text_input("Username scelto"), st.text_input("Password scelta", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRAMI"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("OK! Ora accedi."); st.rerun()
    st.stop()

# --- APP ---
u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
menu = ["📊 Monitoraggio", "👥 Modulo Equipe"]
if u['ruolo'] == "Admin": menu.append("⚙️ Pannello Admin")
else: menu.append("⚙️ Sistema")
nav = st.sidebar.radio("NAVIGAZIONE", menu)
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()

# --- FUNZIONE LOGICA EQUIPE (PER RIUSO ADMIN) ---
def logica_equipe(p_id, ruolo_operativo, firma_operativa):
    if ruolo_operativo == "Psichiatra":
        t1, t2 = st.tabs(["💊 PRESCRIZIONE", "🚫 GESTIONE TURNI"])
        with t1:
            with st.form("p_ps"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("M"), c2.checkbox("P"), c3.checkbox("N")
                if st.form_submit_button("SALVA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma_operativa), True); st.rerun()
        with t2:
            att = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            for tid, fr, ds, mv, pv, nv in att:
                cf, cm, cp, cn, cd = st.columns([3,1,1,1,1])
                cf.write(f"**{fr}**"); nm, np, nn = cm.checkbox("M", value=bool(mv), key=f"m{tid}"), cp.checkbox("P", value=bool(pv), key=f"p{tid}"), cn.checkbox("N", value=bool(nv), key=f"n{tid}")
                if nm != mv or np != pv or nn != nv: db_run("UPDATE terapie SET mat=?, pom=?, nott=? WHERE id_u=?", (int(nm), int(np), int(nn), tid), True); st.rerun()
                if cd.button("🗑️", key=f"dt{tid}"): db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True); st.rerun()

    elif ruolo_operativo == "Infermiere":
        ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
        c1,c2,c3 = st.columns(3)
        for t in ter:
            if t[3]: 
                if c1.button(f"☀️ MAT: {t[1]}", key=f"i{t[0]}m"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM MAT: {t[1]}", "Infermiere", firma_operativa), True); st.rerun()
            if t[4]:
                if c2.button(f"🌤️ POM: {t[1]}", key=f"i{t[0]}p"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM POM: {t[1]}", "Infermiere", firma_operativa), True); st.rerun()
            if t[5]:
                if c3.button(f"🌙 NOT: {t[1]}", key=f"i{t[0]}n"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM NOT: {t[1]}", "Infermiere", firma_operativa), True); st.rerun()

    elif ruolo_operativo == "Educatore":
        mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
        saldo = sum(m[0] if m[1] == "ENTRATA" else -m[0] for m in mov)
        st.markdown(f"<div class='cassa-card'>Saldo: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
        with st.form("cs_e"):
            tp = st.selectbox("Tipo", ["ENTRATA", "USCITA"]); im = st.number_input("€"); cau = st.text_input("Causale")
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), cau, im, tp, firma_operativa), True); st.rerun()

    elif ruolo_operativo == "OSS":
        with st.form("oss_m"):
            m1, m2 = st.checkbox("Pulizia Camera"), st.checkbox("Controllo Fumo")
            if st.form_submit_button("SALVA ATTIVITÀ"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "🧹 Attività registrate", "OSS", firma_operativa), True); st.rerun()

# --- NAVIGAZIONE ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"📁 CARTELLA: {nome}"): render_postits(pid)

elif nav == "⚙️ Pannello Admin":
    st.markdown("<div class='section-banner'><h2>SUPER-ADMIN CONTROL</h2></div>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["👥 GESTIONE UTENTI", "📑 EQUIPE TOTALE", "🗑️ PULIZIA LOG"])
    
    with t1:
        st.subheader("Lista Utenti")
        utenti = db_run("SELECT user, nome, cognome, qualifica FROM utenti")
        for user, nome, cognome, ruolo in utenti:
            c1, c2, c3, c4 = st.columns([2,2,2,1])
            c1.write(f"**{user}**")
            c2.write(f"{nome} {cognome}")
            c3.write(f"*{ruolo}*")
            if user != 'admin':
                if c4.button("Elimina", key=f"u_{user}"):
                    db_run("DELETE FROM utenti WHERE user=?", (user,), True); st.rerun()
            else: c4.write("Sistema")
    
    with t2:
        st.subheader("Simulazione Ruoli Equipe")
        ruolo_sim = st.selectbox("Seleziona Ruolo da simulare", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_lista:
            p_sel_admin = st.selectbox("Seleziona Paziente per simulazione", [p[1] for p in p_lista], key="adm_psel")
            p_id_admin = [p[0] for p in p_lista if p[1] == p_sel_admin][0]
            st.divider()
            logica_equipe(p_id_admin, ruolo_sim, f"ADMIN as {ruolo_sim}")

    with t3:
        st.subheader("Gestione Post-it")
        render_postits(limit=100, can_delete=True)

elif nav == "👥 Modulo Equipe":
    st.markdown(f"<div class='section-banner'><h2>AREA {u['ruolo'].upper()}</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        logica_equipe(p_id, u['ruolo'], firma)

elif nav == "⚙️ Sistema":
    st.markdown("<div class='section-banner'><h2>GESTIONE PAZIENTI</h2></div>", unsafe_allow_html=True)
    with st.form("p_add"):
        np = st.text_input("Nome Nuovo Paziente")
        if st.form_submit_button("AGGIUNGI"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
