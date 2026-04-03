import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar
import google.generativeai as genai
import json

# --- CONFIGURAZIONE CORE E AI ---
# Inserire la chiave API per le funzionalità di analisi clinica
API_KEY_AI = "YOUR_GEMINI_API_KEY" 
genai.configure(api_key=API_KEY_AI)
model_ai = genai.GenerativeModel('gemini-pro')

# --- DATABASE ENGINE & MIGRATION ---
DB_NAME = "rems_final_v12.db"

def inizializza_e_aggiorna_db():
    """Inizializza il database e gestisce le migrazioni delle colonne senza perdita di dati."""
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        # Tabelle Core
        cur.execute("""CREATE TABLE IF NOT EXISTS utenti (
                        user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, 
                        cognome TEXT, qualifica TEXT)""")
        
        cur.execute("""CREATE TABLE IF NOT EXISTS pazienti (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        nome TEXT UNIQUE, stato TEXT DEFAULT 'ATTIVO',
                        anamnesi_ai TEXT)""")
        
        cur.execute("""CREATE TABLE IF NOT EXISTS eventi (
                        id_u INTEGER PRIMARY KEY AUTOINCREMENT,
                        id INTEGER, data TEXT, nota TEXT, ruolo TEXT, 
                        op TEXT, figura_professionale TEXT, esito TEXT,
                        FOREIGN KEY(id) REFERENCES pazienti(id))""")
        
        cur.execute("""CREATE TABLE IF NOT EXISTS terapie (
                        id_u INTEGER PRIMARY KEY AUTOINCREMENT,
                        p_id INTEGER, farmaco TEXT, dose TEXT, 
                        mat_nuovo INTEGER DEFAULT 0, pom_nuovo INTEGER DEFAULT 0, 
                        al_bisogno INTEGER DEFAULT 0, medico TEXT,
                        FOREIGN KEY(p_id) REFERENCES pazienti(id))""")
        
        cur.execute("""CREATE TABLE IF NOT EXISTS cassa (
                        id_u INTEGER PRIMARY KEY AUTOINCREMENT,
                        p_id INTEGER, data TEXT, causale TEXT, 
                        importo REAL, tipo TEXT, op TEXT,
                        FOREIGN KEY(p_id) REFERENCES pazienti(id))""")
        
        cur.execute("""CREATE TABLE IF NOT EXISTS appuntamenti (
                        id_u INTEGER PRIMARY KEY AUTOINCREMENT, 
                        p_id INTEGER, data TEXT, ora TEXT, nota TEXT, 
                        stato TEXT, autore TEXT, tipo_evento TEXT, 
                        mezzo TEXT, accompagnatore TEXT,
                        FOREIGN KEY(p_id) REFERENCES pazienti(id))""")
        
        cur.execute("""CREATE TABLE IF NOT EXISTS stanze (
                        id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)""")
        
        cur.execute("""CREATE TABLE IF NOT EXISTS assegnazioni (
                        p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, 
                        data_ass TEXT, FOREIGN KEY(p_id) REFERENCES pazienti(id))""")

        cur.execute("""CREATE TABLE IF NOT EXISTS logs_sistema (
                        id_log INTEGER PRIMARY KEY AUTOINCREMENT, 
                        data_ora TEXT, utente TEXT, azione TEXT, dettaglio TEXT)""")

        # Controllo Utente Admin Default
        if cur.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
            pw_admin = hashlib.sha256(str.encode("perito2026")).hexdigest()
            cur.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", pw_admin, "SUPER", "USER", "Admin"))
        
        # Inizializzazione Stanze
        if cur.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
            for i in range(1, 7): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"A{i}", "A", "ISOLAMENTO" if i==6 else "STANDARD"))
            for i in range(1, 11): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"B{i}", "B", "ISOLAMENTO" if i==10 else "STANDARD"))
        
        conn.commit()

def db_query(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- UTILITY FUNCTIONS ---
def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

def scrivi_log(azione, dettaglio):
    uid = st.session_state.user_session['uid'] if 'user_session' in st.session_state and st.session_state.user_session else "SISTEMA"
    db_query("INSERT INTO logs_sistema (data_ora, utente, azione, dettaglio) VALUES (?,?,?,?)", 
             (get_now_it().strftime("%d/%m/%Y %H:%M:%S"), uid, azione, dettaglio), True)

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- MOTORE INTELLIGENZA ARTIFICIALE (REMS AI) ---
def analizza_diario_con_ai(p_id, nome_paziente):
    """Analizza gli ultimi eventi del diario clinico per generare un report di rischio."""
    eventi = db_query("SELECT ruolo, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 20", (p_id,))
    if not eventi: return "Dati insufficienti per l'analisi."
    
    testo_diario = "\n".join([f"[{r}]: {n}" for r, n in eventi])
    prompt = f"""Analizza il seguente diario clinico del paziente {nome_paziente}. 
    Identifica: 1) Livello di rischio (Basso/Medio/Alto), 2) Anomalie comportamentali, 3) Suggerimenti per l'equipe.
    Diario:
    {testo_diario}
    Rispondi in modo professionale e sintetico."""
    
    try:
        response = model_ai.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Errore AI: {str(e)}"

# --- INTERFACCIA E STILI ---
st.set_page_config(page_title="REMS Connect ELITE PRO", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; border-right: 3px solid #10b981; }
    .sidebar-title { color: #ffffff !important; font-size: 1.6rem; font-weight: 800; text-align: center; padding: 20px 0; border-bottom: 1px solid #ffffff33; }
    .section-banner { background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 25px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
    .postit { padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 8px solid; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .role-psichiatra { border-color: #ef4444; } .role-infermiere { border-color: #3b82f6; } .role-educatore { border-color: #10b981; }
    .ai-box { background: #f0fdf4; border: 1px solid #86efac; padding: 20px; border-radius: 12px; margin-top: 10px; border-left: 10px solid #22c55e; }
</style>
""", unsafe_allow_html=True)

# --- LOGICA DI ACCESSO ---
inizializza_e_aggiorna_db()

if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h1>🏥 REMS CONNECT ELITE PRO <small>v28.9</small></h1><p>Sistema di Gestione Integrata per Residenze per l'Esecuzione delle Misure di Sicurezza</p></div>", unsafe_allow_html=True)
    tab_l, tab_r = st.tabs(["🔐 LOGIN", "📝 REGISTRAZIONE OPERATORE"])
    
    with tab_l:
        with st.form("login"):
            u_name = st.text_input("Username").lower().strip()
            u_pass = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI AL SISTEMA"):
                res = db_query("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_name, hash_pw(u_pass)))
                if res:
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_name}
                    scrivi_log("LOGIN", "Accesso autorizzato")
                    st.rerun()
                else: st.error("Credenziali non valide.")
    
    with tab_r:
        with st.form("register"):
            new_u = st.text_input("Nuovo Username").lower().strip()
            new_p = st.text_input("Password", type="password")
            new_n = st.text_input("Nome")
            new_c = st.text_input("Cognome")
            new_q = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
            if st.form_submit_button("CREA ACCOUNT"):
                if not db_query("SELECT user FROM utenti WHERE user=?", (new_u,)):
                    db_query("INSERT INTO utenti VALUES (?,?,?,?,?)", (new_u, hash_pw(new_p), new_n, new_c, new_q), True)
                    st.success("Account creato. Procedi al login.")
                else: st.error("Username esistente.")
    st.stop()

# --- SIDEBAR NAVIGAZIONE ---
u = st.session_state.user_session
st.sidebar.markdown(f"<div class='sidebar-title'>REMS CONNECT</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<p style='text-align:center; color:white;'>Benvenuto, <br><b>{u['nome']} {u['cognome']}</b><br><small>{u['ruolo']}</small></p>", unsafe_allow_html=True)

nav = st.sidebar.radio("MENU PRINCIPALE", ["📊 Dashboard Clinica", "🧠 Analisi AI", "💊 Gestione Terapie", "📅 Agenda & Uscite", "🗺️ Mappa Reparto", "⚙️ Pannello Admin"])

if st.sidebar.button("LOGOUT"):
    st.session_state.user_session = None
    st.rerun()

# --- 1. DASHBOARD CLINICA ---
if nav == "📊 Dashboard Clinica":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO INTEGRATO</h2></div>", unsafe_allow_html=True)
    pazienti = db_query("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    
    for pid, pnome in pazienti:
        with st.expander(f"👤 {pnome}"):
            # Inserimento rapido nota
            with st.form(f"nota_{pid}"):
                c1, c2 = st.columns([0.8, 0.2])
                txt = c1.text_area("Nuova annotazione diario", key=f"txt_{pid}", height=100)
                esito = c2.selectbox("Stato", ["Normale", "Agitato", "Collaborativo", "Rifiuto"], key=f"es_{pid}")
                if st.form_submit_button("PUBBLICA NOTA"):
                    db_query("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
                             (pid, get_now_it().strftime("%d/%m/%Y %H:%M"), txt, u['ruolo'], f"{u['nome']} {u['cognome']}", esito), True)
                    st.rerun()
            
            # Visualizzazione Timeline
            st.markdown("---")
            eventi_db = db_query("SELECT data, ruolo, op, nota, esito FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 30", (pid,))
            for d, r, o, nt, es in eventi_db:
                role_cls = f"role-{r.lower().replace(' ', '')}"
                st.markdown(f"""<div class='postit {role_cls}'>
                                <small><b>{d}</b> | {o} ({r})</small><br>
                                <b style='color:#1e3a8a;'>{es}</b>: {nt}
                             </div>""", unsafe_allow_html=True)

# --- 2. ANALISI AI (MODULO CORE) ---
elif nav == "🧠 Analisi AI":
    st.markdown("<div class='section-banner'><h2>REMS INTELLIGENCE ENGINE</h2><p>Analisi predittiva del rischio e reportistica automatizzata</p></div>", unsafe_allow_html=True)
    p_sel = st.selectbox("Seleziona Paziente per Analisi AI", [p[1] for p in db_query("SELECT nome FROM pazienti WHERE stato='ATTIVO'")], index=None)
    
    if p_sel:
        pid = db_query("SELECT id FROM pazienti WHERE nome=?", (p_sel,))[0][0]
        if st.button("GENERA REPORT AI AVANZATO"):
            with st.spinner("L'intelligenza artificiale sta analizzando la cartella clinica..."):
                report = analizza_diario_con_ai(pid, p_sel)
                st.markdown(f"<div class='ai-box'><h3>Analisi AI per {p_sel}</h3><hr>{report}</div>", unsafe_allow_html=True)
                st.download_button("Scarica Report (TXT)", report, file_name=f"Report_AI_{p_sel}_{get_now_it().strftime('%Y%m%d')}.txt")

# --- 3. GESTIONE TERAPIE ---
elif nav == "💊 Gestione Terapie":
    st.markdown("<div class='section-banner'><h2>MODULO FARMACOLOGICO</h2></div>", unsafe_allow_html=True)
    p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in db_query("SELECT nome FROM pazienti WHERE stato='ATTIVO'")], index=None)
    
    if p_sel:
        pid = db_query("SELECT id FROM pazienti WHERE nome=?", (p_sel,))[0][0]
        
        if u['ruolo'] in ["Psichiatra", "Admin"]:
            with st.expander("➕ Nuova Prescrizione Medica"):
                with st.form("prescr"):
                    f = st.text_input("Farmaco")
                    d = st.text_input("Dosaggio")
                    c1, c2, c3 = st.columns(3)
                    m = c1.checkbox("Mattina (08:00)")
                    p = c2.checkbox("Pomeriggio (16:00)")
                    b = c3.checkbox("Al Bisogno (PRN)")
                    if st.form_submit_button("SALVA PRESCRIZIONE"):
                        db_query("INSERT INTO terapie (p_id, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno, medico) VALUES (?,?,?,?,?,?,?)",
                                 (pid, f, d, int(m), int(p), int(b), f"{u['nome']} {u['cognome']}"), True)
                        st.success("Terapia salvata correttamente.")
        
        # Tabella Somministrazione
        st.subheader("Piano Terapeutico Attivo")
        terapie = db_query("SELECT id_u, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno FROM terapie WHERE p_id=?", (pid,))
        for tid, fn, ds, m, p, b in terapie:
            with st.container():
                st.markdown(f"**{fn}** ({ds}) - " + ( "🌅" if m else "") + ( "🌇" if p else "") + ( "🆘" if b else ""))
                if u['ruolo'] in ["Infermiere", "Admin"]:
                    if st.button(f"Smarca Somministrazione: {fn}", key=f"sm_{tid}"):
                        db_query("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)",
                                 (pid, get_now_it().strftime("%d/%m/%Y %H:%M"), f"Somministrato: {fn} {ds}", "Infermiere", f"{u['nome']} {u['cognome']}", "ESEGUITO"), True)
                        st.toast(f"Somministrazione di {fn} registrata!")
                st.divider()

# --- 4. AGENDA & USCITE ---
elif nav == "📅 Agenda & Uscite":
    st.markdown("<div class='section-banner'><h2>AGENDA DINAMICA EQUIPE</h2></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("Nuovo Appuntamento")
        with st.form("agenda"):
            p_ids = st.multiselect("Pazienti coinvolti", db_query("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'"), format_func=lambda x: x[1])
            tipo = st.selectbox("Tipo Evento", ["Uscita Esterna", "Visita Specialistica", "Colloquio Giudice", "Permesso Premio"])
            data_e = st.date_input("Data")
            ora_e = st.time_input("Ora")
            m_trasporto = st.selectbox("Mezzo", ["Mitsubishi", "Fiat Qubo", "Privato", "Nessuno"])
            if st.form_submit_button("REGISTRA IN AGENDA"):
                for p_id_val, p_nome_val in p_ids:
                    db_query("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore, tipo_evento, mezzo) VALUES (?,?,?,?,'PROGRAMMATO',?,?,?)",
                             (p_id_val, str(data_e), str(ora_e)[:5], "Registrato via Agenda", f"{u['nome']} {u['cognome']}", tipo, m_trasporto), True)
                st.success("Evento registrato.")
    
    with c2:
        st.subheader("Scadenze Imminenti")
        scadenze = db_query("""SELECT a.data, a.ora, p.nome, a.tipo_evento FROM appuntamenti a 
                               JOIN pazienti p ON a.p_id=p.id 
                               WHERE a.data >= ? AND a.stato='PROGRAMMATO' ORDER BY a.data ASC""", (str(get_now_it().date()),))
        if scadenze:
            df_agenda = pd.DataFrame(scadenze, columns=["Data", "Ora", "Paziente", "Tipo Evento"])
            st.table(df_agenda)
        else:
            st.info("Nessun impegno in agenda per i prossimi giorni.")

# --- 5. MAPPA REPARTO ---
elif nav == "🗺️ Mappa Reparto":
    st.markdown("<div class='section-banner'><h2>TABELLONE VISIVO POSTI LETTO</h2></div>", unsafe_allow_html=True)
    stanze = db_query("SELECT id, reparto, tipo FROM stanze")
    occupazione = db_query("SELECT a.stanza_id, a.letto, p.nome FROM assegnazioni a JOIN pazienti p ON a.p_id=p.id")
    map_occ = {(s_id, l): p_n for s_id, l, p_n in occupazione}
    
    col_a, col_b = st.columns(2)
    with col_a: st.subheader("Reparto A")
    with col_b: st.subheader("Reparto B")
    
    for s_id, s_rep, s_tipo in stanze:
        target_col = col_a if s_rep == "A" else col_b
        with target_col:
            st.markdown(f"**Stanza {s_id}** ({s_tipo})")
            for l in [1, 2]:
                occ = map_occ.get((s_id, l), "LIBERO")
                color = "red" if occ != "LIBERO" else "green"
                st.markdown(f"Letto {l}: <span style='color:{color}; font-weight:bold;'>{occ}</span>", unsafe_allow_html=True)
            st.divider()

# --- 6. ADMIN ---
elif nav == "⚙️ Pannello Admin":
    if u['ruolo'] != "Admin":
        st.error("Accesso negato. Area riservata agli amministratori.")
    else:
        st.markdown("<div class='section-banner'><h2>AMMINISTRAZIONE SISTEMA</h2></div>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["👥 Gestione Utenti", "📁 Gestione Pazienti", "📜 Log di Sistema"])
        
        with t1:
            utenti_lista = db_query("SELECT user, nome, cognome, qualifica FROM utenti")
            st.dataframe(pd.DataFrame(utenti_lista, columns=["User", "Nome", "Cognome", "Ruolo"]), use_container_width=True)
            
        with t2:
            with st.form("new_paz"):
                nome_p = st.text_input("Nome e Cognome Paziente").upper()
                if st.form_submit_button("INSERISCI NUOVO PAZIENTE"):
                    db_query("INSERT INTO pazienti (nome) VALUES (?)", (nome_p,), True)
                    st.success("Paziente inserito.")
            st.divider()
            for pid, pn, st_p in db_query("SELECT id, nome, stato FROM pazienti"):
                st.write(f"ID: {pid} | {pn} | Stato: {st_p}")

        with t3:
            logs = db_query("SELECT data_ora, utente, azione, dettaglio FROM logs_sistema ORDER BY id_log DESC LIMIT 100")
            st.table(pd.DataFrame(logs, columns=["Data", "Utente", "Azione", "Dettaglio"]))

# --- FOOTER ---
st.sidebar.markdown(f"""
<div style='position: fixed; bottom: 10px; width: 250px; text-align: center; font-size: 0.7rem; color: #ffffff99;'>
    REMS CONNECT ELITE PRO<br>
    Sviluppato da Antony Webmaster<br>
    v28.9.2 - 2026
</div>
""", unsafe_allow_html=True)
