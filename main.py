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
    .sidebar-footer { position: fixed; bottom: 10px; left: 10px; color: #ffffff99 !important; font-size: 0.75rem !important; line-height: 1.2; z-index: 100; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }

    /* --- STILE POST-IT --- */
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .postit-body { font-size: 1rem; line-height: 1.4; font-weight: 500; }
    
    /* COLORI PER RUOLO */
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }        
    .role-default { background-color: #fffbeb; border-color: #d97706; }    

    /* CARD CASSA */
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
            st.error(f"Errore: {e}")
            return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def render_postits(p_id, filtro_ruolo=None, filtro_nota=None):
    query = "SELECT data, ruolo, op, nota FROM eventi WHERE id=?"
    params = [p_id]
    if filtro_ruolo:
        query += " AND ruolo=?"
        params.append(filtro_ruolo)
    if filtro_nota:
        query += " AND nota LIKE ?"
        params.append(f"%{filtro_nota}%")
    query += " ORDER BY id_u DESC LIMIT 15"
    res = db_run(query, tuple(params))
    for d, r, o, nt in res:
        r_l = r.lower()
        if 'psichiatra' in r_l: cls = "role-psichiatra"
        elif 'infermiere' in r_l: cls = "role-infermiere"
        elif 'educatore' in r_l: cls = "role-educatore"
        elif 'oss' in r_l: cls = "role-oss"
        else: cls = "role-default"
        st.markdown(f'<div class="postit {cls}"><div class="postit-header"><span>👤 {o} ({r})</span><span>📅 {d}</span></div><div class="postit-body">{nt}</div></div>', unsafe_allow_html=True)

# --- SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>REMS CONNECT LOGIN</h2></div>", unsafe_allow_html=True)
    with st.form("login"):
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
nav = st.sidebar.radio("MODULI OPERATIVI", ["📊 Monitoraggio", "👥 Modulo Equipe", "⚙️ Sistema"])
if st.sidebar.button("LOGOUT SICURO"):
    st.session_state.user_session = None; st.rerun()
st.sidebar.markdown(f"<div class='sidebar-footer'>REMS CONNECT v12.5<br>Core Architecture: <b>AntonioWebMaster</b></div>", unsafe_allow_html=True)

# --- LOGICA NAVIGAZIONE ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>MONITORAGGIO GENERALE</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"📁 CARTELLA CLINICA: {nome}"):
            render_postits(pid)

elif nav == "👥 Modulo Equipe":
    st.markdown(f"<div class='section-banner'><h2>AREA {u['ruolo'].upper()}</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        # --- SEZIONE EDUCATORE ---
        if u['ruolo'] == "Educatore":
            t_cons_ed, t_cassa = st.tabs(["📝 CONSEGNE EDUCATIVE", "💰 GESTIONE CASSA"])
            
            with t_cons_ed:
                with st.form("ed_c"):
                    nota_ed = st.text_area("Consegne del giorno / Note educative")
                    if st.form_submit_button("SALVA CONSEGNA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota_ed, "Educatore", firma), True); st.rerun()
                st.write("---"); render_postits(p_id, "Educatore")

            with t_cassa:
                # Calcolo Saldo
                movimenti = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum(m[0] if m[1] == "ENTRATA" else -m[0] for m in movimenti)
                
                st.markdown(f"<div class='cassa-card'>Saldo Attuale<br><span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
                
                with st.form("cassa_form"):
                    col1, col2 = st.columns(2)
                    tipo = col1.selectbox("Tipo Movimento", ["ENTRATA", "USCITA"])
                    importo = col2.number_input("Importo (€)", min_value=0.0, step=0.50)
                    causale = st.text_input("Causale (es. Ricarica, Spesa, Sigarette)")
                    if st.form_submit_button("REGISTRA MOVIMENTO"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), causale, importo, tipo, firma), True)
                        # Log nel diario clinico
                        log_cassa = f"💰 {tipo}: {importo:.2f}€ - Causale: {causale}"
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), log_cassa, "Educatore", firma), True)
                        st.rerun()
                
                st.write("#### 📑 Ultimi Movimenti")
                movs = db_run("SELECT data, causale, importo, tipo, op FROM cassa WHERE p_id=? ORDER BY id_u DESC LIMIT 10", (p_id,))
                if movs:
                    for d, c, i, t, o in movs:
                        color = "#166534" if t == "ENTRATA" else "#991b1b"
                        st.markdown(f"**{d}** - <span style='color:{color}'>{t} {i:.2f}€</span> | {c} ({o})", unsafe_allow_html=True)

        # --- SEZIONE INFERMIERE ---
        elif u['ruolo'] == "Infermiere":
            t_somm, t_cons, t_pv = st.tabs(["💊 TERAPIA", "📝 CONSEGNE", "📊 PARAMETRI"])
            with t_somm:
                ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                c1,c2,c3 = st.columns(3); # ... (Logica Somministrazione)
                st.write("---"); render_postits(p_id, filtro_nota="SOMM")
            with t_cons:
                with st.form("in_c"):
                    nota = st.text_area("Consegna Infermieristica")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota, "Infermiere", firma), True); st.rerun()
                render_postits(p_id, "Infermiere")
            with t_pv:
                with st.form("in_pv"):
                    c1,c2,c3 = st.columns(3); pa=c1.text_input("PA"); fc=c2.text_input("FC"); sat=c3.text_input("Sat %")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📊 PV - PA: {pa}, FC: {fc}, Sat: {sat}%", "Infermiere", firma), True); st.rerun()
                render_postits(p_id, filtro_nota="PV")

        # --- SEZIONE OSS ---
        elif u['ruolo'] == "OSS":
            t_mans, t_cons_oss, t_pv_oss = st.tabs(["🧹 MANSIONI", "📝 CONSEGNE OSS", "📊 PARAMETRI"])
            with t_mans:
                with st.form("mans_form"):
                    col_a, col_b = st.columns(2)
                    m1, m2, m3 = col_a.checkbox("Pulizia Camera"), col_a.checkbox("Sala Fumo"), col_a.checkbox("Sala Caffè")
                    m4, m5, m6 = col_b.checkbox("Refettorio"), col_b.checkbox("Cortile"), col_b.checkbox("Lavatrice")
                    if st.form_submit_button("REGISTRA MANSIONI"):
                        sel = [k for k, v in {"Camera":m1, "Sala Fumo":m2, "Sala Caffè":m3, "Refettorio":m4, "Cortile":m5, "Lavatrice":m6}.items() if v]
                        if sel: db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "🧹 ESEGUITE: " + ", ".join(sel), "OSS", firma), True); st.rerun()
                render_postits(p_id, filtro_nota="ESEGUITE")
            with t_cons_oss:
                with st.form("oss_c"):
                    nota_oss = st.text_area("Nota Assistenziale OSS")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota_oss, "OSS", firma), True); st.rerun()
                render_postits(p_id, "OSS")
            with t_pv_oss:
                # ... (Logica PV OSS)
                render_postits(p_id, filtro_nota="PV OSS")

        # --- SEZIONE PSICHIATRA ---
        elif u['ruolo'] == "Psichiatra":
            with st.form("presc"):
                f = st.text_input("Farmaco"); d = st.text_input("Dose"); c1,c2,c3 = st.columns(3)
                m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                if st.form_submit_button("PRESCRIVI"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True); st.rerun()
            render_postits(p_id, "Psichiatra")

elif nav == "⚙️ Sistema":
    with st.form("paz"):
        np = st.text_input("Nome Paziente")
        if st.form_submit_button("AGGIUNGI"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
