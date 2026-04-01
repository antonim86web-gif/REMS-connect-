import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd

# --- FUNZIONE ORARIO ITALIA (UTC+2) ---
def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v29.0 ---
st.set_page_config(page_title="REMS Connect ELITE PRO v29.0", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .user-logged { color: #00ff00 !important; font-weight: 900; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; text-align: center; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 1px solid #ffffff22; }
    .stButton>button[kind="secondary"] { background-color: #22c55e !important; color: white !important; border: none !important; width: 100%; font-weight: 700; }
    
    /* STILI POST-IT PER TUTTI I RUOLI */
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    .role-psicologo { background-color: #faf5ff; border-color: #a855f7; } /* Viola */
    .role-sociale { background-color: #fff7ed; border-color: #f97316; } /* Arancio */
    .role-opsi { background-color: #f1f5f9; border-color: #0f172a; border-style: dashed; } /* Nero/Grigio Scuro */

    .app-card { background-color: #fffbeb; border: 1px solid #fef3c7; padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 6px solid #d97706; color: #1e293b; }
    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2.2rem; font-weight: 900; color: #166534; }
    
    /* MAPPA VISIVA */
    .map-reparto { background: #f1f5f9; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    .reparto-title { text-align: center; color: #1e3a8a; font-weight: 900; text-transform: uppercase; margin-bottom: 15px; border-bottom: 2px solid #1e3a8a33; }
    .stanza-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
    .stanza-tile { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; border-left: 6px solid #94a3b8; }
    .stanza-header { font-weight: 800; font-size: 0.8rem; color: #475569; margin-bottom: 5px; border-bottom: 1px solid #eee; }
    .letto-slot { font-size: 0.8rem; color: #1e293b; padding: 2px 0; }
    .stanza-occupata { border-left-color: #22c55e; background-color: #f0fdf4; }
    .stanza-piena { border-left-color: #2563eb; background-color: #eff6ff; }
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
        cur.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT, FOREIGN KEY(p_id) REFERENCES pazienti(id))")
        
        # Inizializzazione Stanze
        if cur.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
            for i in range(1, 7): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"A{i}", "A", "ISOLAMENTO" if i==6 else "STANDARD"))
            for i in range(1, 11): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"B{i}", "B", "ISOLAMENTO" if i==10 else "STANDARD"))
            conn.commit()
        try:
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def render_postits(p_id=None, limit=50, filter_role=None):
    query = "SELECT data, ruolo, op, nota FROM eventi WHERE 1=1"
    params = []
    if p_id: query += " AND id=?"; params.append(p_id)
    if filter_role: query += " AND ruolo=?"; params.append(filter_role)
    res = db_run(query + " ORDER BY id_u DESC LIMIT ?", tuple(params + [limit]))
    for d, r, o, nt in res:
        # Mapping classi CSS per i nuovi ruoli
        role_map = {"Psichiatra":"psichiatra", "Infermiere":"infermiere", "Educatore":"educatore", "OSS":"oss", "Psicologo":"psicologo", "Assistente Sociale":"sociale", "OPSI":"opsi"}
        cls = f"role-{role_map.get(r, 'oss')}"
        st.markdown(f'<div class="postit {cls}"><div class="postit-header"><span>👤 {o} ({r})</span><span>📅 {d}</span></div><div>{nt}</div></div>', unsafe_allow_html=True)

# --- LOGICA SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT v29.0 - SISTEMA INTEGRATO</h2></div>", unsafe_allow_html=True)
    c_l, c_r = st.columns(2)
    with c_l:
        st.subheader("Accedi")
        with st.form("login_main"):
            u_i, p_i = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
                if res: st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_i}; st.rerun()
                else: st.error("Credenziali non valide")
    with c_r:
        st.subheader("Registra Nuovo Operatore")
        with st.form("reg_main"):
            ru, rp, rn, rc = st.text_input("User"), st.text_input("PW", type="password"), st.text_input("Nome"), st.text_input("Cognome")
            rq = st.selectbox("Ruolo Professionale", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI", "Admin"])
            if st.form_submit_button("CREA PROFILO"):
                if ru and rp:
                    db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (ru, hash_pw(rp), rn.capitalize(), rc.capitalize(), rq), True)
                    st.success("Profilo Creato!")
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-logged'>● {u['nome']} {u['cognome']}</div>", unsafe_allow_html=True)
opts = ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Appuntamenti", "🗺️ Mappa Posti Letto"]
if u['ruolo'] == "Admin": opts.append("⚙️ Admin")
nav = st.sidebar.radio("NAVIGAZIONE", opts)
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()

# --- MODULO EQUIPE (IL CUORE DELLA v29.0) ---
if nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO EQUIPE MULTIDISCIPLINARE</h2></div>", unsafe_allow_html=True)
    ruolo_corr = u['ruolo']
    if u['ruolo'] == "Admin": ruolo_corr = st.selectbox("Simula Ruolo:", ["Psichiatra", "Infermiere", "Psicologo", "Assistente Sociale", "Educatore", "OSS", "OPSI"])
    
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        now = get_now_it(); oggi = now.strftime("%d/%m/%Y")

        # --- MODULO PSICOLOGO ---
        if ruolo_corr == "Psicologo":
            st.subheader("🧠 Area Clinica Psicologica")
            with st.form("f_psi"):
                tipo_c = st.selectbox("Tipo Intervento", ["Colloquio Supporto", "Valutazione Testistica", "Sostegno Familiare", "Osservazione"])
                nota_psi = st.text_area("Note Cliniche Psicologiche")
                if st.form_submit_button("REGISTRA NOTA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧠 {tipo_c}: {nota_psi}", "Psicologo", firma_op), True); st.rerun()

        # --- MODULO ASSISTENTE SOCIALE ---
        elif ruolo_corr == "Assistente Sociale":
            st.subheader("🤝 Area Sociale e Territoriale")
            with st.form("f_soc"):
                ambito = st.selectbox("Ambito", ["Rapporti Enti", "Contatti Famiglia", "Pianificazione Dimissione", "Progetto Esterno"])
                nota_soc = st.text_area("Dettagli Attività Sociale")
                if st.form_submit_button("REGISTRA INTERVENTO"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🤝 {ambito}: {nota_soc}", "Assistente Sociale", firma_op), True); st.rerun()

        # --- MODULO OPSI ---
        elif ruolo_corr == "OPSI":
            st.subheader("🛡️ Area Sicurezza e Vigilanza")
            with st.form("f_opsi"):
                settore = st.selectbox("Attività", ["Ronda Perimetrale", "Ispezione Camera", "Controllo Oggetti", "Rapporto Comportamentale"])
                crit = st.select_slider("Livello Allerta", options=["Verde", "Giallo", "Arancio", "Rosso"])
                nota_opsi = st.text_area("Report Sicurezza")
                if st.form_submit_button("INVIA REPORT"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🛡️ [{settore}] Allerta: {crit} | {nota_opsi}", "OPSI", firma_op), True); st.rerun()

        # --- GLI ALTRI RUOLI RIMANGONO INVARIATI COME RICHIESTO ---
        elif ruolo_corr == "Psichiatra":
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
                            if st.form_submit_button("AGGIORNA"): db_run("UPDATE terapie SET farmaco=?, dose=?, mat=?, pom=?, nott=? WHERE id_u=?", (nf, nd, int(nm), int(np), int(nn), tid), True); st.rerun()
                            if st.form_submit_button("SOSPENDE"): db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True); st.rerun()
        
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
                                st.markdown(f"<div class='therapy-container'><b>{f[1]}</b><br>{f[2]}</div>", unsafe_allow_html=True)
                                if st.button(f"CONFERMA", key=f"ok_{f[0]}_{t_n}"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({t_n}): {f[1]}", "Infermiere", firma_op), True); st.rerun()
            with t2:
                with st.form("vit"):
                    pa,fc,sat=st.text_input("PA"),st.text_input("FC"),st.text_input("SatO2")
                    if st.form_submit_button("REGISTRA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💓 PA:{pa} FC:{fc} Sat:{sat}", "Infermiere", firma_op), True); st.rerun()
            with t3:
                with st.form("ni"):
                    txt = st.text_area("Consegna Clinica"); 
                    if st.form_submit_button("SALVA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), txt, "Infermiere", firma_op), True); st.rerun()

        elif ruolo_corr == "OSS":
            with st.form("oss_f"):
                mans = st.multiselect("Mansioni:", ["Igiene", "Cambio", "Pulizia", "Accompagnamento"]); txt = st.text_area("Note")
                if st.form_submit_button("REGISTRA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧹 {', '.join(mans)} | {txt}", "OSS", firma_op), True); st.rerun()

        elif ruolo_corr == "Educatore":
            mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,)); saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
            st.markdown(f"<div class='cassa-card'>Saldo: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
            with st.form("cs"):
                tp, im, cau = st.selectbox("Tipo", ["ENTRATA", "USCITA"]), st.number_input("€"), st.text_input("Causale")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, oggi, cau, im, tp, firma_op), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💰 {tp}: {im}€ - {cau}", "Educatore", firma_op), True); st.rerun()

        st.divider(); render_postits(p_id)

# --- ALTRI MODULI RIMANGONO INVARIATI (Monitoraggio, Appuntamenti, Mappa, Admin) ---
elif nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO GENERALE</h2></div>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"📁 SCHEDA PAZIENTE: {nome}"): render_postits(pid)

elif nav == "🗺️ Mappa Posti Letto":
    st.markdown("<div class='section-banner'><h2>TABELLONE VISIVO POSTI LETTO</h2></div>", unsafe_allow_html=True)
    stanze_db = db_run("SELECT id, reparto, tipo FROM stanze ORDER BY id")
    paz_db = db_run("SELECT p.id, p.nome, a.stanza_id, a.letto FROM pazienti p LEFT JOIN assegnazioni a ON p.id = a.p_id")
    mappa = {s[0]: {'rep': s[1], 'tipo': s[2], 'letti': {1: None, 2: None}} for s in stanze_db}
    for pid, pnome, sid, letto in paz_db:
        if sid in mappa: mappa[sid]['letti'][letto] = {'id': pid, 'nome': pnome}
    c_a, c_b = st.columns(2)
    for r_code, col_obj in [("A", c_a), ("B", c_b)]:
        with col_obj:
            st.markdown(f"<div class='map-reparto'><div class='reparto-title'>Reparto {r_code}</div><div class='stanza-grid'>", unsafe_allow_html=True)
            for s_id, s_info in {k:v for k,v in mappa.items() if v['rep']==r_code}.items():
                p_count = len([v for v in s_info['letti'].values() if v])
                cls = "stanza-piena" if p_count==2 else ("stanza-occupata" if p_count==1 else "")
                st.markdown(f"<div class='stanza-tile {cls}'><div class='stanza-header'>{s_id} <small>{s_info['tipo']}</small></div>", unsafe_allow_html=True)
                for l in [1, 2]:
                    p = s_info['letti'][l]
                    st.markdown(f"<div class='letto-slot'>L{l}: <b>{p['nome'] if p else 'Libero'}</b></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div></div>", unsafe_allow_html=True)

elif nav == "📅 Appuntamenti":
    st.markdown("<div class='section-banner'><h2>GESTIONE APPUNTAMENTI</h2></div>", unsafe_allow_html=True)
    t_new, t_agenda = st.tabs(["➕ PROGRAMMA", "📋 AGENDA"])
    with t_new:
        with st.form("f_new_app"):
            p_l = db_run("SELECT id, nome FROM pazienti")
            if p_l:
                ps = st.selectbox("Paziente", [p[1] for p in p_l]); pid = [p[0] for p in p_l if p[1]==ps][0]; d = st.date_input("Data"); n = st.text_input("Causale")
                if st.form_submit_button("SALVA"):
                    db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore) VALUES (?,?,?,?,'PROGRAMMATO',?)", (pid, str(d), "", n, firma_op), True); st.rerun()
    with t_agenda:
        agenda = db_run("SELECT a.id_u, a.data, a.ora, p.nome, a.nota FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.stato='PROGRAMMATO'")
        for aid, adt, ahr, apn, ant in agenda:
            st.markdown(f"<div class='app-card'>📅 {adt} - <b>{apn}</b>: {ant}</div>", unsafe_allow_html=True)
            if st.button("FATTO", key=f"app_{aid}"): db_run("UPDATE appuntamenti SET stato='COMPLETATO' WHERE id_u=?", (aid,), True); st.rerun()

elif nav == "⚙️ Admin":
    st.markdown("<div class='section-banner'><h2>PANNELLO AMMINISTRAZIONE</h2></div>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["UTENTI", "PAZIENTI"])
    with tab1:
        for us, un, uc, uq in db_run("SELECT user, nome, cognome, qualifica FROM utenti"):
            st.write(f"**{un} {uc}** ({uq}) - ID: {us}")
    with tab2:
        with st.form("np"):
            np = st.text_input("Nuovo Paziente")
            if st.form_submit_button("AGGIUNGI"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
