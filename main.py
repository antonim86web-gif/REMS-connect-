import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd
import base64

# --- CONFIGURAZIONE ESTETICA ---
st.set_page_config(page_title="REMS Connect ELITE PRO", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    .main-title { text-align: center; color: #1e3a8a; font-weight: 800; font-size: 2.5rem; margin-bottom: 20px; }
    .report-table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; margin-bottom: 20px; }
    .report-table th { background-color: #334155; color: white !important; padding: 10px; text-align: left; }
    .report-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; }
    .report-table tr:nth-child(even) { background-color: #f8fafc; }
    .badge-ruolo { padding: 3px 8px; border-radius: 5px; font-size: 0.7rem; color: white; font-weight: bold; }
    .ruolo-psichiatra { background: #dc2626; } .ruolo-infermiere { background: #2563eb; }
    .ruolo-educatore { background: #059669; } .ruolo-oss { background: #d97706; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE CORE ---
DB_NAME = "rems_database_v4.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        # Correzione Tabella Terapie (Risolve Screenshot 22487)
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, medico TEXT, data TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- ACCESSO ---
if 'user_data' not in st.session_state: st.session_state.user_data = None

if not st.session_state.user_data:
    st.markdown("<h1 class='main-title'>REMS CONNECT ELITE PRO</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔒 Accesso", "✍️ Registrazione"])
    with t1:
        with st.form("l"):
            u_input, p_input = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_input, hash_pw(p_input)))
                if res:
                    st.session_state.user_data = {"n": res[0][0], "c": res[0][1], "q": res[0][2]}
                    st.rerun()
                else: st.error("Dati errati")
    with t2:
        with st.form("r"):
            nu, np = st.text_input("Username"), st.text_input("Password", type="password")
            nn, nc, nq = st.text_input("Nome"), st.text_input("Cognome"), st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("Registrato!")
    st.stop()

# --- FIRMA AUTOMATICA (Risolve Screenshot 22486) ---
u = st.session_state.user_data
firma_legale = f"{u['n']} {u['c']} ({u['q']})"

menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "⚙️ Gestione"])
if st.sidebar.button("LOGOUT"): st.session_state.user_data = None; st.rerun()

# --- MONITORAGGIO (Grafici e Report) ---
if menu == "📊 Monitoraggio":
    st.markdown("<h2 class='main-title'>Diario Clinico Unificato</h2>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            # Grafico Trend (Sistolica, Diastolica, FC, SpO2)
            p_rows = db_run("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '📊 %' ORDER BY id_u ASC", (pid,))
            if p_rows:
                g_list = []
                for d, nt in p_rows:
                    try:
                        v = {pt.split(":")[0]: float(pt.split(":")[1]) for pt in nt.replace("📊 ","").split(" ") if ":" in pt}
                        g_list.append({"Data": d, "MAX": v["MAX"], "MIN": v["MIN"], "FC": v.get("FC", 0), "SpO2": v.get("SpO2", 0)})
                    except: continue
                if g_list: st.line_chart(pd.DataFrame(g_list).set_index("Data"))

            # Tabella Report Zebrata con Firme
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                h = "<table class='report-table'><tr><th>Data</th><th>Ruolo</th><th>Firma</th><th>Evento</th></tr>"
                for d, r, o, nt in evs:
                    h += f"<tr><td>{d}</td><td><span class='badge-ruolo ruolo-{r.lower()}'>{r}</span></td><td style='font-style:italic'>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

# --- EQUIPE (Azioni Professionali e Report di Settore) ---
elif menu == "👥 Equipe":
    st.markdown(f"<h2 class='main-title'>Modulo Operativo: {u['q']}</h2>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        
        # Report di Settore specifico per ruolo
        if u['q'] == "Psichiatra":
            with st.form("ps"):
                farmaco, dose = st.text_input("Farmaco"), st.text_input("Dosaggio")
                if st.form_submit_button("PRESCRIVI"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, medico, data) VALUES (?,?,?,?,?)", (p_id, farmaco, dose, firma_legale, date.today().strftime("%d/%m/%Y")), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💊 NUOVA TERAPIA: {farmaco} {dose}", u['q'], firma_legale), True)
                    st.rerun()
            st.subheader("📋 Report Terapie Attive")
            terapie = db_run("SELECT farmaco, dosaggio, medico, data FROM terapie WHERE p_id=?", (p_id,))
            if terapie: st.table(pd.DataFrame(terapie, columns=["Farmaco", "Dose", "Prescrittore", "Data"]))

        elif u['q'] == "Infermiere":
            st.subheader("✍️ Inserimento Parametri")
            with st.form("pv"):
                c1,c2,c3,c4 = st.columns(4)
                mx, mn = c1.number_input("MAX", 120), c2.number_input("MIN", 80)
                fc, sp = c3.number_input("FC", 72), c4.number_input("SpO2", 98)
                if st.form_submit_button("REGISTRA PARAMETRI"):
                    txt = f"📊 MAX:{mx} MIN:{mn} FC:{fc} SpO2:{sp}"
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), txt, u['q'], firma_legale), True)
                    st.rerun()
            st.subheader("📋 Report Storico Parametri")
            params = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND nota LIKE '📊 %' ORDER BY id_u DESC", (p_id,))
            if params: st.table(pd.DataFrame(params, columns=["Data", "Valori", "Firma"]))

        else: # Educatore / OSS
            nota = st.text_area("Nota di Servizio")
            if st.button("SALVA NOTA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), nota, u['q'], firma_legale), True)
                st.rerun()
            st.subheader(f"📋 Report Ultime Note {u['q']}")
            notes = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND ruolo=? ORDER BY id_u DESC", (p_id, u['q']))
            if notes: st.table(pd.DataFrame(notes, columns=["Data", "Contenuto", "Firma"]))

# --- GESTIONE ANAGRAFICA ---
elif menu == "⚙️ Gestione":
    st.header("Anagrafica Pazienti")
    with st.form("an"):
        nuovo = st.text_input("Nuovo Paziente")
        if st.form_submit_button("AGGIUNGI"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo.upper(),), True); st.rerun()
    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        c1, c2 = st.columns([4, 1])
        c1.write(f"👤 **{n}**")
        if c2.button("Elimina", key=f"d_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
