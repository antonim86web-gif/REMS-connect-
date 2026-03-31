import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib
import pandas as pd

# --- 1. CONFIGURAZIONE E STILE ---
# Modificato il titolo per rimuovere 'PERIZIA'
st.set_page_config(page_title="REMS Connect PRO v14", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 10px; text-align: left; }
    .report-table td { padding: 8px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; }
    .badge { padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; color: white; font-weight: bold; }
    .bg-psichiatra { background: #dc2626; } .bg-infermiere { background: #2563eb; }
    .bg-educatore { background: #059669; } .bg-oss { background: #d97706; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE (v14 - Struttura Pulita) ---
DB_NAME = "rems_pro_v14.db"

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

# --- 3. GESTIONE SESSIONE ---
if 'user_data' not in st.session_state: st.session_state.user_data = None

if not st.session_state.user_data:
    # Modificato il titolo per rimuovere 'ACCESSO PERITI'
    st.title("🏥 REMS CONNECT - ACCESSO")
    t1, t2 = st.tabs(["🔐 Login", "📝 Registrazione"])
    with t1:
        with st.form("l"):
            u_in = st.text_input("User")
            p_in = st.text_input("Pass", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res: 
                    st.session_state.user_data = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Credenziali non valide.")
    with t2:
        with st.form("r"):
            nu, np = st.text_input("Username"), st.text_input("Password", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("OK!")
    st.stop()

# Firma globale
u = st.session_state.user_data
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

st.sidebar.subheader(f"Utente: {u['nome']}")
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "⚙️ Gestione"])
if st.sidebar.button("ESCI"): st.session_state.user_data = None; st.rerun()

# --- 4. MONITORAGGIO ---
if menu == "📊 Monitoraggio":
    st.header("📋 Diario Clinico e Report")
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                h = "<table class='report-table'><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Nota Report</th></tr>"
                for d, r, o, nt in evs:
                    h += f"<tr><td>{d}</td><td><span class='badge bg-{r.lower()}'>{r}</span></td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

# --- 5. EQUIPE (FUNZIONI SPECIFICHE) ---
elif menu == "👥 Equipe":
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_n = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_n][0]

        # PSICHIATRA: Terapia con Checkbox e Modifica
        if u['ruolo'] == "Psichiatra":
            st.subheader("💊 Piano Terapeutico")
            with st.form("f_ter"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1,c2,c3 = st.columns(3)
                m = c1.checkbox("Mattina"); p = c2.checkbox("Pomeriggio"); n = c3.checkbox("Notte")
                if st.form_submit_button("AGGIUNGI/VARIA TERAPIA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 Prescrizione: {f} {d}", u['ruolo'], firma), True)
                    st.rerun()
            
            st.write("---")
            for tid, fa, do, m1, p1, n1 in db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,)):
                col1, col2 = st.columns([5,1])
                col1.info(f"**{fa} {do}** | Orari: {'M' if m1 else '-'} | {'P' if p1 else '-'} | {'N' if n1 else '-'}")
                if col2.button("Elimina", key=f"del_t_{tid}"):
                    db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🗑️ Terapia Eliminata: {fa}", u['ruolo'], firma), True)
                    st.rerun()

        # INFERMIERE: Somministrazione con Rifiuto + Consegne M/P/N
        elif u['ruolo'] == "Infermiere":
            t_som, t_con, t_par = st.tabs(["💊 Somministrazione", "📝 Consegne Turno", "📊 Parametri"])
            with t_som:
                for tid, fa, do in db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,)):
                    c_f, c_ok, c_no = st.columns([2, 1, 1])
                    c_f.write(f"**{fa}** ({do})")
                    if c_ok.button("SOMMINISTRA", key=f"ok_{tid}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"✔️ Somministrato: {fa}", u['ruolo'], firma), True)
                        st.success("Registrato.")
                    if c_no.button("RIFIUTA", key=f"no_{tid}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"❌ RIFIUTATO: {fa}", u['ruolo'], firma), True)
                        st.warning("Rifiuto registrato.")
            
            with t_con:
                fascia = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
                testo_c = st.text_area("Nota Consegna")
                if st.button("SALVA CONSEGNA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📋 CONSEGNA {fascia.upper()}: {testo_c}", u['ruolo'], firma), True)
                    st.rerun()

            with t_par:
                with st.form("pv"):
                    c1,c2,c3,c4 = st.columns(4)
                    mx = c1.number_input("MAX", 120); mn = c2.number_input("MIN", 80)
                    fc = c3.number_input("FC", 72); sp = c4.number_input("SpO2", 98)
                    if st.form_submit_button("REGISTRA PARAMETRI"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA:{mx}/{mn} FC:{fc} SpO2:{sp}", u['ruolo'], firma), True)
                        st.rerun()

        # EDUCATORE: Cassa senza zeri superflui
        elif u['ruolo'] == "Educatore":
            movs = db_run("SELECT data, causale, importo, tipo, op FROM cassa WHERE p_id=?", (p_id,))
            saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in movs])
            st.metric("Saldo Economico", f"€ {saldo:.2f}")
            with st.form("c"):
                tp = st.radio("Operazione", ["Entrata", "Uscita"])
                im = st.number_input("Euro", 0.0); ca = st.text_input("Causale")
                if st.form_submit_button("REGISTRA MOVIMENTO"):
                    db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%y"), ca, im, tp, firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"💰 {tp}: €{im:.2f} ({ca})", u['ruolo'], firma), True)
                    st.rerun()
            if movs:
                df = pd.DataFrame(movs, columns=["Data", "Causale", "Importo", "Tipo", "Operatore"])
                df["Importo"] = df["Importo"].apply(lambda x: f"€ {x:,.2f}") # Pulisce gli zeri
                st.table(df)

        # OSS: Mansioni Richieste
        elif u['ruolo'] == "OSS":
            m_sc = st.selectbox("Mansione", ["Pulizia Camera", "Pulizia Refettorio", "Sale Fumo", "Cortile", "Lavatrice"])
            nota_o = st.text_area("Note OSS")
            if st.button("REGISTRA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🛠️ {m_sc}: {nota_o}", u['ruolo'], firma), True)
                st.rerun()

# --- 6. GESTIONE PAZIENTI ---
elif menu == "⚙️ Gestione":
    st.header("Anagrafica")
    nuovo = st.text_input("Aggiungi Paziente")
    if st.button("SALVA"):
        db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo.upper(),), True); st.rerun()
    
    st.write("---")
    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        c1, c2, c3 = st.columns([3,1,1])
        nn = c1.text_input("Paziente", value=n, key=f"e_{pid}")
        if c2.button("💾 Modifica", key=f"s_{pid}"):
            db_run("UPDATE pazienti SET nome=? WHERE id=?", (nn.upper(), pid), True); st.rerun()
        if c3.button("🗑️ Elimina", key=f"d_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
