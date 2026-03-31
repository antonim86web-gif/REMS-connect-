import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect ELITE v11", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; margin-top: 10px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 10px; text-align: left; font-size: 0.8rem; }
    .report-table td { padding: 8px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; }
    .section-box { padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; background: #f8fafc; margin-bottom: 20px; }
    .badge { padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; color: white; font-weight: bold; }
    .bg-psichiatra { background: #dc2626; } .bg-infermiere { background: #2563eb; }
    .bg-educatore { background: #059669; } .bg-oss { background: #d97706; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE CORE ---
DB_NAME = "rems_v11.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- LOGIN ---
if 'u_data' not in st.session_state: st.session_state.u_data = None

if not st.session_state.u_data:
    st.title("🏥 REMS CONNECT PRO v11")
    t1, t2 = st.tabs(["🔐 Login", "📝 Registrazione"])
    with t1:
        with st.form("l"):
            u, p = st.text_input("User"), st.text_input("Pass", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, hash_pw(p)))
                if res: 
                    st.session_state.u_data = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
    with t2:
        with st.form("r"):
            nu, np = st.text_input("User"), st.text_input("Pass", type="password")
            nn, nc, nq = st.text_input("Nome"), st.text_input("Cognome"), st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("Ok!")
    st.stop()

u = st.session_state.u_data
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio Generale", "👥 Modulo Equipe", "⚙️ Gestione Pazienti"])
if st.sidebar.button("LOGOUT"): st.session_state.u_data = None; st.rerun()

# --- MONITORAGGIO GENERALE ---
if menu == "📊 Monitoraggio Generale":
    st.header("📋 Diario Clinico Integrale")
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                h = "<table class='report-table'><tr><th>Data</th><th>Ruolo</th><th>Firma</th><th>Evento</th></tr>"
                for d, r, o, nt in evs:
                    h += f"<tr><td>{d}</td><td><span class='badge bg-{r.lower()}'>{r}</span></td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

# --- MODULO EQUIPE CON REPORT DEDICATI ---
elif menu == "👥 Modulo Equipe":
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_n = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_n][0]

        # 1. PSICHIATRA
        if u['ruolo'] == "Psichiatra":
            with st.container():
                st.subheader("💊 Prescrizione Terapia")
                with st.form("f_ter"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3)
                    m = c1.checkbox("Mattina")
                    p = c2.checkbox("Pomeriggio")
                    n = c3.checkbox("Notte")
                    if st.form_submit_button("CONFERMA"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 Terapia: {f} {d}", u['ruolo'], firma), True)
                        st.rerun()
                
                st.markdown("#### 📋 Report Terapie Attive")
                t_attive = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                if t_attive:
                    h = "<table class='report-table'><tr><th>Farmaco</th><th>Dose</th><th>M</th><th>P</th><th>N</th><th>Azione</th></tr>"
                    for tid, fa, do, m1, p1, n1 in t_attive:
                        h += f"<tr><td>{fa}</td><td>{do}</td><td>{'X' if m1 else '-'}</td><td>{'X' if p1 else '-'}</td><td>{'X' if n1 else '-'}</td><td>Elimina tramite tasto sotto</td></tr>"
                    st.markdown(h + "</table>", unsafe_allow_html=True)
                    for tid, fa, _, _, _, _ in t_attive:
                        if st.button(f"🗑️ Cancella {fa}", key=f"del_t_{tid}"):
                            db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🗑️ Rimossa: {fa}", u['ruolo'], firma), True)
                            st.rerun()

        # 2. INFERMIERE
        elif u['ruolo'] == "Infermiere":
            t1, t2 = st.tabs(["Somministrazione", "Parametri"])
            with t1:
                st.subheader("💊 Somministrazione Farmaci")
                for fa, do, m, p, n in db_run("SELECT farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,)):
                    if st.button(f"Somministra: {fa} ({do})"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrato: {fa}", u['ruolo'], firma), True)
                        st.success(f"Registrato: {fa}")
                
                st.markdown("#### 📋 Report Ultime Somministrazioni")
                soms = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND nota LIKE '✔️ %' ORDER BY id_u DESC LIMIT 5", (p_id,))
                if soms: st.table(pd.DataFrame(soms, columns=["Data", "Farmaco", "Firma"]))

            with t2:
                with st.form("f_pv"):
                    c1,c2,c3,c4 = st.columns(4)
                    mx = c1.number_input("MAX", 120); mn = c2.number_input("MIN", 80)
                    fc = c3.number_input("FC", 72); sp = c4.number_input("SpO2", 98)
                    if st.form_submit_button("SALVA PARAMETRI"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA:{mx}/{mn} FC:{fc} SpO2:{sp}", u['ruolo'], firma), True)
                        st.rerun()
                
                st.markdown("#### 📋 Report Storico Parametri")
                params = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND nota LIKE '📊 %' ORDER BY id_u DESC LIMIT 10", (p_id,))
                if params: st.table(pd.DataFrame(params, columns=["Data", "Valori", "Firma"]))

        # 3. EDUCATORE
        elif u['ruolo'] == "Educatore":
            t1, t2 = st.tabs(["Cassa", "Diario"])
            with t1:
                movs = db_run("SELECT data, causale, importo, tipo, op FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
                st.metric("Saldo Attuale", f"€ {saldo:.2f}")
                with st.form("c"):
                    tp = st.radio("Tipo", ["Entrata", "Uscita"])
                    im = st.number_input("Euro", 0.0); ca = st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m"), ca, im, tp, firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {tp}: €{im} ({ca})", u['ruolo'], firma), True)
                        st.rerun()
                st.markdown("#### 📋 Report Movimenti Cassa")
                if movs: st.table(pd.DataFrame(movs, columns=["Data", "Causale", "Importo", "Tipo", "Firma"]))

        # 4. OSS
        elif u['ruolo'] == "OSS":
            st.subheader("🛠️ Mansioni e Pulizie")
            m_sc = st.selectbox("Azione", ["Pulizia Camera", "Pulizia Refettorio", "Sale Fumo", "Cortile", "Lavatrice"])
            if st.button("REGISTRA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🛠️ {m_sc}", u['ruolo'], firma), True)
                st.rerun()
            
            st.markdown("#### 📋 Report Mansioni Svolte")
            oss_r = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND ruolo='OSS' ORDER BY id_u DESC LIMIT 10", (p_id,))
            if oss_r: st.table(pd.DataFrame(oss_r, columns=["Data", "Mansione", "Firma"]))

# --- GESTIONE ---
elif menu == "⚙️ Gestione Pazienti":
    st.header("Anagrafica")
    nuovo = st.text_input("Nome Paziente")
    if st.button("SALVA"):
        db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo.upper(),), True); st.rerun()
    
    st.write("---")
    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        c1, c2, c3 = st.columns([3,1,1])
        nn = c1.text_input("Paziente", value=n, key=f"edit_{pid}")
        if c2.button("💾", key=f"s_{pid}"):
            db_run("UPDATE pazienti SET nome=? WHERE id=?", (nn.upper(), pid), True); st.rerun()
        if c3.button("🗑️", key=f"d_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
