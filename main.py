import sqlite3
import streamlit as st
from datetime import datetime, date

# --- 1. CONFIGURAZIONE E DESIGN ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide", page_icon="🏥", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #ffffff; }
    .main-title {
        text-align: center; 
        background: linear-gradient(90deg, #1e40af, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.5rem; margin-bottom: 25px;
    }
    .section-header {
        background-color: #1e40af; color: #ffffff; padding: 12px;
        border-radius: 8px; text-align: center; font-weight: 700; 
        margin-bottom: 20px; font-size: 1.2rem; letter-spacing: 1px;
    }
    .report-box { padding: 10px; border-radius: 6px; margin-bottom: 5px; border: 1px solid #e2e8f0; font-size: 0.85rem; }
    .report-psichiatra { background-color: #e0f2fe; border-left: 5px solid #3b82f6; }
    .report-infermiere { background-color: #f0fdf4; border-left: 5px solid #22c55e; }
    .report-oss { background-color: #fffbeb; border-left: 5px solid #f59e0b; }
    .report-appuntamenti { background-color: #f8fafc; border-left: 5px solid #64748b; }
    .report-educatore { background-color: #fef2f2; border-left: 5px solid #ef4444; }
    [data-testid="stSidebar"] { background-color: #1e40af !important; border-right: 1px solid #1e3a8a; }
    [data-testid="stSidebar"] * { color: #ffffff !important; font-weight: 600 !important; }
    .custom-table { width: 100%; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; overflow: hidden; margin-bottom: 5px; border: 1px solid #e2e8f0; }
    .custom-table th { background-color: #1e293b; color: #ffffff !important; padding: 10px; font-size: 0.75rem; text-align: left; }
    .custom-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; color: #1e293b !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_database_v2.db"
def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (p_id INTEGER, data TEXT, ora TEXT, tipo TEXT, accompagnatore TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>SISTEMA REMS CONNECT</h1>", unsafe_allow_html=True)
    with st.columns([1,1,1])[1]:
        with st.form("login"):
            pwd = st.text_input("Codice Identificativo", type="password")
            if st.form_submit_button("ACCEDI"):
                if pwd == "rems2026": st.session_state.auth = True; st.rerun()
                else: st.error("Codice errato")
    st.stop()

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "📅 Appuntamenti", "⚙️ Gestione"])

# --- 5. LOGICA ---
if menu == "📊 Monitoraggio":
    st.markdown("<h2 class='main-title'>Diario Clinico Unificato</h2>", unsafe_allow_html=True)
    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {n.upper()}", expanded=False):
            log = db_run("SELECT data, ruolo, op, nota, umore FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if log:
                h = "<table class='custom-table'><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Umore</th><th>Evento</th></tr>"
                for d, r, o, nt, u in log: h += f"<tr><td>{d}</td><td>{r}</td><td>{o}</td><td>{u}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

elif menu == "👥 Equipe":
    ruolo = st.sidebar.selectbox("PROFILO OPERATIVO", ["Scegli...", "Psichiatra", "Infermiere", "Educatore", "OSS"])
    if ruolo != "Scegli...":
        heads = {"Psichiatra": "GESTIONE TERAPEUTICA", "Infermiere": "GESTIONE INFERMIERISTICA", "OSS": "GESTIONE E MANSIONI", "Educatore": "GESTIONE EDUCATIVA"}
        st.markdown(f"<div class='section-header'>{heads[ruolo]}</div>", unsafe_allow_html=True)
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_lista:
            p_n = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista]); p_id = [p[0] for p in p_lista if p[1] == p_n][0]

            if ruolo == "Psichiatra":
                f_m = st.text_input("Firma Medico")
                with st.form("pres"):
                    c1,c2 = st.columns(2); fa, do = c1.text_input("Farmaco"), c2.text_input("Dose")
                    m,p,n = st.columns(3); m1, p1, n1 = m.checkbox("M"), p.checkbox("P"), n.checkbox("N")
                    if st.form_submit_button("CONFERMA"):
                        if fa and do: tu = ",".join([s for s, b in zip(["M","P","N"], [m1,p1,n1]) if b]); db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, fa, do, tu, f_m, date.today().strftime("%d/%m/%Y")), True); st.rerun()
                for f, d, t, m, rid in db_run("SELECT farmaco, dosaggio, turni, medico, id_u FROM terapie WHERE p_id=?", (p_id,)):
                    c1, c2 = st.columns([10, 1]); c1.markdown(f"<div class='report-box report-psichiatra'>💊 <b>{f}</b> - {d} | Turni: {t} | Prescr: {m}</div>", unsafe_allow_html=True)
                    if c2.button("🗑️", key=f"t_{rid}"): db_run("DELETE FROM terapie WHERE id_u=?", (rid,), True); st.rerun()

            elif ruolo == "Infermiere":
                f_i = st.text_input("Firma Infermiere")
                t1, t2, t3 = st.tabs(["💊 Farmaci", "📊 Parametri", "📝 Consegne"])
                with t1:
                    turno = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
                    for fa, do, tu, rid in db_run("SELECT farmaco, dosaggio, turni, id_u FROM terapie WHERE p_id=?", (p_id,)):
                        if turno[0] in tu:
                            c1,c2,c3 = st.columns([3,1,1]); c1.write(f"**{fa}** ({do})")
                            if c2.button("✔️", key=f"a_{rid}"): db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"💊 Assunto: {fa}", "Infermiere", f_i), True); st.success("OK")
                            if c3.button("❌", key=f"r_{rid}"): db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"💊 Rifiutato: {fa}", "Infermiere", f_i), True); st.warning("Rifiutato")
                    for d, nt in db_run("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '💊 %' ORDER BY id_u DESC LIMIT 10", (p_id,)): st.markdown(f"<div class='report-box report-infermiere'>{d} - {nt}</div>", unsafe_allow_html=True)
                with t2:
                    with st.form("pv"):
                        c1,c2,c3,c4 = st.columns(4); pa, fc, sp, tc = c1.text_input("PA"), c2.text_input("FC"), c3.text_input("SpO2"), c4.text_input("TC")
                        if st.form_submit_button("SALVA"): db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"📊 PA:{pa} FC:{fc} SpO:{sp} TC:{tc}", "Infermiere", f_i), True); st.rerun()
                    for d, nt in db_run("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '📊 %' ORDER BY id_u DESC LIMIT 10", (p_id,)): st.markdown(f"<div class='report-box report-infermiere'>{d} - {nt}</div>", unsafe_allow_html=True)
                with t3:
                    txt_i = st.text_area("Consegna")
                    if st.button("INVIA"): 
                        if txt_i: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"📝 {txt_i}", "Infermiere", f_i), True); st.rerun()
                    for d, nt, op in db_run("SELECT data, nota, op FROM eventi WHERE id=? AND ruolo='Infermiere' AND nota LIKE '📝 %' ORDER BY id_u DESC LIMIT 5", (p_id,)): st.markdown(f"<div class='report-box report-infermiere'>{d} - {nt} ({op})</div>", unsafe_allow_html=True)

            elif ruolo == "OSS":
                f_o = st.text_input("Firma OSS")
                t_oss1, t_oss2 = st.tabs(["🧹 Mansioni", "📝 Note OSS"])
                with t_oss1:
                    with st.form("oss_m"):
                        m1,m2,m3 = st.columns(3); cam, ref, lav = m1.checkbox("Camera"), m2.checkbox("Refettorio"), m3.checkbox("Lavanderia")
                        if st.form_submit_button("SALVA"):
                            sel = [t for b,t in zip([cam,ref,lav], ["Camera","Refettorio","Lavanderia"]) if b]
                            if sel: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"🧹 {', '.join(sel)}", "OSS", f_o), True); st.rerun()
                    for d, n in db_run("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '🧹 %' ORDER BY id_u DESC LIMIT 5", (p_id,)): st.markdown(f"<div class='report-box report-oss'>{d} - {n}</div>", unsafe_allow_html=True)
                with t_oss2:
                    txt_o = st.text_area("Nota OSS")
                    if st.button("SALVA NOTA"):
                        if txt_o: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"📝 {txt_o}", "OSS", f_o), True); st.rerun()
                    for d, nt, op in db_run("SELECT data, nota, op FROM eventi WHERE id=? AND ruolo='OSS' AND nota LIKE '📝 %' ORDER BY id_u DESC", (p_id,)): st.markdown(f"<div class='report-box report-oss'>{d} - {nt} ({op})</div>", unsafe_allow_html=True)

            elif ruolo == "Educatore":
                f_e = st.text_input("Firma Educatore")
                mov = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY id_u DESC", (p_id,))
                st.metric("SALDO", f"€ {sum([m[2] if m[3] == 'Entrata' else -m[2] for m in mov]):.2f}")
                with st.form("cas"):
                    tp, im, ds = st.radio("Tipo", ["Entrata", "Uscita"]), st.number_input("€", min_value=0.0), st.text_input("Causale")
                    if st.form_submit_button("ESEGUI"):
                        if ds and im > 0: db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tp, f_e), True); st.rerun()
                if mov:
                    h = "<table class='custom-table'><tr><th>Data</th><th>Causale</th><th>Importo</th><th>Operatore</th></tr>"
                    for d, ds, im, tp, op in mov: h += f"<tr><td>{d}</td><td>{ds}</td><td style='color:{'green' if tp=='Entrata' else 'red'}'>{im:.2f}€</td><td>{op}</td></tr>"
                    st.markdown(h + "</table>", unsafe_allow_html=True)

elif menu == "📅 Appuntamenti":
    st.markdown("<h2 class='main-title'>Agenda REMS</h2>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_n = st.selectbox("Paziente", [p[1] for p in p_lista]); p_id = [p[0] for p in p_lista if p[1] == p_n][0]
        with st.form("app"):
            c1, c2 = st.columns(2); d, h = c1.date_input("Data"), c2.time_input("Ora")
            ti, det = st.selectbox("Tipo", ["Udienza", "Visita", "Permesso"]), st.text_input("Dettagli")
            if st.form_submit_button("AGGIUNGI"): db_run("INSERT INTO appuntamenti (p_id, data, ora, tipo, accompagnatore) VALUES (?,?,?,?,?)", (p_id, d.strftime("%d/%m/%Y"), h.strftime("%H:%M"), ti, det), True); st.rerun()
        for da, ora, tip, det, rid in db_run("SELECT data, ora, tipo, accompagnatore, id_u FROM appuntamenti WHERE p_id=?", (p_id,)):
            c1, c2 = st.columns([10, 1]); c1.markdown(f"<div class='report-box report-appuntamenti'>📅 <b>{da}</b> ore <b>{ora}</b> - [{tip}] {det}</div>", unsafe_allow_html=True)
            if c2.button("🗑️", key=f"a_{rid}"): db_run("DELETE FROM appuntamenti WHERE id_u=?", (rid,), True); st.rerun()

elif menu == "⚙️ Gestione":
    st.header("Anagrafica")
    nuovo = st.text_input("Nuovo Paziente")
    if st.button("SALVA"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo.upper(),), True); st.rerun()
    for pid, n in db_run("SELECT id, nome FROM pazienti"):
        c1, c2 = st.columns([5,1]); c1.write(f"**{n}**")
        if c2.button("Elimina", key=f"p_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
