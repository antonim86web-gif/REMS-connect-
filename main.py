import sqlite3
import streamlit as st
from datetime import datetime, date
import hashlib

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12.5", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* SIDEBAR PROFESSIONALE */
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

    /* FORM E INPUT SIDEBAR */
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] .stRadio label { color: #ffffff !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] button { 
        background-color: #dc2626 !important; color: white !important; font-weight: 800 !important; 
        border: 2px solid #ffffff !important; border-radius: 10px !important; width: 100% !important; margin-top: 20px; 
    }
    
    /* TABELLE DATI */
    .report-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #cbd5e1; margin-top: 20px; }
    .report-table th { background-color: #1e293b; color: white !important; padding: 12px; text-align: left; border: 1px solid #cbd5e1; }
    .report-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; color: #1e293b; font-size: 0.9rem; border: 1px solid #cbd5e1; }
    
    /* BADGE AGENDA */
    .cat-badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; color: white; }
    .cat-udienza { background-color: #dc2626; } 
    .cat-medica { background-color: #2563eb; }  
    .cat-uscita { background-color: #059669; }  
    .cat-parenti { background-color: #d97706; }

    /* CARD TERAPIA COMPATTA */
    .therapy-row { 
        background: #f8fafc; border: 1px solid #cbd5e1; padding: 10px; border-radius: 8px; 
        margin-bottom: 10px; border-left: 5px solid #1e3a8a;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNZIONI DATABASE ---
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
            st.error(f"Errore DB: {e}")
            return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def mostra_report_settoriale(p_id, ruolo_utente, filtro_nota=None):
    st.write(f"#### 📋 Registro Storico: {ruolo_utente}")
    query = "SELECT data, op, nota FROM eventi WHERE id=? AND ruolo=?"
    params = [p_id, ruolo_utente]
    if filtro_nota:
        query += " AND nota LIKE ?"
        params.append(f"%{filtro_nota}%")
    query += " ORDER BY id_u DESC LIMIT 10"
    
    res = db_run(query, tuple(params))
    if res:
        h = "<table class='report-table'><thead><tr><th>Data/Ora</th><th>Operatore</th><th>Attività</th></tr></thead><tbody>"
        for d, o, nt in res: h += f"<tr><td>{d}</td><td>{o}</td><td>{nt}</td></tr>"
        st.markdown(h + "</tbody></table>", unsafe_allow_html=True)
    else:
        st.info(f"Nessuna attività registrata per {ruolo_utente}.")

# --- LOGICA DI ACCESSO ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>REMS CONNECT ELITE PRO</h2><p>Piattaforma di Gestione Integrata per Equipe Multidisciplinare</p></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Login Operatore", "📝 Registrazione Staff"])
    with t1:
        with st.form("login_form"):
            u_in, p_in = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI AL SISTEMA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_in, hash_pw(p_in)))
                if res:
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Credenziali errate.")
    with t2:
        with st.form("reg_form"):
            nu, np = st.text_input("Scegli Username"), st.text_input("Scegli Password", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Ruolo Professionale", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA NUOVO ACCOUNT"):
                db_run("INSERT INTO utenti (user, pwd, nome, cognome, qualifica) VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True)
                st.success("Account creato con successo! Ora puoi accedere.")
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR NAVIGAZIONE ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"### 👤 {u['nome']} {u['cognome']}")
nav = st.sidebar.radio("NAVIGAZIONE PRINCIPALE", ["📊 Monitoraggio Generale", "👥 Modulo Equipe", "📅 Agenda Appuntamenti", "⚙️ Gestione Sistema"])
if st.sidebar.button("LOGOUT / ESCI"): st.session_state.user_session = None; st.rerun()
st.sidebar.markdown(f"<div class='sidebar-footer'>v12.5.0 ELITE PRO<br>Sviluppato da: <b>AntonioWebMaster</b></div>", unsafe_allow_html=True)

# --- 1. MONITORAGGIO GENERALE ---
if nav == "📊 Monitoraggio Generale":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO INTEGRATO</h2><p>Cronologia Universale Eventi Pazienti</p></div>", unsafe_allow_html=True)
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in pazienti:
        with st.expander(f"📁 CARTELLA CLINICA: {nome.upper()}"):
            evs = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
            if evs:
                h = "<table class='report-table'><thead><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Evento</th></tr></thead><tbody>"
                for d, r, o, nt in evs: h += f"<tr><td>{d}</td><td>{r}</td><td>{o}</td><td>{nt}</td></tr>"
                st.markdown(h + "</tbody></table>", unsafe_allow_html=True)
            else: st.write("Nessun evento registrato.")

# --- 2. MODULO EQUIPE ---
elif nav == "👥 Modulo Equipe":
    st.markdown(f"<div class='section-banner'><h2>AREA OPERATIVA: {u['ruolo'].upper()}</h2><p>Gestione attività e inserimento dati</p></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente in Carico", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        # SEZIONE PSICHIATRA
        if u['ruolo'] == "Psichiatra":
            with st.form("form_psic"):
                st.subheader("📝 Nuova Prescrizione Farmacologica")
                f, d = st.text_input("Nome Farmaco"), st.text_input("Dosaggio (es. 10mg)")
                c1,c2,c3 = st.columns(3)
                m = c1.checkbox("Mattina (MAT)"); p = c2.checkbox("Pomeriggio (POM)"); n = c3.checkbox("Notte (NOT)")
                if st.form_submit_button("CONFERMA E PUBBLICA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📝 Nuova Terapia: {f} {d}", "Psichiatra", firma), True)
                    st.rerun()
            st.write("---")
            mostra_report_settoriale(p_id, "Psichiatra")

        # SEZIONE INFERMIERE
        elif u['ruolo'] == "Infermiere":
            tab_somm, tab_cons, tab_param = st.tabs(["💊 SOMMINISTRAZIONE", "📝 CONSEGNE", "📊 PARAMETRI"])
            
            with tab_somm:
                st.write("### 📋 Piano Terapeutico Giornaliero")
                col_m, col_p, col_n = st.columns(3)
                terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                
                def riga_terapia(tid, farm, dos, turno_txt):
                    st.markdown(f"<div class='therapy-row'><b>{farm}</b> - {dos}</div>", unsafe_allow_html=True)
                    b_ok, b_no = st.columns(2)
                    if b_ok.button("✅ FIRMA", key=f"ok_{tid}_{turno_txt}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMMINISTRATO ({turno_txt}): {farm}", "Infermiere", firma), True); st.rerun()
                    if b_no.button("❌ RIFIUTO", key=f"no_{tid}_{turno_txt}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"⚠️ RIFIUTATA TERAPIA ({turno_txt}): {farm}", "Infermiere", firma), True); st.rerun()

                with col_m:
                    st.markdown("☀️ **MATTINA**")
                    for t in terapie: 
                        if t[3]: riga_terapia(t[0], t[1], t[2], "MAT")
                with col_p:
                    st.markdown("🌤️ **POMERIGGIO**")
                    for t in terapie: 
                        if t[4]: riga_terapia(t[0], t[1], t[2], "POM")
                with col_n:
                    st.markdown("🌙 **NOTTE**")
                    for t in terapie: 
                        if t[5]: riga_terapia(t[0], t[1], t[2], "NOT")
                
                mostra_report_settoriale(p_id, "Infermiere", "SOMMINISTRATO")

            with tab_cons:
                nota_c = st.text_area("Inserisci Consegna Infermieristica")
                if st.button("REGISTRA CONSEGNA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota_c, "Infermiere", firma), True); st.rerun()
                mostra_report_settoriale(p_id, "Infermiere")

            with tab_param:
                with st.form("f_param"):
                    c1, c2, c3 = st.columns(3)
                    p_max = c1.number_input("Pressione MAX", step=1); p_min = c2.number_input("Pressione MIN", step=1); f_c = c3.number_input("Frequenza C.", step=1)
                    if st.form_submit_button("SALVA PARAMETRI VITALI"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"📊 PV - PA: {p_max}/{p_min}, FC: {f_c}", "Infermiere", firma), True); st.rerun()

        # SEZIONE EDUCATORE
        elif u['ruolo'] == "Educatore":
            tab_cassa, tab_diario = st.tabs(["💰 GESTIONE CASSA", "📝 DIARIO RIABILITATIVO"])
            with tab_cassa:
                movimenti = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum([m[0] if m[1] == "Entrata" else -m[0] for m in movimenti])
                st.metric("DISPONIBILITÀ ECONOMICA", f"€ {saldo:.2f}")
                with st.form("f_cassa"):
                    t_mov = st.radio("Tipo Movimento", ["Entrata", "Uscita"], horizontal=True)
                    i_mov = st.number_input("Importo (€)", min_value=0.0, step=0.50)
                    c_mov = st.text_input("Causale (es. Spesa, Acquisto Sigarette)")
                    if st.form_submit_button("REGISTRA MOVIMENTO"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), c_mov, i_mov, t_mov, firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"💰 {t_mov}: €{i_mov} - {c_mov}", "Educatore", firma), True); st.rerun()
                st.write("### 📜 Estratto Conto")
                mostra_tabella_cassa = db_run("SELECT data, causale, importo, tipo, op FROM cassa WHERE p_id=? ORDER BY id_u DESC", (p_id,))
                if mostra_tabella_cassa:
                    h = "<table class='report-table'><thead><tr><th>Data</th><th>Causale</th><th>Euro</th><th>Tipo</th><th>Operatore</th></tr></thead><tbody>"
                    for d, c, i, t, o in mostra_tabella_cassa: h += f"<tr><td>{d}</td><td>{c}</td><td>{i:.2f}</td><td>{t}</td><td>{o}</td></tr>"
                    st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

            with tab_diario:
                nota_e = st.text_area("Nota Diario Educativo")
                if st.button("SALVA NOTA DIARIO"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), nota_e, "Educatore", firma), True); st.rerun()
                mostra_report_settoriale(p_id, "Educatore")

        # SEZIONE OSS
        elif u['ruolo'] == "OSS":
            with st.form("f_oss"):
                st.subheader("🛠️ Registrazione Attività Assistenziale")
                tipo_att = st.selectbox("Attività Svolta", ["Igiene Personale", "Pasto", "Sanificazione Camera", "Accompagnamento", "Controllo Notturno"])
                osservazioni = st.text_area("Osservazioni / Note")
                if st.form_submit_button("REGISTRA ATTIVITÀ OSS"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), f"🛠️ {tipo_att}: {osservazioni}", "OSS", firma), True); st.rerun()
            mostra_report_settoriale(p_id, "OSS")

# --- 3. AGENDA E SCADENZIARIO ---
elif nav == "📅 Agenda Appuntamenti":
    st.markdown("<div class='section-banner'><h2>AGENDA E PIANIFICAZIONE</h2><p>Udienze, Visite Specialistiche e Permessi</p></div>", unsafe_allow_html=True)
    with st.form("f_agenda"):
        c1, c2 = st.columns(2)
        p_sel = c1.selectbox("Paziente", [p[1] for p in db_run("SELECT id, nome FROM pazienti")])
        pid = [p[0] for p in db_run("SELECT id, nome FROM pazienti") if p[1] == p_sel][0]
        data_a = c2.date_input("Data Evento")
        ora_a = c1.text_input("Ora (HH:MM)")
        cat_a = c2.selectbox("Tipo Evento", ["Udienza", "Visita Medica", "Uscita / Permesso", "Incontro Parenti"])
        desc_a = st.text_area("Dettagli Evento")
        if st.form_submit_button("INSERISCI IN AGENDA"):
            db_run("INSERT INTO agenda (p_id, data, ora, categoria, evento) VALUES (?,?,?,?,?)", (pid, data_a.strftime("%d/%m/%Y"), ora_a, cat_a, desc_a), True); st.rerun()
    
    st.write("### 📆 Appuntamenti in Programma")
    apps = db_run("SELECT a.data, a.ora, a.categoria, p.nome, a.evento FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY a.data ASC")
    if apps:
        h = "<table class='report-table'><thead><tr><th>Data/Ora</th><th>Paziente</th><th>Tipo</th><th>Dettagli</th></tr></thead><tbody>"
        for d, o, c, n, e in apps:
            cls = "cat-udienza" if c == "Udienza" else "cat-medica" if c == "Visita Medica" else "cat-uscita" if c == "Uscita / Permesso" else "cat-parenti"
            h += f"<tr><td>{d} {o}</td><td>{n}</td><td><span class='cat-badge {cls}'>{c}</span></td><td>{e}</td></tr>"
        st.markdown(h + "</tbody></table>", unsafe_allow_html=True)

# --- 4. GESTIONE SISTEMA ---
elif nav == "⚙️ Gestione Sistema":
    st.markdown("<div class='section-banner'><h2>CONFIGURAZIONE ANAGRAFICA</h2><p>Inserimento e rimozione pazienti</p></div>", unsafe_allow_html=True)
    with st.form("f_paz"):
        nuovo_p = st.text_input("Inserisci Nome e Cognome nuovo paziente")
        if st.form_submit_button("REGISTRA PAZIENTE"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo_p.upper(),), True); st.rerun()
    
    st.write("### 👥 Pazienti Attualmente Censiti")
    p_tot = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_tot:
        c1, c2 = st.columns([5,1])
        c1.markdown(f"**{nome}** (ID: {pid})")
        if c2.button("Elimina", key=f"del_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True)
            db_run("DELETE FROM eventi WHERE id=?", (pid,), True)
            st.rerun()
