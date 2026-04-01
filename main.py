import sqlite3
import hashlib
import pandas as pd
import streamlit as st
from datetime import datetime

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12.5", layout="wide", page_icon="🏥")

# --- CSS DEFINITIVO PER TASTI ROSSI E LAYOUT ---
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-top: 10px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); font-weight: 800; font-size: 2rem; }

    /* FORZATURA TASTI ROSSI SCRITTA BIANCA */
    div.stButton > button {
        background-color: #dc2626 !important;
        color: white !important;
        border-radius: 10px !important;
        border: 2px solid #b91c1c !important;
        font-weight: 800 !important;
        height: 45px !important;
        width: 100% !important;
        text-transform: uppercase !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    
    div.stButton > button:hover {
        background-color: #b91c1c !important;
        color: white !important;
        border-color: #991b1b !important;
    }

    /* STILE POST-IT */
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    
    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2rem; font-weight: 900; color: #166534; }
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
        except Exception as e: return []

# --- LOGIN SESSION ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'>ACCESSO SISTEMA REMS</div>", unsafe_allow_html=True)
    u_i = st.text_input("User")
    p_i = st.text_input("Password", type="password")
    if st.button("ACCEDI"):
        res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hashlib.sha256(p_i.encode()).hexdigest()))
        if res: st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}; st.rerun()
    st.stop()

# --- BARRA SUPERIORE (TASTI ROSSI IN RIGA) ---
u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

col_f1, col_f2, col_spacer, col_logout = st.columns([0.15, 0.15, 0.45, 0.25])
with col_f1:
    if st.button("⬅️ INDIETRO"): pass
with col_f2:
    if st.button("AVANTI ➡️"): pass
with col_logout:
    if st.button("LOGOUT 🚪"):
        st.session_state.user_session = None
        st.rerun()

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
menu = ["📊 Monitoraggio", "👥 Modulo Equipe"]
if u['ruolo'] == "Admin": menu.append("⚙️ Pannello Admin")
else: menu.append("⚙️ Sistema")
nav = st.sidebar.radio("NAVIGAZIONE", menu)

# --- FUNZIONI RENDER ---
def render_postits(p_id=None, limit=50, can_delete=False):
    res = db_run("SELECT data, ruolo, op, nota, id_u FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT ?", (p_id, limit))
    if not res: st.info("Nessuna attività registrata."); return
    for d, r, o, nt, uid in res:
        col_p, col_d = st.columns([0.92, 0.08])
        col_p.markdown(f'<div class="postit role-{r.lower()}"><div class="postit-header"><span>👤 {o}</span><span>📅 {d}</span></div><div>{nt}</div></div>', unsafe_allow_html=True)
        if can_delete:
            if col_d.button("🗑️", key=f"del_{uid}"):
                db_run("DELETE FROM eventi WHERE id_u=?", (uid,), True); st.rerun()

# --- NAVIGAZIONE ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'>DIARIO CLINICO</div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"📁 CARTELLA: {nome}"): render_postits(pid)

elif nav == "⚙️ Pannello Admin":
    st.markdown("<div class='section-banner'>PANNELLO ADMIN</div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["👥 UTENTI", "🗑️ GESTIONE LOG"])
    with t1:
        utenti = db_run("SELECT user, nome, cognome, qualifica FROM utenti")
        for us, no, co, ru in utenti:
            c1, c2, c3, c4 = st.columns([2,2,2,1])
            c1.write(f"**{us}**"); c2.write(f"{no} {co}"); c3.write(ru)
            if us != 'admin' and c4.button("ELIMINA", key=f"u_{us}"):
                db_run("DELETE FROM utenti WHERE user=?", (us,), True); st.rerun()
    with t2:
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_lista:
            p_sel = st.selectbox("Gestisci log di:", [p[1] for p in p_lista])
            pid_log = [p[0] for p in p_lista if p[1] == p_sel][0]
            render_postits(pid_log, can_delete=True)

elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'>EQUIPE OPERATIVA</div>", unsafe_allow_html=True)
    r_op = u['ruolo']
    if u['ruolo'] == "Admin":
        r_op = st.selectbox("Simula Ruolo:", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        pid = [p[0] for p in p_lista if p[1] == p_sel][0]
        adesso = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        if r_op == "Psichiatra":
            f, d = st.text_input("Farmaco"), st.text_input("Dose")
            if st.button("PRESCRIVI"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, adesso, f"➕ Prescrizione: {f} {d}", "Psichiatra", firma), True); st.rerun()
        
        elif r_op == "Infermiere":
            txt = st.text_area("Consegne/Parametri")
            if st.button("REGISTRA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, adesso, txt, "Infermiere", firma), True); st.rerun()
        
        elif r_op == "OSS":
            man = st.multiselect("Mansioni:", ["Stanza", "Fumo", "Refettorio", "Cortile", "Caffè", "Lavatrice"])
            if st.button("SALVA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, adesso, f"🧹 {', '.join(man)}", "OSS", firma), True); st.rerun()

        elif r_op == "Educatore":
            tp = st.selectbox("Cassa", ["ENTRATA", "USCITA"])
            im = st.number_input("€", min_value=0.0)
            if st.button("REGISTRA MOVIMENTO"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, adesso, f"💰 {tp}: {im}€", "Educatore", firma), True); st.rerun()

elif nav == "⚙️ Sistema":
    st.markdown("<div class='section-banner'>ANAGRAFICA</div>", unsafe_allow_html=True)
    nome_p = st.text_input("Nuovo Paziente")
    if st.button("AGGIUNGI"):
        db_run("INSERT INTO pazienti (nome) VALUES (?)", (nome_p.upper(),), True); st.rerun()
