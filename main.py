import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar

# --- DATABASE ENGINE & ESTRUTTURA INTEGRALE ---
DB_NAME = "rems_pro_v30_full.db"

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        try:
            # Creazione tabelle se non esistono
            cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, stato INTEGER DEFAULT 0)")
            cur.execute("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY AUTOINCREMENT, id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS cassa (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT, tipo_evento TEXT, mezzo TEXT, accompagnatore TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS logs_sistema (id_log INTEGER PRIMARY KEY AUTOINCREMENT, data_ora TEXT, utente TEXT, azione TEXT, dettaglio TEXT)")
            
            # Utente Admin di default
            if cur.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
                cur.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("perito2026"), "SUPER", "USER", "Admin"))
            
            # Stanze di default
            if cur.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
                for i in range(1, 7): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"A{i}", "A", "ISOLAMENTO" if i==6 else "STANDARD"))
                for i in range(1, 11): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"B{i}", "B", "ISOLAMENTO" if i==10 else "STANDARD"))
            
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}")
            return []

def scrivi_log(azione, dettaglio):
    user_log = st.session_state.user_session['uid'] if st.session_state.user_session else "Sistema"
    db_run("INSERT INTO logs_sistema (data_ora, utente, azione, dettaglio) VALUES (?,?,?,?)", 
           (get_now_it().strftime("%d/%m/%Y %H:%M:%S"), user_log, azione, dettaglio), True)

# --- INTERFACCIA GRAFICA ELITE ---
st.set_page_config(page_title="REMS Connect ELITE PRO v30", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0f172a !important; min-width: 300px !important; }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }
    .sidebar-title { color: #38bdf8 !important; font-size: 2rem; font-weight: 900; text-align: center; padding: 20px 0; border-bottom: 2px solid #1e293b; }
    .user-tag { background: #1e293b; padding: 10px; border-radius: 8px; margin: 10px 0; text-align: center; border-left: 4px solid #38bdf8; }
    .section-banner { background: linear-gradient(135deg, #1e3a8a, #1e40af); color: white; padding: 30px; border-radius: 15px; margin-bottom: 25px; text-align: center; box-shadow: 0 10px 20px rgba(0,0,0,0.2); }
    .stButton>button { border-radius: 8px !important; font-weight: 600 !important; }
    .card-diario { background: white; border: 1px solid #e2e8f0; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 8px solid #94a3b8; }
    .role-psichiatra { border-left-color: #ef4444 !important; background-color: #fef2f2; }
    .role-infermiere { border-left-color: #3b82f6 !important; background-color: #eff6ff; }
    .role-educatore { border-left-color: #10b981 !important; background-color: #ecfdf5; }
    .cal-table { width:100%; border-collapse: collapse; table-layout: fixed; background: white; border-radius: 12px; overflow: hidden; }
    .cal-table th { background: #1e293b; color: white; padding: 12px; font-size: 0.9rem; }
    .cal-table td { border: 1px solid #e2e8f0; height: 120px; vertical-align: top; padding: 8px; position: relative; }
    .today-cell { background-color: #f0fdf4 !important; border: 2px solid #22c55e !important; }
    .event-tag { font-size: 0.7rem; background: #3b82f6; color: white; padding: 3px 6px; border-radius: 4px; margin-bottom: 2px; cursor: pointer; }
    .cassa-saldo { background: #111827; color: #10b981; padding: 20px; border-radius: 12px; text-align: center; font-size: 2rem; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# --- SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if 'cal_month' not in st.session_state: st.session_state.cal_month = get_now_it().month
if 'cal_year' not in st.session_state: st.session_state.cal_year = get_now_it().year

# --- LOGIN ---
if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h1>🏥 REMS CONNECT ELITE PRO</h1><p>Sistema di Gestione Integrata - Ver. 30.0 Total</p></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Login Personale")
        with st.form("login"):
            u_in = st.text_input("Username").lower().strip()
            p_in = st.text_input("Password", type="password")
            if st.form_submit_button("ENTRA NEL SISTEMA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res:
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_in}
                    scrivi_log("LOGIN", "Accesso autorizzato")
                    st.rerun()
                else: st.error("Credenziali non valide")
    with c2:
        st.subheader("Nuovo Profilo")
        with st.form("reg"):
            ru = st.text_input("Username scelto")
            rp = st.text_input("Password", type="password")
            rn, rc = st.text_input("Nome"), st.text_input("Cognome")
            rq = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
            if st.form_submit_button("REGISTRA"):
                if ru and rp:
                    db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (ru.lower().strip(), hash_pw(rp), rn, rc, rq), True)
                    st.success("Registrato!")
    st.stop()

# --- DATI UTENTE ---
u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"
oggi_iso = get_now_it().strftime("%Y-%m-%d")

# --- SIDEBAR ---
st.sidebar.markdown(f"<div class='sidebar-title'>REMS CONNECT</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-tag'>🟢 {u['nome'].upper()} {u['cognome'].upper()}<br><small>{u['ruolo']}</small></div>", unsafe_allow_html=True)

menu = st.sidebar.radio("NAVIGAZIONE PRINCIPALE", ["📊 Diario Clinico", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Reparti", "⚙️ Admin & Archivio"])

if st.sidebar.button("CHIUDI SESSIONE (LOGOUT)"):
    scrivi_log("LOGOUT", "Sessione terminata volontariamente")
    st.session_state.user_session = None
    st.rerun()

# --- 1. DIARIO CLINICO (SOLO PAZIENTI ATTIVI) ---
if menu == "📊 Diario Clinico":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO INTEGRATO</h2></div>", unsafe_allow_html=True)
    p_attivi = db_run("SELECT id, nome FROM pazienti WHERE stato=0 ORDER BY nome")
    if not p_attivi: st.info("Nessun paziente in carico al momento.")
    for pid, nome in p_attivi:
        with st.expander(f"📄 CARTELLA: {nome}"):
            c_f1, c_f2 = st.columns([2, 1])
            with c_f1:
                filtro_r = st.multiselect("Filtra Ruoli", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"], key=f"f_{pid}")
                q = "SELECT data, ruolo, op, nota FROM eventi WHERE id=?"
                p_q = [pid]
                if filtro_r:
                    q += f" AND ruolo IN ({','.join(['?']*len(filtro_r))})"
                    p_q.extend(filtro_r)
                eventi = db_run(q + " ORDER BY id_u DESC LIMIT 50", tuple(p_q))
                for d, r, o, nt in eventi:
                    role_cls = f"role-{r.lower().replace(' ', '')}"
                    st.markdown(f"<div class='card-diario {role_cls}'><b>{d} - {o} ({r})</b><br>{nt}</div>", unsafe_allow_html=True)
            with c_f2:
                st.markdown("### Info Rapide")
                letto = db_run("SELECT stanza_id, letto FROM assegnazioni WHERE p_id=?", (pid,))
                if letto: st.warning(f"📍 Posizione: Stanza {letto[0][0]} - Letto {letto[0][1]}")
                st.markdown("**Terapie in corso:**")
                for t in db_run("SELECT farmaco, dose FROM terapie WHERE p_id=?", (pid,)):
                    st.write(f"- {t[0]} ({t[1]})")

# --- 2. MODULO EQUIPE (ATTIVITÀ OPERATIVE) ---
elif menu == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO EQUIPE</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti WHERE stato=0 ORDER BY nome")
    if p_lista:
        p_sel_nome = st.selectbox("Seleziona Paziente per l'intervento", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel_nome][0]
        
        ruolo_effettivo = u['ruolo']
        if u['ruolo'] == "Admin": 
            ruolo_effettivo = st.selectbox("Modalità Simulazione (Admin):", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])

        # --- LOGICA PER RUOLO ---
        if ruolo_effettivo == "Psichiatra":
            t1, t2 = st.tabs(["💊 Prescrizioni", "🩺 Consegna Medica"])
            with t1:
                with st.form("f_pres"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dosaggio")
                    c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                    if st.form_submit_button("REGISTRA PRESCRIZIONE"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"➕ NUOVA TERAPIA: {f} {d}", "Psichiatra", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("f_cons"):
                    nota_med = st.text_area("Note Cliniche / Diagnostiche")
                    if st.form_submit_button("SALVA CONSEGNA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🩺 MED: {nota_med}", "Psichiatra", firma_op), True)
                        st.rerun()

        elif ruolo_effettivo == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 Somministrazione", "📊 Parametri", "📝 Diario"])
            with t1:
                terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                for tid, f, ds, m, p, n in terapie:
                    st.write(f"**{f}** - {ds}")
                    c = st.columns(3)
                    if m and c[0].button(f"Somm. MAT", key=f"m_{tid}"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMMINISTRATO: {f} (Mattina)", "Infermiere", firma_op), True); st.rerun()
                    if p and c[1].button(f"Somm. POM", key=f"p_{tid}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMMINISTRATO: {f} (Pomeriggio)", "Infermiere", firma_op), True); st.rerun()
                    if n and c[2].button(f"Somm. NOT", key=f"n_{tid}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMMINISTRATO: {f} (Notte)", "Infermiere", firma_op), True); st.rerun()
            with t2:
                with st.form("f_par"):
                    pa = st.text_input("Pressione"); fc = st.text_input("FC"); sat = st.text_input("SatO2")
                    if st.form_submit_button("REGISTRA PARAMETRI"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"📊 PARAMETRI: PA {pa}, FC {fc}, Sat {sat}", "Infermiere", firma_op), True); st.rerun()
            with t3:
                with st.form("f_inf"):
                    txt = st.text_area("Nota Infermieristica")
                    if st.form_submit_button("AGGIUNGI NOTA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), txt, "Infermiere", firma_op), True); st.rerun()

        elif ruolo_effettivo == "Educatore":
            t1, t2 = st.tabs(["💰 Gestione Cassa", "🎨 Attività"])
            with t1:
                movimenti = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in movimenti)
                st.markdown(f"<div class='cassa-saldo'>{saldo:.2f} €</div>", unsafe_allow_html=True)
                with st.form("f_cassa"):
                    tipo = st.selectbox("Tipo", ["ENTRATA", "USCITA"]); imp = st.number_input("Importo €", min_value=0.0); cau = st.text_input("Causale")
                    if st.form_submit_button("REGISTRA MOVIMENTO"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, oggi_iso, cau, imp, tipo, firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"💰 {tipo}: {imp}€ - {cau}", "Educatore", firma_op), True); st.rerun()
            with t2:
                with st.form("f_edu"):
                    not_edu = st.text_area("Relazione Educativa")
                    if st.form_submit_button("SALVA ATTIVITÀ"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🎨 {not_edu}", "Educatore", firma_op), True); st.rerun()

        elif ruolo_effettivo == "OSS":
            with st.form("f_oss"):
                mans = st.multiselect("Interventi:", ["Igiene Personale", "Cambio Biancheria", "Pulizia Camera", "Supporto Pasto"])
                oss_nota = st.text_area("Note aggiuntive")
                if st.form_submit_button("REGISTRA ATTIVITÀ OSS"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🧹 {', '.join(mans)} | {oss_nota}", "OSS", firma_op), True); st.rerun()

        elif ruolo_effettivo == "OPSI":
            with st.form("f_opsi"):
                crit = st.selectbox("Livello di criticità ambientale", ["NORMALE", "TENSIONE", "CRITICITÀ ALTA"])
                opsi_nota = st.text_area("Rapporto di vigilanza")
                if st.form_submit_button("INVIA RAPPORTO"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🛡️ VIGILANZA [{crit}]: {opsi_nota}", "OPSI", firma_op), True); st.rerun()

# --- 3. AGENDA DINAMICA ---
elif menu == "📅 Agenda Dinamica":
    st.markdown("<div class='section-banner'><h2>AGENDA DINAMICA SCADENZE</h2></div>", unsafe_allow_html=True)
    
    # Navigazione Mese
    c_nav = st.columns([1,2,1])
    if c_nav[0].button("PREVIOUS"):
        st.session_state.cal_month -= 1
        if st.session_state.cal_month < 1: st.session_state.cal_month=12; st.session_state.cal_year-=1
        st.rerun()
    if c_nav[2].button("NEXT"):
        st.session_state.cal_month += 1
        if st.session_state.cal_month > 12: st.session_state.cal_month=1; st.session_state.cal_year+=1
        st.rerun()
    c_nav[1].markdown(f"<h2 style='text-align:center'>{st.session_state.cal_month}/{st.session_state.cal_year}</h2>", unsafe_allow_html=True)

    col_sx, col_dx = st.columns([3, 1])
    
    with col_sx:
        # Costruzione Calendario HTML
        cal = calendar.Calendar(firstweekday=0)
        mese_giorni = cal.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month)
        
        # Recupero appuntamenti del mese
        inizio_m = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-01"
        fine_m = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-31"
        ev_mese = db_run("SELECT a.data, p.nome, a.ora FROM appuntamenti a JOIN pazienti p ON a.p_id=p.id WHERE a.data BETWEEN ? AND ? AND a.stato='PROGRAMMATO'", (inizio_m, fine_m))
        
        mappa = {}
        for d_e, p_e, o_e in ev_mese:
            gg = int(d_e.split("-")[2])
            if gg not in mappa: mappa[gg] = []
            mappa[gg].append(f"{o_e} - {p_e}")

        html = "<table class='cal-table'><tr><th>LUN</th><th>MAR</th><th>MER</th><th>GIO</th><th>VEN</th><th>SAB</th><th>DOM</th></tr>"
        for week in mese_giorni:
            html += "<tr>"
            for day in week:
                if day == 0: html += "<td style='background:#f1f5f9'></td>"
                else:
                    is_today = "today-cell" if (day == get_now_it().day and st.session_state.cal_month == get_now_it().month) else ""
                    ev_html = "".join([f"<div class='event-tag'>{x}</div>" for x in mappa.get(day, [])])
                    html += f"<td class='{is_today}'><b>{day}</b><br>{ev_html}</td>"
            html += "</tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)

    with col_dx:
        st.subheader("➕ Inserisci")
        with st.form("f_app"):
            p_ids = db_run("SELECT id, nome FROM pazienti WHERE stato=0")
            p_n = st.selectbox("Paziente", [x[1] for x in p_ids])
            sel_pid = [x[0] for x in p_ids if x[1]==p_n][0]
            d_app = st.date_input("Data"); o_app = st.time_input("Ora")
            t_app = st.selectbox("Tipo", ["Uscita", "Tribunale", "Visita Specialistica", "Colloquio"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, stato, autore, tipo_evento) VALUES (?,?,?,?,?,?)", 
                       (sel_pid, str(d_app), str(o_app)[:5], "PROGRAMMATO", firma_op, t_app), True)
                scrivi_log("AGENDA", f"Nuovo appuntamento per {p_n}")
                st.rerun()
        
        st.divider()
        st.subheader("📋 Scadenze")
        scadenze = db_run("SELECT a.id_u, a.data, a.ora, p.nome FROM appuntamenti a JOIN pazienti p ON a.p_id=p.id WHERE a.stato='PROGRAMMATO' ORDER BY a.data LIMIT 10")
        for aid, ad, ao, ap in scadenze:
            st.write(f"**{ad} {ao}** - {ap}")
            c_a1, c_a2 = st.columns(2)
            if c_a1.button("FATTO", key=f"ok_{aid}"):
                db_run("UPDATE appuntamenti SET stato='COMPLETATO' WHERE id_u=?", (aid,), True)
                st.rerun()
            if c_a2.button("ELIMINA", key=f"del_a_{aid}"):
                scrivi_log("CANCELLAZIONE AGENDA", f"ID Appuntamento {aid} rimosso da {firma_op}")
                db_run("DELETE FROM appuntamenti WHERE id_u=?", (aid,), True)
                st.rerun()

# --- 4. MAPPA REPARTI ---
elif menu == "🗺️ Mappa Reparti":
    st.markdown("<div class='section-banner'><h2>DISPOSIZIONE POSTI LETTO</h2></div>", unsafe_allow_html=True)
    
    stanze = db_run("SELECT id, reparto, tipo FROM stanze")
    pazienti_letti = db_run("SELECT p.id, p.nome, a.stanza_id, a.letto FROM pazienti p JOIN assegnazioni a ON p.id=a.p_id WHERE p.stato=0")
    
    mappa_letti = {s[0]: {"rep": s[1], "tipo": s[2], "l1": "Libero", "l2": "Libero"} for s in stanze}
    for pid, pnome, sid, letto in pazienti_letti:
        if sid in mappa_letti:
            mappa_letti[sid][f"l{letto}"] = pnome

    # Visualizzazione Reparto A e B
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Reparto A")
        for sid, info in mappa_letti.items():
            if info['rep'] == 'A':
                with st.expander(f"Stanza {sid} ({info['tipo']})"):
                    st.write(f"L1: **{info['l1']}**")
                    st.write(f"L2: **{info['l2']}**")
    with col_b:
        st.subheader("Reparto B")
        for sid, info in mappa_letti.items():
            if info['rep'] == 'B':
                with st.expander(f"Stanza {sid} ({info['tipo']})"):
                    st.write(f"L1: **{info['l1']}**")
                    st.write(f"L2: **{info['l2']}**")
    
    st.divider()
    st.subheader("🔄 Sposta Paziente")
    with st.form("f_move"):
        p_move = db_run("SELECT id, nome FROM pazienti WHERE stato=0")
        p_sel = st.selectbox("Paziente da spostare", [x[1] for x in p_move])
        sid_dest = st.selectbox("Stanza Destinazione", [x[0] for x in stanze])
        l_dest = st.selectbox("Letto", [1, 2])
        if st.form_submit_button("CONFERMA TRASFERIMENTO"):
            pid_m = [x[0] for x in p_move if x[1]==p_sel][0]
            db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid_m,), True)
            db_run("INSERT INTO assegnazioni (p_id, stanza_id, letto, data_ass) VALUES (?,?,?,?)", (pid_m, sid_dest, l_dest, oggi_iso), True)
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid_m, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🔄 SPOSTAMENTO: Trasferito in Stanza {sid_dest} Letto {l_dest}", "Sistema", "Automatico"), True)
            scrivi_log("MOVIMENTO", f"Paziente {p_sel} spostato in {sid_dest}")
            st.rerun()

# --- 5. ADMIN & ARCHIVIO ---
elif menu == "⚙️ Admin & Archivio":
    st.markdown("<div class='section-banner'><h2>PANNELLO DI CONTROLLO AMMINISTRATIVO</h2></div>", unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(["👥 Gestione Pazienti", "📦 Archivio Storico", "📜 Log Audit", "👤 Utenti"])
    
    with tab1:
        st.subheader("Aggiungi Nuovo Paziente")
        with st.form("f_new_p"):
            n_p = st.text_input("Nome e Cognome Paziente")
            if st.form_submit_button("REGISTRA INGRESSO"):
                db_run("INSERT INTO pazienti (nome, stato) VALUES (?, 0)", (n_p.upper(),), True)
                scrivi_log("INGRESSO", f"Nuovo paziente registrato: {n_p}")
                st.rerun()
        
        st.divider()
        st.subheader("Pazienti Attivi")
        p_attivi = db_run("SELECT id, nome FROM pazienti WHERE stato=0")
        for pid, nome in p_attivi:
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"**{nome}**")
            if c2.button("ARCHIVIA (DIMESSO)", key=f"arch_{pid}"):
                db_run("UPDATE pazienti SET stato=1 WHERE id=?", (pid,), True)
                db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid,), True)
                scrivi_log("DIMISSIONE", f"Paziente {nome} archiviato")
                st.rerun()

    with tab2:
        st.subheader("Pazienti Dimessi (Sola Lettura)")
        p_arch = db_run("SELECT id, nome FROM pazienti WHERE stato=1")
        for pid, nome in p_arch:
            with st.expander(f"📦 {nome}"):
                st.write("Dati storici conservati:")
                if st.button("RIAMMETTI IN STRUTTURA", key=f"ri_{pid}"):
                    db_run("UPDATE pazienti SET stato=0 WHERE id=?", (pid,), True)
                    scrivi_log("RIAMMISSIONE", f"Paziente {nome} riattivato")
                    st.rerun()
                st.write(db_run("SELECT data, nota, op FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,)))

    with tab3:
        st.subheader("Registro delle Operazioni (Audit Log)")
        st.caption("Ogni azione sensibile dell'Admin e degli utenti viene tracciata qui.")
        logs = db_run("SELECT data_ora, utente, azione, dettaglio FROM logs_sistema ORDER BY id_log DESC LIMIT 200")
        df_logs = pd.DataFrame(logs, columns=["Timestamp", "Operatore", "Azione", "Dettaglio"])
        st.dataframe(df_logs, use_container_width=True)

    with tab4:
        st.subheader("Gestione Accessi Personale")
        utenti = db_run("SELECT user, nome, cognome, qualifica FROM utenti")
        for u_id, u_n, u_c, u_q in utenti:
            st.write(f"{u_n} {u_c} - **{u_q}** (User: {u_id})")
            if u_id != 'admin' and st.button("DISATTIVA ACCOUNT", key=f"del_u_{u_id}"):
                db_run("DELETE FROM utenti WHERE user=?", (u_id,), True)
                scrivi_log("GESTIONE UTENTI", f"Account {u_id} rimosso")
                st.rerun()
