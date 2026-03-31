import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v12.5 FULL ---
st.set_page_config(
    page_title="REMS Connect ELITE PRO",
    layout="wide",
    page_icon="🏥",
    initial_sidebar_state="expanded"
)

# --- MOTORE CSS PERSONALIZZATO ---
st.markdown("""
<style>
    /* SIDEBAR PROFESSIONALE */
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 2px solid #334155; }
    .sidebar-title { 
        color: #f8fafc !important; font-size: 1.8rem !important; font-weight: 800 !important; 
        text-align: center; padding: 25px 0; border-bottom: 1px solid #334155;
    }
    .sidebar-footer { 
        position: fixed; bottom: 10px; left: 10px; color: #94a3b8 !important; 
        font-size: 0.75rem !important; line-height: 1.4; z-index: 100;
    }
    
    /* BANNER SEZIONALI */
    .section-banner { 
        background: linear-gradient(90deg, #1e3a8a 0%, #1e40af 100%); 
        color: white !important; padding: 30px; border-radius: 15px; 
        margin-bottom: 25px; text-align: center; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }
    .section-banner h2 { color: white !important; margin: 0; text-transform: uppercase; font-weight: 900; }
    .section-banner p { opacity: 0.8; font-style: italic; margin-top: 5px; }

    /* TABELLE DI REPORT */
    .report-table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 12px; text-align: left; }
    .report-table td { padding: 10px; border: 1px solid #e2e8f0; font-size: 0.85rem; color: #1e293b; }

    /* CARD TERAPIA INFERMIERE */
    .therapy-card { 
        background: white; border-left: 6px solid #1e3a8a; padding: 15px; 
        border-radius: 10px; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
    }
    .therapy-card b { color: #1e3a8a; font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

# --- MOTORE PERSISTENZA DATI (SQLITE AVANZATO) ---
DB_NAME = "rems_enterprise_v12.db"

def db_init():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS utenti (
            user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS pazienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, data_ingresso TEXT, stato TEXT DEFAULT 'ATTIVO')""")
        cur.execute("""CREATE TABLE IF NOT EXISTS eventi (
            id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, categoria TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS terapie (
            id_t INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, farmaco TEXT, dose TEXT, 
            mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, stato TEXT DEFAULT 'ATTIVO')""")
        cur.execute("""CREATE TABLE IF NOT EXISTS cassa (
            id_c INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, causale TEXT, 
            importo REAL, tipo TEXT, op TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS agenda (
            id_a INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, categoria TEXT, evento TEXT)""")
        conn.commit()

def db_query(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        try:
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore Database: {e}")
            return []

db_init()
def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- GESTIONE SESSIONE E LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = None

if not st.session_state.auth:
    st.markdown("<div class='section-banner'><h2>REMS CONNECT ELITE PRO</h2><p>Piattaforma di Gestione Integrata - AntonioWebMaster</p></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        with st.form("login"):
            u_in = st.text_input("User ID")
            p_in = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_query("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res:
                    st.session_state.auth = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Credenziali non valide.")
    with c2:
        with st.form("reg"):
            nu = st.text_input("Nuovo ID")
            np = st.text_input("Scegli Password", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA STAFF"):
                db_query("INSERT INTO utenti (user, pwd, nome, cognome, qualifica) VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True)
                st.success("Operatore registrato.")
    st.stop()

u = st.session_state.auth
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR NAVIGAZIONE ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"🟢 **{u['nome'].upper()}**\n\n*{u['ruolo']}*")

nav = st.sidebar.radio("MODULI OPERATIVI", [
    "📊 Monitoraggio", "💊 Terapie", "📝 Diario Clinico", "💰 Cassa Pazienti", "📅 Agenda Legale", "⚙️ Sistema"
])

if st.sidebar.button("LOGOUT SICURO"):
    st.session_state.auth = None
    st.rerun()

st.sidebar.markdown(f"<div class='sidebar-footer'><b>REMS CONNECT v12.5</b><br>Core Architecture: AntonioWebMaster</div>", unsafe_allow_html=True)

# --- 1. MONITORAGGIO ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>QUADRO CLINICO GENERALE</h2></div>", unsafe_allow_html=True)
    pax = db_query("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    for pid, nome in pax:
        with st.expander(f"📁 PAZIENTE: {nome}"):
            evs = db_query("SELECT data, op, nota FROM eventi WHERE p_id=? ORDER BY id_u DESC LIMIT 10", (pid,))
            if evs:
                st.table(pd.DataFrame(evs, columns=["Data/Ora", "Operatore", "Nota Clinica"]))
            else: st.info("Nessun evento registrato per questo paziente.")

# --- 2. TERAPIE (SOMMINISTRAZIONE + ELIMINAZIONE) ---
elif nav == "💊 Terapie":
    st.markdown("<div class='section-banner'><h2>PIANO TERAPEUTICO</h2></div>", unsafe_allow_html=True)
    
    if u['ruolo'] == "Psichiatra":
        t1, t2 = st.tabs(["📋 Gestione Terapie Attive", "➕ Nuova Prescrizione"])
        
        with t1:
            st.subheader("Sospensione Farmaci")
            attive = db_query("""
                SELECT t.id_t, p.nome, t.farmaco, t.dose, t.mat, t.pom, t.nott, t.p_id
                FROM terapie t JOIN pazienti p ON t.p_id = p.id 
                WHERE t.stato='ATTIVO' ORDER BY p.nome
            """)
            if attive:
                for tid, p_nome, farm, dose, m, p, n, p_id_ref in attive:
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.markdown(f"**{p_nome}**: {farm} ({dose})")
                    c2.caption(f"Turni: {'MAT ' if m else ''}{'POM ' if p else ''}{'NOT' if n else ''}")
                    if c3.button("❌ Elimina", key=f"del_{tid}"):
                        db_query("UPDATE terapie SET stato='SOSPESO' WHERE id_t=?", (tid,), True)
                        db_query("INSERT INTO eventi (p_id, data, nota, ruolo, op, categoria) VALUES (?,?,?,?,?,?)",
                                 (p_id_ref, datetime.now().strftime("%d/%m/%Y %H:%M"), f"🚫 SOSPESA TERAPIA: {farm}", u['ruolo'], firma, "Terapia"), True)
                        st.rerun()
            else: st.info("Nessuna terapia attiva.")

        with t2:
            with st.form("presc"):
                pax_list = db_query("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
                if pax_list:
                    sel_p = st.selectbox("Paziente", [p[1] for p in pax_list])
                    pid = [p[0] for p in pax_list if p[1] == sel_p][0]
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3); m=c1.checkbox("MAT"); p=c2.checkbox("POM"); n=c3.checkbox("NOTT")
                    if st.form_submit_button("REGISTRA PRESCRIZIONE"):
                        db_query("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (pid, f, d, int(m), int(p), int(n), firma), True)
                        db_query("INSERT INTO eventi (p_id, data, nota, ruolo, op, categoria) VALUES (?,?,?,?,?,?)", (pid, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📝 Prescritto: {f} {d}", u['ruolo'], firma, "Terapia"), True)
                        st.success("Terapia salvata.")
                else: st.warning("Inserire pazienti in anagrafica prima di prescrivere.")

    elif u['ruolo'] == "Infermiere":
        turno = st.radio("Seleziona Turno Operativo:", ["MAT", "POM", "NOTT"], horizontal=True)
        t_col = turno.lower() if turno != "NOTT" else "nott"
        data_t = db_query(f"SELECT p.nome, t.farmaco, t.dose, t.id_t, t.p_id FROM terapie t JOIN pazienti p ON t.p_id = p.id WHERE t.{t_col}=1 AND t.stato='ATTIVO'")
        if data_t:
            for nome, farm, dose, tid, pid in data_t:
                st.markdown(f"<div class='therapy-card'><b>{nome}</b>: {farm} ({dose})</div>", unsafe_allow_html=True)
                if st.button("FIRMA SOMMINISTRAZIONE", key=f"f_{tid}"):
                    db_query("INSERT INTO eventi (p_id, data, nota, ruolo, op, categoria) VALUES (?,?,?,?,?,?)", (pid, datetime.now().strftime("%d/%m %H:%M"), f"✔️ SOMM: {farm} ({turno})", u['ruolo'], firma, "Terapia"), True)
                    st.success(f"Fatto per {nome}")
                    st.rerun()
        else: st.info("Nessuna terapia programmata per questo turno.")

# --- 3. DIARIO CLINICO ---
elif nav == "📝 Diario Clinico":
    st.markdown("<div class='section-banner'><h2>DIARIO MULTIDISCIPLINARE</h2></div>", unsafe_allow_html=True)
    pax_l = db_query("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
    if pax_l:
        p_sel = st.selectbox("Paziente", [p[1] for p in pax_l])
        pid = [p[0] for p in pax_l if p[1] == p_sel][0]
        with st.form("diario"):
            nota = st.text_area("Nota o Osservazione")
            if st.form_submit_button("SALVA NEL DIARIO"):
                db_query("INSERT INTO eventi (p_id, data, nota, ruolo, op, categoria) VALUES (?,?,?,?,?,?)", (pid, datetime.now().strftime("%d/%m/%Y %H:%M"), nota, u['ruolo'], firma, "Diario"), True)
                st.success("Nota salvata.")
    else: st.warning("Nessun paziente attivo.")

# --- 4. CASSA PAZIENTI ---
elif nav == "💰 Cassa Pazienti":
    st.markdown("<div class='section-banner'><h2>GESTIONE ECONOMATO</h2></div>", unsafe_allow_html=True)
    pax_l = db_query("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
    if pax_l:
        p_sel = st.selectbox("Paziente", [p[1] for p in pax_l])
        pid = [p[0] for p in pax_l if p[1] == p_sel][0]
        
        movs = db_query("SELECT importo, tipo FROM cassa WHERE p_id=?", (pid,))
        saldo = sum([m[0] if m[1] == "Entrata" else -m[0] for m in movs])
        st.metric("DISPONIBILITÀ ATTUALE", f"€ {saldo:.2f}")
        
        with st.form("cassa"):
            t = st.radio("Operazione", ["Entrata", "Uscita"], horizontal=True)
            i = st.number_input("Importo (€)", step=0.50)
            c = st.text_input("Causale")
            if st.form_submit_button("REGISTRA MOVIMENTO"):
                db_query("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (pid, date.today().strftime("%d/%m/%Y"), c, i, t, firma), True)
                st.rerun()
    else: st.warning("Nessun paziente attivo.")

# --- 5. AGENDA LEGALE ---
elif nav == "📅 Agenda Legale":
    st.markdown("<div class='section-banner'><h2>AGENDA UDIENZE E VISITE</h2></div>", unsafe_allow_html=True)
    with st.form("agenda"):
        pax_l = db_query("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
        if pax_l:
            p_sel = st.selectbox("Paziente", [p[1] for p in pax_l])
            pid = [p[0] for p in pax_l if p[1] == p_sel][0]
            d = st.date_input("Data"); o = st.text_input("Ora (HH:MM)"); cat = st.selectbox("Categoria", ["Udienza", "Visita", "Permesso"]); ev = st.text_area("Note")
            if st.form_submit_button("PIANIFICA EVENTO"):
                db_query("INSERT INTO agenda (p_id, data, ora, categoria, evento) VALUES (?,?,?,?,?)", (pid, d.strftime("%d/%m/%Y"), o, cat, ev), True)
                st.success("Evento inserito.")
        else: st.warning("Inserire pazienti in anagrafica.")
    
    st.subheader("📅 Scadenziario")
    res_a = db_query("SELECT a.data, a.ora, p.nome, a.categoria FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY a.data ASC")
    if res_a: st.table(pd.DataFrame(res_a, columns=["Data", "Ora", "Paziente", "Tipo"]))

# --- 6. SISTEMA ---
elif nav == "⚙️ Sistema":
    st.markdown("### GESTIONE ANAGRAFICA")
    with st.form("new_p"):
        nome_nuovo = st.text_input("Nuovo Paziente (Nome Cognome)")
        if st.form_submit_button("REGISTRA INGRESSO"):
            db_query("INSERT INTO pazienti (nome, data_ingresso) VALUES (?,?)", (nome_nuovo.upper(), date.today().strftime("%d/%m/%Y")), True)
            st.success("Paziente inserito.")
