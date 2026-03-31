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

# --- GESTIONE DATABASE (v12 per reset totale errori) ---
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

# --- SISTEMA DI ACCESSO ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<h1 class='main-title'>REMS CONNECT ELITE PRO</h1>", unsafe_allow_html=True)
    tab_log, tab_reg = st.tabs(["🔐 Login", "📝 Registrazione Operatore"])
    
    with tab_log:
        with st.form("form_login"):
            u_in = st.text_input("Username")
            p_in = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res: 
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Accesso negato: credenziali errate.")
    
    with tab_reg:
        with st.form("form_reg"):
            nu = st.text_input("Nuovo Username")
            np = st.text_input("Nuova Password", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Qualifica Professionale", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA ACCOUNT"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True)
                st.success("Registrazione completata! Ora puoi accedere.")
    st.stop()

# --- DATI SESSIONE E FIRMA ---
u = st.session_state.user_session
firma_operatore = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

st.sidebar.title("MENU")
nav = st.sidebar.radio("Vai a:", ["📊 Monitoraggio Generale", "👥 Modulo Equipe", "⚙️ Gestione Sistema"])
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()

# --- MONITORAGGIO GENERALE ---
if nav == "📊 Monitoraggio Generale":
    st.markdown("<h2 class='main-title'>Diario Clinico Integrato</h2>", unsafe_allow_html=True)
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            # Report Cronologico
            eventi = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if eventi:
                h = "<table class='report-table'><thead><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Evento</th></tr></thead><tbody>"
                for d, r, o, nt in eventi:
                    h += f"<tr><td>{d}</td><td><span class='badge bg-{r.lower()}'>{r}</span></td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</tbody></table>", unsafe_allow_html=True)
            else:
                st.info("Nessun evento registrato per questo paziente.")

# --- MODULO EQUIPE ---
elif nav == "👥 Modulo Equipe":
    st.write(f"Operatore loggato: **{firma_operatore}**")
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona il paziente su cui operare", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        # SEZIONE PSICHIATRA
        if u['ruolo'] == "Psichiatra":
            st.subheader("💊 Gestione Terapie")
            with st.form("form_terapia"):
                f = st.text_input("Farmaco")
                d = st.text_input("Dosaggio")
                st.write("Fasce Orarie di Somministrazione:")
                c1, c2, c3 = st.columns(3)
                m_check = c1.checkbox("Mattina")
                p_check = c2.checkbox("Pomeriggio")
                n_check = c3.checkbox("Notte")
                if st.form_submit_button("CONFERMA PRESCRIZIONE"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", 
                           (p_id, f, d, int(m_check), int(p_check), int(n_check), firma_operatore), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                           (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 Nuova Terapia: {f} {d}", u['ruolo'], firma_operatore), True)
                    st.rerun()
            
            st.markdown("#### 📋 Report Terapie Attuali")
            ter_attive = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            if ter_attive:
                for tid, fa, do, m1, p1, n1 in ter_attive:
                    c_info, c_del = st.columns([4,1])
                    c_info.warning(f"**{fa} {do}** | Orari: {'MAT ' if m1 else ''}{'POM ' if p1 else ''}{'NOTTE' if n1 else ''}")
                    if c_del.button("Elimina", key=f"t_del_{tid}"):
                        db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                               (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🗑️ Terapia Rimossa: {fa}", u['ruolo'], firma_operatore), True)
                        st.rerun()

        # SEZIONE INFERMIERE
        elif u['ruolo'] == "Infermiere":
            tab_som, tab_par = st.tabs(["💊 Somministrazione", "📊 Parametri Vitali"])
            with tab_som:
                st.subheader("Farmaci da Somministrare (M-P-N)")
                ter_disponibili = db_run("SELECT farmaco, dose FROM terapie WHERE p_id=?", (p_id,))
                for fa, do in ter_disponibili:
                    if st.button(f"Somministrato: {fa} ({do})", key=f"som_{fa}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                               (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrazione: {fa}", u['ruolo'], firma_operatore), True)
                        st.success(f"Somministrazione di {fa} registrata.")
                
                st.markdown("#### 📋 Report Ultime 5 Somministrazioni")
                cron_som = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND nota LIKE '✔️ %' ORDER BY id_u DESC LIMIT 5", (p_id,))
                if cron_som: st.table(pd.DataFrame(cron_som, columns=["Data", "Evento", "Firma"]))

            with tab_par:
                with st.form("form_pv"):
                    c1, c2, c3, c4 = st.columns(4)
                    mx = c1.number_input("Pressione MAX", 120); mn = c2.number_input("Pressione MIN", 80)
                    fc = c3.number_input("Freq. Cardiaca", 72); sp = c4.number_input("SpO2 %", 98)
                    if st.form_submit_button("REGISTRA PARAMETRI"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                               (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA:{mx}/{mn} FC:{fc} SpO2:{sp}", u['ruolo'], firma_operatore), True)
                        st.rerun()
                st.markdown("#### 📋 Storico Parametri")
                cron_par = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND nota LIKE '📊 %' ORDER BY id_u DESC LIMIT 5", (p_id,))
                if cron_par: st.table(pd.DataFrame(cron_par, columns=["Data", "Valori", "Firma"]))

        # SEZIONE EDUCATORE
        elif u['ruolo'] == "Educatore":
            tab_cash, tab_edu = st.tabs(["💰 Gestione Cassa", "📝 Diario Educativo"])
            with tab_cash:
                movimenti = db_run("SELECT data, causale, importo, tipo, op FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movimenti])
                st.metric("SALDO PAZIENTE", f"€ {saldo:.2f}")
                with st.form("form_cassa"):
                    t_mov = st.radio("Operazione", ["Entrata", "Uscita"])
                    i_mov = st.number_input("Importo Euro", 0.0)
                    c_mov = st.text_input("Causale Movimento")
                    if st.form_submit_button("REGISTRA IN CASSA"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", 
                               (p_id, date.today().strftime("%d/%m"), c_mov, i_mov, t_mov, firma_operatore), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                               (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {t_mov}: €{i_mov} ({c_mov})", u['ruolo'], firma_operatore), True)
                        st.rerun()
                st.markdown("#### 📋 Report Movimenti Economici")
                if movimenti: st.table(pd.DataFrame(movimenti, columns=["Data", "Causale", "Importo", "Tipo", "Operatore"]))

            with tab_edu:
                n_edu = st.text_area("Nota di servizio / Attività educativa")
                if st.button("SALVA NOTA EDUCATIVA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                           (p_id, datetime.now().strftime("%d/%m %H:%M"), n_edu, u['ruolo'], firma_operatore), True)
                    st.rerun()

        # SEZIONE OSS
        elif u['ruolo'] == "OSS":
            st.subheader("Mansioni e Pulizie")
            m_scelta = st.selectbox("Seleziona Mansione Effettuata", ["Pulizia Camera", "Pulizia Refettorio", "Sale Fumo", "Cortile", "Lavatrice"])
            nota_oss = st.text_area("Eventuali osservazioni")
            if st.button("REGISTRA MANSIONE"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                       (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🛠️ {m_scelta}: {nota_oss}", u['ruolo'], firma_operatore), True)
                st.rerun()
            
            st.markdown("#### 📋 Report Mansioni OSS")
            cron_oss = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND ruolo='OSS' ORDER BY id_u DESC LIMIT 10", (p_id,))
            if cron_oss: st.table(pd.DataFrame(cron_oss, columns=["Data", "Mansione", "Firma"]))

# --- GESTIONE SISTEMA ---
elif nav == "⚙️ Gestione Sistema":
    st.header("Anagrafica Pazienti")
    with st.expander("➕ Aggiungi Nuovo Paziente"):
        nuovo_p = st.text_input("Inserisci Nome e Cognome")
        if st.button("SALVA IN ANAGRAFICA"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo_p.upper(),), True)
            st.rerun()
    
    st.write("---")
    st.subheader("Modifica o Elimina Pazienti")
    elenco_p = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, n in elenco_p:
        with st.container():
            c1, c2, c3 = st.columns([3,1,1])
            edit_nome = c1.text_input("Paziente", value=n, key=f"p_{pid}")
            if c2.button("💾 Salva", key=f"s_{pid}"):
                db_run("UPDATE pazienti SET nome=? WHERE id=?", (edit_nome.upper(), pid), True); st.rerun()
            if c3.button("🗑️ Elimina", key=f"d_{pid}"):
                db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
