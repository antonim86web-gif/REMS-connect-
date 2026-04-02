import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar

# --- CONFIGURAZIONE DATABASE INTEGRALE E STRUTTURE DATI ---
DB_NAME = "rems_elite_v34_final.db"

def hash_pw(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

def get_now_it():
    # Gestione fuso orario italiano UTC+2
    return datetime.now(timezone.utc) + timedelta(hours=2)

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        try:
            # Creazione di tutte le tabelle previste senza omissioni
            cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, stato INTEGER DEFAULT 0)")
            cur.execute("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY AUTOINCREMENT, id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS cassa (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT, tipo_evento TEXT, mezzo TEXT, accompagnatore TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS logs_sistema (id_log INTEGER PRIMARY KEY AUTOINCREMENT, data_ora TEXT, utente TEXT, azione TEXT, dettaglio TEXT)")
            
            # Setup Iniziale Account Master
            if cur.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
                cur.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("perito2026"), "SUPER", "USER", "Admin"))
            
            # Setup Stanze Reparti A e B
            if cur.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
                for i in range(1, 7): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"A{i}", "A", "ISOLAMENTO" if i==6 else "STANDARD"))
                for i in range(1, 11): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"B{i}", "B", "ISOLAMENTO" if i==10 else "STANDARD"))
            
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"⚠️ ERRORE CRITICO DATABASE: {e}")
            return []

def scrivi_log(azione, dettaglio):
    user_log = st.session_state.user_session['uid'] if st.session_state.user_session else "SISTEMA"
    db_run("INSERT INTO logs_sistema (data_ora, utente, azione, dettaglio) VALUES (?,?,?,?)", 
           (get_now_it().strftime("%d/%m/%Y %H:%M:%S"), user_log, azione, dettaglio), True)

# --- ENGINE INTERFACCIA ELITE (CSS ORIGINALE NON SEMPLIFICATO) ---
st.set_page_config(page_title="REMS CONNECT ELITE v34", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;800&display=swap');
    * { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* Sidebar Stile Notte */
    [data-testid="stSidebar"] { background-color: #010409 !important; border-right: 2px solid #30363d; min-width: 320px !important; }
    .sidebar-header { color: #58a6ff; font-size: 2.2rem; font-weight: 800; text-align: center; padding: 30px 10px; text-transform: uppercase; letter-spacing: 2px; }
    .user-profile { background: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; margin: 10px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
    
    /* Banner Sezioni con Gradienti */
    .main-banner { background: linear-gradient(135deg, #0969da 0%, #1e4eb8 100%); color: white; padding: 50px; border-radius: 25px; margin-bottom: 35px; text-align: center; box-shadow: 0 15px 35px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); }
    
    /* Diario Clinico Card */
    .card-diario { background: white; padding: 25px; border-radius: 18px; margin-bottom: 15px; border-left: 12px solid #8b949e; box-shadow: 0 5px 15px rgba(0,0,0,0.05); transition: transform 0.2s; }
    .card-diario:hover { transform: scale(1.01); }
    .role-psichiatra { border-left-color: #da3633 !important; background-color: #fff5f5 !important; }
    .role-infermiere { border-left-color: #0969da !important; background-color: #f0f7ff !important; }
    .role-educatore { border-left-color: #238636 !important; background-color: #f0fff4 !important; }
    .role-oss { border-left-color: #d29922 !important; background-color: #fffdf2 !important; }
    .role-psicologo { border-left-color: #8957e5 !important; background-color: #f8f0ff !important; }
    .role-sociale { border-left-color: #0ea5e9 !important; background-color: #f0f9ff !important; }
    
    /* Calendario Griglia */
    .cal-grid { width:100%; border-collapse: separate; border-spacing: 8px; }
    .cal-head { background: #0d1117; color: #58a6ff; padding: 15px; border-radius: 10px; font-weight: 800; text-align: center; }
    .cal-day { background: #ffffff; border: 1px solid #d0d7de; height: 130px; vertical-align: top; padding: 12px; border-radius: 15px; transition: all 0.3s; }
    .cal-day:hover { border-color: #0969da; box-shadow: 0 0 20px rgba(9,105,218,0.15); }
    .today-marker { background: #f6f8fa !important; border: 3px solid #0969da !important; }
    .ev-tag { background: #0969da; color: white; padding: 5px 10px; border-radius: 8px; font-size: 0.75rem; font-weight: 600; margin-top: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    
    /* Cassa e Pulsanti */
    .saldo-display { background: #0d1117; color: #39d353; padding: 35px; border-radius: 25px; text-align: center; font-size: 3rem; font-weight: 800; border: 2px solid #30363d; margin: 20px 0; }
    .stButton>button { border-radius: 15px !important; font-weight: 800 !important; letter-spacing: 1px !important; text-transform: uppercase !important; height: 3.5em !important; box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important; }
</style>
""", unsafe_allow_html=True)

# --- LOGICA DI SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if 'cur_m' not in st.session_state: st.session_state.cur_m = get_now_it().month
if 'cur_y' not in st.session_state: st.session_state.cur_y = get_now_it().year

# --- PAGINA DI LOGIN ---
if not st.session_state.user_session:
    st.markdown("<div class='main-banner'><h1>🏥 REMS CONNECT ELITE PRO</h1><p>Versione 34.0 Integral - Accesso Riservato Personale Sanitario</p></div>", unsafe_allow_html=True)
    col_log1, col_log2 = st.columns(2)
    with col_log1:
        st.markdown("### 🔐 Autenticazione")
        with st.form("login_sys"):
            u_in = st.text_input("Utente").lower().strip()
            p_in = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI AL SISTEMA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res:
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_in}
                    scrivi_log("LOGIN", "Accesso operatore riuscito")
                    st.rerun()
                else: st.error("Credenziali Errate")
    with col_log2:
        st.markdown("### 📝 Registrazione Nuovo Staff")
        with st.form("reg_sys"):
            nu = st.text_input("User ID"); np = st.text_input("PW", type="password")
            nn = st.text_input("Nome"); nc = st.text_input("Cognome")
            nq = st.selectbox("Specializzazione", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
            if st.form_submit_button("CREA ACCOUNT"):
                if nu and np:
                    db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu.lower().strip(), hash_pw(np), nn, nc, nq), True)
                    st.success("Account Creato")
    st.stop()

# --- DATI OPERATORE ATTIVO ---
u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR DI NAVIGAZIONE ---
st.sidebar.markdown("<div class='sidebar-header'>REMS v34</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-profile'><b>{u['nome']} {u['cognome']}</b><br><span style='color:#58a6ff'>{u['ruolo']}</span></div>", unsafe_allow_html=True)

nav = st.sidebar.radio("SISTEMA CENTRALE", ["📊 DIARIO CLINICO", "👥 MODULO OPERATIVO", "📅 AGENDA & SCADENZE", "🗺️ MAPPA REPARTI", "⚙️ ADMIN & AUDIT LOG"])

if st.sidebar.button("🚪 ESCI (LOGOUT)"):
    scrivi_log("LOGOUT", "Disconnessione volontaria")
    st.session_state.user_session = None
    st.rerun()

# --- 1. DIARIO CLINICO INTEGRALE ---
if nav == "📊 DIARIO CLINICO":
    st.markdown("<div class='main-banner'><h2>DIARIO CLINICO MULTIDISCIPLINARE</h2></div>", unsafe_allow_html=True)
    pazienti = db_run("SELECT id, nome FROM pazienti WHERE stato=0 ORDER BY nome")
    
    if not pazienti: st.info("Nessun paziente presente in reparto.")
    
    for pid, nome in pazienti:
        with st.expander(f"📁 CARTELLA CLINICA: {nome.upper()}"):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("Cronologia Interventi")
                filtro = st.multiselect("Filtra per Ruolo professionale:", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"], key=f"f_{pid}")
                
                query_e = "SELECT data, ruolo, op, nota FROM eventi WHERE id=?"
                params_e = [pid]
                if filtro:
                    query_e += f" AND ruolo IN ({','.join(['?']*len(filtro))})"
                    params_e.extend(filtro)
                
                for d, r, o, nt in db_run(query_e + " ORDER BY id_u DESC", tuple(params_e)):
                    r_tag = r.lower().replace(" ", "")
                    st.markdown(f"<div class='card-diario role-{r_tag}'><b>[{d}] - {o}</b><br>{nt}</div>", unsafe_allow_html=True)
            with c2:
                st.subheader("Dati Generali")
                loc = db_run("SELECT stanza_id, letto FROM assegnazioni WHERE p_id=?", (pid,))
                if loc: st.success(f"📍 Posizione: Stanza {loc[0][0]} / Letto {loc[0][1]}")
                
                st.markdown("---")
                st.write("**💊 Terapie Correnti:**")
                for f, ds in db_run("SELECT farmaco, dose FROM terapie WHERE p_id=?", (pid,)): st.write(f"- {f} ({ds})")
                
                st.markdown("---")
                movs = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (pid,))
                saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in movs)
                st.metric("Saldo Cassa", f"{saldo:.2f} €")

# --- 2. MODULO OPERATIVO (EQUIPE) ---
elif nav == "👥 MODULO OPERATIVO":
    st.markdown("<div class='main-banner'><h2>INTERVENTI EQUIPE SANITARIA</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti WHERE stato=0 ORDER BY nome")
    
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente su cui operare", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        
        ruolo_act = u['ruolo']
        if u['ruolo'] == "Admin": ruolo_act = st.radio("Simula Ruolo per inserimento:", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"], horizontal=True)

        st.markdown("---")

        if ruolo_act == "Psichiatra":
            t1, t2 = st.tabs(["💊 Nuova Prescrizione", "📝 Nota Clinica"])
            with t1:
                with st.form("psi_t"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dosaggio")
                    c_t = st.columns(3); m = c_t[0].checkbox("MAT"); p = c_t[1].checkbox("POM"); n = c_t[2].checkbox("NOT")
                    if st.form_submit_button("CONFERMA PRESCRIZIONE"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"➕ PRESCRITTO: {f} {d}", "Psichiatra", firma), True); st.rerun()
            with t2:
                with st.form("psi_n"):
                    nota = st.text_area("Diario Psichiatrico")
                    if st.form_submit_button("SALVA NOTA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), nota, "Psichiatra", firma), True); st.rerun()

        elif ruolo_act == "Infermiere":
            t1, t2, t3 = st.tabs(["💉 Somministrazione", "🌡️ Parametri", "📝 Consegne"])
            with t1:
                ters = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                for tid, f, ds, mat, pom, nott in ters:
                    st.write(f"**{f}** ({ds})")
                    c_s = st.columns(3)
                    if mat and c_s[0].button("MATUTINA", key=f"m_{tid}"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ Somministrato {f} (MAT)", "Infermiere", firma), True); st.rerun()
                    if pom and c_s[1].button("POMERIDIANA", key=f"p_{tid}"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ Somministrato {f} (POM)", "Infermiere", firma), True); st.rerun()
                    if nott and c_s[2].button("NOTTURNA", key=f"n_{tid}"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ Somministrato {f} (NOT)", "Infermiere", firma), True); st.rerun()
            with t2:
                with st.form("inf_p"):
                    p_a = st.text_input("PA"); f_c = st.text_input("FC"); s_o = st.text_input("SatO2")
                    if st.form_submit_button("REGISTRA PARAMETRI"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"📊 PARAMETRI: PA {p_a} | FC {f_c} | Sat {s_o}", "Infermiere", firma), True); st.rerun()
            with t3:
                with st.form("inf_c"):
                    nota = st.text_area("Nota Infermieristica")
                    if st.form_submit_button("SALVA CONSEGNA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), nota, "Infermiere", firma), True); st.rerun()

        elif ruolo_act in ["Educatore", "Assistente Sociale"]:
            t1, t2 = st.tabs(["💰 Gestione Cassa", "📝 Relazione"])
            with t1:
                movs = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in movs)
                st.markdown(f"<div class='saldo-display'>{saldo:.2f} €</div>", unsafe_allow_html=True)
                with st.form("cassa_f"):
                    tipo = st.selectbox("Operazione", ["USCITA", "ENTRATA"]); imp = st.number_input("Importo €", min_value=0.0); cau = st.text_input("Causale")
                    if st.form_submit_button("ESEGUI MOVIMENTO"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, get_now_it().strftime("%Y-%m-%d"), cau, imp, tipo, firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"💰 {tipo}: {imp}€ - {cau}", ruolo_act, firma), True); st.rerun()
            with t2:
                with st.form("rel_f"):
                    nota = st.text_area(f"Relazione {ruolo_act}")
                    if st.form_submit_button("SALVA INTERVENTO"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), nota, ruolo_act, firma), True); st.rerun()

        elif ruolo_act == "OSS":
            with st.form("oss_f"):
                atti = st.multiselect("Attività Svolte:", ["Igiene Personale", "Pasto Assitito", "Riordino Stanza", "Vestizione"])
                nota = st.text_area("Note OSS")
                if st.form_submit_button("REGISTRA ATTIVITÀ"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🧹 {', '.join(atti)} | {nota}", "OSS", firma), True); st.rerun()

        elif ruolo_act == "OPSI":
            with st.form("opsi_f"):
                clima = st.selectbox("Clima Reparto", ["Tranquillo", "Tensione", "Rischio Aggressione"])
                nota = st.text_area("Rapporto di Vigilanza")
                if st.form_submit_button("INVIA RAPPORTO"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🛡️ CLIMA {clima.upper()}: {nota}", "OPSI", firma), True); st.rerun()

# --- 3. AGENDA DINAMICA ---
elif nav == "📅 AGENDA & SCADENZE":
    st.markdown("<div class='main-banner'><h2>AGENDA E CALENDARIO REPARTO</h2></div>", unsafe_allow_html=True)
    
    # Navigazione Temporale
    c_cal1, c_cal2, c_cal3 = st.columns([1, 2, 1])
    if c_cal1.button("⬅️ MESE PREC"):
        st.session_state.cur_m -= 1
        if st.session_state.cur_m < 1: st.session_state.cur_m=12; st.session_state.cur_y-=1
        st.rerun()
    if c_cal3.button("MESE SUCC ➡️"):
        st.session_state.cur_m += 1
        if st.session_state.cur_m > 12: st.session_state.cur_m=1; st.session_state.cur_y+=1
        st.rerun()
    c_cal2.markdown(f"<h2 style='text-align:center; color:#0969da'>{st.session_state.cur_m} / {st.session_state.cur_y}</h2>", unsafe_allow_html=True)

    col_a1, col_a2 = st.columns([3, 1])
    with col_a1:
        cal = calendar.Calendar(firstweekday=0)
        days = cal.monthdayscalendar(st.session_state.cur_y, st.session_state.cur_m)
        apps = db_run("SELECT a.data, p.nome, a.ora FROM appuntamenti a JOIN pazienti p ON a.p_id=p.id WHERE a.stato='ATTIVO'")
        map_a = {}
        for d, p, o in apps:
            try:
                dt = datetime.strptime(d, "%Y-%m-%d")
                if dt.month == st.session_state.cur_m and dt.year == st.session_state.cur_y:
                    if dt.day not in map_a: map_a[dt.day] = []
                    map_a[dt.day].append(f"{o} {p}")
            except: pass

        html = "<table class='cal-grid'><tr><th class='cal-head'>LUN</th><th class='cal-head'>MAR</th><th class='cal-head'>MER</th><th class='cal-head'>GIO</th><th class='cal-head'>VEN</th><th class='cal-head'>SAB</th><th class='cal-head'>DOM</th></tr>"
        for week in days:
            html += "<tr>"
            for d in week:
                if d == 0: html += "<td style='background:#f6f8fa; border:none'></td>"
                else:
                    is_t = "today-marker" if (d==get_now_it().day and st.session_state.cur_m==get_now_it().month) else ""
                    tags = "".join([f"<div class='ev-tag'>{x}</div>" for x in map_a.get(d, [])])
                    html += f"<td class='cal-day {is_t}'><b>{d}</b><br>{tags}</td>"
            html += "</tr>"
        st.markdown(html + "</table>", unsafe_allow_html=True)

    with col_a2:
        st.subheader("➕ Nuovo Appuntamento")
        with st.form("new_app_f"):
            p_ids = db_run("SELECT id, nome FROM pazienti WHERE stato=0")
            p_n = st.selectbox("Paziente", [x[1] for x in p_ids])
            sel_pid = [x[0] for x in p_ids if x[1]==p_n][0]
            data_a = st.date_input("Data"); ora_a = st.time_input("Ora")
            if st.form_submit_button("REGISTRA APPUNTAMENTO"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, stato, autore) VALUES (?,?,?,?,?)", (sel_pid, str(data_a), str(ora_a)[:5], "ATTIVO", firma), True)
                scrivi_log("AGENDA", f"Inserito appuntamento per {p_n}"); st.rerun()

# --- 4. MAPPA REPARTI (CAMBIO STANZA INTEGRALE) ---
elif nav == "🗺️ MAPPA REPARTI":
    st.markdown("<div class='main-banner'><h2>DISLOCAZIONE LETTI E TRASFERIMENTI</h2></div>", unsafe_allow_html=True)
    
    stanze = db_run("SELECT id, reparto, tipo FROM stanze")
    occ = db_run("SELECT a.stanza_id, a.letto, p.nome FROM assegnazioni a JOIN pazienti p ON a.p_id=p.id WHERE p.stato=0")
    mappa = {s[0]: {"rep":s[1], "tipo":s[2], "l1":"LIBERO", "l2":"LIBERO"} for s in stanze}
    for sid, let, pn in occ:
        if sid in mappa: mappa[sid][f"l{let}"] = pn

    cA, cB = st.columns(2)
    with cA:
        st.markdown("### 🏢 REPARTO A")
        for sid, info in mappa.items():
            if info['rep'] == 'A':
                with st.expander(f"STANZA {sid} ({info['tipo']})"):
                    st.write(f"🛏️ Letto 1: **{info['l1']}**")
                    st.write(f"🛏️ Letto 2: **{info['l2']}**")
    with cB:
        st.markdown("### 🏢 REPARTO B")
        for sid, info in mappa.items():
            if info['rep'] == 'B':
                with st.expander(f"STANZA {sid} ({info['tipo']})"):
                    st.write(f"🛏️ Letto 1: **{info['l1']}**")
                    st.write(f"🛏️ Letto 2: **{info['l2']}**")

    st.divider()
    st.subheader("🔄 Trasferimento Rapido Paziente")
    with st.form("move_p_form"):
        p_m = db_run("SELECT id, nome FROM pazienti WHERE stato=0")
        p_s = st.selectbox("Scegli Paziente", [x[1] for x in p_m])
        s_d = st.selectbox("Stanza Destinazione", [x[0] for x in stanze])
        l_d = st.selectbox("Posto Letto", [1, 2])
        if st.form_submit_button("ESEGUI TRASFERIMENTO"):
            pid_m = [x[0] for x in p_m if x[1]==p_s][0]
            db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid_m,), True)
            db_run("INSERT INTO assegnazioni (p_id, stanza_id, letto, data_ass) VALUES (?,?,?,?)", (pid_m, s_d, l_d, get_now_it().strftime("%Y-%m-%d")), True)
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid_m, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🔄 TRASLOCO: Spostato in Stanza {s_d} / Letto {l_d}", "Sistema", "Auto"), True)
            scrivi_log("SPOSTAMENTO", f"Paziente {p_s} trasferito in {s_d}-L{l_d}"); st.rerun()

# --- 5. ADMIN & AUDIT LOG (PIENA TRACCIABILITÀ) ---
elif nav == "⚙️ ADMIN & AUDIT LOG":
    st.markdown("<div class='main-banner'><h2>SISTEMA DI CONTROLLO E AUDIT</h2></div>", unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["👥 Gestione Pazienti", "📦 Archivio Storico", "📜 LOG AUDIT (Tracciabilità)"])
    
    with t1:
        st.subheader("Registrazione Nuovo Ingresso")
        with st.form("new_paz_f"):
            nome_p = st.text_input("Nome e Cognome")
            if st.form_submit_button("CONFERMA INGRESSO"):
                db_run("INSERT INTO pazienti (nome, stato) VALUES (?, 0)", (nome_p.upper(),), True)
                scrivi_log("INGRESSO", f"Paziente {nome_p.upper()} registrato"); st.rerun()
        
        st.divider()
        st.subheader("Pazienti Attivi (Dimissioni)")
        for pid, nome in db_run("SELECT id, nome FROM pazienti WHERE stato=0"):
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"**{nome}**")
            if c2.button("DIMETTI", key=f"d_{pid}"):
                db_run("UPDATE pazienti SET stato=1 WHERE id=?", (pid,), True)
                db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid,), True)
                scrivi_log("DIMISSIONE", f"Paziente {nome} archiviato"); st.rerun()

    with t2:
        st.subheader("Archivio Storico (Sola Lettura)")
        for pid, nome in db_run("SELECT id, nome FROM pazienti WHERE stato=1"):
            with st.expander(f"📦 {nome}"):
                if st.button("RIAMMETTI IN REPARTO", key=f"re_{pid}"):
                    db_run("UPDATE pazienti SET stato=0 WHERE id=?", (pid,), True)
                    scrivi_log("RIAMMISSIONE", f"Paziente {nome} riattivato"); st.rerun()
                st.write(db_run("SELECT data, nota, op FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,)))

    with t3:
        st.subheader("📜 REGISTRO AUDIT LOG (Scatola Nera)")
        st.warning("Ogni azione compiuta nel sistema è registrata qui con timestamp legale.")
        logs = db_run("SELECT data_ora, utente, azione, dettaglio FROM logs_sistema ORDER BY id_log DESC LIMIT 500")
        if logs:
            df_logs = pd.DataFrame(logs, columns=["Data/Ora", "Operatore", "Azione", "Dettaglio"])
            st.table(df_logs) # Tabella fissa per massima leggibilità
