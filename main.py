import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect ELITE v8", layout="wide", page_icon="🏥")

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

# --- DATABASE (v8 - Pulizia e Coerenza) ---
DB_NAME = "rems_professional_v8.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat TEXT, pom TEXT, nott TEXT, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- LOGIN ---
if 'u_data' not in st.session_state: st.session_state.u_data = None

if not st.session_state.u_data:
    st.title("🏥 REMS CONNECT ELITE PRO")
    t1, t2 = st.tabs(["🔐 Login", "📝 Registrazione Operatore"])
    with t1:
        with st.form("l"):
            u, p = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, hash_pw(p)))
                if res: 
                    st.session_state.u_data = {"n": res[0][0], "c": res[0][1], "q": res[0][2]}
                    st.rerun()
    with t2:
        with st.form("r"):
            nu, np = st.text_input("Nuovo User"), st.text_input("Nuova Pass", type="password")
            nn, nc, nq = st.text_input("Nome"), st.text_input("Cognome"), st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("Registrato!")
    st.stop()

u = st.session_state.u_data
firma = f"{u['n']} {u['c']} ({u['q']})"
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "⚙️ Gestione"])
if st.sidebar.button("LOGOUT"): st.session_state.u_data = None; st.rerun()

# --- MONITORAGGIO ---
if menu == "📊 Monitoraggio":
    st.header("📋 Registro Clinico Unificato")
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                h = "<table class='report-table'><tr><th>Data</th><th>Qualifica</th><th>Firma</th><th>Evento</th></tr>"
                for d, r, o, nt in evs:
                    h += f"<tr><td>{d}</td><td><span class='badge bg-{r.lower()}'>{r}</span></td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

# --- EQUIPE ---
elif menu == "👥 Equipe":
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_n = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_n][0]

        # --- PSICHIATRA ---
        if u['q'] == "Psichiatra":
            st.subheader("💊 Gestione Terapie (Mat/Pom/Notte)")
            with st.form("f_ter"):
                f, d = st.text_input("Farmaco"), st.text_input("Dosaggio")
                c1,c2,c3 = st.columns(3)
                m = c1.text_input("Mattina", "1"); p = c2.text_input("Pomeriggio", "0"); n = c3.text_input("Notte", "1")
                if st.form_submit_button("AGGIUNGI TERAPIA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, m, p, n, firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 Terapia: {f} ({m}-{p}-{n})", u['q'], firma), True)
                    st.rerun()
            st.write("---")
            for tid, fa, do, m1, p1, n1 in db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,)):
                c_a, c_b = st.columns([5,1])
                c_a.info(f"**{fa} {do}** | Orari: {m1}-{p1}-{n1}")
                if c_b.button("ELIMINA", key=f"t_{tid}"):
                    db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🗑️ Terapia Rimossa: {fa}", u['q'], firma), True)
                    st.rerun()

        # --- INFERMIERE ---
        elif u['q'] == "Infermiere":
            tab1, tab2 = st.tabs(["💊 Somministrazione", "📊 Parametri"])
            with tab1:
                st.subheader("Somministrazione Farmaci")
                for fa, do, m1, p1, n1 in db_run("SELECT farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,)):
                    if st.button(f"Fatto: {fa} ({do}) - {m1}-{p1}-{n1}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrato: {fa}", u['q'], firma), True)
                        st.success(f"Registrato: {fa}")
            with tab2:
                with st.form("pv"):
                    c1,c2,c3,c4 = st.columns(4)
                    mx = c1.number_input("MAX", 120); mn = c2.number_input("MIN", 80)
                    fc = c3.number_input("FC", 72); sp = c4.number_input("SpO2", 98)
                    if st.form_submit_button("REGISTRA VITALI"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA:{mx}/{mn} FC:{fc} SpO2:{sp}", u['q'], firma), True)
                        st.rerun()

        # --- EDUCATORE ---
        elif u['q'] == "Educatore":
            tab1, tab2 = st.tabs(["💰 Gestione Cassa", "📝 Diario"])
            with tab1:
                movs = db_run("SELECT data, causale, importo, tipo, op FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
                st.metric("Saldo Economico", f"€ {saldo:.2f}")
                with st.form("cash"):
                    tipo = st.radio("Tipo", ["Entrata", "Uscita"])
                    imp = st.number_input("Importo €", 0.0); cau = st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO cassa VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m"), cau, imp, tipo, firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {tipo}: €{imp} ({cau})", u['q'], firma), True)
                        st.rerun()
            with tab2:
                n_ed = st.text_area("Nota attività"); 
                if st.button("SALVA NOTA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), n_ed, u['q'], firma), True)
                    st.rerun()

        # --- OSS (Mansioni Specifiche) ---
        elif u['q'] == "OSS":
            st.subheader("Registro Mansioni OSS")
            m_scelta = st.selectbox("Seleziona Mansione", ["Pulizia Camera", "Pulizia Refettorio", "Sale Fumo", "Cortile", "Lavatrice"])
            det_oss = st.text_area("Eventuali note aggiuntive")
            if st.button("REGISTRA AZIONE"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🛠️ {m_scelta}: {det_oss}", u['q'], firma), True)
                st.success("Mansione registrata.")
                st.rerun()

# --- GESTIONE ---
elif menu == "⚙️ Gestione":
    st.subheader("Anagrafica Pazienti")
    np = st.text_input("Nuovo Paziente")
    if st.button("SALVA"):
        db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
