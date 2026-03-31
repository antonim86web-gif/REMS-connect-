import sqlite3
import streamlit as st
from datetime import datetime, date

# --- 1. CONFIGURAZIONE E DESIGN ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide", page_icon="🏥", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #ffffff; }
    .main-title {
        text-align: center; background: linear-gradient(90deg, #1e40af, #3b82f6);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.5rem; margin-bottom: 25px;
    }
    .custom-table { 
        width: 100%; border-collapse: collapse; background-color: #ffffff;
        border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
        margin-bottom: 20px; border: 1px solid #e2e8f0;
    }
    .custom-table th { background-color: #1e293b; color: #ffffff !important; padding: 10px; font-size: 0.75rem; text-align: left; }
    .custom-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; color: #1e293b !important; }
    .badge { padding: 4px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; color: white !important; display: inline-block; }
    .bg-psichiatra { background: #dc2626; } .bg-infermiere { background: #2563eb; }
    .bg-educatore  { background: #059669; } .bg-oss { background: #d97706; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_pro_final_2026.db"
def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (p_id INTEGER, data TEXT, ora TEXT, tipo TEXT, accompagnatore TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>SISTEMA REMS CONNECT</h1>", unsafe_allow_html=True)
    with st.columns([1,1,1])[1]:
        with st.form("login"):
            pwd = st.text_input("Codice Identificativo", type="password")
            if st.form_submit_button("ACCEDI"):
                if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "📅 Appuntamenti", "⚙️ Gestione"])

# --- 5. LOGICA ---

# FUNZIONE DI PROTEZIONE PER EVITARE L'ERRORE INDEXERROR (Screenshot 22477.jpg)
def get_pazienti():
    return db_run("SELECT id, nome FROM pazienti ORDER BY nome")

if menu == "📊 Monitoraggio":
    st.markdown("<h2 class='main-title'>Diario Clinico Unificato</h2>", unsafe_allow_html=True)
    p_lista = get_pazienti()
    if not p_lista:
        st.info("Nessun paziente presente. Vai in 'Gestione' per aggiungerne uno.")
    else:
        for pid, nome in p_lista:
            with st.expander(f"👤 {nome.upper()}", expanded=False):
                log = db_run("SELECT data, ruolo, op, nota, umore FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
                if log:
                    h = "<table class='custom-table'><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Umore</th><th>Evento</th></tr>"
                    for d, r, o, n, u in log:
                        cls = f"bg-{r.lower()}" if r.lower() in ["infermiere", "oss", "psichiatra", "educatore"] else ""
                        h += f"<tr><td>{d}</td><td><span class='badge {cls}'>{r}</span></td><td>{o}</td><td>{u}</td><td>{n}</td></tr>"
                    st.markdown(h + "</table>", unsafe_allow_html=True)

elif menu == "👥 Equipe":
    ruolo = st.sidebar.selectbox("PROFILO OPERATIVO", ["Scegli...", "Psichiatra", "Infermiere", "Educatore", "OSS"])
    if ruolo != "Scegli...":
        p_lista = get_pazienti()
        if not p_lista:
            st.warning("⚠️ Errore: Lista pazienti vuota. Aggiungi un paziente nella sezione 'Gestione'.")
        else:
            p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
            p_id = [p[0] for p in p_lista if p[1] == p_nome][0]
            st.divider()

            if ruolo == "Psichiatra":
                f_m = st.text_input("Firma Medico")
                st.subheader("💊 Nuova Prescrizione")
                with st.form("prescr"):
                    c1,c2 = st.columns(2); fa, do = c1.text_input("Farmaco"), c2.text_input("Dose")
                    m,p,n = st.columns(3); m1, p1, n1 = m.checkbox("M"), p.checkbox("P"), n.checkbox("N")
                    if st.form_submit_button("AGGIUNGI FARMACO"):
                        tu = ",".join([s for s, b in zip(["M","P","N"], [m1,p1,n1]) if b])
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, fa, do, tu, f_m, date.today().strftime("%d/%m/%Y")), True); st.rerun()
                
                piano = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
                for f, d, t, rid in piano:
                    col1, col2 = st.columns([5,1])
                    col1.info(f"**{f}** - {d} (Turni: {t})")
                    if col2.button("🗑️", key=f"del_f_{rid}"):
                        db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True); st.rerun()

            elif ruolo == "OSS":
                f_o = st.text_input("Firma OSS")
                with st.form("oss_m"):
                    st.write("### Mansioni Svolte")
                    c1,c2,c3 = st.columns(3)
                    m1 = c1.checkbox("Camera"); m2 = c2.checkbox("Bagno"); m3 = c3.checkbox("Refettorio")
                    m4 = c1.checkbox("Sale Fumo"); m5 = c2.checkbox("Cortile"); m6 = c3.checkbox("Lavatrice")
                    if st.form_submit_button("REGISTRA MANSIONI"):
                        sel = [t for b,t in zip([m1,m2,m3,m4,m5,m6], ["Camera","Bagno","Refettorio","Sale Fumo","Cortile","Lavatrice"]) if b]
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Collaborante", f"🧹 Svolto: {', '.join(sel)}", "OSS", f_o), True); st.rerun()

            elif ruolo == "Educatore":
                f_e = st.text_input("Firma Educatore")
                mov = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
                saldo = sum([m[2] if m[3] == 'Entrata' else -m[2] for m in mov])
                st.metric("SALDO CASSA", f"€ {saldo:.2f}")
                with st.form("cassa"):
                    tp, im, ds = st.radio("Operazione", ["Entrata", "Uscita"]), st.number_input("€", min_value=0.0), st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tp, f_e), True); st.rerun()

elif menu == "📅 Appuntamenti":
    p_lista = get_pazienti()
    if not p_lista:
        st.info("Aggiungi un paziente per fissare appuntamenti.")
    else:
        p_nome = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_nome][0]
        with st.form("app"):
            c1,c2 = st.columns(2); d, h = c1.date_input("Data"), c2.time_input("Ora")
            ti = st.selectbox("Tipo", ["Udienza", "Visita Medica", "Visita con Parenti", "Permesso"])
            acc = st.text_input("Accompagnatore")
            if st.form_submit_button("FISSA"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, tipo, accompagnatore) VALUES (?,?,?,?,?)", (p_id, d.strftime("%d/%m/%Y"), h.strftime("%H:%M"), ti, acc), True); st.rerun()

elif menu == "⚙️ Gestione":
    st.header("Anagrafica")
    nuovo = st.text_input("Nome Paziente")
    if st.button("AGGIUNGI"):
        if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo.strip().upper(),), True); st.rerun()
    st.divider()
    for pid, nome in get_pazienti():
        c1, c2 = st.columns([5,1])
        c1.write(nome)
        if c2.button("🗑️", key=f"del_p_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
