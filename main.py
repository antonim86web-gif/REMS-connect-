import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar

# --- CONFIGURAZIONE DATABASE E SICUREZZA ---
DB_NAME = "rems_connect_v32_total.db"

def hash_pw(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

def get_now_it():
    # Gestione fuso orario italiano
    return datetime.now(timezone.utc) + timedelta(hours=2)

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        try:
            # Creazione Tabelle Integrali
            cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, stato INTEGER DEFAULT 0)")
            cur.execute("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY AUTOINCREMENT, id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS cassa (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT, tipo_evento TEXT, mezzo TEXT, accompagnatore TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS logs_sistema (id_log INTEGER PRIMARY KEY AUTOINCREMENT, data_ora TEXT, utente TEXT, azione TEXT, dettaglio TEXT)")
            
            # Setup Iniziale Admin e Stanze
            if cur.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
                cur.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("perito2026"), "SUPER", "USER", "Admin"))
            
            if cur.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
                for i in range(1, 7): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"A{i}", "A", "ISOLAMENTO" if i==6 else "STANDARD"))
                for i in range(1, 11): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"B{i}", "B", "ISOLAMENTO" if i==10 else "STANDARD"))
            
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore Critico Database: {e}")
            return []

def scrivi_log(azione, dettaglio):
    user_log = st.session_state.user_session['uid'] if st.session_state.user_session else "Sistema"
    db_run("INSERT INTO logs_sistema (data_ora, utente, azione, dettaglio) VALUES (?,?,?,?)", 
           (get_now_it().strftime("%d/%m/%Y %H:%M:%S"), user_log, azione, dettaglio), True)

# --- INTERFACCIA ELITE ---
st.set_page_config(page_title="REMS Connect v32.0 - INTEGRAL", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0f172a !important; min-width: 280px; }
    .sidebar-title { color: #38bdf8; font-size: 1.8rem; font-weight: 800; text-align: center; padding: 20px; border-bottom: 2px solid #1e293b; }
    .user-box { background: #1e293b; padding: 15px; border-radius: 10px; margin: 10px; border-left: 5px solid #38bdf8; }
    .section-banner { background: linear-gradient(90deg, #1e3a8a, #1e40af); color: white; padding: 25px; border-radius: 15px; margin-bottom: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    .card-diario { background: #ffffff; border: 1px solid #e2e8f0; padding: 15px; border-radius: 10px; margin-bottom: 8px; border-left: 8px solid #64748b; }
    .role-psichiatra { border-left-color: #ef4444; background: #fef2f2; }
    .role-infermiere { border-left-color: #3b82f6; background: #eff6ff; }
    .role-oss { border-left-color: #f59e0b; background: #fffbeb; }
    .role-psicologo { border-left-color: #a855f7; background: #faf5ff; }
    .cal-table { width:100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; }
    .cal-table th { background: #1e293b; color: white; padding: 10px; }
    .cal-table td { border: 1px solid #e2e8f0; height: 100px; vertical-align: top; padding: 5px; }
    .event-tag { font-size: 0.7rem; background: #3b82f6; color: white; padding: 2px 4px; border-radius: 3px; margin-top: 2px; }
    .saldo-box { background: #0f172a; color: #10b981; padding: 20px; border-radius: 12px; text-align: center; font-size: 2.2rem; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# --- GESTIONE SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if 'month' not in st.session_state: st.session_state.month = get_now_it().month
if 'year' not in st.session_state: st.session_state.year = get_now_it().year

# --- LOGIN PAGE ---
if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h1>🏥 REMS CONNECT ELITE PRO v32.0</h1><p>Sistema Integrato Gestione Dati Sanitari</p></div>", unsafe_allow_html=True)
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.subheader("🔐 Accesso Operatore")
        with st.form("login_form"):
            u_in = st.text_input("Username").lower().strip()
            p_in = st.text_input("Password", type="password")
            if st.form_submit_button("ENTRA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res:
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_in}
                    scrivi_log("LOGIN", "Autenticazione riuscita")
                    st.rerun()
                else: st.error("Accesso Negato")
    with col_l2:
        st.subheader("📝 Registrazione")
        with st.form("reg_form"):
            nu = st.text_input("Nuovo User"); np = st.text_input("Password", type="password")
            nn = st.text_input("Nome"); nc = st.text_input("Cognome")
            nq = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
            if st.form_submit_button("REGISTRA"):
                if nu and np:
                    db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu.lower().strip(), hash_pw(np), nn, nc, nq), True)
                    st.success("Operatore Registrato")
    st.stop()

# --- DATI UTENTE ATTIVO ---
u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR NAVIGAZIONE ---
st.sidebar.markdown("<div class='sidebar-title'>REMS v32</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-box'>👤 {u['nome']} {u['cognome']}<br><small>{u['ruolo']}</small></div>", unsafe_allow_html=True)

nav = st.sidebar.radio("MENU PRINCIPALE", ["📊 Diario Clinico", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Reparto", "⚙️ Admin & Log Audit"])

if st.sidebar.button("LOGOUT (Esci dal sistema)"):
    scrivi_log("LOGOUT", "Uscita volontaria")
    st.session_state.user_session = None
    st.rerun()

# --- 1. DIARIO CLINICO INTEGRALE ---
if nav == "📊 Diario Clinico":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO MULTIDISCIPLINARE</h2></div>", unsafe_allow_html=True)
    p_attivi = db_run("SELECT id, nome FROM pazienti WHERE stato=0 ORDER BY nome")
    
    if not p_attivi:
        st.info("Nessun paziente attualmente in forza.")
    
    for pid, nome in p_attivi:
        with st.expander(f"📁 CARTELLA CLINICA: {nome}"):
            c_d1, c_d2 = st.columns([2, 1])
            with c_d1:
                st.subheader("Cronologia Eventi")
                filtro = st.multiselect("Filtra per Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"], key=f"f_{pid}")
                
                query_ev = "SELECT data, ruolo, op, nota FROM eventi WHERE id=?"
                params_ev = [pid]
                if filtro:
                    query_ev += f" AND ruolo IN ({','.join(['?']*len(filtro))})"
                    params_ev.extend(filtro)
                
                eventi = db_run(query_ev + " ORDER BY id_u DESC LIMIT 50", tuple(params_ev))
                for d, r, o, nt in eventi:
                    r_class = f"role-{r.lower().replace(' ', '')}"
                    st.markdown(f"<div class='card-diario {r_class}'><b>{d} | {o} ({r})</b><br>{nt}</div>", unsafe_allow_html=True)
            
            with c_d2:
                st.subheader("Stato Attuale")
                letto_info = db_run("SELECT stanza_id, letto FROM assegnazioni WHERE p_id=?", (pid,))
                if letto_info: st.success(f"📍 Posizione: Stanza {letto_info[0][0]} - Letto {letto_info[0][1]}")
                
                st.markdown("**💊 Terapie Attive:**")
                ter_att = db_run("SELECT farmaco, dose FROM terapie WHERE p_id=?", (pid,))
                for f, ds in ter_att: st.write(f"- {f} ({ds})")
                
                mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (pid,))
                saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
                st.markdown(f"**💰 Saldo Cassa:** {saldo:.2f} €")

# --- 2. MODULO EQUIPE (FUNZIONI OPERATIVE) ---
elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO MULTIPROFESSIONALE</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti WHERE stato=0 ORDER BY nome")
    
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        
        # Switch Ruolo (Admin può simulare tutti)
        ruolo_uso = u['ruolo']
        if u['ruolo'] == "Admin": ruolo_uso = st.radio("Simula Ruolo:", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"], horizontal=True)

        st.divider()
        
        # MODULO PSICHIATRA
        if ruolo_uso == "Psichiatra":
            t1, t2 = st.tabs(["Prescrizione Farmaci", "Relazione Medica"])
            with t1:
                with st.form("f_psi_t"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                    if st.form_submit_button("INSERISCI TERAPIA"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"➕ NUOVA PRESCRIZIONE: {f} {d}", "Psichiatra", firma_op), True)
                        st.success("Terapia inserita"); st.rerun()
            with t2:
                with st.form("f_psi_n"):
                    nota = st.text_area("Nota Clinica")
                    if st.form_submit_button("SALVA NOTA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), nota, "Psichiatra", firma_op), True)
                        st.rerun()

        # MODULO INFERMIERE
        elif ruolo_uso == "Infermiere":
            t1, t2, t3 = st.tabs(["Somministrazione", "Parametri Vitali", "Consegne"])
            with t1:
                ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                for tid, f, ds, mat, pom, nott in ter:
                    st.write(f"**{f}** ({ds})")
                    c = st.columns(3)
                    if mat and c[0].button(f"MAT", key=f"m_{tid}"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ Somministrato: {f} (MAT)", "Infermiere", firma_op), True); st.rerun()
                    if pom and c[1].button(f"POM", key=f"p_{tid}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ Somministrato: {f} (POM)", "Infermiere", firma_op), True); st.rerun()
                    if nott and c[2].button(f"NOT", key=f"n_{tid}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ Somministrato: {f} (NOT)", "Infermiere", firma_op), True); st.rerun()
            with t2:
                with st.form("f_par"):
                    pa = st.text_input("Pressione"); fc = st.text_input("Frequenza"); sat = st.text_input("Saturazione")
                    if st.form_submit_button("SALVA PARAMETRI"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"📊 Parametri: PA {pa} | FC {fc} | Sat {sat}", "Infermiere", firma_op), True); st.rerun()
            with t3:
                with st.form("f_inf_n"):
                    nota = st.text_area("Nota Infermieristica")
                    if st.form_submit_button("SALVA CONSEGNA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), nota, "Infermiere", firma_op), True); st.rerun()

        # MODULO EDUCATORE / ASSISTENTE SOCIALE
        elif ruolo_uso in ["Educatore", "Assistente Sociale"]:
            t1, t2 = st.tabs(["Gestione Cassa", "Relazione Sociale/Educativa"])
            with t1:
                mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
                st.markdown(f"<div class='saldo-box'>{saldo:.2f} €</div>", unsafe_allow_html=True)
                with st.form("f_cas"):
                    tipo = st.selectbox("Tipo", ["USCITA", "ENTRATA"]); imp = st.number_input("Somma €", min_value=0.0); cau = st.text_input("Causale")
                    if st.form_submit_button("REGISTRA MOVIMENTO"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, get_now_it().strftime("%Y-%m-%d"), cau, imp, tipo, firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"💰 {tipo}: {imp}€ - {cau}", ruolo_uso, firma_op), True); st.rerun()
            with t2:
                with st.form("f_edu_n"):
                    nota = st.text_area(f"Relazione {ruolo_uso}")
                    if st.form_submit_button("SALVA RELAZIONE"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), nota, ruolo_uso, firma_op), True); st.rerun()

        # MODULO OSS
        elif ruolo_uso == "OSS":
            with st.form("f_oss"):
                cat = st.multiselect("Attività:", ["Igiene", "Pasto", "Vestizione", "Pulizia Stanza"])
                nota = st.text_area("Note OSS")
                if st.form_submit_button("SALVA ATTIVITÀ"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🧹 {', '.join(cat)} | {nota}", "OSS", firma_op), True); st.rerun()

        # MODULO OPSI
        elif ruolo_uso == "OPSI":
            with st.form("f_opsi"):
                stat = st.selectbox("Clima Ambientale", ["Tranquillo", "Tensione", "Agitazione", "Pericolo"])
                nota = st.text_area("Rapporto Vigilanza")
                if st.form_submit_button("INVIA RAPPORTO"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🛡️ VIGILANZA [{stat}]: {nota}", "OPSI", firma_op), True); st.rerun()

# --- 3. AGENDA DINAMICA ---
elif nav == "📅 Agenda Dinamica":
    st.markdown("<div class='section-banner'><h2>CALENDARIO SCADENZE E USCITE</h2></div>", unsafe_allow_html=True)
    
    # Navigazione Mese
    c_cal1, c_cal2, c_cal3 = st.columns([1,2,1])
    if c_cal1.button("⬅️ Mese Precedente"):
        st.session_state.month -= 1
        if st.session_state.month < 1: st.session_state.month=12; st.session_state.year-=1
        st.rerun()
    if c_cal3.button("Mese Successivo ➡️"):
        st.session_state.month += 1
        if st.session_state.month > 12: st.session_state.month=1; st.session_state.year+=1
        st.rerun()
    c_cal2.markdown(f"<h3 style='text-align:center'>{st.session_state.month} / {st.session_state.year}</h3>", unsafe_allow_html=True)

    col_a1, col_a2 = st.columns([3, 1])
    
    with col_a1:
        cal = calendar.Calendar(firstweekday=0)
        days = cal.monthdayscalendar(st.session_state.year, st.session_state.month)
        
        # Recupero appuntamenti
        data_ini = f"{st.session_state.year}-{st.session_state.month:02d}-01"
        data_fin = f"{st.session_state.year}-{st.session_state.month:02d}-31"
        apps = db_run("SELECT a.data, p.nome, a.ora FROM appuntamenti a JOIN pazienti p ON a.p_id=p.id WHERE a.data BETWEEN ? AND ? AND a.stato='ATTIVO'", (data_ini, data_fin))
        
        mappa = {}
        for d, p, o in apps:
            g = int(d.split("-")[2])
            if g not in mappa: mappa[g] = []
            mappa[g].append(f"{o} {p}")

        html = "<table class='cal-table'><tr><th>LUN</th><th>MAR</th><th>MER</th><th>GIO</th><th>VEN</th><th>SAB</th><th>DOM</th></tr>"
        for week in days:
            html += "<tr>"
            for d in week:
                if d == 0: html += "<td style='background:#f1f5f9'></td>"
                else:
                    evs = "".join([f"<div class='event-tag'>{x}</div>" for x in mappa.get(d, [])])
                    html += f"<td><b>{d}</b><br>{evs}</td>"
            html += "</tr>"
        st.markdown(html + "</table>", unsafe_allow_html=True)

    with col_a2:
        st.subheader("➕ Nuovo Impegno")
        with st.form("new_app"):
            p_ids = db_run("SELECT id, nome FROM pazienti WHERE stato=0")
            p_n = st.selectbox("Paziente", [x[1] for x in p_ids])
            sel_pid = [x[0] for x in p_ids if x[1]==p_n][0]
            d_app = st.date_input("Giorno"); o_app = st.time_input("Ora")
            t_app = st.selectbox("Tipo", ["Colloquio", "Tribunale", "Visita", "Permesso"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, stato, autore, tipo_evento) VALUES (?,?,?,?,?,?)", (sel_pid, str(d_app), str(o_app)[:5], "ATTIVO", firma_op, t_app), True)
                scrivi_log("AGENDA", f"Inserito appuntamento per {p_n}")
                st.rerun()

# --- 4. MAPPA REPARTO ---
elif nav == "🗺️ Mappa Reparto":
    st.markdown("<div class='section-banner'><h2>GESTIONE POSTI LETTO E STANZE</h2></div>", unsafe_allow_html=True)
    
    # Recupero dati stanze e occupazione
    stanze = db_run("SELECT id, reparto, tipo FROM stanze")
    occ = db_run("SELECT a.stanza_id, a.letto, p.nome, p.id FROM assegnazioni a JOIN pazienti p ON a.p_id=p.id WHERE p.stato=0")
    
    mappa = {s[0]: {"rep": s[1], "tipo": s[2], "l1": "LIBERO", "l2": "LIBERO"} for s in stanze}
    for sid, letto, pnome, pid in occ:
        if sid in mappa: mappa[sid][f"l{letto}"] = pnome

    c_rep1, c_rep2 = st.columns(2)
    with c_rep1:
        st.subheader("REPARTO A")
        for sid, info in mappa.items():
            if info['rep'] == "A":
                with st.expander(f"Stanza {sid} ({info['tipo']})"):
                    st.write(f"Letto 1: **{info['l1']}**")
                    st.write(f"Letto 2: **{info['l2']}**")
    with c_rep2:
        st.subheader("REPARTO B")
        for sid, info in mappa.items():
            if info['rep'] == "B":
                with st.expander(f"Stanza {sid} ({info['tipo']})"):
                    st.write(f"Letto 1: **{info['l1']}**")
                    st.write(f"Letto 2: **{info['l2']}**")
    
    st.divider()
    st.subheader("🔄 Trasferimento Paziente")
    with st.form("move_p"):
        p_mov = db_run("SELECT id, nome FROM pazienti WHERE stato=0")
        p_sel = st.selectbox("Paziente", [x[1] for x in p_mov])
        st_dest = st.selectbox("Destinazione", [x[0] for x in stanze])
        l_dest = st.selectbox("Letto", [1, 2])
        if st.form_submit_button("ESEGUI SPOSTAMENTO"):
            pid_m = [x[0] for x in p_mov if x[1]==p_sel][0]
            db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid_m,), True)
            db_run("INSERT INTO assegnazioni (p_id, stanza_id, letto, data_ass) VALUES (?,?,?,?)", (pid_m, st_dest, l_dest, get_now_it().strftime("%Y-%m-%d")), True)
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid_m, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🔄 Trasferito in Stanza {st_dest} - Letto {l_dest}", "Sistema", "Automatico"), True)
            scrivi_log("SPOSTAMENTO", f"Paziente {p_sel} mosso in {st_dest}")
            st.rerun()

# --- 5. ADMIN & LOG AUDIT (LA SEZIONE CHE CERCAVI) ---
elif nav == "⚙️ Admin & Log Audit":
    st.markdown("<div class='section-banner'><h2>SISTEMA DI CONTROLLO E ARCHIVIAZIONE</h2></div>", unsafe_allow_html=True)
    
    t1, t2, t3, t4 = st.tabs(["👥 Gestione Pazienti", "📦 Archivio Storico", "📜 LOG AUDIT (TRACCIABILITÀ)", "👤 Personale"])
    
    with t1:
        st.subheader("Ingresso Nuovo Paziente")
        with st.form("new_p"):
            nome_p = st.text_input("Nome e Cognome Paziente")
            if st.form_submit_button("REGISTRA INGRESSO"):
                db_run("INSERT INTO pazienti (nome, stato) VALUES (?, 0)", (nome_p.upper(),), True)
                scrivi_log("INGRESSO", f"Nuovo paziente: {nome_p}")
                st.rerun()
        
        st.divider()
        st.subheader("Lista Pazienti in Carico")
        p_att = db_run("SELECT id, nome FROM pazienti WHERE stato=0")
        for pid, nome in p_att:
            col1, col2 = st.columns([0.8, 0.2])
            col1.write(f"🆔 {pid} | **{nome}**")
            if col2.button("DIMETTI", key=f"dim_{pid}"):
                db_run("UPDATE pazienti SET stato=1 WHERE id=?", (pid,), True)
                db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid,), True)
                scrivi_log("DIMISSIONE", f"Paziente {nome} archiviato")
                st.rerun()

    with t2:
        st.subheader("Archivio Storico Pazienti Dimessi")
        p_arc = db_run("SELECT id, nome FROM pazienti WHERE stato=1")
        for pid, nome in p_arc:
            with st.expander(f"📦 {nome}"):
                if st.button("RIAMMETTI IN REPARTO", key=f"ri_{pid}"):
                    db_run("UPDATE pazienti SET stato=0 WHERE id=?", (pid,), True)
                    scrivi_log("RIAMMISSIONE", f"Paziente {nome} riattivato")
                    st.rerun()
                # Visualizzazione in sola lettura
                st.write(db_run("SELECT data, nota, op FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,)))

    with t3:
        st.subheader("📜 REGISTRO TRACCIABILITÀ (AUDIT LOG)")
        st.warning("ATTENZIONE: Questo registro è immodificabile e traccia ogni attività del sistema per scopi legali.")
        
        # Questa è la tabella che cercavi: mostra tutto il contenuto della tabella logs_sistema
        logs_dati = db_run("SELECT data_ora, utente, azione, dettaglio FROM logs_sistema ORDER BY id_log DESC LIMIT 500")
        if logs_dati:
            df_logs = pd.DataFrame(logs_dati, columns=["Data/Ora", "Operatore", "Azione", "Dettaglio Operazione"])
            st.table(df_logs) # Utilizzo st.table per una visualizzazione fissa e professionale
        else:
            st.info("Nessun log presente nel database.")

    with t4:
        st.subheader("Gestione Operatori")
        op_lista = db_run("SELECT user, nome, cognome, qualifica FROM utenti")
        for uid, un, uc, uq in op_lista:
            st.write(f"{un} {uc} | **{uq}** (ID: {uid})")
            if uid != "admin" and st.button("ELIMINA ACCOUNT", key=f"del_u_{uid}"):
                db_run("DELETE FROM utenti WHERE user=?", (uid,), True)
                scrivi_log("ADMIN", f"Eliminato account operatore: {uid}")
                st.rerun()
