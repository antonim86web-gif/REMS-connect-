import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12.5", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* SIDEBAR BLU ISTITUZIONALE */
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    .sidebar-title { 
        color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; 
        text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; 
    }
    .sidebar-footer { 
        position: fixed; bottom: 10px; left: 10px; color: #ffffff99 !important; 
        font-size: 0.75rem !important; line-height: 1.2; z-index: 100; 
    }
    
    /* BANNER SEZIONI */
    .section-banner { 
        background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; 
        margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); 
    }
    .section-banner h2 { color: white !important; margin: 0; font-weight: 800; text-transform: uppercase; }
    .section-banner p { margin: 8px 0 0 0; opacity: 0.9; font-size: 1.1rem; font-style: italic; }

    /* MENU SIDEBAR */
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] .stRadio label { color: #ffffff !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] button { 
        background-color: #dc2626 !important; color: white !important; font-weight: 800 !important; 
        border: 2px solid #ffffff !important; border-radius: 10px !important; width: 100% !important; margin-top: 20px; 
    }
    
    /* TABELLE PROFESSIONALI */
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; margin-top: 20px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 12px; text-align: left; border: 1px solid #cbd5e1; font-weight: 700; }
    .report-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; color: #1e293b; font-size: 0.9rem; border: 1px solid #cbd5e1; }
    
    /* BADGE AGENDA */
    .cat-badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; color: white; text-transform: uppercase; }
    .cat-udienza { background-color: #dc2626; } 
    .cat-medica { background-color: #2563eb; }  
    .cat-uscita { background-color: #059669; }  
    .cat-parenti { background-color: #d97706; }

    /* CARD TERAPIA ULTRA COMPATTA */
    .therapy-card { 
        background: #ffffff; border: 1px solid #cbd5e1; padding: 10px; border-radius: 6px; 
        margin-bottom: 8px; border-left: 4px solid #1e3a8a; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .therapy-card b { color: #1e3a8a; font-size: 0.95rem; }
    .therapy-card small { color: #475569; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- MOTORE DATABASE ---
DB_NAME = "rems_final_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, categoria TEXT, evento TEXT, stato TEXT)")
        try:
            if query: cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore Critico Database: {e}")
            return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def mostra_report_settoriale(p_id, ruolo_utente, filtro_parola=None):
    st.write(f"#### 📋 Registro Storico: {ruolo_utente}")
    query = "SELECT data, op, nota FROM eventi WHERE id=? AND ruolo=?"
    params = [p_id, ruolo_utente]
    if filtro_parola:
        query += " AND nota LIKE ?"
        params.append(f"%{filtro_parola}%")
    query += " ORDER BY id_u DESC LIMIT 10"
    
    res = db_run(query, tuple(params))
    if res:
        h = "<table class='report-table'><thead><tr><th>Data/Ora</th><th>Operatore</th><th>Attività / Nota</th></tr></thead><tbody>"
        for d, o, nt in res: h += f"<tr><td>{d}</td><td>{o}</td><td>{nt}</td></tr>"
        st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- GESTIONE SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>REMS CONNECT ELITE PRO</h2><p>Piattaforma Gestionale - AntonioWebMaster</p></div>", unsafe_allow_html=True)
    t_login, t_reg = st.tabs(["🔐 Accesso Staff", "📝 Registrazione"])
    with t_login:
        with st.form("login_form"):
            u_in, p_in = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("AUTENTICA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res:
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Accesso Negato.")
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
nav = st.sidebar.radio("MODULI", ["📊 Monitoraggio Generale", "👥 Modulo Equipe", "📅 Agenda Appuntamenti", "⚙️ Gestione Sistema"])
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()
st.sidebar.markdown(f"<div class='sidebar-footer'>Created by: <b>AntonioWebMaster</b></div>", unsafe_allow_html=True)

# --- 1. MONITORAGGIO ---
if nav == "📊 Monitoraggio Generale":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO</h2></div>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"📁 CARTELLA: {nome.upper()}"):
            mostra_report_settoriale(pid, "Psichiatra")
            mostra_report_settoriale(pid, "Infermiere")
            mostra_report_settoriale(pid, "Educatore")
            mostra_report_settoriale(pid, "OSS")

# --- 2. MODULO EQUIPE ---
elif nav == "👥 Modulo Equipe":
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        if u['ruolo'] == "Psichiatra":
            with st.form("f_ps"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1,c2,c3 = st.columns(3); m=c1.checkbox("MAT"); p=c2.checkbox("POM"); n=c3.checkbox("NOT")
                if st.form_submit_button("PRESCRIVI"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📝 Prescritto: {f} {d}", "Psichiatra", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "Psichiatra")

        elif u['ruolo'] == "Infermiere":
            t_somm, t_cons, t_pv = st.tabs(["💊 SOMMINISTRAZIONE RAPIDA", "📝 CONSEGNE", "📊 PARAMETRI"])
            with t_somm:
                st.markdown("### 🗓️ Piano Terapeutico del Giorno")
                ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                col_m, col_p, col_n = st.columns(3)
                
                def riga_rapida(tid, farm, dos, turno):
                    st.markdown(f"<div class='therapy-card'><b>{farm}</b><br><small>{dos}</small></div>", unsafe_allow_html=True)
                    c_ok, c_no = st.columns(2)
                    if c_ok.button("✅", key=f"ok_{tid}_{turno}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({turno}): {farm}", "Infermiere", firma), True); st.rerun()
                    if c_no.button("❌", key=f"no_{tid}_{turno}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"⚠️ RIFIUTO ({turno}): {farm}", "Infermiere", firma), True); st.rerun()

                with col_m: st.subheader("☀️ MAT"); [riga_rapida(t[0], t[1], t[2], "MAT") for t in ter if t[3]]
                with col_p: st.subheader("🌤️ POM"); [riga_rapida(t[0], t[1], t[2], "POM") for t in ter if t[4]]
                with col_n: st.subheader("🌙 NOT"); [riga_rapida(t[0], t[1], t[2], "NOT") for t in ter if t[5]]
                
                st.write("---")
                mostra_report_settoriale(p_id, "Infermiere", "SOMM")

            with t_cons:
                nota_c = st.text_area("Nota di Consegna")
                if st.button("SALVA CONSEGNA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota_c, "Infermiere", firma), True); st.rerun()
                mostra_report_settoriale(p_id, "Infermiere")
            
            with t_pv:
                with st.form("pv_f"):
                    cx, cn, cf = st.columns(3); mx=cx.number_input("PA Max"); mn=cn.number_input("PA Min"); fc=cf.number_input("FC")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📊 PV - PA: {mx}/{mn}, FC: {fc}", "Infermiere", firma), True); st.rerun()

        elif u['ruolo'] == "Educatore":
            t_cash, t_diary = st.tabs(["💰 CASSA", "📝 DIARIO"])
            with t_cash:
                movs = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum([m[0] if m[1] == "Entrata" else -m[0] for m in movs])
                st.metric("SALDO", f"€ {saldo:.2f}")
                with st.form("f_c"):
                    tm = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True); im = st.number_input("Euro"); cm = st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), cm, im, tm, firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"💰 {tm}: €{im} - {cm}", "Educatore", firma), True); st.rerun()
                st.write("#### Storico Movimenti")
                res_c = db_run("SELECT data, causale, importo, tipo FROM cassa WHERE p_id=? ORDER BY id_u DESC", (p_id,))
                if res_c: st.table(res_c)
            with t_diary:
                nota_e = st.text_area("Nota")
                if st.button("SALVA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota_e, "Educatore", firma), True); st.rerun()
                mostra_report_settoriale(p_id, "Educatore")

        elif u['ruolo'] == "OSS":
            with st.form("f_oss"):
                att = st.selectbox("Attività", ["Igiene", "Pasto", "Sanificazione", "Controllo"]); obs = st.text_area("Note")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"🛠️ {att}: {obs}", "OSS", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "OSS")

# --- 3. AGENDA ---
elif nav == "📅 Agenda Appuntamenti":
    st.markdown("<div class='section-banner'><h2>AGENDA REMS</h2></div>", unsafe_allow_html=True)
    with st.form("f_ag"):
        p_sel = st.selectbox("Paziente", [p[1] for p in db_run("SELECT id, nome FROM pazienti")])
        pid = [p[0] for p in db_run("SELECT id, nome FROM pazienti") if p[1] == p_sel][0]
        c1, c2 = st.columns(2); d_ag = c1.date_input("Data"); o_ag = c2.text_input("Ora (HH:MM)"); cat_ag = st.selectbox("Tipo", ["Udienza", "Visita Medica", "Uscita / Permesso", "Incontro Parenti"]); desc_ag = st.text_area("Dettagli")
        if st.form_submit_button("INSERISCI"):
            db_run("INSERT INTO agenda (p_id, data, ora, categoria, evento) VALUES (?,?,?,?,?)", (pid, d_ag.strftime("%d/%m/%Y"), o_ag, cat_ag, desc_ag), True); st.rerun()
    apps = db_run("SELECT a.data, a.ora, a.categoria, p.nome, a.evento FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY a.data ASC")
    if apps:
        h = "<table class='report-table'><thead><tr><th>Data</th><th>Paziente</th><th>Tipo</th><th>Note</th></tr></thead><tbody>"
        for d, o, c, n, e in apps:
            cls = "cat-udienza" if c == "Udienza" else "cat-medica" if c == "Visita Medica" else "cat-uscita" if c == "Uscita / Permesso" else "cat-parenti"
            h += f"<tr><td>{d} {o}</td><td>{n}</td><td><span class='cat-badge {cls}'>{c}</span></td><td>{e}</td></tr>"
        st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- 4. GESTIONE ---
elif nav == "⚙️ Gestione Sistema":
    st.markdown("<div class='section-banner'><h2>GESTIONE ANAGRAFICA</h2></div>", unsafe_allow_html=True)
    with st.form("f_paz"):
        np = st.text_input("Nuovo paziente")
        if st.form_submit_button("REGISTRA"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    lista_p = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in lista_p:
        c1, c2 = st.columns([6,1])
        c1.markdown(f"**{nome}** (ID: {pid})")
        if c2.button("Elimina", key=f"del_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
