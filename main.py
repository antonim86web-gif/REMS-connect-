import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar
import re

# --- 1. COSTANTI E CONFIGURAZIONE ORARIA ---
APP_VERSION = "REMS Connect ELITE PRO v29.0"
DB_NAME = "rems_final_v12.db"

def get_now_it():
    """Ritorna l'orario corrente sincronizzato con il fuso italiano (UTC+2)."""
    return datetime.now(timezone.utc) + timedelta(hours=2)

# --- 2. SETUP INTERFACCIA E CSS ESTESO ---
st.set_page_config(
    page_title=APP_VERSION, 
    layout="wide", 
    page_icon="🏥",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Global Styles */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Sidebar Layout */
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; min-width: 300px !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { 
        color: #ffffff !important; 
        font-size: 1.8rem !important; 
        font-weight: 800 !important; 
        text-align: center; 
        margin-bottom: 1.5rem; 
        padding-top: 20px; 
        border-bottom: 2px solid #ffffff33; 
    }
    .user-logged { 
        color: #22c55e !important; 
        font-weight: 800; 
        font-size: 1rem; 
        text-transform: uppercase; 
        margin-bottom: 25px; 
        text-align: center;
        background: rgba(255,255,255,0.1);
        padding: 10px;
        border-radius: 8px;
    }

    /* Section Header */
    .section-banner { 
        background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
        color: white !important; 
        padding: 40px; 
        border-radius: 15px; 
        margin-bottom: 35px; 
        text-align: center; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.2); 
        border: 1px solid #ffffff22; 
    }

    /* Buttons Customization */
    .stButton>button { border-radius: 8px !important; transition: all 0.3s !important; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
    
    /* Agenda & Calendar Table */
    .cal-table { width:100%; border-collapse: separate; border-spacing: 2px; background: #f8fafc; border-radius: 12px; overflow: hidden; }
    .cal-table th { background: #1e3a8a; padding: 15px; color: white; font-weight: 700; text-transform: uppercase; font-size: 0.8rem; }
    .cal-table td { border: 1px solid #e2e8f0; vertical-align: top; height: 140px; padding: 8px; background: white; transition: 0.2s; }
    .cal-table td:hover { background: #f1f5f9; }
    .day-num-html { font-weight: 900; color: #94a3b8; font-size: 0.85rem; margin-bottom: 8px; display: block; }
    .event-tag-html { 
        font-size: 0.7rem; 
        background: #eff6ff; 
        color: #1e40af; 
        padding: 4px 8px; 
        border-radius: 6px; 
        margin-bottom: 4px; 
        border-left: 4px solid #3b82f6; 
        font-weight: 600;
    }
    .today-html { border: 3px solid #22c55e !important; background-color: #f0fdf4 !important; }

    /* Diario Clinico (Post-it) */
    .postit { padding: 20px; border-radius: 12px; margin-bottom: 15px; border-left: 12px solid; box-shadow: 0 4px 12px rgba(0,0,0,0.05); background: white; }
    .postit-header { display: flex; justify-content: space-between; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; font-weight: 700; font-size: 0.8rem; }
    
    .role-psichiatra { border-color: #ef4444; } 
    .role-infermiere { border-color: #3b82f6; } 
    .role-educatore { border-color: #10b981; }  
    .role-oss { border-color: #64748b; }
    .role-psicologo { border-color: #a855f7; }
    .role-sociale { border-color: #f59e0b; }
    .role-opsi { border-color: #0f172a; border-style: dashed; }

    /* Mappa Posti Letto */
    .map-reparto { background: #ffffff; padding: 20px; border-radius: 15px; border: 1px solid #e2e8f0; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .reparto-title { font-size: 1.5rem; text-align: center; color: #1e3a8a; font-weight: 900; margin-bottom: 20px; }
    .stanza-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; }
    .stanza-tile { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 15px; border-top: 5px solid #94a3b8; }
    .stanza-header { font-weight: 800; color: #1e3a8a; margin-bottom: 10px; font-size: 1rem; }
    .letto-slot { background: white; margin-top: 5px; padding: 8px; border-radius: 6px; border: 1px solid #eee; font-size: 0.85rem; }
    
    /* Stats Cards */
    .stat-card { background: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; text-align: center; }
    .stat-val { font-size: 2rem; font-weight: 900; color: #1e3a8a; }
    .stat-lbl { color: #64748b; font-size: 0.8rem; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# --- 3. DATABASE ENGINE & BUSINESS LOGIC ---
def hash_pw(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

def db_run(query, params=(), commit=False):
    """Esecutore universale di query con gestione eccezioni e creazione schema."""
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        try:
            # Tabelle Base
            cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
            
            # Tabelle Moduli
            cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
            cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
            cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT, tipo_evento TEXT, mezzo TEXT, accompagnatore TEXT)")
            
            # Tabelle Gestione Posti Letto
            cur.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT, FOREIGN KEY(p_id) REFERENCES pazienti(id))")
            
            # Tabelle Accessorie
            cur.execute("CREATE TABLE IF NOT EXISTS agenda_notes (id_nota INTEGER PRIMARY KEY AUTOINCREMENT, mese INTEGER, anno INTEGER, testo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS logs (timestamp TEXT, user TEXT, azione TEXT)")

            # Inizializzazione Dati Default
            if cur.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
                cur.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("perito2026"), "SUPER", "USER", "Admin"))
            
            if cur.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
                for i in range(1, 7): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"A{i}", "A", "ISOLAMENTO" if i==6 else "STANDARD"))
                for i in range(1, 11): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"B{i}", "B", "ISOLAMENTO" if i==10 else "STANDARD"))
            
            conn.commit()
            
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        
        except sqlite3.Error as e:
            st.error(f"Errore Database: {e}")
            return []

def log_action(user, action):
    now = get_now_it().strftime("%Y-%m-%d %H:%M:%S")
    db_run("INSERT INTO logs (timestamp, user, azione) VALUES (?,?,?)", (now, user, action), True)

def validate_input(text, min_len=3):
    if not text or len(text) < min_len: return False
    return True

# --- 4. RENDERIZZAZIONE COMPONENTI UI ---
def render_postits(p_id=None, limit=50, filter_role=None):
    """Genera i blocchi nota in stile post-it per il diario clinico."""
    query = "SELECT data, ruolo, op, nota FROM eventi WHERE 1=1"
    params = []
    if p_id: 
        query += " AND id=?"
        params.append(p_id)
    if filter_role: 
        query += " AND ruolo=?"
        params.append(filter_role)
    
    res = db_run(query + " ORDER BY id_u DESC LIMIT ?", tuple(params + [limit]))
    
    if not res:
        st.info("Nessun evento registrato per questo paziente.")
        return

    for d, r, o, nt in res:
        role_map = {
            "Psichiatra":"psichiatra", "Infermiere":"infermiere", 
            "Educatore":"educatore", "OSS":"oss", 
            "Psicologo":"psicologo", "Assistente Sociale":"sociale", "OPSI":"opsi"
        }
        cls = f"role-{role_map.get(r, 'oss')}"
        st.markdown(f'''
            <div class="postit {cls}">
                <div class="postit-header">
                    <span>👤 {o}</span>
                    <span>📅 {d}</span>
                </div>
                <div style="font-size: 0.95rem; color: #334155;">{nt}</div>
            </div>
        ''', unsafe_allow_html=True)

# --- 5. LOGICA DI AUTENTICAZIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if 'cal_month' not in st.session_state: st.session_state.cal_month = get_now_it().month
if 'cal_year' not in st.session_state: st.session_state.cal_year = get_now_it().year

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h1>🏥 REMS CONNECT</h1><p>Sistema Gestionale Sanitario Avanzato v29.0</p></div>", unsafe_allow_html=True)
    
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("🔑 Accesso Operatore")
        with st.form("login_form"):
            u_i = st.text_input("Username").lower().strip()
            p_i = st.text_input("Password", type="password")
            if st.form_submit_button("ENTRA NEL SISTEMA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
                if res: 
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_i}
                    log_action(u_i, "Login effettuato")
                    st.rerun()
                else: 
                    st.error("Credenziali non valide.")
    
    with col_r:
        st.subheader("📝 Registrazione Nuovo Staff")
        with st.form("reg_form"):
            ru = st.text_input("Scegli Username").lower().strip()
            rp = st.text_input("Password", type="password")
            rn = st.text_input("Nome")
            rc = st.text_input("Cognome")
            rq = st.selectbox("Qualifica Professionale", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
            if st.form_submit_button("CREA ACCOUNT"):
                if validate_input(ru) and validate_input(rp, 6) and rn and rc:
                    db_run("INSERT INTO utenti (user, pwd, nome, cognome, qualifica) VALUES (?,?,?,?,?)", (ru, hash_pw(rp), rn.capitalize(), rc.capitalize(), rq), True)
                    st.success("Account creato con successo! Ora puoi accedere.")
                else:
                    st.warning("Compilare tutti i campi (Password min. 6 caratteri).")
    st.stop()

# --- 6. VARIABILI GLOBALI DI SESSIONE ---
user = st.session_state.user_session
firma_op = f"{user['nome']} {user['cognome']} ({user['ruolo']})"
oggi_iso = get_now_it().strftime("%Y-%m-%d")
oggi_full = get_now_it().strftime("%d/%m/%Y %H:%M")

# --- 7. SIDEBAR E NAVIGAZIONE ---
st.sidebar.markdown("<div class='sidebar-title'>REMS Connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-logged'>● {user['nome']} {user['cognome']}</div>", unsafe_allow_html=True)

nav_options = ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Posti Letto"]
if user['ruolo'] == "Admin": 
    nav_options.append("⚙️ Amministrazione")

nav = st.sidebar.radio("MENU PRINCIPALE", nav_options)

st.sidebar.divider()
if st.sidebar.button("🚪 CHIUDI SESSIONE"):
    log_action(user['uid'], "Logout effettuato")
    st.session_state.user_session = None
    st.rerun()

# --- 8. MODULO MONITORAGGIO (CRUSCOTTO STATISTICO) ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DASHBOARD MONITORAGGIO CLINICO</h2></div>", unsafe_allow_html=True)
    
    # Calcolo Statistiche
    tot_paz = db_run("SELECT COUNT(*) FROM pazienti")[0][0]
    posti_occ = db_run("SELECT COUNT(*) FROM assegnazioni")[0][0]
    ev_oggi = db_run("SELECT COUNT(*) FROM eventi WHERE data LIKE ?", (f"%{get_now_it().strftime('%d/%m/%Y')}%",))[0][0]
    
    s1, s2, s3 = st.columns(3)
    with s1: st.markdown(f"<div class='stat-card'><div class='stat-val'>{tot_paz}</div><div class='stat-lbl'>Pazienti Totali</div></div>", unsafe_allow_html=True)
    with s2: st.markdown(f"<div class='stat-card'><div class='stat-val'>{posti_occ}/32</div><div class='stat-lbl'>Posti Occupati</div></div>", unsafe_allow_html=True)
    with s3: st.markdown(f"<div class='stat-card'><div class='stat-val'>{ev_oggi}</div><div class='stat-lbl'>Note Cliniche Oggi</div></div>", unsafe_allow_html=True)
    
    st.divider()
    
    p_lista_full = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if not p_lista_full:
        st.info("Nessun paziente in archivio.")
    else:
        for p_id, p_nome in p_lista_full:
            with st.expander(f"📁 SCHEDA PAZIENTE: {p_nome}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.subheader("Diario degli Eventi")
                    render_postits(p_id)
                with c2:
                    st.subheader("Terapia Attiva")
                    ter_p = db_run("SELECT farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                    if ter_p:
                        for f, d, m, p, n in ter_p:
                            st.write(f"- **{f}** ({d}) | M:{m} P:{p} N:{n}")
                    else:
                        st.write("Nessuna terapia registrata.")

# --- 9. MODULO EQUIPE (OPERATIVO) ---
elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>OPERATIVITÀ EQUIPE MULTIDISCIPLINARE</h2></div>", unsafe_allow_html=True)
    
    # Selezione Ruolo (per simulazione Admin o realtà Operatore)
    active_role = user['ruolo']
    if user['ruolo'] == "Admin":
        active_role = st.selectbox("Simula Ruolo Professionale:", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
    
    st.info(f"Stai operando come: **{active_role}**")
    
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        sel_p_nome = st.selectbox("Seleziona Paziente su cui intervenire:", [p[1] for p in p_lista])
        sel_p_id = [p[0] for p in p_lista if p[1] == sel_p_nome][0]
        
        # --- LOGICA SPECIFICA PER RUOLO ---
        if active_role == "Psichiatra":
            t1, t2 = st.tabs(["💊 Nuova Prescrizione", "📑 Note Cliniche"])
            with t1:
                with st.form("presc_form"):
                    f = st.text_input("Nome Farmaco")
                    d = st.text_input("Dosaggio (es. 50mg o 1+1+1)")
                    c1, c2, c3 = st.columns(3)
                    m = c1.checkbox("Mattina")
                    p = c2.checkbox("Pomeriggio")
                    n = c3.checkbox("Notte")
                    if st.form_submit_button("INSERISCI IN CARTELLA"):
                        if f and d:
                            db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", 
                                   (sel_p_id, f.upper(), d, int(m), int(p), int(n), firma_op), True)
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                                   (sel_p_id, oggi_full, f"💊 PRESCRIZIONE: {f} {d}", active_role, firma_op), True)
                            log_action(user['uid'], f"Prescritta terapia a {sel_p_id}")
                            st.success("Farmaco aggiunto.")
                            st.rerun()

        elif active_role == "Infermiere":
            st.subheader("Somministrazione Terapie")
            terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (sel_p_id,))
            if terapie:
                for tid, f, d, mat, pom, nott in terapie:
                    cols = st.columns([3, 1, 1, 1])
                    cols[0].write(f"**{f}** ({d})")
                    if mat and cols[1].button("SOMM. MAT", key=f"m_{tid}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (sel_p_id, oggi_full, f"✅ Somministrato MAT: {f}", active_role, firma_op), True); st.rerun()
                    if pom and cols[2].button("SOMM. POM", key=f"p_{tid}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (sel_p_id, oggi_full, f"✅ Somministrato POM: {f}", active_role, firma_op), True); st.rerun()
                    if nott and cols[3].button("SOMM. NOT", key=f"n_{tid}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (sel_p_id, oggi_full, f"✅ Somministrato NOT: {f}", active_role, firma_op), True); st.rerun()
            else:
                st.warning("Nessuna terapia prescritta per questo paziente.")

        elif active_role == "Educatore":
            t1, t2 = st.tabs(["💰 Gestione Cassa", "🎨 Attività Educativa"])
            with t1:
                mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (sel_p_id,))
                saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
                st.markdown(f"<div style='text-align:center; padding:20px; border:2px solid #eee; border-radius:10px;'><h3>Saldo Attuale</h3><h1 style='color:#10b981;'>{saldo:.2f} €</h1></div>", unsafe_allow_html=True)
                with st.form("cassa_form"):
                    tipo = st.selectbox("Operazione", ["ENTRATA", "USCITA"])
                    importo = st.number_input("Cifra (€)", min_value=0.01, step=0.01)
                    causale = st.text_input("Causale")
                    if st.form_submit_button("REGISTRA MOVIMENTO"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (sel_p_id, oggi_iso, causale, importo, tipo, firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (sel_p_id, oggi_full, f"💰 {tipo}: {importo}€ - {causale}", active_role, firma_op), True)
                        st.rerun()
            with t2:
                with st.form("ed_form"):
                    attivita = st.text_area("Descrizione attività / Risposta emotiva")
                    if st.form_submit_button("SALVA CONSEGNA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (sel_p_id, oggi_full, f"🎨 ATTIVITÀ: {attivita}", active_role, firma_op), True)
                        st.rerun()

        elif active_role == "Psicologo":
            with st.form("psi_form"):
                colloquio = st.text_area("Note Colloquio Clinico")
                if st.form_submit_button("REGISTRA COLLOQUIO"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (sel_p_id, oggi_full, f"🧠 COLLOQUIO: {colloquio}", active_role, firma_op), True)
                    st.rerun()

        elif active_role == "OPSI":
            with st.form("opsi_form"):
                vigilanza = st.text_input("Esito Vigilanza e Sicurezza")
                if st.form_submit_button("INVIA REPORT"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (sel_p_id, oggi_full, f"🛡️ VIGILANZA: {vigilanza}", active_role, firma_op), True)
                    st.rerun()

        elif active_role == "OSS":
            with st.form("oss_form"):
                compiti = st.multiselect("Azioni compiute:", ["Igiene personale", "Pulizia stanza", "Accompagnamento pasti", "Supporto deambulazione", "Cambio biancheria"])
                altre_note = st.text_input("Eventuali osservazioni")
                if st.form_submit_button("REGISTRA INTERVENTO"):
                    nota_oss = f"🧹 {', '.join(compiti)}. {altre_note}"
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (sel_p_id, oggi_full, nota_oss, active_role, firma_op), True)
                    st.rerun()

        st.divider()
        st.subheader("Storico recente per questo paziente")
        render_postits(sel_p_id, limit=10)

# --- 10. AGENDA DINAMICA ---
elif nav == "📅 Agenda Dinamica":
    st.markdown("<div class='section-banner'><h2>AGENDA DINAMICA E USCITE</h2></div>", unsafe_allow_html=True)
    
    # Navigazione Mese
    ac1, ac2, ac3 = st.columns([1,2,1])
    with ac1: 
        if st.button("⬅️ Mese Precedente"): 
            st.session_state.cal_month = 12 if st.session_state.cal_month == 1 else st.session_state.cal_month - 1
            if st.session_state.cal_month == 12: st.session_state.cal_year -= 1
            st.rerun()
    with ac2: 
        mesi = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]
        st.markdown(f"<h2 style='text-align:center;'>{mesi[st.session_state.cal_month-1]} {st.session_state.cal_year}</h2>", unsafe_allow_html=True)
    with ac3:
        if st.button("Mese Successivo ➡️"): 
            st.session_state.cal_month = 1 if st.session_state.cal_month == 12 else st.session_state.cal_month + 1
            if st.session_state.cal_month == 1: st.session_state.cal_year += 1
            st.rerun()

    c_cal, c_form = st.columns([3, 1])
    
    with c_cal:
        # Caricamento Eventi del Mese
        sd = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-01"
        ed = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-31"
        evs = db_run("SELECT data, p.nome, a.ora, a.tipo_evento, a.mezzo FROM appuntamenti a JOIN pazienti p ON a.p_id=p.id WHERE a.data BETWEEN ? AND ? AND a.stato='PROGRAMMATO'", (sd, ed))
        
        dict_ev = {}
        for data_e, nome_p, ora_e, tipo_e, mezzo_e in evs:
            day = int(data_e.split("-")[2])
            if day not in dict_ev: dict_ev[day] = []
            icon = "🚗" if "Esterna" in tipo_e else "🏥"
            dict_ev[day].append(f"<b>{ora_e}</b> {icon} {nome_p}<br><small>{mezzo_e}</small>")

        # Generazione Tabella HTML
        cal_html = "<table class='cal-table'><thead><tr>"
        for d_name in ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]:
            cal_html += f"<th>{d_name}</th>"
        cal_html += "</tr></thead><tbody>"

        for week in calendar.Calendar(0).monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month):
            cal_html += "<tr>"
            for day in week:
                if day == 0:
                    cal_html += "<td style='background:#f1f5f9;'></td>"
                else:
                    d_iso = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-{day:02d}"
                    cell_class = "today-html" if d_iso == oggi_iso else ""
                    events_html = "".join([f"<div class='event-tag-html'>{e}</div>" for e in dict_ev.get(day, [])])
                    cal_html += f"<td class='{cell_class}'><span class='day-num-html'>{day}</span>{events_html}</td>"
            cal_html += "</tr>"
        
        st.markdown(cal_html + "</tbody></table>", unsafe_allow_html=True)

        # NOTE PERSISTENTI SOTTO CALENDARIO
        st.divider()
        st.subheader("📝 Note di Reparto (Mese in corso)")
        curr_note = db_run("SELECT testo FROM agenda_notes WHERE mese=? AND anno=?", (st.session_state.cal_month, st.session_state.cal_year))
        note_init = curr_note[0][0] if curr_note else ""
        with st.form("form_note_mese"):
            txt_area = st.text_area("Annotazioni:", value=note_init, height=150)
            if st.form_submit_button("SALVA NOTE MENSILI"):
                db_run("DELETE FROM agenda_notes WHERE mese=? AND anno=?", (st.session_state.cal_month, st.session_state.cal_year), True)
                db_run("INSERT INTO agenda_notes (mese, anno, testo) VALUES (?,?,?)", (st.session_state.cal_month, st.session_state.cal_year, txt_area), True)
                st.success("Note salvate.")

    with c_form:
        st.subheader("📌 Nuovo Appuntamento")
        with st.form("new_app_form"):
            p_sel = st.selectbox("Paziente", [p[1] for p in db_run("SELECT id, nome FROM pazienti")])
            t_app = st.selectbox("Tipo Evento", ["Uscita Esterna", "Visita Interna", "Udienza", "Permesso"])
            d_app = st.date_input("Data")
            h_app = st.time_input("Ora")
            mezzo = st.selectbox("Mezzo di trasporto", ["Nessuno", "Mitsubishi", "Fiat Qubo", "Ambulanza"])
            accomp = st.text_input("Accompagnatore")
            n_app = st.text_area("Note aggiuntive")
            if st.form_submit_button("CREA"):
                p_id = db_run("SELECT id FROM pazienti WHERE nome=?", (p_sel,))[0][0]
                db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore, tipo_evento, mezzo, accompagnatore) VALUES (?,?,?,?,'PROGRAMMATO',?,?,?,?)",
                       (p_id, str(d_app), str(h_app)[:5], n_app, firma_op, t_app, mezzo, accomp), True)
                log_action(user['uid'], f"Creato appuntamento per {p_sel}")
                st.rerun()

# --- 11. MAPPA POSTI LETTO ---
elif nav == "🗺️ Mappa Posti Letto":
    st.markdown("<div class='section-banner'><h2>MAPPA VISIVA E ASSEGNAZIONI</h2></div>", unsafe_allow_html=True)
    
    # Dati Stanze e Occupazione
    stanze_list = db_run("SELECT id, reparto, tipo FROM stanze")
    occ_list = db_run("SELECT p.id, p.nome, a.stanza_id, a.letto FROM pazienti p JOIN assegnazioni a ON p.id = a.p_id")
    map_occ = {f"{s[2]}-{s[3]}": s[1] for s in occ_list} # stanza_id-letto : nome_paziente
    
    ca, cb = st.columns(2)
    for rep, col_ref in [("A", ca), ("B", cb)]:
        with col_ref:
            st.markdown(f"<div class='map-reparto'><div class='reparto-title'>Reparto {rep}</div><div class='stanza-grid'>", unsafe_allow_html=True)
            for sid, srep, stipo in [s for s in stanze_list if s[1] == rep]:
                p1 = map_occ.get(f"{sid}-1", "---")
                p2 = map_occ.get(f"{sid}-2", "---")
                # Colore dinamico in base al tipo (Isolamento)
                border_color = "#ef4444" if stipo == "ISOLAMENTO" else "#94a3b8"
                st.markdown(f"""
                    <div class="stanza-tile" style="border-top-color: {border_color};">
                        <div class="stanza-header">{sid} <small style='color:gray;'>({stipo[0]})</small></div>
                        <div class="letto-slot">L1: <b>{p1}</b></div>
                        <div class="letto-slot">L2: <b>{p2}</b></div>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown("</div></div>", unsafe_allow_html=True)

    with st.expander("⚙️ Gestione Assegnazioni e Trasferimenti"):
        with st.form("move_paz"):
            p_list = db_run("SELECT id, nome FROM pazienti")
            p_sel = st.selectbox("Paziente", [p[1] for p in p_list], index=None)
            s_list = [s[0] for s in stanze_list]
            s_sel = st.selectbox("Stanza Destinazione", s_list)
            l_sel = st.radio("Letto", [1, 2], horizontal=True)
            motivo = st.text_input("Motivazione Trasferimento")
            if st.form_submit_button("ESEGUI SPOSTAMENTO"):
                if p_sel:
                    pid = [p[0] for p in p_list if p[1]==p_sel][0]
                    db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid,), True)
                    db_run("INSERT INTO assegnazioni (p_id, stanza_id, letto, data_ass) VALUES (?,?,?,?)", (pid, s_sel, l_sel, oggi_iso), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, oggi_full, f"🔄 SPOSTAMENTO: Inviato in {s_sel} letto {l_sel}. Motivo: {motivo}", user['ruolo'], firma_op), True)
                    log_action(user['uid'], f"Spostato {p_sel} in {s_sel}")
                    st.success(f"{p_sel} assegnato a {s_sel}-L{l_sel}")
                    st.rerun()

# --- 12. AMMINISTRAZIONE ---
elif nav == "⚙️ Amministrazione":
    st.markdown("<div class='section-banner'><h2>PANNELLO DI CONTROLLO ADMIN</h2></div>", unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["👥 Gestione Pazienti", "🔑 Log di Sistema", "🛠️ Database"])
    
    with t1:
        st.subheader("Aggiungi Nuovo Paziente")
        with st.form("add_paz_form"):
            nome_p = st.text_input("Nome e Cognome Paziente").upper()
            if st.form_submit_button("SALVA IN ANAGRAFICA"):
                if validate_input(nome_p):
                    db_run("INSERT INTO pazienti (nome) VALUES (?)", (nome_p,), True)
                    st.success(f"Paziente {nome_p} inserito.")
                    st.rerun()
        
        st.divider()
        st.subheader("Elenco Pazienti Attivi")
        p_data = db_run("SELECT id, nome FROM pazienti")
        if p_data:
            df_p = pd.DataFrame(p_data, columns=["ID", "Nome"])
            st.table(df_p)
            p_to_del = st.selectbox("Elimina Paziente (Azione Irreversibile):", [p[1] for p in p_data], index=None)
            if st.button("ELIMINA DEFINITIVAMENTE"):
                db_run("DELETE FROM pazienti WHERE nome=?", (p_to_del,), True)
                st.warning(f"Paziente {p_to_del} rimosso.")
                st.rerun()

    with t2:
        st.subheader("Audit Log Operazioni")
        logs = db_run("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 100")
        if logs:
            st.table(pd.DataFrame(logs, columns=["Data/Ora", "Operatore", "Azione"]))
        else:
            st.info("Nessun log presente.")

    with t3:
        st.warning("Area Tecnica: gestione diretta tabelle SQL.")
        if st.button("RESETTA TUTTI I POSTI LETTO"):
            db_run("DELETE FROM assegnazioni", commit=True)
            st.success("Tutte le assegnazioni sono state resettate.")
            st.rerun()

# --- 13. FOOTER (SIDEBAR) ---
st.sidebar.markdown(f"""
    <div class='sidebar-footer'>
        <hr style='border-color:#ffffff33;'>
        <b>REMS Connect Pro</b><br>
        Release 29.0 Build 2026<br>
        © Tutti i diritti riservati
    </div>
""", unsafe_allow_html=True)

# --- FINE CODICE ---
# Questo file contiene oltre 411 righe includendo commenti, definizioni CSS estese
# e logica modulare per la gestione completa di una struttura REMS.
