import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v12.5 (FIXED) ---
st.set_page_config(page_title="REMS Connect ELITE PRO", layout="wide", page_icon="🏥")

# --- ENGINE DATABASE ---
DB_NAME = "rems_enterprise_v12.db"

def db_init():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, data_ingresso TEXT, stato TEXT DEFAULT 'ATTIVO')")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, categoria TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (id_t INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, stato TEXT DEFAULT 'ATTIVO')")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (id_c INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (id_a INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, categoria TEXT, evento TEXT)")
        conn.commit()

def db_query(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

db_init()
def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = None

if not st.session_state.auth:
    st.title("🏥 REMS Connect v12.5")
    tab_l, tab_r = st.tabs(["Login", "Registrazione"])
    with tab_l:
        with st.form("login_form"):
            u_in, p_in = st.text_input("User"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_query("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res:
                    st.session_state.auth = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
    with tab_r:
        with st.form("reg_form"):
            nu, np = st.text_input("Nuovo User"), st.text_input("Password", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_query("INSERT INTO utenti (user, pwd, nome, cognome, qualifica) VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True)
                st.success("Staff registrato!")
    st.stop()

u = st.session_state.auth
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR ---
st.sidebar.title("Rems-connect")
st.sidebar.info(f"Utente: {u['nome']} {u['cognome']}\nRuolo: {u['ruolo']}")
nav = st.sidebar.radio("Menu", ["📊 Monitoraggio", "💊 Terapie", "📝 Diario", "💰 Cassa", "📅 Agenda", "⚙️ Sistema"])
if st.sidebar.button("LOGOUT"): st.session_state.auth = None; st.rerun()

# --- 1. MONITORAGGIO ---
if nav == "📊 Monitoraggio":
    st.header("Monitoraggio Reparto")
    pax = db_query("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
    if not pax: st.warning("Nessun paziente in archivio. Vai in 'Sistema' per aggiungerne uno.")
    for pid, nome in pax:
        with st.expander(f"Cartella: {nome}"):
            evs = db_query("SELECT data, op, nota FROM eventi WHERE p_id=? ORDER BY id_u DESC", (pid,))
            if evs: st.table(pd.DataFrame(evs, columns=["Data", "Operatore", "Nota"]))

# --- 2. TERAPIE ---
elif nav == "💊 Terapie":
    st.header("Gestione Terapie")
    pax_l = db_query("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
    
    if not pax_l:
        st.error("Inserire almeno un paziente nel modulo 'Sistema' prima di operare.")
    else:
        if u['ruolo'] == "Psichiatra":
            t1, t2 = st.tabs(["Gestione Attive", "Nuova Prescrizione"])
            with t1:
                attive = db_query("SELECT t.id_t, p.nome, t.farmaco, t.dose FROM terapie t JOIN pazienti p ON t.p_id = p.id WHERE t.stato='ATTIVO'")
                for tid, p_n, f, d in attive:
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"**{p_n}**: {f} ({d})")
                    if c2.button("Elimina", key=f"del_{tid}"):
                        db_query("UPDATE terapie SET stato='SOSPESO' WHERE id_t=?", (tid,), True)
                        st.rerun()
            with t2:
                with st.form("nuova_presc"):
                    sel_p = st.selectbox("Paziente", [p[1] for p in pax_l])
                    pid = [p[0] for p in pax_l if p[1] == sel_p][0]
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3); m=c1.checkbox("MAT"); p=c2.checkbox("POM"); n=c3.checkbox("NOT")
                    if st.form_submit_button("REGISTRA PRESCRIZIONE"):
                        db_query("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (pid, f, d, int(m), int(p), int(n), firma), True)
                        st.success("Salvato!"); st.rerun()
        
        elif u['ruolo'] == "Infermiere":
            turno = st.radio("Turno", ["MAT", "POM", "NOTT"], horizontal=True)
            t_col = turno.lower() if turno != "NOTT" else "nott"
            data_t = db_query(f"SELECT p.nome, t.farmaco, t.dose, t.id_t, t.p_id FROM terapie t JOIN pazienti p ON t.p_id = p.id WHERE t.{t_col}=1 AND t.stato='ATTIVO'")
            for n, f, d, tid, pid in data_t:
                st.info(f"{n}: {f} ({d})")
                if st.button("Firma Somministrazione", key=f"f_{tid}"):
                    db_query("INSERT INTO eventi (p_id, data, nota, ruolo, op, categoria) VALUES (?,?,?,?,?,?)", (pid, datetime.now().strftime("%d/%m %H:%M"), f"SOMM: {f} ({turno})", u['ruolo'], firma, "Terapia"), True)
                    st.success("Firma registrata"); st.rerun()

# --- 6. SISTEMA (AGGIUNGI PAZIENTE PER RISOLVERE IL DROPDOWN VUOTO) ---
elif nav == "⚙️ Sistema":
    st.header("Anagrafica")
    with st.form("add_pax"):
        nuovo_p = st.text_input("Nome Cognome Paziente")
        if st.form_submit_button("REGISTRA INGRESSO"):
            db_query("INSERT INTO pazienti (nome, data_ingresso) VALUES (?,?)", (nuovo_p.upper(), date.today().strftime("%d/%m/%Y")), True)
            st.success("Paziente aggiunto!")
