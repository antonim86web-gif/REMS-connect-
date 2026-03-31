import sqlite3
import streamlit as st
from datetime import datetime, date, timedelta
import hashlib
import pandas as pd
import base64

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="REMS Connect ELITE", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #ffffff; font-family: 'Inter', sans-serif; }
    .main-title { text-align: center; background: linear-gradient(90deg, #1e40af, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; font-size: 2.5rem; margin-bottom: 20px; }
    .section-header { background-color: #1e40af; color: #ffffff; padding: 12px; border-radius: 8px; text-align: center; font-weight: 700; margin-bottom: 20px; }
    .alert-card { background-color: #fee2e2; border-left: 5px solid #ef4444; padding: 15px; border-radius: 8px; margin-bottom: 20px; color: #991b1b; }
    .report-box { padding: 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #e2e8f0; background-color: #f8fafc; font-size: 0.85rem; }
    .badge { padding: 4px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; color: white !important; display: inline-block; text-transform: uppercase; }
    .bg-psichiatra { background: #dc2626; } .bg-infermiere { background: #2563eb; }
    .bg-educatore { background: #059669; } .bg-oss { background: #d97706; }
    .custom-table { width: 100%; border-collapse: collapse; border: 1px solid #e2e8f0; margin-top: 10px; }
    .custom-table th { background-color: #1e293b; color: white; padding: 10px; font-size: 0.75rem; text-align: left; }
    .custom-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; }
    .btn-export { text-decoration: none; background: #1e40af; color: white !important; padding: 6px 12px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- 2. GESTIONE DATABASE ---
DB_NAME = "rems_elite_v4.db"
def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (p_id INTEGER, data TEXT, ora TEXT, tipo TEXT, det TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS documenti (p_id INTEGER, nome_file TEXT, tipo_file TEXT, dati BLOB, data_caricamento TEXT, op TEXT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()

# --- 3. LOGICA DI ACCESSO ---
if 'user_data' not in st.session_state: st.session_state.user_data = None
if not st.session_state.user_data:
    st.markdown("<h1 class='main-title'>REMS CONNECT ELITE</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Login", "📝 Registrazione Operatore"])
    with t1:
        with st.form("login"):
            u, p = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, make_hashes(p)))
                if res: 
                    st.session_state.user_data = {"u": u, "n": res[0][0], "c": res[0][1], "q": res[0][2]}
                    st.rerun()
                else: st.error("Credenziali non valide")
    with t2:
        with st.form("reg"):
            nu, np = st.text_input("Username"), st.text_input("Password", type="password")
            nn, nc, nq = st.text_input("Nome"), st.text_input("Cognome"), st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, make_hashes(np), nn, nc, nq), True); st.success("Registrato!")
    st.stop()

# --- 4. INTERFACCIA PRINCIPALE ---
user = st.session_state.user_data
firma = f"{user['n']} {user['c']}"
st.sidebar.markdown(f"### 👤 {firma}\n**{user['q']}**")
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "📅 Agenda", "⚙️ Gestione"])
if st.sidebar.button("LOGOUT"): st.session_state.user_data = None; st.rerun()

# Funzione Export CSV
def get_csv_download_link(p_id, nome):
    data = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (p_id,))
    df = pd.DataFrame(data, columns=['Data', 'Ruolo', 'Operatore', 'Evento'])
    csv = df.to_csv(index=False).encode('utf-8-sig')
    b64 = base64.b64encode(csv).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="Diario_{nome}.csv" class="btn-export">📥 Esporta Diario</a>'

# --- 5. MODULI ---

if menu == "📊 Monitoraggio":
    st.markdown("<h2 class='main-title'>Diario Clinico Unificato</h2>", unsafe_allow_html=True)
    
    # Alert Scadenze
    oggi = date.today().strftime("%d/%m/%Y")
    scadenze = db_run("SELECT p.nome, a.tipo, a.ora FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.data = ?", (oggi,))
    if scadenze:
        for p_n, t_a, ora in scadenze:
            st.markdown(f"<div class='alert-card'>🔔 <b>OGGI:</b> {p_n} ha {t_a} alle ore {ora}</div>", unsafe_allow_html=True)

    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            # GRAFICO PARAMETRI
            p_data = db_run("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '📊 %' ORDER BY id_u ASC", (pid,))
            if p_data:
                try:
                    g_rows = []
                    for d, nt in p_data:
                        parts = nt.replace("📊 ","").split(" ")
                        mx = float(parts[0].split(":")[1])
                        mn = float(parts[1].split(":")[1])
                        fc = float(parts[2].split(":")[1])
                        sp = float(parts[3].split(":")[1])
                        g_rows.append({"Data": d, "Sistolica": mx, "Diastolica": mn, "FC": fc, "SpO2": sp})
                    st.write("📈 **Trend Parametri Vitali**")
                    st.line_chart(pd.DataFrame(g_rows).set_index("Data"))
                except: pass

            eventi = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if eventi:
                html = "<table class='custom-table'><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Nota</th></tr>"
                for d, r, o, nt in eventi:
                    c = f"bg-{r.lower()}"
                    html += f"<tr><td>{d}</td><td><span class='badge {c}'>{r}</span></td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(html + "</table>", unsafe_allow_html=True)

elif menu == "👥 Equipe":
    p_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_list:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_list])
        p_id = [p[0] for p in p_list if p[1] == p_sel][0]
        t_op, t_doc = st.tabs(["🛠️ Operatività", "📂 Cartella Documenti"])

        with t_op:
            if user['q'] == "Psichiatra":
                with st.form("f_ps"):
                    c1,c2 = st.columns(2); f, d = c1.text_input("Farmaco"), c2.text_input("Dosaggio")
                    if st.form_submit_button("PRESCRIVI"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, medico, data_prescr) VALUES (?,?,?,?,?)", (p_id, f, d, firma, oggi), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🔄 NUOVA TERAPIA: {f} {d}", "Psichiatra", firma), True)
                        st.rerun()
                st.subheader("Terapie in Corso")
                for fa, do, rid in db_run("SELECT farmaco, dosaggio, id_u FROM terapie WHERE p_id=?", (p_id,)):
                    c1, c2 = st.columns([10,1]); c1.info(f"💊 {fa} - {do}"); 
                    if c2.button("🗑️", key=f"t_{rid}"): db_run("DELETE FROM terapie WHERE id_u=?", (rid,), True); st.rerun()

            elif user['q'] == "Infermiere":
                it1, it2 = st.tabs(["Somministrazione", "Parametri"])
                with it1:
                    for fa, do, rid in db_run("SELECT farmaco, dosaggio, id_u FROM terapie WHERE p_id=?", (p_id,)):
                        if st.button(f"Conferma {fa}", key=f"s_{rid}"):
                            db_run("INSERT INTO eventi (id,data,nota,ruolo,op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💊 Somministrato: {fa}", "Infermiere", firma), True); st.rerun()
                with it2:
                    with st.form("f_pv"):
                        c1,c2,c3,c4 = st.columns(4)
                        mx = c1.number_input("Sistolica (Max)", value=120); mn = c2.number_input("Diastolica (Min)", value=80)
                        fc = c3.number_input("FC (Battiti)", value=70); sp = c4.number_input("SpO2 %", value=98)
                        if st.form_submit_button("REGISTRA PARAMETRI"):
                            val = f"📊 MAX:{mx} MIN:{mn} FC:{fc} SpO2:{sp}"
                            db_run("INSERT INTO eventi (id,data,nota,ruolo,op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), val, "Infermiere", firma), True); st.rerun()

            elif user['q'] in ["OSS", "Educatore"]:
                nota = st.text_area("Inserisci nota di servizio")
                if st.button("SALVA NOTA"):
                    db_run("INSERT INTO eventi (id,data,nota,ruolo,op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), nota, user['q'], firma), True); st.rerun()

        with t_doc:
            up = st.file_uploader("Carica referti/documenti")
            if up and st.button("SALVA IN CARTELLA"):
                db_run("INSERT INTO documenti (p_id, nome_file, dati, data_caricamento, op) VALUES (?,?,?,?,?)", (p_id, up.name, up.read(), oggi, firma), True); st.success("File caricato!")
            for fn, dc, op, dt in db_run("SELECT nome_file, data_caricamento, op, dati FROM documenti WHERE p_id=?", (p_id,)):
                c1, c2 = st.columns([4,1]); c1.write(f"📄 {fn} ({dc})"); c2.download_button("Download", dt, file_name=fn)

elif menu == "📅 Agenda":
    st.subheader("Agenda Appuntamenti")
    p_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_list:
        p_sel = st.selectbox("Paziente", [p[1] for p in p_list]); p_id = [p[0] for p in p_list if p[1] == p_sel][0]
        with st.form("f_app"):
            d, h = st.date_input("Data"), st.time_input("Ora")
            t, dt = st.selectbox("Tipo", ["Udienza", "Visita", "Permesso"]), st.text_input("Dettagli")
            if st.form_submit_button("AGGIUNGI"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, tipo, det) VALUES (?,?,?,?,?)", (p_id, d.strftime("%d/%m/%Y"), h.strftime("%H:%M"), t, dt), True); st.rerun()

elif menu == "⚙️ Gestione":
    st.markdown("<h2 class='main-title'>Anagrafica ed Export Legale</h2>", unsafe_allow_html=True)
    with st.form("nuovo_p"):
        np = st.text_input("Nome e Cognome Paziente")
        if st.form_submit_button("AGGIUNGI PAZIENTE"):
            if np: db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    
    st.markdown("---")
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.markdown(f"👤 **{nome}**")
        c2.markdown(get_csv_download_link(pid, nome), unsafe_allow_html=True)
        if c3.button("Elimina", key=f"del_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
