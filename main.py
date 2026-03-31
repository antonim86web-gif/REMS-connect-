import streamlit as st
import sqlite3
from datetime import datetime, date

# --- 1. CONFIGURAZIONE E DESIGN UNIFICATO ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide", page_icon="🏥")

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
        font-weight: 800; font-size: 2.5rem; margin-bottom: 20px;
    }

    /* DESIGN UNICO PER TUTTE LE TABELLE */
    .custom-table { 
        width: 100%; border-collapse: separate; border-spacing: 0; 
        background: rgba(255, 255, 255, 0.8); 
        backdrop-filter: blur(10px);
        border-radius: 12px; overflow: hidden;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.05); margin-bottom: 20px;
        border: 1px solid rgba(255,255,255,0.3);
    }
    .custom-table th { 
        background-color: #1e293b; color: #ffffff; padding: 12px 15px; 
        text-align: left; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;
    }
    .custom-table td { 
        padding: 12px 15px; border-bottom: 1px solid rgba(226, 232, 240, 0.5); 
        font-size: 0.85rem; color: #1e293b; vertical-align: middle;
    }
    .custom-table tr:hover { background-color: rgba(241, 245, 249, 0.6); }

    /* BADGE STILIZZATI */
    .badge { 
        padding: 4px 10px; border-radius: 20px; font-size: 0.7rem; 
        font-weight: 700; color: white; display: inline-block; text-transform: uppercase;
    }
    .bg-psichiatra { background: #ef4444; }
    .bg-infermiere { background: #3b82f6; }
    .bg-educatore  { background: #10b981; }
    .bg-oss        { background: #f59e0b; }
    .bg-appuntamento { background: #8b5cf6; }
    .bg-sistema    { background: #64748b; }

    /* CARD INPUT */
    .card-box { 
        background: rgba(255, 255, 255, 0.6);
        border-radius: 12px; padding: 20px; margin-bottom: 15px; 
        border: 1px solid rgba(255,255,255,0.4);
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
        with st.form("login"):
            pwd = st.text_input("Accesso", type="password")
            if st.form_submit_button("ENTRA"):
                if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. NAVIGATION ---
st.sidebar.markdown("<h2 style='color:white; text-align:center;'>🏥 REMS PRO</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "📅 Appuntamenti", "⚙️ Gestione"])

# --- 5. LOGICA SEZIONI ---

if "Appuntamenti" in menu:
    st.header("📅 Agenda Uscite")
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if pazienti:
        p_nome = st.selectbox("Paziente", [p[1] for p in pazienti])
        p_id = [p[0] for p in pazienti if p[1] == p_nome][0]
        with st.form("f_app"):
            c1,c2,c3 = st.columns(3)
            da, ora, ti = c1.date_input("Data"), c2.time_input("Ora"), c3.selectbox("Tipo", ["Udienza", "Visita", "Permesso"])
            acc = st.text_input("Accompagnatore Incaricato")
            det = st.text_area("Note")
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, tipo, dettagli, scorta) VALUES (?,?,?,?,?,?)", (p_id, da.strftime("%d/%m/%Y"), ora.strftime("%H:%M"), ti, det, acc), True)
                db_run("INSERT INTO eventi (id, data, umore, nota, ruolo, op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📅 {ti}: {det} (Acc: {acc})", "Sistema", "Agenda"), True)
                st.rerun()
        
        apps = db_run("SELECT data, ora, tipo, dettagli, scorta, row_id FROM appuntamenti WHERE p_id=? ORDER BY row_id DESC", (p_id,))
        if apps:
            html = "<table class='custom-table'><thead><tr><th>Data/Ora</th><th>Tipo</th><th>Note</th><th>Accompagnatore</th><th>Az.</th></tr></thead>"
            for d, o, t, de, sc, rid in apps:
                html += f"<tr><td>{d} {o}</td><td><b>{t}</b></td><td>{de}</td><td>{sc}</td><td>"
                st.markdown(html, unsafe_allow_html=True)
                if st.button("Elimina", key=f"da_{rid}"): db_run("DELETE FROM appuntamenti WHERE row_id=?", (rid,), True); st.rerun()
                html = ""
            st.markdown("</table>", unsafe_allow_html=True)

elif "Equipe" in menu:
    ruolo = st.sidebar.selectbox("Profilo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if pazienti:
        p_nome = st.selectbox("Paziente", [p[1] for p in pazienti]); p_id = [p[0] for p in pazienti if p[1] == p_nome][0]

        if ruolo == "Psichiatra":
            med_f = st.text_input("Firma Medico")
            with st.form("p_f"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                m, p, n = st.columns(3); m1 = m.checkbox("Mattina"); p1 = p.checkbox("Pomeriggio"); n1 = n.checkbox("Notte")
                if st.form_submit_button("SALVA PRESCRIZIONE"):
                    ts = ",".join([s for s, b in zip(["M","P","N"], [m1,p1,n1]) if b])
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, f, d, ts, med_f, date.today().strftime("%d/%m/%Y")), True); st.rerun()
            
            ter = db_run("SELECT data_prescr, farmaco, dosaggio, turni, medico, row_id FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            if ter:
                html = "<table class='custom-table'><thead><tr><th>Data</th><th>Farmaco</th><th>Dose</th><th>Turni</th><th>Medico</th></tr></thead>"
                for d, f, ds, tu, me, rid in ter:
                    html += f"<tr><td>{d}</td><td><b>{f}</b></td><td>{ds}</td><td>{tu}</td><td>{me}</td></tr>"
                st.markdown(html + "</table>", unsafe_allow_html=True)

        elif ruolo == "Educatore":
            ed_f = st.text_input("Firma Educatore")
            mov = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            saldo = sum([m[2] if m[3] == "Entrata" else -m[2] for m in mov])
            st.metric("SALDO ATTUALE", f"€ {saldo:.2f}")
            with st.form("c_f"):
                tp, im, ds = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True), st.number_input("Importo €"), st.text_input("Causale")
                if st.form_submit_button("REGISTRA MOVIMENTO"):
                    db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tp, ed_f), True); st.rerun()
            if mov:
                html = "<table class='custom-table'><thead><tr><th>Data</th><th>Causale</th><th>Entrata</th><th>Uscita</th><th>Op</th></tr></thead>"
                for d, ds, im, tp, op in mov:
                    e, u = (f"€ {im:.2f}", "") if tp == "Entrata" else ("", f"€ {im:.2f}")
                    html += f"<tr><td>{d}</td><td>{ds}</td><td style='color:#10b981;font-weight:700'>{e}</td><td style='color:#ef4444;font-weight:700'>{u}</td><td>{op}</td></tr>"
                st.markdown(html + "</table>", unsafe_allow_html=True)

elif "Monitoraggio" in menu:
    st.header("📊 Diario Clinico Unificato")
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}", expanded=True):
            log = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            if log:
                html = "<table class='custom-table'><thead><tr><th>Ora</th><th>Profilo</th><th>Nota</th><th>Operatore</th></tr></thead>"
                for d, r, o, n in log:
                    cls = "bg-appuntamento" if "📅" in n else f"bg-{r.lower()}"
                    html += f"<tr><td style='width:140px;'>{d}</td><td style='width:110px;'><span class='badge {cls}'>{r}</span></td><td>{n}</td><td><i>{o}</i></td></tr>"
                st.markdown(html + "</table>", unsafe_allow_html=True)
