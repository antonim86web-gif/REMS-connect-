import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="REMS Connect ELITE PRO", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    .main-title { text-align: center; color: #1e3a8a; font-weight: 800; font-size: 2.2rem; margin-bottom: 20px; }
    .report-table { width: 100%; border-collapse: collapse; background: white; margin-bottom: 20px; border: 1px solid #e2e8f0; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 10px; text-align: left; font-size: 0.8rem; }
    .report-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; }
    .badge-ruolo { padding: 3px 8px; border-radius: 5px; font-size: 0.7rem; color: white; font-weight: bold; }
    .ruolo-psichiatra { background: #dc2626; } .ruolo-infermiere { background: #2563eb; }
    .ruolo-educatore { background: #059669; } .ruolo-oss { background: #d97706; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE CORE (Versione v5 per resettare gli errori di tabella) ---
DB_NAME = "rems_final_v5.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        # Tabella terapie definita con tutti i campi per evitare OperationalError
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, medico TEXT, data TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. SISTEMA DI ACCESSO ---
if 'user_data' not in st.session_state: st.session_state.user_data = None

if not st.session_state.user_data:
    st.markdown("<h1 class='main-title'>REMS CONNECT ELITE PRO</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔒 Accesso", "📝 Registrazione"])
    with t1:
        with st.form("login_form"):
            u_in, p_in = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res:
                    # Salvataggio esplicito delle chiavi per evitare KeyError
                    st.session_state.user_data = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Credenziali non valide.")
    with t2:
        with st.form("reg_form"):
            nu, np = st.text_input("Username"), st.text_input("Password", type="password")
            nn, nc, nq = st.text_input("Nome"), st.text_input("Cognome"), st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True)
                st.success("Registrato con successo! Esegui il login.")
    st.stop()

# --- 4. FIRMA E NAVIGAZIONE ---
u = st.session_state.user_data
# Uso dei nomi completi delle chiavi per sicurezza totale
firma_legale = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "⚙️ Gestione"])
if st.sidebar.button("ESCI"): st.session_state.user_data = None; st.rerun()

# --- 5. MODULI ---

if menu == "📊 Monitoraggio":
    st.markdown("<h2 class='main-title'>Diario Clinico Unificato</h2>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}", expanded=True):
            # Grafico Parametri
            p_rows = db_run("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '📊 %' ORDER BY id_u ASC", (pid,))
            if p_rows:
                g_list = []
                for d, nt in p_rows:
                    try:
                        v = {pt.split(":")[0]: float(pt.split(":")[1]) for pt in nt.replace("📊 ","").split(" ") if ":" in pt}
                        g_list.append({"Data": d, "MAX": v.get("MAX", 0), "MIN": v.get("MIN", 0), "FC": v.get("FC", 0), "SpO2": v.get("SpO2", 0)})
                    except: continue
                if g_list: st.line_chart(pd.DataFrame(g_list).set_index("Data"))

            # Tabella Eventi
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                h = "<table class='report-table'><thead><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Evento</th></tr></thead><tbody>"
                for d, r, o, nt in evs:
                    h += f"<tr><td>{d}</td><td><span class='badge-ruolo ruolo-{r.lower()}'>{r}</span></td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

elif menu == "👥 Equipe":
    st.subheader(f"Area Lavoro: {u['ruolo']}")
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        
        if u['ruolo'] == "Psichiatra":
            with st.form("f_ter"):
                f, d = st.text_input("Farmaco"), st.text_input("Dosaggio")
                if st.form_submit_button("PRESCIVI"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, medico, data) VALUES (?,?,?,?,?)", 
                           (p_id, f, d, firma_legale, date.today().strftime("%d/%m/%Y")), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                           (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💊 NUOVA TERAPIA: {f} {d}", u['ruolo'], firma_legale), True)
                    st.rerun()
            st.subheader("📋 Report Terapie Attive")
            terapie = db_run("SELECT farmaco, dosaggio, medico, data FROM terapie WHERE p_id=?", (p_id,))
            if terapie: st.table(pd.DataFrame(terapie, columns=["Farmaco", "Dosaggio", "Medico", "Data"]))

        elif u['ruolo'] == "Infermiere":
            with st.form("f_pv"):
                c1, c2, c3, c4 = st.columns(4)
                mx = c1.number_input("MAX", 120); mn = c2.number_input("MIN", 80)
                fc = c3.number_input("FC", 72); sp = c4.number_input("SpO2", 98)
                if st.form_submit_button("SALVA PARAMETRI"):
                    txt = f"📊 MAX:{mx} MIN:{mn} FC:{fc} SpO2:{sp}"
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                           (p_id, datetime.now().strftime("%d/%m %H:%M"), txt, u['ruolo'], firma_legale), True)
                    st.rerun()

        else: # Educatore / OSS
            nota = st.text_area("Inserisci nota di servizio")
            if st.button("SALVA NOTA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                       (p_id, datetime.now().strftime("%d/%m %H:%M"), nota, u['ruolo'], firma_legale), True)
                st.rerun()

elif menu == "⚙️ Gestione":
    st.subheader("Anagrafica Pazienti")
    with st.form("add_p"):
        np = st.text_input("Nome e Cognome Paziente")
        if st.form_submit_button("SALVA"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        c1, c2 = st.columns([5, 1])
        c1.write(f"👤 {n}")
        if c2.button("Elimina", key=f"del_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
