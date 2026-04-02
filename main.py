import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar

# --- FUNZIONE AGGIORNAMENTO DB (INTEGRALE) ---
def aggiorna_struttura_db():
    conn = sqlite3.connect('rems_final_v12.db')
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE eventi ADD COLUMN tipo_evento TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE eventi ADD COLUMN figura_professionale TEXT")
    except: pass
    conn.commit()
    conn.close()

aggiorna_struttura_db()

# --- FUNZIONE ORARIO ITALIA (UTC+2) ---
def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v28.9 (CSS TOTALE) ---
st.set_page_config(page_title="REMS Connect ELITE PRO v28.9", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .user-logged { color: #00ff00 !important; font-weight: 900; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; text-align: center; }
    .sidebar-footer { color: #ffffff !important; font-size: 0.8rem; text-align: center; margin-top: 20px; opacity: 0.8; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 1px solid #ffffff22; }
    
    .alert-sidebar { background: #ef4444; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: 800; margin: 10px 5px; border: 2px solid white; animation: pulse 2s infinite; }
    @keyframes pulse { 0% {transform: scale(1);} 50% {transform: scale(1.02);} 100% {transform: scale(1);} }

    .cal-table { width:100%; border-collapse: collapse; table-layout: fixed; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .cal-table th { background: #f1f5f9; padding: 10px; color: #1e3a8a; font-weight: 800; border: 1px solid #e2e8f0; font-size: 0.85rem; }
    .cal-table td { border: 1px solid #e2e8f0; vertical-align: top; height: 150px; padding: 5px; position: relative; }
    .day-num-html { font-weight: 900; color: #64748b; font-size: 0.8rem; margin-bottom: 4px; display: block; }
    
    .event-tag-html { font-size: 0.65rem; background: #dbeafe; color: #1e40af; padding: 2px 4px; border-radius: 4px; margin-bottom: 3px; border-left: 3px solid #2563eb; line-height: 1.1; position: relative; cursor: help; }
    .event-tag-html .tooltip-text { visibility: hidden; width: 220px; background-color: #1e3a8a; color: #fff; text-align: left; border-radius: 8px; padding: 12px; position: absolute; z-index: 9999 !important; bottom: 125%; left: 0%; opacity: 0; transition: opacity 0.3s; font-size: 0.75rem; line-height: 1.4; border: 1px solid #ffffff44; pointer-events: none; }
    .event-tag-html:hover .tooltip-text { visibility: visible; opacity: 1; }
    
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    .role-psicologo { background-color: #faf5ff; border-color: #a855f7; }
    .role-sociale { background-color: #fff7ed; border-color: #f97316; }
    .role-opsi { background-color: #f1f5f9; border-color: #0f172a; border-style: dashed; }

    .therapy-container { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px; margin-bottom: 15px; border-left: 8px solid #1e3a8a; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2.2rem; font-weight: 900; color: #166534; }
    
    .map-reparto { background: #f1f5f9; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    .reparto-title { text-align: center; color: #1e3a8a; font-weight: 900; text-transform: uppercase; margin-bottom: 15px; border-bottom: 2px solid #1e3a8a33; }
    .stanza-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
    .stanza-tile { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; border-left: 6px solid #94a3b8; }
    .stanza-header { font-weight: 800; font-size: 0.8rem; color: #475569; margin-bottom: 5px; border-bottom: 1px solid #eee; }
    .letto-slot { font-size: 0.8rem; color: #1e293b; padding: 2px 0; }
</style>
""", unsafe_allow_html=True)

# --- ENGINE DATABASE (LOGICA INTEGRALE) ---
DB_NAME = "rems_final_v12.db"

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        try:
            cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE)")
            cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
            cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
            cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
            cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT, tipo_evento TEXT, mezzo TEXT, accompagnatore TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT, FOREIGN KEY(p_id) REFERENCES pazienti(id))")
            
            # Utente Admin predefinito
            if cur.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
                cur.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("perito2026"), "SUPER", "USER", "Admin"))
            
            # Inizializzazione Stanze
            if cur.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
                for i in range(1, 7): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"A{i}", "A", "ISOLAMENTO" if i==6 else "STANDARD"))
                for i in range(1, 11): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"B{i}", "B", "ISOLAMENTO" if i==10 else "STANDARD"))
            
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}")
            return []

# --- FUNZIONE VISUALIZZAZIONE DIARIO (CORRETTA) ---
def render_postits(p_id, limit=50):
    st.markdown("### 📖 Diario Clinico & Consegne")
    ruoli_disp = ["Tutti", "Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"]
    scelta_ruolo = st.multiselect("Filtra Figure Professionali", ruoli_disp, default="Tutti", key=f"filter_widget_{p_id}")

    query = "SELECT data, ruolo, op, nota FROM eventi WHERE id=?"
    params = [p_id]
    
    if "Tutti" not in scelta_ruolo and scelta_ruolo:
        query += f" AND ruolo IN ({','.join(['?']*len(scelta_ruolo))})"
        params.extend(scelta_ruolo)

    res = db_run(query + " ORDER BY id_u DESC LIMIT ?", tuple(params + [limit]))
    
    if not res:
        st.info("Nessun evento registrato per questo paziente.")
    
    for d, r, o, nt in res:
        role_map = {"Psichiatra":"psichiatra", "Infermiere":"infermiere", "Educatore":"educatore", "OSS":"oss", "Psicologo":"psicologo", "Assistente Sociale":"sociale", "OPSI":"opsi"}
        cls = f"role-{role_map.get(r, 'oss')}"
        st.markdown(f'''
            <div class="postit {cls}">
                <div class="postit-header">
                    <span>👤 {o} ({r})</span>
                    <span>📅 {d}</span>
                </div>
                <div>{nt}</div>
            </div>
        ''', unsafe_allow_html=True)

# --- GESTIONE SESSIONE E LOGIN ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if 'cal_month' not in st.session_state: st.session_state.cal_month = get_now_it().month
if 'cal_year' not in st.session_state: st.session_state.cal_year = get_now_it().year

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT - ACCESSO PRO</h2></div>", unsafe_allow_html=True)
    c_l, c_r = st.columns(2)
    with c_l:
        st.subheader("Login")
        with st.form("login_form"):
            u_i = st.text_input("Username").lower().strip()
            p_i = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
                if res: 
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_i}
                    st.rerun()
                else: st.error("Credenziali non valide")
    with c_r:
        st.subheader("Registrazione")
        with st.form("reg_form"):
            ru, rp, rn, rc = st.text_input("Username"), st.text_input("Password", type="password"), st.text_input("Nome"), st.text_input("Cognome")
            rq = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
            if st.form_submit_button("REGISTRA"):
                if ru and rp and rn and rc:
                    db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (ru.lower(), hash_pw(rp), rn, rc, rq), True)
                    st.success("Utente creato correttamente!")
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"
oggi_iso = get_now_it().strftime("%Y-%m-%d")

# --- SIDEBAR (NAVIGAZIONE TOTALE) ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-logged'>● {u['nome']} {u['cognome']}</div>", unsafe_allow_html=True)

conta_oggi = db_run("SELECT COUNT(*) FROM appuntamenti WHERE data=? AND stato='PROGRAMMATO'", (oggi_iso,))[0][0]
if conta_oggi > 0:
    st.sidebar.markdown(f"<div class='alert-sidebar'>⚠️ {conta_oggi} SCADENZE OGGI</div>", unsafe_allow_html=True)

opts = ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Posti Letto"]
if u['ruolo'] == "Admin": opts.append("⚙️ Admin")
nav = st.sidebar.radio("NAVIGAZIONE", opts)

if st.sidebar.button("ESCI"):
    st.session_state.user_session = None
    st.rerun()

# --- LOGICA DELLE PAGINE ---

# 1. MONITORAGGIO (VISTA GLOBALE)
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO GENERALE</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"📁 CARTELLA: {nome}"):
            render_postits(pid)

# 2. MODULO EQUIPE (LAVORO QUOTIDIANO)
elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO EQUIPE</h2></div>", unsafe_allow_html=True)
    
    ruolo_corr = u['ruolo']
    if u['ruolo'] == "Admin": 
        ruolo_corr = st.selectbox("Simula Ruolo:", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
    
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        now = get_now_it()

        # LOGICA PER RUOLO
        if ruolo_corr == "Psichiatra":
            t1, t2, t3 = st.tabs(["💊 PRESCRIZIONI", "📝 TERAPIE ATTIVE", "👨‍⚕️ NOTE MEDICHE"])
            with t1:
                with st.form("form_presc"):
                    farm, dose = st.text_input("Farmaco"), st.text_input("Dosaggio")
                    c1, c2, c3 = st.columns(3)
                    m, p, n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, farm, dose, int(m), int(p), int(n), firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"➕ Prescrizione: {farm} {dose}", "Psichiatra", firma_op), True)
                        st.rerun()
            with t2:
                terapie = db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,))
                for tid, fn, ds in terapie:
                    col_t, col_b = st.columns([0.8, 0.2])
                    col_t.write(f"**{fn}** - {ds}")
                    if col_b.button("SOSPENDE", key=f"sos_{tid}"):
                        db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🚫 Sospensione: {fn}", "Psichiatra", firma_op), True)
                        st.rerun()
            with t3:
                with st.form("form_med_note"):
                    txt_med = st.text_area("Consegna Medica / Osservazioni Cliniche", height=200)
                    if st.form_submit_button("PUBBLICA NOTA MEDICA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"👨‍⚕️ NOTA MEDICA: {txt_med}", "Psichiatra", firma_op), True)
                        st.success("Nota salvata")
                        st.rerun()

        elif ruolo_corr == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 TERAPIA", "💓 PARAMETRI", "📝 CONSEGNE"])
            with t1:
                terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                col1, col2, col3 = st.columns(3)
                turni = [("MAT", 3, "☀️"), ("POM", 4, "🌤️"), ("NOT", 5, "🌙")]
                for i, (t_n, t_idx, t_ico) in enumerate(turni):
                    with [col1, col2, col3][i]:
                        st.subheader(f"{t_ico} {t_n}")
                        for f in [x for x in terapie if x[t_idx]]:
                            if st.button(f"SOMMINISTRA {f[1]}", key=f"somm_{f[0]}_{t_n}"):
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({t_n}): {f[1]}", "Infermiere", firma_op), True)
                                st.rerun()
            with t2:
                with st.form("parametri_form"):
                    pa = st.text_input("Pressione Arteriosa")
                    fc = st.text_input("Frequenza Cardiaca")
                    sat = st.text_input("Saturazione O2")
                    if st.form_submit_button("REGISTRA PARAMETRI"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💓 PARAMETRI: PA {pa}, FC {fc}, Sat {sat}", "Infermiere", firma_op), True)
                        st.rerun()
            with t3:
                with st.form("cons_inf"):
                    txt = st.text_area("Nota Consegna")
                    if st.form_submit_button("SALVA CONSEGNA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), txt, "Infermiere", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "Educatore":
            t1, t2 = st.tabs(["💰 GESTIONE CASSA", "📝 PROGETTO EDUCATIVO"])
            with t1:
                mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
                st.markdown(f"<div class='cassa-card'>Saldo Attuale: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
                with st.form("cassa_form"):
                    tipo_m = st.selectbox("Tipo", ["USCITA", "ENTRATA"])
                    importo = st.number_input("Importo €", min_value=0.0, step=0.1)
                    causale = st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, oggi_iso, causale, importo, tipo_m, firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💰 {tipo_m}: {importo}€ - {causale}", "Educatore", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("edu_form"):
                    txt = st.text_area("Osservazione Educativa / Attività")
                    if st.form_submit_button("REGISTRA ATTIVITÀ"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"📝 {txt}", "Educatore", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "OSS":
            with st.form("oss_form"):
                mansioni = st.multiselect("Mansioni Svolte:", ["Igiene Personale", "Rifacimento Letto", "Sanificazione Camera", "Accompagnamento"])
                note_oss = st.text_area("Note Aggiuntive")
                if st.form_submit_button("REGISTRA INTERVENTO"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧹 {', '.join(mansioni)} | {note_oss}", "OSS", firma_op), True)
                    st.rerun()

        st.divider()
        render_postits(p_id)

# 3. AGENDA (INTEGRALE CON TOOLTIP)
elif nav == "📅 Agenda Dinamica":
    st.markdown("<div class='section-banner'><h2>AGENDA DINAMICA REMS</h2></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c1: 
        if st.button("⬅️ Mese Prec."): st.session_state.cal_month -= 1; st.rerun()
    with c2: 
        st.markdown(f"<h3 style='text-align:center;'>{st.session_state.cal_month} / {st.session_state.cal_year}</h3>", unsafe_allow_html=True)
    with c3: 
        if st.button("Mese Succ. ➡️"): st.session_state.cal_month += 1; st.rerun()

    # Logica Calendario
    start_d = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-01"
    end_d = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-31"
    evs = db_run("SELECT a.data, p.nome, a.ora, a.tipo_evento, a.nota FROM appuntamenti a JOIN pazienti p ON a.p_id=p.id WHERE a.data BETWEEN ? AND ? AND a.stato='PROGRAMMATO'", (start_d, end_d))
    
    mappa_ev = {}
    for d_ev, p_n, h_ev, t_ev, nt_ev in evs:
        g = int(d_ev.split("-")[2])
        if g not in mappa_ev: mappa_ev[g] = []
        mappa_ev[g].append(f'<div class="event-tag-html">📌 {p_n} ({h_ev})<span class="tooltip-text">{t_ev}: {nt_ev}</span></div>')

    cal_html = "<table class='cal-table'><tr>" + "".join([f"<th>{d}</th>" for d in ["Lun","Mar","Mer","Gio","Ven","Sab","Dom"]]) + "</tr>"
    cal_obj = calendar.Calendar(firstweekday=0)
    for week in cal_obj.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month):
        cal_html += "<tr>"
        for day in week:
            if day == 0: cal_html += "<td style='background:#f1f5f9;'></td>"
            else:
                cal_html += f"<td><span class='day-num-html'>{day}</span>{''.join(mappa_ev.get(day, []))}</td>"
        cal_html += "</tr>"
    st.markdown(cal_html + "</table>", unsafe_allow_html=True)
    
    with st.expander("➕ AGGIUNGI APPUNTAMENTO"):
        with st.form("new_app"):
            p_a = st.selectbox("Paziente", [p[1] for p in db_run("SELECT nome FROM pazienti")])
            p_id_a = db_run("SELECT id FROM pazienti WHERE nome=?", (p_a,))[0][0]
            d_a, h_a = st.date_input("Data"), st.time_input("Ora")
            t_a, n_a = st.selectbox("Tipo", ["Uscita","Visita","Tribunale"]), st.text_area("Note")
            if st.form_submit_button("SALVA"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore, tipo_evento) VALUES (?,?,?,?,'PROGRAMMATO',?,?)", (p_id_a, str(d_a), str(h_a)[:5], n_a, firma_op, t_a), True)
                st.rerun()

# 4. MAPPA (VISUALIZZAZIONE POSTI LETTO)
elif nav == "🗺️ Mappa Posti Letto":
    st.markdown("<div class='section-banner'><h2>TABELLONE POSTI LETTO</h2></div>", unsafe_allow_html=True)
    stanze = db_run("SELECT id, reparto, tipo FROM stanze")
    paz_map = db_run("SELECT p.nome, a.stanza_id, a.letto FROM pazienti p JOIN assegnazioni a ON p.id = a.p_id")
    occupazione = {(sid, l): nome for nome, sid, l in paz_map}
    
    c_a, c_b = st.columns(2)
    for i, rep in enumerate(["A", "B"]):
        with [c_a, c_b][i]:
            st.markdown(f"<div class='map-reparto'><div class='reparto-title'>Reparto {rep}</div><div class='stanza-grid'>", unsafe_allow_html=True)
            for s_id, s_rep, s_tip in [s for s in stanze if s[1] == rep]:
                st.markdown(f"<div class='stanza-tile'><div class='stanza-header'>{s_id} - {s_tip}</div>", unsafe_allow_html=True)
                for l in [1, 2]:
                    ospite = occupazione.get((s_id, l), "Libero")
                    st.markdown(f"<div class='letto-slot'>L{l}: <b>{ospite}</b></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div></div>", unsafe_allow_html=True)

# 5. ADMIN (GESTIONE ANAGRAFICA)
elif nav == "⚙️ Admin":
    st.markdown("<div class='section-banner'><h2>AMMINISTRAZIONE</h2></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["PAZIENTI", "SPOSTAMENTI"])
    with t1:
        with st.form("new_paz"):
            np = st.text_input("Inserisci Nome e Cognome Paziente")
            if st.form_submit_button("AGGIUNGI PAZIENTE"):
                db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True)
                st.success(f"{np} aggiunto.")
                st.rerun()
        for pid, pnm in db_run("SELECT id, nome FROM pazienti"):
            c_p, c_d = st.columns([0.8, 0.2])
            c_p.write(pnm)
            if c_d.button("ELIMINA", key=f"del_p_{pid}"):
                db_run("DELETE FROM pazienti WHERE id=?", (pid,), True)
                st.rerun()
    with t2:
        st.info("Logica per assegnazione stanze")
        p_list = db_run("SELECT id, nome FROM pazienti")
        s_list = db_run("SELECT id FROM stanze")
        with st.form("move_paz"):
            p_sel = st.selectbox("Paziente", [p[1] for p in p_list])
            s_sel = st.selectbox("Stanza", [s[0] for s in s_list])
            l_sel = st.selectbox("Letto", [1, 2])
            if st.form_submit_button("ASSEGNA POSTO"):
                p_id = [p[0] for p in p_list if p[1]==p_sel][0]
                db_run("INSERT OR REPLACE INTO assegnazioni (p_id, stanza_id, letto, data_ass) VALUES (?,?,?,?)", (p_id, s_sel, l_sel, oggi_iso), True)
                st.success("Spostamento completato")
                st.rerun()
