import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd

# --- FUNZIONE ORARIO ITALIA (UTC+2) ---
def get_now_it():
    # Correzione di 2 ore rispetto all'orario del server (UTC)
    return datetime.now(timezone.utc) + timedelta(hours=2)

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v27.0 ---
st.set_page_config(page_title="REMS Connect ELITE PRO v27.0", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* STILE SIDEBAR */
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    
    /* SCRITTA VERDE FLUO PER OPERATORE */
    .user-logged { color: #00ff00 !important; font-weight: 900; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; text-align: center; }
    
    /* BANNER SUPERIORE */
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 1px solid #ffffff22; }
    
    /* TASTO LOGOUT VERDE */
    .stButton>button[kind="secondary"] { background-color: #22c55e !important; color: white !important; border: none !important; width: 100%; font-weight: 700; }
    
    /* POST-IT */
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    
    /* APPUNTAMENTI BOX */
    .app-card { background-color: #fffbeb; border: 1px solid #fef3c7; padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 6px solid #d97706; color: #1e293b; }

    /* TERAPIA */
    .therapy-container { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px; margin-bottom: 15px; border-left: 8px solid #1e3a8a; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    .turn-header { font-weight: 800; font-size: 0.9rem; text-transform: uppercase; margin-bottom: 10px; }
    .mat-style { color: #d97706; } .pom-style { color: #2563eb; } .not-style { color: #4338ca; }
    
    /* CASSA */
    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2.2rem; font-weight: 900; color: #166534; }
    
    /* FIRMA SIDEBAR */
    .sidebar-footer { color: #ffffff !important; font-size: 0.8rem; margin-top: 50px; border-top: 1px solid #ffffff33; padding-top: 10px; opacity: 0.8; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ENGINE ---
DB_NAME = "rems_final_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT)")
        try:
            if query: cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}"); return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def render_postits(p_id=None, limit=50, filter_role=None):
    query = "SELECT data, ruolo, op, nota FROM eventi WHERE 1=1"
    params = []
    if p_id: query += " AND id=?"; params.append(p_id)
    if filter_role: query += " AND ruolo=?"; params.append(filter_role)
    res = db_run(query + " ORDER BY id_u DESC LIMIT ?", tuple(params + [limit]))
    for d, r, o, nt in res:
        cls = f"role-{r.lower()}"
        st.markdown(f'<div class="postit {cls}"><div class="postit-header"><span>👤 {o} ({r})</span><span>📅 {d}</span></div><div>{nt}</div></div>', unsafe_allow_html=True)

# --- GESTIONE ACCESSO E REGISTRAZIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT - ACCESSO PRO</h2></div>", unsafe_allow_html=True)
    
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.subheader("Login Operatore")
        with st.form("login_main"):
            u_i = st.text_input("Username")
            p_i = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI AL SISTEMA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
                if res:
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_i}
                    st.rerun()
                else:
                    st.error("Credenziali non corrette.")
                    
    with col_r:
        st.subheader("Registrazione Nuovo Account")
        with st.form("register_main"):
            reg_u = st.text_input("Scegli Username")
            reg_p = st.text_input("Scegli Password", type="password")
            reg_n = st.text_input("Nome")
            reg_c = st.text_input("Cognome")
            reg_q = st.selectbox("Qualifica/Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Admin"])
            if st.form_submit_button("CREA ACCOUNT"):
                if reg_u and reg_p and reg_n and reg_c:
                    exist = db_run("SELECT user FROM utenti WHERE user=?", (reg_u,))
                    if exist:
                        st.warning("Questo username è già in uso.")
                    else:
                        db_run("INSERT INTO utenti (user, pwd, nome, cognome, qualifica) VALUES (?,?,?,?,?)", 
                               (reg_u, hash_pw(reg_p), reg_n.capitalize(), reg_c.capitalize(), reg_q), True)
                        st.success("Account creato con successo! Ora puoi effettuare il login.")
                else:
                    st.error("Tutti i campi sono obbligatori.")
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-logged'>● {u['nome']} {u['cognome']}</div>", unsafe_allow_html=True)

menu_options = ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Appuntamenti"]
if u['ruolo'] == "Admin": menu_options.append("⚙️ Admin")
nav = st.sidebar.radio("NAVIGAZIONE", menu_options)

if st.sidebar.button("CHIUDI SESSIONE (LOGOUT)"): 
    st.session_state.user_session = None; st.rerun()

st.sidebar.markdown(f"""
<div class='sidebar-footer'>
    Sviluppato da: AntonioWebMaster<br>
    Versione: ELITE PRO v27.0<br>
    Data: {get_now_it().strftime('%Y')}
</div>
""", unsafe_allow_html=True)

# --- MODULI ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO GENERALE</h2></div>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"📁 SCHEDA PAZIENTE: {nome}"): render_postits(pid)

elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO EQUIPE</h2></div>", unsafe_allow_html=True)
    ruolo_corr = u['ruolo']
    if u['ruolo'] == "Admin": ruolo_corr = st.selectbox("Simula Figura:", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        now = get_now_it()
        oggi = now.strftime("%d/%m/%Y")

        if ruolo_corr == "Psichiatra":
            t1, t2 = st.tabs(["➕ Nuova Prescrizione", "📝 Gestione Terapie"])
            with t1:
                with st.form("f_ps"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"➕ Prescritto: {f} {d}", "Psichiatra", firma_op), True); st.rerun()
            with t2:
                for tid, fn, ds, m_v, p_v, n_v in db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,)):
                    with st.expander(f"Modifica: {fn}"):
                        with st.form(key=f"m_{tid}"):
                            nf, nd = st.text_input("Farmaco", fn), st.text_input("Dose", ds)
                            cc1, cc2, cc3 = st.columns(3); nm, np, nn = cc1.checkbox("MAT", bool(m_v)), cc2.checkbox("POM", bool(p_v)), cc3.checkbox("NOT", bool(n_v))
                            b1, b2 = st.columns(2)
                            if b1.form_submit_button("AGGIORNA"):
                                db_run("UPDATE terapie SET farmaco=?, dose=?, mat=?, pom=?, nott=? WHERE id_u=?", (nf, nd, int(nm), int(np), int(nn), tid), True); st.rerun()
                            if b2.form_submit_button("SOSPENDE"):
                                db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True); st.rerun()

        elif ruolo_corr == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 TERAPIA", "💓 PARAMETRI", "📝 CONSEGNE"])
            with t1:
                terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                cols = st.columns(3); turni = [("MAT", 3, "mat-style", "☀️"), ("POM", 4, "pom-style", "🌤️"), ("NOT", 5, "not-style", "🌙")]
                for i, (t_n, t_idx, t_css, t_ico) in enumerate(turni):
                    with cols[i]:
                        for f in [x for x in terapie if x[t_idx]]:
                            check = db_run("SELECT id_u FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%SOMM ({t_n}): {f[1]}%", f"{oggi}%"))
                            if not check:
                                st.markdown(f"<div class='therapy-container'><div class='turn-header {t_css}'>{t_ico} {t_n}</div><b>{f[1]}</b><br>{f[2]}</div>", unsafe_allow_html=True)
                                if st.button(f"CONFERMA", key=f"ok_{f[0]}_{t_n}"):
                                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({t_n}): {f[1]}", "Infermiere", firma_op), True); st.rerun()
            with t2:
                with st.form("vit"):
                    c1,c2,c3 = st.columns(3); pa=c1.text_input("PA"); fc=c2.text_input("FC"); sat=c3.text_input("SatO2")
                    c4,c5 = st.columns(2); tc=c4.text_input("TC"); gl=c5.text_input("Glicemia")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💓 PA:{pa} FC:{fc} Sat:{sat} TC:{tc} Gl:{gl}", "Infermiere", firma_op), True); st.rerun()
            with t3:
                with st.form("ni"):
                    txt = st.text_area("Consegna Clinica"); 
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), txt, "Infermiere", firma_op), True); st.rerun()

        elif ruolo_corr == "OSS":
            with st.form("oss_f"):
                st.subheader("Diario OSS")
                mans = st.multiselect("Mansioni:", ["Igiene Totale", "Igiene Parziale", "Cambio Panno", "Pulizia Stanza", "Letto", "Cortile", "Sale Fumo", "Lavatrice"])
                txt = st.text_area("Note del turno")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧹 {', '.join(mans)} | {txt}", "OSS", firma_op), True); st.rerun()

        elif ruolo_corr == "Educatore":
            mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
            saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
            st.markdown(f"<div class='cassa-card'>Saldo: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
            with st.form("cs"):
                tp, im, cau = st.selectbox("Tipo", ["ENTRATA", "USCITA"]), st.number_input("€"), st.text_input("Causale")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, oggi, cau, im, tp, firma_op), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💰 {tp}: {im}€ - {cau}", "Educatore", firma_op), True); st.rerun()

        st.divider(); render_postits(p_id, filter_role=ruolo_corr)

elif nav == "📅 Appuntamenti":
    st.markdown("<div class='section-banner'><h2>GESTIONE APPUNTAMENTI E SCADENZE</h2></div>", unsafe_allow_html=True)
    t_new, t_agenda = st.tabs(["➕ PROGRAMMA APPUNTAMENTO", "📋 AGENDA EQUIPE"])
    
    with t_new:
        with st.form("f_new_app"):
            p_lista_app = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
            p_app_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista_app])
            p_app_id = [p[0] for p in p_lista_app if p[1] == p_app_sel][0]
            d_app, h_app = st.date_input("Data"), st.time_input("Ora")
            n_app = st.text_input("Causale (es: Visita Oculistica, Colloquio, Uscita)")
            if st.form_submit_button("SALVA IN AGENDA"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore) VALUES (?,?,?,?,'PROGRAMMATO',?)", (p_app_id, str(d_app), str(h_app)[:5], n_app, firma_op), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_app_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"📅 Programmato appuntamento: {n_app} per il {d_app}", u['ruolo'], firma_op), True)
                st.success("Appuntamento registrato!"); st.rerun()

    with t_agenda:
        st.subheader("Appuntamenti Programmati")
        agenda = db_run("SELECT a.id_u, a.data, a.ora, p.nome, a.nota, a.autore FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.stato='PROGRAMMATO' ORDER BY a.data, a.ora")
        for aid, adt, ahr, apn, ant, aut in agenda:
            st.markdown(f"<div class='app-card'>📅 <b>{adt} alle {ahr}</b> - Paziente: <b>{apn}</b><br>Dettagli: {ant}<br><small>Inserito da: {aut}</small></div>", unsafe_allow_html=True)
            if st.button("SEGNA COME COMPLETATO", key=f"app_ok_{aid}"):
                db_run("UPDATE appuntamenti SET stato='COMPLETATO' WHERE id_u=?", (aid,), True); st.rerun()

elif nav == "⚙️ Admin":
    st.markdown("<div class='section-banner'><h2>PANNELLO AMMINISTRATIVO ELITE</h2></div>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["👥 UTENTI & CREDENZIALI", "👤 GESTIONE PAZIENTI", "🛡️ SICUREZZA LOG"])
    
    with tab1:
        st.subheader("Database Operatori (Username e Password)")
        users_full = db_run("SELECT user, pwd, nome, cognome, qualifica FROM utenti")
        for u_id, u_pw, u_n, u_c, u_q in users_full:
            with st.container():
                c_u1, c_u2, c_u3 = st.columns([0.4, 0.4, 0.2])
                c_u1.markdown(f"**{u_n} {u_c}** ({u_q})")
                c_u2.code(f"User: {u_id} | PW: {u_pw}")
                if c_u3.button("ELIMINA 🗑️", key=f"del_u_{u_id}"):
                    if u_id == u['uid']: st.error("Impossibile auto-eliminarsi")
                    else:
                        db_run("DELETE FROM utenti WHERE user=?", (u_id,), True)
                        st.success(f"Utente {u_id} rimosso."); st.rerun()
                st.divider()

    with tab2:
        st.subheader("Anagrafica Pazienti")
        with st.form("new_p"):
            np = st.text_input("Nuovo Paziente (NOME COGNOME)")
            if st.form_submit_button("AGGIUNGI PAZIENTE"):
                db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
        
        st.divider()
        pazs = db_run("SELECT id, nome FROM pazienti")
        for p_id_a, p_nome_a in pazs:
            col_a, col_b, col_c = st.columns([0.6, 0.2, 0.2])
            new_n_p = col_a.text_input("Modifica Nome", value=p_nome_a, key=f"edit_p_{p_id_a}")
            if col_b.button("💾", key=f"save_p_{p_id_a}"):
                db_run("UPDATE pazienti SET nome=? WHERE id=?", (new_n_p.upper(), p_id_a), True); st.rerun()
            if col_c.button("🗑️", key=f"del_p_{p_id_a}"):
                db_run("DELETE FROM pazienti WHERE id=?", (p_id_a,), True)
                db_run("DELETE FROM terapie WHERE p_id=?", (p_id_a,), True)
                db_run("DELETE FROM eventi WHERE id=?", (p_id_a,), True)
                db_run("DELETE FROM appuntamenti WHERE p_id=?", (p_id_a,), True)
                st.rerun()

    with tab3:
        st.subheader("Cancellazione Puntuale Note Diario")
        pazs_log = db_run("SELECT id, nome FROM pazienti")
        for pl_id, pl_nome in pazs_log:
            with st.expander(f"Dettaglio Log: {pl_nome}"):
                voci = db_run("SELECT id_u, data, nota, op FROM eventi WHERE id=? ORDER BY id_u DESC", (pl_id,))
                if not voci:
                    st.write("Nessuna nota presente.")
                for v_id, v_data, v_nota, v_op in voci:
                    cv1, cv2 = st.columns([0.85, 0.15])
                    cv1.write(f"[{v_data}] **{v_op}**: {v_nota}")
                    if cv2.button("❌", key=f"del_nota_{v_id}"):
                        db_run("DELETE FROM eventi WHERE id_u=?", (v_id,), True)
                        st.rerun()
        
        st.divider()
        st.subheader("Reset Globale")
        if st.button("🚨 CANCELLA OGNI SINGOLO LOG DEL SISTEMA"):
            db_run("DELETE FROM eventi", (), True)
            st.success("Tutti i log di sistema sono stati azzerati."); st.rerun()
