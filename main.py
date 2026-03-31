import streamlit as st
import sqlite3
from datetime import datetime, date

# --- 1. CONFIGURAZIONE PAGINA (SIDEBAR CHIUSA DI DEFAULT) ---
st.set_page_config(
    page_title="REMS Connect PRO", 
    layout="wide", 
    page_icon="🏥",
    initial_sidebar_state="collapsed" # La sidebar si ritira automaticamente dopo l'interazione
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .stApp {
        background: linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 100%);
        background-attachment: fixed;
    }

    .main-title {
        text-align: center; 
        background: linear-gradient(90deg, #1e3a8a, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.5rem; margin-bottom: 25px;
    }

    /* SIDEBAR BLU NOTTE SOLIDO */
    [data-testid="stSidebar"] {
        background-color: #0a192f !important;
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    
    /* TESTI SIDEBAR BIANCHI */
    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }

    /* TABELLE GLASSMORPHISM */
    .custom-table { 
        width: 100%; border-collapse: separate; border-spacing: 0; 
        background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(8px);
        border-radius: 12px; overflow: hidden;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
    .custom-table th { 
        background-color: #1e293b; color: #ffffff !important; 
        padding: 12px; font-size: 0.75rem; text-transform: uppercase;
    }
    .custom-table td { 
        padding: 12px; border-bottom: 1px solid rgba(0,0,0,0.05); 
        font-size: 0.85rem; color: #1e293b !important;
    }

    /* BADGE */
    .badge { 
        padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; 
        font-weight: 700; color: white !important; display: inline-block; 
    }
    .bg-psichiatra { background: #ef4444; }
    .bg-infermiere { background: #3b82f6; }
    .bg-educatore  { background: #10b981; }
    .bg-oss        { background: #f59e0b; }
    .bg-appuntamento { background: #8b5cf6; }
    .bg-sistema    { background: #64748b; }

    /* CARD */
    .card-box { 
        background: rgba(255, 255, 255, 0.75); 
        border-radius: 12px; padding: 15px; margin-bottom: 10px; 
        border: 1px solid rgba(255,255,255,0.4);
        color: #1e293b !important;
    }

    /* FIX TESTO SCURO */
    .stMarkdown, label, p, .stSelectbox label { 
        color: #1e293b !important; 
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_connect_data.db"
def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (p_id INTEGER, data TEXT, ora TEXT, tipo TEXT, dettagli TEXT, scorta TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)
    with st.columns([1,1.5,1])[1]:
        with st.form("login_form"):
            pwd = st.text_input("Accesso Riservato", type="password")
            if st.form_submit_button("ENTRA"):
                if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. SIDEBAR ---
st.sidebar.markdown("<h3 style='text-align:center;'>MENU DI SISTEMA</h3>", unsafe_allow_html=True)
menu = st.sidebar.radio("VAI A:", ["📊 Monitoraggio", "👥 Equipe", "📅 Appuntamenti", "⚙️ Gestione"])

# --- 5. LOGICA SEZIONI ---

if menu == "📊 Monitoraggio":
    st.markdown("<h2 class='main-title'>Monitoraggio Clinico</h2>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            log = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            if log:
                html = "<table class='custom-table'><thead><tr><th>Ora</th><th>Profilo</th><th>Op</th><th>Nota</th></tr></thead>"
                for d, r, o, n in log:
                    cls = "bg-appuntamento" if "📅" in n else f"bg-{r.lower()}"
                    html += f"<tr><td>{d}</td><td><span class='badge {cls}'>{r}</span></td><td>{o}</td><td>{n}</td></tr>"
                st.markdown(html + "</table>", unsafe_allow_html=True)

elif menu == "👥 Equipe":
    st.markdown("<h2 class='main-title'>Area Equipe</h2>", unsafe_allow_html=True)
    # Obblighiamo a scegliere il ruolo nella sidebar prima di procedere
    ruolo = st.sidebar.selectbox("SCEGLI FIGURA PROFESSIONALE", ["Seleziona...", "Psichiatra", "Infermiere", "Educatore", "OSS"])
    
    if ruolo == "Seleziona...":
        st.info("👈 Apri il menù laterale e seleziona la tua figura professionale per operare.")
    else:
        pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if pazienti:
            p_nome = st.selectbox("Paziente", [p[1] for p in pazienti])
            p_id = [p[0] for p in pazienti if p[1] == p_nome][0]
            
            if ruolo == "Psichiatra":
                f_med = st.text_input("Firma Medico")
                with st.form("p_f"):
                    c1,c2 = st.columns(2); f, d = c1.text_input("Farmaco"), c2.text_input("Dose")
                    m,p,n = st.columns(3); m1,p1,n1 = m.checkbox("M"), p.checkbox("P"), n.checkbox("N")
                    if st.form_submit_button("PRESCRIVI"):
                        tu = ",".join([s for s, b in zip(["M","P","N"], [m1,p1,n1]) if b])
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, f, d, tu, f_med, date.today().strftime("%d/%m/%Y")), True); st.rerun()

            elif ruolo == "Infermiere":
                f_inf = st.text_input("Firma Infermiere")
                t1, t2 = st.tabs(["💊 Terapia", "📊 Parametri"])
                with t1:
                    turno = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
                    terapie = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
                    acc, rif = [], []
                    for f, d, tu_p, rid in terapie:
                        if tu_p and turno[0] in tu_p:
                            c_f, c_a, c_r = st.columns([3,1,1])
                            c_f.write(f"**{f}** ({d})")
                            if c_a.checkbox("✔️", key=f"a_{rid}"): acc.append(f"{f} ({d})")
                            if c_r.checkbox("❌", key=f"r_{rid}"): rif.append(f"{f} ({d})")
                    if st.button("REGISTRA SOMMINISTRAZIONE"):
                        if f_inf and (acc or rif):
                            nota = f"💊 [{turno[0]}] Assunti: {', '.join(acc)} | Rifiutati: {', '.join(rif)}"
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", nota, "Infermiere", f_inf), True); st.rerun()
                with t2:
                    with st.form("pv"):
                        c1,c2,c3,c4 = st.columns(4); pa,fc,sa,tc = c1.text_input("PA"), c2.number_input("FC"), c3.number_input("SpO2"), c4.number_input("TC", 34.0, 42.0, 36.5)
                        if st.form_submit_button("SALVA PV"):
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📊 PA:{pa} FC:{fc} SpO2:{sa}% TC:{tc}", "Infermiere", f_inf), True); st.rerun()

            elif ruolo == "Educatore":
                f_ed = st.text_input("Firma Educatore")
                mov = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
                st.metric("CASSA", f"€ {sum([m[2] if m[3] == 'Entrata' else -m[2] for m in mov]):.2f}")
                with st.form("c"):
                    tp, im, ds = st.radio("Tipo", ["Entrata", "Uscita"]), st.number_input("€"), st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tp, f_ed), True); st.rerun()

            elif ruolo == "OSS":
                f_oss = st.text_input("Firma OSS")
                with st.form("oss_m"):
                    m1, m2, m3 = st.checkbox("Camera"), st.checkbox("Refettorio"), st.checkbox("Bagno")
                    if st.form_submit_button("CONFERMA PULIZIE"):
                        sel = [t for b,t in zip([m1,m2,m3], ["Camera","Refettorio","Bagno"]) if b]
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"🧹 Pulizie: {', '.join(sel)}", "OSS", f_oss), True); st.rerun()

elif menu == "📅 Appuntamenti":
    st.markdown("<h2 class='main-title'>Agenda Uscite</h2>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_nome = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_nome][0]
        with st.form("f_agenda"):
            c1,c2 = st.columns(2); d_u = c1.date_input("Data"); h_u = c2.time_input("Ora")
            t_u = st.selectbox("Tipo", ["Udienza", "Visita", "Permesso"])
            acc = st.text_input("Accompagnatore")
            if st.form_submit_button("SALVA"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, tipo, dettagli, scorta) VALUES (?,?,?,?,?,?)", (p_id, d_u.strftime("%d/%m/%Y"), h_u.strftime("%H:%M"), t_u, "", acc), True)
                db_run("INSERT INTO eventi (id, data, umore, nota, ruolo, op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📅 {t_u} (Acc: {acc})", "Sistema", "Agenda"), True); st.rerun()

elif menu == "⚙️ Gestione":
    st.markdown("<h2 class='main-title'>Anagrafica</h2>", unsafe_allow_html=True)
    n = st.text_input("Nome Paziente")
    if st.button("AGGIUNGI"):
        if n: db_run("INSERT INTO pazienti (nome) VALUES (?)", (n,), True); st.rerun()
