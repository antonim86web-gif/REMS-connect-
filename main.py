import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="REMS Connect ELITE PRO v28.9.3", layout="wide", page_icon="🏥")

# --- DATABASE ENGINE & MIGRATION ---
DB_NAME = "rems_final_v12.db"

def inizializza_db():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        # Tabelle Base
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, stato TEXT DEFAULT 'ATTIVO')")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY AUTOINCREMENT, id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, is_prn INTEGER DEFAULT 0, medico TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT, tipo_evento TEXT, mezzo TEXT, accompagnatore TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS logs_sistema (id_log INTEGER PRIMARY KEY AUTOINCREMENT, data_ora TEXT, utente TEXT, azione TEXT, dettaglio TEXT)")
        
        # Migrazione: Aggiunta colonna is_prn (TAB) se non esiste
        try: cur.execute("ALTER TABLE terapie ADD COLUMN is_prn INTEGER DEFAULT 0")
        except: pass
        
        # Utente Admin Default
        if cur.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
            pw_admin = hashlib.sha256("perito2026".encode()).hexdigest()
            cur.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", pw_admin, "SUPER", "USER", "Admin"))
        
        # Inizializzazione Stanze
        if cur.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
            for i in range(1, 7): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"A{i}", "A", "ISOLAMENTO" if i==6 else "STANDARD"))
            for i in range(1, 11): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"B{i}", "B", "ISOLAMENTO" if i==10 else "STANDARD"))
        conn.commit()

inizializza_db()

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        try:
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}")
            return []

# --- UTILS ---
def get_now_it(): return datetime.now(timezone.utc) + timedelta(hours=2)

def scrivi_log(azione, dettaglio):
    user_log = st.session_state.user_session['uid'] if 'user_session' in st.session_state and st.session_state.user_session else "SISTEMA"
    db_run("INSERT INTO logs_sistema (data_ora, utente, azione, dettaglio) VALUES (?,?,?,?)", 
           (get_now_it().strftime("%d/%m/%Y %H:%M:%S"), user_log, azione, dettaglio), True)

# --- CSS PERSONALIZZATO ---
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    .sidebar-title { font-size: 1.8rem; font-weight: 800; text-align: center; border-bottom: 2px solid #ffffff33; padding-bottom: 10px; }
    .user-logged { color: #00ff00 !important; font-weight: 900; text-align: center; margin: 15px 0; }
    .section-banner { background: #1e3a8a; color: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
    .postit { padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 8px solid; background: #f8fafc; color: #1e293b; font-size: 0.9rem; }
    .role-psichiatra { border-color: #dc2626; background: #fef2f2; }
    .role-infermiere { border-color: #2563eb; background: #eff6ff; }
    .role-educatore { border-color: #059669; background: #ecfdf5; }
    .role-opsi { border-color: #0f172a; background: #f1f5f9; }
    .firma-a { color: #166534; font-weight: 900; font-size: 1.2rem; }
    .firma-r { color: #991b1b; font-weight: 900; font-size: 1.2rem; }
    .cal-table { width:100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; }
    .cal-table th { background: #1e3a8a; color: white; padding: 8px; font-size: 0.8rem; }
    .cal-table td { border: 1px solid #e2e8f0; height: 100px; vertical-align: top; padding: 5px; }
    .event-tag-html { font-size: 0.7rem; background: #dbeafe; padding: 2px; margin-top: 2px; border-radius: 3px; border-left: 3px solid #2563eb; }
</style>
""", unsafe_allow_html=True)

# --- LOGICA DI FIRMA RAPIDA ---
def render_firma_rapida(col_obj, f_id, f_nome, turno, p_id, p_nome, firma_op, oggi):
    check = db_run("SELECT nota FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                   (p_id, f"%SOMM ({turno}): {f_nome}%", f"{oggi}%"))
    if check:
        esito = check[0][0].split("|")[-1].strip()
        color_cls = "firma-a" if esito == "A" else "firma-r"
        col_obj.markdown(f"<div class='{color_cls}'>{esito}</div>", unsafe_allow_html=True)
    else:
        c_a, c_r = col_obj.columns(2)
        if c_a.button("A", key=f"A_{f_id}_{turno}_{p_id}"):
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                   (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({turno}): {f_nome} | A", "Infermiere", firma_op), True)
            st.rerun()
        if c_r.button("R", key=f"R_{f_id}_{turno}_{p_id}"):
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                   (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({turno}): {f_nome} | R", "Infermiere", firma_op), True)
            st.rerun()

def render_postits(p_id):
    res = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 50", (p_id,))
    for d, r, o, nt in res:
        role_cls = f"role-{r.lower().replace(' ', '')}"
        st.markdown(f"<div class='postit {role_cls}'><b>{o} ({r})</b> - <small>{d}</small><br>{nt}</div>", unsafe_allow_html=True)

# --- SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if 'cal_month' not in st.session_state: st.session_state.cal_month = get_now_it().month
if 'cal_year' not in st.session_state: st.session_state.cal_year = get_now_it().year

# --- LOGIN / REGISTRAZIONE ---
if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h1>🏥 REMS CONNECT PRO</h1></div>", unsafe_allow_html=True)
    l, r = st.columns(2)
    with l:
        with st.form("login"):
            st.subheader("Login")
            u_i = st.text_input("User").lower().strip()
            p_i = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hashlib.sha256(p_i.encode()).hexdigest()))
                if res:
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_i}
                    scrivi_log("LOGIN", "Accesso eseguito")
                    st.rerun()
                else: st.error("Credenziali errate")
    with r:
        with st.form("reg"):
            st.subheader("Registrazione")
            ru = st.text_input("Nuovo User").lower().strip()
            rp = st.text_input("Nuova Password", type="password")
            rn = st.text_input("Nome")
            rc = st.text_input("Cognome")
            rq = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
            if st.form_submit_button("REGISTRA"):
                if ru and rp:
                    db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (ru, hashlib.sha256(rp.encode()).hexdigest(), rn, rc, rq), True)
                    st.success("Registrato! Ora accedi.")
    st.stop()

# --- SIDEBAR NAV ---
u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"
oggi_iso = get_now_it().strftime("%Y-%m-%d")
oggi_it = get_now_it().strftime("%d/%m/%Y")

st.sidebar.markdown(f"<div class='sidebar-title'>REMS Connect</div><div class='user-logged'>● {u['nome']} {u['cognome']}</div>", unsafe_allow_html=True)
nav = st.sidebar.radio("MENU", ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda", "🗺️ Mappa", "⚙️ Admin"])
if st.sidebar.button("LOGOUT"):
    st.session_state.user_session = None
    st.rerun()

# --- MODULO EQUIPE (IL CUORE) ---
if nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>OPERATIVITÀ EQUIPE</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    if p_lista:
        p_sel_nome = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel_nome][0]
        
        # Ruolo Corrente (Simulazione per Admin)
        ruolo_effettivo = st.selectbox("Agisci come:", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"]) if u['ruolo']=="Admin" else u['ruolo']

        if ruolo_effettivo == "Psichiatra":
            t1, t2 = st.tabs(["➕ Nuova Prescrizione", "🩺 Diario Medico"])
            with t1:
                with st.form("presc"):
                    f = st.text_input("Farmaco")
                    d = st.text_input("Dose")
                    c1,c2,c3,c4 = st.columns(4)
                    m_f, p_f, n_f, tsu_f = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT"), c4.checkbox("TAB (TSU)")
                    if st.form_submit_button("SALVA PRESCRIZIONE"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, is_prn, medico) VALUES (?,?,?,?,?,?,?,?)", 
                               (p_id, f, d, int(m_f), int(p_f), int(n_f), int(tsu_f), firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"➕ Prescrizione: {f} {d}", "Psichiatra", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("nota_m"):
                    txt = st.text_area("Nota Clinica")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🩺 {txt}", "Psichiatra", firma_op), True)
                        st.rerun()

        elif ruolo_effettivo == "Infermiere":
            t1, t2 = st.tabs(["💊 SOMMINISTRAZIONE", "💓 PARAMETRI"])
            with t1:
                st.markdown("### Registro Terapie")
                # Tabella 5 colonne: Farmaco, MAT, POM, NOT, TAB
                h1, h2, h3, h4, h5 = st.columns([2.5, 1, 1, 1, 1])
                h1.caption("FARMACO")
                h2.caption("MAT")
                h3.caption("POM")
                h4.caption("NOT")
                h5.caption("TAB")
                st.divider()
                
                terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott, is_prn FROM terapie WHERE p_id=?", (p_id,))
                for f in terapie:
                    c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 1])
                    c1.markdown(f"**{f[1]}**<br><small>{f[2]}</small>", unsafe_allow_html=True)
                    # Loop Turni (MAT, POM, NOT)
                    for i, t_nome in enumerate(["MAT", "POM", "NOT"]):
                        col_t = [c2, c3, c4][i]
                        if f[i+3]: render_firma_rapida(col_t, f[0], f[1], t_nome, p_id, p_sel_nome, firma_op, oggi_it)
                        else: col_t.write("-")
                    # Colonna TAB
                    if f[6]: render_firma_rapida(c5, f[0], f[1], "TAB", p_id, p_sel_nome, firma_op, oggi_it)
                    else: c5.write("-")

            with t2:
                with st.form("par"):
                    pa, fc, sat = st.text_input("PA"), st.text_input("FC"), st.text_input("SatO2")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"💓 PA:{pa} FC:{fc} Sat:{sat}", "Infermiere", firma_op), True)
                        st.rerun()

        elif ruolo_effettivo == "Educatore":
            t1, t2 = st.tabs(["💰 CASSA", "📝 NOTA EDUCATIVA"])
            with t1:
                mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
                st.metric("Saldo Cassa", f"{saldo:.2f} €")
                with st.form("cs"):
                    tp, im, cau = st.selectbox("Tipo", ["ENTRATA", "USCITA"]), st.number_input("€"), st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, oggi_it, cau, im, tp, firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"💰 {tp}: {im}€ - {cau}", "Educatore", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("edu"):
                    txt = st.text_area("Osservazione Educativa")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"📝 {txt}", "Educatore", firma_op), True)
                        st.rerun()

        st.divider()
        st.subheader("Storico Recente")
        render_postits(p_id)

# --- ALTRI MODULI (AGENDA, MAPPA, ADMIN) ---
elif nav == "📅 Agenda":
    st.markdown("<div class='section-banner'><h2>AGENDA DINAMICA</h2></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    if c1.button("⬅️ Precedente"): st.session_state.cal_month -= 1
    if c3.button("Successivo ➡️"): st.session_state.cal_month += 1
    
    cal = calendar.Calendar(firstweekday=0)
    days = cal.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month)
    
    # Visualizzazione semplificata per brevità ma completa logica
    st.write(f"Mese: {st.session_state.cal_month} / {st.session_state.cal_year}")
    with st.form("app"):
        st.subheader("Nuovo Appuntamento")
        pa_sel = st.selectbox("Paziente", [p[1] for p in db_run("SELECT nome FROM pazienti WHERE stato='ATTIVO'")])
        pid_a = db_run("SELECT id FROM pazienti WHERE nome=?", (pa_sel,))[0][0]
        dt_a, hr_a, nt_a = st.date_input("Data"), st.time_input("Ora"), st.text_input("Cosa")
        if st.form_submit_button("REGISTRA"):
            db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, stato) VALUES (?,?,?,?,'PROGRAMMATO')", (pid_a, str(dt_a), str(hr_a)[:5], nt_a), True)
            st.rerun()

elif nav == "🗺️ Mappa":
    st.markdown("<div class='section-banner'><h2>MAPPA POSTI LETTO</h2></div>", unsafe_allow_html=True)
    stanze = db_run("SELECT id, reparto FROM stanze")
    for r in ["A", "B"]:
        st.subheader(f"REPARTO {r}")
        cols = st.columns(5)
        r_stanze = [s for s in stanze if s[1] == r]
        for i, s in enumerate(r_stanze):
            with cols[i % 5]:
                st.info(f"Stanza {s[0]}")
                paz = db_run("SELECT p.nome FROM pazienti p JOIN assegnazioni a ON p.id=a.p_id WHERE a.stanza_id=?", (s[0],))
                for p in paz: st.write(f"👤 {p[0]}")

elif nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>MONITORAGGIO GENERALE</h2></div>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome"):
        with st.expander(f"📁 SCHEDA: {nome}"):
            render_postits(pid)

elif nav == "⚙️ Admin":
    st.markdown("<div class='section-banner'><h2>PANNELLO AMMINISTRAZIONE</h2></div>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["Utenti", "Pazienti", "Log Sistema"])
    with t1:
        st.write(pd.DataFrame(db_run("SELECT user, nome, cognome, qualifica FROM utenti"), columns=["User", "Nome", "Cognome", "Ruolo"]))
    with t2:
        with st.form("add_p"):
            n_p = st.text_input("Nuovo Paziente (Nome Cognome)")
            if st.form_submit_button("AGGIUNGI"):
                db_run("INSERT INTO pazienti (nome) VALUES (?)", (n_p.upper(),), True)
                st.rerun()
    with t3:
        st.dataframe(pd.DataFrame(db_run("SELECT * FROM logs_sistema ORDER BY id_log DESC LIMIT 100")), use_container_width=True)

# --- FOOTER ---
st.sidebar.markdown(f"<br><br><small>v28.9.3 Elite | Antony Perito</small>", unsafe_allow_html=True)
