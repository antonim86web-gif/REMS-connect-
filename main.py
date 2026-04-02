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
    # Colonne per eventi
    try: c.execute("ALTER TABLE eventi ADD COLUMN tipo_evento TEXT")
    except: pass
    try: c.execute("ALTER TABLE eventi ADD COLUMN figura_professionale TEXT")
    except: pass
    
    # --- LOGICA DI STATO PAZIENTE (DIMISSIONI) ---
    try: c.execute("ALTER TABLE pazienti ADD COLUMN stato TEXT DEFAULT 'ATTIVO'")
    except: pass
    
    # --- AGGIORNAMENTO TERAPIE PER S.T.U. ---
    try: c.execute("ALTER TABLE terapie ADD COLUMN bis INTEGER DEFAULT 0")
    except: pass
    
    # Nuova Tabella per Marcatura STU puntuale (A/R) - Necessaria per il pop-up
    c.execute("""CREATE TABLE IF NOT EXISTS stu_registrazioni (
                 id_stu INTEGER PRIMARY KEY AUTOINCREMENT,
                 p_id INTEGER, t_id INTEGER, giorno INTEGER, mese INTEGER, anno INTEGER,
                 stato TEXT, op_firma TEXT, timestamp TEXT)""")

    # Tabella Log per Tracciabilità Legale
    c.execute("""CREATE TABLE IF NOT EXISTS logs_sistema (
                 id_log INTEGER PRIMARY KEY AUTOINCREMENT, 
                 data_ora TEXT, 
                 utente TEXT, 
                 azione TEXT, 
                 dettaglio TEXT)""")
    conn.commit()
    conn.close()

aggiorna_struttura_db()

# --- FUNZIONE ORARIO ITALIA (UTC+2) ---
def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

# --- FUNZIONE SCRITTURA LOG ---
def scrivi_log(azione, dettaglio):
    user_log = st.session_state.user_session['uid'] if st.session_state.user_session else "SISTEMA"
    with sqlite3.connect('rems_final_v12.db') as conn:
        conn.execute("INSERT INTO logs_sistema (data_ora, utente, azione, dettaglio) VALUES (?,?,?,?)", 
                     (get_now_it().strftime("%d/%m/%Y %H:%M:%S"), user_log, azione, dettaglio))
        conn.commit()

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v28.9.2 ---
st.set_page_config(page_title="REMS Connect ELITE PRO v28.9.2", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .user-logged { color: #00ff00 !important; font-weight: 900; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; text-align: center; }
    .sidebar-footer { color: #ffffff !important; font-size: 0.8rem; text-align: center; margin-top: 20px; opacity: 0.8; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 1px solid #ffffff22; }
    .stButton>button[kind="secondary"] { background-color: #22c55e !important; color: white !important; border: none !important; width: 100%; font-weight: 700; }
    
    .alert-sidebar { background: #ef4444; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: 800; margin: 10px 5px; border: 2px solid white; animation: pulse 2s infinite; }
    @keyframes pulse { 0% {transform: scale(1);} 50% {transform: scale(1.02);} 100% {transform: scale(1);} }

    /* CSS STU OPERATIVA PROFESSIONALE */
    .stu-container { background: white; padding: 15px; border: 2px solid #000; border-radius: 8px; margin-top: 10px; }
    .firma-medica-box { border: 2px dashed #1e3a8a; padding: 10px; background: #f0f4f8; margin-bottom: 15px; border-radius: 5px; }
    .stu-table-header { font-weight: 900; font-size: 0.75rem; color: #1e3a8a; text-transform: uppercase; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .label-a { color: #22c55e; font-weight: 900; text-align: center; }
    .label-r { color: #ef4444; font-weight: 900; text-align: center; }

    /* ALTRI CSS PREESISTENTI */
    .cal-table { width:100%; border-collapse: collapse; table-layout: fixed; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .cal-table th { background: #f1f5f9; padding: 10px; color: #1e3a8a; font-weight: 800; border: 1px solid #e2e8f0; font-size: 0.85rem; }
    .cal-table td { border: 1px solid #e2e8f0; vertical-align: top; height: 150px; padding: 5px; position: relative; }
    .day-num-html { font-weight: 900; color: #64748b; font-size: 0.8rem; margin-bottom: 4px; display: block; }
    .event-tag-html { font-size: 0.65rem; background: #dbeafe; color: #1e40af; padding: 2px 4px; border-radius: 4px; margin-bottom: 3px; border-left: 3px solid #2563eb; position: relative; cursor: help; }
    .event-tag-html .tooltip-text { visibility: hidden; width: 220px; background-color: #1e3a8a; color: #fff; text-align: left; border-radius: 8px; padding: 12px; position: absolute; z-index: 9999; bottom: 125%; left: 0%; opacity: 0; transition: opacity 0.3s; box-shadow: 0 8px 20px rgba(0,0,0,0.4); font-size: 0.75rem; white-space: normal; pointer-events: none; }
    .event-tag-html:hover .tooltip-text { visibility: visible; opacity: 1; }
    .today-html { background-color: #f0fdf4 !important; border: 2px solid #22c55e !important; }
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
    .turn-header { font-weight: 800; font-size: 0.9rem; text-transform: uppercase; margin-bottom: 10px; }
    .mat-style { color: #d97706; } .pom-style { color: #2563eb; } .not-style { color: #4338ca; }
    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2.2rem; font-weight: 900; color: #166534; }
    .map-reparto { background: #f1f5f9; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    .reparto-title { text-align: center; color: #1e3a8a; font-weight: 900; text-transform: uppercase; margin-bottom: 15px; border-bottom: 2px solid #1e3a8a33; }
    .stanza-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
    .stanza-tile { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; border-left: 6px solid #94a3b8; }
    .stanza-header { font-weight: 800; font-size: 0.8rem; color: #475569; margin-bottom: 5px; border-bottom: 1px solid #eee; }
    .letto-slot { font-size: 0.8rem; color: #1e293b; padding: 2px 0; }
    .stanza-occupata { border-left-color: #22c55e; background-color: #f0fdf4; }
    .stanza-piena { border-left-color: #2563eb; background-color: #eff6ff; }
    .stanza-isolamento { border-left-color: #ef4444; background-color: #fef2f2; border-width: 2px; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ENGINE ---
DB_NAME = "rems_final_v12.db"

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        try:
            cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, stato TEXT DEFAULT 'ATTIVO')")
            cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT, figura_professionale TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT, bis INTEGER DEFAULT 0)")
            cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
            cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT, tipo_evento TEXT, mezzo TEXT, accompagnatore TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT, FOREIGN KEY(p_id) REFERENCES pazienti(id))")
            
            if cur.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
                cur.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("perito2026"), "SUPER", "USER", "Admin"))
            
            if cur.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
                for i in range(1, 7): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"A{i}", "A", "ISOLAMENTO" if i==6 else "STANDARD"))
                for i in range(1, 11): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"B{i}", "B", "ISOLAMENTO" if i==10 else "STANDARD"))
            
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}")
            return []

# --- RENDERER S.T.U. OPERATIVA (AGGIORNAMENTO TOOLTIP & FIRME) ---
def render_stu_operativa_interattiva(p_id, ruolo, operatore):
    now = get_now_it()
    
    # Firma Medico Responsabile (Ultima validazione)
    med_info = db_run("SELECT medico FROM terapie WHERE p_id=? AND medico IS NOT NULL ORDER BY id_u DESC LIMIT 1", (p_id,))
    firma_medico = med_info[0][0] if med_info else "DA VALIDARE"

    st.markdown(f"""<div class='firma-medica-box'>
        <small style='color:#1e3a8a'>VALIDAZIONE MEDICA PIANO TERAPEUTICO:</small><br>
        <b style='font-family:Courier; font-size:1.2rem;'>f.to Dott. {firma_medico}</b>
    </div>""", unsafe_allow_html=True)

    terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott, bis FROM terapie WHERE p_id=?", (p_id,))
    regs = db_run("SELECT t_id, stato, op_firma, timestamp FROM stu_registrazioni WHERE p_id=? AND giorno=? AND mese=?", 
                  (p_id, now.day, now.month))
    mappa_regs = {r[0]: {"stato": r[1], "op": r[2], "ora": r[3]} for r in regs}

    h_cols = st.columns([2, 1, 0.4, 0.4, 0.8])
    h_cols[0].markdown("<div class='stu-table-header'>Farmaco</div>", unsafe_allow_html=True)
    h_cols[1].markdown("<div class='stu-table-header'>Dose</div>", unsafe_allow_html=True)
    h_cols[2].markdown("<div class='label-a'>A</div>", unsafe_allow_html=True)
    h_cols[3].markdown("<div class='label-r'>R</div>", unsafe_allow_html=True)
    h_cols[4].markdown("<div class='stu-table-header'>Stato</div>", unsafe_allow_html=True)
    st.divider()

    for t in terapie:
        t_id, f_nome, f_dose = t[0], t[1], t[2]
        reg = mappa_regs.get(t_id)
        cols = st.columns([2, 1, 0.4, 0.4, 0.8])

        if ruolo == "Psichiatra":
            with cols[0]: n_f = st.text_input("F", f_nome, key=f"edit_f_{t_id}", label_visibility="collapsed")
            with cols[1]: n_d = st.text_input("D", f_dose, key=f"edit_d_{t_id}", label_visibility="collapsed")
            with cols[2]: 
                if st.button("💾", key=f"save_{t_id}", help="Valida e Firma Modifica"):
                    db_run("UPDATE terapie SET farmaco=?, dose=?, medico=? WHERE id_u=?", (n_f, n_d, operatore, t_id), True)
                    st.rerun()
        else:
            cols[0].write(f"**{f_nome}**")
            cols[1].write(f"{f_dose}")
            with cols[2]:
                if st.button("A", key=f"a_{t_id}"):
                    db_run("DELETE FROM stu_registrazioni WHERE t_id=? AND giorno=? AND mese=?", (t_id, now.day, now.month), True)
                    db_run("INSERT INTO stu_registrazioni (p_id,t_id,giorno,mese,anno,stato,op_firma,timestamp) VALUES (?,?,?,?,?,?,?,?)",
                           (p_id, t_id, now.day, now.month, now.year, "A", operatore, now.strftime("%H:%M")), True)
                    st.rerun()
            with cols[3]:
                if st.button("R", key=f"r_{t_id}"):
                    db_run("DELETE FROM stu_registrazioni WHERE t_id=? AND giorno=? AND mese=?", (t_id, now.day, now.month), True)
                    db_run("INSERT INTO stu_registrazioni (p_id,t_id,giorno,mese,anno,stato,op_firma,timestamp) VALUES (?,?,?,?,?,?,?,?)",
                           (p_id, t_id, now.day, now.month, now.year, "R", operatore, now.strftime("%H:%M")), True)
                    st.rerun()

        with cols[4]:
            if reg:
                lbl = "✅ ASSUNTO" if reg['stato'] == "A" else "❌ RIFIUTATO"
                st.button(lbl, key=f"st_{t_id}", help=f"Operatore: {reg['op']}\nOra: {reg['ora']}", use_container_width=True)
            else:
                st.write("-")

def render_stu_cartacea(p_id):
    terapie = db_run("SELECT farmaco, dose, mat, pom, nott, bis FROM terapie WHERE p_id=?", (p_id,))
    t_mattina = [t for t in terapie if t[2] == 1]
    t_pomeriggio = [t for t in terapie if t[3] == 1 or t[4] == 1]
    t_bisogno = [t for t in terapie if t[5] == 1]
    
    oggi = get_now_it()
    giorni_mese = calendar.monthrange(oggi.year, oggi.month)[1]
    
    html = "<div class='stu-container'><table class='stu-table'>"
    html += "<tr class='header-row'><th class='sticky-col'>FARMACO / POSOLOGIA</th>"
    for d in range(1, 32):
        style = "class='cell-today-stu'" if d == oggi.day else ""
        html += f"<th {style}>{d:02d}</th>"
    html += "</tr>"

    def add_section(lista, titolo):
        res = f"<tr><td colspan='32' class='section-label-stu'>{titolo}</td></tr>"
        if not lista:
            res += "<tr><td class='sticky-col'>---</td>" + "<td></td>"*31 + "</tr>"
        for t in lista:
            res += f"<tr><td class='sticky-col'><b>{t[0]}</b><br><small>{t[1]}</small></td>" + "<td></td>"*31 + "</tr>"
        return res

    html += add_section(t_mattina, "Terapia del Mattino")
    html += "<tr class='spacer-row-stu'><td colspan='32'></td></tr>" * 2
    html += add_section(t_pomeriggio, "Terapia del Pomeriggio / Sera")
    html += "<tr class='spacer-row-stu'><td colspan='32'></td></tr>" * 2
    html += add_section(t_bisogno, "Terapia al Bisogno (P.R.N.)")
    html += "</table></div>"
    st.markdown(html, unsafe_allow_html=True)

def render_postits(p_id, limit=50):
    ruoli_disp = ["Tutti", "Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"]
    scelta_ruolo = st.multiselect("Filtra per Figura Professionale", ruoli_disp, default="Tutti", key=f"filt_{p_id}")
    query = "SELECT data, ruolo, op, nota FROM eventi WHERE id=?"
    params = [p_id]
    if "Tutti" not in scelta_ruolo and scelta_ruolo:
        query += f" AND ruolo IN ({','.join(['?']*len(scelta_ruolo))})"
        params.extend(scelta_ruolo)
    res = db_run(query + " ORDER BY id_u DESC LIMIT ?", tuple(params + [limit]))
    for d, r, o, nt in res:
        role_map = {"Psichiatra":"psichiatra", "Infermiere":"infermiere", "Educatore":"educatore", "OSS":"oss", "Psicologo":"psicologo", "Assistente Sociale":"sociale", "OPSI":"opsi"}
        cls = f"role-{role_map.get(r, 'oss')}"
        st.markdown(f'<div class="postit {cls}"><div class="postit-header"><span>👤 {o} ({r})</span><span>📅 {d}</span></div><div>{nt}</div></div>', unsafe_allow_html=True)

# --- SESSIONE E LOGIN ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if 'cal_month' not in st.session_state: st.session_state.cal_month = get_now_it().month
if 'cal_year' not in st.session_state: st.session_state.cal_year = get_now_it().year

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT - ACCESSO PRO</h2></div>", unsafe_allow_html=True)
    c_l, c_r = st.columns(2)
    with c_l:
        st.subheader("Login")
        with st.form("login_main"):
            u_i = st.text_input("Username").lower().strip()
            p_i = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
                if res: 
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_i}
                    scrivi_log("LOGIN", "Accesso eseguito correttamente")
                    st.rerun()
                else: st.error("Errore login: Credenziali errate.")
    with c_r:
        st.subheader("Registrazione")
        with st.form("reg_main"):
            ru = st.text_input("Scegli Username").lower().strip()
            rp = st.text_input("Scegli Password", type="password")
            rn = st.text_input("Nome")
            rc = st.text_input("Cognome")
            rq = st.selectbox("Qualifica Professionale", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
            if st.form_submit_button("REGISTRA NUOVO UTENTE"):
                if ru and rp and rn and rc:
                    if not db_run("SELECT user FROM utenti WHERE user=?", (ru,)):
                        db_run("INSERT INTO utenti (user, pwd, nome, cognome, qualifica) VALUES (?,?,?,?,?)", (ru, hash_pw(rp), rn.capitalize(), rc.capitalize(), rq), True)
                        scrivi_log("REGISTRAZIONE", f"Creato nuovo utente {ru} con qualifica {rq}")
                        st.success(f"Profilo {rq} creato! Accedi a sinistra.")
                    else: st.error("Username già in uso.")
                else: st.warning("Compila tutti i campi.")
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"
oggi_iso = get_now_it().strftime("%Y-%m-%d")

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-logged'>● {u['nome']} {u['cognome']}</div>", unsafe_allow_html=True)
conta_oggi = db_run("SELECT COUNT(*) FROM appuntamenti WHERE data=? AND stato='PROGRAMMATO'", (oggi_iso,))[0][0]
if conta_oggi > 0:
    st.sidebar.markdown(f"<div class='alert-sidebar'>⚠️ {conta_oggi} SCADENZE OGGI</div>", unsafe_allow_html=True)
opts = ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Posti Letto"]
if u['ruolo'] == "Admin": opts.append("⚙️ Admin")
nav = st.sidebar.radio("NAVIGAZIONE", opts)
if st.sidebar.button("LOGOUT"): 
    scrivi_log("LOGOUT", "Uscita dal sistema")
    st.session_state.user_session = None; 
    st.rerun()
st.sidebar.markdown(f"<br><br><br><div class='sidebar-footer'><b>Antony</b><br>Webmaster<br>ver. 28.9 Elite</div>", unsafe_allow_html=True)

# --- MODULO MAPPA ---
if nav == "🗺️ Mappa Posti Letto":
    st.markdown("<div class='section-banner'><h2>TABELLONE VISIVO POSTI LETTO</h2></div>", unsafe_allow_html=True)
    stanze_db = db_run("SELECT id, reparto, tipo FROM stanze ORDER BY id")
    paz_db = db_run("SELECT p.id, p.nome, a.stanza_id, a.letto FROM pazienti p LEFT JOIN assegnazioni a ON p.id = a.p_id WHERE p.stato='ATTIVO'")
    mappa = {s[0]: {'rep': s[1], 'tipo': s[2], 'letti': {1: None, 2: None}} for s in stanze_db}
    for pid, pnome, sid, letto in paz_db:
        if sid in mappa: mappa[sid]['letti'][letto] = {'id': pid, 'nome': pnome}
    
    c_a, c_b = st.columns(2)
    for r_code, col_obj in [("A", c_a), ("B", c_b)]:
        with col_obj:
            st.markdown(f"<div class='map-reparto'><div class='reparto-title'>Reparto {r_code}</div><div class='stanza-grid'>", unsafe_allow_html=True)
            for s_id, s_info in {k:v for k,v in mappa.items() if v['rep']==r_code}.items():
                p_count = len([v for v in s_info['letti'].values() if v])
                cls = "stanza-isolamento" if s_info['tipo']=="ISOLAMENTO" and p_count>0 else ("stanza-piena" if p_count==2 else ("stanza-occupata" if p_count==1 else ""))
                st.markdown(f"<div class='stanza-tile {cls}'><div class='stanza-header'>{s_id} <small>{s_info['tipo']}</small></div>", unsafe_allow_html=True)
                for l in [1, 2]:
                    p = s_info['letti'][l]
                    st.markdown(f"<div class='letto-slot'>L{l}: <b>{p['nome'] if p else 'Libero'}</b></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div></div>", unsafe_allow_html=True)

    with st.expander("Sposta Paziente"):
        p_list = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
        sel_p = st.selectbox("Paziente", [p[1] for p in p_list], index=None)
        if sel_p:
            pid_sel = [p[0] for p in p_list if p[1]==sel_p][0]
            posti_liberi = [f"{sid}-L{l}" for sid, si in mappa.items() for l, po in si['letti'].items() if not po]
            dest = st.selectbox("Destinazione", posti_liberi)
            mot = st.text_input("Motivo Trasferimento")
            if st.button("ESEGUI TRASFERIMENTO") and mot:
                dsid, dl = dest.split("-L")
                db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid_sel,), True)
                db_run("INSERT INTO assegnazioni (p_id, stanza_id, letto, data_ass) VALUES (?,?,?,?)", (pid_sel, dsid, int(dl), get_now_it().strftime("%Y-%m-%d")), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid_sel, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🔄 TRASFERIMENTO: Spostato in {dsid} Letto {dl}. Motivo: {mot}", u['ruolo'], firma_op), True)
                scrivi_log("SPOSTAMENTO", f"Paziente {sel_p} spostato in {dsid}-L{dl}. Motivo: {mot}")
                st.success("Trasferimento completato!")
                st.rerun()

elif nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO GENERALE</h2></div>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome"):
        with st.expander(f"📁 SCHEDA PAZIENTE: {nome}"):
            m_t1, m_t2 = st.tabs(["📑 DIARIO", "💊 S.T.U. OPERATIVA"])
            with m_t1: render_postits(pid)
            with m_t2: render_stu_operativa_interattiva(pid, u['ruolo'], firma_op)

elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO EQUIPE</h2></div>", unsafe_allow_html=True)
    ruolo_corr = u['ruolo']
    if u['ruolo'] == "Admin": ruolo_corr = st.selectbox("Simula Figura:", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
    p_lista = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        now = get_now_it(); oggi = now.strftime("%d/%m/%Y")

        if ruolo_corr == "Psichiatra":
            t1, t2, t3, t4 = st.tabs(["➕ Nuova Prescrizione", "📝 Gestione Terapie", "🩺 CONSEGNE MEDICHE", "💊 S.T.U."])
            with t1:
                with st.form("f_ps"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3,c4 = st.columns(4); m,p,n,bis = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT"), c4.checkbox("AL BISOGNO")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico, bis) VALUES (?,?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma_op, int(bis)), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"➕ Prescritto: {f} {d}", "Psichiatra", firma_op), True)
                        scrivi_log("PRESCRIZIONE", f"Inserita terapia {f} per {p_sel}")
                        st.rerun()
            with t2:
                for tid, fn, ds, m_v, p_v, n_v, b_v in db_run("SELECT id_u, farmaco, dose, mat, pom, nott, bis FROM terapie WHERE p_id=?", (p_id,)):
                    with st.expander(f"Modifica: {fn}"):
                        with st.form(key=f"m_{tid}"):
                            nf, nd = st.text_input("Farmaco", fn), st.text_input("Dose", ds)
                            cc1,cc2,cc3,cc4 = st.columns(4); nm,np,nn,nb = cc1.checkbox("MAT",bool(m_v)),cc2.checkbox("POM",bool(p_v)),cc3.checkbox("NOT",bool(n_v)), cc4.checkbox("BIS",bool(b_v))
                            if st.form_submit_button("AGGIORNA"): 
                                db_run("UPDATE terapie SET farmaco=?, dose=?, mat=?, pom=?, nott=?, bis=? WHERE id_u=?", (nf, nd, int(nm), int(np), int(nn), int(nb), tid), True)
                                st.rerun()
                            if st.form_submit_button("SOSPENDE"): 
                                db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
                                st.rerun()
            with t3:
                with st.form("f_cons_med"):
                    nota_medica = st.text_area("Indicazioni Cliniche / Note Diagnostiche")
                    if st.form_submit_button("SALVA CONSEGNA MEDICA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🩺 MED: {nota_medica}", "Psichiatra", firma_op), True)
                        st.rerun()
            with t4: render_stu_operativa_interattiva(p_id, ruolo_corr, firma_op)

        elif ruolo_corr == "Infermiere":
            t1, t2, t3, t4 = st.tabs(["💊 SOMMINISTRAZIONE", "💓 PARAMETRI", "📝 CONSEGNE", "📑 S.T.U. INTERATTIVA"])
            with t1:
                terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott, bis FROM terapie WHERE p_id=?", (p_id,))
                sezioni = [("MATTINA", 3, "mat-style", "☀️"), ("POMERIGGIO", 4, "pom-style", "🌤️"), ("NOTTE", 5, "not-style", "🌙"), ("AL BISOGNO", 7, "not-style", "🧪")]
                cols = st.columns(4)
                for i, (titolo, idx_db, css, icona) in enumerate(sezioni):
                    with cols[i]:
                        st.markdown(f"<div class='turn-header {css}'>{icona} {titolo}</div>", unsafe_allow_html=True)
                        farmaci_fascia = [f for f in terapie if f[idx_db] == 1]
                        if not farmaci_fascia: st.caption("Nessuna terapia")
                        for f in farmaci_fascia:
                            f_id, f_nome, f_dose = f[0], f[1], f[2]
                            chiave_somm = f"%✔️ SOMM ({titolo}): {f_nome}%"
                            if not db_run("SELECT id_u FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, chiave_somm, f"{oggi}%")):
                                st.markdown(f"<div class='therapy-container'><small>{titolo}</small><br><b>{f_nome}</b><br>{f_dose}</div>", unsafe_allow_html=True)
                                if st.button(f"REGISTRA", key=f"btn_{f_id}_{titolo}", use_container_width=True):
                                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({titolo}): {f_nome} {f_dose}", "Infermiere", firma_op), True)
                                    st.rerun()
                            else: st.success(f"✅ {f_nome} fatto")
            with t2:
                with st.form("vit_inf"):
                    c1,c2,c3 = st.columns(3); pa=c1.text_input("PA"); fc=c2.text_input("FC"); sat=c3.text_input("SatO2"); tc=c1.text_input("TC"); gl=c2.text_input("Glicemia")
                    if st.form_submit_button("REGISTRA PARAMETRI"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💓 PARAMETRI: PA:{pa} FC:{fc} Sat:{sat} TC:{tc} Gl:{gl}", "Infermiere", firma_op), True)
                        st.rerun()
            with t3:
                with st.form("consegna_inf"):
                    txt = st.text_area("Diario Infermieristico / Consegne")
                    if st.form_submit_button("SALVA IN DIARIO"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), txt, "Infermiere", firma_op), True)
                        st.rerun()
            with t4: render_stu_operativa_interattiva(p_id, ruolo_corr, firma_op)

        elif ruolo_corr == "Psicologo":
            t1, t2 = st.tabs(["🧠 COLLOQUIO", "📝 TEST/VALUTAZIONE"])
            with t1:
                with st.form("f_psi"):
                    txt = st.text_area("Sintesi Colloquio Clinico")
                    if st.form_submit_button("SALVA NOTA"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧠 {txt}", "Psicologo", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("f_test"):
                    test_n = st.text_input("Nome Test / Scala"); test_r = st.text_area("Risultato/Osservazioni")
                    if st.form_submit_button("REGISTRA VALUTAZIONE"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"📊 TEST {test_n}: {test_r}", "Psicologo", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "Assistente Sociale":
            t1, t2 = st.tabs(["🤝 RETE TERRITORIALE", "🏠 PROGETTO POST-DIMISSIONE"])
            with t1:
                with st.form("f_soc"):
                    cont = st.text_input("Ente/Contatto"); txt = st.text_area("Esito colloquio")
                    if st.form_submit_button("SALVA ATTIVITÀ"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🤝 CONTATTO {cont}: {txt}", "Assistente Sociale", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("f_prog"):
                    prog = st.text_area("Aggiornamento Progetto di Reinserimento")
                    if st.form_submit_button("AGGIORNA PROGETTO"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🏠 PROGETTO: {prog}", "Assistente Sociale", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "OPSI":
            t1, t2 = st.tabs(["🛡️ VIGILANZA", "🚨 SEGNALAZIONE CRITICITÀ"])
            with t1:
                with st.form("f_opsi"):
                    cond = st.multiselect("Stato ambiente:", ["Tranquillo", "Agitato", "Ispezione camera"]); nota = st.text_input("Note")
                    if st.form_submit_button("REGISTRA TURNO"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🛡️ VIGILANZA: {', '.join(cond)} | {nota}", "OPSI", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("f_crit"):
                    tipo = st.selectbox("Livello Criticità", ["BASSO", "MEDIO", "ALTO"]); dett = st.text_area("Dettaglio")
                    if st.form_submit_button("INVIA SEGNALAZIONE"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🚨 CRITICITÀ {tipo}: {dett}", "OPSI", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "OSS":
            with st.form("oss_f"):
                mans = st.multiselect("Mansioni:", ["Igiene", "Cambio", "Pulizia", "Letto"]); txt = st.text_area("Note")
                if st.form_submit_button("REGISTRA"): 
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧹 {', '.join(mans)} | {txt}", "OSS", firma_op), True)
                    st.rerun()

        elif ruolo_corr == "Educatore":
            t1, t2 = st.tabs(["💰 CASSA", "📝 CONSEGNA EDUCATIVA"])
            with t1:
                mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,)); saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
                st.markdown(f"<div class='cassa-card'>Saldo: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
                with st.form("cs"):
                    tp, im, cau = st.selectbox("Tipo", ["ENTRATA", "USCITA"]), st.number_input("€"), st.text_input("Causale")
                    if st.form_submit_button("REGISTRA MOVIMENTO"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, oggi, cau, im, tp, firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💰 {tp}: {im}€ - {cau}", "Educatore", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("edu_cons"):
                    txt_edu = st.text_area("Osservazioni Educative")
                    if st.form_submit_button("SALVA CONSEGNA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"📝 {txt_edu}", "Educatore", firma_op), True)
                        st.rerun()
        
        st.divider(); render_postits(p_id)

elif nav == "📅 Agenda Dinamica":
    st.markdown("<div class='section-banner'><h2>AGENDA DINAMICA REMS</h2></div>", unsafe_allow_html=True)
    c_nav1, c_nav2, c_nav3 = st.columns([1,2,1])
    with c_nav1: 
        if st.button("⬅️ Mese Precedente"): 
            st.session_state.cal_month -= 1
            if st.session_state.cal_month < 1: st.session_state.cal_month=12; st.session_state.cal_year-=1
            st.rerun()
    with c_nav2: 
        mesi_nomi = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]
        st.markdown(f"<h3 style='text-align:center;'>{mesi_nomi[st.session_state.cal_month-1]} {st.session_state.cal_year}</h3>", unsafe_allow_html=True)
    with c_nav3:
        if st.button("Mese Successivo ➡️"):
            st.session_state.cal_month += 1
            if st.session_state.cal_month > 12: st.session_state.cal_month=1; st.session_state.cal_year+=1
            st.rerun()
            
    col_cal, col_ins = st.columns([3, 1])
    with col_cal:
        start_d = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-01"
        end_d = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-31"
        evs_mese = db_run("""SELECT a.data, p.nome, a.ora, a.tipo_evento, a.mezzo, a.nota, a.accompagnatore FROM appuntamenti a JOIN pazienti p ON a.p_id=p.id WHERE a.data BETWEEN ? AND ? AND a.stato='PROGRAMMATO'""", (start_d, end_d))
        mappa_ev = {}
        for d_ev, p_n, h_ev, t_ev, m_ev, nt_ev, acc_ev in evs_mese:
            try:
                g_int = int(d_ev.split("-")[2])
                if g_int not in mappa_ev: mappa_ev[g_int] = []
                prefix = "🚗" if t_ev == "Uscita Esterna" else "🏠"
                info_popup = f"<b>{t_ev}</b><br>⏰ {h_ev}<br>👤 {p_n}<br>🚗 {m_ev}<br>🤝 Accomp: {acc_ev}<br>📝 {nt_ev}"
                tag_final = f'<div class="event-tag-html">{prefix} {p_n}<span class="tooltip-text">{info_popup}</span></div>'
                mappa_ev[g_int].append(tag_final)
            except: pass
        
        cal_html = "<table class='cal-table'><thead><tr>" + "".join([f"<th>{d}</th>" for d in ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]]) + "</tr></thead><tbody>"
        cal_obj = calendar.Calendar(firstweekday=0)
        for week in cal_obj.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month):
            cal_html += "<tr>"
            for day in week:
                if day == 0: cal_html += "<td style='background:#f8fafc;'></td>"
                else:
                    d_iso = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-{day:02d}"
                    cls_today = "today-html" if d_iso == oggi_iso else ""
                    cal_html += f"<td class='{cls_today}'><span class='day-num-html'>{day}</span>{''.join(mappa_ev.get(day, []))}</td>"
            cal_html += "</tr>"
        cal_html += "</tbody></table>"
        st.markdown(cal_html, unsafe_allow_html=True)

    with col_ins:
        st.subheader("➕ Nuovo Appuntamento")
        with st.form("add_app_cal"):
            p_l = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
            ps_sel = st.multiselect("Paziente/i", [p[1] for p in p_l])
            tipo_e = st.selectbox("Tipo", ["Uscita Esterna", "Appuntamento Interno"])
            dat, ora = st.date_input("Giorno"), st.time_input("Ora")
            mezzo_usato = st.selectbox("Macchina", ["Mitsubishi", "Fiat Qubo", "Nessuno"]) if tipo_e == "Uscita Esterna" else "Nessuno"
            accomp, not_a = st.text_input("Accompagnatore"), st.text_area("Note")
            if st.form_submit_button("REGISTRA"):
                for nome_p in ps_sel:
                    pid = [p[0] for p in p_l if p[1]==nome_p][0]
                    db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore, tipo_evento, mezzo, accompagnatore) VALUES (?,?,?,?,'PROGRAMMATO',?,?,?,?)", (pid, str(dat), str(ora)[:5], not_a, firma_op, tipo_e, mezzo_usato, accomp), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, get_now_it().strftime("%d/%m/%Y %H:%M"), f"📅 {tipo_e}: {not_a}", u['ruolo'], firma_op), True)
                st.rerun()

elif nav == "⚙️ Admin":
    st.markdown("<div class='section-banner'><h2>PANNELLO AMMINISTRAZIONE</h2></div>", unsafe_allow_html=True)
    t_ut, t_paz_att, t_paz_dim, t_diar, t_log = st.tabs(["UTENTI", "PAZIENTI ATTIVI", "ARCHIVIO DIMESSI", "DIARIO EVENTI", "📜 LOG SISTEMA"])
    
    with t_ut:
        for us, un, uc, uq in db_run("SELECT user, nome, cognome, qualifica FROM utenti"):
            c1, c2 = st.columns([0.8, 0.2]); c1.write(f"**{un} {uc}** ({uq})")
            if us != "admin" and c2.button("ELIMINA", key=f"d_{us}"): 
                db_run("DELETE FROM utenti WHERE user=?", (us,), True)
                st.rerun()

    with t_paz_att:
        with st.form("np"):
            np_val = st.text_input("Nuovo Paziente")
            if st.form_submit_button("AGGIUNGI"): 
                db_run("INSERT INTO pazienti (nome, stato) VALUES (?, 'ATTIVO')", (np_val.upper(),), True)
                st.rerun()
        for pid, pn in db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome"):
            c1, c2, c3 = st.columns([0.6, 0.2, 0.2]); c1.write(f"**{pn}**")
            if c2.button("DIMETTI", key=f"dim_{pid}"):
                db_run("UPDATE pazienti SET stato='DIMESSO' WHERE id=?", (pid,), True)
                db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid,), True)
                st.rerun()
            if c3.button("ELIMINA", key=f"dp_{pid}"): 
                db_run("DELETE FROM pazienti WHERE id=?", (pid,), True)
                st.rerun()

    with t_paz_dim:
        for pid, pn in db_run("SELECT id, nome FROM pazienti WHERE stato='DIMESSO' ORDER BY nome"):
            c1, c2 = st.columns([0.8, 0.2]); c1.write(f"📁 {pn} (Dimesso)")
            if c2.button("RIAMMETTI", key=f"re_{pid}"):
                db_run("UPDATE pazienti SET stato='ATTIVO' WHERE id=?", (pid,), True)
                st.rerun()

    with t_diar:
        lista_p = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        filtro_p = st.selectbox("Filtra per Paziente:", ["TUTTI"] + [p[1] for p in lista_p])
        query_log = "SELECT e.id_u, e.data, e.ruolo, e.op, e.nota, p.nome FROM eventi e JOIN pazienti p ON e.id = p.id"
        params_log = []
        if filtro_p != "TUTTI": query_log += " WHERE p.nome = ?"; params_log.append(filtro_p)
        tutti_log = db_run(query_log + " ORDER BY e.id_u DESC LIMIT 100", tuple(params_log))
        for lid, ldt, lru, lop, lnt, lpnome in tutti_log:
            st.text(f"[{ldt}] {lpnome} | {lop} ({lru}): {lnt}")

    with t_log:
        logs_audit = db_run("SELECT data_ora, utente, azione, dettaglio FROM logs_sistema ORDER BY id_log DESC LIMIT 200")
        if logs_audit:
            df_audit = pd.DataFrame(logs_audit, columns=["Data/Ora", "Operatore", "Azione", "Descrizione"])
            st.dataframe(df_audit, use_container_width=True)
