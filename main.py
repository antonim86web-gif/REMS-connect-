import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO (REPRISTINATA) ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12.5", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .stButton > button[kind="secondary"] { background-color: #dc2626 !important; color: white !important; border: none !important; width: 100%; font-weight: bold !important; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }

    /* --- STILE POST-IT --- */
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .postit-body { font-size: 1rem; line-height: 1.4; font-weight: 500; }
    
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    .role-admin { background-color: #f1f5f9; border-color: #0f172a; }

    .therapy-container { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px; margin-bottom: 15px; border-left: 8px solid #1e3a8a; }
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

# Init Admin
if not db_run("SELECT * FROM utenti WHERE user='admin'"):
    db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("admin"), "Responsabile", "Centro", "Admin"), True)

def render_postits(p_id=None, limit=20):
    query = "SELECT data, ruolo, op, nota FROM eventi"
    params = []
    if p_id:
        query += " WHERE id=?"; params.append(p_id)
    query += " ORDER BY id_u DESC LIMIT ?"
    res = db_run(query, tuple(params + [limit]))
    for d, r, o, nt in res:
        r_l = r.lower()
        cls = f"role-{r_l}"
        st.markdown(f'''
            <div class="postit {cls}">
                <div class="postit-header"><span>👤 {o} ({r})</span><span>📅 {d}</span></div>
                <div class="postit-body">{nt}</div>
            </div>
        ''', unsafe_allow_html=True)

# --- LOGIN ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
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
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
menu = ["📊 Monitoraggio", "👥 Modulo Equipe"]
if u['ruolo'] == "Admin": menu.append("⚙️ Pannello Admin")
else: menu.append("⚙️ Sistema")
nav = st.sidebar.radio("MODULI OPERATIVI", menu)
if st.sidebar.button("LOGOUT SICURO"): st.session_state.user_session = None; st.rerun()

# --- NAVIGAZIONE ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>MONITORAGGIO GENERALE</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"📁 CARTELLA CLINICA: {nome}"): render_postits(pid)

elif nav == "⚙️ Pannello Admin":
    st.markdown("<div class='section-banner'><h2>AMMINISTRAZIONE</h2></div>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["👤 UTENTI", "🏥 PAZIENTI", "🌍 LOG GLOBALE"])
    with t1:
        with st.form("adm_u"):
            nu, np = st.text_input("User"), st.text_input("Pass", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Ruolo", ["Admin", "Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("CREA UTENTE"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("OK")
    with t2:
        with st.form("adm_p"):
            n_p = st.text_input("Nome Paziente")
            if st.form_submit_button("AGGIUNGI"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (n_p.upper(),), True); st.rerun()
    with t3: render_postits(limit=50)

elif nav == "👥 Modulo Equipe":
    st.markdown(f"<div class='section-banner'><h2>AREA {u['ruolo'].upper()}</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        if u['ruolo'] == "Psichiatra":
            t1, t2 = st.tabs(["💊 NUOVA TERAPIA", "🚫 GESTIONE TURNI"])
            with t1:
                with st.form("p_f"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                    if st.form_submit_button("PRESCRIVI"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True); st.rerun()
            with t2:
                att = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                for tid, fr, ds, mv, pv, nv in att:
                    c_f, c_m, c_p, c_n, c_d = st.columns([3, 1, 1, 1, 1])
                    c_f.write(f"**{fr}** ({ds})")
                    nm = c_m.checkbox("MAT", value=bool(mv), key=f"m{tid}")
                    np = c_p.checkbox("POM", value=bool(pv), key=f"p{tid}")
                    nn = c_n.checkbox("NOT", value=bool(nv), key=f"n{tid}")
                    if nm != mv or np != pv or nn != nv:
                        db_run("UPDATE terapie SET mat=?, pom=?, nott=? WHERE id_u=?", (int(nm), int(np), int(nn), tid), True); st.rerun()
                    if c_d.button("🗑️", key=f"d{tid}"): db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True); st.rerun()

        elif u['ruolo'] == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 SOMMINISTRAZIONE", "📝 CONSEGNE", "📊 PARAMETRI"])
            with t1:
                ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                c1,c2,c3 = st.columns(3)
                def card_s(tid, farm, dos, turn, icon, col):
                    if col.button(f"{icon} {turn}: {farm}", key=f"b_{tid}_{turn}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM {turn}: {farm}", "Infermiere", firma), True); st.rerun()
                for t in ter:
                    if t[3]: card_s(t[0], t[1], t[2], "MAT", "☀️", c1)
                    if t[4]: card_s(t[0], t[1], t[2], "POM", "🌤️", c2)
                    if t[5]: card_s(t[0], t[1], t[2], "NOT", "🌙", c3)
            with t2:
                with st.form("i_c"):
                    nota = st.text_area("Consegna"); 
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota, "Infermiere", firma), True); st.rerun()
            with t3:
                with st.form("i_p"):
                    pa, fc, sat = st.text_input("PA"), st.text_input("FC"), st.text_input("Sat%")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📊 PV - PA: {pa}, FC: {fc}, Sat: {sat}%", "Infermiere", firma), True); st.rerun()

        elif u['ruolo'] == "Educatore":
            t1, t2 = st.tabs(["📝 CONSEGNE", "💰 CASSA"])
            with t2:
                mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum(m[0] if m[1] == "ENTRATA" else -m[0] for m in mov)
                st.markdown(f"<div class='cassa-card'>Saldo attuale: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
                with st.form("e_c"):
                    tp = st.selectbox("Tipo", ["ENTRATA", "USCITA"]); im = st.number_input("€"); cau = st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), cau, im, tp, firma), True); st.rerun()

        elif u['ruolo'] == "OSS":
            t1, t2 = st.tabs(["🧹 MANSIONI", "📝 NOTE"])
            with t1:
                with st.form("o_m"):
                    m1, m2 = st.checkbox("Pulizia"), st.checkbox("Fumo")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "🧹 Attività registrate", "OSS", firma), True); st.rerun()

elif nav == "⚙️ Sistema":
    st.markdown("<div class='section-banner'><h2>GESTIONE SISTEMA</h2></div>", unsafe_allow_html=True)
    with st.form("s_p"):
        np = st.text_input("Nome Paziente")
        if st.form_submit_button("AGGIUNGI"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
