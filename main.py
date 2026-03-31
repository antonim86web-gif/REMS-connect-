import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* SIDEBAR BLU */
    [data-testid="stSidebar"] {
        background-color: #1e3a8a !important;
    }
    
    /* FORZA BIANCO ASSOLUTO SU TUTTE LE SCRITTE DEL MENU LATERALE */
    [data-testid="stSidebar"] *, 
    [data-testid="stSidebar"] .stRadio label, 
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] span {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
    }

    /* TASTO LOGOUT ROSSO */
    [data-testid="stSidebar"] button {
        background-color: #dc2626 !important;
        color: white !important;
        font-weight: bold !important;
        border: 2px solid #ffffff !important;
        border-radius: 10px !important;
        height: 3em !important;
        width: 100% !important;
    }
    
    /* TITOLI E TABELLE */
    .main-title { text-align: center; color: #1e3a8a; font-weight: 800; font-size: 2.5rem; margin-bottom: 20px; }
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; margin-top: 10px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 10px; text-align: left; }
    .report-table td { padding: 8px; border-bottom: 1px solid #f1f5f9; color: #1e293b; }
    
    .cat-badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; color: white; }
    .cat-udienza { background-color: #dc2626; } 
    .cat-medica { background-color: #2563eb; }  
    .cat-uscita { background-color: #059669; }  
    .cat-parenti { background-color: #d97706; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ---
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
            st.error("Errore: Lo username o il dato inserito esiste già nel sistema.")
            return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def mostra_report_settoriale(p_id, ruolo_utente):
    st.write("---")
    st.subheader(f"📋 Registro Attività {ruolo_utente}")
    eventi = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? AND ruolo=? ORDER BY id_u DESC LIMIT 10", (p_id, ruolo_utente))
    if eventi:
        h = "<table class='report-table'><thead><tr><th>Data/Ora</th><th>Operatore</th><th>Attività</th></tr></thead><tbody>"
        for d, r, o, nt in eventi:
            h += f"<tr><td>{d}</td><td>{o}</td><td>{nt}</td></tr>"
        st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- LOGICA ACCESSO ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<h1 class='main-title'>REMS CONNECT ELITE PRO</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Login", "📝 Registrazione"])
    with t1:
        with st.form("login"):
            u_in, p_in = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res: 
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
    with t2:
        with st.form("reg"):
            nu, np = st.text_input("Scegli Username"), st.text_input("Scegli Password", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA ACCOUNT"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True)
                st.success("Registrazione completata! Ora puoi fare il login.")
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# SIDEBAR
st.sidebar.markdown(f"### 👤 {u['nome']} {u['cognome']}")
nav = st.sidebar.radio("MENU DI NAVIGAZIONE", ["📊 Monitoraggio Generale", "👥 Modulo Equipe", "📅 Agenda Appuntamenti", "⚙️ Gestione Sistema"])
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
                    h += f"<tr><td>{d}</td><td>{r}</td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- 2. MODULO EQUIPE ---
elif nav == "👥 Modulo Equipe":
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        if u['ruolo'] == "Psichiatra":
            with st.form("psic"):
                f, d = st.text_input("Farmaco"), st.text_input("Dosaggio")
                c1,c2,c3 = st.columns(3); m=c1.checkbox("MAT"); p=c2.checkbox("POM"); n=c3.checkbox("NOT")
                if st.form_submit_button("CONFERMA PRESCRIZIONE"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📝 Prescritto: {f} {d}", "Psichiatra", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "Psichiatra")

        elif u['ruolo'] == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 Somministrazione", "📝 Consegne", "📊 Parametri"])
            with t1:
                ter = db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,))
                for tid, fa, do in ter:
                    with st.expander(f"📌 {fa} ({do})", expanded=True):
                        c_dt, c_btn = st.columns([2, 1])
                        d_s = c_dt.text_input("Data/Ora Effettiva", value=datetime.now().strftime("%d/%m/%Y %H:%M"), key=f"dt_{tid}")
                        if c_btn.button("REGISTRA SOMMINISTRAZIONE", key=f"btn_{tid}"):
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, d_s, f"✔️ SOMMINISTRATO: {fa} ({do})", "Infermiere", firma), True); st.rerun()
            with t2:
                nota = st.text_area("Nota Consegne")
                if st.button("SALVA CONSEGNA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota, "Infermiere", firma), True); st.rerun()
            with t3:
                with st.form("pv"):
                    c1,c2 = st.columns(2); mx=c1.number_input("MAX"); mn=c2.number_input("MIN")
                    if st.form_submit_button("SALVA PARAMETRI"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📊 PA:{mx}/{mn}", "Infermiere", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "Infermiere")

        elif u['ruolo'] == "Educatore":
            tc, te = st.tabs(["💰 Cassa", "📝 Diario"])
            with tc:
                movs = db_run("SELECT data, causale, importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
                st.metric("SALDO ATTUALE", f"€ {saldo:.2f}")
                with st.form("c"):
                    tipo=st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True); imp=st.number_input("Euro", 0.0); cau=st.text_input("Causale")
                    if st.form_submit_button("REGISTRA MOVIMENTO"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), cau, imp, tipo, firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"💰 {tipo}: €{imp} ({cau})", "Educatore", firma), True); st.rerun()
            with te:
                nota = st.text_area("Nota Educativa")
                if st.button("SALVA NOTA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota, "Educatore", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "Educatore")

        elif u['ruolo'] == "OSS":
            m_s = st.selectbox("Attività", ["Igiene", "Pulizia", "Pasti", "Sanificazione", "Controllo"])
            n_o = st.text_area("Note Operatore")
            if st.button("REGISTRA ATTIVITÀ"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"🛠️ {m_s}: {n_o}", "OSS", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "OSS")

# --- 3. AGENDA ---
elif nav == "📅 Agenda Appuntamenti":
    st.markdown("<h2 class='main-title'>Agenda REMS</h2>", unsafe_allow_html=True)
    with st.form("ag"):
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        p_sel = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        c1, c2, c3 = st.columns(3)
        d_app, o_app, cat = c1.date_input("Data"), c2.text_input("Ora (HH:MM)"), c3.selectbox("Tipo", ["Uscita", "Visita Medica", "Udienza", "Parenti"])
        desc = st.text_area("Dettagli")
        if st.form_submit_button("SALVA IN AGENDA"):
            db_run("INSERT INTO agenda (p_id, data, ora, categoria, evento, stato) VALUES (?,?,?,?,?,?)", (p_id, d_app.strftime("%d/%m/%Y"), o_app, cat, desc, "In programma"), True); st.success("Ok")
    
    apps = db_run("SELECT a.data, a.ora, a.categoria, p.nome, a.evento FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY a.data ASC")
    if apps:
        h = "<table class='report-table'><thead><tr><th>Data</th><th>Ora</th><th>Paziente</th><th>Cat</th><th>Dettagli</th></tr></thead><tbody>"
        for d, o, c, n, e in apps:
            cls = "cat-uscita" if c == "Uscita" else "cat-medica" if c == "Visita Medica" else "cat-udienza" if c == "Udienza" else "cat-parenti"
            h += f"<tr><td>{d}</td><td>{o}</td><td>{n}</td><td><span class='cat-badge {cls}'>{c}</span></td><td>{e}</td></tr>"
        st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- 4. GESTIONE ---
elif nav == "⚙️ Gestione Sistema":
    np = st.text_input("Nome e Cognome Nuovo Paziente")
    if st.button("SALVA PAZIENTE"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        c1, c2 = st.columns([5,1])
        c1.write(f"👤 {n}")
        if c2.button("Elimina", key=f"d_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
