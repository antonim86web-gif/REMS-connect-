import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="REMS Connect PRO v16", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; margin-bottom: 20px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 10px; text-align: left; }
    .report-table td { padding: 8px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; }
    .badge { padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; color: white; font-weight: bold; }
    .bg-psichiatra { background: #dc2626; } .bg-infermiere { background: #2563eb; }
    .bg-educatore { background: #059669; } .bg-oss { background: #d97706; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE (v16 - Reset totale per risolvere OperationalError) ---
DB_NAME = "rems_periti_v16.db"

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
    st.title("🏥 REMS CONNECT PRO v16")
    t1, t2 = st.tabs(["🔐 Login", "📝 Registrazione"])
    with t1:
        with st.form("l_f"):
            u, p = st.text_input("User"), st.text_input("Pass", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, hash_pw(p)))
                if res: 
                    st.session_state.u_data = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
    with t2:
        with st.form("r_f"):
            nu, np = st.text_input("User"), st.text_input("Pass", type="password")
            nn, nc, nq = st.text_input("Nome"), st.text_input("Cognome"), st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("OK!")
    st.stop()

# Firma dinamica
usr = st.session_state.u_data
firma = f"{usr['nome']} {usr['cognome']} ({usr['ruolo']})"

st.sidebar.write(f"Operatore: **{firma}**")
nav = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "⚙️ Gestione"])
if st.sidebar.button("LOGOUT"): st.session_state.u_data = None; st.rerun()

# --- MONITORAGGIO ---
if nav == "📊 Monitoraggio":
    st.header("📋 Diario Clinico")
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                h = "<table class='report-table'><tr><th>Data</th><th>Ruolo</th><th>Firma</th><th>Evento</th></tr>"
                for d, r, o, nt in evs:
                    h += f"<tr><td>{d}</td><td><span class='badge bg-{r.lower()}'>{r}</span></td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

# --- EQUIPE (VISUALIZZAZIONE A SETTORI) ---
elif nav == "👥 Equipe":
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_n = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_n][0]

        # 1. PSICHIATRA
        if usr['ruolo'] == "Psichiatra":
            st.subheader("💊 Gestione Terapie")
            with st.form("f_ps"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1,c2,c3 = st.columns(3)
                m, p, n = c1.checkbox("Mattina"), c2.checkbox("Pomeriggio"), c3.checkbox("Notte")
                if st.form_submit_button("SALVA PRESCRIZIONE"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 Prescr: {f} {d}", "Psichiatra", firma), True)
                    st.rerun()
            
            st.markdown("#### 📋 Report Terapie Attive")
            ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            for tid, fa, do, m1, p1, n1 in ter:
                c1, c2 = st.columns([5,1])
                c1.info(f"**{fa} {do}** | Orari: {'M' if m1 else '-'} {'P' if p1 else '-'} {'N' if n1 else '-'}")
                if c2.button("Elimina", key=f"d_{tid}"):
                    db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True); st.rerun()

        # 2. INFERMIERE
        elif usr['ruolo'] == "Infermiere":
            st.subheader("💊 Somministrazione e Parametri")
            for fa, do in db_run("SELECT farmaco, dose FROM terapie WHERE p_id=?", (p_id,)):
                col1, col2, col3 = st.columns([2,1,1])
                col1.write(f"**{fa}** ({do})")
                if col2.button("SOMMINISTRA", key=f"ok_{fa}"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrato: {fa}", "Infermiere", firma), True); st.rerun()
                if col3.button("RIFIUTA", key=f"no_{fa}"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"❌ RIFIUTATO: {fa}", "Infermiere", firma), True); st.rerun()
            
            st.write("---")
            st.subheader("📝 Consegne M/P/N")
            f_turno = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
            t_con = st.text_area("Nota di consegna")
            if st.button("SALVA CONSEGNA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📋 CONSEGNA {f_turno.upper()}: {t_con}", "Infermiere", firma), True); st.rerun()
            
            st.write("---")
            st.subheader("📊 Parametri Vitali")
            with st.form("f_pv"):
                # Rimosso il parametro 'min_value' per evitare blocchi come da screenshot
                c1,c2,c3,c4 = st.columns(4)
                mx = c1.number_input("MAX", value=120); mn = c2.number_input("MIN", value=80)
                fc = c3.number_input("FC", value=70); sp = c4.number_input("SpO2", value=98)
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA:{mx}/{mn} FC:{fc} SpO2:{sp}", "Infermiere", firma), True); st.rerun()

        # 3. EDUCATORE
        elif usr['ruolo'] == "Educatore":
            st.subheader("💰 Gestione Cassa")
            movs = db_run("SELECT data, causale, importo, tipo, op FROM cassa WHERE p_id=?", (p_id,))
            saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
            st.metric("Saldo Attuale", f"€ {saldo:.2f}")
            
            with st.form("f_ed"):
                tp = st.radio("Tipo", ["Entrata", "Uscita"])
                im = st.number_input("Importo Euro", value=0.0)
                ca = st.text_input("Causale")
                if st.form_submit_button("REGISTRA MOVIMENTO"):
                    db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m"), ca, im, tp, firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {tp}: €{im:.2f} ({ca})", "Educatore", firma), True); st.rerun()
            
            # Report economico pulito (senza zeri superflui)
            if movs:
                df = pd.DataFrame(movs, columns=["Data", "Causale", "Importo", "Tipo", "Operatore"])
                df["Importo"] = df["Importo"].apply(lambda x: f"{x:.2f}")
                st.table(df)

        # 4. OSS
        elif usr['ruolo'] == "OSS":
            st.subheader("🛠️ Mansioni e Pulizie")
            m_sc = st.selectbox("Attività", ["Pulizia Camera", "Pulizia Refettorio", "Sale Fumo", "Cortile", "Lavatrice"])
            if st.button("REGISTRA ATTIVITÀ"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🛠️ {m_sc}", "OSS", firma), True); st.rerun()
            
            st.markdown("#### 📋 Report Mansioni Svolte")
            oss_ev = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND ruolo='OSS' ORDER BY id_u DESC LIMIT 10", (p_id,))
            if oss_ev: st.table(pd.DataFrame(oss_ev, columns=["Data", "Mansione", "Firma"]))

# --- GESTIONE ---
elif nav == "⚙️ Gestione":
    st.header("Anagrafica Pazienti")
    n_p = st.text_input("Inserisci Nome e Cognome")
    if st.button("AGGIUNGI"):
        db_run("INSERT INTO pazienti (nome) VALUES (?)", (n_p.upper(),), True); st.rerun()
    
    st.write("---")
    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        c1, c2, c3 = st.columns([3,1,1])
        nn = c1.text_input("Nome", value=n, key=f"e_{pid}")
        if c2.button("💾", key=f"s_{pid}"):
            db_run("UPDATE pazienti SET nome=? WHERE id=?", (nn.upper(), pid), True); st.rerun()
        if c3.button("🗑️", key=f"d_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
