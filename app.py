import streamlit as st
import sqlite3
import pandas as pd
import hashlib  # <--- MANCAVA QUESTO (Risolve l'errore riga 141)
import calendar
from datetime import datetime, timedelta, timezone # <--- Risolve l'errore orario
from groq import Groq # <--- Per l'IA di Groq

# Configurazione Groq
client = Groq(api_key=st.secrets["GROQ_API_KEY"])


# --- FUNZIONE AGGIORNAMENTO DB (INTEGRALE) ---
def aggiorna_struttura_db():
    conn = sqlite3.connect('rems_final_v12.db')
    c = conn.cursor()
    # Colonne per eventi
    try: c.execute("ALTER TABLE eventi ADD COLUMN tipo_evento TEXT")
    except: pass
    try: c.execute("ALTER TABLE eventi ADD COLUMN figura_professionale TEXT")
    except: pass
    try: c.execute("ALTER TABLE eventi ADD COLUMN esito TEXT")
    except: pass
    
    # --- LOGICA DI STATO PAZIENTE (DIMISSIONI) ---
    try: c.execute("ALTER TABLE pazienti ADD COLUMN stato TEXT DEFAULT 'ATTIVO'")
    except: pass
    
    # --- NUOVE COLONNE TERAPIA PER ORARI SPECIFICI ---
    try: c.execute("ALTER TABLE terapie ADD COLUMN mat_nuovo INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE terapie ADD COLUMN pom_nuovo INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE terapie ADD COLUMN al_bisogno INTEGER DEFAULT 0")
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

# --- FUNZIONE GENERATORE RELAZIONE IA ---
def genera_relazione_ia(p_id, p_sel, g_rel):
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Sei un esperto clinico REMS. Genera relazioni formali."},
                {"role": "user", "content": f"ID: {p_id}, Paziente: {p_sel}, Note: {g_rel}"}
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Errore Groq: {str(e)}"
        

        

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v28.9.2 ---
st.set_page_config(page_title="REMS Connect ELITE PRO v28.9.2", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .user-logged { color: #00ff00 !important; font-weight: 900; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; text-align: center; }
    .sidebar-footer { color: #ffffff !important; font-size: 0.8rem; text-align: center; margin-top: 20px; opacity: 0.8; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: solidolid #ffffff22; }
    .stButton>button[kind="secondary"] { background-color: #22c55e !important; color: white !important; border: none !important; width: 100%; font-weight: 700; }
    
    .ai-box { background: #f8fafc; border: 2px solid #a855f7; border-radius: 15px; padding: 25px; margin-top: 10px; box-shadow: 0 4px 12px rgba(168, 85, 247, 0.2); }
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
    .scroll-giorni { display: flex; overflow-x: auto; gap: 4px; padding: 8px; background: #fdfdfd; }
    .quadratino { 
        min-width: 38px; height: 50px; border-radius: 4px; border: 1px solid #eee; 
        display: flex; flex-direction: column; align-items: center; justify-content: center; flex-shrink: 0;
    }
    .q-oggi { border: 2px solid #1e3a8a !important; background: #fffde7; }
    .q-num { font-size: 7px; color: #999; }
    .q-esito { font-size: 11px; font-weight: 900; }
    .q-op { font-size: 6px; color: #444; }
    .therapy-container { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px; margin-bottom: 15px; border-left: 8px solid #1e3a8a; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
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
            cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT, figura_professionale TEXT, esito TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT, mat_nuovo INTEGER DEFAULT 0, pom_nuovo INTEGER DEFAULT 0, al_bisogno INTEGER DEFAULT 0)")
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

# --- LOGICA NAVIGAZIONE ---
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
        now = get_now_it(); oggi = now.strftime("%d/%m/%Y")

        if ruolo_corr == "Psichiatra":
            t1, t2, t3, t_ai = st.tabs(["📋 DIARIO CLINICO", "💊 TERAPIA", "🩺 ESAME OBIETTIVO", "🤖 ANALISI CLINICA IA"])

            with t1:
                st.subheader("Inserimento Nota in Diario Clinico")
                with st.form("form_diario_med"):
                    nota_med = st.text_area("Valutazione clinica, colloqui, variazioni...", height=200)
                    if st.form_submit_button("REGISTRA NOTA CLINICA"):
                        if nota_med:
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                                   (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🩺 [DIARIO] {nota_med}", "Psichiatra", firma_op), True)
                            st.success("Nota registrata con successo.")
                            st.rerun()

            with t2:
                st.subheader("Gestione Terapia Farmacologica")
                terapie_attuali = db_run("SELECT id_u, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno FROM terapie WHERE p_id=?", (p_id,))
                if terapie_attuali:
                    for t in terapie_attuali:
                        c1, c2 = st.columns([4, 1])
                        c1.info(f"💊 {t[1]} - {t[2]} (M:{'✅' if t[3] else '❌'} | P:{'✅' if t[4] else '❌'} | Bisogno:{'✅' if t[5] else '❌'})")
                        if c2.button("🗑️", key=f"del_{t[0]}"):
                            db_run("DELETE FROM terapie WHERE id_u=?", (t[0],), True)
                            st.rerun()
                
                with st.expander("➕ Prescrivi Nuovo Farmaco"):
                    with st.form("nuova_terapia"):
                        f_nome = st.text_input("Nome Farmaco")
                        f_dose = st.text_input("Dosaggio")
                        col1, col2, col3 = st.columns(3)
                        m_n, p_n, a_b = col1.checkbox("M"), col2.checkbox("P"), col3.checkbox("Bisogno")
                        if st.form_submit_button("CONFERMA PRESCRIZIONE"):
                            db_run("INSERT INTO terapie (p_id, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno) VALUES (?,?,?,?,?,?)",
                                   (p_id, f_nome, f_dose, 1 if m_n else 0, 1 if p_n else 0, 1 if a_b else 0), True)
                            st.rerun()

            with t3:
                st.subheader("Esame Obiettivo")
                with st.form("esame_ob"):
                    e_o = st.text_area("Descrizione esame obiettivo e stato mentale...")
                    if st.form_submit_button("SALVA ESAME OBIETTIVO"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                               (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🧠 [E.O.] {e_o}", "Psichiatra", firma_op), True)
                        st.rerun()

            with t_ai:
                st.subheader("🤖 Analisi Clinica IA")
                if st.button("GENERA RELAZIONE CLINICA"):
                    with st.spinner("Analisi in corso..."):
                        relazione = genera_relazione_ia(p_id, p_sel, 7)
                        st.markdown(f"<div style='background:#fdf4ff; border-left:5px solid #a855f7; padding:15px; border-radius:8px; color:#581c87; white-space:pre-wrap;'><b>🧠 VALUTAZIONE IA:</b><br><br>{relazione}</div>", unsafe_allow_html=True)

        elif ruolo_corr == "Infermiere":
            import calendar 
            t1, t2, t3, t4, t_ai = st.tabs(["💊 KEEP TERAPIA", "💓 PARAMETRI", "📝 CONSEGNE", "📋 BRIEFING", "🤖 RELAZIONE IA"])
            
            with t1:
                st.subheader("Registrazione Somministrazione Farmaci")
                # RECUPERO FIRMA MIGLIORATO
                nome_loggato = st.session_state.get('user', st.session_state.get('username', 'Operatore Rems'))
                
                turno_attivo = st.selectbox("Seleziona Turno Operativo", ["8:13 (Mattina)", "16:20 (Pomeriggio)", "Al bisogno"])
                terapie_keep = db_run("SELECT id_u, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno FROM terapie WHERE p_id=?", (p_id,))
                
                for f in terapie_keep:
                    t_id_univoco, nome_f, dose_f = f[0], f[1], f[2]
                    mostra = (turno_attivo == "8:13 (Mattina)" and f[3] == 1) or (turno_attivo == "16:20 (Pomeriggio)" and f[4] == 1) or (turno_attivo == "Al bisogno" and f[5] == 1)
                    
                    if mostra:
                        st.markdown(f"### 💊 {nome_f} <small>({dose_f})</small>", unsafe_allow_html=True)
                        mese_corrente = get_now_it().strftime('%m/%Y')
                        firme = db_run("SELECT data, esito, op FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%[{t_id_univoco}]%", f"%/{mese_corrente}%"))
                        f_map = {int(d[0].split("/")[0]): {"full": d[0], "e": d[1], "o": d[2]} for d in firme if d[0] and "/" in d[0]}
                        num_giorni = calendar.monthrange(get_now_it().year, get_now_it().month)[1]
                        
                        h = "<div style='display: flex; overflow-x: auto; padding: 10px; gap: 5px;'>"
                        for d in range(1, num_giorni + 1):
                            info = f_map.get(d)
                            is_today = "border: 2px solid #2563eb;" if d == get_now_it().day else "border: 1px solid #ddd;"
                            esito_txt, col_t, bg_c = ("-", "#888", "white")
                            t_pop = f"Giorno {d}: Libero"
                            
                            if info:
                                ora_s = info['full'].split(" ")[1] if " " in info['full'] else "--:--"
                                op_f = info['o'] if info['o'] else "N.D."
                                # Rimosso \n e usato spazio semplice per compatibilità tooltip
                                if info['e'] == "A":
                                    esito_txt, col_t, bg_c = ("A", "#15803d", "#dcfce7")
                                    t_pop = f"✅ ASSUNTO - Ore: {ora_s} - Op: {op_f}"
                                elif info['e'] == "R":
                                    esito_txt, col_t, bg_c = ("R", "#b91c1c", "#fee2e2")
                                    t_pop = f"❌ RIFIUTATO - Ore: {ora_s} - Op: {op_f}"
                            
                            h += f"<div title='{t_pop}' style='min-width: 40px; height: 50px; background: {bg_c}; color: {col_t}; {is_today} border-radius: 5px; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: default; font-size: 0.8rem;'><div style='font-weight: bold;'>{d}</div><div style='font-size: 1rem;'>{esito_txt}</div></div>"
                        
                        st.markdown(h + "</div>", unsafe_allow_html=True)
                        
                        with st.popover(f"Smarca {nome_f}"):
                            c1, c2 = st.columns(2)
                            if c1.button("✅ ASSUNTO", key=f"ok_{t_id_univoco}_{turno_attivo}"):
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ [{t_id_univoco}] {nome_f} ({turno_attivo})", "Infermiere", nome_loggato, "A"), True)
                                st.rerun()
                            if c2.button("❌ RIFIUTO", key=f"ko_{t_id_univoco}_{turno_attivo}"):
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"❌ [{t_id_univoco}] RIFIUTO {nome_f} ({turno_attivo})", "Infermiere", nome_loggato, "R"), True)
                                st.rerun()
                        st.divider()

            with t2: # Parametri
                with st.form("vit_inf"):
                    c1, c2, c3 = st.columns(3)
                    p_val = c1.text_input("PA"); f_val = c2.text_input("FC"); s_val = c3.text_input("SatO2")
                    if st.form_submit_button("SALVA PARAMETRI"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"💓 PA:{p_val} FC:{f_val} Sat:{s_val}", "Infermiere", st.session_state.get('user', 'Op')), True)
                        st.rerun()

            with t3: # Consegne
                with st.form("cons_inf"):
                    txt_c = st.text_area("Nota Clinica")
                    if st.form_submit_button("SALVA CONSEGNA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"📝 [CONSEGNA] {txt_c}", "Infermiere", st.session_state.get('user', 'Op')), True)
                        st.rerun()

            with t4: # Briefing (24h)
                st.subheader("📋 Briefing Turno (Last 24h)")
                ieri = (get_now_it() - timedelta(days=1)).strftime("%d/%m/%Y %H:%M")
                b_logs = db_run("SELECT data, op, nota FROM eventi WHERE id=? AND data >= ? ORDER BY id_u DESC", (p_id, ieri))
                for d_b, op_b, nt_b in b_logs:
                    bg = "#fff1f2" if any(x in nt_b for x in ["RIFIUTO", "⚠️", "❌"]) else "#f8fafc"
                    st.markdown(f"<div style='background:{bg}; border-left:5px solid #1e3a8a; padding:10px; margin-bottom:5px; border-radius:5px;'><small><b>{d_b} - {op_b}</b></small><br>{nt_b}</div>", unsafe_allow_html=True)

            with t_ai: # Relazione IA
                st.subheader("🤖 Sintesi IA")
                if st.button("GENERA REPORT"):
                    with st.spinner("Analisi..."):
                        report = genera_relazione_ia(p_id, p_sel, 7)
                        st.markdown(f"<div style='background:#f0f7ff; border-left:5px solid #2563eb; padding:15px; border-radius:8px; color:#1e3a8a; white-space:pre-wrap;'><b>SINTESI IA:</b><br><br>{report}</div>", unsafe_allow_html=True)

        elif ruolo_corr == "Psicologo":
            t1, t2 = st.tabs(["🧠 COLLOQUIO", "📝 TEST"])
            with t1:
                with st.form("f_psi"):
                    txt = st.text_area("Sintesi Colloquio")
                    if st.form_submit_button("SALVA"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧠 {txt}", "Psicologo", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("f_test"):
                    test_n = st.text_input("Nome Test"); test_r = st.text_area("Risultato")
                    if st.form_submit_button("REGISTRA"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"📊 TEST {test_n}: {test_r}", "Psicologo", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "Assistente Sociale":
            t1, t2 = st.tabs(["🤝 RETE", "🏠 PROGETTO"])
            with t1:
                with st.form("f_soc"):
                    cont = st.text_input("Contatto"); txt = st.text_area("Esito")
                    if st.form_submit_button("SALVA"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🤝 CONTATTO {cont}: {txt}", "Assistente Sociale", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("f_prog"):
                    prog = st.text_area("Aggiornamento Progetto")
                    if st.form_submit_button("SALVA"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🏠 PROGETTO: {prog}", "Assistente Sociale", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "OPSI":
            with st.form("f_opsi"):
                cond = st.multiselect("Stato:", ["Tranquillo", "Agitato", "Ispezione"]); nota = st.text_input("Note")
                if st.form_submit_button("REGISTRA"): 
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🛡️ VIGILANZA: {', '.join(cond)} | {nota}", "OPSI", firma_op), True)
                    st.rerun()

        elif ruolo_corr == "OSS":
            with st.form("oss_f"):
                mans = st.multiselect("Mansioni:", ["Igiene", "Cambio", "Pulizia", "Letto"]); txt = st.text_area("Note")
                if st.form_submit_button("REGISTRA"): 
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧹 {', '.join(mans)} | {txt}", "OSS", firma_op), True)
                    st.rerun()

        elif ruolo_corr == "Educatore":
            t1, t2 = st.tabs(["💰 CASSA", "📝 CONSEGNA"])
            with t1:
                mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,)); saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
                st.markdown(f"<div class='cassa-card'>Saldo: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
                with st.form("cs"):
                    tp, im, cau = st.selectbox("Tipo", ["ENTRATA", "USCITA"]), st.number_input("€"), st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, oggi, cau, im, tp, firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💰 {tp}: {im}€ - {cau}", "Educatore", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("edu_cons"):
                    txt_edu = st.text_area("Osservazioni")
                    if st.form_submit_button("SALVA"):
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
                tag_final = f'<div class="event-tag-html">{prefix} {p_n}<span class="tooltip-text"><b>{t_ev}</b><br>⏰ {h_ev}<br>🚗 {m_ev}<br>📝 {nt_ev}</span></div>'
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
        st.markdown(cal_html + "</tbody></table>", unsafe_allow_html=True)

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
        
        st.divider()
        st.subheader("📋 Lista Scadenze")
        agenda_list = db_run("SELECT a.id_u, a.data, a.ora, p.nome, a.tipo_evento FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.data >= ? AND a.stato='PROGRAMMATO' ORDER BY a.data, a.ora", (oggi_iso,))
        for aid, adt, ahr, apn, atev in agenda_list:
            st.markdown(f"**{adt} {ahr}** - {apn}<br>{atev}", unsafe_allow_html=True)
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
    t_ut, t_paz_att, t_paz_dim, t_diar, t_log = st.tabs(["UTENTI", "PAZIENTI ATTIVI", "ARCHIVIO", "DIARIO EVENTI", "📜 LOG"])
    
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
            c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
            c1.write(f"**{pn}**")
            if c2.button("DIMETTI", key=f"dim_{pid}"):
                db_run("UPDATE pazienti SET stato='DIMESSO' WHERE id=?", (pid,), True)
                db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid,), True)
                st.rerun()
            if c3.button("ELIMINA", key=f"dp_{pid}"): 
                db_run("DELETE FROM pazienti WHERE id=?", (pid,), True)
                st.rerun()

    with t_paz_dim:
        for pid, pn in db_run("SELECT id, nome FROM pazienti WHERE stato='DIMESSO' ORDER BY nome"):
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"📁 {pn}")
            if c2.button("RIAMMETTI", key=f"re_{pid}"):
                db_run("UPDATE pazienti SET stato='ATTIVO' WHERE id=?", (pid,), True)
                st.rerun()

    with t_diar:
        lista_p = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        filtro_p = st.selectbox("Filtra per Paziente:", ["TUTTI"] + [p[1] for p in lista_p])
        query_log = "SELECT e.data, e.ruolo, e.op, e.nota, p.nome FROM eventi e JOIN pazienti p ON e.id = p.id"
        params_log = []
        if filtro_p != "TUTTI": query_log += " WHERE p.nome = ?"; params_log.append(filtro_p)
        tutti_log = db_run(query_log + " ORDER BY e.id_u DESC LIMIT 100", tuple(params_log))
        for ldt, lru, lop, lnt, lpnome in tutti_log:
            st.text(f"[{ldt}] {lpnome} | {lop} ({lru}): {lnt}")

    with t_log:
        logs_audit = db_run("SELECT data_ora, utente, azione, dettaglio FROM logs_sistema ORDER BY id_log DESC LIMIT 200")
        if logs_audit:
            st.dataframe(pd.DataFrame(logs_audit, columns=["Data/Ora", "Operatore", "Azione", "Descrizione"]), use_container_width=True)
