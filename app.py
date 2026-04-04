import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import calendar
from datetime import datetime, timedelta, timezone
from groq import Groq

# --- 1. CONFIGURAZIONE CORE & IA ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
DB_NAME = "rems_final_v12.db"

def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

def hash_pw(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- 2. ENGINE DATABASE (SCHEMA INTEGRALE) ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Tabelle Base
        c.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, stato TEXT DEFAULT 'ATTIVO', data_nascita TEXT, cf TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY AUTOINCREMENT, id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, esito TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, farmaco TEXT, dose TEXT, mat_nuovo INTEGER DEFAULT 0, pom_nuovo INTEGER DEFAULT 0, al_bisogno INTEGER DEFAULT 0, medico TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS cassa (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT, tipo_evento TEXT, mezzo TEXT, accompagnatore TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS logs_sistema (id_log INTEGER PRIMARY KEY AUTOINCREMENT, data_ora TEXT, utente TEXT, azione TEXT, dettaglio TEXT)")
        
        # Admin di sistema di default
        if c.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
            c.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("perito2026"), "SUPER", "USER", "Admin"))
        
        # Setup Stanze
        if c.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
            for r in ["A", "B"]:
                for i in range(1, 11): 
                    tipo = "ISOLAMENTO" if i > 8 else "STANDARD"
                    c.execute("INSERT INTO stanze VALUES (?,?,?)", (f"{r}{i}", r, tipo))
        conn.commit()

init_db()

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def scrivi_log(azione, dettaglio):
    user_log = st.session_state.user_session['uid'] if st.session_state.get('user_session') else "SISTEMA"
    db_run("INSERT INTO logs_sistema (data_ora, utente, azione, dettaglio) VALUES (?,?,?,?)", 
           (get_now_it().strftime("%d/%m/%Y %H:%M:%S"), user_log, azione, dettaglio), True)

# --- 3. CSS ELITE NEON (RE-DESIGN) ---
st.set_page_config(page_title="REMS Connect ELITE PRO", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* Global Neon Theme */
    .stApp { background-color: #020617; color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #000000; border-right: 2px solid #0ea5e9; }
    
    /* Post-it & Cards */
    .postit { background: white; color: #1e293b; padding: 15px; border-radius: 10px; margin-bottom: 12px; border-left: 10px solid #64748b; box-shadow: 0 0 15px rgba(255,255,255,0.1); }
    .role-psichiatra { border-color: #ef4444; } .role-infermiere { border-color: #3b82f6; }
    .role-educatore { border-color: #10b981; } .role-psicologo { border-color: #a855f7; }
    .role-opsi { border-color: #f59e0b; } .role-sociale { border-color: #ec4899; }

    /* Mappa Stanze Neon */
    .stanza-tile { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 12px; transition: 0.3s; }
    .stanza-piena { border: 2px solid #3b82f6; box-shadow: 0 0 10px #3b82f6; }
    .stanza-occupata { border: 2px solid #10b981; box-shadow: 0 0 10px #10b981; }
    .stanza-isolamento { border: 2px dashed #ef4444; }

    /* Keep Terapia Grid */
    .scroll-giorni { display: flex; overflow-x: auto; gap: 5px; padding: 10px; }
    .quadratino { min-width: 40px; height: 55px; border-radius: 6px; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 10px; border: 1px solid #475569; background: #0f172a; }
    .q-assunto { background: #14532d; color: #4ade80; border-color: #22c55e; }
    .q-rifiuto { background: #7f1d1d; color: #f87171; border-color: #ef4444; }
    .q-oggi { border: 2px solid #0ea5e9; transform: scale(1.1); }

    /* Agenda Tooltip */
    .event-tag-html { background: #0ea5e9; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; margin-bottom: 2px; cursor: pointer; }
    
    /* Sidebar Custom */
    .sidebar-title { font-size: 24px; font-weight: 900; color: #0ea5e9; text-align: center; text-shadow: 0 0 10px #0ea5e9; }
</style>
""", unsafe_allow_html=True)

# --- 4. LOGICA DI NAVIGAZIONE E SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<h1 style='text-align:center; color:#0ea5e9;'>🏥 REMS CONNECT ELITE</h1>", unsafe_allow_html=True)
    tab_l, tab_r = st.tabs(["🔐 Login", "📝 Registrazione"])
    with tab_l:
        u_in = st.text_input("Username").lower()
        p_in = st.text_input("Password", type="password")
        if st.button("ACCEDI"):
            res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
            if res:
                st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_in}
                scrivi_log("LOGIN", "Utente loggato")
                st.rerun()
            else: st.error("Credenziali Errate")
    with tab_r:
        with st.form("reg"):
            ru, rp = st.text_input("Username"), st.text_input("Password", type="password")
            rn, rc = st.text_input("Nome"), st.text_input("Cognome")
            rq = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (ru.lower(), hash_pw(rp), rn.capitalize(), rc.capitalize(), rq), True)
                st.success("Utente creato!")
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# SIDEBAR
with st.sidebar:
    st.markdown(f"<div class='sidebar-title'>REMS PRO</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center;'>● {firma_op}</div>", unsafe_allow_html=True)
    st.divider()
    nav = st.radio("MENU", ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda", "🗺️ Mappa", "🗂️ Anagrafica", "⚙️ Admin"])
    if st.button("LOGOUT"):
        st.session_state.user_session = None
        st.rerun()

# --- 5. LE 6 PARTI OPERATIVE ---

# PARTE 1: MONITORAGGIO (DIARIO CLINICO)
if nav == "📊 Monitoraggio":
    st.title("📊 Diario Clinico Generale")
    pazienti = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    for pid, pnome in pazienti:
        with st.expander(f"📁 Scheda: {pnome}"):
            res = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            for d, r, o, n in res:
                role_cls = f"role-{r.lower().split()[0]}"
                st.markdown(f"""<div class='postit {role_cls}'>
                    <div class='postit-header'><b>{o}</b> | {d}</div><div>{n}</div>
                </div>""", unsafe_allow_html=True)

# PARTE 2: MODULO EQUIPE (KEEP TERAPIA, CASSA, SPECIALISTICI)
elif nav == "👥 Modulo Equipe":
    st.title("👥 Modulo Operativo")
    p_sel_nome = st.selectbox("Seleziona Paziente", [p[0] for p in db_run("SELECT nome FROM pazienti WHERE stato='ATTIVO'")], index=None)
    
    if p_sel_nome:
        p_id = db_run("SELECT id FROM pazienti WHERE nome=?", (p_sel_nome,))[0][0]
        
        # Logica Infermiere: KEEP TERAPIA
        if u['ruolo'] in ["Infermiere", "Admin"]:
            st.subheader("💊 Keep Terapia")
            turno = st.selectbox("Fascia Oraria", ["Mattina", "Pomeriggio", "Al bisogno"])
            terapie = db_run("SELECT id_u, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno FROM terapie WHERE p_id=?", (p_id,))
            
            for tid, farm, dose, m, p, b in terapie:
                if (turno=="Mattina" and m) or (turno=="Pomeriggio" and p) or (turno=="Al bisogno" and b):
                    st.write(f"**{farm}** - {dose}")
                    # Griglia quadratini mese corrente
                    firme = db_run("SELECT data, esito FROM eventi WHERE id=? AND nota LIKE ?", (p_id, f"%{farm}%"))
                    f_map = {int(f[0].split("/")[0]): f[1] for f in firme if "/" in f[0]}
                    
                    h = "<div class='scroll-giorni'>"
                    for d in range(1, 32):
                        cls = "quadratino"
                        if d == datetime.now().day: cls += " q-oggi"
                        esito = f_map.get(d, "-")
                        if esito == "A": cls += " q-assunto"
                        elif esito == "R": cls += " q-rifiuto"
                        h += f"<div class='{cls}'><b>{d}</b><br>{esito}</div>"
                    st.markdown(h + "</div>", unsafe_allow_html=True)
                    
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Assunto", key=f"A_{tid}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
                               (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ Assunto {farm} ({turno})", u['ruolo'], firma_op, "A"), True)
                        st.rerun()
                    if c2.button("❌ Rifiuto", key=f"R_{tid}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
                               (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"❌ Rifiuto {farm} ({turno})", u['ruolo'], firma_op, "R"), True)
                        st.rerun()

        # Logica Educatore: CASSA
        if u['ruolo'] in ["Educatore", "Admin"]:
            st.subheader("💰 Gestione Cassa")
            mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
            saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
            st.metric("Saldo Attuale", f"{saldo:.2f} €")
            with st.form("cassa_f"):
                t, i, c = st.selectbox("Tipo", ["ENTRATA", "USCITA"]), st.number_input("Euro"), st.text_input("Causale")
                if st.form_submit_button("Registra Movimento"):
                    db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", 
                           (p_id, get_now_it().strftime("%d/%m/%Y"), c, i, t, firma_op), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                           (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"💰 {t}: {i}€ ({c})", u['ruolo'], firma_op), True)
                    st.rerun()

# PARTE 3: AGENDA DINAMICA
elif nav == "📅 Agenda":
    st.title("📅 Agenda Appuntamenti")
    col_a, col_b = st.columns([2, 1])
    with col_b:
        with st.form("new_app"):
            pa = st.selectbox("Paziente", [p[0] for p in db_run("SELECT nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")])
            da, orar = st.date_input("Data"), st.time_input("Ora")
            dest = st.text_input("Destinazione / Note")
            mezzo = st.selectbox("Mezzo", ["Doblò", "Panda", "Privato"])
            if st.form_submit_button("Pianifica"):
                pid = db_run("SELECT id FROM pazienti WHERE nome=?", (pa,))[0][0]
                db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore, mezzo) VALUES (?,?,?,?,'PROGRAMMATO',?,?)", 
                       (pid, str(da), str(orar)[:5], dest, firma_op, mezzo), True)
                st.rerun()
    with col_a:
        # Calendario semplificato
        res_app = db_run("SELECT p.nome, a.data, a.ora, a.nota FROM appuntamenti a JOIN pazienti p ON a.p_id=p.id WHERE a.stato='PROGRAMMATO' ORDER BY a.data")
        st.table(pd.DataFrame(res_app, columns=["Paziente", "Data", "Ora", "Destinazione"]))

# PARTE 4: MAPPA POSTI LETTO
elif nav == "🗺️ Mappa":
    st.title("🗺️ Mappa Reparti")
    stanze = db_run("SELECT id, reparto, tipo FROM stanze")
    assegnati = db_run("SELECT p.nome, a.stanza_id, a.letto FROM pazienti p JOIN assegnazioni a ON p.id=a.p_id")
    mappa_p = {f"{sid}_{l}": nome for nome, sid, l in assegnati}
    
    for rep in ["A", "B"]:
        st.subheader(f"Reparto {rep}")
        cols = st.columns(5)
        r_stanze = [s for s in stanze if s[1] == rep]
        for i, s in enumerate(r_stanze):
            with cols[i % 5]:
                p1 = mappa_p.get(f"{s[0]}_1", "Libero")
                p2 = mappa_p.get(f"{s[0]}_2", "Libero")
                cls = "stanza-tile"
                if p1 != "Libero" and p2 != "Libero": cls += " stanza-piena"
                elif p1 != "Libero" or p2 != "Libero": cls += " stanza-occupata"
                st.markdown(f"<div class='{cls}'><b>Stanza {s[0]}</b><br><small>L1: {p1}<br>L2: {p2}</small></div>", unsafe_allow_html=True)

# PARTE 5: ANAGRAFICA
elif nav == "🗂️ Anagrafica":
    st.title("🗂️ Gestione Anagrafica")
    with st.form("nuovo_p"):
        c1, c2 = st.columns(2)
        nome_p = c1.text_input("Nome e Cognome")
        cf_p = c2.text_input("Codice Fiscale")
        if st.form_submit_button("Inserisci Paziente"):
            db_run("INSERT INTO pazienti (nome, cf) VALUES (?,?)", (nome_p.upper(), cf_p.upper()), True)
            st.success("Inserito")
    
    st.divider()
    for pid, nome, cf in db_run("SELECT id, nome, cf FROM pazienti WHERE stato='ATTIVO'"):
        c1, c2 = st.columns([4, 1])
        c1.write(f"**{nome}** ({cf})")
        if c2.button("Dimetti", key=f"dim_{pid}"):
            db_run("UPDATE pazienti SET stato='DIMESSO' WHERE id=?", (pid,), True)
            st.rerun()

# PARTE 6: ADMIN
elif nav == "⚙️ Admin":
    st.title("⚙️ Pannello di Controllo")
    st.subheader("Log Ultime Operazioni")
    logs = db_run("SELECT data_ora, utente, azione, dettaglio FROM logs_sistema ORDER BY id_log DESC LIMIT 50")
    st.table(pd.DataFrame(logs, columns=["Data", "User", "Azione", "Dettaglio"]))
