import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v12.5 ---
st.set_page_config(page_title="REMS Connect ELITE PRO", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; border-bottom: 2px solid #ffffff33; padding: 10px 0; }
    .sidebar-footer { position: fixed; bottom: 10px; left: 10px; color: #ffffff99 !important; font-size: 0.75rem !important; z-index: 100; }
    
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 20px; border-radius: 12px; margin-bottom: 25px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
    .section-banner h2 { color: white !important; margin: 0; text-transform: uppercase; font-weight: 800; }

    /* TABELLE DINAMICHE */
    .dynamic-table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .dynamic-table th { background-color: #1e293b; color: white !important; padding: 12px; text-align: left; font-size: 0.9rem; }
    .dynamic-table td { padding: 12px; border-bottom: 1px solid #e2e8f0; color: #1e293b; font-size: 0.85rem; vertical-align: middle; }
    .dynamic-table tr:hover { background-color: #f8fafc; }
    
    /* BADGE TURNO */
    .turno-badge { padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 0.75rem; text-transform: uppercase; }
    .bg-mat { background-color: #fef3c7; color: #92400e; }
    .bg-pom { background-color: #dbeafe; color: #1e40af; }
    .bg-not { background-color: #e0e7ff; color: #3730a3; }
</style>
""", unsafe_allow_html=True)

# --- ENGINE DATABASE ---
DB_NAME = "rems_pro_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, stato TEXT DEFAULT 'ATTIVO', id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, categoria TEXT, evento TEXT)")
        try:
            if query: cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore: {e}")
            return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- AUTENTICAZIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>REMS CONNECT ELITE PRO</h2><p>AntonioWebMaster Digital Architecture</p></div>", unsafe_allow_html=True)
    with st.form("login"):
        u_in, p_in = st.text_input("Username"), st.text_input("Password", type="password")
        if st.form_submit_button("ACCEDI"):
            res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
            if res:
                st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                st.rerun()
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
nav = st.sidebar.radio("MODULI", ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda", "⚙️ Sistema"])
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()
st.sidebar.markdown(f"<div class='sidebar-footer'>Created by: <b>AntonioWebMaster</b></div>", unsafe_allow_html=True)

# --- 1. MONITORAGGIO ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO</h2></div>", unsafe_allow_html=True)
    pax = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in pax:
        with st.expander(f"📁 CARTELLA: {nome}"):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 20", (pid,))
            if evs:
                h = "<table class='dynamic-table'><thead><tr><th>Data</th><th>Qualifica</th><th>Operatore</th><th>Nota</th></tr></thead><tbody>"
                for d, r, o, nt in evs: h += f"<tr><td>{d}</td><td>{r}</td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- 2. MODULO EQUIPE ---
elif nav == "👥 Modulo Equipe":
    if u['ruolo'] == "Infermiere":
        st.markdown("<div class='section-banner'><h2>TABELLA SOMMINISTRAZIONE DINAMICA</h2><p>Gestione Turno Corrente</p></div>", unsafe_allow_html=True)
        
        # Filtro Turno Dinamico
        turno_scelto = st.radio("Seleziona Turno Operativo:", ["Mattina (MAT)", "Pomeriggio (POM)", "Notte (NOT)"], horizontal=True)
        mappa_turni = {"Mattina (MAT)": (3, "MAT"), "Pomeriggio (POM)": (4, "POM"), "Notte (NOT)": (5, "NOT")}
        idx_db, label_turno = mappa_turni[turno_scelto]

        # Estrazione Dati Incrociati (Paziente + Terapia)
        query_terapie = f"SELECT p.nome, t.farmaco, t.dose, t.id_u, t.p_id FROM terapie t JOIN pazienti p ON t.p_id = p.id WHERE t.{label_turno.lower()} = 1 AND t.stato='ATTIVO' ORDER BY p.nome"
        dati_terapia = db_run(query_terapie)

        if dati_terapia:
            st.markdown(f"#### 💊 Farmaci da somministrare nel turno: **{label_turno}**")
            
            # Intestazione Tabella
            cols = st.columns([3, 3, 2, 2, 2])
            cols[0].write("**Paziente**")
            cols[1].write("**Farmaco**")
            cols[2].write("**Dosaggio**")
            cols[3].write("**Esito**")
            cols[4].write("**Nota/Rifiuto**")
            st.write("---")

            for nome_p, farmaco, dose, tid, pid in dati_terapia:
                r_col = st.columns([3, 3, 2, 2, 2])
                r_col[0].markdown(f"**{nome_p}**")
                r_col[1].write(farmaco)
                r_col[2].write(dose)
                
                # Azioni Dinamiche
                if r_col[3].button("✅ Firma", key=f"ok_{tid}"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({label_turno}): {farmaco}", "Infermiere", firma), True); st.rerun()
                
                nota_rif = r_col[4].text_input("Nota...", key=f"not_{tid}", label_visibility="collapsed")
                if r_col[3].button("❌ Rifiuto", key=f"no_{tid}"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, datetime.now().strftime("%d/%m/%Y %H:%M"), f"⚠️ RIFIUTO ({label_turno}): {farmaco} - {nota_rif}", "Infermiere", firma), True); st.rerun()
        else:
            st.success(f"Tutte le somministrazioni per il turno {label_turno} sono state completate o non previste.")

    else:
        # Altri ruoli mantengono la logica standard
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_lista:
            p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
            p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

            if u['ruolo'] == "Psichiatra":
                with st.form("f_ps"):
                    st.subheader("Prescrizione Medica")
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3); m=c1.checkbox("MAT"); p=c2.checkbox("POM"); n=c3.checkbox("NOT")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True); st.rerun()

            elif u['ruolo'] == "Educatore":
                nota = st.text_area("Diario Educativo")
                if st.button("SALVA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota, "Educatore", firma), True); st.rerun()

# --- 3. AGENDA ---
elif nav == "📅 Agenda":
    st.markdown("<div class='section-banner'><h2>AGENDA REMS</h2></div>", unsafe_allow_html=True)
    with st.form("ag"):
        p_sel = st.selectbox("Paziente", [p[1] for p in db_run("SELECT id, nome FROM pazienti")])
        pid = [p[0] for p in db_run("SELECT id, nome FROM pazienti") if p[1] == p_sel][0]
        c1, c2 = st.columns(2); d_ag = c1.date_input("Data"); o_ag = c2.text_input("Ora"); cat = st.selectbox("Tipo", ["Udienza", "Visita", "Permesso"]); desc = st.text_area("Note")
        if st.form_submit_button("AGGIUNGI"):
            db_run("INSERT INTO agenda (p_id, data, ora, categoria, evento) VALUES (?,?,?,?,?)", (pid, d_ag.strftime("%d/%m/%Y"), o_ag, cat, desc), True); st.rerun()

# --- 4. SISTEMA ---
elif nav == "⚙️ Sistema":
    st.markdown("### GESTIONE PAZIENTI")
    np = st.text_input("Nome e Cognome")
    if st.button("REGISTRA"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
