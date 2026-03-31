import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="REMS Connect PRO v9", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 12px; text-align: left; }
    .report-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; }
    .badge { padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; color: white; font-weight: bold; }
    .bg-psichiatra { background: #dc2626; } .bg-infermiere { background: #2563eb; }
    .bg-educatore { background: #059669; } .bg-oss { background: #d97706; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE (v9) ---
DB_NAME = "rems_v9.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- LOGIN ---
if 'u_data' not in st.session_state: st.session_state.u_data = None

if not st.session_state.u_data:
    st.title("🏥 REMS CONNECT PRO")
    t1, t2 = st.tabs(["🔐 Login", "📝 Registrazione"])
    with t1:
        with st.form("l"):
            u, p = st.text_input("User"), st.text_input("Pass", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, hash_pw(p)))
                if res: 
                    st.session_state.u_data = {"nome": res[0][0], "cognome": res[0][1], "qualifica": res[0][2]}
                    st.rerun()
    with t2:
        with st.form("r"):
            nu, np = st.text_input("Username"), st.text_input("Password", type="password")
            nn, nc, nq = st.text_input("Nome"), st.text_input("Cognome"), st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("Registrato!")
    st.stop()

# Firma corretta (Risolve KeyError)
u = st.session_state.u_data
firma = f"{u['nome']} {u['cognome']} ({u['qualifica']})"

menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "⚙️ Gestione"])
if st.sidebar.button("LOGOUT"): st.session_state.u_data = None; st.rerun()

# --- MONITORAGGIO ---
if menu == "📊 Monitoraggio":
    st.header("📋 Registro Clinico")
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                h = "<table class='report-table'><tr><th>Data</th><th>Ruolo</th><th>Firma</th><th>Evento</th></tr>"
                for d, r, o, nt in evs:
                    h += f"<tr><td>{d}</td><td><span class='badge bg-{r.lower()}'>{r}</span></td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

# --- EQUIPE ---
elif menu == "👥 Equipe":
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_n = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_n][0]

        if u['qualifica'] == "Psichiatra":
            st.subheader("💊 Nuova Prescrizione")
            with st.form("f_ter"):
                f = st.text_input("Farmaco")
                d = st.text_input("Dosaggio")
                st.write("Fasce Orarie:")
                c1, c2, c3 = st.columns(3)
                m_check = c1.checkbox("Mattina")
                p_check = c2.checkbox("Pomeriggio")
                n_check = c3.checkbox("Notte")
                if st.form_submit_button("AGGIUNGI TERAPIA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", 
                           (p_id, f, d, int(m_check), int(p_check), int(n_check), firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                           (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 Terapia: {f} {d}", u['qualifica'], firma), True)
                    st.rerun()

        elif u['qualifica'] == "Infermiere":
            st.subheader("💊 Somministrazione")
            t_attive = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            for tid, fa, do, m, p, n in t_attive:
                orari = []
                if m: orari.append("MAT")
                if p: orari.append("POM")
                if n: orari.append("NOTTE")
                if st.button(f"Somministra: {fa} ({do}) - {', '.join(orari)}", key=f"s_{tid}"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrato: {fa}", u['qualifica'], firma), True)
                    st.success(f"{fa} registrato.")

        elif u['qualifica'] == "OSS":
            st.subheader("Registro Mansioni")
            m_scelta = st.selectbox("Mansione", ["Pulizia Camera", "Pulizia Refettorio", "Sale Fumo", "Cortile", "Lavatrice"])
            if st.button("REGISTRA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🛠️ {m_scelta}", u['qualifica'], firma), True)
                st.rerun()

# --- GESTIONE ---
elif menu == "⚙️ Gestione":
    st.header("Anagrafica e Modifiche")
    
    # AGGIUNGI
    with st.expander("➕ Aggiungi Nuovo Paziente"):
        np = st.text_input("Nome")
        if st.button("SALVA NUOVO"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True)
            st.rerun()

    st.write("---")
    
    # MODIFICA / ELIMINA
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, n in pazienti:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            nuovo_nome = col1.text_input(f"Nome", value=n, key=f"input_{pid}")
            if col2.button("💾 Modifica", key=f"mod_{pid}"):
                db_run("UPDATE pazienti SET nome=? WHERE id=?", (nuovo_nome.upper(), pid), True)
                st.rerun()
            if col3.button("🗑️ Elimina", key=f"del_{pid}"):
                db_run("DELETE FROM pazienti WHERE id=?", (pid,), True)
                db_run("DELETE FROM eventi WHERE id=?", (pid,), True) # Pulisce anche la cronologia
                st.rerun()
