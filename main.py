import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd
import base64

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect ELITE", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    .main-title { text-align: center; color: #1e40af; font-weight: 800; font-size: 2.2rem; margin-bottom: 20px; }
    .section-header { background-color: #1e40af; color: white; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 20px; }
    .report-box { padding: 10px; border-radius: 8px; margin-bottom: 5px; border: 1px solid #e2e8f0; background: #f8fafc; font-size: 0.85rem; }
    .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.7rem; color: white; font-weight: bold; }
    .bg-infermiere { background: #2563eb; } .bg-psichiatra { background: #dc2626; }
    .bg-educatore { background: #059669; } .bg-oss { background: #d97706; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_final_v4.db" # Database pulito per evitare conflitti
def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (p_id INTEGER, data TEXT, ora TEXT, tipo TEXT, det TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS documenti (p_id INTEGER, nome_file TEXT, dati BLOB, data TEXT, op TEXT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. GESTIONE SESSIONE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'u_data' not in st.session_state: st.session_state.u_data = {}

if not st.session_state.logged_in:
    st.markdown("<h1 class='main-title'>REMS CONNECT ELITE</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["Login", "Registrazione"])
    with t1:
        with st.form("l"):
            u, p = st.text_input("User"), st.text_input("Password", type="password")
            if st.form_submit_button("ENTRA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, make_hash(p)))
                if res:
                    st.session_state.u_data = {"n": res[0][0], "c": res[0][1], "q": res[0][2]}
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("Errore login")
    with t2:
        with st.form("r"):
            nu, np = st.text_input("Nuovo User"), st.text_input("Nuova Password", type="password")
            nn, nc, nq = st.text_input("Nome"), st.text_input("Cognome"), st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, make_hash(np), nn, nc, nq), True); st.success("Fatto!")
    st.stop()

# Dati utente corrente
u = st.session_state.u_data
firma = f"{u['n']} {u['c']}"

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("MENU", ["📊 Monitoraggio", "👥 Equipe", "📅 Agenda", "⚙️ Gestione"])
if st.sidebar.button("LOGOUT"): st.session_state.logged_in = False; st.rerun()

# --- 5. LOGICA ---

if menu == "📊 Monitoraggio":
    st.markdown("<h2 class='main-title'>Diario Clinico Unificato</h2>", unsafe_allow_html=True)
    
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            # --- LOGICA GRAFICO ---
            p_rows = db_run("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '📊 %' ORDER BY id_u ASC", (pid,))
            if p_rows:
                g_data = []
                for d, nt in p_rows:
                    try:
                        # Pulizia e parsing sicuro
                        parts = nt.replace("📊 ","").split(" ")
                        valori = {p.split(":")[0]: float(p.split(":")[1]) for p in parts if ":" in p}
                        if all(k in valori for k in ["MAX", "MIN", "FC"]):
                            g_data.append({"Data": d, "Sistolica": valori["MAX"], "Diastolica": valori["MIN"], "FC": valori["FC"], "SpO2": valori.get("SpO2", 0)})
                    except: continue # Salta i dati vecchi o malformati
                
                if g_data:
                    st.write("📈 **Andamento Parametri**")
                    st.line_chart(pd.DataFrame(g_data).set_index("Data"))

            # --- TABELLA DIARIO ---
            eventi = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if eventi:
                df_ev = pd.DataFrame(eventi, columns=["Data", "Ruolo", "Operatore", "Evento"])
                st.table(df_ev)

elif menu == "👥 Equipe":
    st.markdown(f"<div class='section-header'>AREA {u['q'].upper()}</div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_n = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_n][0]
        
        if u['q'] == "Infermiere":
            with st.form("pv"):
                c1,c2,c3,c4 = st.columns(4)
                mx = c1.number_input("MAX", value=120); mn = c2.number_input("MIN", value=80)
                fc = c3.number_input("FC", value=72); sp = c4.number_input("SpO2", value=98)
                if st.form_submit_button("SALVA PARAMETRI"):
                    txt = f"📊 MAX:{mx} MIN:{mn} FC:{fc} SpO2:{sp}"
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), txt, u['q'], firma), True)
                    st.rerun()
        else:
            nota = st.text_area("Nota clinica / Consegna")
            if st.button("SALVA NOTA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), nota, u['q'], firma), True)
                st.rerun()

elif menu == "⚙️ Gestione":
    st.markdown("<h2 class='main-title'>Anagrafica Pazienti</h2>", unsafe_allow_html=True)
    with st.form("ap"):
        np = st.text_input("Nome e Cognome")
        if st.form_submit_button("AGGIUNGI"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    
    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        c1, c2 = st.columns([4, 1])
        c1.write(f"👤 **{n}**")
        if c2.button("Elimina", key=f"d_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
