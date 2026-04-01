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

def render_postits(p_id, filtro_ruolo=None, filtro_nota=None):
    query = "SELECT data, ruolo, op, nota FROM eventi WHERE id=?"
    params = [p_id]
    if filtro_ruolo: query += " AND ruolo=?"; params.append(filtro_ruolo)
    if filtro_nota: query += " AND nota LIKE ?"; params.append(f"%{filtro_nota}%")
    query += " ORDER BY id_u DESC LIMIT 20"
    res = db_run(query, tuple(params))
    for d, r, o, nt in res:
        r_l = r.lower()
        cls = "role-psichiatra" if 'psichiatra' in r_l else "role-infermiere" if 'infermiere' in r_l else "role-educatore" if 'educatore' in r_l else "role-oss" if 'oss' in r_l else "role-default"
        st.markdown(f'<div class="postit {cls}"><div class="postit-header"><span>👤 {o} ({r})</span><span>📅 {d}</span></div><div class="postit-body">{nt}</div></div>', unsafe_allow_html=True)

# --- SESSIONE ---
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
st.sidebar.markdown(f"**Operatore:** {u['nome']} {u['cognome']}")
nav = st.sidebar.radio("MODULI OPERATIVI", ["📊 Monitoraggio", "👥 Modulo Equipe", "⚙️ Sistema"])
if st.sidebar.button("LOGOUT SICURO"): st.session_state.user_session = None; st.rerun()

# --- NAVIGAZIONE ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>MONITORAGGIO GENERALE</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"📁 CARTELLA CLINICA: {nome}"): render_postits(pid)

elif nav == "👥 Modulo Equipe":
    st.markdown(f"<div class='section-banner'><h2>AREA {u['ruolo'].upper()}</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        # --- PSICHIATRA ---
        if u['ruolo'] == "Psichiatra":
            t1, t2 = st.tabs(["💊 NUOVA TERAPIA", "🚫 GESTIONE E SOSPENSIONE"])
            with t1:
                with st.form("presc"):
                    f = st.text_input("Farmaco"); d = st.text_input("Dose"); c1,c2,c3 = st.columns(3)
                    m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                    if st.form_submit_button("PRESCRIVI"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"💊 NUOVA TERAPIA: {f} {d}", "Psichiatra", firma), True); st.rerun()
            with t2:
                st.write("### 📋 Riepilogo Terapie Attive")
                attive = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                if attive:
                    for tid, farm, dos, m, p, n in attive:
                        with st.container():
                            c_f, c_m, c_p, c_n, c_b = st.columns([3, 1, 1, 1, 2])
                            c_f.write(f"**{farm}** ({dos})")
                            c_m.write("☀️" if m else "-")
                            c_p.write("🌤️" if p else "-")
                            c_n.write("🌙" if n else "-")
                            if c_b.button("🚫 SOSPENDI", key=f"s_{tid}"):
                                db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"🚫 SOSPESO FARMACO: {farm}", "Psichiatra", firma), True); st.rerun()
                            st.divider()
                else: st.info("Nessun farmaco in corso per questo paziente.")

        # --- INFERMIERE ---
        elif u['ruolo'] == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 SOMMINISTRAZIONE", "📝 CONSEGNE", "📊 PARAMETRI"])
            with t1:
                ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                def card_s(tid, farm, dos, turn, icon):
                    check = db_run("SELECT id_u FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%✔️ SOMM ({turn}): {farm}%", f"{datetime.now().strftime('%d/%m/%Y')}%"))
                    if not check:
                        st.markdown(f"<div class='therapy-container'><b>{icon} {turn}</b>: {farm} - {dos}</div>", unsafe_allow_html=True)
                        if st.button(f"ESEGUITO {turn} {farm}", key=f"btn_{tid}_{turn}"):
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({turn}): {farm}", "Infermiere", firma), True); st.rerun()
                c1,c2,c3 = st.columns(3)
                with c1: [card_s(t[0],t[1],t[2],"MAT","☀️") for t in ter if t[3]]
                with c2: [card_s(t[0],t[1],t[2],"POM","🌤️") for t in ter if t[4]]
                with c3: [card_s(t[0],t[1],t[2],"NOT","🌙") for t in ter if t[5]]
                st.write("---"); render_postits(p_id, filtro_nota="SOMM")
            with t2:
                with st.form("in_c"):
                    n = st.text_area("Consegna Infermieristica")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), n, "Infermiere", firma), True); st.rerun()
                render_postits(p_id, "Infermiere")
            with t3:
                with st.form("in_pv"):
                    c1,c2,c3 = st.columns(3); pa=c1.text_input("PA"); fc=c2.text_input("FC"); sat=c3.text_input("Sat%")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📊 PV - PA: {pa}, FC: {fc}, Sat: {sat}%", "Infermiere", firma), True); st.rerun()
                render_postits(p_id, filtro_nota="PV")

        # --- EDUCATORE ---
        elif u['ruolo'] == "Educatore":
            t1, t2 = st.tabs(["📝 CONSEGNE EDUCATIVE", "💰 GESTIONE CASSA"])
            with t1:
                with st.form("ed_c"):
                    n = st.text_area("Consegna del giorno")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), n, "Educatore", firma), True); st.rerun()
                render_postits(p_id, "Educatore")
            with t2:
                mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum(m[0] if m[1] == "ENTRATA" else -m[0] for m in mov)
                st.markdown(f"<div class='cassa-card'>Saldo attuale: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
                with st.form("c_f"):
                    tp = st.selectbox("Tipo", ["ENTRATA", "USCITA"]); imp = st.number_input("€", 0.0); caus = st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), caus, imp, tp, firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"💰 {tp}: {imp:.2f}€ - {caus}", "Educatore", firma), True); st.rerun()

        # --- OSS ---
        elif u['ruolo'] == "OSS":
            t1, t2, t3 = st.tabs(["🧹 MANSIONI", "📝 CONSEGNE OSS", "📊 PARAMETRI"])
            with t1:
                with st.form("m_f"):
                    c1, c2 = st.columns(2)
                    m1=c1.checkbox("Pulizia Camera"); m2=c1.checkbox("Sala Fumo"); m3=c1.checkbox("Sala Caffè")
                    m4=c2.checkbox("Refettorio"); m5=c2.checkbox("Cortile"); m6=c2.checkbox("Lavatrice")
                    if st.form_submit_button("REGISTRA"):
                        sel = [k for k, v in {"Camera":m1, "S. Fumo":m2, "S. Caffè":m3, "Refettorio":m4, "Cortile":m5, "Lavatrice":m6}.items() if v]
                        if sel: db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "🧹 ESEGUITE: "+", ".join(sel), "OSS", firma), True); st.rerun()
            with t2:
                with st.form("o_c"):
                    n = st.text_area("Nota OSS")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), n, "OSS", firma), True); st.rerun()
                render_postits(p_id, "OSS")
            with t3:
                with st.form("o_p"):
                    c1,c2,c3 = st.columns(3); pa=c1.text_input("PA"); fc=c2.text_input("FC"); sat=c3.text_input("Sat%")
                    if st.form_submit_button("SALVA PV"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📊 PV OSS - PA: {pa}, FC: {fc}, Sat: {sat}%", "OSS", firma), True); st.rerun()

elif nav == "⚙️ Sistema":
    st.markdown("<div class='section-banner'><h2>GESTIONE SISTEMA</h2></div>", unsafe_allow_html=True)
    with st.form("add_p"):
        np = st.text_input("Nome Paziente")
        if st.form_submit_button("AGGIUNGI"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
