import sqlite3
import streamlit as st
from datetime import datetime
import hashlib
import pandas as pd

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect v12.8", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: center; }
    .postit { padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); background-color: #ffffff; color: #1e293b; }
    .role-infermiere { border-color: #2563eb; } 
    .role-educatore { border-color: #059669; }  
    .role-oss { border-color: #64748b; }
    .turno-header { background: #f1f5f9; padding: 8px; border-radius: 5px; border-left: 5px solid #1e3a8a; margin: 15px 0 5px 0; font-weight: bold; color: #1e3a8a; }
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
        try:
            if query: cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore: {e}"); return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def render_postits(p_id=None, filter_role=None):
    query = "SELECT data, ruolo, op, nota, id_u FROM eventi WHERE 1=1"
    params = []
    if p_id: query += " AND id=?"; params.append(p_id)
    if filter_role: query += " AND ruolo=?"; params.append(filter_role)
    query += " ORDER BY id_u DESC LIMIT 50"
    res = db_run(query, tuple(params))
    for d, r, o, nt, uid in res:
        st.markdown(f'<div class="postit role-{r.lower()}"><b>{o} ({r})</b> - {d}<br>{nt}</div>', unsafe_allow_html=True)

# --- ACCESSO ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>ACCESSO REMS</h2></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["ACCEDI", "REGISTRATI"])
    with t1:
        with st.form("l"):
            u_i, p_i = st.text_input("User"), st.text_input("Password", type="password")
            if st.form_submit_button("ENTRA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
                if res: st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}; st.rerun()
    with t2:
        with st.form("r"):
            nu, np, nn, nc = st.text_input("Username"), st.text_input("Pass", type="password"), st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.rerun()
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- NAVIGAZIONE ---
nav = st.sidebar.radio("MENU", ["📊 Monitoraggio", "👥 Modulo Equipe", "⚙️ Admin"])
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()

if nav == "📊 Monitoraggio":
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"📁 Diario: {nome}"): render_postits(pid)

elif nav == "👥 Modulo Equipe":
    ruolo_corr = u['ruolo']
    if u['ruolo'] == "Admin": ruolo_corr = st.selectbox("Simula:", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Paziente:", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        
        now = datetime.now()
        # Reset 06:00
        data_rif = (now.replace(hour=0, minute=0) - pd.Timedelta(days=1 if now.hour < 6 else 0)).strftime("%d/%m/%Y")
        rif_full = f"{data_rif} 06:00"

        if ruolo_corr == "Infermiere":
            t1, t2 = st.tabs(["💊 TERAPIE", "📝 NOTE"])
            with t1:
                ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                for lab, col in [("MAT", 3), ("POM", 4), ("NOT", 5)]:
                    st.markdown(f"<div class='turno-header'>{lab}</div>", unsafe_allow_html=True)
                    for f in [t for t in ter if t[col] == 1]:
                        # RICERCA SEMPLICE: Se il farmaco e il turno sono nella nota di oggi, sparisce
                        cerca_nota = f"SOMM: {f[1]} ({lab})"
                        check = db_run("SELECT id_u FROM eventi WHERE id=? AND data >= ? AND nota=?", (p_id, rif_full, cerca_nota))
                        
                        if not check:
                            col1, col2 = st.columns([0.8, 0.2])
                            col1.write(f"**{f[1]}** {f[2]}")
                            if col2.button("✅", key=f"btn_{p_id}_{f[0]}_{lab}"):
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                                       (p_id, now.strftime("%d/%m/%Y %H:%M"), cerca_nota, "Infermiere", firma), True)
                                st.rerun()
            with t2:
                with st.form("f_i"):
                    txt = st.text_area("Consegna")
                    if st.form_submit_button("INVIA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), txt, "Infermiere", firma), True); st.rerun()

        elif ruolo_corr == "OSS":
            with st.form("f_o"):
                mans = st.multiselect("Mansioni:", ["Pulizia Stanza", "Sale Fumo", "Refettorio", "Sala Caffè", "Cortile", "Lavatrice"])
                cons = st.text_area("Consegne OSS")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧹 {', '.join(mans)} | {cons}", "OSS", firma), True); st.rerun()

        elif ruolo_corr == "Educatore":
            t1, t2 = st.tabs(["💰 CASSA", "📝 NOTE"])
            with t1:
                mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
                st.metric("Saldo", f"{saldo:.2f} €")
                with st.form("f_e"):
                    tp, im, cau = st.selectbox("Tipo", ["ENTRATA", "USCITA"]), st.number_input("€"), st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), cau, im, tp, firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💰 {tp}: {im}€ - {cau}", "Educatore", firma), True); st.rerun()

        st.divider()
        st.subheader("I Miei Post-it")
        render_postits(p_id, filter_role=ruolo_corr)

elif nav == "⚙️ Admin":
    with st.form("add_p"):
        np = st.text_input("Nome Paziente")
        if st.form_submit_button("AGGIUNGI"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    p_all = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_all:
        c1, c2 = st.columns([0.9, 0.1])
        c1.write(nome)
        if c2.button("❌", key=f"p_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
