import sqlite3
import streamlit as st
from datetime import datetime, date, timedelta
import hashlib
import pandas as pd
import base64

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect ELITE", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #ffffff; }
    .main-title { text-align: center; background: linear-gradient(90deg, #1e40af, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; font-size: 2.5rem; margin-bottom: 25px; }
    .section-header { background-color: #1e40af; color: #ffffff; padding: 12px; border-radius: 8px; text-align: center; font-weight: 700; margin-bottom: 20px; font-size: 1.2rem; }
    .alert-card { background-color: #fee2e2; border-left: 5px solid #ef4444; padding: 15px; border-radius: 8px; margin-bottom: 20px; font-size: 0.9rem; }
    .report-box { padding: 10px; border-radius: 6px; margin-bottom: 5px; border: 1px solid #e2e8f0; font-size: 0.85rem; }
    .badge { padding: 4px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; color: white !important; display: inline-block; }
    .bg-psichiatra { background: #dc2626; } .bg-infermiere { background: #2563eb; }
    .bg-educatore { background: #059669; } .bg-oss { background: #d97706; }
    .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 5px; border: 1px solid #e2e8f0; }
    .custom-table th { background-color: #1e293b; color: #ffffff !important; padding: 10px; font-size: 0.75rem; text-align: left; }
    .custom-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; }
    .text-red { color: #dc2626; font-weight: bold; }
    .text-green { color: #16a34a; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_database_v4.db"
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

# --- 3. ACCESSO ---
if 'user_data' not in st.session_state: st.session_state.user_data = None
if not st.session_state.user_data:
    st.markdown("<h1 class='main-title'>REMS CONNECT ELITE</h1>", unsafe_allow_html=True)
    tab_l, tab_r = st.tabs(["🔐 Accedi", "📝 Registrati"])
    with tab_l:
        with st.form("login"):
            u, p = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ENTRA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, make_hashes(p)))
                if res: 
                    st.session_state.user_data = {"user": u, "nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Credenziali errate")
    with tab_r:
        with st.form("reg"):
            nu, np = st.text_input("Username"), st.text_input("Password", type="password")
            n, c = st.text_input("Nome"), st.text_input("Cognome")
            q = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, make_hashes(np), n, c, q), True); st.success("Registrato!")
    st.stop()

# --- 4. UTILS ---
u_info = st.session_state.user_data
firma = f"{u_info['nome']} {u_info['cognome']}"
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "📅 Agenda", "⚙️ Gestione"])
if st.sidebar.button("LOGOUT"): st.session_state.user_data = None; st.rerun()

def get_csv_download_link(p_id, nome):
    data = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (p_id,))
    df = pd.DataFrame(data, columns=['Data', 'Ruolo', 'Operatore', 'Evento'])
    csv = df.to_csv(index=False).encode('utf-8-sig')
    b64 = base64.b64encode(csv).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="Diario_{nome}.csv" style="text-decoration:none; background:#1e40af; color:white; padding:8px 15px; border-radius:5px; font-size:0.8rem;">📥 Esporta Diario</a>'

# --- 5. LOGICA ---

if menu == "📊 Monitoraggio":
    st.markdown("<h2 class='main-title'>Diario Clinico Unificato</h2>", unsafe_allow_html=True)
    
    # ALERT SCADENZE
    oggi = date.today().strftime("%d/%m/%Y")
    alerts = db_run("SELECT p.nome, a.tipo, a.ora FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.data = ?", (oggi,))
    if alerts:
        st.markdown("<div class='alert-card'>🔔 <b>APPUNTAMENTI DI OGGI:</b></div>", unsafe_allow_html=True)
        for p_n, ti, orario in alerts: st.error(f"Paziente: **{p_n}** | {ti} alle {orario}")

    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {n.upper()}", expanded=False):
            # GRAFICO A 4 PARAMETRI (MAX, MIN, FC, SpO2)
            p_data = db_run("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '📊 %' ORDER BY id_u ASC", (pid,))
            if p_data:
                try:
                    g_list = []
                    for d, nt in p_data:
                        parts = nt.replace("📊 ","").split(" ")
                        p_max = float(parts[0].split(":")[1])
                        p_min = float(parts[1].split(":")[1])
                        p_fc = float(parts[2].split(":")[1])
                        p_sp = float(parts[3].split(":")[1])
                        g_list.append({"Data": d, "Sistolica (Max)": p_max, "Diastolica (Min)": p_min, "Frequenza (FC)": p_fc, "Saturazione (SpO2)": p_sp})
                    st.write("📈 **Andamento Parametri Clinici**")
                    st.line_chart(pd.DataFrame(g_list).set_index("Data"))
                except: pass

            log = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if log:
                h = "<table class='custom-table'><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Evento</th></tr>"
                for d, r, o, nt in log:
                    cls = f"bg-{r.lower()}"
                    h += f"<tr><td>{d}</td><td><span class='badge {cls}'>{r}</span></td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

elif menu == "👥 Equipe":
    ruolo = u_info['ruolo']
    st.markdown(f"<div class='section-header'>GESTIONE {ruolo.upper()}</div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_n = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista]); p_id = [p[0] for p in p_lista if p[1] == p_n][0]
        t_op, t_doc = st.tabs(["Operatività", "📂 Cartella Documenti"])

        with t_op:
            if ruolo == "Psichiatra":
                with st.form("ps"):
                    c1,c2 = st.columns(2); fa, do = c1.text_input("Farmaco"), c2.text_input("Dose")
                    m,p,n = st.columns(3); m1, p1, n1 = m.checkbox("M"), p.checkbox("P"), n.checkbox("N")
                    if st.form_submit_button("CONFERMA TERAPIA"):
                        tu = ",".join([s for s, b in zip(["M","P","N"], [m1,p1,n1]) if b])
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, fa, do, tu, firma, date.today().strftime("%d/%m/%Y")), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🔄 MODIFICA TERAPIA: {fa} ({do})", "Psichiatra", firma), True)
                        st.rerun()
                for f, d, t, m, rid in db_run("SELECT farmaco, dosaggio, turni, medico, id_u FROM terapie WHERE p_id=?", (p_id,)):
                    c1, c2 = st.columns([10, 1]); c1.markdown(f"<div class='report-box'>💊 <b>{f}</b> - {d} | Turni: {t}</div>", unsafe_allow_html=True)
                    if c2.button("🗑️", key=f"t_{rid}"): db_run("DELETE FROM terapie WHERE id_u=?", (rid,), True); st.rerun()

            elif ruolo == "Infermiere":
                it1, it2, it3 = st.tabs(["💊 Farmaci", "📊 Parametri", "📝 Consegne"])
                with it1:
                    turno = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
                    for fa, do, tu, rid in db_run("SELECT farmaco, dosaggio, turni, id_u FROM terapie WHERE p_id=?", (p_id,)):
                        if turno[0] in tu:
                            c1,c2,c3 = st.columns([3,1,1]); c1.write(f"**{fa}** ({do})")
                            if c2.button("✔️", key=f"a_{rid}"): db_run("INSERT INTO eventi (id,data,nota,ruolo,op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💊 Assunto: {fa}", "Infermiere", firma), True); st.rerun()
                    for d, nt in db_run("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '💊 %' ORDER BY id_u DESC LIMIT 5", (p_id,)): st.markdown(f"<div class='report-box'>{d} - {nt}</div>", unsafe_allow_html=True)
                with it2:
                    with st.form("pv"):
                        c1,c2,c3,c4,c5 = st.columns(5)
                        pa_max = c1.number_input("PA Max", value=120); pa_min = c2.number_input("PA Min", value=80)
                        fc = c3.number_input("FC", value=70); sp = c4.number_input("SpO2", value=98); tc = c5.text_input("TC °C")
                        if st.form_submit_button("SALVA PV"):
                            nota_v = f"📊 MAX:{pa_max} MIN:{pa_min} FC:{fc} SpO2:{sp} TC:{tc}"
                            db_run("INSERT INTO eventi (id,data,nota,ruolo,op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), nota_v, "Infermiere", firma), True); st.rerun()
                    for d, nt in db_run("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '📊 %' ORDER BY id_u DESC LIMIT 5", (p_id,)): st.markdown(f"<div class='report-box'>{d} - {nt}</div>", unsafe_allow_html=True)
                with it3:
                    txt = st.text_area("Consegna")
                    if st.button("INVIA"): db_run("INSERT INTO eventi (id,data,nota,ruolo,op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 {txt}", "Infermiere", firma), True); st.rerun()

            elif ruolo == "OSS":
                txt = st.text_area("Nota OSS")
                if st.button("SALVA"): db_run("INSERT INTO eventi (id,data,nota,ruolo,op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 {txt}", "OSS", firma), True); st.rerun()
                for d, nt in db_run("SELECT data, nota FROM eventi WHERE id=? AND ruolo='OSS' ORDER BY id_u DESC LIMIT 5", (p_id,)): st.markdown(f"<div class='report-box'>{d} - {nt}</div>", unsafe_allow_html=True)

            elif ruolo == "Educatore":
                mov = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY id_u DESC", (p_id,))
                st.metric("SALDO", f"€ {sum([m[2] if m[3] == 'Entrata' else -m[2] for m in mov]):.2f}")
                with st.form("cas"):
                    tp, im, ds = st.radio("Tipo", ["Entrata", "Uscita"]), st.number_input("€"), st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"): db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tp, firma), True); st.rerun()
                for d, ds, im, tp, op in mov: st.write(f"{d} - {tp}: {im}€ ({ds})")

        with t_doc:
            up = st.file_uploader("Carica file")
            if up and st.button("SALVA DOCUMENTO"):
                db_run("INSERT INTO documenti (p_id, nome_file, tipo_file, dati, data_caricamento, op) VALUES (?,?,?,?,?,?)", (p_id, up.name, up.type, up.read(), date.today().strftime("%d/%m/%Y"), firma), True); st.success("Caricato!")
            for fn, dc, op, dt in db_run("SELECT nome_file, data_caricamento, op, dati FROM documenti WHERE p_id=?", (p_id,)):
                c1, c2 = st.columns([4, 1]); c1.write(f"📄 {fn} (del {dc})"); c2.download_button("Scarica", dt, file_name=fn)

elif menu == "📅 Agenda":
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_n = st.selectbox("Paziente", [p[1] for p in p_lista]); p_id = [p[0] for p in p_lista if p[1] == p_n][0]
        with st.form("app"):
            d, h = st.date_input("Data"), st.time_input("Ora")
            ti, det = st.selectbox("Tipo", ["Udienza", "Visita", "Permesso"]), st.text_input("Dettagli")
            if st.form_submit_button("SALVA"): db_run("INSERT INTO appuntamenti (p_id, data, ora, tipo, det) VALUES (?,?,?,?,?)", (p_id, d.strftime("%d/%m/%Y"), h.strftime("%H:%M"), ti, det), True); st.rerun()

elif menu == "⚙️ Gestione":
    st.header("Anagrafica ed Export")
    nuovo = st.text_input("Nuovo Paziente")
    if st.button("SALVA"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo.upper(),), True); st.rerun()
    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.write(f"👤 **{n}**"); c2.markdown(get_csv_download_link(pid, n), unsafe_allow_html=True)
        if c3.button("Elimina", key=f"del_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
