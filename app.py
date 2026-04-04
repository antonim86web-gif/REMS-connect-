import streamlit as st
import sqlite3
import pandas as pd
import hashlib  # <--- MANCAVA QUESTO (Risolve l'errore riga 141)
from datetime import datetime, timedelta, timezone # <--- Risolve l'errore orario
from groq import Groq # <--- Per l'IA di Groq

# Configurazione Groq
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.markdown("""
<style>
    /* 1. SIDEBAR DEEP NIGHT */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #000000 100%) !important;
        box-shadow: 15px 0 35px rgba(0,0,0,0.9) !important;
    }

    /* 2. KILLER PALLINI */
    [data-testid="stMarker"], 
    [data-baseweb="radio"] div:first-child,
    [data-testid="stSidebar"] input[type="radio"] {
        display: none !important;
    }

    /* 3. CARD DEL MENU - TESTO BIANCO E GRANDE */
    div[role="radiogroup"] label {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        padding: 18px 20px !important; /* Più spazio interno */
        border-radius: 12px !important;
        margin-bottom: 12px !important;
        color: #ffffff !important; /* TESTO BIANCO PURO */
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        display: flex !important;
        width: 100% !important;
        cursor: pointer !important;
    }

    /* 4. EFFETTO HOVER */
    div[role="radiogroup"] label:hover {
        background: rgba(52, 152, 219, 0.1) !important;
        border-color: #3498db !important;
        transform: translateX(5px) !important; /* Scivola un po' a destra */
    }

    /* 5. TASTO ATTIVO (FLOATING) */
    div[role="radiogroup"] label:has(input:checked) {
        background: rgba(52, 152, 219, 0.25) !important;
        border-color: #3498db !important;
        color: #ffffff !important;
        transform: translateY(-6px) scale(1.02) !important; /* ALZA E INGRANDISCE */
        box-shadow: 0 15px 30px rgba(52, 152, 219, 0.4) !important;
    }

    /* 6. DIMENSIONE CARATTERI */
    div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {
        margin-left: 0px !important;
        font-size: 18px !important; /* SCRITTE BELLE GRANDI */
        font-weight: 600 !important;
        letter-spacing: 0.5px !important;
    }

    /* TITOLI SIDEBAR */
    .sidebar-title { 
        color: #ffffff !important; 
        font-size: 1.8rem; 
        font-weight: 800; 
        text-align: center;
    }
    .user-logged { 
        color: #00ff00 !important; 
        text-shadow: 0 0 10px rgba(0,255,0,0.3);
    }
</style>
""", unsafe_allow_html=True)


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
            t1, t2, t3, t_ai = st.tabs(["➕ Nuova Prescrizione", "📝 Gestione Terapie", "🩺 CONSEGNE MEDICHE", "🤖 RELAZIONE IA"])
            with t1:
                with st.form("f_ps"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    st.write("**Fasce Orarie**")
                    c1,c2,c3 = st.columns(3)
                    m, p, b = c1.checkbox("8:13 (Mattina)"), c2.checkbox("16:20 (Pomeriggio)"), c3.checkbox("Al bisogno")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno, medico) VALUES (?,?,?,?,?,?,?)", 
                               (p_id, f, d, int(m), int(p), int(b), firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"➕ Prescritto: {f} {d}", "Psichiatra", firma_op), True)
                        st.rerun()
            with t2:
                for tid, fn, ds, m_v, p_v, b_v in db_run("SELECT id_u, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno FROM terapie WHERE p_id=?", (p_id,)):
                    with st.expander(f"Modifica: {fn}"):
                        with st.form(key=f"m_{tid}"):
                            nf, nd = st.text_input("Farmaco", fn), st.text_input("Dose", ds)
                            cc1,cc2,cc3 = st.columns(3)
                            nm, np, nb = cc1.checkbox("8:13", bool(m_v)), cc2.checkbox("16:20", bool(p_v)), cc3.checkbox("Al bisogno", bool(b_v))
                            if st.form_submit_button("AGGIORNA"): 
                                db_run("UPDATE terapie SET farmaco=?, dose=?, mat_nuovo=?, pom_nuovo=?, al_bisogno=? WHERE id_u=?", (nf, nd, int(nm), int(np), int(nb), tid), True)
                                st.rerun()
                            if st.form_submit_button("SOSPENDE"): 
                                db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
                                st.rerun()
            with t3:
                with st.form("f_cons_med"):
                    nota_medica = st.text_area("Indicazioni Cliniche")
                    if st.form_submit_button("SALVA CONSEGNA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🩺 MED: {nota_medica}", "Psichiatra", firma_op), True)
                        st.rerun()
            with t_ai:
                st.markdown("<div class='ai-box'>", unsafe_allow_html=True)
                st.subheader("🪄 Analisi Clinica IA")
         
