import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v12.5 ---
# Sviluppato da AntonioWebMaster
st.set_page_config(page_title="REMS Connect ELITE PRO", layout="wide", page_icon="🏥")

# --- STILE CSS ESTESO ---
st.markdown("""
<style>
    /* SIDEBAR PROFESSIONALE */
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 2px solid #334155; }
    .sidebar-title { 
        color: #f8fafc !important; font-size: 1.8rem !important; font-weight: 800 !important; 
        text-align: center; padding: 20px 0; border-bottom: 1px solid #334155;
    }
    .sidebar-footer { 
        position: fixed; bottom: 10px; left: 10px; color: #94a3b8 !important; 
        font-size: 0.7rem !important; line-height: 1.4;
    }
    
    /* BANNER SEZIONALI */
    .section-banner { 
        background: linear-gradient(90deg, #1e3a8a 0%, #1e40af 100%); 
        color: white !important; padding: 30px; border-radius: 15px; 
        margin-bottom: 25px; text-align: center; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }
    .section-banner h2 { color: white !important; margin: 0; text-transform: uppercase; letter-spacing: 2px; }
    .section-banner p { opacity: 0.8; font-style: italic; margin-top: 5px; }

    /* TABELLE DINAMICHE EQUIPE */
    .dynamic-table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; }
    .dynamic-table th { background-color: #1e293b; color: #f8fafc !important; padding: 15px; text-align: left; font-size: 0.9rem; border: 1px solid #334155; }
    .dynamic-table td { padding: 12px; border: 1px solid #e2e8f0; color: #1e293b; font-size: 0.85rem; vertical-align: middle; }
    .dynamic-table tr:nth-child(even) { background-color: #f8fafc; }
    .dynamic-table tr:hover { background-color: #f1f5f9; }
    
    /* BADGE E STATI */
    .badge { padding: 5px 12px; border-radius: 50px; font-weight: 700; font-size: 0.7rem; text-transform: uppercase; }
    .badge-ok { background-color: #dcfce7; color: #166534; }
    .badge-error { background-color: #fee2e2; color: #991b1b; }
    .badge-info { background-color: #e0e7ff; color: #3730a3; }

    /* BOTTONI AZIONE */
    .stButton>button { border-radius: 8px !important; font-weight: 600 !important; transition: 0.2s; }
</style>
""", unsafe_allow_html=True)

# --- MOTORE PERSISTENZA DATI (SQLITE COMPLETO) ---
DB_NAME = "rems_architecture_v12.db"

def db_init():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        # Tabella Staff
        cur.execute("""CREATE TABLE IF NOT EXISTS utenti (
            user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT, ultimo_accesso TEXT)""")
        # Tabella Anagrafica
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, data_ingresso TEXT, cella TEXT)")
        # Tabella Diario Clinico (Eventi)
        cur.execute("""CREATE TABLE IF NOT EXISTS eventi (
            id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, nota TEXT, ruolo TEXT, operatore TEXT, gravita TEXT)""")
        # Tabella Terapie
        cur.execute("""CREATE TABLE IF NOT EXISTS terapie (
            id_t INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, farmaco TEXT, dose TEXT, 
            mat INTEGER, pom INTEGER, nott INTEGER, prescritto_da TEXT, data_inizio TEXT, stato TEXT DEFAULT 'ATTIVO')""")
        # Tabella Economato (Cassa)
        cur.execute("""CREATE TABLE IF NOT EXISTS cassa (
            id_c INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, causale TEXT, 
            importo REAL, tipo TEXT, operatore TEXT)""")
        # Tabella Agenda Scadenze
        cur.execute("""CREATE TABLE IF NOT EXISTS agenda (
            id_a INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, 
            categoria TEXT, evento TEXT, completato INTEGER DEFAULT 0)""")
        conn.commit()

def db_run(query, params=(), commit=False):
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

# --- UTILS ---
def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- GESTIONE ACCESSO E SICUREZZA ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>REMS CONNECT ELITE PRO</h2><p>Sistemi Informativi Sanitari - AntonioWebMaster</p></div>", unsafe_allow_html=True)
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.subheader("🔐 Login Operatore")
        with st.form("login_form"):
            u_in = st.text_input("ID Utente")
            p_in = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI AL SISTEMA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res:
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "id": u_in}
                    db_run("UPDATE utenti SET ultimo_accesso=? WHERE user=?", (datetime.now().strftime("%Y-%m-%d %H:%M"), u_in), True)
                    st.rerun()
                else: st.error("Credenziali non autorizzate.")
    
    with col_r:
        st.subheader("📝 Registrazione Staff")
        with st.form("reg_form"):
            nu = st.text_input("Nuovo ID")
            np = st.text_input("Password", type="password")
            nn = st.text_input("Nome"); nc = st.text_input("Cognome")
            nq = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti (user, pwd, nome, cognome, qualifica) VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True)
                st.success("Operatore inserito.")
    st.stop()

# --- DASHBOARD PRINCIPALE ---
u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

st.sidebar.markdown(f"<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"🟢 **{u['nome'].upper()}**\n\n*{u['ruolo']}*")

nav = st.sidebar.radio("MODULI OPERATIVI", [
    "📊 Monitoraggio Pazienti", 
    "💊 Gestione Terapie", 
    "📝 Diario Multidisciplinare", 
    "💰 Servizio Cassa",
    "📅 Agenda & Udienze",
    "⚙️ Configurazione"
])

if st.sidebar.button("LOGOUT SICURO"): 
    st.session_state.user_session = None
    st.rerun()

st.sidebar.markdown(f"<div class='sidebar-footer'>REMS CONNECT v12.5<br>Core Engine: Python 3.x<br>DB: SQLite3 Local<br>Dev: <b>AntonioWebMaster</b></div>", unsafe_allow_html=True)

# --- 1. MONITORAGGIO PAZIENTI ---
if nav == "📊 Monitoraggio Pazienti":
    st.markdown("<div class='section-banner'><h2>STATO CLINICO GENERALE</h2><p>Riepilogo cartelle attive</p></div>", unsafe_allow_html=True)
    pazienti = db_run("SELECT id, nome, data_ingresso, cella FROM pazienti ORDER BY nome")
    
    if pazienti:
        for pid, nome, data, cella in pazienti:
            with st.expander(f"📁 PAZIENTE: {nome} (Ingresso: {data})"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown("#### Ultimi Eventi Registrati")
                    evs = db_run("SELECT data, ruolo, operatore, nota FROM eventi WHERE p_id=? ORDER BY id_u DESC LIMIT 5", (pid,))
                    if evs:
                        for d, r, o, nt in evs:
                            st.info(f"**{d}** - *{o} ({r})*:\n\n{nt}")
                    else: st.write("Nessun evento in cronologia.")
                with c2:
                    st.markdown("#### Info Rapide")
                    st.write(f"**Ubicazione:** Cella {cella}")
                    mov = db_run("SELECT SUM(CASE WHEN tipo='Entrata' THEN importo ELSE -importo END) FROM cassa WHERE p_id=?", (pid,))
                    saldo = mov[0][0] if mov[0][0] else 0
                    st.metric("Disponibilità Cassa", f"€ {saldo:.2f}")

# --- 2. GESTIONE TERAPIE (INFERMIERI / PSICHIATRI) ---
elif nav == "💊 Gestione Terapie":
    st.markdown("<div class='section-banner'><h2>CENTRO SOMMINISTRAZIONE</h2><p>Pianificazione e Firma Terapie</p></div>", unsafe_allow_html=True)
    
    if u['ruolo'] in ["Psichiatra", "Infermiere"]:
        t_piano, t_nuova = st.tabs(["📋 Tabella Dinamica Turno", "➕ Nuova Prescrizione"])
        
        with t_piano:
            turno_attivo = st.radio("Seleziona Turno Operativo:", ["MAT", "POM", "NOTT"], horizontal=True)
            # Query complessa: unisce pazienti e le loro terapie specifiche per il turno
            query = f"SELECT p.nome, t.farmaco, t.dose, t.id_t, t.p_id FROM terapie t JOIN pazienti p ON t.p_id = p.id WHERE t.{turno_attivo.lower()} = 1 AND t.stato='ATTIVO'"
            dati = db_run(query)
            
            if dati:
                st.markdown(f"### Farmaci in somministrazione per il turno: **{turno_attivo}**")
                # Header Tabella Manuale per controllo totale
                h_col = st.columns([3, 2, 2, 2, 2])
                h_col[0].write("**Paziente**")
                h_col[1].write("**Farmaco**")
                h_col[2].write("**Dose**")
                h_col[3].write("**Azione**")
                h_col[4].write("**Esito**")
                st.divider()

                for nome, farmaco, dose, tid, pid in dati:
                    r_col = st.columns([3, 2, 2, 2, 2])
                    r_col[0].write(f"**{nome}**")
                    r_col[1].write(farmaco)
                    r_col[2].write(dose)
                    
                    if r_col[3].button("✅ Firma", key=f"ok_{tid}"):
                        db_run("INSERT INTO eventi (p_id, data, nota, ruolo, operatore) VALUES (?,?,?,?,?)", 
                               (pid, datetime.now().strftime("%d/%m/%y %H:%M"), f"SOMM. TERAPIA: {farmaco} ({turno_attivo})", u['ruolo'], firma), True)
                        st.toast(f"Terapia {farmaco} registrata per {nome}")
                    
                    motivo = r_col[4].text_input("Nota se rifiuto", key=f"not_{tid}", label_visibility="collapsed")
                    if r_col[3].button("❌ Rifiuta", key=f"no_{tid}"):
                        db_run("INSERT INTO eventi (p_id, data, nota, ruolo, operatore) VALUES (?,?,?,?,?)", 
                               (pid, datetime.now().strftime("%d/%m/%y %H:%M"), f"RIFIUTO TERAPIA: {farmaco} ({turno_attivo}). Note: {motivo}", u['ruolo'], firma), True)
                        st.error("Rifiuto registrato.")
            else:
                st.success("Nessuna terapia programmata per questo turno.")

        with t_nuova:
            if u['ruolo'] == "Psichiatra":
                with st.form("presc"):
                    p_sel = st.selectbox("Paziente", [p[1] for p in db_run("SELECT id, nome FROM pazienti")])
                    pid = [p[0] for p in db_run("SELECT id, nome FROM pazienti") if p[1] == p_sel][0]
                    farm = st.text_input("Nome Farmaco")
                    dos = st.text_input("Dosaggio")
                    c1,c2,c3 = st.columns(3)
                    m = c1.checkbox("Mattina"); p = c2.checkbox("Pomeriggio"); n = c3.checkbox("Notte")
                    if st.form_submit_button("REGISTRA PRESCRIZIONE"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, prescritto_da, data_inizio) VALUES (?,?,?,?,?,?,?,?)",
                               (pid, farm, dos, int(m), int(p), int(n), firma, date.today().strftime("%d/%m/%Y")), True)
                        st.success("Farmaco inserito nel piano terapeutico.")
            else:
                st.warning("Solo i Medici Psichiatri possono prescrivere nuove terapie.")

# --- 3. DIARIO MULTIDISCIPLINARE ---
elif nav == "📝 Diario Multidisciplinare":
    st.markdown("<div class='section-banner'><h2>REGISTRO ATTIVITÀ</h2><p>Inserimento note e osservazioni</p></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        
        with st.form("diario_f"):
            nota = st.text_area("Inserisci osservazione clinica o attività svolta")
            grav = st.select_slider("Livello di Attenzione", ["Normale", "Monitoraggio", "Urgente"])
            if st.form_submit_button("SALVA NEL DIARIO"):
                db_run("INSERT INTO eventi (p_id, data, nota, ruolo, operatore, gravita) VALUES (?,?,?,?,?,?)",
                       (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota, u['ruolo'], firma, grav), True)
                st.success("Nota salvata.")
        
        st.divider()
        st.subheader("Storico Recente")
        storico = db_run("SELECT data, operatore, nota, gravita FROM eventi WHERE p_id=? ORDER BY id_u DESC LIMIT 10", (p_id,))
        for d, op, nt, gr in storico:
            color = "red" if gr == "Urgente" else "blue" if gr == "Monitoraggio" else "black"
            st.markdown(f"**{d}** - Operatore: {op}  \n**Stato:** :{color}[{gr}]  \n{nt}")
            st.write("---")

# --- 4. SERVIZIO CASSA ---
elif nav == "💰 Servizio Cassa":
    st.markdown("<div class='section-banner'><h2>GESTIONE FONDI PAZIENTI</h2><p>Contabilità interna ed economato</p></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Nuovo Movimento")
            with st.form("cassa_f"):
                tipo = st.radio("Tipo Operazione", ["Entrata", "Uscita"], horizontal=True)
                importo = st.number_input("Somma (€)", min_value=0.0, step=0.5)
                causale = st.text_input("Causale (es. Acquisto sigarette, versamento familiare)")
                if st.form_submit_button("REGISTRA MOVIMENTO"):
                    db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, operatore) VALUES (?,?,?,?,?,?)",
                           (p_id, date.today().strftime("%d/%m/%Y"), causale, importo, tipo, firma), True)
                    st.success("Contabilità aggiornata.")
        with c2:
            st.subheader("Situazione Contabile")
            movimenti = db_run("SELECT data, causale, importo, tipo FROM cassa WHERE p_id=? ORDER BY id_c DESC", (p_id,))
            if movimenti:
                df_cassa = pd.DataFrame(movimenti, columns=["Data", "Causale", "Euro", "Tipo"])
                st.dataframe(df_cassa, use_container_width=True)
            else: st.info("Nessun movimento registrato.")

# --- 5. AGENDA & UDIENZE ---
elif nav == "📅 Agenda & Udienze":
    st.markdown("<div class='section-banner'><h2>SCADENZIARIO E APPUNTAMENTI</h2></div>", unsafe_allow_html=True)
    with st.form("agenda_f"):
        p_sel = st.selectbox("Paziente", [p[1] for p in db_run("SELECT id, nome FROM pazienti")])
        pid = [p[0] for p in db_run("SELECT id, nome FROM pazienti") if p[1] == p_sel][0]
        c1, c2 = st.columns(2)
        d_ev = c1.date_input("Data Evento")
        o_ev = c2.text_input("Ora (HH:MM)")
        cat = st.selectbox("Categoria", ["Udienza Tribunale", "Visita Specialistica", "Permesso Premio", "Incontro Avvocato"])
        desc = st.text_area("Dettagli Evento")
        if st.form_submit_button("AGGIUNGI IN AGENDA"):
            db_run("INSERT INTO agenda (p_id, data, ora, categoria, evento) VALUES (?,?,?,?,?)",
                   (pid, d_ev.strftime("%d/%m/%Y"), o_ev, cat, desc), True)
            st.success("Evento pianificato.")

# --- 6. CONFIGURAZIONE ---
elif nav == "⚙️ Configurazione":
    st.markdown("### GESTIONE ANAGRAFICA PAZIENTI")
    with st.form("paz_f"):
        nome_p = st.text_input("Nome e Cognome Paziente")
        cella_p = st.text_input("Cella / Settore")
        if st.form_submit_button("REGISTRA NUOVO INGRESSO"):
            db_run("INSERT INTO pazienti (nome, data_ingresso, cella) VALUES (?,?,?)",
                   (nome_p.upper(), date.today().strftime("%d/%m/%Y"), cella_p), True)
            st.success("Paziente inserito nel sistema.")
    
    st.divider()
    st.subheader("Pazienti a Sistema")
    list_p = db_run("SELECT id, nome, cella FROM pazienti")
    for pid, nome, cella in list_p:
        c1, c2 = st.columns([5,1])
        c1.write(f"**{nome}** - Ubicazione: {cella}")
        if c2.button("❌", key=f"del_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True)
            st.rerun()
