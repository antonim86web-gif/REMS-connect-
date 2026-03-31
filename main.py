import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    .main-title { text-align: center; color: #1e3a8a; font-weight: 800; font-size: 2.5rem; margin-bottom: 20px; }
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; margin-top: 10px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 10px; text-align: left; font-size: 0.8rem; }
    .report-table td { padding: 8px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; }
    .badge { padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; color: white; font-weight: bold; }
    .bg-psichiatra { background: #dc2626; } .bg-infermiere { background: #2563eb; }
    .bg-educatore { background: #059669; } .bg-oss { background: #d97706; }
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
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def mostra_report_settoriale(p_id, ruolo_utente):
    st.write("---")
    st.subheader(f"📋 Registro Attività {ruolo_utente}")
    eventi = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? AND ruolo=? ORDER BY id_u DESC LIMIT 10", (p_id, ruolo_utente))
    if eventi:
        h = "<table class='report-table'><thead><tr><th>Data</th><th>Operatore</th><th>Attività / Nota</th></tr></thead><tbody>"
        for d, r, o, nt in eventi:
            h += f"<tr><td>{d}</td><td>{o}</td><td>{nt}</td></tr>"
        st.markdown(h + "</tbody></table>", unsafe_allow_html=True)
    else:
        st.info(f"Nessun evento registrato per {ruolo_utente}.")

# --- LOGICA ACCESSO ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<h1 class='main-title'>REMS CONNECT ELITE PRO</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Login", "📝 Registrazione"])
    with t1:
        with st.form("login"):
            u_in = st.text_input("User")
            p_in = st.text_input("Pass", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res: 
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Credenziali errate")
    with t2:
        with st.form("reg"):
            nu, np = st.text_input("User"), st.text_input("Pass", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("OK!")
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# Sidebar
nav = st.sidebar.radio("Vai a:", ["📊 Monitoraggio Generale", "👥 Modulo Equipe", "⚙️ Gestione Sistema"])
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()

# --- 1. MONITORAGGIO GENERALE ---
if nav == "📊 Monitoraggio Generale":
    st.markdown("<h2 class='main-title'>Diario Integrato</h2>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}"):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                h = "<table class='report-table'><thead><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Evento</th></tr></thead><tbody>"
                for d, r, o, nt in evs:
                    h += f"<tr><td>{d}</td><td><span class='badge bg-{r.lower()}'>{r}</span></td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- 2. MODULO EQUIPE ---
elif nav == "👥 Modulo Equipe":
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        # SEZIONE PSICHIATRA
        if u['ruolo'] == "Psichiatra":
            with st.form("f_ter"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1,c2,c3 = st.columns(3); m=c1.checkbox("MAT"); p=c2.checkbox("POM"); n=c3.checkbox("NOT")
                if st.form_submit_button("CONFERMA PRESCRIZIONE"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 Prescritta: {f} {d}", "Psichiatra", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "Psichiatra")

        # SEZIONE INFERMIERE
        elif u['ruolo'] == "Infermiere":
            t_som, t_con, t_par = st.tabs(["💊 Somministrazione", "📝 Consegne", "📊 Parametri"])
            with t_som:
                ter = db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,))
                for tid, fa, do in ter:
                    with st.container():
                        c_f, c_ass, c_rif, c_btn = st.columns([2, 1, 1, 1])
                        c_f.write(f"**{fa}** ({do})")
                        ass = c_ass.checkbox("Assume", key=f"ass_{tid}")
                        rif = c_rif.checkbox("Rifiuta", key=f"rif_{tid}")
                        if c_btn.button("Salva", key=f"btn_{tid}"):
                            if ass and not rif:
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ ASSUNTO: {fa}", "Infermiere", firma), True); st.rerun()
                            elif rif and not ass:
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"❌ RIFIUTATO: {fa}", "Infermiere", firma), True); st.rerun()
                            else: st.warning("Seleziona una sola opzione.")
            with t_con:
                t_consegna = st.text_area("Testo della Consegna")
                if st.button("SALVA CONSEGNA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📋 CONSEGNA: {t_consegna}", "Infermiere", firma), True); st.rerun()
            with t_par:
                with st.form("f_pv"):
                    c1,c2,c3,c4 = st.columns(4); mx=c1.number_input("MAX",120); mn=c2.number_input("MIN",80); fc=c3.number_input("FC",72); sp=c4.number_input("SpO2",98)
                    if st.form_submit_button("REGISTRA PARAMETRI"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA:{mx}/{mn} FC:{fc} SpO2:{sp}", "Infermiere", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "Infermiere")

        # SEZIONE EDUCATORE
        elif u['ruolo'] == "Educatore":
            t_cash, t_edu = st.tabs(["💰 Cassa", "📝 Diario"])
            with t_cash:
                movs = db_run("SELECT data, causale, importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
                st.metric("SALDO", f"€ {saldo:.2f}")
                with st.form("f_cash"):
                    tipo = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True); imp = st.number_input("Euro", 0.0); caus = st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m"), caus, imp, tipo, firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {tipo}: €{imp} ({caus})", "Educatore", firma), True); st.rerun()
            with t_edu:
                nota_e = st.text_area("Nota Educativa")
                if st.button("SALVA NOTA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), nota_e, "Educatore", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "Educatore")

        # SEZIONE OSS (RIPRISTINATA)
        elif u['ruolo'] == "OSS":
            st.subheader("Gestione Mansioni")
            m_scelta = st.selectbox("Seleziona Mansione", ["Pulizia Camera", "Igiene Personale", "Pasto", "Sale Fumo", "Cortile", "Lavatrice", "Sanificazione"])
            nota_oss = st.text_area("Note e Osservazioni")
            if st.button("REGISTRA ATTIVITÀ OSS"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🛠️ {m_scelta}: {nota_oss}", "OSS", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "OSS")

# --- 3. GESTIONE SISTEMA ---
elif nav == "⚙️ Gestione Sistema":
    np = st.text_input("Aggiungi Paziente")
    if st.button("SALVA"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
