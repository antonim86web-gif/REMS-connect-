import sqlite3
import streamlit as st
from datetime import datetime, date

# --- 1. CONFIGURAZIONE E DESIGN PRO ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide", page_icon="🏥", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #f8fafc; }
    
    /* Intestazione fissa del corpo centrale */
    .main-header {
        background: #ffffff; padding: 20px; border-bottom: 2px solid #e2e8f0;
        margin-bottom: 30px; border-radius: 0 0 15px 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .main-title {
        text-align: center; 
        background: linear-gradient(90deg, #1e40af, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.2rem; margin: 0;
    }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #1e40af !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }

    /* Layout Post-it */
    .postit-container { display: flex; flex-wrap: wrap; gap: 15px; padding: 10px; }
    .postit {
        width: 280px; min-height: 180px; padding: 18px;
        box-shadow: 4px 4px 8px rgba(0,0,0,0.1);
        font-family: 'Inter', sans-serif; border-bottom-right-radius: 45px 5px;
        margin-bottom: 15px;
    }
    .postit-inf { background: #e0f2fe; border-left: 6px solid #0284c7; }
    .postit-oss { background: #fef9c3; border-left: 6px solid #eab308; }
    .postit-header { font-size: 0.7rem; font-weight: 800; text-transform: uppercase; color: #475569; margin-bottom: 8px; border-bottom: 1px solid rgba(0,0,0,0.1); }
    .postit-body { font-size: 0.88rem; color: #1e293b; line-height: 1.5; font-weight: 500; }
    .postit-footer { margin-top: 12px; font-size: 0.7rem; font-weight: 700; color: #64748b; text-align: right; }

    /* Tabelle */
    .custom-table { width: 100%; border-collapse: collapse; margin-top: 10px; border-radius: 8px; overflow: hidden; background: white; }
    .custom-table th { background: #1e293b; color: white !important; padding: 12px; font-size: 0.75rem; text-align: left; }
    .custom-table td { padding: 12px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; color: #334155; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_pro_v4.db"
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

# --- 3. GESTIONE CORPO PAGINA (DOPO IL MENU) ---

if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("<div class='main-header'><h1 class='main-title'>SISTEMA REMS CONNECT</h1></div>", unsafe_allow_html=True)
    with st.container():
        _, col, _ = st.columns([1, 1, 1])
        with col:
            with st.form("login_form"):
                pwd = st.text_input("Inserire Codice Accesso", type="password")
                if st.form_submit_button("ENTRA"):
                    if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- SIDEBAR MENU ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2966/2966327.png", width=80)
st.sidebar.title("NAVIGAZIONE")
menu = st.sidebar.radio("", ["📊 Monitoraggio", "👥 Operatività Equipe", "📅 Agenda Appuntamenti", "⚙️ Gestione Reparto"])

# --- CORPO CENTRALE DINAMICO ---
st.markdown(f"<div class='main-header'><h1 class='main-title'>{menu}</h1></div>", unsafe_allow_html=True)

container_corpo = st.container()

with container_corpo:
    if menu == "📊 Monitoraggio":
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if not p_lista:
            st.info("Nessun paziente presente in reparto.")
        for pid, nome in p_lista:
            with st.expander(f"📁 CARTELLA: {nome}", expanded=False):
                ev = db_run("SELECT data, ruolo, op, nota, umore FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
                if ev:
                    # Sezione Post-it nel diario
                    st.markdown("### 📝 Consegne di Turno")
                    h_post = "<div class='postit-container'>"
                    for d, r, o, n, u in ev:
                        if "📝" in n:
                            p_class = "postit-inf" if r == "Infermiere" else "postit-oss"
                            h_post += f"<div class='postit {p_class}'><div class='postit-header'>{d} | {u}</div><div class='postit-body'>{n}</div><div class='postit-footer'>{r}: {o}</div></div>"
                    st.markdown(h_post + "</div>", unsafe_allow_html=True)
                    
                    # Sezione Dati Tecnici
                    st.markdown("### 🛠️ Registro Attività")
                    h_tab = "<table class='custom-table'><tr><th>Data</th><th>Ruolo</th><th>Attività / Parametri</th><th>Operatore</th></tr>"
                    for d, r, o, n, u in ev:
                        if "📝" not in n: h_tab += f"<tr><td>{d}</td><td>{r}</td><td>{n}</td><td>{o}</td></tr>"
                    st.markdown(h_tab + "</table>", unsafe_allow_html=True)

    elif menu == "👥 Operatività Equipe":
        ruolo = st.selectbox("Seleziona il tuo Profilo", ["Scegli...", "Psichiatra", "Infermiere", "Educatore", "OSS"])
        if ruolo != "Scegli...":
            p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
            if p_lista:
                p_nome = st.selectbox("Paziente", [p[1] for p in p_lista])
                p_id = [p[0] for p in p_lista if p[1] == p_nome][0]
                
                if ruolo == "Psichiatra":
                    f_m = st.text_input("Firma Medico")
                    with st.form("prescr"):
                        fa, do = st.text_input("Farmaco"), st.text_input("Dose")
                        c1,c2,c3 = st.columns(3); m1, p1, n1 = c1.checkbox("M"), c2.checkbox("P"), c3.checkbox("N")
                        if st.form_submit_button("Prescrivi"):
                            if f_m and fa:
                                tu = ",".join([s for s, b in zip(["M","P","N"], [m1,p1,n1]) if b])
                                db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, fa, do, tu, f_m, date.today().strftime("%d/%m/%Y")), True); st.rerun()

                elif ruolo == "Infermiere":
                    f_i = st.text_input("Firma Infermiere")
                    tab_i1, tab_i2 = st.tabs(["📊 Parametri e Terapia", "📝 Consegne Post-it"])
                    with tab_i1:
                        c1,c2,c3,c4 = st.columns(4); pa, fc, sp, tc = c1.text_input("PA"), c2.text_input("FC"), c3.text_input("SpO2"), c4.text_input("TC")
                        if st.button("Salva Parametri"):
                            if f_i: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📊 PA:{pa} FC:{fc} SpO2:{sp} TC:{tc}", "Infermiere", f_i), True); st.rerun()
                    with tab_i2:
                        u_i = st.selectbox("Stato Umorale", ["Stabile", "Agitato", "Depresso", "Collaborante"])
                        txt = st.text_area("Scrivi consegna...")
                        if st.button("Appendi Post-it"):
                            if f_i and txt: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), u_i, f"📝 {txt}", "Infermiere", f_i), True); st.rerun()

                elif ruolo == "OSS":
                    f_o = st.text_input("Firma Operatore OSS")
                    tab_o1, tab_o2 = st.tabs(["🧹 Mansioni", "📝 Note di Turno"])
                    with tab_o1:
                        with st.form("mans_o"):
                            # Mansioni richieste: Stanza, Refettorio, Sale Fumo, Cortile, Lavatrice
                            m = [st.checkbox(l) for l in ["Pulizia Stanza", "Refettorio", "Sale Fumo", "Cortile", "Lavatrice"]]
                            if st.form_submit_button("Registra Mansioni"):
                                sel = [l for b,l in zip(m, ["Stanza","Refettorio","Sale Fumo","Cortile","Lavatrice"]) if b]
                                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"🧹 Mansioni: {', '.join(sel)}", "OSS", f_o), True); st.rerun()
                    with tab_o2:
                        txt_o = st.text_area("Note OSS...")
                        if st.button("Salva Post-it OSS"):
                            if f_o and txt_o: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📝 {txt_o}", "OSS", f_o), True); st.rerun()

    elif menu == "📅 Agenda Appuntamenti":
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_lista:
            p_nome = st.selectbox("Paziente", [p[1] for p in p_lista])
            p_id = [p[0] for p in p_lista if p[1] == p_nome][0]
            with st.form("app_form"):
                d, h = st.date_input("Data"), st.time_input("Ora")
                ti = st.selectbox("Tipo Uscita", ["Udienza", "Visita Medica", "Visita con Parenti", "Permesso"])
                acc = st.text_input("Accompagnatore")
                if st.form_submit_button("Programma Uscita"):
                    db_run("INSERT INTO appuntamenti (p_id, data, ora, tipo, accompagnatore) VALUES (?,?,?,?,?)", (p_id, d.strftime("%d/%m/%Y"), h.strftime("%H:%M"), ti, acc), True)
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📅 {ti} con {acc}", "Sistema", "Agenda"), True); st.rerun()

    elif menu == "⚙️ Gestione Reparto":
        st.subheader("Anagrafica Pazienti")
        nuovo = st.text_input("Nuovo Ingresso (Nome e Cognome)")
        if st.button("Registra Paziente"):
            if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo.strip().upper(),), True); st.rerun()
        st.write("---")
        for pid, nome in db_run("SELECT id, nome FROM pazienti"):
            c1, c2 = st.columns([5, 1])
            c1.write(f"🏷️ {nome}")
            if c2.button("🗑️", key=f"del_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
