import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect PRO v17", layout="wide", page_icon="🏥")

# --- STILE SETTORI ---
st.markdown("""
<style>
    .sector { padding: 15px; border-radius: 10px; border: 2px solid #e2e8f0; margin-bottom: 20px; background-color: #ffffff; }
    .title-psichiatra { color: #dc2626; border-bottom: 2px solid #dc2626; }
    .title-infermiere { color: #2563eb; border-bottom: 2px solid #2563eb; }
    .title-educatore { color: #059669; border-bottom: 2px solid #059669; }
    .title-oss { color: #d97706; border-bottom: 2px solid #d97706; }
    .report-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; margin-top: 10px; }
    .report-table th { background-color: #f1f5f9; padding: 5px; text-align: left; border-bottom: 1px solid #cbd5e1; }
    .report-table td { padding: 5px; border-bottom: 1px dotted #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE (v17 - Reset finale per evitare ogni OperationalError) ---
DB_NAME = "rems_final_v17.db"

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

# --- ACCESSO ---
if 'u_data' not in st.session_state: st.session_state.u_data = None

if not st.session_state.u_data:
    st.title("🏥 REMS CONNECT - ACCESSO")
    c1, c2 = st.columns(2)
    with c1:
        with st.form("login"):
            u, p = st.text_input("User"), st.text_input("Pass", type="password")
            if st.form_submit_button("LOGIN"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, hash_pw(p)))
                if res: st.session_state.u_data = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}; st.rerun()
    with c2:
        with st.form("reg"):
            nu, np = st.text_input("Nuovo User"), st.text_input("Nuova Pass", type="password")
            nn, nc, nq = st.text_input("Nome"), st.text_input("Cognome"), st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("Registrato!")
    st.stop()

# --- PAGINA PRINCIPALE ---
usr = st.session_state.u_data
firma = f"{usr['nome']} {usr['cognome']} ({usr['ruolo']})"

st.title(f"🏥 Gestione Paziente - {firma}")
if st.sidebar.button("LOGOUT"): st.session_state.u_data = None; st.rerun()

p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
if not p_lista:
    st.warning("Nessun paziente in anagrafica.")
    with st.expander("Aggiungi primo paziente"):
        np = st.text_input("Nome Cognome")
        if st.button("SALVA"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    st.stop()

p_sel = st.selectbox("SELEZIONA PAZIENTE", [p[1] for p in p_lista])
p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

st.divider()

# --- LAYOUT A SETTORI (DASHBOARD) ---
col_left, col_right = st.columns(2)

# 1. SETTORE PSICHIATRA
with col_left:
    st.markdown('<div class="sector"><h3 class="title-psichiatra">🔴 SETTORE PSICHIATRA</h3>', unsafe_allow_html=True)
    if usr['ruolo'] == "Psichiatra":
        with st.form("f_psi", clear_on_submit=True):
            f, d = st.text_input("Farmaco"), st.text_input("Dose")
            c1,c2,c3 = st.columns(3); m, p, n = c1.checkbox("M"), c2.checkbox("P"), c3.checkbox("N")
            if st.form_submit_button("SALVA TERAPIA"):
                db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 Prescr: {f} {d}", "Psichiatra", firma), True); st.rerun()
    
    st.write("**Terapie Attive:**")
    for tid, fa, do, m1, p1, n1 in db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,)):
        st.caption(f"💊 {fa} {do} ({'M' if m1 else '-'}|{'P' if p1 else '-'}|{'N' if n1 else '-'})")
        if usr['ruolo'] == "Psichiatra" and st.button(f"Elimina {tid}", key=f"del_{tid}"):
            db_run("DELETE FROM terapie WHERE id_u=?", (tid, ), True); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# 2. SETTORE INFERMIERE
with col_right:
    st.markdown('<div class="sector"><h3 class="title-infermiere">🔵 SETTORE INFERMIERE</h3>', unsafe_allow_html=True)
    if usr['ruolo'] == "Infermiere":
        # Somministrazione rapida
        st.write("**Somministrazione:**")
        for tid, fa, do in db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,)):
            c_ok, c_no = st.columns(2)
            if c_ok.button(f"✅ {fa}", key=f"ok_{tid}"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrato: {fa}", "Infermiere", firma), True); st.success(f"{fa} OK")
            if c_no.button(f"❌ {fa}", key=f"no_{tid}"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"❌ RIFIUTATO: {fa}", "Infermiere", firma), True); st.warning(f"{fa} Rifiutato")
        
        # Consegne e Parametri
        st.write("**Parametri e Consegne:**")
        with st.expander("Apri Inserimento"):
            turno = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
            cons = st.text_area("Nota Consegna")
            mx = st.number_input("Pressione MAX", value=120)
            if st.button("SALVA DATI INFERMIERISTICI"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📋 {turno}: {cons} | PA MAX: {mx}", "Infermiere", firma), True); st.rerun()

    # Report Infermiere
    inf_ev = db_run("SELECT data, nota FROM eventi WHERE id=? AND ruolo='Infermiere' ORDER BY id_u DESC LIMIT 3", (p_id,))
    for d, nt in inf_ev: st.caption(f"🕒 {d}: {nt}")
    st.markdown('</div>', unsafe_allow_html=True)

col_left2, col_right2 = st.columns(2)

# 3. SETTORE EDUCATORI
with col_left2:
    st.markdown('<div class="sector"><h3 class="title-educatore">🟢 SETTORE EDUCATORI</h3>', unsafe_allow_html=True)
    movs = db_run("SELECT data, causale, importo, tipo FROM cassa WHERE p_id=?", (p_id,))
    saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
    st.write(f"**Saldo: € {saldo:.2f}**")
    
    if usr['ruolo'] == "Educatore":
        with st.form("f_edu"):
            tp = st.radio("Cassa", ["Entrata", "Uscita"], horizontal=True)
            im = st.number_input("Euro", value=0.0); ca = st.text_input("Causale")
            if st.form_submit_button("REGISTRA MOVIMENTO"):
                db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m"), ca, im, tp, firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {tp}: €{im:.2f} ({ca})", "Educatore", firma), True); st.rerun()
    
    # Report Cassa
    for d, c, i, t in movs[-3:]: st.caption(f"💰 {d}: {t} €{i:.2f} ({c})")
    st.markdown('</div>', unsafe_allow_html=True)

# 4. SETTORE OSS
with col_right2:
    st.markdown('<div class="sector"><h3 class="title-oss">🟠 SETTORE OSS</h3>', unsafe_allow_html=True)
    if usr['ruolo'] == "OSS":
        mans = st.selectbox("Mansione", ["Pulizia Camera", "Pulizia Refettorio", "Sale Fumo", "Cortile", "Lavatrice"])
        if st.button("REGISTRA MANSIONE"):
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🛠️ {mans}", "OSS", firma), True); st.rerun()
    
    # Report OSS
    oss_ev = db_run("SELECT data, nota FROM eventi WHERE id=? AND ruolo='OSS' ORDER BY id_u DESC LIMIT 5", (p_id,))
    for d, nt in oss_ev: st.caption(f"🕒 {d}: {nt}")
    st.markdown('</div>', unsafe_allow_html=True)

# --- MONITORAGGIO GENERALE IN FONDO ---
st.divider()
st.subheader("📋 DIARIO CLINICO STORICO")
ev_tutti = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (p_id,))
if ev_tutti:
    df_storico = pd.DataFrame(ev_tutti, columns=["Data", "Ruolo", "Operatore", "Nota"])
    st.table(df_storico)
