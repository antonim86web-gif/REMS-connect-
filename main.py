import sqlite3
import streamlit as st
from datetime import datetime, date

# --- 1. CONFIGURAZIONE E DESIGN PRO ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide", page_icon="🏥", initial_sidebar_state="collapsed")

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
    
    /* DESIGN POST-IT */
    .postit-container { display: flex; flex-wrap: wrap; gap: 15px; padding: 10px; justify-content: flex-start; }
    .postit {
        width: 280px; min-height: 180px; padding: 18px;
        box-shadow: 4px 4px 8px rgba(0,0,0,0.1);
        font-family: 'Inter', sans-serif; border-bottom-right-radius: 45px 5px;
        transition: 0.3s; margin-bottom: 10px;
    }
    .postit-inf { background: #e0f2fe; border-left: 6px solid #0284c7; }
    .postit-oss { background: #fef9c3; border-left: 6px solid #eab308; }
    .postit-header { font-size: 0.7rem; font-weight: 800; text-transform: uppercase; color: #475569; margin-bottom: 8px; border-bottom: 1px solid rgba(0,0,0,0.05); }
    .postit-body { font-size: 0.88rem; color: #1e293b; line-height: 1.5; font-weight: 500; }
    .postit-footer { margin-top: 12px; font-size: 0.7rem; font-weight: 700; color: #64748b; text-align: right; }

    /* TABELLE */
    .custom-table { width: 100%; border-collapse: collapse; margin: 10px 0; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
    .custom-table th { background: #1e293b; color: white !important; padding: 10px; font-size: 0.75rem; text-align: left; }
    .custom-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. GESTIONE DATI ---
DB_NAME = "rems_pro_v3.db"
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

# --- 3. ACCESSO ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)
    with st.columns([1,1,1])[1]:
        with st.form("login"):
            pwd = st.text_input("Codice Operatore", type="password")
            if st.form_submit_button("ACCEDI"):
                if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. MENU ---
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "📅 Appuntamenti", "⚙️ Gestione"])

# --- 5. LOGICA ---

if menu == "📊 Monitoraggio":
    st.markdown("<h2 class='main-title'>Diario Clinico Unificato</h2>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            # Visualizzazione mista: Tabelle per dati tecnici, Post-it per note
            ev = db_run("SELECT data, ruolo, op, nota, umore FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            if ev:
                st.write("**Note e Consegne Recenti:**")
                h_post = "<div class='postit-container'>"
                for d, r, o, n, u in ev:
                    if "📝" in n:
                        p_class = "postit-inf" if r == "Infermiere" else "postit-oss"
                        h_post += f"<div class='postit {p_class}'><div class='postit-header'>{d} | {u}</div><div class='postit-body'>{n}</div><div class='postit-footer'>{r}: {o}</div></div>"
                st.markdown(h_post + "</div>", unsafe_allow_html=True)
                
                st.write("**Riepilogo Attività Tecniche:**")
                h_tab = "<table class='custom-table'><tr><th>Data</th><th>Ruolo</th><th>Evento/Dati</th></tr>"
                for d, r, o, n, u in ev:
                    if "📝" not in n: h_tab += f"<tr><td>{d}</td><td>{r}</td><td>{n}</td></tr>"
                st.markdown(h_tab + "</table>", unsafe_allow_html=True)

elif menu == "👥 Equipe":
    ruolo = st.sidebar.selectbox("PROFILO", ["Scegli...", "Psichiatra", "Infermiere", "Educatore", "OSS"])
    if ruolo != "Scegli...":
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_lista:
            p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
            p_id = [p[0] for p in p_lista if p[1] == p_nome][0]
            umore_list = ["Stabile", "Agitato", "Collaborante", "Provocatorio", "Depresso"]

            if ruolo == "Psichiatra":
                f_m = st.text_input("Firma Medico")
                with st.form("p_f"):
                    c1,c2 = st.columns(2); fa, do = c1.text_input("Farmaco"), c2.text_input("Dose")
                    m,p,n = st.columns(3); m1,p1,n1 = m.checkbox("M"), p.checkbox("P"), n.checkbox("N")
                    if st.form_submit_button("PRESCRIVI"):
                        if f_m and fa:
                            tu = ",".join([s for s, b in zip(["M","P","N"], [m1,p1,n1]) if b])
                            db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, fa, do, tu, f_m, date.today().strftime("%d/%m/%Y")), True); st.rerun()

            elif ruolo == "Infermiere":
                f_i = st.text_input("Firma Infermiere")
                t1, t2, t3 = st.tabs(["💊 Terapia", "📊 Parametri", "📝 Consegne (Post-it)"])
                with t1:
                    tur = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
                    ter = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
                    acc, rif = [], []
                    for fa, do, tu, rid in ter:
                        if tu and tur[0] in tu:
                            c1,c2,c3 = st.columns([3,1,1]); c1.write(f"**{fa}** ({do})")
                            if c2.checkbox("✔️", key=f"a_{rid}"): acc.append(fa)
                            if c3.checkbox("❌", key=f"r_{rid}"): rif.append(fa)
                    if st.button("REGISTRA"):
                        if f_i and (acc or rif):
                            n = f"💊 [{tur}] Assunti: {', '.join(acc)} | Rif: {', '.join(rif)}"
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", n, "Infermiere", f_i), True); st.rerun()
                with t3:
                    u_i, t_i = st.selectbox("Umore", umore_list), st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
                    txt = st.text_area("Nota clinica...")
                    if st.button("APPENDI POST-IT"):
                        if f_i and txt:
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), u_i, f"📝 [{t_i}] {txt}", "Infermiere", f_i), True); st.rerun()
                    st.write("---")
                    logs = db_run("SELECT data, nota, op, umore FROM eventi WHERE id=? AND ruolo='Infermiere' AND nota LIKE '📝%' ORDER BY row_id DESC", (p_id,))
                    h_p = "<div class='postit-container'>"
                    for d, n, o, u in logs: h_p += f"<div class='postit postit-inf'><div class='postit-header'>{d} | {u}</div><div class='postit-body'>{n}</div><div class='postit-footer'>Firma: {o}</div></div>"
                    st.markdown(h_p + "</div>", unsafe_allow_html=True)

            elif ruolo == "OSS":
                f_o = st.text_input("Firma OSS")
                t_m, t_n = st.tabs(["🧹 Mansioni", "📝 Note (Post-it)"])
                with t_m:
                    with st.form("oss_m"):
                        m = [st.checkbox(l) for l in ["Stanza", "Refettorio", "Sale Fumo", "Cortile", "Lavatrice"]]
                        if st.form_submit_button("SALVA"):
                            sel = [l for b,l in zip(m, ["Stanza", "Refettorio", "Sale Fumo", "Cortile", "Lavatrice"]) if b]
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Collaborante", f"🧹 Mansioni: {', '.join(sel)}", "OSS", f_o), True); st.rerun()
                with t_n:
                    u_o, t_o = st.selectbox("Umore", umore_list, key="uo"), st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"], key="to")
                    txt_o = st.text_area("Osservazioni...")
                    if st.button("SALVA NOTA OSS"):
                        if f_o and txt_o:
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), u_o, f"📝 [{t_o}] {txt_o}", "OSS", f_o), True); st.rerun()
                    st.write("---")
                    logs_o = db_run("SELECT data, nota, op, umore FROM eventi WHERE id=? AND ruolo='OSS' AND nota LIKE '📝%' ORDER BY row_id DESC", (p_id,))
                    h_po = "<div class='postit-container'>"
                    for d, n, o, u in logs_o: h_po += f"<div class='postit postit-oss'><div class='postit-header'>{d} | {u}</div><div class='postit-body'>{n}</div><div class='postit-footer'>Op: {o}</div></div>"
                    st.markdown(h_po + "</div>", unsafe_allow_html=True)

elif menu == "📅 Appuntamenti":
    st.markdown("<h2 class='main-title'>Agenda</h2>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_nome = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_nome][0]
        with st.form("agenda"):
            c1,c2 = st.columns(2); d, h = c1.date_input("Data"), c2.time_input("Ora")
            ti = st.selectbox("Tipo", ["Udienza", "Visita Medica", "Visita con Parenti", "Permesso"])
            acc = st.text_input("Accompagnatore")
            if st.form_submit_button("CONFERMA USCITA"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, tipo, accompagnatore) VALUES (?,?,?,?,?)", (p_id, d.strftime("%d/%m/%Y"), h.strftime("%H:%M"), ti, acc), True)
                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📅 {ti} ({d.strftime('%d/%m')}) con {acc}", "Sistema", "Agenda"), True); st.rerun()
        apps = db_run("SELECT data, ora, tipo, accompagnatore FROM appuntamenti WHERE p_id=? ORDER BY row_id DESC", (p_id,))
        if apps:
            h = "<table class='custom-table'><tr><th>Data</th><th>Ora</th><th>Tipo</th><th>Accompagnatore</th></tr>"
            for da, ora, tip, sco in apps: h += f"<tr><td>{da}</td><td>{ora}</td><td>{tip}</td><td>{sco}</td></tr>"
            st.markdown(h + "</table>", unsafe_allow_html=True)

elif menu == "⚙️ Gestione":
    st.header("Anagrafica")
    nuovo = st.text_input("Inserisci Nuovo Paziente")
    if st.button("REGISTRA"):
        if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo.strip().upper(),), True); st.rerun()
    for pid, nome in db_run("SELECT id, nome FROM pazienti"):
        c1, c2 = st.columns([5,1])
        c1.write(nome)
        if c2.button("🗑️", key=f"del_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
