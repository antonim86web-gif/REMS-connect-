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
    [data-testid="stSidebar"] { background-color: #1e40af !important; border-right: 1px solid #1e3a8a; }
    [data-testid="stSidebar"] * { color: #ffffff !important; font-weight: 600 !important; }
    .custom-table { 
        width: 100%; border-collapse: collapse; background-color: #ffffff;
        border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
        margin-bottom: 5px; border: 1px solid #e2e8f0;
    }
    .custom-table th { background-color: #1e293b; color: #ffffff !important; padding: 10px; font-size: 0.75rem; text-transform: uppercase; text-align: left; }
    .custom-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; color: #1e293b !important; }
    .badge { padding: 4px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; color: white !important; display: inline-block; }
    .bg-psichiatra { background: #dc2626; } .bg-infermiere { background: #2563eb; }
    .bg-educatore  { background: #059669; } .bg-oss        { background: #d97706; }
    .bg-sistema    { background: #475569; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_pro_2026.db"
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
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            log = db_run("SELECT data, ruolo, op, nota, umore FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if log:
                h = "<table class='custom-table'><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Umore</th><th>Evento</th></tr>"
                for d, r, o, n, u in log:
                    cls = f"bg-{r.lower()}" if r.lower() in ["infermiere", "oss", "psichiatra", "educatore"] else "bg-sistema"
                    h += f"<tr><td>{d}</td><td><span class='badge {cls}'>{r}</span></td><td>{o}</td><td>{u}</td><td>{n}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)
            else: st.info("Nessun evento registrato per questo paziente.")

elif menu == "👥 Equipe":
    ruolo = st.sidebar.selectbox("PROFILO OPERATIVO", ["Scegli...", "Psichiatra", "Infermiere", "Educatore", "OSS"])
    if ruolo != "Scegli...":
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_lista:
            p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
            p_id = [p[0] for p in p_lista if p[1] == p_nome][0]
            umore_list = ["Stabile", "Agitato", "Collaborante", "Provocatorio", "Depresso"]

            if ruolo == "Psichiatra":
                f_m = st.text_input("Firma Medico")
                with st.form("prescr"):
                    c1,c2 = st.columns(2); fa, do = c1.text_input("Farmaco"), c2.text_input("Dose")
                    m,p,n = st.columns(3); m1, p1, n1 = m.checkbox("Mattina"), p.checkbox("Pomeriggio"), n.checkbox("Notte")
                    if st.form_submit_button("CONFERMA PRESCRIZIONE"):
                        if fa and do and f_m:
                            tu = ",".join([s for s, b in zip(["M","P","N"], [m1,p1,n1]) if b])
                            db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, fa, do, tu, f_m, date.today().strftime("%d/%m/%Y")), True)
                            st.success("Terapia inserita"); st.rerun()
                st.write("**Piano Terapeutico Attivo:**")
                piano = db_run("SELECT farmaco, dosaggio, turni, medico, id_u FROM terapie WHERE p_id=?", (p_id,))
                if piano:
                    st.markdown("<table class='custom-table'><tr><th>Farmaco</th><th>Dose</th><th>Turni</th><th>Medico</th><th>Azioni</th></tr></table>", unsafe_allow_html=True)
                    for f, d, t, m, rid in piano:
                        c_i, c_d = st.columns([10, 1])
                        with c_i: st.markdown(f"<table class='custom-table'><tr><td style='width:25%'>{f}</td><td style='width:15%'>{d}</td><td style='width:15%'>{t}</td><td style='width:45%'>{m}</td></tr></table>", unsafe_allow_html=True)
                        with c_d: 
                            if st.button("🗑️", key=f"t_{rid}"): db_run("DELETE FROM terapie WHERE id_u=?", (rid,), True); st.rerun()

            elif ruolo == "Infermiere":
                f_i = st.text_input("Firma Infermiere")
                t1, t2, t3 = st.tabs(["💊 Farmaci", "📊 Parametri", "📝 Consegne"])
                with t1:
                    turno = st.selectbox("Turno Attuale", ["Mattina", "Pomeriggio", "Notte"])
                    ter = db_run("SELECT farmaco, dosaggio, turni, id_u FROM terapie WHERE p_id=?", (p_id,))
                    for fa, do, tu, rid in ter:
                        if turno[0] in tu:
                            c1,c2,c3 = st.columns([3,1,1]); c1.write(f"**{fa}** ({do})")
                            if c2.button("Somministra", key=f"a_{rid}"):
                                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"💊 Assunto: {fa} ({do})", "Infermiere", f_i), True); st.success(f"{fa} OK")
                            if c3.button("Rifiuta", key=f"r_{rid}"):
                                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"💊 RIFIUTATO: {fa}", "Infermiere", f_i), True); st.warning(f"{fa} Rifiutato")
                    st.divider()
                    st.write("**Storico Farmaci (Ultime 24h):**")
                    for d, n in db_run("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '💊 %' ORDER BY id_u DESC LIMIT 10", (p_id,)):
                        st.markdown(f"<small>{d} - {n}</small>", unsafe_allow_html=True)
                with t2:
                    with st.form("pv"):
                        c1,c2,c3,c4 = st.columns(4); pa, fc, sp, tc = c1.text_input("PA"), c2.text_input("FC"), c3.text_input("SpO2"), c4.text_input("TC")
                        if st.form_submit_button("REGISTRA"):
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"📊 PA:{pa} FC:{fc} SpO:{sp} TC:{tc}", "Infermiere", f_i), True); st.rerun()
                    st.write("**Andamento Parametri:**")
                    for d, n, o in db_run("SELECT data, nota, op FROM eventi WHERE id=? AND nota LIKE '📊 %' ORDER BY id_u DESC", (p_id,)):
                        st.markdown(f"<p style='font-size:0.8rem; margin:0;'>{d} | {n} ({o})</p>", unsafe_allow_html=True)
                with t3:
                    u_i = st.selectbox("Stato Umore", umore_list); txt_i = st.text_area("Nota Clinica")
                    if st.button("INVIA CONSEGNA"):
                        if txt_i: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), u_i, f"📝 {txt_i}", "Infermiere", f_i), True); st.rerun()
                    for d, um, nt, op in db_run("SELECT data, umore, nota, op FROM eventi WHERE id=? AND ruolo='Infermiere' AND nota LIKE '📝 %' ORDER BY id_u DESC LIMIT 5", (p_id,)):
                        st.info(f"{d} - [{um}] {nt} ({op})")

            elif ruolo == "OSS":
                f_o = st.text_input("Firma OSS")
                with st.form("oss_m"):
                    c1,c2 = st.columns(2); m1,m2 = c1.checkbox("Igiene Camera"), c1.checkbox("Cambio Biancheria"); m3,m4 = c2.checkbox("Accompagnamento"), c2.checkbox("Monitoraggio Pasto")
                    if st.form_submit_button("SALVA ATTIVITÀ"):
                        sel = [t for b,t in zip([m1,m2,m3,m4], ["Igiene","Biancheria","Accompagnamento","Pasto"]) if b]
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Collaborante", f"🧹 {', '.join(sel)}", "OSS", f_o), True); st.rerun()
                for d, n in db_run("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '🧹 %' ORDER BY id_u DESC", (p_id,)):
                    st.markdown(f"<small>{d} - {n}</small>", unsafe_allow_html=True)

            elif ruolo == "Educatore":
                f_e = st.text_input("Firma Educatore")
                mov = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY id_u DESC", (p_id,))
                saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in mov])
                st.metric("DISPONIBILITÀ PAZIENTE", f"€ {saldo:.2f}")
                with st.form("cassa"):
                    tp, im, ds = st.radio("Tipo", ["Entrata", "Uscita"]), st.number_input("Importo €", min_value=0.0), st.text_input("Causale")
                    if st.form_submit_button("REGISTRA MOVIMENTO"):
                        db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tp, f_e), True); st.rerun()
                if mov:
                    h = "<table class='custom-table'><tr><th>Data</th><th>Causale</th><th>Importo</th><th>Firma</th></tr>"
                    for d, ds, im, tp, op in mov:
                        col = "#16a34a" if tp == "Entrata" else "#dc2626"
                        h += f"<tr><td>{d}</td><td>{ds}</td><td style='color:{col}; font-weight:bold;'>{' ' if tp=='Entrata' else '-'}{im:.2f}€</td><td>{op}</td></tr>"
                    st.markdown(h + "</table>", unsafe_allow_html=True)

elif menu == "📅 Appuntamenti":
    st.markdown("<h2 class='main-title'>Agenda REMS</h2>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_n = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_n][0]
        with st.form("app_f"):
            c1, c2 = st.columns(2); d, h = c1.date_input("Data"), c2.time_input("Ora")
            ti, det = st.selectbox("Tipo", ["Udienza", "Visita Specialistica", "Permesso", "VTL"]), st.text_input("Dettagli")
            if st.form_submit_button("AGGIUNGI IN AGENDA"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, tipo, accompagnatore) VALUES (?,?,?,?,?)", (p_id, d.strftime("%d/%m/%Y"), h.strftime("%H:%M"), ti, det), True); st.rerun()
        st.divider()
        apps = db_run("SELECT data, ora, tipo, accompagnatore, id_u FROM appuntamenti WHERE p_id=?", (p_id,))
        if apps:
            st.markdown("<table class='custom-table'><tr><th>Data</th><th>Ora</th><th>Tipo</th><th>Dettagli</th><th>Azioni</th></tr></table>", unsafe_allow_html=True)
            for da, ora, tip, det, rid in apps:
                c_i, c_d = st.columns([10, 1])
                with c_i: st.markdown(f"<table class='custom-table'><tr><td style='width:20%'>{da}</td><td style='width:15%'>{ora}</td><td style='width:20%'>{tip}</td><td style='width:45%'>{det}</td></tr></table>", unsafe_allow_html=True)
                with c_d: 
                    if st.button("🗑️", key=f"a_{rid}"): db_run("DELETE FROM appuntamenti WHERE id_u=?", (rid,), True); st.rerun()

elif menu == "⚙️ Gestione":
    st.header("Anagrafica Pazienti")
    nuovo = st.text_input("Inserisci Nome e Cognome")
    if st.button("SALVA NUOVO PAZIENTE"):
        if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo.upper(),), True); st.success("Paziente aggiunto"); st.rerun()
    st.divider()
    for pid, n in db_run("SELECT id, nome FROM pazienti"):
        c1, c2 = st.columns([5,1]); c1.write(f"ID: {pid} - **{n}**")
        if c2.button("Elimina", key=f"p_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
