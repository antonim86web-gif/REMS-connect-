import sqlite3
import streamlit as st
from datetime import datetime, timedelta
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v23.0 ---
st.set_page_config(page_title="REMS Connect ELITE PRO v23.0", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* SIDEBAR PROFESSIONALE */
    [data-testid="stSidebar"] { background-color: #0f172a !important; min-width: 300px !important; }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }
    .sidebar-title { font-size: 2rem !important; font-weight: 800 !important; color: #38bdf8 !important; text-align: center; margin-bottom: 2rem; border-bottom: 2px solid #334155; padding-bottom: 10px; }
    .user-logged { color: #4ade80 !important; font-weight: 700; text-align: center; background: #1e293b; padding: 10px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #334155; }
    
    /* BANNER E CONTENITORI */
    .section-banner { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); color: white !important; padding: 30px; border-radius: 15px; margin-bottom: 30px; text-align: center; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
    .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; text-align: center; }
    
    /* DIARIO A POST-IT */
    .postit { padding: 20px; border-radius: 12px; margin-bottom: 15px; border-left: 12px solid; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); background: #ffffff; transition: 0.3s; }
    .postit:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
    .postit-header { font-weight: 800; font-size: 0.9rem; text-transform: uppercase; margin-bottom: 10px; display: flex; justify-content: space-between; color: #64748b; border-bottom: 1px solid #f1f5f9; padding-bottom: 5px; }
    
    /* COLORI RUOLI */
    .role-psichiatra { border-color: #ef4444; } .role-infermiere { border-color: #3b82f6; } 
    .role-educatore { border-color: #10b981; } .role-oss { border-color: #f59e0b; }
    .role-admin { border-color: #6366f1; }
    
    /* APPUNTAMENTI */
    .app-card { background: #f8fafc; border-radius: 10px; padding: 15px; border-left: 8px solid #d97706; margin-bottom: 10px; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; }
    .tag-clinico { background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; }
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
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, tipo TEXT, stato TEXT, autore TEXT)")
        try:
            if query: cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}"); return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- GESTIONE LOGIN ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h1>🏥 REMS CONNECT SYSTEM</h1><p>Inserire le credenziali per accedere al modulo di gestione</p></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.form("login"):
            u_i = st.text_input("Username Operatore")
            p_i = st.text_input("Codice di Accesso", type="password")
            if st.form_submit_button("AUTENTICAZIONE"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
                if res:
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_i}
                    st.rerun()
                else: st.error("Credenziali non valide.")
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR NAV ---
st.sidebar.markdown("<div class='sidebar-title'>REMS-CONNECT</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-logged'>👤 {u['nome']} {u['cognome']}<br><small>{u['ruolo']}</small></div>", unsafe_allow_html=True)

nav = st.sidebar.radio("MENU PRINCIPALE", ["📊 Monitoraggio Reparto", "👥 Modulo Operativo", "📅 Agenda Appuntamenti", "⚙️ Pannello Admin"])
if st.sidebar.button("🔴 ESCI DAL SISTEMA"): st.session_state.user_session = None; st.rerun()

# --- 1. MONITORAGGIO ---
if nav == "📊 Monitoraggio Reparto":
    st.markdown("<div class='section-banner'><h2>DASHBOARD DI MONITORAGGIO</h2></div>", unsafe_allow_html=True)
    
    # Quick Stats
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Pazienti Totali", len(db_run("SELECT id FROM pazienti")))
    s2.metric("Note (24h)", len(db_run("SELECT id_u FROM eventi WHERE data LIKE ?", (datetime.now().strftime("%d/%m/%Y")+"%",))))
    s3.metric("Appuntamenti Oggi", len(db_run("SELECT id_u FROM appuntamenti WHERE data=? AND stato='PROGRAMMATO'", (datetime.now().strftime("%Y-%m-%d"),))))
    s4.metric("Stato Sistema", "ONLINE", delta="PRO")

    st.divider()
    
    col_p, col_d = st.columns([1, 3])
    with col_p:
        st.subheader("Seleziona Paziente")
        p_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        p_sel = st.radio("Cartelle Cliniche:", [p[1] for p in p_list])
        p_id = [p[0] for p in p_list if p[1] == p_sel][0]
    
    with col_d:
        st.subheader(f"Diario Clinico: {p_sel}")
        f_op = st.selectbox("Filtra per operatore:", ["TUTTI"] + [x[0] for x in db_run("SELECT DISTINCT op FROM eventi WHERE id=?", (p_id,))])
        
        query = "SELECT data, ruolo, op, nota FROM eventi WHERE id=?"
        params = [p_id]
        if f_op != "TUTTI": query += " AND op=?"; params.append(f_op)
        
        voci = db_run(query + " ORDER BY id_u DESC LIMIT 50", tuple(params))
        for d, r, o, nt in voci:
            st.markdown(f'''
            <div class="postit role-{r.lower()}">
                <div class="postit-header">
                    <span><b>{o}</b> • {r}</span>
                    <span>{d}</span>
                </div>
                <div style="font-size: 1.1rem; line-height: 1.6;">{nt}</div>
            </div>
            ''', unsafe_allow_html=True)

# --- 2. MODULO OPERATIVO ---
elif nav == "👥 Modulo Operativo":
    st.markdown("<div class='section-banner'><h2>REGISTRAZIONE ATTIVITÀ EQUIPE</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_id = st.selectbox("Seleziona il paziente oggetto della nota:", [p[0] for p in p_lista], format_func=lambda x: [p[1] for p in p_lista if p[0]==x][0])
        
        with st.form("nuova_nota"):
            st.write("### Nuova voce di diario")
            txt = st.text_area("Descrizione dettagliata dell'intervento o dell'osservazione", height=200)
            c1, c2 = st.columns(2)
            urgenza = c1.checkbox("Segnala come URGENZA")
            if st.form_submit_button("PUBBLICA NOTA NEL DIARIO"):
                final_txt = f"🚨 [URGENTE] {txt}" if urgenza else txt
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                       (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), final_txt, u['ruolo'], firma_op), True)
                st.success("Nota registrata correttamente.")
                st.rerun()

# --- 3. APPUNTAMENTI ---
elif nav == "📅 Agenda Appuntamenti":
    st.markdown("<div class='section-banner'><h2>AGENDA E SCADENZARIO</h2></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("Programma Impegno")
        with st.form("add_app"):
            p_app = st.selectbox("Paziente", [p[1] for p in db_run("SELECT id, nome FROM pazienti")])
            p_app_id = [p[0] for p in db_run("SELECT id, nome FROM pazienti") if p[1]==p_app][0]
            d_app = st.date_input("Giorno")
            h_app = st.time_input("Orario")
            tipo_app = st.selectbox("Tipo:", ["Sanitario", "Colloquio", "Uscita Scortata", "Legale", "Altro"])
            nota_app = st.text_input("Dettagli/Luogo")
            if st.form_submit_button("INSERISCI IN AGENDA"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, tipo, stato, autore) VALUES (?,?,?,?,?,'PROGRAMMATO',?)",
                       (p_app_id, str(d_app), str(h_app)[:5], nota_app, tipo_app, firma_op), True)
                st.rerun()

    with c2:
        st.subheader("Prossimi Appuntamenti")
        view_apps = db_run("SELECT a.id_u, a.data, a.ora, p.nome, a.nota, a.tipo, a.autore FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.stato='PROGRAMMATO' ORDER BY a.data, a.ora")
        for aid, adt, ahr, apn, ant, atp, aut in view_apps:
            with st.container():
                st.markdown(f"""
                <div class='app-card'>
                    <div style='display: flex; justify-content: space-between;'>
                        <span class='tag-clinico'>{atp.upper()}</span>
                        <b>{adt} • {ahr}</b>
                    </div>
                    <div style='margin-top:10px;'><b>Paziente:</b> {apn}</div>
                    <div><b>Note:</b> {ant}</div>
                    <div style='font-size:0.8rem; color:gray;'>Inserito da: {aut}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("SEGNA COME SVOLTO", key=f"sv_{aid}"):
                    db_run("UPDATE appuntamenti SET stato='COMPLETATO' WHERE id_u=?", (aid,), True); st.rerun()

# --- 4. ADMIN ---
elif nav == "⚙️ Pannello Admin":
    if u['ruolo'] != "Admin":
        st.error("ACCESSO NEGATO. Questa sezione è riservata all'Amministratore.")
        st.stop()
        
    st.markdown("<div class='section-banner'><h2>SISTEMA DI CONTROLLO ADMIN</h2></div>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["🛡️ GESTIONE UTENTI", "👥 ANAGRAFICA PAZIENTI", "🛡️ SICUREZZA LOG"])
    
    with t1:
        st.subheader("Database Operatori")
        users = db_run("SELECT user, pwd, nome, cognome, qualifica FROM utenti")
        df_u = pd.DataFrame(users, columns=["Username", "Password (Hash/Chiaro)", "Nome", "Cognome", "Ruolo"])
        st.table(df_u)
        
        st.divider()
        st.subheader("Rimozione Rapida")
        u_del = st.selectbox("Seleziona utente da rimuovere:", [x[0] for x in users])
        if st.button("ELIMINA DEFINITIVAMENTE UTENTE"):
            if u_del == u['uid']: st.warning("Non puoi eliminare te stesso.")
            else: db_run("DELETE FROM utenti WHERE user=?", (u_del,), True); st.rerun()

    with t2:
        st.subheader("Gestione Anagrafica")
        with st.form("new_p"):
            n_p = st.text_input("Nuovo Paziente (NOME COGNOME)")
            if st.form_submit_button("REGISTRA PAZIENTE"):
                db_run("INSERT INTO pazienti (nome) VALUES (?)", (n_p.upper(),), True); st.rerun()
        
        for pid, pnm in db_run("SELECT id, nome FROM pazienti"):
            c_a, c_b = st.columns([0.8, 0.2])
            c_a.write(f"📁 {pnm}")
            if c_b.button("CANCELLA", key=f"pdel_{pid}"):
                db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()

    with t3:
        st.subheader("Revisione e Cancellazione Puntuale Log")
        for pid, pnm in db_run("SELECT id, nome FROM pazienti"):
            with st.expander(f"Cartella di {pnm}"):
                voci_l = db_run("SELECT id_u, data, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (pid,))
                for vid, vdt, vop, vnt in voci_l:
                    cl1, cl2 = st.columns([0.85, 0.15])
                    cl1.write(f"**[{vdt}] {vop}:** {vnt}")
                    if cl2.button("🗑️", key=f"ldel_{vid}"):
                        db_run("DELETE FROM eventi WHERE id_u=?", (vid,), True); st.rerun()
