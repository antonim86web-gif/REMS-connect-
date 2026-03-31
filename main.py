import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12.5", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* SIDEBAR BLU */
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    
    /* TITOLO PERSONALIZZATO SIDEBAR */
    .sidebar-title {
        color: #ffffff !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        text-align: center;
        margin-bottom: 1rem;
        padding-top: 10px;
        border-bottom: 2px solid #ffffff33;
    }

    /* CREDITI SIDEBAR */
    .sidebar-footer {
        position: fixed;
        bottom: 10px;
        left: 10px;
        color: #ffffff99 !important;
        font-size: 0.75rem !important;
        line-height: 1.2;
        z-index: 100;
    }
    
    /* BANNER SEZIONE (BLU CON SCRITTA BIANCA) */
    .section-banner {
        background-color: #1e3a8a;
        color: white !important;
        padding: 25px;
        border-radius: 12px;
        margin-bottom: 30px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .section-banner h2 { color: white !important; margin: 0; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; }
    .section-banner p { margin: 8px 0 0 0; opacity: 0.9; font-size: 1.1rem; font-style: italic; }

    /* FORZA BIANCO NELLA SIDEBAR */
    [data-testid="stSidebar"] *, 
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stMarkdown p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* TASTO LOGOUT */
    [data-testid="stSidebar"] button {
        background-color: #dc2626 !important;
        color: white !important;
        font-weight: 800 !important;
        border: 2px solid #ffffff !important;
        border-radius: 10px !important;
        width: 100% !important;
        margin-top: 20px;
    }
    
    /* TABELLE */
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 12px; text-align: left; }
    .report-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; color: #1e293b; font-size: 0.9rem; }
    
    /* BADGE */
    .badge { padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; color: white; font-weight: bold; }
    .cat-badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; color: white; }
    .cat-udienza { background-color: #dc2626; } 
    .cat-medica { background-color: #2563eb; }  
    .cat-uscita { background-color: #059669; }  
    .cat-parenti { background-color: #d97706; }
</style>
""", unsafe_allow_html=True)

# --- GESTIONE DATABASE ---
DB_NAME = "rems_final_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, categoria TEXT, evento TEXT, stato TEXT)")
        try:
            if query: cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except sqlite3.IntegrityError:
            st.error("Errore di integrità: Dato già presente.")
            return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def mostra_report_settoriale(p_id, ruolo_utente):
    st.write("---")
    st.subheader(f"📋 Registro Attività Recenti - {ruolo_utente}")
    eventi = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? AND ruolo=? ORDER BY id_u DESC LIMIT 10", (p_id, ruolo_utente))
    if eventi:
        h = "<table class='report-table'><thead><tr><th>Data/Ora</th><th>Operatore</th><th>Attività Svolta</th></tr></thead><tbody>"
        for d, r, o, nt in eventi:
            h += f"<tr><td>{d}</td><td>{o}</td><td>{nt}</td></tr>"
        st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- SISTEMA DI ACCESSO ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>REMS CONNECT ELITE PRO</h2><p>Piattaforma Gestionale Sanitaria - Accesso Riservato</p></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Login Operatore", "📝 Registrazione Nuovo Staff"])
    with t1:
        with st.form("login"):
            u_in, p_in = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res: 
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Credenziali errate.")
    with t2:
        with st.form("reg"):
            nu, np = st.text_input("Username"), st.text_input("Password", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True)
                st.success("Registrazione completata.")
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR COMPLETA ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"### 👤 {u['nome']} {u['cognome']}")
nav = st.sidebar.radio("NAVIGAZIONE PRINCIPALE", ["📊 Monitoraggio Generale", "👥 Modulo Equipe", "📅 Agenda Appuntamenti", "⚙️ Gestione Sistema"])
if st.sidebar.button("LOGOUT / ESCI"): st.session_state.user_session = None; st.rerun()
st.sidebar.markdown(f"<div class='sidebar-footer'>REMS v12.5.0 ELITE PRO<br>Created by: <b>AntonioWebMaster</b></div>", unsafe_allow_html=True)

# --- 1. MONITORAGGIO / DIARIO CLINICO ---
if nav == "📊 Monitoraggio Generale":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO INTEGRATO</h2><p>Monitoraggio centralizzato di tutti gli eventi clinici, educativi e assistenziali</p></div>", unsafe_allow_html=True)
    pax = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in pax:
        with st.expander(f"📁 CARTELLA: {nome.upper()}"):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                h = "<table class='report-table'><thead><tr><th>Data</th><th>Qualifica</th><th>Operatore</th><th>Nota Clinica</th></tr></thead><tbody>"
                for d, r, o, nt in evs:
                    h += f"<tr><td>{d}</td><td>{r}</td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- 2. MODULO EQUIPE ---
elif nav == "👥 Modulo Equipe":
    desc_ruolo = {
        "Psichiatra": "Gestione prescrizioni farmacologiche e monitoraggio diagnostico.",
        "Infermiere": "Somministrazione terapie, parametri vitali e consegne infermieristiche.",
        "Educatore": "Progetti riabilitativi, attività esterne e gestione cassa pazienti.",
        "OSS": "Monitoraggio igiene, comfort alberghiero e supporto assistenziale."
    }
    st.markdown(f"<div class='section-banner'><h2>AREA OPERATIVA: {u['ruolo'].upper()}</h2><p>{desc_ruolo.get(u['ruolo'], '')}</p></div>", unsafe_allow_html=True)
    
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente in carico", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        # --- PSICHIATRA ---
        if u['ruolo'] == "Psichiatra":
            with st.form("psic"):
                f, d = st.text_input("Farmaco"), st.text_input("Dosaggio/Posologia")
                c1,c2,c3 = st.columns(3); m=c1.checkbox("MAT"); p=c2.checkbox("POM"); n=c3.checkbox("NOT")
                if st.form_submit_button("SALVA PRESCRIZIONE"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📝 Prescritta terapia: {f} {d}", "Psichiatra", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "Psichiatra")

        # --- INFERMIERE ---
        elif u['ruolo'] == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 Terapie", "📝 Consegne", "📊 Parametri"])
            with t1:
                ter = db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,))
                for tid, fa, do in ter:
                    with st.expander(f"📌 {fa} - {do}", expanded=True):
                        c_dt, c_btn = st.columns([3, 1])
                        d_s = c_dt.text_input("Ora Somministrazione", value=datetime.now().strftime("%d/%m/%Y %H:%M"), key=f"t_{tid}")
                        if c_btn.button("REGISTRA", key=f"b_{tid}"):
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, d_s, f"✔️ Somministrato: {fa} {do}", "Infermiere", firma), True); st.rerun()
            with t2:
                nota = st.text_area("Inserisci consegna di fine turno")
                if st.button("SALVA CONSEGNA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota, "Infermiere", firma), True); st.rerun()
            with t3:
                with st.form("pv"):
                    c1,c2,c3 = st.columns(3); mx=c1.number_input("Pressione MAX"); mn=c2.number_input("MIN"); fc=c3.number_input("FC")
                    if st.form_submit_button("REGISTRA PARAMETRI"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📊 PA:{mx}/{mn} FC:{fc}", "Infermiere", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "Infermiere")

        # --- EDUCATORE ---
        elif u['ruolo'] == "Educatore":
            tc, te = st.tabs(["💰 Gestione Cassa", "📝 Nota Educativa"])
            with tc:
                movs = db_run("SELECT data, causale, importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
                st.metric("DISPONIBILITÀ PAZIENTE", f"€ {saldo:.2f}")
                with st.form("c"):
                    tipo=st.radio("Movimento", ["Entrata", "Uscita"], horizontal=True); imp=st.number_input("Importo €"); cau=st.text_input("Causale")
                    if st.form_submit_button("REGISTRA MOVIMENTO"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), cau, imp, tipo, firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"💰 {tipo}: €{imp} ({cau})", "Educatore", firma), True); st.rerun()
            with te:
                nota_e = st.text_area("Descrizione attività / intervento")
                if st.button("SALVA DIARIO EDUCATIVO"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota_e, "Educatore", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "Educatore")

        # --- OSS ---
        elif u['ruolo'] == "OSS":
            act = st.selectbox("Attività Svolta", ["Igiene Personale", "Pulizia Camera", "Distribuzione Pasti", "Monitoraggio Notturno"])
            obs = st.text_area("Osservazioni / Note")
            if st.button("SALVA ATTIVITÀ OSS"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"🛠️ {act}: {obs}", "OSS", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "OSS")

# --- 3. AGENDA ---
elif nav == "📅 Agenda Appuntamenti":
    st.markdown("<div class='section-banner'><h2>AGENDA E SCADENZIARIO</h2><p>Pianificazione coordinata di uscite, udienze e visite mediche</p></div>", unsafe_allow_html=True)
    with st.form("ag"):
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        p_sel = st.selectbox("Paziente", [p[1] for p in p_lista])
        pid = [p[0] for p in p_lista if p[1] == p_sel][0]
        c1, c2, c3 = st.columns(3)
        d_app, o_app, cat = c1.date_input("Giorno"), c2.text_input("Ora"), c3.selectbox("Categoria", ["Uscita", "Visita Medica", "Udienza", "Parenti"])
        desc = st.text_area("Dettagli / Luogo / Accompagnatori")
        if st.form_submit_button("REGISTRA APPUNTAMENTO"):
            db_run("INSERT INTO agenda (p_id, data, ora, categoria, evento) VALUES (?,?,?,?,?)", (pid, d_app.strftime("%d/%m/%Y"), o_app, cat, desc), True); st.success("Pianificato!")
    
    apps = db_run("SELECT a.data, a.ora, a.categoria, p.nome, a.evento FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY a.data ASC")
    if apps:
        h = "<table class='report-table'><thead><tr><th>Data</th><th>Ora</th><th>Paziente</th><th>Tipo</th><th>Dettaglio</th></tr></thead><tbody>"
        for d, o, c, n, e in apps:
            cls = "cat-uscita" if c == "Uscita" else "cat-medica" if c == "Visita Medica" else "cat-udienza" if c == "Udienza" else "cat-parenti"
            h += f"<tr><td>{d}</td><td>{o}</td><td>{n}</td><td><span class='cat-badge {cls}'>{c}</span></td><td>{e}</td></tr>"
        st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- 4. GESTIONE SISTEMA ---
elif nav == "⚙️ Gestione Sistema":
    st.markdown("<div class='section-banner'><h2>GESTIONE ANAGRAFICA</h2><p>Inserimento e manutenzione dei dati relativi ai pazienti della struttura</p></div>", unsafe_allow_html=True)
    with st.form("add_p"):
        np = st.text_input("Nome e Cognome Nuovo Paziente")
        if st.form_submit_button("AGGIUNGI PAZIENTE"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    
    st.write("### Elenco Pazienti Attivi")
    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        c1, c2 = st.columns([5,1])
        c1.write(f"👤 {n}")
        if c2.button("🗑️", key=f"del_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
