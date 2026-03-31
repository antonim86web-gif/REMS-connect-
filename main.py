import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12.5", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    .sidebar-title { 
        color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; 
        text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; 
    }
    .section-banner { 
        background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; 
        margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); 
    }
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; margin-top: 20px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 12px; text-align: left; border: 1px solid #cbd5e1; font-weight: 700; }
    .report-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; color: #1e293b; font-size: 0.9rem; border: 1px solid #cbd5e1; }
    
    /* GRAFICA TERAPIA INFERMIERE */
    .therapy-container {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 15px; margin-bottom: 15px; border-left: 8px solid #1e3a8a;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .turn-header { font-weight: 800; font-size: 0.9rem; text-transform: uppercase; margin-bottom: 10px; }
    .mat-style { color: #d97706; } .pom-style { color: #2563eb; } .not-style { color: #4338ca; }
    .farmaco-title { font-size: 1.2rem; font-weight: 900; color: #1e293b; margin: 0; }
    .dose-subtitle { font-size: 1rem; color: #64748b; font-weight: 600; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- MOTORE DATABASE ---
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
        except Exception as e:
            st.error(f"Errore: {e}")
            return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>REMS CONNECT LOGIN</h2></div>", unsafe_allow_html=True)
    with st.form("login"):
        u_in, p_in = st.text_input("User"), st.text_input("Password", type="password")
        if st.form_submit_button("LOGIN"):
            res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
            if res:
                st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                st.rerun()
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR (Sincronizzata con Screenshot) ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.write(f"🟢 **{u['nome'].upper()}**")
st.sidebar.write(f"*{u['ruolo']}*")

nav = st.sidebar.radio("MODULI OPERATIVI", ["📊 Monitoraggio", "💊 Terapie", "📝 Diario Clinico", "💰 Cassa Pazienti", "📅 Agenda Legale", "⚙️ Sistema"])

if st.sidebar.button("LOGOUT SICURO"):
    st.session_state.user_session = None
    st.rerun()

# --- LOGICA MODULI ---

if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>MONITORAGGIO GENERALE</h2></div>", unsafe_allow_html=True)
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in pazienti:
        with st.expander(f"📁 CARTELLA: {nome}"):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                df = pd.DataFrame(evs, columns=["Data", "Ruolo", "Operatore", "Nota"])
                st.table(df)

elif nav == "💊 Terapie":
    st.markdown("<div class='section-banner'><h2>GESTIONE TERAPIE</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        # SEZIONE PSICHIATRA
        if u['ruolo'] == "Psichiatra":
            t1, t2 = st.tabs(["➕ Nuova Prescrizione", "❌ Sospensione"])
            with t1:
                with st.form("form_prescrizione"):
                    f = st.text_input("Farmaco")
                    d = st.text_input("Dosaggio")
                    c1, c2, c3 = st.columns(3)
                    m = c1.checkbox("MAT")
                    p = c2.checkbox("POM")
                    n = c3.checkbox("NOT")
                    # RISOLTO: Aggiunto pulsante submit mancante nello screenshot
                    if st.form_submit_button("REGISTRA PRESCRIZIONE"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"Prescritto: {f}", u['ruolo'], firma), True)
                        st.success("Registrato!")
            with t2:
                farmaci = db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,))
                for fid, fn, fs in farmaci:
                    if st.button(f"Sospendi {fn}", key=f"s_{fid}"):
                        db_run("DELETE FROM terapie WHERE id_u=?", (fid,), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"Sospeso: {fn}", u['ruolo'], firma), True)
                        st.rerun()

        # SEZIONE INFERMIERE (RISOLTO IL PROBLEMA NULL)
        elif u['ruolo'] == "Infermiere":
            st.write("### 🏥 Dashboard Somministrazione Farmaci")
            oggi = datetime.now().strftime("%d/%m/%Y")
            terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            
            c_mat, c_pom, c_not = st.columns(3)
            
            def render_card(tid, f, d, turno, css, icon):
                check = db_run("SELECT id_u FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%SOMM ({turno}): {f}%", f"{oggi}%"))
                if not check:
                    st.markdown(f"<div class='therapy-container'><div class='turn-header {css}'>{icon} {turno}</div><div class='farmaco-title'>{f}</div><div class='dose-subtitle'>{d}</div></div>", unsafe_allow_html=True)
                    col_a, col_b = st.columns(2)
                    if col_a.button("✅", key=f"ok_{tid}_{turno}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({turno}): {f}", u['ruolo'], firma), True)
                        st.rerun()
                    if col_b.button("❌", key=f"no_{tid}_{turno}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"⚠️ RIFIUTO ({turno}): {f}", u['ruolo'], firma), True)
                        st.rerun()

            with c_mat:
                st.write("☀️ **MATTINA**")
                for t in terapie:
                    if t[3]: render_card(t[0], t[1], t[2], "MAT", "mat-style", "☀️")
            with c_pom:
                st.write("🌤️ **POMERIGGIO**")
                for t in terapie:
                    if t[4]: render_card(t[0], t[1], t[2], "POM", "pom-style", "🌤️")
            with c_not:
                st.write("🌙 **NOTTE**")
                for t in terapie:
                    if t[5]: render_card(t[0], t[1], t[2], "NOT", "not-style", "🌙")

elif nav == "📝 Diario Clinico":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    p_sel = st.selectbox("Paziente", [p[1] for p in p_lista])
    p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
    
    nota = st.text_area("Inserisci nota clinica")
    if st.button("SALVA NOTA"):
        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota, u['ruolo'], firma), True)
        st.success("Salvato!")

elif nav == "⚙️ Sistema":
    st.markdown("<div class='section-banner'><h2>GESTIONE ANAGRAFICA</h2></div>", unsafe_allow_html=True)
    with st.form("nuovo_paz"):
        nome_p = st.text_input("Nome e Cognome Paziente")
        if st.form_submit_button("REGISTRA PAZIENTE"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (nome_p.upper(),), True)
            st.success("Paziente aggiunto!")
