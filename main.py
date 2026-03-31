import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* SIDEBAR BLU PROFESSIONALE */
    [data-testid="stSidebar"] {
        background-color: #1e3a8a !important;
        border-right: 2px solid #1e293b;
    }
    
    /* TESTO MENU LATERALE */
    [data-testid="stSidebar"] .stRadio label {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
    }

    /* TASTO LOGOUT - MASSIMA LEGGIBILITÀ */
    [data-testid="stSidebar"] button {
        background-color: #991b1b !important; /* Rosso Scuro */
        color: #ffffff !important;           /* Testo Bianco */
        font-weight: 800 !important;
        border: 2px solid #f87171 !important;
        border-radius: 8px !important;
        padding: 10px !important;
        text-transform: uppercase;
        margin-top: 20px;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #7f1d1d !important; /* Rosso ancora più scuro al passaggio */
        border-color: #ffffff !important;
    }

    .main-title { text-align: center; color: #1e3a8a; font-weight: 800; font-size: 2.5rem; margin-bottom: 20px; }
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; margin-top: 10px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 10px; text-align: left; font-size: 0.8rem; }
    .report-table td { padding: 8px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; }
    .badge { padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; color: white; font-weight: bold; }
    .bg-psichiatra { background: #dc2626; } .bg-infermiere { background: #2563eb; }
    .bg-educatore { background: #059669; } .bg-oss { background: #d97706; }
    
    /* BADGE CATEGORIE AGENDA */
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
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def mostra_report_settoriale(p_id, ruolo_utente):
    st.write("---")
    st.subheader(f"📋 Registro Attività {ruolo_utente}")
    eventi = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? AND ruolo=? ORDER BY id_u DESC LIMIT 10", (p_id, ruolo_utente))
    if eventi:
        h = "<table class='report-table'><thead><tr><th>Data/Ora</th><th>Operatore</th><th>Attività / Nota</th></tr></thead><tbody>"
        for d, r, o, nt in eventi:
            h += f"<tr><td>{d}</td><td>{o}</td><td>{nt}</td></tr>"
        st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- SISTEMA DI ACCESSO ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<h1 class='main-title'>REMS CONNECT ELITE PRO</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Login", "📝 Registrazione Operatore"])
    with t1:
        with st.form("login_form"):
            u_in = st.text_input("Username")
            p_in = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res: 
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Credenziali non valide")
    with t2:
        with st.form("reg_form"):
            nu, np = st.text_input("Nuovo User"), st.text_input("Nuova Pass", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Ruolo Professionale", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True)
                st.success("Account Creato")
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# Sidebar
st.sidebar.markdown(f"### 🧑‍⚕️ {u['nome']} {u['cognome']}")
nav = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio Generale", "👥 Modulo Equipe", "📅 Agenda Appuntamenti", "⚙️ Gestione Sistema"])
if st.sidebar.button("LOGOUT / ESCI"): st.session_state.user_session = None; st.rerun()

# --- 1. MONITORAGGIO ---
if nav == "📊 Monitoraggio Generale":
    st.markdown("<h2 class='main-title'>Diario Clinico Integrato</h2>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 PAZIENTE: {nome.upper()}"):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                h = "<table class='report-table'><thead><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Evento</th></tr></thead><tbody>"
                for d, r, o, nt in evs:
                    h += f"<tr><td>{d}</td><td><span class='badge bg-{r.lower()}'>{r}</span></td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- 2. MODULO EQUIPE ---
elif nav == "👥 Modulo Equipe":
    st.write(f"Operativo come: **{firma}**")
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        if u['ruolo'] == "Psichiatra":
            with st.form("form_psic"):
                f, d = st.text_input("Farmaco"), st.text_input("Dosaggio")
                c1,c2,c3 = st.columns(3); m=c1.checkbox("MAT"); p=c2.checkbox("POM"); n=c3.checkbox("NOT")
                if st.form_submit_button("CONFERMA PRESCRIZIONE"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📝 Prescritta: {f} {d}", "Psichiatra", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "Psichiatra")

        elif u['ruolo'] == "Infermiere":
            tab1, tab2, tab3 = st.tabs(["💊 Somministrazione Legale", "📝 Consegne", "📊 Parametri Vitali"])
            with tab1:
                ter = db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,))
                for tid, fa, do in ter:
                    with st.expander(f"📌 {fa} ({do})", expanded=True):
                        c_dt, c_ass, c_rif, c_btn = st.columns([2, 1, 1, 1])
                        d_s = c_dt.text_input("Data/Ora Effettiva", value=datetime.now().strftime("%d/%m/%Y %H:%M"), key=f"dt_{tid}")
                        ass = c_ass.checkbox("Assume", key=f"ass_{tid}")
                        rif = c_rif.checkbox("Rifiuta", key=f"rif_{tid}")
                        if c_btn.button("REGISTRA SOMM.", key=f"btn_{tid}"):
                            if ass != rif:
                                s = "✔️ SOMMINISTRATO" if ass else "❌ RIFIUTATO"
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, d_s, f"{s}: {fa} ({do})", "Infermiere", firma), True); st.rerun()
                            else: st.error("Selezionare solo una opzione")
            with tab2:
                nota_inf = st.text_area("Consegna di fine turno")
                if st.button("SALVA CONSEGNA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota_inf, "Infermiere", firma), True); st.rerun()
            with tab3:
                with st.form("pv_form"):
                    c1,c2,c3,c4 = st.columns(4); mx=c1.number_input("Pressione MAX", value=None); mn=c2.number_input("Pressione MIN", value=None); fc=c3.number_input("Frequenza (FC)", value=None); sp=c4.number_input("Saturazione (SpO2)", value=None)
                    if st.form_submit_button("REGISTRA PARAMETRI"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📊 PA:{mx}/{mn} FC:{fc} SpO2:{sp}", "Infermiere", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "Infermiere")

        elif u['ruolo'] == "Educatore":
            tab_c, tab_e = st.tabs(["💰 Gestione Cassa", "📝 Diario Educativo"])
            with tab_c:
                movs = db_run("SELECT data, causale, importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
                st.metric("SALDO DISPONIBILE", f"€ {saldo:.2f}")
                with st.form("cassa_form"):
                    t=st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True); i=st.number_input("Importo", 0.0); c=st.text_input("Causale")
                    if st.form_submit_button("SALVA MOVIMENTO"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), c, i, t, firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"💰 {t}: €{i} ({c})", "Educatore", firma), True); st.rerun()
            with tab_e:
                nota_e = st.text_area("Nota Attività Educativa")
                if st.button("SALVA NOTA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota_e, "Educatore", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "Educatore")

        elif u['ruolo'] == "OSS":
            st.subheader("Mansionario Operativo OSS")
            m_s = st.selectbox("Attività Svolta", ["Igiene Personale", "Pulizia Camera", "Distribuzione Pasti", "Sanificazione Sale", "Controllo Cortile", "Lavatrice/Guardaroba"])
            n_o = st.text_area("Osservazioni durante l'attività")
            if st.button("REGISTRA ATTIVITÀ OSS"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"🛠️ {m_s}: {n_o}", "OSS", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "OSS")

# --- 3. AGENDA APPUNTAMENTI ---
elif nav == "📅 Agenda Appuntamenti":
    st.markdown("<h2 class='main-title'>Gestione Agenda REMS</h2>", unsafe_allow_html=True)
    with st.form("agenda_form"):
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        p_sel = st.selectbox("Paziente Interessato", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        c1, c2, c3 = st.columns(3)
        d_app, o_app = c1.date_input("Data"), c2.text_input("Ora (HH:MM)")
        cat = c3.selectbox("Categoria Evento", ["Uscita", "Visita Medica", "Udienza", "Visita con Parenti"])
        desc = st.text_area("Dettagli dell'appuntamento")
        if st.form_submit_button("INSERISCI IN AGENDA"):
            db_run("INSERT INTO agenda (p_id, data, ora, categoria, evento, stato) VALUES (?,?,?,?,?,?)", (p_id, d_app.strftime("%d/%m/%Y"), o_app, cat, desc, "In programma"), True)
            st.success("Appuntamento Salvato")
    
    st.write("### Elenco Scadenze e Appuntamenti")
    apps = db_run("SELECT a.data, a.ora, a.categoria, p.nome, a.evento FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY a.data ASC")
    if apps:
        h = "<table class='report-table'><thead><tr><th>Data</th><th>Ora</th><th>Paziente</th><th>Categoria</th><th>Dettagli</th></tr></thead><tbody>"
        for d, o, c, n, e in apps:
            cls = "cat-uscita" if c == "Uscita" else "cat-medica" if c == "Visita Medica" else "cat-udienza" if c == "Udienza" else "cat-parenti"
            h += f"<tr><td>{d}</td><td>{o}</td><td>{n}</td><td><span class='cat-badge {cls}'>{c}</span></td><td>{e}</td></tr>"
        st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- 4. GESTIONE SISTEMA ---
elif nav == "⚙️ Gestione Sistema":
    st.header("Anagrafica Pazienti")
    with st.form("add_pax"):
        np = st.text_input("Inserisci Nome e Cognome Nuovo Paziente")
        if st.form_submit_button("SALVA NUOVO PAZIENTE"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    st.write("---")
    pax_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, n in pax_list:
        col_n, col_d = st.columns([5,1])
        col_n.write(f"👤 {n}")
        if col_d.button("Elimina", key=f"delp_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
