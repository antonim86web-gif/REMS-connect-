import sqlite3
import streamlit as st
from datetime import datetime, date

# --- 1. CONFIGURAZIONE PAGINA E DESIGN (SIDEBAR BLU + CORPO BIANCO) ---
st.set_page_config(
    page_title="REMS Connect PRO", 
    layout="wide", 
    page_icon="🏥",
    initial_sidebar_state="collapsed" 
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #ffffff; }
    .main-title {
        text-align: center; 
        background: linear-gradient(90deg, #1e40af, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.5rem; margin-bottom: 25px;
    }
    [data-testid="stSidebar"] { background-color: #1e40af !important; border-right: 1px solid #1e3a8a; }
    [data-testid="stSidebar"] * { color: #ffffff !important; font-weight: 600 !important; }
    .custom-table { 
        width: 100%; border-collapse: collapse; background-color: #ffffff;
        border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
        margin-bottom: 20px; border: 1px solid #e2e8f0;
    }
    .custom-table th { background-color: #1e293b; color: #ffffff !important; padding: 12px; font-size: 0.75rem; text-transform: uppercase; text-align: left; }
    .custom-table td { padding: 12px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; color: #1e293b !important; }
    .custom-table tr:nth-child(even) { background-color: #f8fafc; }
    .badge { padding: 4px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; color: white !important; display: inline-block; }
    .bg-psichiatra { background: #dc2626; }
    .bg-infermiere { background: #2563eb; }
    .bg-educatore  { background: #059669; }
    .bg-oss        { background: #d97706; }
    .bg-appuntamento { background: #7c3aed; }
    .bg-sistema    { background: #475569; }
    .stMarkdown, label, p, .stSelectbox label { color: #1e293b !important; font-weight: 600; }
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
    with st.columns([1,1,1])[1]:
        with st.form("login"):
            pwd = st.text_input("Codice Identificativo", type="password")
            if st.form_submit_button("ACCEDI"):
                if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
st.sidebar.markdown("<h2 style='text-align:center;'>REMS CONNECT</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "📅 Appuntamenti", "⚙️ Gestione"])

# --- 5. LOGICA ---
if menu == "📊 Monitoraggio":
    st.markdown("<h2 class='main-title'>Diario Clinico Unificato</h2>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            log = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            if log:
                html = "<table class='custom-table'><thead><tr><th>Data/Ora</th><th>Ruolo</th><th>Operatore</th><th>Nota</th></tr></thead><tbody>"
                for d, r, o, n in log:
                    cls = "bg-appuntamento" if "📅" in n else f"bg-{r.lower()}"
                    html += f"<tr><td>{d}</td><td><span class='badge {cls}'>{r}</span></td><td>{o}</td><td>{n}</td></tr>"
                st.markdown(html + "</tbody></table>", unsafe_allow_html=True)

elif menu == "👥 Equipe":
    ruolo = st.sidebar.selectbox("PROFILO OPERATIVO", ["Scegli...", "Psichiatra", "Infermiere", "Educatore", "OSS"])
    if ruolo == "Scegli...": st.info("👈 Seleziona il tuo profilo nella sidebar.")
    else:
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_lista:
            p_nome = st.selectbox("Paziente", [p[1] for p in p_lista])
            p_id = [p[0] for p in p_lista if p[1] == p_nome][0]

            if ruolo == "Psichiatra":
                f_med = st.text_input("Firma Medico")
                with st.form("p_f"):
                    c1,c2 = st.columns(2); f,d = c1.text_input("Farmaco"), c2.text_input("Dose")
                    m,p,n = st.columns(3); m1,p1,n1 = m.checkbox("M"), p.checkbox("P"), n.checkbox("N")
                    if st.form_submit_button("PRESCRIVI"):
                        tu = ",".join([s for s, b in zip(["M","P","N"], [m1,p1,n1]) if b])
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, f, d, tu, f_med, date.today().strftime("%d/%m/%Y")), True); st.rerun()

            elif ruolo == "Infermiere":
                f_inf = st.text_input("Firma Infermiere")
                t1, t2, t3 = st.tabs(["💊 Farmaci", "📊 Parametri", "📝 Consegne"])
                with t1:
                    turno = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
                    ter = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
                    acc, rif = [], []
                    for fa, do, tu_p, rid in ter:
                        if tu_p and turno[0] in tu_p:
                            c1,c2,c3 = st.columns([3,1,1])
                            c1.write(f"**{fa}** ({do})")
                            if c2.checkbox("✔️", key=f"a_{rid}"): acc.append(f"{fa}({do})")
                            if c3.checkbox("❌", key=f"r_{rid}"): rif.append(f"{fa}({do})")
                    if st.button("REGISTRA SOMMINISTRAZIONE"):
                        if f_inf and (acc or rif):
                            nota = f"💊 [{turno[0]}] Assunti: {', '.join(acc)} | Rifiutati: {', '.join(rif)}"
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", nota, "Infermiere", f_inf), True); st.rerun()
                    
                    # --- TABELLA REGISTRAZIONE TERAPIE SOMMINISTRATE ---
                    st.write("---")
                    st.write("**Registro Somministrazioni Recenti:**")
                    inf_log = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND ruolo='Infermiere' AND nota LIKE '💊%' ORDER BY row_id DESC", (p_id,))
                    if inf_log:
                        html_inf = "<table class='custom-table'><tr><th>Data/Ora</th><th>Dettaglio Somministrazione</th><th>Infermiere</th></tr>"
                        for d, n, o in inf_log: html_inf += f"<tr><td>{d}</td><td>{n}</td><td>{o}</td></tr>"
                        st.markdown(html_inf + "</table>", unsafe_allow_html=True)

                with t2:
                    with st.form("pv"):
                        c1,c2,c3,c4 = st.columns(4); pa,fc,sa,tc = c1.text_input("PA"), c2.number_input("FC"), c3.number_input("SpO2"), c4.number_input("TC", 34.0, 42.0, 36.5)
                        if st.form_submit_button("SALVA PV"):
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📊 PA:{pa} FC:{fc} SpO2:{sa}% TC:{tc}", "Infermiere", f_inf), True); st.rerun()
                with t3:
                    txt = st.text_area("Consegne Infermieristiche")
                    if st.button("SALVA CONSEGNA"):
                        if f_inf and txt: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📝 {txt}", "Infermiere", f_inf), True); st.rerun()

            elif ruolo == "Educatore":
                f_ed = st.text_input("Firma Educatore")
                mov = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
                st.metric("CASSA", f"€ {sum([m[2] if m[3] == 'Entrata' else -m[2] for m in mov]):.2f}")
                with st.form("cash"):
                    tp, im, ds = st.radio("Tipo", ["Entrata", "Uscita"]), st.number_input("€"), st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tp, f_ed), True); st.rerun()

            elif ruolo == "OSS":
                f_oss = st.text_input("Firma OSS")
                t_pul, t_cons = st.tabs(["🧹 Pulizie", "📝 Consegne OSS"])
                with t_pul:
                    with st.form("oss_f"):
                        m1,m2,m3 = st.checkbox("Igiene Camera"), st.checkbox("Refettorio"), st.checkbox("Bagno Personale")
                        if st.form_submit_button("SALVA PULIZIE"):
                            sel = [t for b,t in zip([m1,m2,m3], ["Camera","Refettorio","Bagno"]) if b]
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"🧹 Pulizie: {', '.join(sel)}", "OSS", f_oss), True); st.rerun()
                with t_cons:
                    txt_oss = st.text_area("Osservazioni / Consegne OSS")
                    if st.button("SALVA NOTA OSS"):
                        if f_oss and txt_oss: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📝 {txt_oss}", "OSS", f_oss), True); st.rerun()
                
                oss_log = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND ruolo='OSS' ORDER BY row_id DESC", (p_id,))
                if oss_log:
                    st.write("Riepilogo Attività OSS:")
                    html_oss = "<table class='custom-table'><tr><th>Data/Ora</th><th>Nota/Attività</th><th>Op</th></tr>"
                    for d, n, o in oss_log: html_oss += f"<tr><td>{d}</td><td>{n}</td><td>{o}</td></tr>"
                    st.markdown(html_oss + "</table>", unsafe_allow_html=True)

elif menu == "📅 Appuntamenti":
    st.markdown("<h2 class='main-title'>Agenda Uscite</h2>", unsafe_allow_html=True)
    paz = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if paz:
        p_nome = st.selectbox("Paziente", [p[1] for p in paz]); p_id = [p[0] for p in paz if p[1] == p_nome][0]
        with st.form("ag"):
            c1,c2 = st.columns(2); d, h = c1.date_input("Data"), c2.time_input("Ora")
            ti = st.selectbox("Tipo", ["Udienza", "Visita", "Permesso"]); acc = st.text_input("Scorta")
            if st.form_submit_button("AGGIUNGI"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, tipo, dettagli, scorta) VALUES (?,?,?,?,?,?)", (p_id, d.strftime("%d/%m/%Y"), h.strftime("%H:%M"), ti, "", acc), True)
                db_run("INSERT INTO eventi (id, data, umore, nota, ruolo, op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📅 {ti} (Scorta: {acc})", "Sistema", "Agenda"), True); st.rerun()

elif menu == "⚙️ Gestione":
    st.header("Anagrafica")
    nuovo = st.text_input("Nome")
    if st.button("AGGIUNGI"):
        if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), True); st.rerun()
