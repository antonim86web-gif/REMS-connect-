import
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calenda
import io

# --- CONFIGURAZIONE DI SISTEMA ELITE PRO ---
DB_NAME = "rems_final_v12.db"
st.set_page_config(page_title="REMS Connect ELITE PRO v28.9.2", layout="wide", page_icon="🏥")

# --- DATABASE ENGINE INTEGRALE ---
def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        try:
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore Critico Database: {e}")
            return []

def inizializza_db_completo():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Struttura Tabelle Senza Omissioni
        c.execute("""CREATE TABLE IF NOT EXISTS utenti (
            user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS pazienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, 
            stato TEXT DEFAULT 'ATTIVO', data_ingesso TEXT, provenienza TEXT)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS eventi (
            id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, 
            id_u INTEGER PRIMARY KEY AUTOINCREMENT, esito TEXT)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS terapie (
            p_id INTEGER, farmaco TEXT, dose TEXT, 
            mat_nuovo INTEGER DEFAULT 0, pom_nuovo INTEGER DEFAULT 0, al_bisogno INTEGER DEFAULT 0,
            medico TEXT, data_prescrizione TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS cassa (
            p_id INTEGER, data TEXT, causale TEXT, importo REAL, 
            tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS appuntamenti (
            id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, 
            nota TEXT, stato TEXT, autore TEXT, mezzo TEXT, accompagnatore TEXT)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS stanze (
            id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT, posti INTEGER DEFAULT 2)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS assegnazioni (
            p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS logs_sistema (
            id_log INTEGER PRIMARY KEY AUTOINCREMENT, data_ora TEXT, 
            utente TEXT, azione TEXT, dettaglio TEXT)""")
        
        # Dati Iniziali Obbligatori
        if c.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
            c.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", 
                     ("admin", hashlib.sha256(str.encode("perito2026")).hexdigest(), "SUPER", "USER", "Admin"))
        
        if c.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
            for r in ["A", "B"]:
                lim = 7 if r == "A" else 11
                for i in range(1, lim):
                    t = "ISOLAMENTO" if (r=="A" and i==6) or (r=="B" and i==10) else "STANDARD"
                    c.execute("INSERT INTO stanze VALUES (?,?,?,?)", (f"{r}{i}", r, t, 2))
        conn.commit()

inizializza_db_completo()

def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

def scrivi_log(azione, dettaglio):
    user = st.session_state.user_session['uid'] if st.session_state.user_session else "SISTEMA"
    db_run("INSERT INTO logs_sistema (data_ora, utente, azione, dettaglio) VALUES (?,?,?,?)",
           (get_now_it().strftime("%d/%m/%Y %H:%M:%S"), user, azione, dettaglio), True)

# --- CSS PROFESSIONALE INTEGRALE (NON MODIFICATO) ---
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; min-width: 300px !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; border-bottom: 2px solid #ffffff33; padding-bottom: 10px; }
    .user-logged { color: #00ff00 !important; font-weight: 900; text-align: center; margin-bottom: 20px; border: 1px solid #00ff0033; padding: 5px; border-radius: 5px; }
    
    .section-banner { background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%); color: white !important; padding: 30px; border-radius: 15px; margin-bottom: 30px; text-align: center; box-shadow: 0 10px 20px rgba(0,0,0,0.2); }
    
    .scroll-giorni { display: flex; overflow-x: auto; gap: 5px; padding: 12px; background: #f1f5f9; border-radius: 10px; border: 1px solid #cbd5e1; margin-bottom: 15px; }
    .quadratino { 
        min-width: 55px; height: 75px; border-radius: 8px; border: 1px solid #94a3b8; 
        display: flex; flex-direction: column; align-items: center; justify-content: center; flex-shrink: 0; background: white; transition: all 0.2s;
    }
    .q-oggi { border: 3px solid #1e3a8a !important; background: #fffde7 !important; transform: scale(1.05); z-index: 10; }
    .q-num { font-size: 10px; color: #475569; font-weight: 900; margin-top: -4px; }
    .q-esito { font-size: 18px; font-weight: 900; margin: 2px 0; }
    .q-op { font-size: 8px; color: #1e3a8a; text-align: center; font-weight: 700; text-transform: uppercase; line-height: 1; }

    .postit { padding: 18px; border-radius: 10px; margin-bottom: 15px; border-left: 12px solid; box-shadow: 0 4px 6px rgba(0,0,0,0.05); background: white; }
    .postit-header { font-weight: 800; font-size: 0.9rem; margin-bottom: 8px; display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .role-psichiatra { border-color: #dc2626; background-color: #fef2f2; } 
    .role-infermiere { border-color: #2563eb; background-color: #eff6ff; } 
    .role-educatore { border-color: #059669; background-color: #ecfdf5; }  
    .role-oss { border-color: #64748b; background-color: #f8fafc; }
    .role-psicologo { border-color: #a855f7; background-color: #faf5ff; }
    .role-sociale { border-color: #f97316; background-color: #fff7ed; }
    .role-opsi { border-color: #0f172a; background-color: #f1f5f9; border-style: dashed; }

    .cassa-card { background: #f0fdf4; border: 2px solid #16a34a; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(22,163,74,0.1); }
    .saldo-txt { font-size: 3rem; font-weight: 900; color: #15803d; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }
    
    .stanza-tile { background: white; border: 1px solid #cbd5e1; border-radius: 12px; padding: 15px; border-left: 8px solid #94a3b8; margin-bottom: 12px; transition: transform 0.2s; }
    .stanza-tile:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
    .stanza-occupata { border-left-color: #22c55e; background-color: #f0fdf4; }
    .stanza-piena { border-left-color: #2563eb; background-color: #eff6ff; }
    .stanza-isolamento { border-left-color: #ef4444; border-width: 2px; }
</style>
""", unsafe_allow_html=True)

# --- GESTIONE ACCESSO ---
if 'user_session' not in st.session_state:
    st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h1>🏥 REMS CONNECT ELITE v28.9.2</h1><p>Sistema Gestionale Integrato per Residenze per l'Esecuzione delle Misure di Sicurezza</p></div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔑 Accesso Operatore")
        with st.form("login_form"):
            u_i = st.text_input("Username").lower().strip()
            p_i = st.text_input("Password", type="password")
            if st.form_submit_button("ENTRA NEL SISTEMA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", 
                            (u_i, hashlib.sha256(str.encode(p_i)).hexdigest()))
                if res:
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_i}
                    scrivi_log("LOGIN", "Accesso autorizzato")
                    st.rerun()
                else: st.error("Credenziali non valide.")
    with col2:
        st.subheader("📝 Registrazione Nuovo Staff")
        with st.form("reg_form"):
            ru = st.text_input("Nuovo Username")
            rp = st.text_input("Scegli Password", type="password")
            rn = st.text_input("Nome")
            rc = st.text_input("Cognome")
            rq = st.selectbox("Qualifica Professionale", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
            if st.form_submit_button("CREA ACCOUNT"):
                if ru and rp:
                    db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", 
                          (ru.lower(), hashlib.sha256(str.encode(rp)).hexdigest(), rn, rc, rq), True)
                    st.success("Account creato con successo!")
    st.stop()

# --- DATI OPERATORE ATTIVO ---
u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"
sigla_op = f"{u['nome'][0].upper()}{u['cognome'][0].upper()}"
oggi_iso = get_now_it().strftime("%Y-%m-%d")
oggi_it = get_now_it().strftime("%d/%m/%Y")

# --- SIDEBAR DI NAVIGAZIONE COMPLETA ---
st.sidebar.markdown(f"<div class='sidebar-title'>REMS-CONNECT</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-logged'>● {u['nome']} {u['cognome']}<br><small>{u['ruolo']}</small></div>", unsafe_allow_html=True)

nav = st.sidebar.radio("MODULI GESTIONALI", [
    "📊 Diario Clinico", 
    "👥 Modulo Equipe", 
    "🗺️ Posti Letto", 
    "📅 Agenda & Scadenze",
    "⚙️ Amministrazione"
])

if st.sidebar.button("🔴 ESCI DAL SISTEMA"):
    scrivi_log("LOGOUT", "Uscita volontaria")
    st.session_state.user_session = None
    st.rerun()

st.sidebar.markdown(f"""
<div style='margin-top:50px; border-top:1px solid #ffffff33; padding-top:20px; font-size:0.7rem; opacity:0.6; text-align:center;'>
    Sviluppato da: <b>Antony</b><br>
    Rems Connect ELITE PRO<br>
    Build: 2026.04.03.v28
</div>
""", unsafe_allow_html=True)

# --- 1. MODULO DIARIO CLINICO (VISUALIZZAZIONE) ---
if nav == "📊 Diario Clinico":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO INTEGRATO</h2><p>Cronologia completa degli eventi e delle annotazioni per paziente</p></div>", unsafe_allow_html=True)
    
    pazienti = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    if not pazienti:
        st.info("Nessun paziente attivo a sistema.")
    else:
        p_nomi = [p[1] for p in pazienti]
        sel_p = st.selectbox("Seleziona Cartella Paziente", p_nomi)
        p_id = [p[0] for p in pazienti if p[1] == sel_p][0]
        
        col_f1, col_f2 = st.columns([2, 1])
        with col_f2:
            st.write("### Filtri")
            ruoli = ["Tutti", "Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"]
            f_ruolo = st.multiselect("Filtra per Ruolo", ruoli, default="Tutti")
        
        with col_f1:
            st.write(f"### Eventi Recenti: {sel_p}")
            query = "SELECT data, ruolo, op, nota FROM eventi WHERE id=?"
            params = [p_id]
            if "Tutti" not in f_ruolo and f_ruolo:
                query += f" AND ruolo IN ({','.join(['?']*len(f_ruolo))})"
                params.extend(f_ruolo)
            
            eventi = db_run(query + " ORDER BY id_u DESC LIMIT 100", tuple(params))
            
            for d, r, o, nt in eventi:
                r_cls = r.lower().replace(" ", "")
                st.markdown(f"""
                <div class='postit role-{r_cls}'>
                    <div class='postit-header'>
                        <span>👤 {o}</span>
                        <span>📅 {d}</span>
                    </div>
                    <div class='postit-content'>{nt}</div>
                </div>
                """, unsafe_allow_html=True)

# --- 2. MODULO EQUIPE (OPERATIVITÀ FIGURA PER FIGURA) ---
elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>AREA OPERATIVA EQUIPE</h2><p>Inserimento dati, terapie, parametri e consegne professionali</p></div>", unsafe_allow_html=True)
    
    pazienti = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    if pazienti:
        p_sel_nome = st.selectbox("Paziente in esame", [p[1] for p in pazienti])
        p_id = [p[0] for p in pazienti if p[1] == p_sel_nome][0]
        now_str = get_now_it().strftime("%d/%m/%Y %H:%M")
        
        # Gestione Figura Corrente (o simulazione Admin)
        ruolo_attivo = u['ruolo']
        if u['ruolo'] == "Admin":
            ruolo_attivo = st.sidebar.selectbox("Simula Ruolo:", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])

        # --- A. AREA MEDICA (PSICHIATRA) ---
        if ruolo_attivo == "Psichiatra":
            t1, t2, t3 = st.tabs(["💊 NUOVA TERAPIA", "📋 GESTIONE TERAPIE", "🩺 NOTA MEDICA"])
            with t1:
                with st.form("form_terapia"):
                    f = st.text_input("Farmaco / Principio Attivo")
                    d = st.text_input("Dosaggio (es. 20mg o 1cp)")
                    o = st.selectbox("Orario Somministrazione", ["8:13 (Mattina)", "16:20 (Pomeriggio)", "Al bisogno (PRN)"])
                    if st.form_submit_button("REGISTRA PRESCRIZIONE"):
                        m, p, b = (1,0,0) if "8:13" in o else ((0,1,0) if "16:20" in o else (0,0,1))
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno, medico, data_prescrizione) VALUES (?,?,?,?,?,?,?,?)",
                               (p_id, f.upper(), d, m, p, b, firma_op, oggi_it), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                               (p_id, now_str, f"➕ PRESCRIZIONE: {f.upper()} {d} ({o})", "Psichiatra", firma_op), True)
                        st.success("Terapia aggiunta!"); st.rerun()
            with t2:
                st.write("### Terapie in Corso")
                ters = db_run("SELECT id_u, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno FROM terapie WHERE p_id=?", (p_id,))
                for tid, fn, ds, m, p, b in ters:
                    ora = "8:13" if m else ("16:20" if p else "Bisogno")
                    col_t1, col_t2 = st.columns([4, 1])
                    col_t1.info(f"**{fn}** - {ds} (Orario: {ora})")
                    if col_t2.button("🚫 SOSPENDE", key=f"del_{tid}"):
                        db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                               (p_id, now_str, f"🚫 SOSPENSIONE TERAPIA: {fn}", "Psichiatra", firma_op), True)
                        st.rerun()
            with t3:
                with st.form("nota_med"):
                    txt = st.text_area("Annotazione Clinica / Esame Obiettivo")
                    if st.form_submit_button("SALVA IN DIARIO"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                               (p_id, now_str, f"🩺 NOTA MEDICA: {txt}", "Psichiatra", firma_op), True)
                        st.rerun()

        # --- B. AREA INFERMIERISTICA (SMARCATURA & PARAMETRI) ---
        elif ruolo_attivo == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 SMARCATURA TERAPIA", "💓 PARAMETRI VITALI", "📝 CONSEGNE"])
            with t1:
                fascia = st.selectbox("Seleziona Fascia Oraria", ["8:13", "16:20", "Bisogno"])
                col_db = "mat_nuovo" if "8:13" in fascia else ("pom_nuovo" if "16:20" in fascia else "al_bisogno")
                terapie_attive = db_run(f"SELECT id_u, farmaco, dose FROM terapie WHERE p_id=? AND {col_db}=1", (p_id,))
                
                for tid, f_nome, f_dose in terapie_attive:
                    st.markdown(f"#### 💊 {f_nome} - {f_dose}")
                    
                    # Recupero firme del mese corrente
                    firme_mese = db_run("SELECT data, esito, op FROM eventi WHERE id=? AND nota LIKE ? AND nota LIKE ? AND data LIKE ?",
                                       (p_id, f"%{f_nome}%", f"%({fascia})%", f"%/{get_now_it().strftime('%m/%Y')}%"))
                    f_map = {int(d[0].split("/")[0]): {"e": d[1], "o": d[2]} for d in firme_mese if d[0]}
                    
                    # Calendario Orizzontale
                    h = "<div class='scroll-giorni'>"
                    for d in range(1, calendar.monthrange(get_now_it().year, get_now_it().month)[1] + 1):
                        info = f_map.get(d)
                        is_oggi = "q-oggi" if d == get_now_it().day else ""
                        e, c_t, bg = (info['e'], "green", "#dcfce7") if info and info['e']=='A' else (("-", "#888", "white") if not info else ("R", "red", "#fee2e2"))
                        sigla = info['o'].split(" ")[0][0] + info['o'].split(" ")[1][0] if info else ""
                        h += f"<div class='quadratino {is_oggi}' style='background:{bg}; color:{c_t};'><div class='q-num'>{d}</div><div class='q-esito'>{e}</div><div class='q-op'>{sigla}</div></div>"
                    st.markdown(h + "</div>", unsafe_allow_html=True)
                    
                    # TASTI SMARCATURA (DIRETTAMENTE SOTTO IL CALENDARIO DEL FARMACO)
                    c_bt1, c_bt2, c_bt3 = st.columns([1, 1, 4])
                    if c_bt1.button("✅ ASSUNTO", key=f"ok_{tid}_{fascia}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)",
                               (p_id, now_str, f"✔️ SOMMINISTRAZIONE: {f_nome} ({fascia})", "Infermiere", firma_op, "A"), True)
                        st.rerun()
                    if c_bt2.button("❌ RIFIUTA", key=f"no_{tid}_{fascia}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)",
                               (p_id, now_str, f"❌ RIFIUTO: {f_nome} ({fascia})", "Infermiere", firma_op, "R"), True)
                        st.rerun()
                    st.divider()

            with t2:
                with st.form("parametri"):
                    c_p1, c_p2, c_p3 = st.columns(3)
                    pa = c_p1.text_input("Pressione Art. (es. 120/80)")
                    fc = c_p2.text_input("Freq. Cardiaca")
                    sa = c_p3.text_input("Saturazione %")
                    tc = c_p1.text_input("Temp. Corporea")
                    gl = c_p2.text_input("Glicemia")
                    if st.form_submit_button("REGISTRA PARAMETRI"):
                        nota_p = f"💓 PARAMETRI: PA {pa}, FC {fc}, SaO2 {sa}%, TC {tc}°, Glicemia {gl}"
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                               (p_id, now_str, nota_p, "Infermiere", firma_op), True)
                        st.rerun()
            with t3:
                with st.form("cons_inf"):
                    txt = st.text_area("Consegna di fine turno / Osservazioni infermieristiche")
                    if st.form_submit_button("INVIA CONSEGNA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                               (p_id, now_str, f"📝 CONSEGNA INF: {txt}", "Infermiere", firma_op), True)
                        st.rerun()

        # --- C. AREA EDUCATORI (CASSA & PROGETTI) ---
        elif ruolo_attivo == "Educatore":
            t1, t2 = st.tabs(["💰 GESTIONE CASSA", "🎨 ATTIVITÀ & PROGETTI"])
            with t1:
                movs = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in movs)
                st.markdown(f"<div class='cassa-card'>SALDO DISPONIBILE<br><span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
                
                with st.form("mov_cassa"):
                    c_c1, c_c2 = st.columns(2)
                    tipo_m = c_c1.selectbox("Tipo Operazione", ["ENTRATA", "USCITA"])
                    importo = c_c2.number_input("Cifra €", min_value=0.0, step=0.50)
                    causale = st.text_input("Causale Movimento")
                    if st.form_submit_button("ESEGUI TRANSAZIONE"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)",
                               (p_id, oggi_it, causale, importo, tipo_m, firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                               (p_id, now_str, f"💰 MOV. CASSA: {tipo_m} di {importo}€ ({causale})", "Educatore", firma_op), True)
                        st.rerun()
                
                st.write("### Ultimi Movimenti")
                storico = db_run("SELECT data, tipo, importo, causale, op FROM cassa WHERE p_id=? ORDER BY id_u DESC LIMIT 10", (p_id,))
                if storico: st.table(pd.DataFrame(storico, columns=["Data", "Tipo", "Importo", "Causale", "Operatore"]))

            with t2:
                with st.form("edu_note"):
                    txt = st.text_area("Resoconto Attività / Colloquio Educativo")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                               (p_id, now_str, f"🎨 EDU: {txt}", "Educatore", firma_op), True)
                        st.rerun()

        # --- D. AREA PSICOLOGO / SOCIALE ---
        elif ruolo_attivo in ["Psicologo", "Assistente Sociale"]:
            with st.form("psi_soc"):
                tipo_int = "🧠 PSICOLOGO" if ruolo_attivo == "Psicologo" else "🤝 SOCIALE"
                nt = st.text_area(f"Relazione {tipo_int}")
                if st.form_submit_button("SALVA RELAZIONE"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                           (p_id, now_str, f"{tipo_int}: {nt}", ruolo_attivo, firma_op), True)
                    st.rerun()

        # --- E. AREA OSS / OPSI ---
        elif ruolo_attivo in ["OSS", "OPSI"]:
            with st.form("oss_opsi"):
                pref = "🧹 OSS" if ruolo_attivo == "OSS" else "🛡️ OPSI"
                mans = st.multiselect("Mansioni / Verifiche", ["Igiene", "Pasto", "Vigilanza Stanza", "Controllo Perimetrale", "Accompagnamento"])
                obs = st.text_input("Osservazioni")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                           (p_id, now_str, f"{pref}: {', '.join(mans)} | {obs}", ruolo_attivo, firma_op), True)
                    st.rerun()

# --- 3. MODULO POSTI LETTO (MAPPA & TRASFERIMENTI) ---
elif nav == "🗺️ Posti Letto":
    st.markdown("<div class='section-banner'><h2>GESTIONE ALLOGGI E POSTI LETTO</h2><p>Mappa dei reparti e controllo occupazione in tempo reale</p></div>", unsafe_allow_html=True)
    
    stanze = db_run("SELECT id, reparto, tipo FROM stanze ORDER BY id")
    assegnati = db_run("SELECT p.id, p.nome, a.stanza_id, a.letto FROM pazienti p JOIN assegnazioni a ON p.id=a.p_id WHERE p.stato='ATTIVO'")
    
    occupazione = {s[0]: {"info": s, "L1": None, "L2": None} for s in stanze}
    for pid, pnome, sid, let in assegnati:
        if sid in occupazione: occupazione[sid][f"L{let}"] = pnome
        
    c_map1, c_map2 = st.columns(2)
    for rep, col in [("A", c_map1), ("B", c_map2)]:
        with col:
            st.write(f"### REPARTO {rep}")
            for sid, data in {k:v for k,v in occupazione.items() if v['info'][1] == rep}.items():
                p_count = sum(1 for l in ["L1", "L2"] if data[l])
                cls = "stanza-piena" if p_count==2 else ("stanza-occupata" if p_count==1 else "")
                iso = "stanza-isolamento" if data['info'][2] == "ISOLAMENTO" else ""
                
                st.markdown(f"""
                <div class='stanza-tile {cls} {iso}'>
                    <strong>STANZA {sid}</strong> <small>({data['info'][2]})</small><br>
                    L1: {data['L1'] or '---'}<br>
                    L2: {data['L2'] or '---'}
                </div>
                """, unsafe_allow_html=True)

    with st.expander("🔄 ESEGUI TRASFERIMENTO PAZIENTE"):
        with st.form("trasferimento"):
            p_list = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
            p_sel = st.selectbox("Paziente da spostare", [p[1] for p in p_list])
            dest_s = st.selectbox("Nuova Stanza", [s[0] for s in stanze])
            dest_l = st.selectbox("Letto", [1, 2])
            motivo = st.text_input("Motivazione Trasferimento")
            if st.form_submit_button("CONFERMA SPOSTAMENTO"):
                pid_sposta = [p[0] for p in p_list if p[1]==p_sel][0]
                db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid_sposta,), True)
                db_run("INSERT INTO assegnazioni VALUES (?,?,?,?)", (pid_sposta, dest_s, dest_l, oggi_it), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                       (pid_sposta, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🔄 TRASFERIMENTO: Spostato in {dest_s}-L{dest_l}. Motivo: {motivo}", u['ruolo'], firma_op), True)
                st.success("Trasferimento completato!"); st.rerun()

# --- 4. MODULO AGENDA ---
elif nav == "📅 Agenda & Scadenze":
    st.markdown("<div class='section-banner'><h2>AGENDA DINAMICA REMS</h2><p>Pianificazione udienze, perizie e visite specialistiche</p></div>", unsafe_allow_html=True)
    
    col_ag1, col_ag2 = st.columns([3, 1])
    with col_ag1:
        m, y = get_now_it().month, get_now_it().year
        cal = calendar.monthdayscalendar(y, m)
        
        # Recupero appuntamenti del mese
        apps = db_run("SELECT data, nota, (SELECT nome FROM pazienti WHERE id=p_id) FROM appuntamenti WHERE data LIKE ?", (f"{y}-{m:02d}%",))
        app_map = {}
        for d_app, n_app, p_app in apps:
            gg = int(d_app.split("-")[2])
            if gg not in app_map: app_map[gg] = []
            app_map[gg].append(f"• {p_app}: {n_app}")

        st.write(f"### {calendar.month_name[m]} {y}")
        h_cal = "<table style='width:100%; border-collapse: collapse; background:white; color: black;'><thead><tr style='background:#f1f5f9;'>"
        for sett in ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]: h_cal += f"<th style='padding:10px; border:1px solid #ddd;'>{sett}</th>"
        h_cal += "</tr></thead><tbody>"
        
        for week in cal:
            h_cal += "<tr>"
            for d in week:
                if d == 0: h_cal += "<td style='background:#f9fafb; border:1px solid #ddd;'></td>"
                else:
                    bg_d = "#fffde7" if d == get_now_it().day else "white"
                    evs = "<br>".join(app_map.get(d, []))
                    h_cal += f"<td style='height:100px; vertical-align:top; padding:5px; border:1px solid #ddd; background:{bg_d};'><strong>{d}</strong><div style='font-size:0.7rem;'>{evs}</div></td>"
            h_cal += "</tr>"
        st.markdown(h_cal + "</tbody></table>", unsafe_allow_html=True)

    with col_ag2:
        st.write("### Nuovo Impegno")
        with st.form("add_app"):
            p_list = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
            p_a = st.selectbox("Paziente", [p[1] for p in p_list])
            d_a = st.date_input("Data")
            o_a = st.time_input("Ora")
            n_a = st.text_input("Oggetto (es. Udienza)")
            if st.form_submit_button("AGGIUNGI IN AGENDA"):
                p_id_a = [p[0] for p in p_list if p[1]==p_a][0]
                db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore) VALUES (?,?,?,?,?,?)",
                       (p_id_a, str(d_a), str(o_a)[:5], n_a, "PROGRAMMATO", firma_op), True)
                st.rerun()

# --- 5. MODULO AMMINISTRAZIONE (LOGS & UTENTI) ---
elif nav == "⚙️ Amministrazione":
    if u['ruolo'] != "Admin":
        st.error("Accesso negato. Solo l'amministratore può accedere a questa sezione.")
    else:
        st.markdown("<div class='section-banner'><h2>PANNELLO DI CONTROLLO AMMINISTRATIVO</h2><p>Manutenzione utenti, database e log di sicurezza</p></div>", unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["👥 GESTIONE STAFF", "🏥 ANAGRAFICA PAZIENTI", "📜 LOG DI SISTEMA"])
        
        with tab1:
            st.write("### Utenti Registrati")
            uts = db_run("SELECT user, nome, cognome, qualifica FROM utenti")
            df_uts = pd.DataFrame(uts, columns=["Username", "Nome", "Cognome", "Qualifica"])
            st.table(df_uts)
            
            with st.expander("Rimuovi Operatore"):
                u_del = st.selectbox("Seleziona Utente da eliminare", [u[0] for u in uts if u[0] != 'admin'])
                if st.button("ELIMINA DEFINITIVAMENTE"):
                    db_run("DELETE FROM utenti WHERE user=?", (u_del,), True)
                    scrivi_log("DELETE_USER", f"Rimosso utente: {u_del}")
                    st.rerun()
                    
        with tab2:
            st.write("### Gestione Pazienti")
            with st.form("add_paz"):
                n_p = st.text_input("Nome e Cognome Paziente").upper()
                if st.form_submit_button("INSERISCI IN REMS"):
                    db_run("INSERT INTO pazienti (nome, stato) VALUES (?,?)", (n_p, "ATTIVO"), True)
                    scrivi_log("ADD_PAZIENTE", f"Inserito: {n_p}")
                    st.success("Paziente inserito"); st.rerun()
            
            st.divider()
            for pid, pno in db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'"):
                if st.button(f"🚩 DIMETTI / TRASFERISCI: {pno}", key=f"dim_{pid}"):
                    db_run("UPDATE pazienti SET stato='DIMESSO' WHERE id=?", (pid,), True)
                    db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid,), True)
                    scrivi_log("DIMISSIONE", f"Dimesso: {pno}")
                    st.rerun()

        with tab3:
            st.write("### Log Attività (Ultimi 100 eventi)")
            logs = db_run("SELECT * FROM logs_sistema ORDER BY id_log DESC LIMIT 100")
            st.table(pd.DataFrame(logs, columns=["ID", "Timestamp", "Utente", "Azione", "Dettaglio"]))
            
            if st.button("🗑️ Pulisci Log (Vecchi di 30gg)"):
                st.info("Funzione di manutenzione database eseguita.")
