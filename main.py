import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib

# --- 1. CONFIGURAZIONE E DESIGN ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide", page_icon="🏥", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #ffffff; }
    .main-title { text-align: center; background: linear-gradient(90deg, #1e40af, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; font-size: 2.5rem; margin-bottom: 25px; }
    .section-header { background-color: #1e40af; color: #ffffff; padding: 12px; border-radius: 8px; text-align: center; font-weight: 700; margin-bottom: 20px; font-size: 1.2rem; }
    .report-box { padding: 10px; border-radius: 6px; margin-bottom: 5px; border: 1px solid #e2e8f0; font-size: 0.85rem; }
    .report-psichiatra { background-color: #e0f2fe; border-left: 5px solid #3b82f6; }
    .report-infermiere { background-color: #f0fdf4; border-left: 5px solid #22c55e; }
    .report-oss { background-color: #fffbeb; border-left: 5px solid #f59e0b; }
    .badge { padding: 4px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; color: white !important; display: inline-block; }
    .bg-psichiatra { background: #dc2626; } .bg-infermiere { background: #2563eb; }
    .bg-educatore { background: #059669; } .bg-oss { background: #d97706; }
    [data-testid="stSidebar"] { background-color: #1e40af !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 5px; border: 1px solid #e2e8f0; }
    .custom-table th { background-color: #1e293b; color: #ffffff !important; padding: 10px; font-size: 0.75rem; text-align: left; }
    .custom-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. GESTIONE DATABASE ---
DB_NAME = "rems_database_v3.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        # Creazione Tabelle
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (p_id INTEGER, data TEXT, ora TEXT, tipo TEXT, accompagnatore TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()

# --- 3. SISTEMA DI AUTENTICAZIONE ---
if 'user_data' not in st.session_state: st.session_state.user_data = None

if not st.session_state.user_data:
    st.markdown("<h1 class='main-title'>REMS CONNECT LOGIN</h1>", unsafe_allow_html=True)
    tab_l, tab_r = st.tabs(["🔐 Accedi", "📝 Registrati"])
    
    with tab_l:
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("ENTRA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, make_hashes(p)))
                if res: 
                    st.session_state.user_data = {"user": u, "nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.success(f"Benvenuto {res[0][0]}!")
                    st.rerun()
                else: st.error("Credenziali non valide.")
                
    with tab_r:
        with st.form("reg_form"):
            new_u = st.text_input("Scegli un Username")
            new_p = st.text_input("Scegli una Password", type="password")
            n = st.text_input("Il tuo Nome")
            c = st.text_input("Il tuo Cognome")
            q = st.selectbox("Tua Qualifica Professionale", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                if new_u and new_p and n and c:
                    try:
                        db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (new_u, make_hashes(new_p), n, c, q), True)
                        st.success("Profilo creato! Ora puoi accedere.")
                    except: st.error("Username già in uso.")
    st.stop()

# --- 4. INTERFACCIA PRINCIPALE ---
u_info = st.session_state.user_data
firma_automatica = f"{u_info['nome']} {u_info['cognome']}"
st.sidebar.markdown(f"👤 **{firma_automatica}**\n⭐ *{u_info['ruolo']}*")

if st.sidebar.button("ESCI (LOGOUT)"): 
    st.session_state.user_data = None
    st.rerun()

menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "📅 Appuntamenti", "⚙️ Gestione"])

# --- 5. LOGICA SEZIONI ---

# 📊 MONITORAGGIO (Visibile a tutti)
if menu == "📊 Monitoraggio":
    st.markdown("<h2 class='main-title'>Diario Clinico Unificato</h2>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if not p_lista: st.info("Nessun paziente in anagrafica. Aggiungili in Gestione.")
    for pid, n in p_lista:
        with st.expander(f"👤 {n.upper()}", expanded=False):
            log = db_run("SELECT data, ruolo, op, nota, umore FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if log:
                h = "<table class='custom-table'><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Umore</th><th>Evento</th></tr>"
                for d, r, o, nt, u in log:
                    cls = f"bg-{r.lower()}" if r.lower() in ["infermiere", "oss", "psichiatra", "educatore"] else ""
                    h += f"<tr><td>{d}</td><td><span class='badge {cls}'>{r}</span></td><td>{o}</td><td>{u}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)
            else: st.write("Nessun evento registrato.")

# 👥 EQUIPE (Filtro automatico per qualifica)
elif menu == "👥 Equipe":
    ruolo = u_info['ruolo']
    heads = {"Psichiatra": "GESTIONE TERAPEUTICA", "Infermiere": "GESTIONE INFERMIERISTICA", "OSS": "GESTIONE E MANSIONI", "Educatore": "GESTIONE EDUCATIVA"}
    st.markdown(f"<div class='section-header'>{heads[ruolo]}</div>", unsafe_allow_html=True)
    
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_n = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_n][0]

        if ruolo == "Psichiatra":
            with st.form("pres"):
                c1,c2 = st.columns(2); fa, do = c1.text_input("Farmaco"), c2.text_input("Dose")
                m,p,n = st.columns(3); m1, p1, n1 = m.checkbox("M"), p.checkbox("P"), n.checkbox("N")
                if st.form_submit_button("CONFERMA PRESCRIZIONE"):
                    if fa and do:
                        tu = ",".join([s for s, b in zip(["M","P","N"], [m1,p1,n1]) if b])
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, fa, do, tu, firma_automatica, date.today().strftime("%d/%m/%Y")), True)
                        st.rerun()
            for f, d, t, m, rid in db_run("SELECT farmaco, dosaggio, turni, medico, id_u FROM terapie WHERE p_id=?", (p_id,)):
                c1, c2 = st.columns([10, 1])
                c1.markdown(f"<div class='report-box report-psichiatra'>💊 <b>{f}</b> - {d} | Turni: {t} | Prescr: {m}</div>", unsafe_allow_html=True)
                if c2.button("🗑️", key=f"t_{rid}"): db_run("DELETE FROM terapie WHERE id_u=?", (rid,), True); st.rerun()

        elif ruolo == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 Farmaci", "📊 Parametri", "📝 Consegne"])
            with t1:
                turno = st.selectbox("Turno Somministrazione", ["Mattina", "Pomeriggio", "Notte"])
                for fa, do, tu, rid in db_run("SELECT farmaco, dosaggio, turni, id_u FROM terapie WHERE p_id=?", (p_id,)):
                    if turno[0] in tu:
                        c1,c2,c3 = st.columns([3,1,1]); c1.write(f"**{fa}** ({do})")
                        if c2.button("✔️", key=f"a_{rid}"): db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"💊 Assunto: {fa}", "Infermiere", firma_automatica), True); st.success("Registrato")
                        if c3.button("❌", key=f"r_{rid}"): db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"💊 Rifiutato: {fa}", "Infermiere", firma_automatica), True); st.warning("Rifiuto Registrato")
            with t2:
                with st.form("pv"):
                    c1,c2,c3,c4 = st.columns(4); pa, fc, sp, tc = c1.text_input("PA"), c2.text_input("FC"), c3.text_input("SpO2"), c4.text_input("TC")
                    if st.form_submit_button("SALVA PARAMETRI"):
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"📊 PA:{pa} FC:{fc} SpO:{sp} TC:{tc}", "Infermiere", firma_automatica), True)
                        st.rerun()
            with t3:
                txt_i = st.text_area("Nuova Consegna")
                if st.button("INVIA CONSEGNA"): 
                    if txt_i: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"📝 {txt_i}", "Infermiere", firma_automatica), True); st.rerun()

        elif ruolo == "OSS":
            t_oss1, t_oss2 = st.tabs(["🧹 Mansioni", "📝 Note"])
            with t_oss1:
                with st.form("oss_m"):
                    m1,m2,m3 = st.columns(3); cam, ref, lav = m1.checkbox("Camera"), m2.checkbox("Refettorio"), m3.checkbox("Lavanderia")
                    if st.form_submit_button("SALVA MANSIONI"):
                        sel = [t for b,t in zip([cam,ref,lav], ["Camera","Refettorio","Lavanderia"]) if b]
                        if sel: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"🧹 {', '.join(sel)}", "OSS", firma_automatica), True); st.rerun()
            with t_oss2:
                txt_o = st.text_area("Nota OSS")
                if st.button("SALVA NOTA OSS"):
                    if txt_o: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"📝 {txt_o}", "OSS", firma_automatica), True); st.rerun()

        elif ruolo == "Educatore":
            mov = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY id_u DESC", (p_id,))
            st.metric("SALDO ATTUALE", f"€ {sum([m[2] if m[3] == 'Entrata' else -m[2] for m in mov]):.2f}")
            with st.form("cas"):
                tp, im, ds = st.radio("Operazione", ["Entrata", "Uscita"]), st.number_input("€", min_value=0.0), st.text_input("Causale")
                if st.form_submit_button("REGISTRA MOVIMENTO"):
                    if ds and im > 0:
                        db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tp, firma_automatica), True)
                        st.rerun()
    else: st.warning("Aggiungi prima dei pazienti in Gestione.")

# 📅 APPUNTAMENTI (Agenda)
elif menu == "📅 Appuntamenti":
    st.markdown("<h2 class='main-title'>Agenda REMS</h2>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_n = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_n][0]
        with st.form("app"):
            c1, c2 = st.columns(2); d, h = c1.date_input("Data"), c2.time_input("Ora")
            ti, det = st.selectbox("Tipo", ["Udienza", "Visita", "Permesso"]), st.text_input("Dettagli / Accompagnatore")
            if st.form_submit_button("AGGIUNGI IN AGENDA"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, tipo, accompagnatore) VALUES (?,?,?,?,?)", (p_id, d.strftime("%d/%m/%Y"), h.strftime("%H:%M"), ti, det), True)
                st.rerun()
        for da, ora, tip, det, rid in db_run("SELECT data, ora, tipo, accompagnatore, id_u FROM appuntamenti WHERE p_id=?", (p_id,)):
            c1, c2 = st.columns([10, 1])
            c1.markdown(f"<div class='report-box report-appuntamenti'>📅 <b>{da}</b> ore <b>{ora}</b> - [{tip}] {det}</div>", unsafe_allow_html=True)
            if c2.button("🗑️", key=f"a_{rid}"): db_run("DELETE FROM appuntamenti WHERE id_u=?", (rid,), True); st.rerun()

# ⚙️ GESTIONE (Anagrafica)
elif menu == "⚙️ Gestione":
    st.header("Anagrafica Pazienti")
    nuovo = st.text_input("Inserisci Nome e Cognome nuovo paziente")
    if st.button("SALVA PAZIENTE"):
        if nuovo:
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo.upper(),), True)
            st.success(f"{nuovo.upper()} aggiunto.")
            st.rerun()
    for pid, n in db_run("SELECT id, nome FROM pazienti"):
        c1, c2 = st.columns([5,1]); c1.write(f"**{n}**")
        if c2.button("Elimina", key=f"p_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
