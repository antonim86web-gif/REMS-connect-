

import sqlite3

import streamlit as st

from datetime import datetime, timedelta, timezone

import hashlib

import pandas as pd

import calendar

import google.generativeai as genai



# --- CONFIGURAZIONE IA SICURA ---

import os

try:

    if "GOOGLE_API_KEY" in st.secrets:

        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

    else:

        st.warning("⚠️ Chiave API non configurata nei Secrets di Streamlit.")

except Exception as e:

    st.error(f"Errore configurazione IA: {e}")


except:

    st.error("Chiave API non configurata nei Secrets di Streamlit!")



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

def genera_relazione_ia(p_id, p_nome, giorni=30):

    eventi = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u ASC", (p_id,))

    

    if not eventi:

        return "Dati insufficienti nei diari per generare una relazione."


    testo_per_ia = f"PAZIENTE: {p_nome}\nPERIODO ANALISI: Ultimi {giorni} giorni\n\nDIARI CLINICI REGISTRATI:\n"

    for d, r, o, nt in eventi:

        testo_per_ia += f"[{d}] {r} ({o}): {nt}\n"


    prompt = f"Analizza clinicamente questi diari per il paziente {p_nome}: {testo_per_ia}"

    

    try:

        # USA QUESTO NOME MODELLO (senza -latest e senza models/)

        model = genai.GenerativeModel('gemini-1.5-flash')

        response = model.generate_content(prompt)

        return response.text

    except Exception as e:

        return f"Errore nell'elaborazione IA: {str(e)}"



    prompt = f"""

    Sei un assistente clinico esperto per una REMS (Residenza per l'Esecuzione delle Misure di Sicurezza).

    Analizza i diari clinici seguenti e redigi una RELAZIONE CLINICA INTEGRATA formale.

    

    STRUTTURA RICHIESTA:

    1. QUADRO PSICHIATRICO: Sintetizza le note del Medico/Psichiatra.

    2. ADERENZA TERAPEUTICA E PARAMETRI: Valuta la compliance ai farmaci e i dati vitali (note Infermiere).

    3. AREA EDUCATIVA E OSSERVATIVA: Sintetizza le note di OSS, Educatori e Psicologi.

    4. CONCLUSIONI CLINICHE: Indica stabilità o eventuali criticità rilevate.


    Usa un linguaggio tecnico, professionale e asciutto. Non inventare fatti non presenti nei dati.

    

    DATI DA ANALIZZARE:

    {testo_per_ia}

    """

    try:

        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        response = model.generate_content(prompt)

        return response.text

    except Exception as e:

        return f"Errore nell'elaborazione IA: {str(e)}"


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

    paz_db = db_run("SELECT p.id, p.nome, a.stanza_id, a.letto FROM pazienti p LEFT JOIN assegnazioni a ON p.id = a.p_id WHERE p.stato='ATTIVO'")

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

                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid_sel, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🔄 TRASFERIMENTO: Spostato in {dsid} Letto {dl}. Motivo: {mot}", u['ruolo'], firma_op), True) Da questo codice fai solo le correzioni richieste e poi vanno avanti completo senza omissioni e senza semplificazioni. 
