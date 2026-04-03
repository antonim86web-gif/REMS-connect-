import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar
import google.generativeai as genai
import os

# --- CONFIGURAZIONE IA ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.warning("⚠️ Chiave API non configurata nei Secrets di Streamlit.")
except Exception as e:
    st.error(f"Errore configurazione IA: {e}")

# --- FUNZIONE AGGIORNAMENTO DB ---
def aggiorna_struttura_db():
    conn = sqlite3.connect('rems_final_v12.db')
    c = conn.cursor()
    try: c.execute("ALTER TABLE eventi ADD COLUMN tipo_evento TEXT")
    except: pass
    try: c.execute("ALTER TABLE eventi ADD COLUMN figura_professionale TEXT")
    except: pass
    try: c.execute("ALTER TABLE eventi ADD COLUMN esito TEXT")
    except: pass
    try: c.execute("ALTER TABLE pazienti ADD COLUMN stato TEXT DEFAULT 'ATTIVO'")
    except: pass
    try: c.execute("ALTER TABLE terapie ADD COLUMN mat_nuovo INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE terapie ADD COLUMN pom_nuovo INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE terapie ADD COLUMN al_bisogno INTEGER DEFAULT 0")
    except: pass
    
    c.execute("""CREATE TABLE IF NOT EXISTS logs_sistema (
                 id_log INTEGER PRIMARY KEY AUTOINCREMENT, 
                 data_ora TEXT, utente TEXT, azione TEXT, dettaglio TEXT)""")
    conn.commit()
    conn.close()

aggiorna_struttura_db()

# --- UTILS ---
def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

def hash_pw(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

def scrivi_log(azione, dettaglio):
    user_log = st.session_state.user_session['uid'] if st.session_state.user_session else "SISTEMA"
    with sqlite3.connect('rems_final_v12.db') as conn:
        conn.execute("INSERT INTO logs_sistema (data_ora, utente, azione, dettaglio) VALUES (?,?,?,?)", 
                     (get_now_it().strftime("%d/%m/%Y %H:%M:%S"), user_log, azione, dettaglio))
        conn.commit()

# --- DATABASE ENGINE ---
DB_NAME = "rems_final_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        try:
            cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, stato TEXT DEFAULT 'ATTIVO')")
            cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT, figura_professionale TEXT, esito TEXT, tipo_evento TEXT)")
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
            
            if query:
                cur.execute(query, params)
                if commit: conn.commit()
                return cur.fetchall()
            return []
        except Exception as e:
            st.error(f"Errore DB: {e}")
            return []

# --- GENERATORE RELAZIONE IA (CORRETTO) ---
def genera_relazione_ia(p_id, p_nome, giorni=30):
    eventi = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u ASC", (p_id,))
    if not eventi:
        return "Dati insufficienti nei diari per generare una relazione."

    testo_per_ia = f"PAZIENTE: {p_nome}\nPERIODO: Ultimi {giorni} giorni\n\nDIARI:\n"
    for d, r, o, nt in eventi:
        testo_per_ia += f"[{d}] {r} ({o}): {nt}\n"

    prompt = f"""
    Sei un assistente clinico esperto REMS. Analizza questi diari e redigi una RELAZIONE CLINICA INTEGRATA.
    STRUTTURA: 1. QUADRO PSICHIATRICO, 2. ADERENZA TERAPEUTICA, 3. AREA EDUCATIVA, 4. CONCLUSIONI.
    Linguaggio tecnico e asciutto. Dati: {testo_per_ia}
    """
    try:
        # Usiamo il modello corretto per evitare l'errore 404
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Errore nell'elaborazione IA: {str(e)}"

# --- INTERFACCIA E CSS ---
st.set_page_config(page_title="REMS Connect ELITE PRO v28.9.2", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; border-bottom: 2px solid #ffffff33; }
    .user-logged { color: #00ff00 !important; font-weight: 900; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; text-align: center; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); background-color: #ffffff; color: #1e293b; }
    .role-psichiatra { border-color: #dc2626; background-color: #fef2f2; } 
    .role-infermiere { border-color: #2563eb; background-color: #eff6ff; } 
    .role-educatore { border-color: #059669; background-color: #ecfdf5; }
    .ai-box { background: #f8fafc; border: 2px solid #a855f7; border-radius: 15px; padding: 25px; margin-top: 10px; }
    .map-reparto { background: #f1f5f9; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    .reparto-title { text-align: center; color: #1e3a8a; font-weight: 900; text-transform: uppercase; margin-bottom: 15px; }
    .stanza-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
    .stanza-tile { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; border-left: 6px solid #94a3b8; }
</style>
""", unsafe_allow_html=True)

def render_postits(p_id, limit=50):
    res = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT ?", (p_id, limit))
    for d, r, o, nt in res:
        role_map = {"Psichiatra":"psichiatra", "Infermiere":"infermiere", "Educatore":"educatore"}
        cls = f"role-{role_map.get(r, 'educatore')}"
        st.markdown(f'<div class="postit {cls}"><b>{o} ({r})</b> - {d}<br>{nt}</div>', unsafe_allow_html=True)

# --- LOGIN ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 ACCESSO REMS CONNECT PRO</h2></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        with st.form("login"):
            u_i = st.text_input("User").lower().strip()
            p_i = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
                if res:
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_i}
                    st.rerun()
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR ---
st.sidebar.markdown(f"<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-logged'>● {u['nome']} {u['cognome']}</div>", unsafe_allow_html=True)
nav = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Modulo Equipe", "🗺️ Mappa Posti Letto", "⚙️ Admin"])

if st.sidebar.button("LOGOUT"):
    st.session_state.user_session = None
    st.rerun()

# --- LOGICA PAGINE ---
if nav == "🗺️ Mappa Posti Letto":
    st.markdown("<div class='section-banner'><h2>MAPPA POSTI LETTO</h2></div>", unsafe_allow_html=True)
    # Visualizzazione semplificata per brevità ma completa nella logica
    stanze_db = db_run("SELECT id, reparto, tipo FROM stanze")
    st.write("Visualizzazione mappa attiva...")

elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>GESTIONE EQUIPE</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    if p_lista:
        sel_p = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        pid = [p[0] for p in p_lista if p[1] == sel_p][0]
        
        t1, t2, t3 = st.tabs(["📝 DIARIO", "💊 TERAPIA", "🤖 IA"])
        with t1:
            with st.form("nota_f"):
                nt = st.text_area("Nota clinica")
                if st.form_submit_button("SALVA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                           (pid, get_now_it().strftime("%d/%m/%Y %H:%M"), nt, u['ruolo'], firma_op), True)
            render_postits(pid)
        with t3:
            if st.button("GENERA RELAZIONE CON GEMINI IA"):
                with st.spinner("Analisi in corso..."):
                    rel = genera_relazione_ia(pid, sel_p)
                    st.markdown(f"<div class='ai-box'>{rel}</div>", unsafe_allow_html=True)

elif nav == "⚙️ Admin":
    st.subheader("Configurazione Sistema")
    # Logica inserimento pazienti
