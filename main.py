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
    
    /* STILE TABELLA TERAPIA MENSILE */
    .stu-container { overflow-x: auto; background: white; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; }
    .stu-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
    .stu-table th, .stu-table td { border: 1px solid #e2e8f0; padding: 6px; text-align: center; }
    .stu-table th { background: #f8fafc; color: #1e3a8a; font-weight: 800; }
    .stu-table td:first-child { text-align: left; background: #f1f5f9; font-weight: 700; position: sticky; left: 0; z-index: 10; }
    
    .cell-a { background: #22c55e !important; color: white !important; font-weight: 900; border-radius: 4px; cursor: help; padding: 2px 6px; }
    .cell-r { background: #ef4444 !important; color: white !important; font-weight: 900; border-radius: 4px; cursor: help; padding: 2px 6px; }
    .cell-p { color: #94a3b8; font-style: italic; font-size: 0.7rem; }

    /* TOOLTIP POPUP */
    .stu-cell { position: relative; display: inline-block; }
    .stu-cell .tooltip-stu { visibility: hidden; width: 180px; background-color: #0f172a; color: #fff; text-align: center; border-radius: 6px; padding: 8px; position: absolute; z-index: 100; bottom: 125%; left: 50%; margin-left: -90px; opacity: 0; transition: opacity 0.3s; font-size: 0.7rem; line-height: 1.2; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
    .stu-cell:hover .tooltip-stu { visibility: visible; opacity: 1; }

    .alert-sidebar { background: #ef4444; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: 800; margin: 10px 5px; border: 2px solid white; animation: pulse 2s infinite; }
    @keyframes pulse { 0% {transform: scale(1);} 50% {transform: scale(1.02);} 100% {transform: scale(1);} }

    .cal-table { width:100%; border-collapse: collapse; table-layout: fixed; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .cal-table th { background: #f1f5f9; padding: 10px; color: #1e3a8a; font-weight: 800; border: 1px solid #e2e8f0; font-size: 0.85rem; }
    .cal-table td { border: 1px solid #e2e8f0; vertical-align: top; height: 150px; padding: 5px; position: relative; overflow: visible !important; }
    .day-num-html { font-weight: 900; color: #64748b; font-size: 0.8rem; margin-bottom: 4px; display: block; }
    
    .event-tag-html { font-size: 0.65rem; background: #dbeafe; color: #1e40af; padding: 2px 4px; border-radius: 4px; margin-bottom: 3px; border-left: 3px solid #2563eb; line-height: 1.1; position: relative; cursor: help; }
    .event-tag-html .tooltip-text { visibility: hidden; width: 220px; background-color: #1e3a8a; color: #fff; text-align: left; border-radius: 8px; padding: 12px; position: absolute; z-index: 9999 !important; bottom: 125%; left: 0%; opacity: 0; transition: opacity 0.3s; box-shadow: 0 8px 20px rgba(0,0,0,0.4); font-size: 0.75rem; line-height: 1.4; white-space: normal; border: 1px solid #ffffff44; pointer-events: none; }
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
            cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
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
oggi_dt = get_now_it()
oggi_iso = oggi_dt.strftime("%Y-%m-%d")
oggi_str = oggi_dt.strftime("%d/%m/%Y")

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
            render_postits(pid)

elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO EQUIPE</h2></div>", unsafe_allow_html=True)
    ruolo_corr = u['ruolo']
    if u['ruolo'] == "Admin": ruolo_corr = st.selectbox("Simula Figura:", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
    p_lista = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        
        # --- LOGICA S.T.U. MENSILE ---
        month_days = calendar.monthrange(oggi_dt.year, oggi_dt.month)[1]
        terapie_attive = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
        
        if ruolo_corr == "Psichiatra":
            t1, t2, t3 = st.tabs(["➕ Nuova Prescrizione", "📝 Foglio Terapia Mensile", "🩺 CONSEGNE MEDICHE"])
            with t1:
                with st.form("f_ps"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f.upper(), d, int(m), int(p), int(n), firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_str + " " + oggi_dt.strftime("%H:%M"), f"➕ Prescritto: {f.upper()} {d}", "Psichiatra", firma_op), True)
                        st.rerun()
            with t2:
                st.markdown(f"### 📋 S.T.U. {p_sel} - {calendar.month_name[oggi_dt.month]} {oggi_dt.year}")
                if terapie_attive:
                    html_stu = "<div class='stu-container'><table class='stu-table'><thead><tr><th>Farmaco / Orario</th>"
                    for d in range(1, month_days + 1): html_stu += f"<th>{d}</th>"
                    html_stu += "<th>Azioni</th></tr></thead><tbody>"
                    
                    for tid, fn, ds, mv, pv, nv in terapie_attive:
                        for turn, turn_val in [("MAT", mv), ("POM", pv), ("NOT", nv)]:
                            if turn_val:
                                html_stu += f"<tr><td><b>{fn}</b><br><small>{ds} ({turn})</small></td>"
                                for day in range(1, month_days + 1):
                                    day_str = f"{day:02d}/{oggi_dt.month:02d}/{oggi_dt.year}"
                                    check = db_run("SELECT op, data, nota FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%SOMMINISTRAZIONE [{turn}] {fn}%", f"{day_str}%"))
                                    if check:
                                        op_f, d_f, n_f = check[0]
                                        h_f = d_f.split(" ")[1]
                                        cls_c = "cell-a" if "ASSUNTA" in n_f else "cell-r"
                                        label_c = "A" if "ASSUNTA" in n_f else "R"
                                        html_stu += f"<td><div class='stu-cell'><span class='{cls_c}'>{label_c}</span><span class='tooltip-stu'>Firma: {op_f}<br>Ore: {h_f}</span></div></td>"
                                    else:
                                        html_stu += "<td><span class='cell-p'>-</span></td>"
                                html_stu += f"<td>Sospendi</td></tr>"
                    html_stu += "</tbody></table></div>"
                    st.markdown(html_stu, unsafe_allow_html=True)
            with t3:
                with st.form("f_cons_med"):
                    nota_medica = st.text_area("Indicazioni Cliniche / Note Diagnostiche")
                    if st.form_submit_button("SALVA CONSEGNA MEDICA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_str + " " + oggi_dt.strftime("%H:%M"), f"🩺 MED: {nota_medica}", "Psichiatra", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 SOMMINISTRAZIONE S.T.U.", "💓 PARAMETRI", "📝 CONSEGNE"])
            with t1:
                st.markdown(f"### 📋 Somministrazione: {p_sel} (Oggi: {oggi_str})")
                for tid, fn, ds, mv, pv, nv in terapie_attive:
                    st.markdown(f"---")
                    c_info, c_m, c_p, c_n = st.columns([2,1,1,1])
                    c_info.markdown(f"**{fn}** \n<small>{ds}</small>", unsafe_allow_html=True)
                    
                    for turn_label, turn_active in [("MAT", mv), ("POM", pv), ("NOT", nv)]:
                        curr_col = c_m if turn_label == "MAT" else (c_p if turn_label == "POM" else c_n)
                        with curr_col:
                            if turn_active:
                                check = db_run("SELECT op, data, nota FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%SOMMINISTRAZIONE [{turn_label}] {fn}%", f"{oggi_str}%"))
                                if check:
                                    op_f, d_f, n_f = check[0]
                                    h_f = d_f.split(" ")[1]
                                    label_f = "✅ A" if "ASSUNTA" in n_f else "❌ R"
                                    bg_f = "#22c55e" if "ASSUNTA" in n_f else "#ef4444"
                                    st.markdown(f"<div class='stu-cell'><span style='background:{bg_f}; color:white; padding:4px 8px; border-radius:4px; font-weight:bold;'>{label_f}</span><span class='tooltip-stu'>Firma: {op_f}<br>Ore: {h_f}</span></div>", unsafe_allow_html=True)
                                else:
                                    ca, cr = st.columns(2)
                                    if ca.button("A", key=f"A_{tid}_{turn_label}", help="Assunta"):
                                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_str + " " + oggi_dt.strftime("%H:%M"), f"✔️ SOMMINISTRAZIONE [{turn_label}] {fn}: STATO ASSUNTA", "Infermiere", firma_op), True)
                                        st.rerun()
                                    if cr.button("R", key=f"R_{tid}_{turn_label}", help="Rifiutata"):
                                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_str + " " + oggi_dt.strftime("%H:%M"), f"❌ SOMMINISTRAZIONE [{turn_label}] {fn}: STATO RIFIUTATA", "Infermiere", firma_op), True)
                                        st.rerun()
            with t2:
                with st.form("vit"):
                    pa,fc,sat,tc,gl=st.text_input("PA"),st.text_input("FC"),st.text_input("SatO2"),st.text_input("TC"),st.text_input("Glicemia")
                    if st.form_submit_button("REGISTRA"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_str + " " + oggi_dt.strftime("%H:%M"), f"💓 PA:{pa} FC:{fc} Sat:{sat} TC:{tc} Gl:{gl}", "Infermiere", firma_op), True)
                        st.rerun()
            with t3:
                with st.form("ni"):
                    txt = st.text_area("Consegna Clinica"); 
                    if st.form_submit_button("SALVA"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_str + " " + oggi_dt.strftime("%H:%M"), txt, "Infermiere", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "Psicologo":
            t1, t2 = st.tabs(["🧠 COLLOQUIO", "📝 TEST/VALUTAZIONE"])
            with t1:
                with st.form("f_psi"):
                    txt = st.text_area("Sintesi Colloquio Clinico")
                    if st.form_submit_button("SALVA NOTA"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_str + " " + oggi_dt.strftime("%H:%M"), f"🧠 {txt}", "Psicologo", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("f_test"):
                    test_n = st.text_input("Nome Test / Scala"); test_r = st.text_area("Risultato/Osservazioni")
                    if st.form_submit_button("REGISTRA VALUTAZIONE"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_str + " " + oggi_dt.strftime("%H:%M"), f"📊 TEST {test_n}: {test_r}", "Psicologo", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "Assistente Sociale":
            t1, t2 = st.tabs(["🤝 RETE TERRITORIALE", "🏠 PROGETTO POST-DIMISSIONE"])
            with t1:
                with st.form("f_soc"):
                    cont = st.text_input("Ente/Contatto"); txt = st.text_area("Esito colloquio")
                    if st.form_submit_button("SALVA ATTIVITÀ"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_str + " " + oggi_dt.strftime("%H:%M"), f"🤝 CONTATTO {cont}: {txt}", "Assistente Sociale", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("f_prog"):
                    prog = st.text_area("Aggiornamento Progetto di Reinserimento")
                    if st.form_submit_button("AGGIORNA PROGETTO"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_str + " " + oggi_dt.strftime("%H:%M"), f"🏠 PROGETTO: {prog}", "Assistente Sociale", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "OPSI":
            t1, t2 = st.tabs(["🛡️ VIGILANZA", "🚨 SEGNALAZIONE CRITICITÀ"])
            with t1:
                with st.form("f_opsi"):
                    cond = st.multiselect("Stato ambiente:", ["Tranquillo", "Agitato", "Ispezione camera"]); nota = st.text_input("Note")
                    if st.form_submit_button("REGISTRA TURNO"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_str + " " + oggi_dt.strftime("%H:%M"), f"🛡️ VIGILANZA: {', '.join(cond)} | {nota}", "OPSI", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("f_crit"):
                    tipo = st.selectbox("Livello Criticità", ["BASSO", "MEDIO", "ALTO"]); dett = st.text_area("Dettaglio")
                    if st.form_submit_button("INVIA SEGNALAZIONE"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_str + " " + oggi_dt.strftime("%H:%M"), f"🚨 CRITICITÀ {tipo}: {dett}", "OPSI", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "OSS":
            with st.form("oss_f"):
                mans = st.multiselect("Mansioni:", ["Igiene", "Cambio", "Pulizia", "Letto"]); txt = st.text_area("Note")
                if st.form_submit_button("REGISTRA"): 
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_str + " " + oggi_dt.strftime("%H:%M"), f"🧹 {', '.join(mans)} | {txt}", "OSS", firma_op), True)
                    st.rerun()

        elif ruolo_corr == "Educatore":
            t1, t2 = st.tabs(["💰 CASSA", "📝 CONSEGNA EDUCATIVA"])
            with t1:
                mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,)); saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
                st.markdown(f"<div class='cassa-card'>Saldo: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
                with st.form("cs"):
                    tp, im, cau = st.selectbox("Tipo", ["ENTRATA", "USCITA"]), st.number_input("€"), st.text_input("Causale")
                    if st.form_submit_button("REGISTRA MOVIMENTO"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, oggi_str, cau, im, tp, firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_str + " " + oggi_dt.strftime("%H:%M"), f"💰 {tp}: {im}€ - {cau}", "Educatore", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("edu_cons"):
                    txt_edu = st.text_area("Osservazioni Educative")
                    if st.form_submit_button("SALVA CONSEGNA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_str + " " + oggi_dt.strftime("%H:%M"), f"📝 {txt_edu}", "Educatore", firma_op), True)
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
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, oggi_str + " " + oggi_dt.strftime("%H:%M"), f"📅 {tipo_e}: {not_a}", u['ruolo'], firma_op), True)
                st.rerun()
        st.divider()
        st.subheader("📋 Lista Scadenze")
        agenda_list = db_run("SELECT a.id_u, a.data, a.ora, p.nome, a.tipo_evento FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.data >= ? AND a.stato='PROGRAMMATO' ORDER BY a.data, a.ora", (oggi_iso,))
        for aid, adt, ahr, apn, atev in agenda_list:
            with st.container():
                st.markdown(f"**{adt} {ahr}** - {atev}<br>{apn}", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("FATTO", key=f"done_{aid}"): 
                    db_run("UPDATE appuntamenti SET stato='COMPLETATO' WHERE id_u=?", (aid,), True)
                    st.rerun()
                if c2.button("ELIMINA", key=f"del_{aid}"):
                    db_run("DELETE FROM appuntamenti WHERE id_u=?", (aid,), True)
                    st.rerun()
            st.markdown("---")

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
        st.subheader("Gestione Pazienti in Reparto")
        with st.form("np"):
            np_val = st.text_input("Nuovo Paziente")
            if st.form_submit_button("AGGIUNGI"): 
                db_run("INSERT INTO pazienti (nome, stato) VALUES (?, 'ATTIVO')", (np_val.upper(),), True)
                st.rerun()
        for pid, pn in db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome"):
            c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
            c1.write(f"**{pn}**")
            if c2.button("DIMETTI", key=f"dim_{pid}"):
                db_run("UPDATE pazienti SET stato='DIMESSO' WHERE id=?", (pid,), True)
                db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid,), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, oggi_str + " " + oggi_dt.strftime("%H:%M"), "🚪 PAZIENTE DIMESSO DALLA STRUTTURA", "SISTEMA", firma_op), True)
                st.rerun()
            if c3.button("ELIMINA", key=f"dp_{pid}"): 
                db_run("DELETE FROM pazienti WHERE id=?", (pid,), True)
                db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid,), True)
                st.rerun()

    with t_paz_dim:
        st.subheader("Pazienti Dimessi (Archivio)")
        for pid, pn in db_run("SELECT id, nome FROM pazienti WHERE stato='DIMESSO' ORDER BY nome"):
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"📁 {pn} (Dimesso)")
            if c2.button("RIAMMETTI", key=f"re_{pid}"):
                db_run("UPDATE pazienti SET stato='ATTIVO' WHERE id=?", (pid,), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, oggi_str + " " + oggi_dt.strftime("%H:%M"), "🔄 PAZIENTE RIAMMESSO IN STRUTTURA", "SISTEMA", firma_op), True)
                st.rerun()

    with t_diar:
        lista_p = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        filtro_p = st.selectbox("Filtra per Paziente:", ["TUTTI"] + [p[1] for p in lista_p])
        query_log = "SELECT e.id_u, e.data, e.ruolo, e.op, e.nota, p.nome FROM eventi e JOIN pazienti p ON e.id = p.id"
        params_log = []
        if filtro_p != "TUTTI": query_log += " WHERE p.nome = ?"; params_log.append(filtro_p)
        tutti_log = db_run(query_log + " ORDER BY e.id_u DESC LIMIT 100", tuple(params_log))
        if st.button("🚨 RESET LOG EVENTI"): 
            db_run("DELETE FROM eventi", (), True)
            st.rerun()
        for lid, ldt, lru, lop, lnt, lpnome in tutti_log:
            st.text(f"[{ldt}] {lpnome} | {lop} ({lru}): {lnt}")

    with t_log:
        st.subheader("📜 Log Tracciabilità Sistema")
        logs_audit = db_run("SELECT data_ora, utente, azione, dettaglio FROM logs_sistema ORDER BY id_log DESC LIMIT 200")
        if logs_audit:
            df_audit = pd.DataFrame(logs_audit, columns=["Data/Ora", "Operatore", "Azione", "Descrizione"])
            st.dataframe(df_audit, use_container_width=True)
            if st.button("Svuota Log Audit"):
                db_run("DELETE FROM logs_sistema", (), True)
                st.rerun()
