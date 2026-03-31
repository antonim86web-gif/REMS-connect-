import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="REMS Connect PRO v15", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; margin-top: 20px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 10px; text-align: left; }
    .report-table td { padding: 8px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; }
    .badge { padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; color: white; font-weight: bold; }
    .bg-psichiatra { background: #dc2626; } .bg-infermiere { background: #2563eb; }
    .bg-educatore { background: #059669; } .bg-oss { background: #d97706; }
    .stCheckbox { margin-bottom: 0px; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_pro_v15.db"

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

# --- 3. FUNZIONE REPORT INTEGRATA ---
def mostra_report_paziente(p_id, ruolo_filtro=None):
    if ruolo_filtro:
        evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? AND ruolo=? ORDER BY id_u DESC LIMIT 10", (p_id, ruolo_filtro))
    else:
        evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 20", (p_id,))
    
    if evs:
        st.markdown("### 📋 Diario Clinico Recente")
        h = "<table class='report-table'><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Nota</th></tr>"
        for d, r, o, nt in evs:
            h += f"<tr><td>{d}</td><td><span class='badge bg-{r.lower()}'>{r}</span></td><td>{o}</td><td>{nt}</td></tr>"
        st.markdown(h + "</table>", unsafe_allow_html=True)
    else:
        st.info("Nessuna nota presente nel diario per questo paziente.")

# --- 4. GESTIONE SESSIONE ---
if 'user_data' not in st.session_state: st.session_state.user_data = None

if not st.session_state.user_data:
    st.title("🏥 REMS CONNECT - ACCESSO")
    t1, t2 = st.tabs(["🔐 Login", "📝 Registrazione"])
    with t1:
        with st.form("login"):
            u_in = st.text_input("User")
            p_in = st.text_input("Pass", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res: 
                    st.session_state.user_data = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Credenziali non valide.")
    with t2:
        with st.form("reg"):
            nu, np = st.text_input("Username"), st.text_input("Password", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("Registrato!")
    st.stop()

u = st.session_state.user_data
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# Sidebar
st.sidebar.title(f"Benvenuto {u['nome']}")
if st.sidebar.button("LOGOUT"):
    st.session_state.user_data = None
    st.rerun()

# --- 5. CORE APP ---
p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
if not p_lista:
    st.warning("Aggiungi un paziente nella sezione Gestione.")
    if st.button("Vai a Gestione"): st.session_state.menu = "⚙️ Gestione"; st.rerun()
    # Fallback per il primo avvio
    p_nome = st.text_input("Aggiungi il primo paziente")
    if st.button("Salva"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (p_nome.upper(),), True); st.rerun()
    st.stop()

p_sel_nome = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
p_id = [p[0] for p in p_lista if p[1] == p_sel_nome][0]

st.divider()

# --- AREA OPERATIVA PER RUOLO ---
if u['ruolo'] == "Psichiatra":
    st.subheader("💊 Piano Terapeutico (Prescrizione)")
    with st.form("f_ter"):
        f, d = st.text_input("Farmaco"), st.text_input("Dose (es. 1 cp)")
        st.write("Orari Somministrazione:")
        c1, c2, c3 = st.columns(3)
        m = c1.checkbox("Mattina")
        p = c2.checkbox("Pomeriggio")
        n = c3.checkbox("Notte")
        if st.form_submit_button("AGGIUNGI TERAPIA"):
            db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 Nuova Terapia: {f} {d}", "Psichiatra", firma), True)
            st.rerun()
    
    st.write("---")
    mostra_report_paziente(p_id)

elif u['ruolo'] == "Infermiere":
    t_som, t_con, t_par = st.tabs(["💊 Somministrazione", "📝 Consegne", "📊 Parametri"])
    
    with t_som:
        terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
        for tid, fa, do, m1, p1, n1 in terapie:
            with st.container():
                c_f, c_ok, c_no = st.columns([2, 1, 1])
                orari = f"[{'M' if m1 else '-'} | {'P' if p1 else '-'} | {'N' if n1 else '-'}]"
                c_f.write(f"**{fa}** {do}  \n{orari}")
                if c_ok.button("SOMMINISTRA", key=f"ok_{tid}"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrato: {fa}", "Infermiere", firma), True); st.rerun()
                if c_no.button("RIFIUTA", key=f"no_{tid}"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"❌ RIFIUTATO: {fa}", "Infermiere", firma), True); st.rerun()

    with t_con:
        turno = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
        testo_c = st.text_area("Testo della Consegna")
        if st.button("SALVA CONSEGNA"):
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📋 CONSEGNA {turno.upper()}: {testo_c}", "Infermiere", firma), True); st.rerun()

    with t_par:
        with st.form("pv"):
            c1,c2,c3,c4 = st.columns(4)
            mx = c1.number_input("MAX", 120); mn = c2.number_input("MIN", 80)
            fc = c3.number_input("FC", 72); sp = c4.number_input("SpO2", 98)
            if st.form_submit_button("REGISTRA PARAMETRI"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA:{mx}/{mn} FC:{fc} SpO2:{sp}%", "Infermiere", firma), True); st.rerun()
    
    mostra_report_paziente(p_id)

elif u['ruolo'] == "Educatore":
    movs = db_run("SELECT data, causale, importo, tipo FROM cassa WHERE p_id=?", (p_id,))
    saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
    st.metric("Saldo Cassa", f"€ {saldo:.2f}")
    
    with st.expander("💸 Registra Movimento", expanded=True):
        with st.form("cassa_form"):
            tp = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
            im = st.number_input("Importo Euro", 0.0, step=0.5)
            ca = st.text_input("Causale")
            if st.form_submit_button("SALVA MOVIMENTO"):
                db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%y"), ca, im, tp, firma), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {tp}: €{im:.2f} ({ca})", "Educatore", firma), True); st.rerun()
    
    mostra_report_paziente(p_id)

elif u['ruolo'] == "OSS":
    man = st.selectbox("Mansionario", ["Pulizia Camera", "Igiene Personale", "Pasto", "Sale Fumo", "Cortile"])
    nota_o = st.text_area("Note aggiuntive")
    if st.button("REGISTRA ATTIVITÀ"):
        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🛠️ {man}: {nota_o}", "OSS", firma), True); st.rerun()
    
    mostra_report_paziente(p_id)

# --- GESTIONE ANAGRAFICA (Sempre visibile in fondo o via Sidebar) ---
with st.sidebar.expander("⚙️ Gestione Pazienti"):
    nuovo_p = st.text_input("Nuovo Paziente")
    if st.button("Aggiungi"):
        db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo_p.upper(),), True); st.rerun()
