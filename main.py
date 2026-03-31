import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect PRO v15", layout="wide", page_icon="🏥")

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

# --- DATABASE (v15 - Reset per eliminare OperationalError) ---
DB_NAME = "rems_database_v15.db"

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

# --- ACCESSO (Risolve KeyError firma) ---
if 'u_data' not in st.session_state: st.session_state.u_data = None

if not st.session_state.u_data:
    st.title("🏥 REMS CONNECT PRO v15")
    t1, t2 = st.tabs(["🔐 Login", "📝 Registrazione"])
    with t1:
        with st.form("login_form"):
            u, p = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u, hash_pw(p)))
                if res: 
                    st.session_state.u_data = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
    with t2:
        with st.form("reg_form"):
            nu, np = st.text_input("User"), st.text_input("Pass", type="password")
            nn, nc, nq = st.text_input("Nome"), st.text_input("Cognome"), st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("Fatto!")
    st.stop()

# Firma sicura
usr = st.session_state.u_data
firma = f"{usr['nome']} {usr['cognome']} ({usr['ruolo']})"

menu = st.sidebar.radio("MENU", ["📊 Monitoraggio", "👥 Equipe", "⚙️ Gestione"])
if st.sidebar.button("LOGOUT"): st.session_state.u_data = None; st.rerun()

# --- 1. MONITORAGGIO ---
if menu == "📊 Monitoraggio":
    st.header("📋 Diario Clinico Generale")
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                h = "<table class='report-table'><tr><th>Data</th><th>Qualifica</th><th>Firma</th><th>Evento</th></tr>"
                for d, r, o, nt in evs:
                    h += f"<tr><td>{d}</td><td><span class='badge bg-{r.lower()}'>{r}</span></td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

# --- 2. EQUIPE (CON REPORT SOTTO OGNI COSA) ---
elif menu == "👥 Equipe":
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_n = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_n][0]

        # PSICHIATRA
        if usr['ruolo'] == "Psichiatra":
            st.subheader("💊 Prescrizione Terapia")
            with st.form("presc"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1,c2,c3 = st.columns(3)
                m, p, n = c1.checkbox("Mattina"), c2.checkbox("Pomeriggio"), c3.checkbox("Notte")
                if st.form_submit_button("SALVA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 Prescr.: {f} {d}", usr['ruolo'], firma), True)
                    st.rerun()
            
            st.markdown("#### 📋 Report Terapie Attive")
            ter_attive = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            if ter_attive:
                for tid, fa, do, m1, p1, n1 in ter_attive:
                    c_t, c_b = st.columns([4,1])
                    c_t.info(f"**{fa} {do}** | Orari: {'M ' if m1 else ''}{'P ' if p1 else ''}{'N' if n1 else ''}")
                    if c_b.button("Elimina", key=f"t_{tid}"):
                        db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True); st.rerun()

        # INFERMIERE
        elif usr['ruolo'] == "Infermiere":
            st.subheader("💊 Somministrazione e Consegne")
            # Somministrazione
            for fa, do in db_run("SELECT farmaco, dose FROM terapie WHERE p_id=?", (p_id,)):
                col1, col2, col3 = st.columns([2,1,1])
                col1.write(f"**{fa}** ({do})")
                if col2.button("Somministra", key=f"ok_{fa}"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrato: {fa}", usr['ruolo'], firma), True); st.success(f"{fa} ok")
                if col3.button("RIFIUTA", key=f"no_{fa}"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"❌ RIFIUTATO: {fa}", usr['ruolo'], firma), True); st.warning(f"{fa} rifiutato")
            
            st.write("---")
            # Consegne M/P/N
            f_con = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
            t_con = st.text_area("Consegna di turno")
            if st.button("SALVA CONSEGNA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📋 CONSEGNA {f_con.upper()}: {t_con}", usr['ruolo'], firma), True); st.rerun()
            
            # Parametri (Senza limiti minimi per evitare errori v14)
            st.write("---")
            with st.form("pv"):
                c1,c2,c3,c4 = st.columns(4)
                mx = c1.number_input("MAX", value=120); mn = c2.number_input("MIN", value=80)
                fc = c3.number_input("FC", value=70); sp = c4.number_input("SpO2", value=98)
                if st.form_submit_button("REGISTRA PARAMETRI"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA:{mx}/{mn} FC:{fc} SpO2:{sp}", usr['ruolo'], firma), True); st.rerun()
            
            st.markdown("#### 📋 Report Ultime Attività Infermieristiche")
            inf_ev = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND ruolo='Infermiere' ORDER BY id_u DESC LIMIT 5", (p_id,))
            if inf_ev: st.table(pd.DataFrame(inf_ev, columns=["Data", "Evento", "Firma"]))

        # EDUCATORI (Correzione zeri e report cassa)
        elif usr['ruolo'] == "Educatore":
            st.subheader("💰 Gestione Cassa")
            movs = db_run("SELECT data, causale, importo, tipo, op FROM cassa WHERE p_id=?", (p_id,))
            saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
            st.metric("Saldo Attuale", f"€ {saldo:.2f}")
            
            with st.form("cassa_form"):
                tp = st.radio("Operazione", ["Entrata", "Uscita"])
                im = st.number_input("Importo Euro", value=0.0, step=0.5)
                ca = st.text_input("Causale")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m"), ca, im, tp, firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {tp}: €{im:.2f} ({ca})", usr['ruolo'], firma), True); st.rerun()
            
            st.markdown("#### 📋 Report Movimenti Economici")
            if movs:
                df_c = pd.DataFrame(movs, columns=["Data", "Causale", "Importo", "Tipo", "Operatore"])
                df_c["Importo"] = df_c["Importo"].map('{:.2f}'.format) # Toglie gli zeri superflui
                st.table(df_c)

        # OSS
        elif usr['ruolo'] == "OSS":
            st.subheader("🛠️ Mansioni OSS")
            m_sc = st.selectbox("Azione", ["Pulizia Camera", "Pulizia Refettorio", "Sale Fumo", "Cortile", "Lavatrice"])
            if st.button("REGISTRA MANSIONE"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🛠️ {m_sc}", usr['ruolo'], firma), True); st.rerun()
            
            st.markdown("#### 📋 Report Mansioni Svolte")
            oss_ev = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND ruolo='OSS' ORDER BY id_u DESC LIMIT 10", (p_id,))
            if oss_ev: st.table(pd.DataFrame(oss_ev, columns=["Data", "Mansione", "Firma"]))

# --- 3. GESTIONE ---
elif menu == "⚙️ Gestione":
    st.header("Anagrafica e Sistema")
    n_p = st.text_input("Nuovo Paziente")
    if st.button("AGGIUNGI"):
        db_run("INSERT INTO pazienti (nome) VALUES (?)", (n_p.upper(),), True); st.rerun()
    
    st.write("---")
    st.subheader("Modifica / Elimina")
    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        c1, c2, c3 = st.columns([3,1,1])
        nn = c1.text_input("Nome", value=n, key=f"ed_{pid}")
        if c2.button("💾", key=f"s_{pid}"):
            db_run("UPDATE pazienti SET nome=? WHERE id=?", (nn.upper(), pid), True); st.rerun()
        if c3.button("🗑️", key=f"d_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
