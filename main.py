import sqlite3
import streamlit as st
from datetime import datetime, date

# --- 1. CONFIGURAZIONE E DESIGN ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #f8fafc; }
    .main-header {
        background: #ffffff; padding: 20px; border-bottom: 2px solid #e2e8f0;
        margin-bottom: 30px; border-radius: 0 0 15px 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .main-title {
        text-align: center; background: linear-gradient(90deg, #1e40af, #3b82f6);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.2rem; margin: 0;
    }
    /* Stile Post-it */
    .postit-container { display: flex; flex-wrap: wrap; gap: 15px; padding: 10px; }
    .postit {
        width: 280px; min-height: 180px; padding: 18px;
        box-shadow: 4px 4px 8px rgba(0,0,0,0.1); border-bottom-right-radius: 45px 5px;
    }
    .postit-inf { background: #e0f2fe; border-left: 6px solid #0284c7; }
    .postit-oss { background: #fef9c3; border-left: 6px solid #eab308; }
    .postit-header { font-size: 0.7rem; font-weight: 800; text-transform: uppercase; color: #475569; border-bottom: 1px solid rgba(0,0,0,0.1); margin-bottom: 8px; }
    .postit-body { font-size: 0.88rem; color: #1e293b; line-height: 1.5; font-weight: 500; }
    .postit-footer { margin-top: 12px; font-size: 0.7rem; font-weight: 700; color: #64748b; text-align: right; }
</style>
""", unsafe_allow_html=True)

# --- 2. MOTORE DATABASE ---
DB_NAME = "rems_final_v1.db"
def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (p_id INTEGER, data TEXT, ora TEXT, tipo TEXT, accompagnatore TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# Inizializzazione DB al primo avvio
db_run("")

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<div class='main-header'><h1 class='main-title'>REMS CONNECT PRO</h1></div>", unsafe_allow_html=True)
    with st.container():
        _, col, _ = st.columns([1, 1, 1])
        with col:
            with st.form("login"):
                pwd = st.text_input("Codice Accesso Operatore", type="password")
                if st.form_submit_button("ENTRA"):
                    if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. SIDEBAR ---
st.sidebar.title("MENU PRINCIPALE")
menu = st.sidebar.radio("Scegli Sezione:", ["📊 Monitoraggio", "👥 Equipe Operativa", "📅 Agenda Appuntamenti", "⚙️ Gestione"])

# --- 5. CORPO PAGINA ---
st.markdown(f"<div class='main-header'><h1 class='main-title'>{menu}</h1></div>", unsafe_allow_html=True)

if menu == "📊 Monitoraggio":
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if not p_lista: st.info("Nessun paziente in archivio.")
    for pid, nome in p_lista:
        with st.expander(f"📁 CARTELLA: {nome.upper()}", expanded=False):
            ev = db_run("SELECT data, ruolo, op, nota, umore FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            if ev:
                st.markdown("### 📝 Consegne Turno (Post-it)")
                h_post = "<div class='postit-container'>"
                for d, r, o, n, u in ev:
                    if "📝" in n:
                        cls = "postit-inf" if r == "Infermiere" else "postit-oss"
                        h_post += f"<div class='postit {cls}'><div class='postit-header'>{d} | {u}</div><div class='postit-body'>{n}</div><div class='postit-footer'>{r}: {o}</div></div>"
                st.markdown(h_post + "</div>", unsafe_allow_html=True)
                
                st.markdown("### 📋 Diario Attività")
                st.table([{"Data": d, "Ruolo": r, "Attività": n, "Operatore": o} for d, r, o, n, u in ev if "📝" not in n])

elif menu == "👥 Equipe Operativa":
    ruolo = st.selectbox("Identificati come:", ["Scegli...", "Psichiatra", "Infermiere", "Educatore", "OSS"])
    if ruolo != "Scegli...":
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_lista:
            p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
            p_id = [p[0] for p in p_lista if p[1] == p_nome][0]
            st.write("---")

            if ruolo == "Psichiatra":
                firma = st.text_input("Firma Medico")
                with st.form("psic_f"):
                    fa, do = st.text_input("Farmaco"), st.text_input("Dose e Orari")
                    if st.form_submit_button("Prescrivi"):
                        if firma and fa:
                            db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, medico, data_prescr) VALUES (?,?,?,?,?)", (p_id, fa, do, firma, date.today().strftime("%d/%m/%Y")), True); st.success("Prescrizione Inserita."); st.rerun()

            elif ruolo == "Infermiere":
                firma = st.text_input("Firma Infermiere")
                t1, t2 = st.tabs(["📊 Parametri", "📝 Consegne"])
                with t1:
                    with st.form("inf_p"):
                        c1,c2,c3,c4 = st.columns(4); pa, fc, sp, tc = c1.text_input("PA"), c2.text_input("FC"), c3.text_input("SpO2"), c4.text_input("TC")
                        if st.form_submit_button("Salva Parametri"):
                            if firma: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📊 PA:{pa} FC:{fc} SpO2:{sp} TC:{tc}", "Infermiere", firma), True); st.rerun()
                with t2:
                    txt = st.text_area("Consegna fine turno...")
                    if st.button("Salva Post-it"):
                        if firma and txt: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📝 {txt}", "Infermiere", firma), True); st.rerun()

            elif ruolo == "OSS":
                firma = st.text_input("Firma OSS")
                t1, t2 = st.tabs(["🧹 Mansioni", "📝 Note"])
                with t1:
                    with st.form("oss_m"):
                        m = [st.checkbox(l) for l in ["Stanza", "Refettorio", "Sale Fumo", "Cortile", "Lavatrice"]]
                        if st.form_submit_button("Salva Mansioni"):
                            if firma:
                                sel = [l for b,l in zip(m, ["Stanza","Refettorio","Sale Fumo","Cortile","Lavatrice"]) if b]
                                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Collaborante", f"🧹 Mansioni: {', '.join(sel)}", "OSS", firma), True); st.rerun()
                with t2:
                    txt = st.text_area("Nota OSS...")
                    if st.button("Salva Post-it OSS"):
                        if firma and txt: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📝 {txt}", "OSS", firma), True); st.rerun()

            elif ruolo == "Educatore":
                firma = st.text_input("Firma Educatore")
                with st.form("edu_s"):
                    tp = st.radio("Tipo", ["Entrata", "Uscita"])
                    im, ds = st.number_input("€", min_value=0.0), st.text_input("Causale")
                    if st.form_submit_button("Salva Movimento"):
                        if firma: db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tp, firma), True); st.rerun()

elif menu == "📅 Agenda Appuntamenti":
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_nome = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_nome][0]
        with st.form("agenda"):
            d, h = st.date_input("Data"), st.time_input("Ora")
            ti = st.selectbox("Tipo", ["Udienza", "Visita Medica", "Visita con Parenti", "Permesso"])
            acc = st.text_input("Accompagnatore")
            if st.form_submit_button("Salva Appuntamento"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, tipo, accompagnatore) VALUES (?,?,?,?,?)", (p_id, d.strftime("%d/%m/%Y"), h.strftime("%H:%M"), ti, acc), True)
                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📅 {ti} con {acc}", "Sistema", "Agenda"), True); st.rerun()

elif menu == "⚙️ Gestione":
    st.subheader("Anagrafica Pazienti")
    nuovo = st.text_input("Nome e Cognome")
    if st.button("AGGIUNGI"):
        if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo.strip().upper(),), True); st.rerun()
    st.write("---")
    p_lista = db_run("SELECT id, nome FROM pazienti")
    for pid, nome in p_lista:
        c1, c2 = st.columns([5, 1])
        c1.write(f"🏷️ {nome}")
        if c2.button("🗑️", key=f"del_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
