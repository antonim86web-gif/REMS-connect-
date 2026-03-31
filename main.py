import streamlit as st
import sqlite3
from datetime import datetime, date

# --- 1. CONFIGURAZIONE PAGINA E DESIGN CORRETTO (NO GLITCH) ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    /* SFONDO SFUMATO */
    .stApp {
        background: linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 100%);
        background-attachment: fixed;
    }

    /* TITOLO */
    .main-title {
        text-align: center; 
        background: linear-gradient(90deg, #1e3a8a, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.5rem; margin-bottom: 25px;
    }

    /* TABELLE GLASSMORPHISM CON TESTO SCURO E PULITO */
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

    /* CARD INPUT */
    .card-box { 
        background: rgba(255, 255, 255, 0.7); 
        border-radius: 12px; padding: 15px; margin-bottom: 10px; 
        border: 1px solid rgba(255,255,255,0.4);
        color: #1e293b !important;
    }

    /* SIDEBAR CORREZIONE TESTO */
    section[data-testid="stSidebar"] { background-color: #0f172a !important; }
    section[data-testid="stSidebar"] * { color: white !important; }
    
    /* FIX PER EVITARE TESTO BIANCO SU SFONDO CHIARO */
    .stMarkdown, label, p, .stSelectbox label { color: #1e293b !important; }
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
            pwd = st.text_input("Codice Accesso", type="password")
            if st.form_submit_button("ENTRA"):
                if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
st.sidebar.title("🏥 REMS PRO")
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "📅 Appuntamenti", "⚙️ Gestione"])

# --- 5. LOGICA SEZIONI ---

if menu == "📊 Monitoraggio":
    st.header("📊 Diario Clinico Unificato")
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"PAZIENTE: {nome.upper()}", expanded=True):
            log = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            if log:
                html = "<table class='custom-table'><thead><tr><th>Data</th><th>Ruolo</th><th>Op</th><th>Nota</th></tr></thead>"
                for d, r, o, n in log:
                    cls = "bg-appuntamento" if "📅" in n else f"bg-{r.lower()}"
                    html += f"<tr><td>{d}</td><td><span class='badge {cls}'>{r}</span></td><td>{o}</td><td>{n}</td></tr>"
                st.markdown(html + "</table>", unsafe_allow_html=True)

elif menu == "📅 Appuntamenti":
    st.header("📅 Agenda Uscite")
    paz = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if paz:
        p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in paz])
        p_id = [p[0] for p in paz if p[1] == p_nome][0]
        with st.form("f_app"):
            c1,c2,c3 = st.columns(3)
            da, ora, ti = c1.date_input("Data"), c2.time_input("Ora"), c3.selectbox("Tipo", ["Udienza", "Visita", "Permesso"])
            acc = st.text_input("Accompagnatore Incaricato")
            det = st.text_area("Destinazione/Note")
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, tipo, dettagli, scorta) VALUES (?,?,?,?,?,?)", (p_id, da.strftime("%d/%m/%Y"), ora.strftime("%H:%M"), ti, det, acc), True)
                db_run("INSERT INTO eventi (id, data, umore, nota, ruolo, op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📅 {ti}: {det} (Scorta: {acc})", "Sistema", "Agenda"), True); st.rerun()
        
        apps = db_run("SELECT data, ora, tipo, dettagli, scorta, row_id FROM appuntamenti WHERE p_id=? ORDER BY row_id DESC", (p_id,))
        if apps:
            html = "<table class='custom-table'><tr><th>Data/Ora</th><th>Tipo</th><th>Scorta</th><th>Az.</th></tr>"
            for d, o, t, de, sc, rid in apps:
                html += f"<tr><td>{d} {o}</td><td><b>{t}</b></td><td>{sc}</td><td>"
                st.markdown(html, unsafe_allow_html=True)
                if st.button("Elimina", key=f"del_{rid}"): db_run("DELETE FROM appuntamenti WHERE row_id=?", (rid,), True); st.rerun()
                html = ""
            st.markdown("</table>", unsafe_allow_html=True)

elif menu == "👥 Equipe":
    ruolo = st.sidebar.selectbox("Profilo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    paz = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if paz:
        p_nome = st.selectbox("Paziente", [p[1] for p in paz]); p_id = [p[0] for p in paz if p[1] == p_nome][0]
        
        if ruolo == "Psichiatra":
            f_med = st.text_input("Firma Medico")
            with st.form("p_f"):
                c1,c2 = st.columns(2); f,d = c1.text_input("Farmaco"), c2.text_input("Dose")
                m,p,n = st.columns(3); m1,p1,n1 = m.checkbox("M"), p.checkbox("P"), n.checkbox("N")
                if st.form_submit_button("PRESCRIVI"):
                    tu = ",".join([s for s, b in zip(["M","P","N"], [m1,p1,n1]) if b])
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, f, d, tu, f_med, date.today().strftime("%d/%m/%Y")), True); st.rerun()
            ter = db_run("SELECT data_prescr, farmaco, dosaggio, turni, medico FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            if ter:
                html = "<table class='custom-table'><tr><th>Data</th><th>Farmaco</th><th>Dose</th><th>Turni</th><th>Medico</th></tr>"
                for dt, fa, ds, tu, me in ter: html += f"<tr><td>{dt}</td><td><b>{fa}</b></td><td>{ds}</td><td>{tu}</td><td>{me}</td></tr>"
                st.markdown(html + "</table>", unsafe_allow_html=True)

        elif ruolo == "Infermiere":
            f_inf = st.text_input("Firma Infermiere")
            tab1, tab2, tab3 = st.tabs(["💊 Farmaci", "📊 Parametri", "📝 Consegne"])
            with tab1:
                turno = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
                terapie = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
                acc, rif = [], []
                for f, d, tu_p, rid in terapie:
                    if tu_p and turno[0] in tu_p:
                        col1, col2, col3 = st.columns([3,1,1])
                        col1.write(f"**{f}** ({d})")
                        if col2.checkbox("✔️", key=f"a_{rid}"): acc.append(f"{f} ({d})")
                        if col3.checkbox("❌", key=f"r_{rid}"): rif.append(f"{f} ({d})")
                if st.button("REGISTRA SOMMINISTRAZIONE"):
                    if f_inf and (acc or rif):
                        nota = f"💊 [{turno[0]}] Assunti: {', '.join(acc)} | Rifiutati: {', '.join(rif)}"
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", nota, "Infermiere", f_inf), True); st.rerun()
            with tab2:
                with st.form("pv"):
                    c1,c2,c3,c4 = st.columns(4); pa,fc,sa,tc = c1.text_input("PA"), c2.number_input("FC"), c3.number_input("SpO2"), c4.number_input("TC", 34.0, 42.0, 36.5)
                    if st.form_submit_button("SALVA PV"):
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📊 PA:{pa} FC:{fc} SpO2:{sa}% TC:{tc}", "Infermiere", f_inf), True); st.rerun()
            with tab3:
                txt = st.text_area("Nota")
                if st.button("SALVA NOTA"):
                    if f_inf and txt: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📝 {txt}", "Infermiere", f_inf), True); st.rerun()

        elif ruolo == "Educatore":
            f_ed = st.text_input("Firma Educatore")
            mov = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            st.metric("CASSA", f"€ {sum([m[2] if m[3] == 'Entrata' else -m[2] for m in mov]):.2f}")
            with st.form("cassa"):
                tp, im, ds = st.radio("Tipo", ["Entrata", "Uscita"]), st.number_input("Importo"), st.text_input("Causale")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tp, f_ed), True); st.rerun()
            if mov:
                html = "<table class='custom-table'><tr><th>Data</th><th>Causale</th><th>E</th><th>U</th><th>Op</th></tr>"
                for d, ds, im, tp, op in mov:
                    e, u = (f"€ {im:.2f}", "") if tp == "Entrata" else ("", f"€ {im:.2f}")
                    html += f"<tr><td>{d}</td><td>{ds}</td><td style='color:green'>{e}</td><td style='color:red'>{u}</td><td>{op}</td></tr>"
                st.markdown(html + "</table>", unsafe_allow_html=True)

        elif ruolo == "OSS":
            f_oss = st.text_input("Firma OSS")
            m1, m2, m3 = st.checkbox("Camera"), st.checkbox("Refettorio"), st.checkbox("Bagno")
            if st.button("REGISTRA PULIZIE"):
                sel = [t for b,t in zip([m1,m2,m3], ["Camera","Refettorio","Bagno"]) if b]
                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"🧹 Pulizie: {', '.join(sel)}", "OSS", f_oss), True); st.rerun()

elif menu == "⚙️ Gestione":
    st.header("Anagrafica")
    nuovo = st.text_input("Nuovo Paziente")
    if st.button("AGGIUNGI"):
        if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), True); st.rerun()
    for idx, nome in db_run("SELECT id, nome FROM pazienti"):
        st.write(f"ID: {idx} - **{nome}**")
